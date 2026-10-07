import time
import os
import pymupdf
import sys

# Ensure MNIME is in python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.file_item import FileItem
from core.pdf_engine import PDFEngine

def create_dummy_pdf(path, pages=20):
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text(pymupdf.Point(50, 50), f"This is a dummy page {i} for benchmarking NLP filename generation. We are testing how long it takes to process this entire document using the NLP engine. It contains various text that the AI must summarize to generate a smart filename.", fontsize=12)
    doc.save(path)
    doc.close()

if __name__ == "__main__":
    # Pre-load PyQt Application to use QSettings
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    dummy_pdf_path = os.path.abspath("dummy_benchmark.pdf")
    output_dir = os.path.abspath("benchmark_output")
    
    print(f"Creating dummy PDF with 20 pages at {dummy_pdf_path}...")
    create_dummy_pdf(dummy_pdf_path, 20)
    file_item = FileItem(dummy_pdf_path)
    
    from PyQt6.QtCore import QSettings
    settings = QSettings("MNIME", "MNIMEApp")
    
    # Benchmark without NLP
    print("\nBenchmarking without NLP...")
    settings.setValue("nlp_smart_indexing", False)
    settings.sync()
    t0 = time.time()
    PDFEngine.split_pdf(file_item, output_dir)
    t1 = time.time()
    time_without = t1 - t0
    print(f"Time without NLP (20 pages): {time_without:.2f} seconds ({time_without/20:.4f}s per page)")
    
    # Benchmark with NLP
    print("\nBenchmarking with NLP...")
    settings.setValue("nlp_smart_indexing", True)
    settings.sync()
    
    from core.nlp_engine import NLPEngine
    nlp = NLPEngine.get_instance()
    print("Loading NLP model...")
    nlp.reload_model()
    
    t0 = time.time()
    PDFEngine.split_pdf(file_item, output_dir)
    t1 = time.time()
    time_with = t1 - t0
    print(f"Time with NLP (20 pages): {time_with:.2f} seconds ({time_with/20:.4f}s per page)")
    
    print(f"\nNLP overhead is {time_with/time_without:.1f}x slower.")
