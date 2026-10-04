import os
import json
import shutil
import threading
import logging
from typing import Optional, Dict, List
from PyQt6.QtCore import QObject, pyqtSignal

log = logging.getLogger("nlp")

# Files copied verbatim from the base model so the output folder is a complete
# HuggingFace model directory that convert_hf_to_gguf.py can consume directly.
_SIDECAR_FILES = (
    "config.json", "generation_config.json", "tokenizer.json",
    "tokenizer_config.json", "vocab.json", "merges.txt",
    "special_tokens_map.json", "added_tokens.json", "chat_template.jinja",
)

_MAX_SHARD_BYTES = 2 * 1024 ** 3


class AssimilationError(Exception):
    """Raised for user-correctable problems (bad input format, mismatched models)."""


def _resolve_weight_files(model_dir: str) -> Dict[str, str]:
    """Map tensor name -> safetensors file for a HuggingFace model directory."""
    if not os.path.isdir(model_dir):
        if model_dir.lower().endswith(".gguf"):
            raise AssimilationError(
                "GGUF input is not supported for assimilation. GGUF files are quantized "
                "(Q4_K_M is ~4-bit) and use different tensor names, so merging them "
                "destroys precision. Use the full-precision fp16 model folder instead "
                "(e.g. training/v4_out/MNIME-Core-V4-merged)."
            )
        raise AssimilationError(f"Not a model directory: {model_dir}")

    index_path = os.path.join(model_dir, "model.safetensors.index.json")
    if os.path.isfile(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            weight_map = json.load(f)["weight_map"]
        return {name: os.path.join(model_dir, fn) for name, fn in weight_map.items()}

    single = os.path.join(model_dir, "model.safetensors")
    if os.path.isfile(single):
        from safetensors import safe_open
        with safe_open(single, framework="pt") as f:
            return {name: single for name in f.keys()}

    raise AssimilationError(
        f"No .safetensors weights found in {model_dir}. Expected an fp16 HuggingFace folder."
    )


def _load_tensor(files: Dict[str, str], name: str):
    from safetensors import safe_open
    with safe_open(files[name], framework="pt") as f:
        return f.get_tensor(name)


def ties_merge_tensor(base, donor, ancestor=None, density: float = 0.3, weight: float = 1.0):
    """
    TIES-merge one tensor (computed in fp32, returned in the base dtype).

    Task vectors are taken relative to `ancestor` (the common pretrained model, e.g.
    Qwen2.5-1.5B-Instruct). If no ancestor is given, the donor delta is measured
    against the base itself.

      1. Trim: keep only the top `density` fraction of donor delta by magnitude.
      2. Elect sign: majority sign by total magnitude across base delta and donor delta.
      3. Disjoint merge: average only the entries agreeing with the elected sign.
    """
    import torch

    out_dtype = base.dtype
    b = base.float()
    d = donor.float()
    ref = ancestor.float() if ancestor is not None else b

    donor_delta = d - ref
    base_delta = (b - ref) if ancestor is not None else torch.zeros_like(b)

    # Non-float or scalar tensors: nothing meaningful to merge
    if donor_delta.numel() == 0:
        return base

    # 1. Trim donor delta to its top-k magnitudes
    k = max(1, int(donor_delta.numel() * density))
    if k < donor_delta.numel():
        threshold = donor_delta.abs().flatten().kthvalue(donor_delta.numel() - k + 1).values
        donor_delta = torch.where(donor_delta.abs() >= threshold, donor_delta, torch.zeros_like(donor_delta))

    # 2. Elect sign by summed magnitude
    elected = torch.sign(base_delta + donor_delta)

    # 3. Disjoint mean over entries that agree with the elected sign
    base_mask = (torch.sign(base_delta) == elected) & (base_delta != 0)
    donor_mask = (torch.sign(donor_delta) == elected) & (donor_delta != 0)
    total = base_mask.float() + donor_mask.float()
    summed = base_delta * base_mask + donor_delta * donor_mask * weight
    merged_delta = torch.where(total > 0, summed / total.clamp(min=1), torch.zeros_like(summed))

    # Where only the donor contributes, apply its (weighted) delta in full
    return (ref + merged_delta).to(out_dtype) if ancestor is not None else (b + merged_delta).to(out_dtype)


def linear_merge_tensor(base, donor, weight: float = 0.5):
    out_dtype = base.dtype
    return (base.float() * (1.0 - weight) + donor.float() * weight).to(out_dtype)


class NeuralAssimilationEngine(QObject):
    """
    The Neural Assimilation Engine.

    Ingests a donor model and selectively merges its high-value parameter deltas
    into MNIME-Core. Operates on FULL-PRECISION (fp16/bf16) HuggingFace safetensors
    folders, tensor by tensor, so peak memory stays near one tensor plus one shard
    rather than the whole model. The result is a complete HF folder; convert it to
    GGUF with llama.cpp (convert_hf_to_gguf.py) and quantize afterwards.

    Quantized GGUF files are rejected on purpose: merging 4-bit weights is lossy.
    """

    progress_updated = pyqtSignal(int, str)
    fusion_complete = pyqtSignal(str)
    fusion_failed = pyqtSignal(str)

    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        super().__init__()
        self.is_assimilating = False
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = NeuralAssimilationEngine()
        return cls._instance

    def assimilate_model_async(
        self,
        base_model_path: str,
        donor_model_path: str,
        output_path: str,
        method: str = "ties",
        ancestor_path: Optional[str] = None,
        density: float = 0.3,
        weight: float = 1.0,
    ):
        """
        base_model_path   fp16 HF folder of MNIME-Core (the model being grown)
        donor_model_path  fp16 HF folder of the donor model
        output_path       directory to write the merged HF folder into
        method            "ties" or "linear"
        ancestor_path     optional common ancestor (e.g. Qwen2.5-1.5B-Instruct) for task vectors
        density           fraction of donor deltas kept by TIES trimming (0-1)
        weight            donor strength (TIES scale, or linear interpolation factor)
        """
        if self.is_assimilating:
            self.fusion_failed.emit("Assimilation engine is already busy digesting another model.")
            return

        self.is_assimilating = True
        thread = threading.Thread(
            target=self._assimilate_worker,
            args=(base_model_path, donor_model_path, output_path, method, ancestor_path, density, weight),
            daemon=True,
        )
        thread.start()

    def assimilate_model(self, *args, **kwargs) -> str:
        """Synchronous variant for scripts and tests. Returns the output directory."""
        return self._run_merge(*args, **kwargs)

    # ------------------------------------------------------------------

    def _assimilate_worker(self, base_model_path, donor_model_path, output_path, method,
                           ancestor_path, density, weight):
        try:
            with self._lock:
                out = self._run_merge(base_model_path, donor_model_path, output_path, method,
                                      ancestor_path, density, weight)
                self.progress_updated.emit(100, "Assimilation successfully completed.")
                self.fusion_complete.emit(out)
        except AssimilationError as e:
            self.fusion_failed.emit(str(e))
        except Exception as e:
            log.exception("Fatal error during model assimilation.")
            self.fusion_failed.emit(str(e))
        finally:
            self.is_assimilating = False

    def _emit(self, pct: int, msg: str):
        self.progress_updated.emit(pct, msg)

    def _run_merge(self, base_model_path, donor_model_path, output_path, method="ties",
                   ancestor_path=None, density=0.3, weight=1.0) -> str:
        import torch
        from safetensors.torch import save_file

        if method not in ("ties", "linear"):
            raise AssimilationError(f"Unknown merge method '{method}'. Use 'ties' or 'linear'.")
        if not 0.0 < density <= 1.0:
            raise AssimilationError("density must be in (0, 1].")

        self._emit(5, "Indexing base and donor weights...")
        base_files = _resolve_weight_files(base_model_path)
        donor_files = _resolve_weight_files(donor_model_path)
        anc_files = _resolve_weight_files(ancestor_path) if ancestor_path else None

        shared = [n for n in base_files if n in donor_files]
        if not shared:
            raise AssimilationError("Base and donor share no tensor names. They are different architectures.")
        missing = len(base_files) - len(shared)
        if missing:
            log.warning("%d base tensors have no donor counterpart and are copied unchanged.", missing)

        os.makedirs(output_path, exist_ok=True)
        names = sorted(base_files)
        total = len(names)

        shard: Dict[str, "torch.Tensor"] = {}
        shard_bytes = 0
        shard_idx = 0
        weight_map: Dict[str, str] = {}
        shard_files: List[str] = []

        def flush():
            nonlocal shard, shard_bytes, shard_idx
            if not shard:
                return
            shard_idx += 1
            fname = f"model-{shard_idx:05d}.safetensors"
            save_file(shard, os.path.join(output_path, fname), metadata={"format": "pt"})
            for n in shard:
                weight_map[n] = fname
            shard_files.append(fname)
            shard, shard_bytes = {}, 0

        for i, name in enumerate(names):
            base_t = _load_tensor(base_files, name)
            merged = base_t
            if name in donor_files and base_t.is_floating_point():
                donor_t = _load_tensor(donor_files, name)
                if donor_t.shape != base_t.shape:
                    raise AssimilationError(
                        f"Shape mismatch on '{name}': base {tuple(base_t.shape)} vs donor {tuple(donor_t.shape)}."
                    )
                if method == "ties":
                    anc_t = _load_tensor(anc_files, name) if anc_files and name in anc_files else None
                    merged = ties_merge_tensor(base_t, donor_t, anc_t, density, weight)
                else:
                    merged = linear_merge_tensor(base_t, donor_t, weight)

            shard[name] = merged.contiguous()
            shard_bytes += merged.numel() * merged.element_size()
            if shard_bytes >= _MAX_SHARD_BYTES:
                flush()

            if i % 8 == 0:
                pct = 10 + int(80 * (i + 1) / total)
                self._emit(pct, f"Assimilating tensor {i + 1}/{total}: {name}")

        flush()

        self._emit(92, "Writing index and model metadata...")
        total_size = sum(os.path.getsize(os.path.join(output_path, f)) for f in shard_files)
        with open(os.path.join(output_path, "model.safetensors.index.json"), "w", encoding="utf-8") as f:
            json.dump({"metadata": {"total_size": total_size}, "weight_map": weight_map}, f, indent=2)

        for fn in _SIDECAR_FILES:
            src = os.path.join(base_model_path, fn)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(output_path, fn))

        self._emit(98, "Merged model saved. Convert to GGUF with llama.cpp to run it in MNIME.")
        return output_path
