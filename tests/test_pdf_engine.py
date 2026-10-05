import os
import pytest
import pymupdf
import numpy as np
from PIL import Image
from core.pdf_engine import PDFEngine, PDFInputError, open_pdf_checked
from core.file_item import FileItem

@pytest.fixture
def dummy_pdf(tmp_path):
    pdf_path = str(tmp_path / "dummy.pdf")
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Hello World", fontsize=20)
    doc.save(pdf_path)
    doc.close()
    return pdf_path

def test_pdf_to_jpg_not_blank(dummy_pdf, tmp_path):
    item = FileItem(dummy_pdf)
    
    out_dir = str(tmp_path / "jpgs")
    os.makedirs(out_dir, exist_ok=True)
    
    files = PDFEngine.convert_pdf_to_jpg(item, out_dir)
    assert len(files) == 1
    
    # Check that it is not blank (not all white)
    img = Image.open(files[0])
    arr = np.array(img)
    
    # A completely white image would have all pixels at 255
    # Since we drew "Hello World", it shouldn't be all 255
    assert arr.min() < 255

def test_merge_pdfs(dummy_pdf, tmp_path):
    out_file = str(tmp_path / "merged.pdf")
    PDFEngine.combine_files([FileItem(dummy_pdf), FileItem(dummy_pdf)], out_file)
    
    assert os.path.exists(out_file)
    doc = pymupdf.open(out_file)
    assert doc.page_count == 2
    doc.close()

def test_split_pdf(dummy_pdf, tmp_path):
    # Make a 2-page pdf
    merged = str(tmp_path / "merged.pdf")
    PDFEngine.combine_files([FileItem(dummy_pdf), FileItem(dummy_pdf)], merged)
    
    out_dir = str(tmp_path / "splits")
    os.makedirs(out_dir, exist_ok=True)
    
    files = PDFEngine.split_pdf(FileItem(merged), out_dir)
    assert len(files) == 2
    for f in files:
        doc = pymupdf.open(f)
        assert doc.page_count == 1
        doc.close()

def test_empty_pdf_handled(tmp_path):
    empty_pdf = str(tmp_path / "empty.pdf")
    # Write a 0 byte file
    with open(empty_pdf, "wb") as f:
        pass
    
    with pytest.raises(PDFInputError):
        open_pdf_checked(empty_pdf)

def test_merge_pdfs_batched(dummy_pdf, tmp_path):
    # Test batching logic (>250 items)
    items = [FileItem(dummy_pdf) for _ in range(300)]
    out_file = str(tmp_path / "merged_batched.pdf")
    PDFEngine.combine_files(items, out_file)
    
    assert os.path.exists(out_file)
    doc = pymupdf.open(out_file)
    assert doc.page_count == 300
    doc.close()

