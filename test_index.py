import sys
import os

# Add root to sys path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.search_engine import SearchEngine
from core.file_item import FileItem

def test_index():
    item = FileItem("test.txt", ".txt", "test")
    with open("test.txt", "w") as f:
        f.write("This is a test document for indexing.")
        
    try:
        SearchEngine.build_index([item], use_smart_sampling=True)
        print("Success!")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_index()
