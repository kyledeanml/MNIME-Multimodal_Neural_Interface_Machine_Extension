"""
File card widget representing an uploaded file item in the carousel.
Replicates the visual cards with thumbnails, status overlays, and drag-and-drop reordering.
"""

import os
from ui.cursor_fx import get_custom_cursor
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import (
    QPixmap, QPainter, QColor, QPainterPath
)
from core.file_item import FileItem, FileStatus
from .icons import get_svg_pixmap, get_icon
from PyQt6.QtCore import QThreadPool, QRunnable, QMetaObject, Q_ARG


class FileCard(QFrame):
    """Visual card displaying file thumbnail, status, progress, and remove button."""

    remove_requested = pyqtSignal(object)   # FileItem
    card_moved = pyqtSignal(int, int)        # from_index, to_index
    card_double_clicked = pyqtSignal(object) # FileItem

    CARD_WIDTH = 165
    CARD_HEIGHT = 205

    def __init__(self, item: FileItem, index: int, parent=None):
        super().__init__(parent)
        self.item = item
        self.index = index
        self._drag_start_pos = QPoint()

        self.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT)
        self.setCursor(get_custom_cursor())
        # Only accept internal card-reorder drops; OS file drops must bubble up
        self.setAcceptDrops(True)
        self._thumb_requested = False

        self._setup_ui()
        self.update_state()

    def _setup_ui(self):
        self.setObjectName("fileCard")
        self.setStyleSheet("""
            #fileCard {
                background-color: #11151f;
                border: 1.5px solid #1f2737;
                border-radius: 10px;
            }
            #fileCard:hover {
                border: 1.5px solid #00d2ff;
                background-color: #141a26;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Top Bar: File name + Remove (X) button
        self.top_bar_widget = QWidget()
        top_bar = QHBoxLayout(self.top_bar_widget)
        top_bar.setContentsMargins(4, 4, 4, 4)
        top_bar.setSpacing(2)

        self.name_label = QLabel(self.item.file_name)
        self.name_label.setStyleSheet("color: #ffffff; font-size: 10px; font-weight: 500;")
        self.name_label.setToolTip(f"{self.item.file_name}\n({self.item.formatted_size()})")

        # Elide long file names
        metrics = self.name_label.fontMetrics()
        elided = metrics.elidedText(self.item.file_name, Qt.TextElideMode.ElideMiddle, 75)
        self.name_label.setText(elided)

        self.remove_btn = QPushButton()
        self.remove_btn.setFixedSize(18, 18)
        self.remove_btn.setIcon(get_icon("close", "#ffffff"))
        self.remove_btn.setCursor(get_custom_cursor())
        self.remove_btn.setToolTip("Remove this file")
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(60, 60, 60, 180);
                border: none;
                border-radius: 9px;
            }
            QPushButton:hover {
                background-color: #e74c3c;
            }
        """)
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self.item))

        top_bar.addWidget(self.name_label)
        top_bar.addStretch()
        top_bar.addWidget(self.remove_btn)
        
        self.top_bar_widget.setStyleSheet("background-color: rgba(10, 15, 24, 200); border-radius: 6px;")
        self.top_bar_widget.setVisible(False)
        layout.addWidget(self.top_bar_widget)

        # Center Preview / Status Container
        self.preview_container = QWidget()
        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_icon = QLabel()
        self.status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.status_icon)

        self.status_text = QLabel("Waiting...")
        self.status_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_text.setStyleSheet("color: #ffffff; font-size: 10px; font-weight: 600;")
        preview_layout.addWidget(self.status_text)

        layout.addWidget(self.preview_container, 1)

        # Bottom Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #00e5ff;
                border-radius: 2px;
            }
        """)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

    def update_state(self):
        """Update the visual state matching status: WAITING, UPLOADING, READY, etc."""
        status = self.item.status

        if status == FileStatus.UPLOADING:
            self.status_icon.setPixmap(get_svg_pixmap("upload", 28, "#00e5ff"))
            self.status_text.setText("Uploading...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(int(self.item.progress))
        elif status == FileStatus.WAITING:
            self.status_icon.setPixmap(get_svg_pixmap("hourglass", 28, "#8b949e"))
            self.status_text.setText("Waiting...")
            self.progress_bar.setVisible(False)
        elif status == FileStatus.PROCESSING:
            self.status_icon.setPixmap(get_svg_pixmap("hourglass", 28, "#00e5ff"))
            self.status_text.setText("Processing...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(int(self.item.progress))
        elif status in [FileStatus.READY, FileStatus.COMPLETED]:
            self.status_icon.setPixmap(get_svg_pixmap("check", 28, "#00e5ff"))
            self.status_text.setText("Ready")
            self.status_text.setStyleSheet("color: #00e5ff; font-size: 10px; font-weight: bold;")
            self.progress_bar.setVisible(False)
        elif status == FileStatus.ERROR:
            self.status_icon.setPixmap(get_svg_pixmap("clear", 28, "#ff6b6b"))
            self.status_text.setText("Error")
            self.status_text.setStyleSheet("color: #ff6b6b; font-size: 10px; font-weight: bold;")
            self.progress_bar.setVisible(False)

        self.update()

    def paintEvent(self, event):
        """Draw thumbnail background and subtle checkerboard pattern."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 8, 8)
        painter.setClipPath(path)

        # 1. Checkerboard background strip at bottom (transparency indicator)
        checker_size = 8
        for x in range(0, self.width(), checker_size):
            for y in range(self.height() - 25, self.height(), checker_size):
                color = (QColor(220, 220, 220)
                         if ((x // checker_size) + (y // checker_size)) % 2 == 0
                         else QColor(190, 190, 190))
                painter.fillRect(x, y, checker_size, checker_size, color)

        # 2. Thumbnail (lazy load to prevent RAM spikes and UI stutter)
        scaled = None
        if self.item._cached_pixmap is not None:
            scaled = self.item._cached_pixmap
        elif getattr(self.item, "thumbnail_bytes", None) is not None:
            scaled = self.item.get_thumbnail_pixmap(self.width(), self.height(), expand=True)
            
        if scaled and not scaled.isNull():
            px = (self.width() - scaled.width()) // 2
            py = (self.height() - scaled.height()) // 2
            painter.drawPixmap(px, py, scaled)
            
            # Subtle vignette so status text and borders are legible
            painter.fillRect(0, 0, self.width(), self.height(), QColor(10, 15, 24, 60))
        else:
            painter.fillRect(0, 0, self.width(), self.height(), QColor(20, 26, 38))
            if not self._thumb_requested:
                self._thumb_requested = True
                self._request_thumbnail_async()

        painter.end()
        super().paintEvent(event)

    def _request_thumbnail_async(self):
        class ThumbWorker(QRunnable):
            def __init__(self, item, card_width, card_height, cb):
                super().__init__()
                self.item = item
                self.card_width = card_width
                self.card_height = card_height
                self.cb = cb

            def run(self):
                self.item.generate_thumbnail(self.card_width * 2, self.card_height * 2)
                QMetaObject.invokeMethod(self.cb, "update", Qt.ConnectionType.QueuedConnection)

        QThreadPool.globalInstance().start(ThumbWorker(self.item, self.width(), self.height(), self))

    # ------------------------------------------------------------------
    # Mouse events — manual drag reorder (no QDrag/OLE, works with WM_DROPFILES)
    # ------------------------------------------------------------------
    def enterEvent(self, event):
        self.top_bar_widget.setVisible(True)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.top_bar_widget.setVisible(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
            self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if not hasattr(self, '_drag_start_pos') or self._drag_start_pos is None:
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
            return

        if not self._dragging:
            self._dragging = True
            # Create floating ghost overlay at the top-level window
            self._start_manual_drag(event)
        else:
            self._update_manual_drag(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and getattr(self, '_dragging', False):
            self._finish_manual_drag(event)
            self._dragging = False
        self._drag_start_pos = QPoint()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.card_double_clicked.emit(self.item)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _start_manual_drag(self, event):
        """Turn the mouse cursor into a blue file icon during the drag."""
        from PyQt6.QtWidgets import QApplication
        from ui.cursor_fx import get_file_drag_cursor

        drag_cursor = get_file_drag_cursor()
        QApplication.setOverrideCursor(drag_cursor)
        self.grabMouse()

    def _update_manual_drag(self, event):
        """No need to update ghost position since we are using a real OS cursor."""
        pass

    def _finish_manual_drag(self, event):
        """Release the mouse grab and calculate which card index we landed on."""
        from PyQt6.QtWidgets import QApplication
        self.releaseMouse()
        while QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()

        # Determine drop target index from cursor position
        from PyQt6.QtGui import QCursor
        global_pos = QCursor.pos()

        # Walk up to ClippedCardsArea
        cards_area = self.parent()
        if cards_area is None or not hasattr(cards_area, '_cards'):
            return

        local_pos = cards_area.mapFromGlobal(global_pos)
        target_index = self.index  # default: no move

        for card in cards_area._cards:
            if card is self:
                continue
            card_rect = card.geometry()
            if card_rect.contains(local_pos):
                target_index = card.index
                break
            # Check if cursor is between cards (to the left of this card)
            if local_pos.x() < card_rect.center().x() and local_pos.x() >= card_rect.left() - 7:
                target_index = card.index
                break

        if target_index != self.index:
            self.card_moved.emit(self.index, target_index)

    def hideEvent(self, event):
        if getattr(self, '_dragging', False):
            from PyQt6.QtWidgets import QApplication
            self.releaseMouse()
            while QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()
            self._dragging = False
        super().hideEvent(event)

    # ------------------------------------------------------------------
    # Drop events — only handle OS file drops that bubble up from nativeEvent
    # Card reorder is now handled by mouse events, not DnD.
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls():
            from ui.cursor_fx import get_file_drag_cursor
            from PyQt6.QtWidgets import QApplication
            if QApplication.overrideCursor() is None:
                QApplication.setOverrideCursor(get_file_drag_cursor())
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        from PyQt6.QtWidgets import QApplication
        while QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()
        super().dragLeaveEvent(event)

    def dragMoveEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls():
            paths = [u.toLocalFile() for u in mime.urls() if u.isLocalFile()]
            if paths:
                p = self.parent()
                while p and not hasattr(p, "files_dropped"):
                    p = p.parent()
                if p:
                    p.files_dropped.emit(paths)
                event.acceptProposedAction()
        else:
            event.ignore()

