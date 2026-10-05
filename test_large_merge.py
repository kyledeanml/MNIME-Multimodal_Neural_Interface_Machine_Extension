import os
import time
from core.pdf_engine import PDFEngine
from core.file_item import FileItem
import pymupdf

folder = "dummy_test_folder"
pdf_paths = [os.path.join(folder, f"{i}.pdf") for i in range(1, 5001)]
file_items = [FileItem(p) for p in pdf_paths if os.path.exists(p)]

print(f"Loaded {len(file_items)} file items for merging...")

output_pdf = "merged_5000_output.pdf"

start_time = time.time()

def progress(pct, msg):
    if pct % 10 == 0:
        print(f"[{pct}%] {msg}")

result = PDFEngine.combine_files(file_items, output_pdf, progress_callback=progress)

elapsed = time.time() - start_time
print(f"Successfully merged {len(file_items)} files in {elapsed:.2f} seconds.")

doc = pymupdf.open(output_pdf)
print(f"Merged output page count: {len(doc)} pages!")
print(f"Merged output size: {os.path.getsize(output_pdf) / (1024*1024):.2f} MB")
doc.close()
