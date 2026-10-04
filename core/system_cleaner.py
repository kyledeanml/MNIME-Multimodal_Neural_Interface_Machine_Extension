import os
import gc
import shutil

# Directories never touched by the purger (environments, VCS, model weights, training data).
EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "build_env", "node_modules",
    "models", "training", "unsloth_compiled_cache", "paper",
}
TEMP_SUFFIXES = (".tmp", ".tmp.pdf")

class SystemCleaner:
    """
    The MNIME System Resource Purger.
    Responsible for purging temporary file artifacts, stale vector caches,
    reclaiming RAM/VRAM, and cleaning orphaned system caches.
    """

    def __init__(self, root_dir: str = None):
        if root_dir is None:
            self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        else:
            self.root_dir = os.path.abspath(root_dir)

    def _walk_project(self):
        """os.walk over the project, pruning excluded directories in place."""
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            yield root, dirs, files

    def purge_temp_files(self) -> dict:
        """Removes *.tmp / *.tmp.pdf in project folders and the root build_log.txt."""
        candidates = []
        for root, _dirs, files in self._walk_project():
            for name in files:
                if name.lower().endswith(TEMP_SUFFIXES):
                    candidates.append(os.path.join(root, name))
        build_log = os.path.join(self.root_dir, "build_log.txt")
        if os.path.isfile(build_log):
            candidates.append(build_log)

        removed_files = []
        bytes_reclaimed = 0
        for file_path in candidates:
            try:
                file_size = os.path.getsize(file_path)
                os.remove(file_path)
                removed_files.append(file_path)
                bytes_reclaimed += file_size
            except OSError:
                pass

        return {
            "files_removed": len(removed_files),
            "bytes_reclaimed": bytes_reclaimed,
            "details": removed_files
        }

    def purge_python_cache(self) -> int:
        """Removes __pycache__ directories across the repository."""
        pycache_count = 0
        for root, dirs, _files in self._walk_project():
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")
                try:
                    shutil.rmtree(os.path.join(root, "__pycache__"))
                    pycache_count += 1
                except OSError:
                    pass
        return pycache_count

    def flush_memory(self):
        """
        Releases model memory: unloads the llama.cpp model (which owns the GPU/VRAM
        allocation), drops the in-memory global vector store, runs garbage collection,
        and clears torch's CUDA cache if torch is present (used by embeddings).
        """
        import sys
        nlp_mod = sys.modules.get("core.nlp_engine")
        if nlp_mod is not None and getattr(nlp_mod.NLPEngine, "_instance", None) is not None:
            try:
                nlp_mod.NLPEngine._instance.unload_model()
            except Exception:
                pass
        search_mod = sys.modules.get("core.search_engine")
        if search_mod is not None:
            search_mod.SearchEngine.release_global_store()

        gc.collect()
        torch = sys.modules.get("torch")
        if torch is not None:
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()
            except Exception:
                pass

    def on_app_exit(self):
        """Called from the main window on close: free memory, then remove temp files."""
        import sys
        self.flush_memory()
        if not getattr(sys, "frozen", False):
            self.purge_temp_files()

    def purge_all_resources(self) -> dict:
        """Executes a full system resource cleanup sweep (developer use)."""
        temp_results = self.purge_temp_files()
        cache_count = self.purge_python_cache()
        self.flush_memory()

        return {
            "status": "success",
            "temp_files_removed": temp_results["files_removed"],
            "bytes_reclaimed": temp_results["bytes_reclaimed"],
            "pycache_dirs_removed": cache_count,
        }

if __name__ == "__main__":
    cleaner = SystemCleaner()
    results = cleaner.purge_all_resources()
    print(">>> SYSTEM RESOURCE PURGE COMPLETE <<<")
    print(f"Temporary Files Removed: {results['temp_files_removed']}")
    print(f"Bytes Reclaimed: {results['bytes_reclaimed']} bytes")
    print(f"PyCache Directories Cleared: {results['pycache_dirs_removed']}")
