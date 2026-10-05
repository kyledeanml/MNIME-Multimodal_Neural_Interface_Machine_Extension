"""
Generates high-resolution PNG cover preview images for the MNIME Research Paper.
Compiles via pdflatex, distills/normalizes to robust PDF 1.4, and renders Page 1
at 300 DPI to docs/paper_cover.png and docs/paper_cover_v5.png.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_ghostscript() -> str | None:
    """Find Ghostscript executable (mgs.exe in MiKTeX, gswin64c, or gs)."""
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64" / "mgs.exe",
        shutil.which("mgs"),
        shutil.which("gswin64c"),
        shutil.which("gswin32c"),
        shutil.which("gs")
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return str(c)
    return None


def distill_pdf_14(input_pdf: Path, output_pdf: Path) -> bool:
    """Distill PDF to standard PDF 1.4 with full link preservation and clean xref."""
    gs_exe = find_ghostscript()
    if not gs_exe:
        print("Note: Ghostscript not found. Using raw pdflatex output.")
        if input_pdf != output_pdf:
            shutil.copy2(input_pdf, output_pdf)
        return True

    temp_out = input_pdf.parent / (input_pdf.stem + "_distilled.tmp.pdf")
    cmd = [
        gs_exe,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-dPDFSETTINGS=/prepress",
        "-dPrinted=false",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={temp_out}",
        str(input_pdf)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if temp_out.exists() and temp_out.stat().st_size > 1000:
            shutil.move(str(temp_out), str(output_pdf))
            print(f"Successfully distilled {output_pdf.name} to standard PDF 1.4 ({output_pdf.stat().st_size:,} bytes).")
            return True
    except Exception as err:
        print(f"Warning: Ghostscript distillation failed ({err}); retaining raw PDF.")
    finally:
        if temp_out.exists():
            temp_out.unlink(missing_ok=True)
    return False


def render_paper_cover(root_dir: Path):
    paper_dir = root_dir / "paper"
    tex_path = paper_dir / "MNIME_Whitepaper.tex"
    pdf_in_paper = paper_dir / "MNIME_Whitepaper.pdf"
    pdf_in_root = root_dir / "MNIME_Whitepaper.pdf"
    cover_png = root_dir / "docs" / "paper_cover.png"
    cover_png_v5 = root_dir / "docs" / "paper_cover_v5.png"

    # If tex is newer than pdf or user specifies --compile, compile via pdflatex
    should_compile = "--compile" in sys.argv or not pdf_in_paper.exists()
    if should_compile and tex_path.exists():
        print(f"Compiling {tex_path.name} via pdflatex...")
        try:
            for pass_num in (1, 2):
                subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", tex_path.name],
                    cwd=str(paper_dir),
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            print("LaTeX compilation finished successfully (2 passes).")
            # Distill to standard PDF 1.4 for universal viewer compatibility
            distill_pdf_14(pdf_in_paper, pdf_in_paper)
        except Exception as err:
            print(f"LaTeX compilation warning: {err}")

    # Synchronize root PDF if paper/ PDF exists and is newer
    if pdf_in_paper.exists():
        shutil.copy2(pdf_in_paper, pdf_in_root)
        print(f"Synchronized {pdf_in_paper} -> {pdf_in_root}")
    elif pdf_in_root.exists():
        shutil.copy2(pdf_in_root, pdf_in_paper)
        print(f"Synchronized {pdf_in_root} -> {pdf_in_paper}")

    target_pdf = pdf_in_root if pdf_in_root.exists() else pdf_in_paper
    if not target_pdf.exists():
        print(f"ERROR: Cannot find MNIME_Whitepaper.pdf in {root_dir} or {paper_dir}")
        return False

    import pymupdf
    print(f"Opening {target_pdf.name} for cover rasterization...")
    doc = pymupdf.open(str(target_pdf))
    if len(doc) == 0:
        print("ERROR: Document contains no pages.")
        doc.close()
        return False

    page = doc[0]
    # Render at 300 DPI (zoom = 300 / 72 ≈ 4.166667)
    zoom = 300.0 / 72.0
    mat = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)

    cover_png.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(cover_png))
    pix.save(str(cover_png_v5))
    doc.close()

    # Clean up LaTeX auxiliary build files to keep the paper directory clean
    for ext in ("aux", "log", "out", "bbl", "blg", "tmp", "toc"):
        for f in paper_dir.glob(f"*.{ext}"):
            try:
                f.unlink()
            except OSError:
                pass

    print(f"Cover preview successfully generated: {pix.width}x{pix.height}px")
    print(f"  - {cover_png} ({cover_png.stat().st_size:,} bytes)")
    print(f"  - {cover_png_v5} ({cover_png_v5.stat().st_size:,} bytes)")
    return True


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    success = render_paper_cover(project_root)
    sys.exit(0 if success else 1)
