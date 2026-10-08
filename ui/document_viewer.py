"""
Cross-Reference viewer.

Shows a source document on the left. The user drags a box over a passage (PDF)
or selects text (text files), and MNIME searches every other file in the queue
for related passages, then asks the local NLP model for a comparative brief.
"""

import html
import os
from typing import Callable, List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QTextBrowser, QTextEdit, QStackedWidget, QProgressBar, QFrame, QSplitter, QWidget
)
from PyQt6.QtCore import Qt, QRectF, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QImage
from core.file_item import FileItem

TEXT_EXTENSIONS = (".txt", ".md", ".py", ".json", ".csv", ".js", ".ts", ".html", ".css", ".cpp", ".c", ".h", ".java")


class PDFPageView(QGraphicsView):
    text_selected = pyqtSignal(str)
    prev_page_requested = pyqtSignal()
    next_page_requested = pyqtSignal()
    zoom_changed = pyqtSignal()

    BASE_DPI = 96.0

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.rubber_band = QRect()
        self.start_pos = QPoint()
        self.is_drawing = False
        self.current_page = None
        self._render_scale = 1.0
        self.setCursor(Qt.CursorShape.CrossCursor)

    def get_render_scale(self) -> float:
        view_scale = self.transform().m11()
        scale = view_scale * (self.BASE_DPI / 72.0)
        return max(scale, 1.0)

    def set_page(self, page, pixmap, render_scale: float = 1.0, clip=None):
        self.current_page = page
        self.scene().clear()
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        inv = 1.0 / (render_scale / self.devicePixelRatioF()) if render_scale > 0 else 1.0
        self.pixmap_item.setScale(inv)
        if clip:
            self.pixmap_item.setPos(clip.x0, clip.y0)
        self.scene().addItem(self.pixmap_item)
        self.scene().setSceneRect(QRectF(0, 0, page.rect.width, page.rect.height))
        self.rubber_band = QRect()

    def fit_width(self):
        rect = self.scene().sceneRect()
        if rect.isEmpty():
            return
        self.resetTransform()
        scale = (self.viewport().width() - 20) / max(rect.width(), 1)
        self.scale(scale, scale)
        self.zoom_changed.emit()

    def wheelEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)
            self.zoom_changed.emit()
            return
        bar = self.verticalScrollBar()
        at_top = bar.value() <= bar.minimum()
        at_bottom = bar.value() >= bar.maximum()
        if event.angleDelta().y() > 0 and at_top:
            self.prev_page_requested.emit()
        elif event.angleDelta().y() < 0 and at_bottom:
            self.next_page_requested.emit()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.rubber_band = QRect(self.start_pos, self.start_pos)
            self.is_drawing = True
            self.viewport().update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self.rubber_band = QRect(self.start_pos, event.pos()).normalized()
            self.viewport().update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_drawing:
            self.is_drawing = False
            self._extract_text()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.rubber_band.isEmpty():
            painter = QPainter(self.viewport())
            pen = QPen(QColor(0, 229, 255, 200))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(QColor(0, 229, 255, 40))
            painter.drawRect(self.rubber_band)

    def _extract_text(self):
        if not self.current_page or self.rubber_band.width() < 4 or self.rubber_band.height() < 4:
            return

        top_left = self.mapToScene(self.rubber_band.topLeft())
        bottom_right = self.mapToScene(self.rubber_band.bottomRight())

        # Scene units are already in PDF points since mapToScene converts from viewport pixels
        import pymupdf
        rect = pymupdf.Rect(
            top_left.x(),
            top_left.y(),
            bottom_right.x(),
            bottom_right.y()
        )

        text = self.current_page.get_text("text", clip=rect).strip()
        if text:
            self.text_selected.emit(text)


class DocumentViewer(QDialog):
    """Cross-reference window: pick a passage in the source, compare it with the other files."""

    def __init__(
        self,
        file_item: FileItem,
        reference_items: Optional[List[FileItem]] = None,
        run_reference: Optional[Callable[[str, "DocumentViewer"], None]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.file_item = file_item
        self.reference_items = list(reference_items or [])
        self._run_reference = run_reference
        self.setWindowTitle(f"MNIME - Cross-Reference - {file_item.file_name}")
        self.setWindowFlags(Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMinimumSize(1100, 720)
        self.resize(1300, 820)

        self.doc = None
        self.page_idx = 0
        self.is_pdf = file_item.extension == ".pdf"

        self.setStyleSheet("""
            QDialog { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1c212b, stop:0.5 #10141c, stop:1 #080a0f); color: #f0f6fc; }
            QPushButton { background-color: #162438; color: #00e5ff; border: 1px solid #00d2ff; border-radius: 6px; padding: 6px 14px; font-weight: bold; }
            QPushButton:hover { background-color: #0077b6; color: #ffffff; }
            QPushButton:disabled { background-color: #11151f; color: #3b4a5e; border: 1px solid #1f2737; }
            QPushButton#crossref_btn { font-size: 13px; padding: 9px 14px; letter-spacing: 1px; }
            QLabel { color: #8b949e; font-size: 12px; }
            QLabel#section { color: #00d2ff; font-family: 'Segoe UI Black'; font-size: 11px; letter-spacing: 1px; }
            QLabel#title { color: #00e5ff; font-family: 'Segoe UI Black'; font-size: 15px; letter-spacing: 1px; }
            QTextBrowser, QTextEdit { background-color: #0a0d14; color: #c9d1d9; border: 1px solid #1f2737; border-radius: 6px; padding: 8px; font-size: 13px; }
            QTextEdit:focus { border: 1px solid #00d2ff; }
            QProgressBar { border: 1px solid #1f2737; border-radius: 4px; text-align: center; color: white; background-color: #0d1117; max-height: 14px; font-size: 10px; }
            QProgressBar::chunk { background-color: #00e5ff; }
            QSplitter::handle { background-color: #1f2737; }
        """)

        self._load_doc()
        self._setup_ui()
        self._render_page()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _load_doc(self):
        if not self.is_pdf:
            return
        try:
            import pymupdf
            self.doc = pymupdf.open(self.file_item.file_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open PDF: {e}")
            self.doc = None

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 14)
        outer.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("CROSS-REFERENCE")
        title.setObjectName("title")
        source_lbl = QLabel(f"Source: {self.file_item.file_name}")
        source_lbl.setStyleSheet("color: #c9d1d9; font-size: 12px;")
        header.addWidget(title)
        header.addSpacing(16)
        header.addWidget(source_lbl)
        header.addStretch()
        outer.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ---- Left: source document ----
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        self.scene = QGraphicsScene(self)
        self.view = PDFPageView(self.scene, self)
        self.view.setStyleSheet("background-color: #0a0d14; border: 1px solid #1f2737; border-radius: 6px;")
        self.view.text_selected.connect(self._on_text_selected)
        self.view.prev_page_requested.connect(self._prev_page)
        self.view.next_page_requested.connect(self._next_page)
        self.view.zoom_changed.connect(self._on_zoom_changed)
        self.stack.addWidget(self.view)

        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.selectionChanged.connect(self._on_text_view_selection)
        self.stack.addWidget(self.text_view)
        left_layout.addWidget(self.stack, 1)

        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("Prev Page")
        self.prev_btn.clicked.connect(self._prev_page)
        self.next_btn = QPushButton("Next Page")
        self.next_btn.clicked.connect(self._next_page)
        self.page_label = QLabel()
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.page_label)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_btn)
        left_layout.addLayout(nav_layout)

        if self.is_pdf:
            self.stack.setCurrentWidget(self.view)
        else:
            self.stack.setCurrentWidget(self.text_view)
            self.prev_btn.hide()
            self.next_btn.hide()
            self._load_text_source()

        splitter.addWidget(left)

        # ---- Right: passage + results ----
        right = QFrame()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(6)

        how_to = (
            "Drag a box over a passage on the page" if self.is_pdf else "Select a passage in the document"
        ) + ", or type/paste text below, then press CROSS-REFERENCE."
        info_label = QLabel(how_to)
        info_label.setWordWrap(True)
        right_layout.addWidget(info_label)

        sec = QLabel(f"COMPARING AGAINST ({len(self.reference_items)})")
        sec.setObjectName("section")
        right_layout.addWidget(sec)
        names = ", ".join(html.escape(i.file_name) for i in self.reference_items[:8])
        if len(self.reference_items) > 8:
            names += f" and {len(self.reference_items) - 8} more"
        self.targets_label = QLabel(names or "No other files in the queue. Add files to MNIME first.")
        self.targets_label.setWordWrap(True)
        self.targets_label.setStyleSheet("color: #c9d1d9; font-size: 12px;")
        right_layout.addWidget(self.targets_label)

        sec2 = QLabel("SOURCE PASSAGE")
        sec2.setObjectName("section")
        right_layout.addWidget(sec2)
        self.source_text_view = QTextEdit()
        self.source_text_view.setAcceptRichText(False)
        self.source_text_view.setPlaceholderText("Selected text will appear here...")
        self.source_text_view.setMaximumHeight(140)
        self.source_text_view.textChanged.connect(self._update_button_state)
        right_layout.addWidget(self.source_text_view)

        self.reference_btn = QPushButton("CROSS-REFERENCE")
        self.reference_btn.setObjectName("crossref_btn")
        self.reference_btn.setEnabled(False)
        self.reference_btn.clicked.connect(self._trigger_reference)
        right_layout.addWidget(self.reference_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_label = QLabel("")
        right_layout.addWidget(self.progress_bar)
        right_layout.addWidget(self.status_label)

        sec3 = QLabel("COMPARATIVE BRIEF")
        sec3.setObjectName("section")
        right_layout.addWidget(sec3)
        self.result_view = QTextBrowser()
        self.result_view.setOpenExternalLinks(False)
        self.result_view.setPlaceholderText("Results will appear here...")
        right_layout.addWidget(self.result_view, 1)

        splitter.addWidget(right)
        splitter.setSizes([780, 520])
        outer.addWidget(splitter, 1)

    def _load_text_source(self):
        try:
            try:
                with open(self.file_item.file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(self.file_item.file_path, "r", encoding="latin-1", errors="replace") as f:
                    content = f.read()
        except OSError as e:
            content = f"Could not read file: {e}"
        self.text_view.setPlainText(content)
        self.page_label.setText("Text document")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        if self.is_pdf:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self.view.fit_width)

    def _render_page(self, render_scale: float | None = None):
        if not self.is_pdf or not self.doc or self.page_idx >= len(self.doc):
            return
        self.page_label.setText(f"Page {self.page_idx + 1} of {len(self.doc)}")

        page = self.doc[self.page_idx]
        from core.render_utils import render_page
        
        qpixmap, scale, clip = render_page(page, self.view, self.view.devicePixelRatioF(), self.view.BASE_DPI / 72.0)
        
        self.view.set_page(page, qpixmap, render_scale=scale, clip=clip)
        self.view.verticalScrollBar().setValue(0)

    def _on_zoom_changed(self):
        if not self.doc:
            return
        new_scale = self.view.get_render_scale()
        if abs(new_scale - self.view._render_scale) / max(self.view._render_scale, 0.001) > 0.05:
            h_bar = self.view.horizontalScrollBar()
            v_bar = self.view.verticalScrollBar()
            h_ratio = h_bar.value() / max(h_bar.maximum(), 1)
            v_ratio = v_bar.value() / max(v_bar.maximum(), 1)

            self._render_page(render_scale=new_scale)

            def restore_scroll():
                h_bar.setValue(int(h_ratio * h_bar.maximum()))
                v_bar.setValue(int(v_ratio * v_bar.maximum()))
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, restore_scroll)

    def _prev_page(self):
        if self.doc and self.page_idx > 0:
            self.page_idx -= 1
            self._render_page()

    def _next_page(self):
        if self.doc and self.page_idx < len(self.doc) - 1:
            self.page_idx += 1
            self._render_page()

    # ------------------------------------------------------------------
    # Selection + referencing
    # ------------------------------------------------------------------

    def _on_text_selected(self, text: str):
        self.source_text_view.setPlainText(text)

    def _on_text_view_selection(self):
        text = self.text_view.textCursor().selectedText().replace("\u2029", "\n").strip()
        if text:
            self.source_text_view.setPlainText(text)

    def _update_button_state(self):
        busy = self.progress_bar.isVisible()
        has_text = bool(self.source_text_view.toPlainText().strip())
        self.reference_btn.setEnabled(has_text and bool(self.reference_items) and not busy)

    def _trigger_reference(self):
        text = self.source_text_view.toPlainText().strip()
        if not text or not self._run_reference:
            return
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Searching your other files...")
        self._update_button_state()
        self.result_view.setHtml(
            "<div style='color:#8b949e'>Building the comparison. The first run indexes the other "
            "files, later runs reuse that index.</div>"
        )
        self._run_reference(text, self)

    def set_progress(self, pct: int, msg: str):
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(pct)
        self.status_label.setText(msg)

    def set_result(self, result):
        """Render either a plain string or a dict {'brief': str, 'passages': [...], 'note': str}."""
        self.progress_bar.setVisible(False)
        self.status_label.setText("Done.")
        if isinstance(result, dict):
            parts = []
            note = result.get("note")
            if note:
                parts.append(f"<div style='color:#ffb300'>{html.escape(note)}</div><br>")
            brief = result.get("brief")
            if brief:
                parts.append(
                    "<div style='color:#00e5ff; font-weight:bold'>Brief</div>"
                    f"<div style='color:#c9d1d9'>{html.escape(brief).replace(chr(10), '<br>')}</div><br>"
                )
            passages = result.get("passages") or []
            if passages:
                parts.append("<div style='color:#00e5ff; font-weight:bold'>Related passages</div>")
                for p in passages:
                    src = html.escape(os.path.basename(str(p.get("source", "Unknown"))))
                    body = html.escape(str(p.get("content", ""))[:700]).replace("\n", "<br>")
                    parts.append(
                        f"<div style='margin-top:6px; color:#00d2ff'>{src}</div>"
                        f"<div style='color:#a9b4c2'>{body}</div>"
                    )
            elif not brief:
                parts.append("<div style='color:#8b949e'>No related passages were found in the other files.</div>")
            self.result_view.setHtml("".join(parts))
        else:
            self.result_view.setPlainText(str(result))
        self._update_button_state()

    def closeEvent(self, event):
        if self.doc:
            try:
                self.doc.close()
            except Exception:
                pass
            self.doc = None
        super().closeEvent(event)
