"""
Data model representing a file in the processing queue with high-performance
metadata extraction and thumbnail pixmap caching.
"""

from enum import Enum
import os
import io
from typing import Optional
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

# File types accepted when another process asks the running instance to open files
SUPPORTED_EXTENSIONS = frozenset({
    ".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif", ".txt",
})


class FileStatus(Enum):
    QUEUED = "queued"
    UPLOADING = "uploading"
    WAITING = "waiting"
    PROCESSING = "processing"
    READY = "ready"
    COMPLETED = "completed"
    ERROR = "error"


class FileItem:
    """Represents a file uploaded to the application queue with cached pixmap rendering."""

    def __init__(self, file_path: str):
        self.file_path = os.path.abspath(file_path)
        self.file_name = os.path.basename(file_path)
        try:
            self.file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        except OSError:
            self.file_size = 0
        self.extension = os.path.splitext(file_path)[1].lower()
        self.status = FileStatus.READY
        self.progress: float = 0.0
        self.error_message: Optional[str] = None
        self.page_count: int = 1
        self.thumbnail_bytes: Optional[bytes] = None
        self._cached_pixmap: Optional[QPixmap] = None
        self.output_path: Optional[str] = None

        self._load_meta()

    def _load_meta(self):
        """Extract basic metadata such as page count using fast C-level PyMuPDF first."""
        if self.extension == ".pdf":
            try:
                import pymupdf
                doc = pymupdf.open(self.file_path)
                self.page_count = len(doc)
                doc.close()
            except Exception:
                try:
                    import pypdf
                    with open(self.file_path, "rb") as f:
                        reader = pypdf.PdfReader(f)
                        self.page_count = len(reader.pages)
                except Exception:
                    self.page_count = 1
        else:
            self.page_count = 1

    def generate_thumbnail(self, max_width: int = 160, max_height: int = 210) -> Optional[bytes]:
        """
        Generate PNG bytes for the file's thumbnail preview.
        Returns None if generation is not possible.
        """
        if self.thumbnail_bytes:
            return self.thumbnail_bytes

        try:
            import hashlib
            thumb_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "MNIME", "thumbs")
            os.makedirs(thumb_dir, exist_ok=True)
            cache_key = f"{self.file_path}_{max_width}_{max_height}_{os.path.getmtime(self.file_path)}"
            cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
            cache_path = os.path.join(thumb_dir, f"{cache_hash}.jpg")
            
            if os.path.exists(cache_path):
                with open(cache_path, "rb") as f:
                    self.thumbnail_bytes = f.read()
                    return self.thumbnail_bytes

            if self.extension == ".pdf":
                try:
                    import pymupdf
                    doc = pymupdf.open(self.file_path)
                    if len(doc) > 0:
                        page = doc[0]
                        rect = page.rect
                        zoom = min(max_width / max(1, rect.width), max_height / max(1, rect.height))
                        mat = pymupdf.Matrix(zoom * 1.5, zoom * 1.5)
                        pix = page.get_pixmap(matrix=mat, alpha=False)
                        self.thumbnail_bytes = pix.tobytes("jpeg")
                        doc.close()
                        try:
                            with open(cache_path, "wb") as f:
                                f.write(self.thumbnail_bytes)
                        except Exception: pass
                        return self.thumbnail_bytes
                except Exception:
                    pass

            elif self.extension == ".txt":
                from PIL import Image, ImageDraw
                img = Image.new("RGB", (max_width, max_height), color=(255, 255, 255))
                d = ImageDraw.Draw(img)
                try:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        text_preview = f.read(200)
                except UnicodeDecodeError:
                    try:
                        with open(self.file_path, "r", encoding="latin-1", errors="replace") as f:
                            text_preview = f.read(200)
                    except Exception:
                        text_preview = "Text Document"
                except Exception:
                    text_preview = "Text Document"
                d.text((10, 10), text_preview, fill=(50, 50, 50))
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG")
                self.thumbnail_bytes = buffer.getvalue()
                try:
                    with open(cache_path, "wb") as f:
                        f.write(self.thumbnail_bytes)
                except Exception: pass
                return self.thumbnail_bytes

            elif self.extension in [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"]:
                from PIL import Image
                with Image.open(self.file_path) as img:
                    img = img.convert("RGB")
                    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                    buffer = io.BytesIO()
                    img.save(buffer, format="JPEG")
                    self.thumbnail_bytes = buffer.getvalue()
                    try:
                        with open(cache_path, "wb") as f:
                            f.write(self.thumbnail_bytes)
                    except Exception: pass
                    return self.thumbnail_bytes

        except Exception:
            pass

        return None

    def get_thumbnail_pixmap(self, max_width: int = 120, max_height: int = 130, expand: bool = False) -> Optional[QPixmap]:
        """
        Returns a pre-rendered, pre-scaled QPixmap cached in memory.
        Subsequent calls return the cached pixmap in O(1) time.
        """
        if self._cached_pixmap is not None:
            return self._cached_pixmap

        thumb_bytes = self.generate_thumbnail(max_width * 2, max_height * 2)
        if thumb_bytes:
            pixmap = QPixmap()
            if pixmap.loadFromData(thumb_bytes):
                mode = Qt.AspectRatioMode.KeepAspectRatioByExpanding if expand else Qt.AspectRatioMode.KeepAspectRatio
                self._cached_pixmap = pixmap.scaled(
                    max_width,
                    max_height,
                    mode,
                    Qt.TransformationMode.SmoothTransformation
                )
                # Drop raw bytes to save RAM (F7 Viewer Diet)
                self.thumbnail_bytes = None
                return self._cached_pixmap

        return None

    def formatted_size(self) -> str:
        """Return human-readable file size."""
        size = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def __repr__(self) -> str:
        return f"<FileItem {self.file_name} ({self.status.value})>"
