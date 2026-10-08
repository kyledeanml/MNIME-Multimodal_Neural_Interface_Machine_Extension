"""
High-Performance PDF Engine implementing core document transformations.
Uses PyMuPDF (C-level rendering) for blazing-fast batch operations with seamless
fallbacks to pypdf and Pillow.
"""

import os
import io
from typing import List, Callable, Optional
from .file_item import FileItem
from .logging_setup import get_logger
from .text_safety import safe_filename

log = get_logger("pdf_engine")


class PDFInputError(ValueError):
    """A problem with the user's input file (encrypted, empty, missing) that no fallback can fix."""


def open_pdf_checked(path: str):
    """Open a PDF with PyMuPDF and fail early with a clear, user-facing message."""
    import pymupdf

    if not os.path.isfile(path):
        raise PDFInputError(f"File not found: {path}")
    if os.path.getsize(path) == 0:
        raise PDFInputError(f"'{os.path.basename(path)}' contains no data.")
        
    try:
        doc = pymupdf.open(path)
    except Exception as e:
        raise PDFInputError(f"Could not open '{os.path.basename(path)}': {e}")
        
    if doc.needs_pass:
        doc.close()
        raise PDFInputError(f"'{os.path.basename(path)}' is password protected. Remove the password first.")
    if len(doc) == 0:
        doc.close()
        raise PDFInputError(f"'{os.path.basename(path)}' contains no pages.")
    return doc


class PDFEngine:
    """Core backend engine optimized for high-throughput batch document processing."""

    @staticmethod
    def combine_files(
        file_items: List[FileItem],
        output_path: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> str:
        """
        Combines multiple PDF files and images in sequential order into a single PDF.
        Optimized with PyMuPDF for lightning-fast multi-file merging.
        """
        total_items = len(file_items)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Check NLP engine status
        try:
            from PyQt6.QtCore import QSettings
            from core.nlp_engine import NLPEngine
            settings = QSettings("MNIME", "MNIMEApp")
            use_nlp = str(settings.value("nlp_smart_indexing", "true")).lower() == "true"
            nlp_engine = NLPEngine.get_instance()
            if use_nlp:
                nlp_engine.check_model()
            is_nlp_active = use_nlp and nlp_engine.is_loaded
        except Exception:
            is_nlp_active = False
            nlp_engine = None

        # 1. Primary High-Speed Engine: PyMuPDF
        try:
            import pymupdf
            import tempfile

            BATCH_SIZE = 250
            toc_entries = []
            current_page_count = 1

            if total_items <= BATCH_SIZE:
                merged_doc = pymupdf.open()
                for idx, item in enumerate(file_items):
                    if progress_callback:
                        pct = int((idx / total_items) * 90)
                        progress_callback(pct, f"Merging {item.file_name} ({idx + 1}/{total_items})...")

                    start_page = len(merged_doc) + 1
                    ext = item.extension.lower()
                    if ext == ".pdf":
                        sub_doc = open_pdf_checked(item.file_path)
                        bm_title = item.file_name
                        if is_nlp_active:
                            try:
                                first_page_txt = sub_doc[0].get_text("text").strip() if len(sub_doc) > 0 else ""
                                smart_t = nlp_engine.generate_smart_filename(first_page_txt, item.file_name)
                                if smart_t and smart_t != item.file_name:
                                    bm_title = f"{item.file_name} ({smart_t})"
                            except Exception:
                                pass
                        toc_entries.append([1, bm_title, start_page])
                        merged_doc.insert_pdf(sub_doc)
                        sub_doc.close()
                    elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
                        img_doc = pymupdf.open(item.file_path)
                        pdf_bytes = img_doc.convert_to_pdf()
                        img_pdf = pymupdf.open("pdf", pdf_bytes)
                        toc_entries.append([1, item.file_name, start_page])
                        merged_doc.insert_pdf(img_pdf)
                        img_pdf.close()
                        img_doc.close()
                    elif ext == ".txt":
                        try:
                            with open(item.file_path, "r", encoding="utf-8") as f:
                                text_content = f.read()
                        except UnicodeDecodeError:
                            with open(item.file_path, "r", encoding="latin-1", errors="replace") as f:
                                text_content = f.read()

                        txt_pdf = pymupdf.open()
                        lines = text_content.splitlines() or [""]
                        lines_per_page = 45
                        for chunk_start in range(0, len(lines), lines_per_page):
                            page = txt_pdf.new_page()
                            rect = pymupdf.Rect(50, 50, page.rect.width - 50, page.rect.height - 50)
                            chunk_text = "\n".join(lines[chunk_start:chunk_start + lines_per_page])
                            page.insert_textbox(rect, chunk_text, fontsize=11, fontname="helv")
                        
                        toc_entries.append([1, item.file_name, start_page])
                        merged_doc.insert_pdf(txt_pdf)
                        txt_pdf.close()

                if toc_entries:
                    try:
                        merged_doc.set_toc(toc_entries)
                    except Exception:
                        pass

                if progress_callback:
                    progress_callback(95, "Compacting and saving document...")

                merged_doc.save(output_path, garbage=3, deflate=True)
                merged_doc.close()

            else:
                # High-Volume Batch Processing (prevents RAM/handle exhaustion on 1000s of files)
                temp_chunks = []
                with tempfile.TemporaryDirectory(prefix="mnime_merge_batch_") as tmp_dir:
                    for batch_start in range(0, total_items, BATCH_SIZE):
                        batch_items = file_items[batch_start:batch_start + BATCH_SIZE]
                        chunk_doc = pymupdf.open()

                        for idx_in_batch, item in enumerate(batch_items):
                            global_idx = batch_start + idx_in_batch
                            if progress_callback:
                                pct = int((global_idx / total_items) * 85)
                                progress_callback(pct, f"Merging {item.file_name} ({global_idx + 1}/{total_items})...")

                            ext = item.extension.lower()
                            if ext == ".pdf":
                                sub_doc = open_pdf_checked(item.file_path)
                                bm_title = item.file_name
                                if is_nlp_active:
                                    try:
                                        first_page_txt = sub_doc[0].get_text("text").strip() if len(sub_doc) > 0 else ""
                                        smart_t = nlp_engine.generate_smart_filename(first_page_txt, item.file_name)
                                        if smart_t and smart_t != item.file_name:
                                            bm_title = f"{item.file_name} ({smart_t})"
                                    except Exception:
                                        pass
                                toc_entries.append([1, bm_title, current_page_count])
                                current_page_count += len(sub_doc)
                                chunk_doc.insert_pdf(sub_doc)
                                sub_doc.close()
                            elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
                                img_doc = pymupdf.open(item.file_path)
                                pdf_bytes = img_doc.convert_to_pdf()
                                img_pdf = pymupdf.open("pdf", pdf_bytes)
                                toc_entries.append([1, item.file_name, current_page_count])
                                current_page_count += len(img_pdf)
                                chunk_doc.insert_pdf(img_pdf)
                                img_pdf.close()
                                img_doc.close()
                            elif ext == ".txt":
                                try:
                                    with open(item.file_path, "r", encoding="utf-8") as f:
                                        text_content = f.read()
                                except UnicodeDecodeError:
                                    with open(item.file_path, "r", encoding="latin-1", errors="replace") as f:
                                        text_content = f.read()

                                txt_pdf = pymupdf.open()
                                lines = text_content.splitlines() or [""]
                                lines_per_page = 45
                                for chunk_start_line in range(0, len(lines), lines_per_page):
                                    page = txt_pdf.new_page()
                                    rect = pymupdf.Rect(50, 50, page.rect.width - 50, page.rect.height - 50)
                                    chunk_text = "\n".join(lines[chunk_start_line:chunk_start_line + lines_per_page])
                                    page.insert_textbox(rect, chunk_text, fontsize=11, fontname="helv")
                                
                                toc_entries.append([1, item.file_name, current_page_count])
                                current_page_count += len(txt_pdf)
                                chunk_doc.insert_pdf(txt_pdf)
                                txt_pdf.close()

                        chunk_path = os.path.join(tmp_dir, f"chunk_{batch_start // BATCH_SIZE}.pdf")
                        chunk_doc.save(chunk_path, garbage=3, deflate=True)
                        chunk_doc.close()
                        temp_chunks.append(chunk_path)

                    # Final Assembly Pass using incremental save to avoid RAM exhaustion
                    import shutil
                    if not temp_chunks:
                        raise RuntimeError("No chunks generated.")
                        
                    shutil.copy(temp_chunks[0], output_path)
                    
                    for c_idx, c_path in enumerate(temp_chunks[1:]):
                        if progress_callback:
                            pct = 85 + int(((c_idx + 1) / len(temp_chunks)) * 10)
                            progress_callback(pct, f"Assembling batch segment {c_idx + 2}/{len(temp_chunks)}...")
                        
                        final_doc = pymupdf.open(output_path)
                        c_doc = pymupdf.open(c_path)
                        final_doc.insert_pdf(c_doc)
                        final_doc.saveIncr()
                        c_doc.close()
                        final_doc.close()

                    if toc_entries:
                        try:
                            final_doc = pymupdf.open(output_path)
                            final_doc.set_toc(toc_entries)
                            final_doc.saveIncr()
                            final_doc.close()
                        except Exception:
                            pass

                    if progress_callback:
                        progress_callback(98, "Saving final merged document...")

            if progress_callback:
                progress_callback(100, f"Finished! Merged {total_items} files.")

            return output_path

        except PDFInputError:
            raise  # Clear user-facing problem (e.g. encrypted PDF); a fallback engine cannot fix it
        except Exception:
            log.exception("PyMuPDF merge failed; falling back to pypdf/Pillow")
            # 2. Fallback Engine: pypdf & Pillow
            import pypdf
            from PIL import Image

            writer = pypdf.PdfWriter()
            for idx, item in enumerate(file_items):
                if progress_callback:
                    pct = int((idx / total_items) * 90)
                    progress_callback(pct, f"Processing {item.file_name} (fallback)...")

                ext = item.extension.lower()
                if ext == ".pdf":
                    reader = pypdf.PdfReader(item.file_path)
                    for page in reader.pages:
                        writer.add_page(page)
                elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
                    with Image.open(item.file_path) as img:
                        img_rgb = img.convert("RGB")
                        temp_pdf_bytes = io.BytesIO()
                        img_rgb.save(temp_pdf_bytes, format="PDF", resolution=150.0)
                        temp_pdf_bytes.seek(0)
                        img_reader = pypdf.PdfReader(temp_pdf_bytes)
                        for page in img_reader.pages:
                            writer.add_page(page)
                elif ext == ".txt":
                    try:
                        with open(item.file_path, "r", encoding="utf-8") as f:
                            text_content = f.read()
                    except UnicodeDecodeError:
                        with open(item.file_path, "r", encoding="latin-1", errors="replace") as f:
                            text_content = f.read()

                    from PIL import Image, ImageDraw
                    lines = text_content.splitlines()
                    if not lines:
                        lines = [""]
                    lines_per_page = 45
                    for chunk_start in range(0, len(lines), lines_per_page):
                        img = Image.new('RGB', (850, 1100), color=(255, 255, 255))
                        d = ImageDraw.Draw(img)
                        chunk_text = "\n".join(lines[chunk_start:chunk_start + lines_per_page])
                        d.text((50, 50), chunk_text, fill=(0, 0, 0))

                        temp_pdf_bytes = io.BytesIO()
                        img.save(temp_pdf_bytes, format="PDF", resolution=150.0)
                        temp_pdf_bytes.seek(0)
                        txt_reader = pypdf.PdfReader(temp_pdf_bytes)
                        for page in txt_reader.pages:
                            writer.add_page(page)

            if progress_callback:
                progress_callback(95, "Writing output file...")

            with open(output_path, "wb") as f_out:
                writer.write(f_out)

            if progress_callback:
                progress_callback(100, f"Finished! Merged {total_items} files.")

            return output_path

    @staticmethod
    def convert_jpg_to_pdf(
        image_items: List[FileItem],
        output_path: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> str:
        """
        Converts one or multiple images into a single clean PDF document.
        """
        if not image_items:
            raise ValueError("No images provided for conversion.")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        total = len(image_items)

        # 1. Primary Engine: PyMuPDF
        try:
            import pymupdf

            def convert_image(item):
                try:
                    img_doc = pymupdf.open(item.file_path)
                    pdf_bytes = img_doc.convert_to_pdf()
                    img_doc.close()
                    return pdf_bytes
                except Exception:
                    return None

            # NOTE: MuPDF is not thread-safe; convert sequentially.
            pdf_bytes_list = []
            for idx, item in enumerate(image_items):
                pdf_bytes_list.append(convert_image(item))
                if progress_callback:
                    pct = int(((idx + 1) / total) * 80)
                    progress_callback(pct, f"Converted {idx + 1}/{total} images...")

            pdf_doc = pymupdf.open()
            open_docs = []
            
            for b in pdf_bytes_list:
                if b:
                    img_pdf = pymupdf.open("pdf", b)
                    pdf_doc.insert_pdf(img_pdf)
                    open_docs.append(img_pdf)

            if progress_callback:
                progress_callback(95, "Optimizing PDF output...")

            pdf_doc.save(output_path, garbage=3, deflate=True)
            pdf_doc.close()

            for d in open_docs:
                d.close()

            if progress_callback:
                progress_callback(100, "Done!")

            return output_path

        except Exception:
            # 2. Fallback Engine: Pillow
            from PIL import Image

            images = []
            for i, item in enumerate(image_items):
                if progress_callback:
                    progress_callback(int((i / total) * 80), f"Loading {item.file_name}...")
                img = Image.open(item.file_path).convert("RGB")
                images.append(img)

            first_img = images[0]
            remaining = images[1:] if len(images) > 1 else []

            if progress_callback:
                progress_callback(90, "Saving PDF...")

            first_img.save(
                output_path,
                "PDF",
                resolution=150.0,
                save_all=True,
                append_images=remaining,
            )

            for img in images:
                img.close()

            if progress_callback:
                progress_callback(100, "Done!")

            return output_path

    @staticmethod
    def split_pdf(
        pdf_item: FileItem,
        output_dir: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> List[str]:
        """
        Splits a PDF into individual 1-page PDF files.
        """
        output_files: List[str] = []
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(pdf_item.file_name)[0]

        try:
            import pymupdf
            from PyQt6.QtCore import QSettings
            from core.nlp_engine import NLPEngine

            settings = QSettings("MNIME", "MNIMEApp")
            use_nlp = str(settings.value("nlp_smart_indexing", "true")).lower() == "true"
            nlp_engine = NLPEngine.get_instance()
            if use_nlp:
                nlp_engine.check_model()
            is_nlp_active = use_nlp and nlp_engine.is_loaded

            failed_pages: List[int] = []
            # NOTE: MuPDF is not thread-safe; split sequentially.
            local_doc = open_pdf_checked(pdf_item.file_path)
            try:
                total_pages = len(local_doc)
                for page_num in range(total_pages):
                    try:
                        page = local_doc[page_num]
                        fallback_name = f"{base_name}_page_{page_num + 1:03d}"
                        final_name = fallback_name

                        if is_nlp_active:
                            page_text = page.get_text("text").strip()
                            smart_name = nlp_engine.generate_smart_filename(page_text, fallback_name)
                            # Append page number to guarantee uniqueness
                            if smart_name != fallback_name:
                                final_name = f"{safe_filename(smart_name)}_p{page_num + 1:03d}"

                        new_doc = pymupdf.open()
                        try:
                            new_doc.insert_pdf(local_doc, from_page=page_num, to_page=page_num)
                            out_path = os.path.join(output_dir, f"{final_name}.pdf")
                            new_doc.save(out_path, garbage=3, deflate=True)
                        finally:
                            new_doc.close()
                        output_files.append(out_path)
                    except Exception:
                        log.exception("Error splitting page %d of %s", page_num + 1, pdf_item.file_path)
                        failed_pages.append(page_num + 1)
                    if progress_callback:
                        pct = int(((page_num + 1) / total_pages) * 95)
                        progress_callback(pct, f"Split {page_num + 1}/{total_pages} pages...")
            finally:
                local_doc.close()

            if not output_files:
                raise RuntimeError("No pages could be written.")
            output_files.sort()

            if progress_callback:
                msg = f"Saved {len(output_files)} pages."
                if failed_pages:
                    msg += f" Skipped pages: {', '.join(map(str, failed_pages))}."
                progress_callback(100, msg)

            return output_files

        except PDFInputError:
            raise
        except Exception as e:
            raise RuntimeError(f"Error splitting PDF: {e}") from e

    @staticmethod
    def convert_pdf_to_jpg(
        pdf_item: FileItem,
        output_dir: str,
        dpi: int = 200,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> List[str]:
        """
        Converts pages of a PDF document into individual high-resolution JPG images.
        """
        output_files: List[str] = []
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(pdf_item.file_name)[0]
        dpi = max(36, min(int(dpi), 2400))  # Bound memory use

        try:
            import pymupdf

            # NOTE: MuPDF is not thread-safe; render sequentially to avoid blank pages.
            zoom = dpi / 72.0
            matrix = pymupdf.Matrix(zoom, zoom)
            render_doc = open_pdf_checked(pdf_item.file_path)
            try:
                total_pages = len(render_doc)
                for page_num in range(total_pages):
                    page = render_doc[page_num]
                    rect = page.rect
                    current_zoom = zoom
                    max_dim = 32768
                    if rect.width * current_zoom > max_dim:
                        current_zoom = max_dim / rect.width
                    if rect.height * current_zoom > max_dim:
                        current_zoom = min(current_zoom, max_dim / rect.height)
                    matrix = pymupdf.Matrix(current_zoom, current_zoom)
                    
                    pix = page.get_pixmap(
                        matrix=matrix, colorspace=pymupdf.csRGB, alpha=False
                    )
                    out_path = os.path.join(output_dir, f"{base_name}_page_{page_num + 1:03d}.jpg")
                    pix.save(out_path)
                    output_files.append(out_path)
                    if progress_callback:
                        pct = int(((page_num + 1) / total_pages) * 95)
                        progress_callback(pct, f"Rendered {page_num + 1}/{total_pages} pages...")
            finally:
                render_doc.close()

            output_files.sort()

        except PDFInputError:
            raise
        except Exception as e:
            raise RuntimeError(f"Error rendering PDF to images: {e}") from e

        if progress_callback:
            progress_callback(100, f"Saved {len(output_files)} images.")

        return output_files

    @staticmethod
    def compress_pdf(
        pdf_item: FileItem,
        output_path: str,
        compression_level: str = "medium",
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> str:
        """
        Compresses a PDF using PyMuPDF stream deflation, xref compaction,
        and duplicate object elimination.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        try:
            import pymupdf

            if progress_callback:
                progress_callback(20, "Analyzing PDF structure for compression...")

            doc = pymupdf.open(pdf_item.file_path)

            if progress_callback:
                progress_callback(60, "Deflating streams & compacting objects...")

            doc.save(output_path, garbage=4, deflate=True, clean=True)
            doc.close()

            if progress_callback:
                progress_callback(100, "Compression complete!")

            return output_path

        except Exception:
            # Fallback to pypdf
            import pypdf

            if progress_callback:
                progress_callback(10, "Opening PDF for compression...")

            reader = pypdf.PdfReader(pdf_item.file_path)
            writer = pypdf.PdfWriter()

            total_pages = len(reader.pages)
            for i, page in enumerate(reader.pages):
                if progress_callback:
                    pct = 10 + int((i / total_pages) * 70)
                    progress_callback(pct, f"Compressing page {i + 1} of {total_pages}...")

                page.compress_content_streams()
                writer.add_page(page)

            if progress_callback:
                progress_callback(85, "Optimizing and saving compressed file...")

            with open(output_path, "wb") as f_out:
                writer.write(f_out)

            if progress_callback:
                progress_callback(100, "Compression complete!")

            return output_path

    @staticmethod
    def convert_pdf_to_docx(
        pdf_item: FileItem,
        output_path: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> str:
        """
        Converts a PDF file to a Microsoft Word (.docx) document.
        """
        try:
            from pdf2docx import Converter

            if progress_callback:
                progress_callback(10, "Initializing PDF to DOCX converter...")

            cv = Converter(pdf_item.file_path)
            if progress_callback:
                progress_callback(40, "Parsing layout and extracting content...")

            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            cv.convert(output_path, start=0, end=None)
            cv.close()

            if progress_callback:
                progress_callback(100, "Word document generated successfully!")

            return output_path

        except ImportError:
            try:
                import pypdf
                from docx import Document

                if progress_callback:
                    progress_callback(20, "Extracting text with pypdf...")

                reader = pypdf.PdfReader(pdf_item.file_path)
                doc = Document()
                doc.add_heading(os.path.splitext(pdf_item.file_name)[0], 0)

                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        doc.add_paragraph(text)
                    doc.add_page_break()

                doc.save(output_path)
                if progress_callback:
                    progress_callback(100, "Document saved (text extracted).")
                return output_path

            except Exception as e:
                raise RuntimeError(
                    f"Please install pdf2docx (`pip install pdf2docx`) for full formatting fidelity: {e}"
                )

    @staticmethod
    def bookmark(
        pdf_item: FileItem,
        output_path: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> str:
        """
        Automatically adds bookmarks to a PDF by extracting the most prominent text
        (e.g., largest font size) from each page to use as a section header.
        """
        try:
            import pymupdf
            from PyQt6.QtCore import QSettings
            from core.nlp_engine import NLPEngine
            
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            settings = QSettings("MNIME", "MNIMEApp")
            use_nlp = str(settings.value("nlp_smart_indexing", "true")).lower() == "true"
            nlp_engine = NLPEngine.get_instance()
            if use_nlp:
                nlp_engine.check_model()
            is_nlp_active = use_nlp and nlp_engine.is_loaded

            if progress_callback:
                progress_callback(5, "Opening PDF for analysis...")

            doc = pymupdf.open(pdf_item.file_path)
            toc = []

            total_pages = len(doc)
            
            # Step 1: Sample the first few pages to find the most common (base) font size
            import re
            from collections import Counter
            font_sizes = Counter()
            sample_pages = min(10, total_pages)
            for i in range(sample_pages):
                blocks = doc[i].get_text("dict").get("blocks", [])
                for b in blocks:
                    if b.get("type") == 0:
                        for l in b.get("lines", []):
                            for s in l.get("spans", []):
                                text = s.get("text", "").strip()
                                size = round(s.get("size", 0), 1)
                                if text and size > 0:
                                    font_sizes[size] += len(text)
                                    
            base_size = 10.0
            if font_sizes:
                # The font size with the most characters is likely the body text
                base_size = font_sizes.most_common(1)[0][0]

            # Regex for explicit chapter/section markers
            chapter_pattern = re.compile(r"^(chapter|part|section|appendix|unit|module)\s+([a-z0-9\.\-]+)", re.IGNORECASE)

            all_largest_texts = []

            for i in range(total_pages):
                if progress_callback:
                    pct = 10 + int((i / total_pages) * 70)
                    progress_callback(pct, f"Analyzing page {i+1}/{total_pages}...")

                page = doc[i]
                blocks = page.get_text("dict").get("blocks", [])

                largest_size = -1
                best_text = ""
                has_explicit_chapter = False
                page_largest_text = f"Page {i+1}"
                page_absolute_largest_size = -1

                for b in blocks:
                    if b.get("type") == 0:  # Text block
                        for l in b.get("lines", []):
                            for s in l.get("spans", []):
                                text = s.get("text", "").strip()
                                size = s.get("size", 0)
                                flags = s.get("flags", 0)
                                is_bold = bool(flags & 16) # Bit 4 is bold in PyMuPDF
                                
                                if not text or len(text) > 100:
                                    continue
                                    
                                # Track absolute largest text for fallback
                                if size > page_absolute_largest_size:
                                    page_absolute_largest_size = size
                                    page_largest_text = text
                                    
                                # Rule 1: Explicit match
                                if chapter_pattern.match(text):
                                    best_text = text
                                    has_explicit_chapter = True
                                    break
                                    
                                # Rule 2: Largest text on page, and significantly larger than body text
                                # Or slightly larger and Bold
                                if size > largest_size and (size >= (base_size * 1.15) or (is_bold and size >= base_size * 1.05)):
                                    largest_size = size
                                    best_text = text
                            
                            if has_explicit_chapter:
                                break
                    if has_explicit_chapter:
                        break

                all_largest_texts.append(page_largest_text)

                # Only add a bookmark if we confidently found a heading
                if best_text:
                    if is_nlp_active:
                        if progress_callback:
                            progress_callback(pct, f"NLP summarizing page {i+1}/{total_pages}...")
                        page_text = page.get_text("text").strip()
                        best_text = nlp_engine.generate_verbose_bookmark(best_text, page_text)
                        
                    toc.append([1, best_text, i + 1])
                    
            if not toc:
                # Fallback: if heuristics failed completely (e.g. plain text or images only),
                # just bookmark every page using the largest text found
                for i, text in enumerate(all_largest_texts):
                    toc.append([1, text, i + 1])
                
                # Explicitly yield GIL to prevent main thread cursor animations from lagging
                import time
                time.sleep(0.005)

            if progress_callback:
                progress_callback(85, "Generating Table of Contents...")

            doc.set_toc(toc)

            if progress_callback:
                progress_callback(90, "Saving bookmarked PDF...")

            doc.save(output_path, garbage=3, deflate=True)
            doc.close()

            if progress_callback:
                progress_callback(100, "Done! Bookmarks added.")

            return output_path

        except Exception as e:
            raise RuntimeError(f"Error bookmarking PDF: {e}")
