"""
Semantic Search Engine for MNIME.
Adapts the "CodeEyes" codebase semantic search concept for offline document/codebase querying.
"""

import os
import zipfile
import shutil
import time
import stat
import re
import threading
import json
from collections import Counter
from typing import List, Callable, Optional, Dict, Any

from .file_item import FileItem
from .logging_setup import get_logger

log = get_logger("search")

EMBEDDING_MODEL_FILENAME = "bge-small-en-v1.5-q8_0.gguf"

def get_embedding_model_path() -> str:
    """Locate the bundled embedding model so semantic search never touches the network."""
    from .app_icon import get_resource_path
    path = get_resource_path(os.path.join("models", "bge-small-en-v1.5", EMBEDDING_MODEL_FILENAME))
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Embedding model not found at '{path}'. Run scripts/download_gguf.py to download it."
        )
    return path

class VectorStore:
    def __init__(self, dim: int = 384):
        import faiss
        self.index = faiss.IndexFlatIP(dim)
        self.docs = []
        
    def add_documents(self, docs: List[Dict[str, str]], embeddings: List[List[float]]):
        if not embeddings: return
        import faiss
        import numpy as np
        emb_arr = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(emb_arr)
        self.index.add(emb_arr)
        self.docs.extend(docs)

    def similarity_search(self, query_emb: List[float], k: int = 5) -> List[Dict[str, str]]:
        if self.index.ntotal == 0:
            return []
        import faiss
        import numpy as np
        emb_arr = np.array([query_emb], dtype=np.float32)
        faiss.normalize_L2(emb_arr)
        D, I = self.index.search(emb_arr, k)
        results = []
        for i in range(len(I[0])):
            idx = I[0][i]
            if idx != -1 and idx < len(self.docs):
                results.append(self.docs[idx])
        return results

    def save_local(self, path: str):
        import faiss
        os.makedirs(path, exist_ok=True)
        faiss.write_index(self.index, os.path.join(path, "index.faiss"))
        with open(os.path.join(path, "docs.json"), "w", encoding="utf-8") as f:
            json.dump(self.docs, f)

    @classmethod
    def load_local(cls, path: str) -> "VectorStore":
        import faiss
        vs = cls()
        vs.index = faiss.read_index(os.path.join(path, "index.faiss"))
        with open(os.path.join(path, "docs.json"), "r", encoding="utf-8") as f:
            vs.docs = json.load(f)
        return vs

def simple_text_split(text: str, chunk_size: int = 1500, chunk_overlap: int = 200) -> List[str]:
    chunks = []
    i = 0
    while i < len(text):
        chunk = text[i:i+chunk_size]
        if i + chunk_size < len(text):
            break_idx = max(chunk.rfind('\n'), chunk.rfind('. '))
            if break_idx > chunk_size // 2:
                chunk = text[i:i+break_idx+1]
        chunks.append(chunk)
        i += len(chunk) - chunk_overlap
        if i < 0: i = 0
    return chunks

class SearchEngine:
    """Core backend engine for semantic search over codebases and text documents."""

    @staticmethod
    def _safe_remove_directory(directory_path: str):
        if not os.path.exists(directory_path):
            return
        def remove_readonly(func, p, _):
            os.chmod(p, stat.S_IWRITE)
            func(p)
        try:
            shutil.rmtree(directory_path, onexc=remove_readonly)
        except OSError:
            time.sleep(0.1)
            try:
                shutil.rmtree(directory_path, onexc=remove_readonly)
            except OSError:
                try:
                    trash_path = f"{directory_path}_trash_{int(time.time())}"
                    os.rename(directory_path, trash_path)
                except OSError:
                    pass

    @staticmethod
    def extract_probe_terms(contents: List[str], top_k: int = 20) -> List[str]:
        tokens = []
        for content in contents:
            tokens += re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{3,}\b", content)
        common = Counter(tokens).most_common(top_k)
        return [term for term, _ in common]

    @staticmethod
    def load_files(root_dir: str) -> List[Dict[str, Any]]:
        data_list = []
        ignore_dirs = {'.venv', 'venv', 'env', '.git', 'node_modules', '__pycache__', '.idea', '.vscode'}
        
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in (".py", ".txt", ".md", ".json", ".csv", ".js", ".ts", ".html", ".css", ".cpp", ".c", ".h", ".java"):
                    fpath = os.path.join(root, fname)
                    try:
                        try:
                            with open(fpath, 'r', encoding='utf-8') as f_reader:
                                content_str = f_reader.read()
                        except UnicodeDecodeError:
                            with open(fpath, 'r', encoding='latin-1', errors='replace') as f_reader:
                                content_str = f_reader.read()
                        data_list.append({
                            "path": fpath,
                            "content": content_str,
                            "lines": len(content_str.splitlines())
                        })
                    except (OSError, PermissionError):
                        continue
        return data_list

    @staticmethod
    def _extract_text_windows_ocr(pixmap) -> str:
        try:
            import asyncio
            from winsdk.windows.media.ocr import OcrEngine
            from winsdk.windows.globalization import Language
            from winsdk.windows.graphics.imaging import BitmapDecoder
            from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
            
            async def _recognize(png_bytes):
                stream = InMemoryRandomAccessStream()
                writer = DataWriter(stream)
                writer.write_bytes(png_bytes)
                await writer.store_async()
                writer.detach_stream()
                stream.seek(0)
                
                decoder = await BitmapDecoder.create_async(stream)
                software_bitmap = await decoder.get_software_bitmap_async()
                
                engine = OcrEngine.try_create_from_user_profile_languages()
                if not engine:
                    engine = OcrEngine.try_create_from_language(Language("en-US"))
                
                if not engine:
                    return ""
                    
                result = await engine.recognize_async(software_bitmap)
                return result.text
                
            return asyncio.run(asyncio.wait_for(_recognize(pixmap.tobytes("png")), timeout=10.0))
        except Exception:
            return ""

    _embedding_model = None
    _embedding_lock = threading.Lock()
    _idle_timer = None

    @classmethod
    def get_embeddings(cls):
        """Thread-safe cached instance of llama.cpp embedding model."""
        with cls._embedding_lock:
            if cls._embedding_model is None:
                from llama_cpp import Llama
                cls._embedding_model = Llama(
                    model_path=get_embedding_model_path(),
                    embedding=True,
                    n_ctx=512,
                    verbose=False
                )
            cls._reset_idle_timer()
        return cls._embedding_model

    @classmethod
    def _reset_idle_timer(cls):
        if cls._idle_timer:
            cls._idle_timer.cancel()
        from PyQt6.QtCore import QSettings
        settings = QSettings("kyledeanml", "MNIME")
        idle_minutes = int(settings.value("nlp_idle_unload_minutes", 5))
        if idle_minutes > 0:
            cls._idle_timer = threading.Timer(idle_minutes * 60, cls.unload_model)
            cls._idle_timer.start()

    @classmethod
    def unload_model(cls):
        with cls._embedding_lock:
            if cls._embedding_model is not None:
                del cls._embedding_model
                cls._embedding_model = None
                log.info("Unloaded embedding model due to idle timeout.")

    _global_vstore = None

    @staticmethod
    def get_global_cache_path() -> str:
        """Persistent global vector store location (user-writable, survives reinstalls)."""
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".mnime")
        path = os.path.join(base, "MNIME", "global_vector_store_v2")
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def build_index(
        file_items: List[FileItem],
        use_smart_sampling: bool = True,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Any:
        import pandas as pd

        if progress_callback:
            progress_callback(10, "Preparing files...")

        data_list = []
        for file_item in file_items:
            if file_item.extension == ".pdf":
                try:
                    import pymupdf
                    with pymupdf.open(file_item.file_path) as doc:
                        parts = []
                        total_doc_pages = max(1, len(doc))
                        for i, page in enumerate(doc):
                            if progress_callback:
                                read_pct = 10 + int(((i + 1) / total_doc_pages) * 28)
                                progress_callback(read_pct, f"Reading PDF Page {i+1}/{total_doc_pages}...")
                            text = page.get_text()
                            if not text.strip():
                                if progress_callback:
                                    progress_callback(read_pct, f"Running OCR on PDF Page {i+1}/{total_doc_pages}...")
                                rect = page.rect
                                zoom = 2.0
                                if rect.width * zoom > 2400:
                                    zoom = 2400 / max(1, rect.width)
                                if rect.height * zoom > 2400:
                                    zoom = min(zoom, 2400 / max(1, rect.height))
                                pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
                                text = SearchEngine._extract_text_windows_ocr(pix)
                            parts.append(text)
                    content_str = "\n".join(parts)
                    data_list.append({
                        "path": file_item.file_path,
                        "content": content_str,
                        "lines": len(content_str.splitlines())
                    })
                except Exception:
                    log.exception("Could not read PDF for indexing: %s", file_item.file_path)
            elif file_item.extension in (".py", ".txt", ".md", ".json", ".csv", ".js", ".ts", ".html", ".css", ".cpp", ".c", ".h", ".java"):
                try:
                    try:
                        with open(file_item.file_path, 'r', encoding='utf-8') as f_reader:
                            content_str = f_reader.read()
                    except UnicodeDecodeError:
                        with open(file_item.file_path, 'r', encoding='latin-1', errors='replace') as f_reader:
                            content_str = f_reader.read()
                    data_list.append({
                        "path": file_item.file_path,
                        "content": content_str,
                        "lines": len(content_str.splitlines())
                    })
                except Exception:
                    log.exception("Could not read file for indexing: %s", file_item.file_path)

        if not data_list:
            raise ValueError("No valid text files found to index.")

        df = pd.DataFrame(data_list)

        if progress_callback:
            progress_callback(40, "Initializing Embedding Model...")

        emb = SearchEngine.get_embeddings()

        final_docs = []
        if use_smart_sampling and len(df) > 0:
            if progress_callback:
                progress_callback(50, "Smart Indexing (Extracting Probe Terms)...")

            frac = 0.1 if len(df) > 10 else 1.0
            sample = df['content'].sample(frac=frac, random_state=42).tolist()
            p_terms = SearchEngine.extract_probe_terms(sample)

            for i, (_, row) in enumerate(df.iterrows()):
                chunks = simple_text_split(row['content'])
                for chk in chunks:
                    if any(term in chk for term in p_terms):
                        final_docs.append({"content": chk, "source": row['path']})
                
                if progress_callback:
                    pct = 50 + int((i / len(df)) * 40)
                    progress_callback(pct, f"Smart Indexing ({i+1}/{len(df)})...")
            
            if not final_docs:
                if progress_callback:
                    progress_callback(90, "Fallback: Full Indexing...")
                for _, row in df.iterrows():
                    final_docs.extend([{"content": c, "source": row['path']} for c in simple_text_split(row['content'])])

            if not final_docs:
                raise ValueError("No readable text could be extracted.")
        else:
            if progress_callback:
                progress_callback(50, "Full Indexing...")
                
            for i, (_, row) in enumerate(df.iterrows()):
                final_docs.extend([{"content": c, "source": row['path']} for c in simple_text_split(row['content'])])
                if progress_callback:
                    pct = 50 + int((i / len(df)) * 40)
                    progress_callback(pct, f"Full Indexing ({i+1}/{len(df)})...")
            
            if not final_docs:
                raise ValueError("No readable text could be extracted.")

        # Batch encode
        if progress_callback:
            progress_callback(92, "Generating Embeddings...")
            
        embeddings_res = emb.create_embedding([doc["content"] for doc in final_docs])
        embeddings = [e["embedding"] for e in embeddings_res["data"]]

        vstore = VectorStore(dim=len(embeddings[0]))
        vstore.add_documents(final_docs, embeddings)

        if progress_callback:
            progress_callback(95, "Updating Persistent Vector Store...")
            
        try:
            cache_path = SearchEngine.get_global_cache_path()
            if os.path.exists(os.path.join(cache_path, "index.faiss")):
                global_vstore = VectorStore.load_local(cache_path)
                global_vstore.add_documents(final_docs, embeddings)
                global_vstore.save_local(cache_path)
            else:
                global_vstore = VectorStore(dim=len(embeddings[0]))
                global_vstore.add_documents(final_docs, embeddings)
                global_vstore.save_local(cache_path)
            SearchEngine._global_vstore = global_vstore
        except Exception as e:
            log.exception("Failed to update global vector store: %s", e)

        if progress_callback:
            progress_callback(100, "Index Ready!")

        return vstore

    @staticmethod
    def search(vectorstore: Any, query: str, k: int = 5) -> List[Dict[str, Any]]:
        if not vectorstore:
            return []
        
        emb = SearchEngine.get_embeddings()
        q_emb = emb.create_embedding(query)["data"][0]["embedding"]
        hits = vectorstore.similarity_search(q_emb, k=k)
        return hits

    @staticmethod
    def search_global_memory(query: str, k: int = 5) -> List[Dict[str, Any]]:
        try:
            if SearchEngine._global_vstore is None:
                cache_path = SearchEngine.get_global_cache_path()
                if not os.path.exists(os.path.join(cache_path, "index.faiss")):
                    return []
                SearchEngine._global_vstore = VectorStore.load_local(cache_path)
            
            emb = SearchEngine.get_embeddings()
            q_emb = emb.create_embedding(query)["data"][0]["embedding"]
            hits = SearchEngine._global_vstore.similarity_search(q_emb, k=k)
            return hits
        except Exception as e:
            log.exception("Failed to search global vector store: %s", e)
            return []

    @staticmethod
    def release_global_store():
        SearchEngine._global_vstore = None

