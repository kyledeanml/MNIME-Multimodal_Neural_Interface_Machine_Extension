from PyQt6.QtGui import QPixmap, QImage
import pymupdf

MAX_PIXELS = 16_000_000

def render_page(page, view, dpr, extra_scale=1.0):
    """
    Renders a PyMuPDF page optimally based on the current graphics view's transform.
    Clips rendering to only the visible viewport if pixel count is high to save RAM.
    """
    # Combine the view transform scale with any extra scale (e.g. baseline DPR)
    scale = view.transform().m11() * dpr * extra_scale
    w, h = page.rect.width * scale, page.rect.height * scale
    
    clip = None
    if w * h > MAX_PIXELS:
        # Cap to viewport, we only render what is visible
        vis = view.mapToScene(view.viewport().rect()).boundingRect()
        clip = pymupdf.Rect(vis.left(), vis.top(), vis.right(), vis.bottom()) & page.rect
        
    mat = pymupdf.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
    
    img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
    qpm = QPixmap.fromImage(img)
    del img, pix
    
    qpm.setDevicePixelRatio(dpr)
    return qpm, scale, clip
