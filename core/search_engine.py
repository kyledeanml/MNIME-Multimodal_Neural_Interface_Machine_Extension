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
from collections import Counter
from typing import List, Callable, Optional, Dict, Any

# Ensure progress bars and telemetry are disabled globally to prevent GUI thread deadlocks
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

from .file_item import FileItem
from .logging_setup import get_logger

log = get_logger("search")

EMBEDDING_MODEL_DIRNAME = "bge-small-en-v1.5"


def get_embedding_model_path() -> str:
    """Locate the bundled embedding model so semantic search never touches the network."""
    from .app_icon import get_resource_path
    path = get_resource_path(os.path.join("models", EMBEDDING_MODEL_DIRNAME))
    if not os.path.isfile(os.path.join(path, "model.safetensors")):
        raise FileNotFoundError(
            f"Embedding model not found at '{path}'. Run 'python scripts/fetch_models.py' "
            "to download it once, or reinstall MNIME."
        )
    return path


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
            # Skip ignored directories to avoid hanging on dependencies
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

    @classmethod
    def get_embeddings(cls):
        """Thread-safe cached instance of HuggingFaceEmbeddings with disabled progress bars to prevent GUI thread deadlocks."""
        if cls._embedding_model is None:
            with cls._embedding_lock:
                if cls._embedding_model is None:
                    os.environ.setdefault("HF_HUB_OFFLINE", "1")
                    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
                    os.environ.setdefault("TQDM_DISABLE", "1")
                    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
                    try:
                        import transformers.utils.logging as tul
                        tul.disable_progress_bar()
                    except Exception:
                        pass
                    from langchain_huggingface import HuggingFaceEmbeddings
                    cls._embedding_model = HuggingFaceEmbeddings(
                        model_name=get_embedding_model_path(),
                        model_kwargs={"device": "cpu"},
                        encode_kwargs={"normalize_embeddings": True},
                    )
        return cls._embedding_model

    @staticmethod
    def get_global_cache_path() -> str:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.abspath(os.path.join(script_dir, "..", "models", "global_memory_cache"))
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def build_index(
        file_items: List[FileItem],
        use_smart_sampling: bool = True,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Any:
        """
        Loads texts from given files, including PDFs, and builds a FAISS vector index.
        Returns the FAISS vectorstore.
        """
        import pandas as pd
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document
        from langchain_text_splitters import RecursiveCharacterTextSplitter

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
        split = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)

        if use_smart_sampling and len(df) > 0:
            if progress_callback:
                progress_callback(50, "Smart Indexing (Extracting Probe Terms)...")

            frac = 0.1 if len(df) > 10 else 1.0
            sample = df['content'].sample(frac=frac, random_state=42).tolist()
            p_terms = SearchEngine.extract_probe_terms(sample)

            final_docs = []
            for i, (_, row) in enumerate(df.iterrows()):
                chunks = split.split_text(row['content'])
                for chk in chunks:
                    if any(term in chk for term in p_terms):
                        final_docs.append(Document(page_content=chk, metadata={"source": row['path']}))
                
                if progress_callback:
                    pct = 50 + int((i / len(df)) * 40)
                    progress_callback(pct, f"Smart Indexing ({i+1}/{len(df)})...")
            
            if not final_docs:
                if progress_callback:
                    progress_callback(90, "Fallback: Full Indexing...")
                for _, row in df.iterrows():
                    final_docs.extend([Document(page_content=c, metadata={"source": row['path']}) for c in split.split_text(row['content'])])

            if not final_docs:
                raise ValueError("No readable text could be extracted. Ensure the documents contain selectable text (not just scanned images).")

            docs_to_index = final_docs
            vstore = FAISS.from_documents(final_docs, emb)
            
        else:
            if progress_callback:
                progress_callback(50, "Full Indexing...")
                
            all_docs = []
            for i, (_, row) in enumerate(df.iterrows()):
                all_docs.extend([Document(page_content=c, metadata={"source": row['path']}) for c in split.split_text(row['content'])])
                if progress_callback:
                    pct = 50 + int((i / len(df)) * 40)
                    progress_callback(pct, f"Full Indexing ({i+1}/{len(df)})...")
            
            if not all_docs:
                raise ValueError("No readable text could be extracted. Ensure the documents contain selectable text (not just scanned images).")

            docs_to_index = all_docs
            vstore = FAISS.from_documents(all_docs, emb)

        # Update global persistent memory cache
        if progress_callback:
            progress_callback(95, "Updating Persistent Vector Store...")
        try:
            cache_path = SearchEngine.get_global_cache_path()
            if os.path.exists(os.path.join(cache_path, "index.faiss")):
                global_vstore = FAISS.load_local(cache_path, emb, allow_dangerous_deserialization=True)
                global_vstore.add_documents(docs_to_index)
                global_vstore.save_local(cache_path)
            else:
                global_vstore = FAISS.from_documents(docs_to_index, emb)
                global_vstore.save_local(cache_path)
        except Exception as e:
            log.exception("Failed to update global memory cache: %s", e)

        if progress_callback:
            progress_callback(100, "Index Ready!")

        return vstore

    @staticmethod
    def search(vectorstore: Any, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Searches the built FAISS index.
        Returns a list of dicts with 'content' and 'source'.
        """
        if not vectorstore:
            return []
            
        hits = vectorstore.similarity_search(query, k=k)
        results = []
        for hit in hits:
            results.append({
                "content": hit.page_content,
                "source": hit.metadata.get("source", "Unknown")
            })
        return results

    @staticmethod
    def search_global_memory(query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Searches the global persistent memory cache.
        Returns a list of dicts with 'content' and 'source'.
        """
        cache_path = SearchEngine.get_global_cache_path()
        if not os.path.exists(os.path.join(cache_path, "index.faiss")):
            return []
            
        emb = SearchEngine.get_embeddings()
        try:
            from langchain_community.vectorstores import FAISS
            global_vstore = FAISS.load_local(cache_path, emb, allow_dangerous_deserialization=True)
            hits = global_vstore.similarity_search(query, k=k)
            results = []
            for hit in hits:
                results.append({
                    "content": hit.page_content,
                    "source": hit.metadata.get("source", "Unknown")
                })
            return results
        except Exception as e:
            log.exception("Failed to search global memory cache: %s", e)
            return []
