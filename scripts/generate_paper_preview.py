"""
Generates high-resolution PNG cover preview images for the MNIME Research Paper.
Renders Page 1 of MNIME_Research_Paper.pdf at 300 DPI to docs/paper_cover.png and docs/paper_cover_v5.png.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def render_paper_cover(root_dir: Path):
    paper_dir = root_dir / "paper"
    tex_path = paper_dir / "MNIME_Research_Paper.tex"
    pdf_in_paper = paper_dir / "MNIME_Research_Paper.pdf"
    pdf_in_root = root_dir / "MNIME_Research_Paper.pdf"
    cover_png = root_dir / "docs" / "paper_cover.png"
    cover_png_v5 = root_dir / "docs" / "paper_cover_v5.png"

    # If tex is newer than pdf or user specifies --compile, compile via pdflatex
    should_compile = "--compile" in sys.argv
    if should_compile and tex_path.exists():
        print(f"Compiling {tex_path.name} via pdflatex...")
        try:
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", tex_path.name],
                cwd=str(paper_dir),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print("LaTeX compilation finished successfully.")
        except Exception as err:
            print(f"LaTeX compilation warning: {err}")

    # Synchronize root PDF if paper/ PDF exists and is newer
    if pdf_in_paper.exists():
        if not pdf_in_root.exists() or pdf_in_paper.stat().st_mtime >= pdf_in_root.stat().st_mtime:
            shutil.copy2(pdf_in_paper, pdf_in_root)
            print(f"Synchronized {pdf_in_paper} -> {pdf_in_root}")
    elif pdf_in_root.exists():
        shutil.copy2(pdf_in_root, pdf_in_paper)
        print(f"Synchronized {pdf_in_root} -> {pdf_in_paper}")

    target_pdf = pdf_in_root if pdf_in_root.exists() else pdf_in_paper
    if not target_pdf.exists():
        print(f"ERROR: Cannot find MNIME_Research_Paper.pdf in {root_dir} or {paper_dir}")
        return False

    import pymupdf
    print(f"Opening {target_pdf.name} for cover rasterization and sanitization...")
    doc = pymupdf.open(str(target_pdf))
    if len(doc) == 0:
        print("ERROR: Document contains no pages.")
        doc.close()
        return False

    # Sanitize and optimize the PDF to prevent GitHub's pdf.js "Invalid PDF" errors
    temp_pdf = target_pdf.with_name(target_pdf.name + ".tmp")
    doc.save(str(temp_pdf), garbage=4, deflate=True)

    page = doc[0]
    # Render at 300 DPI (zoom = 300 / 72 ≈ 4.166667)
    zoom = 300.0 / 72.0
    mat = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)

    cover_png.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(cover_png))
    pix.save(str(cover_png_v5))
    doc.close()

    # Replace original PDF with the sanitized version
    shutil.move(str(temp_pdf), str(target_pdf))
    
    # Also sync the sanitized version back to the paper directory if needed
    if target_pdf == pdf_in_root and pdf_in_paper.exists():
        shutil.copy2(pdf_in_root, pdf_in_paper)
    elif target_pdf == pdf_in_paper and pdf_in_root.exists():
        shutil.copy2(pdf_in_paper, pdf_in_root)

    print(f"Cover preview successfully generated: {pix.width}x{pix.height}px")
    print(f"  - {cover_png} ({cover_png.stat().st_size:,} bytes)")
    print(f"  - {cover_png_v5} ({cover_png_v5.stat().st_size:,} bytes)")
    return True


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    success = render_paper_cover(project_root)
    sys.exit(0 if success else 1)
