import json
import pytest

torch = pytest.importorskip("torch")
safetensors_torch = pytest.importorskip("safetensors.torch")

from core.fusion_engine import (
    NeuralAssimilationEngine, AssimilationError,
    ties_merge_tensor, linear_merge_tensor,
)


def _make_model(path, tensors):
    path.mkdir(parents=True, exist_ok=True)
    safetensors_torch.save_file(tensors, str(path / "model.safetensors"), metadata={"format": "pt"})
    (path / "config.json").write_text(json.dumps({"model_type": "test"}))


def test_ties_applies_donor_delta_and_keeps_dtype():
    anc = torch.zeros(100, dtype=torch.float16)
    base = anc.clone()
    donor = torch.zeros(100, dtype=torch.float16)
    donor[:10] = 1.0  # top-10% delta
    out = ties_merge_tensor(base, donor, anc, density=0.1, weight=1.0)
    assert out.dtype == torch.float16
    assert torch.allclose(out[:10].float(), torch.ones(10))
    assert torch.allclose(out[10:].float(), torch.zeros(90))


def test_ties_trims_small_deltas():
    anc = torch.zeros(100, dtype=torch.float16)
    donor = torch.full((100,), 0.01, dtype=torch.float16)
    donor[0] = 5.0
    out = ties_merge_tensor(anc.clone(), donor, anc, density=0.01, weight=1.0)
    assert out[0].item() == pytest.approx(5.0)
    assert torch.count_nonzero(out) == 1


def test_ties_sign_conflict_resolves_to_majority():
    anc = torch.zeros(4, dtype=torch.float32)
    base = torch.tensor([3.0, 3.0, 0.0, 0.0])
    donor = torch.tensor([-1.0, 4.0, 2.0, 0.0])
    out = ties_merge_tensor(base, donor, anc, density=1.0, weight=1.0)
    # idx0: base +3 beats donor -1 -> elected + -> only base kept -> 3
    assert out[0].item() == pytest.approx(3.0)
    # idx1: both positive -> mean (3+4)/2
    assert out[1].item() == pytest.approx(3.5)
    # idx2: only donor
    assert out[2].item() == pytest.approx(2.0)


def test_linear_merge():
    a = torch.zeros(4, dtype=torch.float16)
    b = torch.ones(4, dtype=torch.float16)
    assert torch.allclose(linear_merge_tensor(a, b, 0.25).float(), torch.full((4,), 0.25))


def test_full_merge_writes_valid_hf_folder(tmp_path):
    g = torch.Generator().manual_seed(0)
    anc = {"w": torch.randn(8, 8, generator=g).half(), "b": torch.randn(8, generator=g).half()}
    base = {k: v.clone() for k, v in anc.items()}
    donor = {k: (v + torch.randn_like(v.float()).half()) for k, v in anc.items()}
    _make_model(tmp_path / "anc", anc)
    _make_model(tmp_path / "base", base)
    _make_model(tmp_path / "donor", donor)

    engine = NeuralAssimilationEngine()
    out = engine.assimilate_model(
        str(tmp_path / "base"), str(tmp_path / "donor"), str(tmp_path / "out"),
        method="ties", ancestor_path=str(tmp_path / "anc"), density=0.5,
    )
    idx = json.loads((tmp_path / "out" / "model.safetensors.index.json").read_text())
    assert set(idx["weight_map"]) == {"w", "b"}
    assert (tmp_path / "out" / "config.json").exists()

    merged = safetensors_torch.load_file(str(tmp_path / "out" / idx["weight_map"]["w"]))["w"]
    assert merged.dtype == torch.float16
    assert not torch.equal(merged, base["w"])  # donor actually changed the weights


def test_shape_mismatch_raises(tmp_path):
    _make_model(tmp_path / "base", {"w": torch.zeros(4, 4).half()})
    _make_model(tmp_path / "donor", {"w": torch.zeros(2, 2).half()})
    with pytest.raises(AssimilationError):
        NeuralAssimilationEngine().assimilate_model(
            str(tmp_path / "base"), str(tmp_path / "donor"), str(tmp_path / "out"))


def test_gguf_input_rejected(tmp_path):
    _make_model(tmp_path / "base", {"w": torch.zeros(4).half()})
    fake = tmp_path / "donor.gguf"
    fake.write_bytes(b"GGUF")
    with pytest.raises(AssimilationError, match="fp16"):
        NeuralAssimilationEngine().assimilate_model(
            str(tmp_path / "base"), str(fake), str(tmp_path / "out"))
