import os
import sys

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.system_cleaner import SystemCleaner

def main():
    print(">>> INITIALIZATION: SYSTEM RESOURCE PURGER <<<")
    print("Scanning system for orphaned temp files, stale caches, and uncollected RAM/VRAM waste...\n")

    cleaner = SystemCleaner()
    results = cleaner.purge_all_resources()

    print(f"[1/3] Temporary File Purge: {results['temp_files_removed']} files removed ({results['bytes_reclaimed']} bytes reclaimed)")
    print(f"[2/3] PyCache Directory Purge: {results['pycache_dirs_removed']} directories flushed")
    print("[3/3] RAM / VRAM Memory Flush: Garbage collection and GPU memory clear executed successfully.")

    print("\n>>> SYSTEM RESOURCE CLEANUP COMPLETED SUCCESSFULLY <<<")

if __name__ == "__main__":
    main()
