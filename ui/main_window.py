"""
Main application window assembling Header, Tabs, Controls, Carousel, and Action Bar.
Free-floating dark metallic UI with dark neon blue highlights.
Handles file picking, OS drag-and-drop, worker threads, and file conversions.
"""

import os
import shutil
import subprocess
import tempfile
from typing import List, Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
    QMessageBox, QApplication, QFrame, QPushButton, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QColor, QIcon

from core.file_item import FileItem, FileStatus
from core.pdf_engine import PDFEngine
from core.worker import TaskWorker
from core.app_icon import get_app_icon
from core.logging_setup import get_logger

log = get_logger("main_window")

from .tabs_bar import TabsBar, ToolMode
from .carousel_view import CarouselView
from .action_bar import ActionBar
from .output_view import OutputView
from .nlp_view import NLPView
from .document_viewer import DocumentViewer
from ui.cursor_fx import get_custom_cursor

import sys
if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

    WM_DROPFILES = 0x0233
    WM_COPYDATA = 0x004A
    WM_COPYGLOBALDATA = 0x0049
    MSGFLT_ALLOW = 1

    class WinMSG(ctypes.Structure):
        _fields_ = [
            ("hwnd",    ctypes.wintypes.HWND),
            ("message", ctypes.c_uint),
            ("wParam",  ctypes.wintypes.WPARAM),
            ("lParam",  ctypes.wintypes.LPARAM),
            ("time",    ctypes.wintypes.DWORD),
            ("pt",      ctypes.wintypes.POINT),
        ]

    try:
        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32

        if hasattr(user32, "ChangeWindowMessageFilterEx"):
            user32.ChangeWindowMessageFilterEx.argtypes = [
                ctypes.wintypes.HWND,
                ctypes.wintypes.UINT,
                ctypes.wintypes.DWORD,
                ctypes.c_void_p
            ]
            user32.ChangeWindowMessageFilterEx.restype = ctypes.wintypes.BOOL

        shell32.DragAcceptFiles.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.BOOL]
        shell32.DragAcceptFiles.restype = None

        shell32.DragQueryFileW.argtypes = [
            ctypes.wintypes.WPARAM,
            ctypes.wintypes.UINT,
            ctypes.wintypes.LPWSTR,
            ctypes.wintypes.UINT
        ]
        shell32.DragQueryFileW.restype = ctypes.wintypes.UINT

        shell32.DragFinish.argtypes = [ctypes.wintypes.WPARAM]
        shell32.DragFinish.restype = None
    except Exception:
        pass


class MainWindow(QMainWindow):
    """MNIME main application window featuring a free-floating dark metallic interface."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MNIME - Advanced File Manipulator")
        self.setMinimumWidth(940)
        self.setFixedHeight(420) # Lock vertical resize, make it very slim
        self.resize(1350, 420)

        # Set window icon (taskbar / quickbar / titlebar)
        app_icon = get_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)

        self.current_mode = ToolMode.COMBINE_PDF
        self.file_items: List[FileItem] = []
        self.worker: TaskWorker = None
        self._reference_worker: TaskWorker = None
        self._load_worker: TaskWorker = None
        self._temp_roots: List[str] = []
        self._drag_pos: QPoint = None
        self._active_reader = None
        self._active_crossref = None
        self._crossref_index_cache = {}

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self._dnd_registered = False

        # Lazy-loaded views
        self._output_view = None
        self._nlp_view = None
        self._particle_overlay = None

        self._setup_ui()
        self._restore_session()
        
        self.particle_cursor = self._get_particle_cursor()
        self.setCursor(self.particle_cursor)
        
        # Install a global event filter to seamlessly handle cursor changes on edges
        from PyQt6.QtCore import QCoreApplication, QTimer
        QCoreApplication.instance().installEventFilter(self)

        # Start idle trim timer assuming we start hidden (in tray)
        if not hasattr(self, '_idle_trim_timer'):
            self._idle_trim_timer = QTimer(self)
            self._idle_trim_timer.setSingleShot(True)
            self._idle_trim_timer.timeout.connect(self._do_idle_trim)
        self._idle_trim_timer.start(30000)

        # NOTE: _bypass_uipi_for_drag_drop is intentionally NOT called here.
        # It must run AFTER show() so it can override Qt's OLE DnD registration.
        # See showEvent().

    def showEvent(self, event):
        """Register WM_DROPFILES AFTER Qt has finished its internal OLE DnD setup."""
        super().showEvent(event)
        if hasattr(self, '_idle_trim_timer'):
            self._idle_trim_timer.stop()
        try:
            from core.idle_trim import set_efficiency_mode
            set_efficiency_mode(False)
        except Exception:
            pass
            
        if not self._dnd_registered:
            # Defer by one event-loop cycle so RegisterDragDrop has fully completed
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(50, self._bypass_uipi_for_drag_drop)

    def _bypass_uipi_for_drag_drop(self):
        """Register HWND as a shell drop target via WM_DROPFILES and bypass UIPI.

        On Windows, Qt registers an OLE IDropTarget during show().  OLE drag-and-drop
        is blocked by UIPI when our process is elevated and the drag source (Explorer)
        is not.  We work around this by:
          1. Revoking Qt's OLE drop target
          2. Allowing WM_DROPFILES through the UIPI message filter
          3. Registering for the legacy WM_DROPFILES mechanism via DragAcceptFiles
        """
        if sys.platform != "win32" or self._dnd_registered:
            return
        try:
            hwnd = int(self.winId())

            # Step 1: Revoke Qt's OLE drop target so DragAcceptFiles can take over
            try:
                ole32 = ctypes.windll.ole32
                ole32.RevokeDragDrop.argtypes = [ctypes.wintypes.HWND]
                ole32.RevokeDragDrop.restype = ctypes.wintypes.LONG
                ole32.RevokeDragDrop(hwnd)
            except Exception:
                pass

            # Step 2: Punch through UIPI for drop-related messages
            if hasattr(user32, "ChangeWindowMessageFilterEx"):
                user32.ChangeWindowMessageFilterEx(hwnd, WM_DROPFILES, MSGFLT_ALLOW, None)
                user32.ChangeWindowMessageFilterEx(hwnd, WM_COPYDATA, MSGFLT_ALLOW, None)
                user32.ChangeWindowMessageFilterEx(hwnd, WM_COPYGLOBALDATA, MSGFLT_ALLOW, None)

            # Step 3: Register for WM_DROPFILES
            shell32.DragAcceptFiles(hwnd, True)
            self._dnd_registered = True
        except Exception as e:
            print(f"Drop registration failed: {e}")

    def nativeEvent(self, event_type, message):
        """Process Win32 WM_DROPFILES messages sent by Explorer / the shell."""
        if sys.platform == "win32":
            try:
                raw_type = bytes(event_type) if hasattr(event_type, "data") else event_type
                if raw_type in (b"windows_generic_MSG", "windows_generic_MSG"):
                    msg = WinMSG.from_address(int(message))
                    if msg.message == WM_DROPFILES:
                        hDrop = msg.wParam
                        count = shell32.DragQueryFileW(hDrop, 0xFFFFFFFF, None, 0)
                        paths = []
                        for i in range(count):
                            buf_len = shell32.DragQueryFileW(hDrop, i, None, 0) + 1
                            buf = ctypes.create_unicode_buffer(buf_len)
                            shell32.DragQueryFileW(hDrop, i, buf, buf_len)
                            paths.append(buf.value)
                        shell32.DragFinish(hDrop)
                        if paths:
                            self._add_files(paths)
                        return True, 0
            except Exception as e:
                print(f"nativeEvent drop error: {e}")

        return False, 0

    def eventFilter(self, obj, event):
        # We only care about mouse moves for updating the edge-resizing cursors
        if event.type() != event.Type.MouseMove:
            return super().eventFilter(obj, event)

        # Respect global override cursors and mouse grabs (e.g. BlankCursor during card drag)
        from PyQt6.QtWidgets import QApplication, QWidget
        if QApplication.overrideCursor() is not None or QWidget.mouseGrabber() is not None:
            return super().eventFilter(obj, event)
        # Map the global cursor position to window coordinates
        from PyQt6.QtGui import QCursor
        pos = self.mapFromGlobal(QCursor.pos())
        
        # Check if we are hovering over an edge
        edge = self._get_edge(pos)
        if edge == Qt.Edge.LeftEdge or edge == Qt.Edge.RightEdge:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            if hasattr(self, 'particle_cursor'):
                self.setCursor(self.particle_cursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
                
        return super().eventFilter(obj, event)

    def _get_edge(self, pos: QPoint) -> Qt.Edge:
        edge = Qt.Edge(0)
        margin = 15 # Include the 10px transparent padding + 5px grab area
        
        if pos.x() <= margin:
            edge |= Qt.Edge.LeftEdge
        elif pos.x() >= self.width() - margin:
            edge |= Qt.Edge.RightEdge
            
        # Vertical resizing is disabled, so we only return horizontal edges
        return edge

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_edge(event.pos())
            if edge != Qt.Edge(0):
                self.windowHandle().startSystemResize(edge)
                return
            
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        from PyQt6.QtWidgets import QApplication, QWidget
        if QApplication.overrideCursor() is not None or QWidget.mouseGrabber() is not None:
            if self._drag_pos is not None:
                delta = event.globalPosition().toPoint() - self._drag_pos
                self.move(self.pos() + delta)
                self._drag_pos = event.globalPosition().toPoint()
            return

        # Update cursor based on hover position
        edge = self._get_edge(event.pos())
        if edge == Qt.Edge.LeftEdge or edge == Qt.Edge.RightEdge:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            if hasattr(self, 'particle_cursor'):
                self.setCursor(self.particle_cursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

        # Handle moving the window
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None

    def changeEvent(self, event):
        if event.type() == event.Type.WindowStateChange:
            if self.isMinimized():
                self.hide()
                self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
                event.ignore()
                return
            super().changeEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            from ui.cursor_fx import get_file_drag_cursor
            if QApplication.overrideCursor() is None:
                QApplication.setOverrideCursor(get_file_drag_cursor())
            event.acceptProposedAction()
            if hasattr(self, 'carousel') and self.carousel.isVisible():
                self.carousel._set_drag_style(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        while QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()
        if hasattr(self, 'carousel') and self.carousel.isVisible():
            self.carousel._set_drag_style(False)
        super().dragLeaveEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        while QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()
        if hasattr(self, 'carousel') and self.carousel.isVisible():
            self.carousel._set_drag_style(False)

        if event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
            if paths:
                self._add_files(paths)
                event.acceptProposedAction()

    def _get_particle_cursor(self):
        from PyQt6.QtGui import QCursor, QPixmap, QPainter, QColor
        from PyQt6.QtCore import Qt, QPointF
        
        size = 24
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cx, cy = size / 2, size / 2
        
        # Subtle cyan outer glow
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(140, 230, 255, 120))
        painter.drawEllipse(QPointF(cx, cy), 5.0, 5.0)
        
        # Bright white particle core
        painter.setBrush(QColor(255, 255, 255, 255))
        painter.drawEllipse(QPointF(cx, cy), 2.0, 2.0)
        
        painter.end()
        return QCursor(pixmap, int(cx), int(cy))

    def _setup_ui(self):
        # Global dark dialog styling
        self.setStyleSheet("""
            QMessageBox {
                background-color: #11151f;
                color: #f0f6fc;
                border: 1px solid #1f2737;
            }
            QMessageBox QLabel {
                color: #f0f6fc;
                font-size: 13px;
            }
            QMessageBox QPushButton {
                background-color: #162438;
                color: #00e5ff;
                border: 1px solid #00d2ff;
                border-radius: 6px;
                padding: 6px 18px;
                font-size: 12px;
                font-weight: 700;
            }
            QMessageBox QPushButton:hover {
                background-color: #0077b6;
                color: #ffffff;
            }
            QFileDialog {
                background-color: #0d1117;
                color: #c9d1d9;
            }
            QFileDialog QWidget {
                background-color: #0d1117;
                color: #c9d1d9;
            }
            QFileDialog QListView, QFileDialog QTreeView {
                background-color: #161b22;
                color: #f0f6fc;
                border: 1px solid #2d333b;
                border-radius: 6px;
            }
            QFileDialog QHeaderView::section {
                background-color: #21262d;
                color: #8b949e;
                border: none;
                border-bottom: 1px solid #30363d;
                padding: 4px;
            }
            QFileDialog QPushButton {
                background-color: #162438;
                color: #00e5ff;
                border: 1px solid #00d2ff;
                border-radius: 6px;
                padding: 6px 18px;
                font-size: 12px;
                font-weight: 700;
            }
            QFileDialog QPushButton:hover {
                background-color: #1b304f;
                color: #ffffff;
            }
            QFileDialog QComboBox, QFileDialog QLineEdit {
                background-color: #161b22;
                color: #f0f6fc;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 4px;
            }
            QFileDialog QLabel {
                color: #8b949e;
            }
        """)

        central_widget = QWidget()
        central_widget.setMouseTracking(True)
        base_layout = QVBoxLayout(central_widget)
        base_layout.setContentsMargins(10, 10, 10, 10)

        class WatermarkFrame(QFrame):
            def __init__(self, parent=None):
                super().__init__(parent)

            def paintEvent(self, event):
                super().paintEvent(event)
                from PyQt6.QtGui import QPainter, QFont, QPen, QColor
                from PyQt6.QtCore import Qt
                
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
                font = QFont("Segoe UI Black", 80, QFont.Weight.Black)
                font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 15.0)
                painter.setFont(font)
                painter.setPen(QPen(QColor(255, 255, 255, 4)))
                
                text = "MNIME        " * 20
                y_offset = 80
                while y_offset < self.height() + 100:
                    painter.drawText(-100, y_offset, text)
                    y_offset += 180

        self.container_frame = WatermarkFrame()
        self.container_frame.setMouseTracking(True)
        self.container_frame.setObjectName("container_frame")
        self.container_frame.setStyleSheet("""
            #container_frame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(28, 33, 43, 230), stop:0.5 rgba(16, 20, 28, 220), stop:1 rgba(8, 10, 15, 230));
                border-top: 1.5px solid rgba(255, 255, 255, 40);
                border-left: 1.5px solid rgba(255, 255, 255, 30);
                border-right: 1.5px solid rgba(0, 210, 255, 150);
                border-bottom: 1.5px solid rgba(0, 210, 255, 150);
                border-top-left-radius: 40px;
                border-top-right-radius: 8px;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 40px;
            }
        """)
        
        # Removed QGraphicsDropShadowEffect as it causes severe CPU bottlenecks and window flickering during system resize on frameless windows.
        # The clean glassmorphic border defined in the stylesheet above provides sufficient edge definition.
        
        # Center the window seamlessly on the primary display
        if app := QApplication.instance():
            screen = app.primaryScreen().geometry()
            self.move(
                (screen.width() - self.width()) // 2,
                (screen.height() - self.height()) // 2
            )
        
        main_layout = QVBoxLayout(self.container_frame)
        main_layout.setContentsMargins(16, 8, 16, 12)
        main_layout.setSpacing(8)

        # Custom window controls (Minimize and Close buttons)
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.setSpacing(8)
        
        # 2. Free-floating Tabs Bar inline with window controls
        self.tabs_bar = TabsBar(self)
        self.tabs_bar.mode_changed.connect(self._on_mode_changed)
        top_bar.addWidget(self.tabs_bar, 1)
        
        min_btn = QPushButton("─")
        min_btn.setFixedSize(28, 28)
        min_btn.setStyleSheet("""
            QPushButton {
                background-color: #11151f;
                color: #00e5ff;
                border: 1px solid #1f2737;
                font-size: 14px;
                font-weight: bold;
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: #162438;
                border: 1px solid #00d2ff;
                color: #ffffff;
            }
        """)
        min_btn.clicked.connect(self._animate_minimize_to_tray)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #11151f;
                color: #00e5ff;
                border: 1px solid #1f2737;
                font-size: 14px;
                font-weight: bold;
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: #c53030;
                border: 1px solid #ff4d4d;
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self._quit_app)
        
        top_bar.addWidget(min_btn)
        top_bar.addWidget(close_btn)
        main_layout.addLayout(top_bar)




        # 3. Free-floating File Cards Carousel & Clean Dropzone
        self.carousel = CarouselView(self)
        self.carousel.files_dropped.connect(self._add_files)
        self.carousel.file_removed.connect(self._on_file_removed)
        self.carousel.files_reordered.connect(self._on_files_reordered)
        self.carousel.upload_clicked.connect(self._open_file_dialog)
        self.carousel.clear_clicked.connect(self._clear_files)
        self.carousel.card_double_clicked.connect(lambda item: self._open_reader(item.file_path))
        main_layout.addWidget(self.carousel, 1)
        # Views are lazily constructed when accessed via properties to reduce startup memory
        self.tabs_bar.nlp_toggled.connect(self._on_nlp_toggled)

        self.action_bar = ActionBar(self)
        self.action_bar.action_triggered.connect(self._execute_action)
        self.action_bar.action_hovered.connect(self._on_action_hovered)
        self.carousel.drop_layout.insertWidget(1, self.action_bar)

        base_layout.addWidget(self.container_frame)
        self.setCentralWidget(central_widget)
        
        self.tray_icon = None
        if "--managed" not in sys.argv:
            # System Tray Integration
            self.tray_icon = QSystemTrayIcon(self)
            from core.app_icon import get_tray_icon
            tray_icon = get_tray_icon()
            if not tray_icon.isNull():
                self.tray_icon.setIcon(tray_icon)
            self.tray_icon.setToolTip("MNIME")
            
            self.tray_menu = QMenu(self)
            self.tray_menu.setStyleSheet("""
                QMenu {
                    background-color: #11151f;
                    color: #f0f6fc;
                    border: 1px solid #1f2737;
                }
                QMenu::item:selected {
                    background-color: #0077b6;
                }
            """)
            show_action = self.tray_menu.addAction("Show MNIME")
            show_action.triggered.connect(self._show_from_tray)
            
            self.startup_action = self.tray_menu.addAction("Run on Startup")
            self.startup_action.setCheckable(True)
            self.startup_action.setChecked(self._check_startup_enabled())
            self.startup_action.triggered.connect(self._toggle_startup)
            
            self.tray_menu.addSeparator()
            
            quit_action = self.tray_menu.addAction("Quit")
            quit_action.triggered.connect(self._quit_app)
            
            self.tray_icon.setContextMenu(self.tray_menu)
            self.tray_icon.activated.connect(self._on_tray_activated)
            self.tray_icon.show()
            
        # W1: If managed by the native tray, exit fully when hidden for 10 minutes to clear footprint.
        self.managed_exit_timer = QTimer(self)
        self.managed_exit_timer.setInterval(10 * 60 * 1000) # 10 minutes
        self.managed_exit_timer.timeout.connect(self._quit_app)
        
    def hideEvent(self, event):
        super().hideEvent(event)
        if "--managed" in sys.argv:
            self.managed_exit_timer.start()
            
    def showEvent(self, event):
        super().showEvent(event)
        if "--managed" in sys.argv:
            self.managed_exit_timer.stop()

    def _on_nlp_toggled(self, checked):
        if not checked and self._nlp_view is not None:
            self._nlp_view.clear_index()

    @property
    def output_view(self):
        if self._output_view is None:
            from ui.output_view import OutputView
            self._output_view = OutputView(self)
            self._output_view.start_over_clicked.connect(self._start_over)
            self._output_view.hide()
            self.container_frame.layout().addWidget(self._output_view, 1)
        return self._output_view

    @property
    def nlp_view(self):
        if self._nlp_view is None:
            from ui.nlp_view import NLPView
            self._nlp_view = NLPView(self)
            self._nlp_view.start_over_clicked.connect(self._start_over)
            self._nlp_view.hide()
            self.container_frame.layout().addWidget(self._nlp_view, 1)
        return self._nlp_view

    @property
    def particle_overlay(self):
        if self._particle_overlay is None:
            from ui.merge_particles import MergeParticleOverlay
            self._particle_overlay = MergeParticleOverlay(self)
        return self._particle_overlay

    def _on_reader_files_updated(self, paths):
        self._clear_files()
        self._add_files(paths)

    def _bring_to_foreground(self, widget):
        """Bring any widget or dialog to the absolute foreground on Windows 11."""
        if not widget:
            return
        try:
            widget.setWindowState(widget.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
            widget.show()
            widget.raise_()
            widget.activateWindow()
            if sys.platform == "win32":
                import ctypes
                hwnd = int(widget.winId())
                user32 = ctypes.windll.user32
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
        except Exception:
            pass

    def _open_reader(self, target_path: Optional[str] = None):
        from ui.reader_dialog import ReaderDialog

        # Normalize target_path in case a boolean or invalid arg was passed
        if not isinstance(target_path, str) or not target_path:
            target_path = self.file_items[0].file_path if self.file_items else None

        target_item = None
        if target_path and os.path.exists(target_path):
            abs_path = os.path.abspath(target_path)
            existing = [item for item in self.file_items if os.path.abspath(item.file_path) == abs_path]
            if existing:
                target_item = existing[0]
            else:
                new_item = FileItem(abs_path)
                self.file_items.append(new_item)
                self.carousel.set_items(self.file_items)
                self.action_bar.update_count(len(self.file_items))
                target_item = new_item

        initial_idx = 0
        if target_item and target_item in self.file_items:
            initial_idx = self.file_items.index(target_item)
        elif self.file_items:
            initial_idx = 0

        # If reader is already open, update it and bring to front
        if getattr(self, "_active_reader", None) is not None:
            try:
                self._active_reader.update_file_items(self.file_items, select_index=initial_idx)
                self._bring_to_foreground(self._active_reader)
                return
            except Exception:
                self._active_reader = None

        dialog = ReaderDialog(
            self.file_items, 
            parent=None, 
            update_callback=self._on_reader_files_updated,
            initial_index=initial_idx,
            crossref_callback=self._open_cross_reference,
        )
        self._active_reader = dialog
        dialog.finished.connect(lambda: setattr(self, "_active_reader", None))
        self._bring_to_foreground(dialog)

    # ------------------------------------------------------------------
    # Cross-referencing
    # ------------------------------------------------------------------

    CROSSREF_SOURCE_EXTS = (".pdf", ".txt", ".md", ".py", ".json", ".csv", ".js", ".ts", ".html", ".css", ".cpp", ".c", ".h", ".java")

    def _open_cross_reference(self, source_path: Optional[str] = None):
        """Open the cross-reference window for *source_path* (or the first usable file in the queue).

        Every other PDF/text file in the queue becomes a reference target.
        """
        from ui.document_viewer import DocumentViewer

        source_item = None
        if isinstance(source_path, str) and source_path:
            abs_path = os.path.abspath(source_path)
            source_item = next((i for i in self.file_items if os.path.abspath(i.file_path) == abs_path), None)
        if source_item is None:
            source_item = next((i for i in self.file_items if i.extension in self.CROSSREF_SOURCE_EXTS), None)

        if source_item is None:
            QMessageBox.information(
                self, "Cross-Reference",
                "Add a PDF or text document to MNIME first. It will be the source you highlight from."
            )
            return
        if source_item.extension not in self.CROSSREF_SOURCE_EXTS:
            QMessageBox.information(self, "Cross-Reference", "Cross-referencing works with PDFs and text documents.")
            return

        others = [i for i in self.file_items if i is not source_item and i.extension in self.CROSSREF_SOURCE_EXTS]
        if not others:
            QMessageBox.information(
                self, "Cross-Reference",
                "Add at least one more PDF or text document. MNIME compares the passage you "
                "highlight in the source against the other files in the queue."
            )
            return

        if self._active_crossref is not None:
            try:
                self._active_crossref.close()
            except RuntimeError:
                pass

        viewer = DocumentViewer(source_item, others, run_reference=self._run_reference, parent=None)
        self._active_crossref = viewer
        viewer.finished.connect(lambda: setattr(self, "_active_crossref", None))
        self._bring_to_foreground(viewer)

    def handle_external_open(self, file_paths: List[str]):
        """Handle opening files passed via CLI or IPC from an external process."""
        import urllib.parse
        cleaned = []
        for f in file_paths:
            if not f or not isinstance(f, str):
                continue
            s = f.strip(' \t\r\n"\'')
            if s.startswith("file:///"):
                s = urllib.parse.unquote(s[8:])
            elif s.startswith("file://"):
                s = urllib.parse.unquote(s[7:])
            s = os.path.normpath(s)
            from core.file_item import SUPPORTED_EXTENSIONS
            if os.path.isfile(s) and os.path.splitext(s)[1].lower() in SUPPORTED_EXTENSIONS:
                cleaned.append(os.path.abspath(s))

        if cleaned:
            # Synchronously register newly opened files into file_items
            existing_abs = {os.path.abspath(item.file_path) for item in self.file_items}
            for path in cleaned:
                if path not in existing_abs:
                    self.file_items.append(FileItem(path))
                    existing_abs.add(path)
            self.carousel.set_items(self.file_items)
            self.action_bar.update_count(len(self.file_items))
            self._open_reader(target_path=cleaned[0])
        else:
            self._bring_to_foreground(self)

    def _check_startup_enabled(self) -> bool:
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, "MNIME")
            winreg.CloseKey(key)
            return True
        except WindowsError:
            return False

    def _toggle_startup(self, checked: bool):
        import winreg, sys, os
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
            if checked:
                exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
                winreg.SetValueEx(key, "MNIME", 0, winreg.REG_SZ, f'"{exe_path}"')
            else:
                winreg.DeleteValue(key, "MNIME")
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Failed to set startup: {e}")

    def _show_from_tray(self):
        # Prevent double triggering
        if getattr(self, '_is_restoring', False):
            return
        self._is_restoring = True
        
        self.showNormal()
        self.activateWindow()
        self._is_restoring = False

    def _animate_minimize_to_tray(self):
        self.hide()

    def hideEvent(self, event):
        super().hideEvent(event)
        from PyQt6.QtCore import QTimer
        if not hasattr(self, '_idle_trim_timer'):
            self._idle_trim_timer = QTimer(self)
            self._idle_trim_timer.setSingleShot(True)
            self._idle_trim_timer.timeout.connect(self._do_idle_trim)
        self._idle_trim_timer.start(30000)

    def _do_idle_trim(self):
        from PyQt6.QtWidgets import QApplication
        if self.isVisible():
            return
        
        # Unload model if setting enabled
        from PyQt6.QtCore import QSettings
        if str(QSettings("MNIME", "MNIMEApp").value("nlp_idle_unload_tray", "true")).lower() == "true":
            try:
                from core.nlp_engine import NLPEngine
                NLPEngine.get_instance().unload_model()
            except Exception:
                pass
                
        # Are there other top-level windows open?
        for w in QApplication.topLevelWidgets():
            if w.isVisible() and w is not self and not w.inherits("QMenu") and not w.inherits("QToolTip"):
                # E.g. ReaderDialog is open
                return
                
        try:
            from core.idle_trim import trim_now, set_efficiency_mode
            trim_now()
            set_efficiency_mode(True)
        except Exception:
            pass

    def closeEvent(self, event):
        from PyQt6.QtWidgets import QApplication
        try:
            from core.system_cleaner import SystemCleaner
            SystemCleaner().on_app_exit()
        except Exception:
            pass
        QApplication.quit()
        event.accept()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick or reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_from_tray()

    def _on_mode_changed(self, mode: ToolMode):
        """Handle tab switching and update UI action text and badge."""
        # Launcher tab: opens the Reader without changing the active tool
        if mode == ToolMode.READER:
            target = self.file_items[0].file_path if self.file_items else None
            self._open_reader(target)
            return

        if mode != ToolMode.STATS:
            self.current_mode = mode
        if mode == ToolMode.COMBINE_PDF:
            self.action_bar.set_action_title("MERGE")
        elif mode == ToolMode.JPG_TO_PDF:
            self.action_bar.set_action_title("CONVERT TO PDF")
        elif mode == ToolMode.TXT_TO_PDF:
            self.action_bar.set_action_title("CONVERT TO PDF")
        elif mode == ToolMode.PDF_TO_JPG:
            self.action_bar.set_action_title("EXTRACT TO JPG")
        elif mode == ToolMode.COMPRESS_PDF:
            self.action_bar.set_action_title("COMPRESS")
        elif mode == ToolMode.PDF_TO_DOCX:
            self.action_bar.set_action_title("CONVERT TO DOCX")
        elif mode == ToolMode.SPLIT_PDF:
            self.action_bar.set_action_title("SPLIT")
        elif mode == ToolMode.EDIT_IMAGE:
            self.action_bar.set_action_title("EDIT")
        elif mode == ToolMode.NLP:
            self.action_bar.set_action_title("START NLP")
        elif mode == ToolMode.REFERENCE:
            self.action_bar.set_action_title("CROSS-REFERENCE")
        elif mode == ToolMode.BOOKMARK:
            self.action_bar.set_action_title("BOOKMARK")
        elif mode == ToolMode.STATS:
            from ui.nerds import StatsForNerdsDialog
            if getattr(self, "_stats_dialog", None) is None:
                self._stats_dialog = StatsForNerdsDialog(self)

            if self._stats_dialog.isVisible():
                if self._stats_dialog.isActiveWindow():
                    self._stats_dialog.hide()
                else:
                    self._stats_dialog.raise_()
                    self._stats_dialog.activateWindow()
            else:
                geo = self.geometry()
                diag_w, diag_h = self._stats_dialog.width(), self._stats_dialog.height()
                x = max(geo.x() + (geo.width() - diag_w) // 2, 40)
                y = max(geo.y() + (geo.height() - diag_h) // 2, 40)
                self._stats_dialog.move(x, y)
                self._stats_dialog.show()
                self._stats_dialog.raise_()
                self._stats_dialog.activateWindow()

            if self.current_mode in self.tabs_bar._buttons:
                self.tabs_bar._buttons[self.current_mode].setChecked(True)
            return

        self.action_bar.update_count(len(self.file_items))

        # Handle view switching
        if mode == ToolMode.NLP:
            from core.nlp_engine import NLPEngine
            engine = NLPEngine.get_instance()
            if not engine.is_loaded and not engine.is_loading:
                engine.check_model(auto_load=True)
            if not engine.is_loaded and not engine.is_loading:
                from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel
                from PyQt6.QtCore import Qt
                
                dialog = QDialog(self)
                dialog.setWindowTitle("Model Required")
                dialog.setFixedSize(450, 220)
                dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
                dialog.setStyleSheet("""
                    QDialog { background-color: #0b0f19; border: 2px solid #00d2ff; border-radius: 12px; }
                    QLabel { color: #f0f6fc; font-size: 14px; }
                    QLabel#title { color: #00e5ff; font-size: 18px; font-weight: bold; }
                    QPushButton { background-color: #162438; color: #00e5ff; border: 1px solid #00d2ff; border-radius: 6px; padding: 8px 24px; font-weight: bold; font-size: 14px; }
                    QPushButton:hover { background-color: #0077b6; color: #ffffff; }
                """)
                
                layout = QVBoxLayout(dialog)
                layout.setContentsMargins(30, 30, 30, 30)
                layout.setSpacing(15)
                
                title = QLabel("NLP Model Required")
                title.setObjectName("title")
                title.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(title)
                
                msg = QLabel(f"The bundled MNIME model could not be loaded.\n\n{engine.error}")
                msg.setWordWrap(True)
                msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(msg)
                
                layout.addStretch()
                
                btn_layout = QHBoxLayout()
                btn_layout.addStretch()
                ok_btn = QPushButton("OK")
                from ui.cursor_fx import get_custom_cursor
                ok_btn.setCursor(get_custom_cursor())
                ok_btn.clicked.connect(dialog.accept)
                btn_layout.addWidget(ok_btn)
                btn_layout.addStretch()
                layout.addLayout(btn_layout)
                
                dialog.exec()
                
                # Fix TabsBar state mismatch
                self.tabs_bar.current_mode = ToolMode.COMBINE_PDF
                self.tabs_bar._buttons[ToolMode.COMBINE_PDF].setChecked(True)
                self._on_mode_changed(ToolMode.COMBINE_PDF)
                return
                
            is_nlp_active = self.nlp_view.vectorstore is not None or (hasattr(self.nlp_view, 'worker') and self.nlp_view.worker.isRunning())
            if is_nlp_active:
                self.carousel.hide()
                self.action_bar.hide()
                self.output_view.hide()
                self.nlp_view.show()
            else:
                self.nlp_view.hide()
                if not self.output_view.isVisible():
                    self.carousel.show()
                    self.action_bar.show()
        else:
            self.nlp_view.hide()
            if not self.output_view.isVisible():
                self.carousel.show()
                self.action_bar.show()

    def _get_file_filters(self) -> str:
        """Return file dialog filter based on active tool mode."""
        if self.current_mode == ToolMode.COMBINE_PDF:
            return "Documents & Images (*.pdf *.jpg *.jpeg *.png *.webp *.bmp *.txt);;PDF Files (*.pdf);;Text Files (*.txt);;Images (*.jpg *.png);;All Files (*.*)"
        elif self.current_mode in [ToolMode.JPG_TO_PDF, ToolMode.EDIT_IMAGE]:
            return "Images (*.jpg *.jpeg *.png *.webp *.bmp);;All Files (*.*)"
        elif self.current_mode == ToolMode.TXT_TO_PDF:
            return "Text Files (*.txt);;All Files (*.*)"
        elif self.current_mode in [ToolMode.PDF_TO_JPG, ToolMode.COMPRESS_PDF, ToolMode.PDF_TO_DOCX, ToolMode.SPLIT_PDF, ToolMode.BOOKMARK, ToolMode.NLP]:
            return "PDF Files (*.pdf);;All Files (*.*)"
        elif self.current_mode == ToolMode.REFERENCE:
            return "Documents (*.pdf *.txt *.md);;PDF Files (*.pdf);;Text Files (*.txt *.md);;All Files (*.*)"
        return "All Files (*.*)"

    def _open_file_dialog(self):
        """Open custom file explorer with built-in semantic search."""
        from .file_dialog import CustomFileDialog
        dialog = CustomFileDialog(self)
        if dialog.exec():
            files = dialog.selected_files
            if files:
                self._add_files(files)

    MAX_FILE_LIMIT = 5000

    def _add_files(self, paths: List[str]):
        """Add newly selected files to the queue, recursively expanding any dropped folders asynchronously."""
        import re
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

        expanded_paths = []
        for p in paths:
            if not p:
                continue
            p = os.path.normpath(p)
            if os.path.isdir(p):
                for root, _, files in os.walk(p):
                    for f in sorted(files, key=natural_sort_key):
                        expanded_paths.append(os.path.join(root, f))
            elif os.path.isfile(p):
                expanded_paths.append(p)

        if not expanded_paths:
            return

        expanded_paths = sorted(expanded_paths, key=natural_sort_key)
        
        # Disable UI components during load to prevent duplicate drops
        self.action_bar.action_btn.setEnabled(False)
        self.action_bar.show_progress(0, "Scanning files...")

        existing_paths = {item.file_path for item in self.file_items}
        
        def _load_batch_task(progress_callback=None):
            new_items = []
            added = 0
            total = len(expanded_paths)
            current_count = len(self.file_items)
            
            for i, path in enumerate(expanded_paths):
                if current_count + added >= self.MAX_FILE_LIMIT:
                    break
                    
                if progress_callback and i % 5 == 0:
                    progress_callback(int((i / total) * 100), f"Loading metadata {i+1}/{total}...")
                    
                if path in existing_paths:
                    continue
                    
                try:
                    item = FileItem(path)
                    new_items.append(item)
                    existing_paths.add(path)
                    added += 1
                except Exception:
                    log.exception("Could not load file metadata: %s", path)
            return new_items

        def _on_load_finished(new_items):
            self.action_bar.hide_progress()
            self.action_bar.action_btn.setEnabled(True)
            
            if new_items:
                self.file_items.extend(new_items)
                self.carousel.set_items(self.file_items)
                self.action_bar.update_count(len(self.file_items))
                
            if len(self.file_items) > 5000:
                QMessageBox.information(
                    self,
                    "Batch Limit",
                    "Queue exceeded maximum capacity of 5000 files.\nPlease remove some files or process in batches."
                )

        def _on_load_error(err):
            self.action_bar.hide_progress()
            self.action_bar.action_btn.setEnabled(True)
            log.error("Error loading files: %s", err)

        # Reuse TaskWorker for background loading
        self._load_worker = TaskWorker(_load_batch_task)
        self._load_worker.progress.connect(self._on_worker_progress)
        self._load_worker.finished.connect(_on_load_finished)
        self._load_worker.error.connect(_on_load_error)
        self._load_worker.start()

    def _clear_files(self):
        """Clear all files from the queue and reset the view."""
        self.file_items.clear()
        self._crossref_index_cache.clear()
        self.carousel.set_items(self.file_items)
        self.action_bar.update_count(0)
        self.action_bar.hide_progress()
        self.output_view.hide()
        self.carousel.show()
        self.action_bar.show()
        if hasattr(self, 'particle_overlay'):
            self.particle_overlay.clear_all()

    def _on_file_removed(self, item: FileItem):
        self._crossref_index_cache.clear()
        self.action_bar.update_count(len(self.file_items))

    def _on_files_reordered(self):
        # Update references
        self.file_items = self.carousel.file_items

    def _on_action_hovered(self, is_hovered: bool, global_pos: QPoint):
        """Start or stop pulling file particles into the merge button on hover."""
        if not hasattr(self, 'particle_overlay'):
            return

        # Crucial: the merge particle animation must ONLY occur on the file selection screen (carousel visible),
        # NEVER on the merge result screen (output_view visible).
        if hasattr(self, 'output_view') and self.output_view.isVisible():
            self.particle_overlay.clear_all()
            return
        if hasattr(self, 'carousel') and not self.carousel.isVisible():
            self.particle_overlay.clear_all()
            return

        if is_hovered and self.file_items:
            # Particle Physics Throttling: Disable simulation for extreme batch sizes to maintain 60 FPS
            if len(self.file_items) > 100:
                self.particle_overlay.stop_hover_pull()
                return

            local_pos = self.mapFromGlobal(global_pos)
            if self.particle_overlay.hover_active:
                self.particle_overlay.update_target_pos(local_pos)
            else:
                self.particle_overlay.start_hover_pull(local_pos)
        else:
            self.particle_overlay.stop_hover_pull()

    def _execute_action(self):
        """Execute the primary operation depending on active tab."""
        if not self.file_items:
            if self.current_mode == ToolMode.REFERENCE:
                self._open_cross_reference()
                return
            QMessageBox.warning(self, "No Files", "Please add at least one document before running this tool.")
            return

        single_file_modes = [ToolMode.PDF_TO_JPG, ToolMode.SPLIT_PDF, ToolMode.COMPRESS_PDF, ToolMode.PDF_TO_DOCX, ToolMode.BOOKMARK, ToolMode.NLP]
        if self.current_mode in single_file_modes and len(self.file_items) > 1:
            QMessageBox.information(
                self,
                "Batch Limit",
                f"{self.current_mode.value} only processes one file at a time. Only the first file ({self.file_items[0].file_name}) will be processed."
            )

        if self.current_mode == ToolMode.COMBINE_PDF and len(self.file_items) < 2:
            QMessageBox.warning(self, "Not Enough Files", "Please add at least two files to merge.")
            return

        pdf_modes = [ToolMode.SPLIT_PDF, ToolMode.COMPRESS_PDF, ToolMode.PDF_TO_DOCX, ToolMode.BOOKMARK, ToolMode.PDF_TO_JPG]
        if self.current_mode in pdf_modes:
            if not self.file_items[0].file_path.lower().endswith('.pdf'):
                QMessageBox.warning(self, "Invalid File Type", f"{self.current_mode.value} requires a PDF file.")
                return
                
        image_modes = [ToolMode.JPG_TO_PDF]
        if self.current_mode in image_modes:
            valid_exts = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
            if not all(item.file_path.lower().endswith(valid_exts) for item in self.file_items):
                QMessageBox.warning(self, "Invalid File Type", f"{self.current_mode.value} only supports image files (JPG, PNG, WEBP, BMP).")
                return
                
        if self.current_mode == ToolMode.EDIT_IMAGE:
            valid_exts = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.pdf')
            if not all(item.file_path.lower().endswith(valid_exts) for item in self.file_items):
                QMessageBox.warning(self, "Invalid File Type", f"EDIT only supports images and PDFs.")
                return
                
        txt_modes = [ToolMode.TXT_TO_PDF]
        if self.current_mode in txt_modes:
            valid_exts = ('.txt',)
            if not all(item.file_path.lower().endswith(valid_exts) for item in self.file_items):
                QMessageBox.warning(self, "Invalid File Type", f"{self.current_mode.value} only supports text files (TXT).")
                return

        # Trigger hyper-speed collapse of file particles into the merge button center!
        if hasattr(self, 'particle_overlay'):
            interactive_modes = {ToolMode.EDIT_IMAGE, ToolMode.NLP, ToolMode.REFERENCE}
            if self.current_mode not in interactive_modes:
                if len(self.file_items) <= 100:
                    self.particle_overlay.trigger_hyper_collapse()
            else:
                self.particle_overlay.clear_all()

        if self.current_mode == ToolMode.EDIT_IMAGE:
            for item in self.file_items:
                if item.file_path.lower().endswith('.pdf'):
                    from ui.pdf_editor import PDFEditorDialog
                    dialog = PDFEditorDialog(item, self)
                    dialog.exec()
                else:
                    from ui.image_editor import ImageEditorDialog
                    dialog = ImageEditorDialog(item, self)
                    dialog.exec()
                # Clear cached thumbnail so it redraws
                item.thumbnail_bytes = None
                item._cached_pixmap = None
            
            self.carousel.refresh_view()
            return
            
        if self.current_mode == ToolMode.NLP:
            self.carousel.hide()
            self.action_bar.hide()
            self.nlp_view.show()
            self.nlp_view.start_indexing([self.file_items[0]])
            return
            
        if self.current_mode == ToolMode.REFERENCE:
            self._open_cross_reference()
            return

        temp_dir = self._new_temp_dir()

        from core.pdf_engine import PDFEngine

        if self.current_mode == ToolMode.COMBINE_PDF:
            output_file = os.path.join(temp_dir, "MNIME_merged.pdf")
            self._start_task(target=PDFEngine.combine_files, file_items=self.file_items, output_path=output_file)
        elif self.current_mode == ToolMode.JPG_TO_PDF:
            output_file = os.path.join(temp_dir, "MNIME_converted.pdf")
            self._start_task(target=PDFEngine.convert_jpg_to_pdf, image_items=self.file_items, output_path=output_file)
        elif self.current_mode == ToolMode.TXT_TO_PDF:
            output_file = os.path.join(temp_dir, "MNIME_txt_converted.pdf")
            # Reuse the high-speed combine_files which already handles .txt merging & conversion
            self._start_task(target=PDFEngine.combine_files, file_items=self.file_items, output_path=output_file)
        elif self.current_mode == ToolMode.PDF_TO_JPG:
            output_dir = os.path.join(temp_dir, "MNIME_jpg_export")
            os.makedirs(output_dir, exist_ok=True)
            self._start_task(target=PDFEngine.convert_pdf_to_jpg, pdf_item=self.file_items[0], output_dir=output_dir, dpi=200)
            self.temp_dir_to_zip = output_dir
        elif self.current_mode == ToolMode.SPLIT_PDF:
            output_dir = os.path.join(temp_dir, "MNIME_split_export")
            os.makedirs(output_dir, exist_ok=True)
            self._start_task(target=PDFEngine.split_pdf, pdf_item=self.file_items[0], output_dir=output_dir)
            self.temp_dir_to_zip = output_dir
        elif self.current_mode == ToolMode.COMPRESS_PDF:
            base_name = os.path.splitext(self.file_items[0].file_name)[0]
            output_file = os.path.join(temp_dir, f"{base_name}_compressed.pdf")
            self._start_task(target=PDFEngine.compress_pdf, pdf_item=self.file_items[0], output_path=output_file)
        elif self.current_mode == ToolMode.PDF_TO_DOCX:
            base_name = os.path.splitext(self.file_items[0].file_name)[0]
            output_file = os.path.join(temp_dir, f"{base_name}.docx")
            self._start_task(target=PDFEngine.convert_pdf_to_docx, pdf_item=self.file_items[0], output_path=output_file)
        elif self.current_mode == ToolMode.BOOKMARK:
            base_name = os.path.splitext(self.file_items[0].file_name)[0]
            output_file = os.path.join(temp_dir, f"{base_name}_bookmarked.pdf")
            self._start_task(target=PDFEngine.bookmark, pdf_item=self.file_items[0], output_path=output_file)

    # ------------------------------------------------------------------
    # Temp directory + worker lifecycle
    # ------------------------------------------------------------------

    def _new_temp_dir(self) -> str:
        """Create a unique per-job working directory and discard the previous jobs' output."""
        if not (self.worker is not None and self.worker.isRunning()):
            self._cleanup_temp_dirs()
        root = tempfile.mkdtemp(prefix="MNIME_")
        self._temp_roots.append(root)
        return root

    def _cleanup_temp_dirs(self):
        for root in self._temp_roots:
            shutil.rmtree(root, ignore_errors=True)
        self._temp_roots.clear()

    def _any_worker_running(self) -> bool:
        return any(
            w is not None and w.isRunning()
            for w in (self.worker, self._reference_worker, self._load_worker)
        )

    def _save_session(self):
        """Save current file queue to session.json."""
        try:
            base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".mnime")
            session_path = os.path.join(base, "MNIME", "session.json")
            os.makedirs(os.path.dirname(session_path), exist_ok=True)
            # Dump the files when the program closes by not saving them to the session
            import json
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump({"files": []}, f)
        except Exception as e:
            log.exception("Failed to save session: %s", e)
            
    def _restore_session(self):
        """Restore file queue from session.json."""
        try:
            base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".mnime")
            session_path = os.path.join(base, "MNIME", "session.json")
            if os.path.exists(session_path):
                import json
                with open(session_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                files = data.get("files", [])
                if files:
                    self.handle_external_open(files)
        except Exception as e:
            log.exception("Failed to restore session: %s", e)

    def _quit_app(self):
        """Cancel and join background work, remove temp output, then exit."""
        self._save_session()
        for w in (self.worker, self._reference_worker, self._load_worker):
            if w is not None and w.isRunning():
                w.cancel()
                if not w.wait(5000):
                    log.warning("Worker did not stop in time; terminating")
                    w.terminate()
                    w.wait(1000)
        self._cleanup_temp_dirs()
        QApplication.instance().quit()

    def _start_task(self, target, **kwargs):
        """Starts worker thread and connects UI feedback signals."""
        if self.worker is not None and self.worker.isRunning():
            log.warning("Ignored start request: a task is already running")
            return

        self.action_bar.action_btn.setEnabled(False)
        self.action_bar.show_progress(0, "Processing task...")

        self.worker = TaskWorker(target, **kwargs)
        self.worker.progress.connect(self._on_worker_progress)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.error.connect(self._on_worker_error)
        
        # Delay the actual start of the intensive worker thread to guarantee 
        # that the cinematic particle collapse animation finishes rendering at 
        # 60 FPS without being starved by Python's Global Interpreter Lock (GIL).
        from PyQt6.QtCore import QTimer
        worker = self.worker
        QTimer.singleShot(1000, worker.start)

    def _run_reference(self, text: str, viewer: DocumentViewer):
        """Search the viewer's reference files for *text* and ask the NLP model for a comparative brief."""
        if self._reference_worker is not None and self._reference_worker.isRunning():
            return  # A synthesis is already in flight

        other_files = list(viewer.reference_items)
        cache_key = tuple(sorted(os.path.abspath(f.file_path) for f in other_files))
        cache = self._crossref_index_cache

        def _reference_task(progress_callback=None):
            if not other_files:
                return "No other documents available to reference against."

            from core.search_engine import SearchEngine
            from PyQt6.QtCore import QSettings

            vectorstore = cache.get(cache_key)
            if vectorstore is None:
                settings = QSettings("MNIME", "MNIMEApp")
                smart_sampling = str(settings.value("nlp_smart_indexing", "true")).lower() == "true"
                vectorstore = SearchEngine.build_index(
                    other_files, use_smart_sampling=smart_sampling, progress_callback=progress_callback
                )
                cache.clear()  # keep only the most recent file set in memory
                cache[cache_key] = vectorstore

            if progress_callback:
                progress_callback(96, "Finding related passages...")
            passages = SearchEngine.search(vectorstore, text, k=5)

            from core.nlp_engine import NLPEngine
            nlp = NLPEngine.get_instance()
            if progress_callback:
                progress_callback(98, "Loading NLP model..." if not nlp.is_loaded else "Writing comparative brief...")
            nlp.check_model(auto_load=True)
            if not nlp.is_loaded:
                return {
                    "brief": "",
                    "passages": passages,
                    "note": f"NLP model unavailable ({nlp.error}). Showing the matching passages only.",
                }
            if progress_callback:
                progress_callback(99, "Writing comparative brief...")
            brief = nlp.synthesize_reference(text, passages)
            return {"brief": brief, "passages": passages}

        self.action_bar.show_progress(0, "Cross-referencing...")
        self._reference_worker = TaskWorker(_reference_task)
        self._reference_worker.progress.connect(lambda pct, msg: self._on_reference_progress(pct, msg, viewer))
        self._reference_worker.finished.connect(lambda res: self._on_reference_finished(res, viewer))
        self._reference_worker.error.connect(lambda err: self._on_reference_finished(f"Error: {err}", viewer))
        self._reference_worker.start()

    def _on_reference_progress(self, pct: int, msg: str, viewer: DocumentViewer):
        self.action_bar.show_progress(pct, msg)
        try:
            viewer.set_progress(pct, msg)
        except RuntimeError:
            pass  # viewer window was closed

    def _on_reference_finished(self, result, viewer: DocumentViewer):
        self.action_bar.hide_progress()
        try:
            viewer.set_result(result)
        except RuntimeError:
            pass  # viewer window was closed

    def _on_worker_progress(self, pct: int, msg: str):
        self.action_bar.show_progress(pct, msg)

    def _on_worker_finished(self, result):
        self.action_bar.action_btn.setEnabled(True)
        self.action_bar.show_progress(100, "Completed successfully!")
        
        final_result = result
        # If PDF to JPG or Split PDF, pass the output directory instead of the list of files or a zip
        if self.current_mode in [ToolMode.PDF_TO_JPG, ToolMode.SPLIT_PDF] and hasattr(self, 'temp_dir_to_zip'):
            final_result = self.temp_dir_to_zip

        def perform_screen_swap():
            self.carousel.hide()
            self.action_bar.hide()
            self.output_view.show_output(final_result)
            if hasattr(self, 'particle_overlay'):
                self.particle_overlay.clear_all()

        # Trigger dramatic cinematic flash & shockwave transition into the merge screen!
        if hasattr(self, 'particle_overlay'):
            btn_center = self.action_bar.action_btn.mapTo(self, self.action_bar.action_btn.rect().center())
            self.particle_overlay.trigger_dramatic_flash(btn_center, on_peak_callback=perform_screen_swap)
        else:
            perform_screen_swap()

    def _on_worker_error(self, err_msg: str):
        self.action_bar.action_btn.setEnabled(True)
        self.action_bar.hide_progress()
        QMessageBox.critical(self, "Processing Error", f"An error occurred during processing:\n{err_msg}")
        if hasattr(self, 'particle_overlay'):
            self.particle_overlay.clear_all()

    def _start_over(self):
        self._clear_files()
        self.output_view.hide()
        self.nlp_view.clear_index()
        self.nlp_view.hide()
        self.carousel.show()
        self.action_bar.show()
        self.action_bar.hide_progress()
        if hasattr(self, 'particle_overlay'):
            self.particle_overlay.clear_all()
