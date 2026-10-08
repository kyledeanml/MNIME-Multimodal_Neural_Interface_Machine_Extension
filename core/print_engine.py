"""
MNIME Print Engine - native Windows GDI printing (no Qt print pipeline, no external viewer).

Pages are rasterised with PyMuPDF/Pillow at up to ``MAX_DPI`` and sent straight to the
selected printer through the Win32 print API (PrintDlgW + StartDoc/StretchDIBits).
"""

import ctypes
import os
from ctypes import wintypes
from typing import Callable, Optional, Tuple

MAX_DPI = 1200  # Upper bound for the raster resolution sent to the printer
MAX_RASTER_PIXELS = 240_000_000  # Hard memory cap per page raster (~960 MB as BGRA)


class PrintCancelled(Exception):
    """Raised when the user dismisses the print dialog."""


class PrintError(RuntimeError):
    """Raised when the Windows print API reports a failure."""


# ---------------------------------------------------------------------------
# Win32 structures / prototypes
# ---------------------------------------------------------------------------

class PRINTDLGW(ctypes.Structure):
    _fields_ = [
        ("lStructSize", wintypes.DWORD),
        ("hwndOwner", wintypes.HWND),
        ("hDevMode", wintypes.HGLOBAL),
        ("hDevNames", wintypes.HGLOBAL),
        ("hDC", wintypes.HDC),
        ("Flags", wintypes.DWORD),
        ("nFromPage", wintypes.WORD),
        ("nToPage", wintypes.WORD),
        ("nMinPage", wintypes.WORD),
        ("nMaxPage", wintypes.WORD),
        ("nCopies", wintypes.WORD),
        ("hInstance", wintypes.HINSTANCE),
        ("lCustData", wintypes.LPARAM),
        ("lpfnPrintHook", ctypes.c_void_p),
        ("lpfnSetupHook", ctypes.c_void_p),
        ("lpPrintTemplateName", wintypes.LPCWSTR),
        ("lpSetupTemplateName", wintypes.LPCWSTR),
        ("hPrintTemplate", wintypes.HGLOBAL),
        ("hSetupTemplate", wintypes.HGLOBAL),
    ]


class DOCINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_int),
        ("lpszDocName", wintypes.LPCWSTR),
        ("lpszOutput", wintypes.LPCWSTR),
        ("lpszDatatype", wintypes.LPCWSTR),
        ("fwType", wintypes.DWORD),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


PD_PAGENUMS = 0x00000002
PD_NOSELECTION = 0x00000004
PD_RETURNDC = 0x00000100
PD_USEDEVMODECOPIESANDCOLLATE = 0x00040000
PD_NOCURRENTPAGE = 0x00800000

HORZRES, VERTRES, LOGPIXELSX, LOGPIXELSY = 8, 10, 88, 90
SRCCOPY = 0x00CC0020
HALFTONE = 4


def _load_apis():
    if os.name != "nt":
        raise PrintError("Native printing is only available on Windows.")
    comdlg32 = ctypes.WinDLL("comdlg32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    comdlg32.PrintDlgW.argtypes = [ctypes.POINTER(PRINTDLGW)]
    comdlg32.PrintDlgW.restype = wintypes.BOOL
    comdlg32.CommDlgExtendedError.restype = wintypes.DWORD

    gdi32.StartDocW.argtypes = [wintypes.HDC, ctypes.POINTER(DOCINFOW)]
    gdi32.StartDocW.restype = ctypes.c_int
    for name in ("StartPage", "EndPage", "EndDoc", "AbortDoc"):
        fn = getattr(gdi32, name)
        fn.argtypes = [wintypes.HDC]
        fn.restype = ctypes.c_int
    gdi32.GetDeviceCaps.argtypes = [wintypes.HDC, ctypes.c_int]
    gdi32.GetDeviceCaps.restype = ctypes.c_int
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    gdi32.DeleteDC.restype = wintypes.BOOL
    gdi32.SetStretchBltMode.argtypes = [wintypes.HDC, ctypes.c_int]
    gdi32.SetStretchBltMode.restype = ctypes.c_int
    gdi32.StretchDIBits.argtypes = [
        wintypes.HDC,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT, wintypes.DWORD,
    ]
    gdi32.StretchDIBits.restype = ctypes.c_int

    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.restype = wintypes.HGLOBAL
    return comdlg32, gdi32, kernel32


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_bgra(rgb) -> "numpy.ndarray":
    """Convert an (h, w, 3) RGB uint8 array to a contiguous (h, w, 4) BGRA array."""
    import numpy as np
    h, w = rgb.shape[:2]
    out = np.empty((h, w, 4), dtype=np.uint8)
    out[..., 0] = rgb[..., 2]
    out[..., 1] = rgb[..., 1]
    out[..., 2] = rgb[..., 0]
    out[..., 3] = 255
    return np.ascontiguousarray(out)


def _fit(src_w: float, src_h: float, box_w: int, box_h: int, allow_upscale: bool) -> Tuple[int, int]:
    scale = min(box_w / src_w, box_h / src_h)
    if not allow_upscale:
        scale = min(scale, 1.0)
    return max(int(src_w * scale), 1), max(int(src_h * scale), 1)


# ---------------------------------------------------------------------------
# Core job runner
# ---------------------------------------------------------------------------

# render(index, area_w, area_h, dpi_x, dpi_y) -> (bgra_array, dest_x, dest_y, dest_w, dest_h)
RenderFn = Callable[[int, int, int, int, int], Tuple["numpy.ndarray", int, int, int, int]]


def _run_job(hwnd: int, title: str, page_count: int, render: RenderFn,
             progress: Optional[Callable[[int, int], None]] = None,
             on_start: Optional[Callable[[], None]] = None) -> int:
    comdlg32, gdi32, kernel32 = _load_apis()

    dlg = PRINTDLGW()
    dlg.lStructSize = ctypes.sizeof(PRINTDLGW)
    dlg.hwndOwner = hwnd or None
    dlg.Flags = (PD_RETURNDC | PD_NOSELECTION | PD_NOCURRENTPAGE
                 | PD_USEDEVMODECOPIESANDCOLLATE)
    dlg.nMinPage = 1
    dlg.nMaxPage = max(1, min(page_count, 65535))
    dlg.nFromPage = 1
    dlg.nToPage = dlg.nMaxPage
    dlg.nCopies = 1

    if not comdlg32.PrintDlgW(ctypes.byref(dlg)):
        err = comdlg32.CommDlgExtendedError()
        if err == 0:
            raise PrintCancelled()
        raise PrintError(f"Print dialog failed (error 0x{err:04X}).")

    hdc = dlg.hDC
    started = False
    try:
        if not hdc:
            raise PrintError("The selected printer did not return a device context.")

        first, last = 0, page_count - 1
        if dlg.Flags & PD_PAGENUMS:
            first = max(0, dlg.nFromPage - 1)
            last = min(page_count - 1, dlg.nToPage - 1)

        area_w = gdi32.GetDeviceCaps(hdc, HORZRES)
        area_h = gdi32.GetDeviceCaps(hdc, VERTRES)
        dpi_x = gdi32.GetDeviceCaps(hdc, LOGPIXELSX) or 300
        dpi_y = gdi32.GetDeviceCaps(hdc, LOGPIXELSY) or 300

        info = DOCINFOW()
        info.cbSize = ctypes.sizeof(DOCINFOW)
        info.lpszDocName = title or "MNIME Document"
        if gdi32.StartDocW(hdc, ctypes.byref(info)) <= 0:
            raise PrintError(f"StartDoc failed (error {ctypes.get_last_error()}).")
        started = True
        gdi32.SetStretchBltMode(hdc, HALFTONE)

        printed = 0
        total = last - first + 1
        for idx in range(first, last + 1):
            bgra, dx, dy, dw, dh = render(idx, area_w, area_h, dpi_x, dpi_y)
            h, w = bgra.shape[:2]

            bmi = BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth = w
            bmi.biHeight = -h  # top-down
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0  # BI_RGB

            if gdi32.StartPage(hdc) <= 0:
                raise PrintError("StartPage failed.")
            rc = gdi32.StretchDIBits(
                hdc, dx, dy, dw, dh, 0, 0, w, h,
                bgra.ctypes.data, ctypes.byref(bmi), 0, SRCCOPY,
            )
            if rc == 0 or rc == -1:  # GDI_ERROR
                gdi32.EndPage(hdc)
                raise PrintError("The printer driver rejected the page bitmap.")
            if gdi32.EndPage(hdc) <= 0:
                raise PrintError("EndPage failed.")
            printed += 1
            if progress:
                progress(printed, total)

        gdi32.EndDoc(hdc)
        started = False
        return printed
    except BaseException:
        if started:
            gdi32.AbortDoc(hdc)
        raise
    finally:
        if hdc:
            gdi32.DeleteDC(hdc)
        if dlg.hDevMode:
            kernel32.GlobalFree(dlg.hDevMode)
        if dlg.hDevNames:
            kernel32.GlobalFree(dlg.hDevNames)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def print_pdf(hwnd: int, doc, title: str = "", progress=None) -> int:
    """Print an open PyMuPDF document. Returns the number of pages printed."""
    import numpy as np
    import pymupdf

    def render(i, area_w, area_h, dpi_x, dpi_y):
        page = doc[i]
        rect = page.rect
        pw_px = rect.width * dpi_x / 72.0
        ph_px = rect.height * dpi_y / 72.0

        rotate = (pw_px > ph_px) != (area_w > area_h)  # match paper orientation
        src_w, src_h = (ph_px, pw_px) if rotate else (pw_px, ph_px)
        dw, dh = _fit(src_w, src_h, area_w, area_h, allow_upscale=False)

        # Raster resolution: never above MAX_DPI
        cap = min(1.0, MAX_DPI / float(max(dpi_x, 1)))
        zoom = (dw * cap) / (rect.height if rotate else rect.width)
        mat = pymupdf.Matrix(zoom, zoom)
        if rotate:
            mat = mat.prerotate(90)
        pix = page.get_pixmap(matrix=mat, colorspace=pymupdf.csRGB, alpha=False)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.stride)
        rgb = arr[:, : pix.width * 3].reshape(pix.height, pix.width, 3)
        return _to_bgra(rgb), (area_w - dw) // 2, (area_h - dh) // 2, dw, dh

    return _run_job(hwnd, title, len(doc), render, progress)


def print_image(hwnd: int, path: str, title: str = "") -> int:
    """Print a single image file. Returns the number of pages printed."""
    import numpy as np
    from PIL import Image, ImageOps

    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA", "P"):
            rgba = im.convert("RGBA")
            base = Image.new("RGB", rgba.size, (255, 255, 255))
            base.paste(rgba, mask=rgba.split()[3])
            img = base
        else:
            img = im.convert("RGB")

    def render(i, area_w, area_h, dpi_x, dpi_y):
        pic = img
        if (pic.width > pic.height) != (area_w > area_h):
            pic = pic.rotate(90, expand=True)
        dw, dh = _fit(pic.width, pic.height, area_w, area_h, allow_upscale=True)
        # Downsample large images to at most the printer's native pixel size
        if pic.width > dw or pic.height > dh:
            pic = pic.resize((dw, dh), Image.LANCZOS)
        rgb = np.asarray(pic, dtype=np.uint8)
        return _to_bgra(rgb), (area_w - dw) // 2, (area_h - dh) // 2, dw, dh

    return _run_job(hwnd, title or os.path.basename(path), 1, render)
