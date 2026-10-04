import os
import gc
import shutil
import glob

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

    def purge_temp_files(self) -> dict:
        """Finds and removes temporary files like *.tmp, *.tmp.pdf, build_log.txt, etc."""
        patterns = [
            "*.tmp",
            "*.tmp.pdf",
            "build_log.txt",
            "*.log",
            "temp_*",
        ]
        removed_files = []
        bytes_reclaimed = 0

        for pattern in patterns:
            search_path = os.path.join(self.root_dir, "**", pattern)
            for file_path in glob.glob(search_path, recursive=True):
                if ".git" in file_path:
                    continue
                try:
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    removed_files.append(file_path)
                    bytes_reclaimed += file_size
                except Exception:
                    pass

        return {
            "files_removed": len(removed_files),
            "bytes_reclaimed": bytes_reclaimed,
            "details": removed_files
        }

    def purge_python_cache(self) -> int:
        """Removes __pycache__ directories across the repository."""
        pycache_count = 0
        for root, dirs, files in os.walk(self.root_dir):
            if "__pycache__" in dirs:
                pycache_dir = os.path.join(root, "__pycache__")
                try:
                    shutil.rmtree(pycache_dir)
                    pycache_count += 1
                except Exception:
                    pass
        return pycache_count

    def flush_memory(self):
        """Forces Python garbage collection and attempts to release VRAM if torch/CUDA is active."""
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
        except ImportError:
            pass

    def purge_all_resources(self) -> dict:
        """Executes a full system resource cleanup sweep."""
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
