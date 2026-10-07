import os
import re
import sys
import threading
import atexit
import signal
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import QSettings

from core.logging_setup import get_logger
from core.text_safety import sanitize_prompt_text, safe_filename

log = get_logger("nlp")

_STOP_TOKENS = ["<|im_end|>", "<|im_start|>"]


class NLPEngine:
    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        # Check for bundled model
        bundled_model = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "MNIME-Core-V5-Q4_K_M.gguf")
        default_path = bundled_model if os.path.exists(bundled_model) else ""

        settings = QSettings("MNIME", "MNIMEApp")
        saved_path = settings.value("gguf_model_path", "")
        if not saved_path or not os.path.exists(saved_path):
            self.model_path = default_path
            if default_path:
                settings.setValue("gguf_model_path", default_path)
        else:
            self.model_path = saved_path
            
        self.lora_path = settings.value("gguf_lora_path", "")
        try:
            self.lora_scale = float(settings.value("gguf_lora_scale", 1.0))
        except (ValueError, TypeError):
            self.lora_scale = 1.0
            
        self.llm = None
        self.is_loaded = False
        self.is_loading = False
        self.error = None
        # Re-entrant: a single llama.cpp context is NOT safe for concurrent calls,
        # so every inference and every load/unload goes through this lock.
        self._lock = threading.RLock()

        self._idle_ttl_timer = None
        try:
            self.nlp_idle_unload_minutes = float(settings.value("nlp_idle_unload_minutes", 5))
        except (ValueError, TypeError):
            self.nlp_idle_unload_minutes = 5.0

        # Free the model on normal interpreter exit
        atexit.register(self.unload_model)

        # Signal handlers can only be installed from the main thread
        if threading.current_thread() is threading.main_thread():
            try:
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
            except (ValueError, OSError) as e:
                log.debug("Signal handlers not installed: %s", e)

    def _signal_handler(self, signum, frame):
        self.unload_model()
        sys.exit(0)

    def _reset_idle_timer(self):
        with self._lock:
            if self._idle_ttl_timer:
                self._idle_ttl_timer.cancel()
            if self.is_loaded and self.nlp_idle_unload_minutes > 0:
                self._idle_ttl_timer = threading.Timer(self.nlp_idle_unload_minutes * 60, self._on_idle_timeout)
                self._idle_ttl_timer.daemon = True
                self._idle_ttl_timer.start()

    def _on_idle_timeout(self):
        log.info("NLP model idle TTL reached; unloading to free resources.")
        self.unload_model()

    def unload_model(self):
        with self._lock:
            if self._idle_ttl_timer:
                self._idle_ttl_timer.cancel()
                self._idle_ttl_timer = None
            if self.llm is not None:
                try:
                    self.llm.close()
                except AttributeError:
                    pass
                except Exception:
                    log.exception("Error closing model")
                self.llm = None
            self.is_loaded = False
            self.is_loading = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = NLPEngine()
        return cls._instance

    def set_model_path(self, path: str):
        self.model_path = path
        QSettings("MNIME", "MNIMEApp").setValue("gguf_model_path", path)
        self.reload_model()

    def set_lora(self, path: str, scale: float = 1.0, background: bool = True):
        """Set (or clear, with path="") the LoRA adapter and reload the model."""
        self.lora_path = path or ""
        self.lora_scale = scale
        settings = QSettings("MNIME", "MNIMEApp")
        settings.setValue("gguf_lora_path", self.lora_path)
        settings.setValue("gguf_lora_scale", scale)
        if background:
            self.reload_model_async()
        else:
            self.reload_model()

    def reload_model(self):
        """Reload the model synchronously. Call reload_model_async() to run on a background thread."""
        with self._lock:
            self.unload_model()
            self.error = None
            self.is_loading = True
            if not self.model_path or not os.path.exists(self.model_path):
                self.error = "Model path not set or file does not exist."
                self.is_loading = False
                log.warning(self.error)
                return False

            try:
                from llama_cpp import Llama

                kwargs = {
                    "model_path": self.model_path,
                    "n_ctx": 4096,
                    "n_threads": max(1, min(8, os.cpu_count() or 4)),
                    "n_gpu_layers": -1,
                    "main_gpu": 0,
                    "use_mlock": False,
                    "verbose": False,
                }
                
                if getattr(self, "lora_path", "") and os.path.exists(self.lora_path):
                    kwargs["lora_path"] = self.lora_path
                    kwargs["lora_scale"] = getattr(self, "lora_scale", 1.0)
                    log.info("Injecting LoRA adapter: %s (scale: %s)", self.lora_path, kwargs["lora_scale"])

                # Conditionally inject features that might not exist on older builds
                try:
                    kwargs["flash_attn"] = True
                    self.llm = Llama(**kwargs)
                except TypeError:
                    kwargs.pop("flash_attn", None)
                    self.llm = Llama(**kwargs)

                self.is_loaded = True
                self.is_loading = False
                self._reset_idle_timer()
                log.info("NLP model loaded: %s", self.model_path)
                
                # --- V5 Tone-Down Doohickey ---
                # Removing problematic token-level penalties that caused subword collateral damage.
                self.v5_logit_bias = {}
                # ------------------------------
                
                return True
            except Exception as e:
                self.error = str(e)
                self.is_loading = False
                log.exception("Failed to load NLP model")
                return False

    def reload_model_async(self):
        """Reload the model on a background thread so the UI stays responsive."""
        t = threading.Thread(target=self.reload_model, daemon=True)
        t.start()

    def check_model(self, auto_load: bool = False):
        enabled = str(QSettings("MNIME", "MNIMEApp").value("nlp_enabled", "true")).lower() == "true"
        if not enabled:
            self.unload_model()
            self.error = "NLP is globally disabled via Tabs Bar toggle."
            return

        if not self.is_loaded:
            if auto_load and not self.is_loading:
                self.reload_model()
                if not self.is_loaded:
                    return
            else:
                self.error = "Model not loaded. Click the reload button to start NLP."
                return

    def _complete(self, prompt: str, max_tokens: int, extra_stop: Optional[List[str]] = None) -> str:
        """Run one thread-safe completion. Raises if the model is unavailable."""
        with self._lock:
            if self.llm is None:
                raise RuntimeError(self.error or "Model not loaded.")
            self._reset_idle_timer()
            response = self.llm(
                prompt,
                max_tokens=max_tokens,
                stop=_STOP_TOKENS + (extra_stop or []),
                echo=False,
                logit_bias=getattr(self, 'v5_logit_bias', {}),
            )
        return response["choices"][0]["text"].strip()

    @staticmethod
    def _format_context(context_docs: List[Dict[str, Any]]) -> str:
        parts = []
        for doc in context_docs:
            source = sanitize_prompt_text(str(doc.get("source", "Unknown")), 300)
            content = sanitize_prompt_text(str(doc.get("content", "")), 3000)
            parts.append(f"Document ({source}):\n{content}")
        return sanitize_prompt_text("\n\n".join(parts))

    def generate_response(self, prompt: str, context_docs: List[Dict[str, Any]], history: List[Dict[str, str]] = None) -> str:
        self.check_model(auto_load=True)
        if not self.is_loaded:
            return f"Error: {self.error}"

        context_text = self._format_context(context_docs)
        system_prompt = (
            "You are an advanced local NLP assistant for MNIME. "
            "Use the provided document context (which includes document titles as sources) to answer the user's query accurately. "
            "You are allowed to perform clerical tasks, organize information, list document titles, summarize them, or discuss the documents themselves as long as it is in scope of the documents. "
            "If the answer is not in the context, state that clearly."
        )
        full_prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        
        if history:
            for i, msg in enumerate(history):
                # The last message is the current query, so we treat it specially
                if i == len(history) - 1 and msg["role"] == "user":
                    full_prompt += f"<|im_start|>user\nCONTEXT:\n{context_text}\n\nQUERY: {sanitize_prompt_text(msg['content'], 1000)}<|im_end|>\n"
                else:
                    role = msg["role"]
                    content = sanitize_prompt_text(msg["content"], 1000)
                    full_prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"
        else:
            full_prompt += f"<|im_start|>user\nCONTEXT:\n{context_text}\n\nQUERY: {sanitize_prompt_text(prompt, 1000)}<|im_end|>\n"

        full_prompt += "<|im_start|>assistant\n"
        try:
            return self._complete(full_prompt, 1024)
        except Exception as e:
            log.exception("generate_response failed")
            return f"Error generating response: {e}"

    def generate_response_stream(self, prompt: str, context_docs: List[Dict[str, Any]], history: List[Dict[str, str]] = None):
        self.check_model(auto_load=True)
        if not self.is_loaded:
            yield f"Error: {self.error}"
            return

        context_text = self._format_context(context_docs)
        system_prompt = (
            "You are an advanced local NLP assistant for MNIME. "
            "Use the provided document context (which includes document titles as sources) to answer the user's query accurately. "
            "You are allowed to perform clerical tasks, organize information, list document titles, summarize them, or discuss the documents themselves as long as it is in scope of the documents. "
            "If the answer is not in the context, state that clearly."
        )
        full_prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        
        if history:
            for i, msg in enumerate(history):
                # The last message is the current query, so we treat it specially
                if i == len(history) - 1 and msg["role"] == "user":
                    full_prompt += f"<|im_start|>user\nCONTEXT:\n{context_text}\n\nQUERY: {sanitize_prompt_text(msg['content'], 1000)}<|im_end|>\n"
                else:
                    role = msg["role"]
                    content = sanitize_prompt_text(msg["content"], 1000)
                    full_prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"
        else:
            full_prompt += f"<|im_start|>user\nCONTEXT:\n{context_text}\n\nQUERY: {sanitize_prompt_text(prompt, 1000)}<|im_end|>\n"

        full_prompt += "<|im_start|>assistant\n"
        try:
            with self._lock:
                if self.llm is None:
                    raise RuntimeError(self.error or "Model not loaded.")
                self._reset_idle_timer()
                stream = self.llm(
                    full_prompt,
                    max_tokens=1024,
                    stop=_STOP_TOKENS,
                    echo=False,
                    stream=True,
                    logit_bias=getattr(self, 'v5_logit_bias', {}),
                )
                for chunk in stream:
                    yield chunk["choices"][0]["text"]
        except Exception as e:
            log.exception("generate_response_stream failed")
            yield f"\n[Error generating response: {e}]"


    def synthesize_reference(self, source_text: str, context_docs: List[Dict[str, Any]]) -> str:
        self.check_model(auto_load=True)
        if not self.is_loaded:
            return f"Error: {self.error}"

        context_text = self._format_context(context_docs)
        system_prompt = (
            "You are an advanced legal and document analysis NLP. "
            "The user has highlighted a specific section from one document. "
            "You are provided with semantic search results from other open documents in their workspace. "
            "Synthesize a comparative brief: analyze how the highlighted text relates, conflicts, or aligns with the other documents."
        )
        full_prompt = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\nOTHER DOCUMENTS CONTEXT:\n{context_text}\n\n"
            f"HIGHLIGHTED SOURCE TEXT:\n{sanitize_prompt_text(source_text, 1500)}<|im_end|>\n"
            f"<|im_start|>assistant\nCOMPARATIVE BRIEF:\n"
        )
        try:
            return self._complete(full_prompt, 1024)
        except Exception as e:
            log.exception("synthesize_reference failed")
            return f"Error generating synthesis: {e}"

    def generate_verbose_bookmark(self, heading_candidate: str, page_text: str) -> str:
        self.check_model()
        if not self.is_loaded:
            return heading_candidate

        system_prompt = (
            "You are an expert document summarizer. "
            "Based on the following page text, generate a single, highly concise bookmark title (under 60 characters) that summarizes the core topic. "
            "Do not include introductory text, quotes, or markdown. Just return the bookmark text."
        )
        # Limit page text to 1500 chars to speed up inference and avoid huge context
        safe_text = sanitize_prompt_text(page_text, 1500).strip()
        safe_heading = sanitize_prompt_text(heading_candidate, 300)
        full_prompt = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\nHEADING CANDIDATE: {safe_heading}\n\nPAGE TEXT:\n{safe_text}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        try:
            title = self._complete(full_prompt, 25, extra_stop=["\n"])
            title = title.strip('\'"*- ')
            return title if title else heading_candidate
        except Exception:
            log.exception("generate_verbose_bookmark failed")
            return heading_candidate

    def generate_smart_filename(self, page_text: str, fallback_name: str) -> str:
        self.check_model()
        if not self.is_loaded or not page_text.strip():
            return fallback_name

        system_prompt = (
            "You are an expert document archiver. "
            "Based on the following document text, generate a highly concise filename (under 40 characters) that summarizes the core topic. "
            "Use underscores instead of spaces. Do not include file extensions. "
            "If the text is empty or meaningless, just reply UNKNOWN."
        )
        safe_text = sanitize_prompt_text(page_text, 1000).strip()
        full_prompt = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\nDOCUMENT TEXT:\n{safe_text}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        try:
            raw_name = self._complete(full_prompt, 20, extra_stop=["\n", "."])
            if not raw_name or "UNKNOWN" in raw_name.upper():
                return fallback_name

            clean_name = re.sub(r'[<>:"/\\|?*]', "", raw_name).replace(" ", "_").strip('\'"_-')
            clean_name = safe_filename(clean_name, fallback="")
            return clean_name if clean_name else fallback_name
        except Exception:
            log.exception("generate_smart_filename failed")
            return fallback_name
