from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QMessageBox, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QSplitter, QTreeWidget, QTreeWidgetItem, QComboBox, QWidget,
    QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QRectF, QPoint, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QPen, QImage
import os


class ReaderPageView(QGraphicsView):
    prev_page_requested = pyqtSignal()
    next_page_requested = pyqtSignal()
    zoom_changed = pyqtSignal()  # emitted after a zoom so the dialog can re-render

    # Base render DPI: 96 screen DPI * this factor = render resolution
    BASE_DPI = 96.0

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )
        self.current_page = None
        # _render_scale tracks the pymupdf matrix scale used for the current pixmap
        self._render_scale = 1.0
        self.scale(1.0, 1.0)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_render_scale(self) -> float:
        """Return the pymupdf render scale that will produce 1 rendered pixel
        per screen pixel at the current view zoom level, clamped to a
        sensible minimum so pages are never blurry."""
        # m11() is the horizontal scale factor of the current view transform
        view_scale = self.transform().m11()
        # We need to cancel out any pre-existing render scale so the new
        # pixmap sits at scene-coordinate size == PDF point size.
        # render_scale controls how many pixels pymupdf produces per PDF point.
        # A scale of 1.0 gives 72 DPI; multiply by view_scale to hit screen pixels.
        scale = view_scale * (self.BASE_DPI / 72.0)
        # Never render below 1x (72 DPI) — keeps text legible even when
        # zoomed way out, and avoids re-renders for trivial zoom changes.
        return max(scale, 1.0)

    def set_page(self, page, pixmap, render_scale: float = 1.0, fit_view: bool = True, clip=None):
        """Display *pixmap* (rendered at *render_scale* px/pt) for *page*."""
        self.current_page = page
        self._render_scale = render_scale
        self.scene().clear()
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        # Scale the item so that 1 scene unit == 1 PDF point regardless of
        # how many pixels pymupdf put in the bitmap.
        if page:
            inv = 1.0 / (render_scale / self.devicePixelRatioF()) if render_scale > 0 else 1.0
            self.pixmap_item.setScale(inv)
            if clip:
                self.pixmap_item.setPos(clip.x0, clip.y0)
            self.scene().addItem(self.pixmap_item)
            # Scene rect in PDF-point coordinates always matches the full page
            self.scene().setSceneRect(QRectF(0, 0, page.rect.width, page.rect.height))
        else:
            self.pixmap_item.setScale(1.0)
            self.scene().addItem(self.pixmap_item)
            self.scene().setSceneRect(QRectF(0, 0, pixmap.width() / pixmap.devicePixelRatio(), pixmap.height() / pixmap.devicePixelRatio()))

        if fit_view:
            QTimer.singleShot(10, self._fit_to_view)

    def _fit_to_view(self):
        if self.scene() and not self.scene().sceneRect().isEmpty():
            self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self.scale(0.95, 0.95)
            # After fitting, request a re-render at the correct resolution
            self.zoom_changed.emit()

    def wheelEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                factor = 1.15
            else:
                factor = 1 / 1.15
            self.scale(factor, factor)
            self.zoom_changed.emit()
        else:
            v_bar = self.verticalScrollBar()
            
            can_scroll_vert = v_bar.isVisible() and v_bar.maximum() > v_bar.minimum()
            
            if can_scroll_vert:
                super().wheelEvent(event)
                return
                
            if event.angleDelta().y() > 0:
                self.prev_page_requested.emit()
            elif event.angleDelta().y() < 0:
                self.next_page_requested.emit()
            event.accept()

class ReaderDialog(QDialog):
    def __init__(self, file_items, parent=None, update_callback=None, initial_index: int = 0, crossref_callback=None):
        super().__init__(parent)
        self.update_callback = update_callback
        self.crossref_callback = crossref_callback
        self.file_items = file_items
        self.setWindowTitle("MNIME - READER")
        self.setMinimumSize(800, 600)
        self.resize(1200, 900)
        
        # Frameless dark metallic UI
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        self.doc = None
        self.page_idx = 0
        self._drag_pos = None
        
        # Match MNIME styling
        self.setStyleSheet("""
            ReaderDialog { background: transparent; }
            QWidget { color: #f0f6fc; }
            QPushButton { 
                background-color: #162438; color: #00e5ff; 
                border: 1px solid #00d2ff; border-radius: 6px; 
                padding: 6px 12px; font-weight: bold; 
            }
            QPushButton:hover { background-color: #0077b6; color: #ffffff; }
            QLabel { color: #8b949e; font-size: 13px; }
            QComboBox { 
                background-color: #161b22; color: #f0f6fc; 
                border: 1px solid #30363d; border-radius: 4px; padding: 4px; 
            }
            QTreeWidget { 
                background-color: #0a0d14; color: #c9d1d9; 
                border: 1px solid #1f2737; border-radius: 6px; padding: 5px; 
            }
            QTreeWidget::item:selected { background-color: #162438; color: #00d2ff; }
            QSplitter::handle { background-color: #1f2737; }
        """)
        
        self._setup_ui()
        if self.file_items:
            idx = min(max(0, initial_index), len(self.file_items) - 1)
            self.file_combo.setCurrentIndex(idx)
            self._on_file_selected(idx)
        else:
            self.page_label.setText("No external data loaded. Inject files to begin.")

    def _setup_ui(self):
        central_layout = QVBoxLayout(self)
        central_layout.setContentsMargins(10, 10, 10, 10)
        
        class WatermarkFrame(QFrame):
            def paintEvent(self, event):
                super().paintEvent(event)
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
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
        
        central_layout.addWidget(self.container_frame)
        
        self.setMouseTracking(True)
        self.container_frame.setMouseTracking(True)
        
        main_layout = QVBoxLayout(self.container_frame)
        main_layout.setContentsMargins(16, 8, 16, 16)
        main_layout.setSpacing(8)
        
        # Unified Tools & Title Bar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 10)
        
        title_label = QLabel("READER")
        title_label.setStyleSheet("color: #00d2ff; font-family: 'Segoe UI Black'; font-weight: 900; font-size: 14px; letter-spacing: 1px;")
        
        # Floating Close Button matching MNIME Theme
        self.close_btn = QPushButton("✕", self.container_frame)
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #162438;
                color: #00e5ff;
                border: 1px solid #00d2ff;
                border-radius: 16px;
                font-size: 16px;
                font-weight: 900;
            }
            QPushButton:hover {
                background-color: #00d2ff;
                color: #000000;
            }
        """)
        self.close_btn.clicked.connect(self.close)
        
        self.file_combo = QComboBox()
        self.file_combo.setMaximumWidth(800)
        for item in self.file_items:
            self.file_combo.addItem(item.file_name, item)
        self.file_combo.currentIndexChanged.connect(self._on_file_selected)
        
        self.add_files_btn = QPushButton("Add Files")
        self.add_files_btn.clicked.connect(self._open_file_dialog)
        
        self.print_btn = QPushButton("Print Document")
        self.print_btn.clicked.connect(self._print_document)
        
        top_bar.addWidget(title_label)
        top_bar.addSpacing(20)
        top_bar.addWidget(QLabel("Select File:"))
        top_bar.addWidget(self.file_combo)
        top_bar.addStretch()
        top_bar.addWidget(self.add_files_btn)
        top_bar.addWidget(self.print_btn)
        top_bar.addSpacing(15)
        top_bar.addWidget(self.close_btn)
        
        main_layout.addLayout(top_bar)
        
        # Splitter for Side Pane (Bookmarks/TOC) and Viewer
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: TOC
        left_widget = QTreeWidget()
        left_widget.setHeaderHidden(True)
        self.toc_tree = left_widget
        self.toc_tree.itemClicked.connect(self._on_toc_clicked)
        splitter.addWidget(left_widget)
        
        # Right: Viewer
        right_widget = QWidget() # simple container
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scene = QGraphicsScene(self)
        self.view = ReaderPageView(self.scene, self)
        self.view.setStyleSheet("background-color: #0a0d14; border: 1px solid #1f2737;")
        self.view.prev_page_requested.connect(self._prev_page)
        self.view.next_page_requested.connect(self._next_page)
        self.view.zoom_changed.connect(self._on_zoom_changed)
        right_layout.addWidget(self.view, 1)
        
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
        right_layout.addLayout(nav_layout)
        splitter.addWidget(right_widget)
        splitter.setSizes([250, 800])
        main_layout.addWidget(splitter, 1)

        self.installEventFilter(self)

    def _open_file_dialog(self):
        from ui.file_dialog import CustomFileDialog
        dialog = CustomFileDialog(self)
        if dialog.exec():
            selected = dialog.selected_files
            if selected:
                if self.update_callback:
                    self.update_callback(selected)
                    
                    self.file_combo.blockSignals(True)
                    self.file_combo.clear()
                    for item in self.file_items:
                        self.file_combo.addItem(item.file_name, item)
                    self.file_combo.blockSignals(False)
                    
                    if self.file_items:
                        self.file_combo.setCurrentIndex(0)
                        self._on_file_selected(0)
                    else:
                        self.scene.clear()
                        self.doc = None

    def _on_file_selected(self, index):
        if index < 0 or index >= len(self.file_items):
            return
        item = self.file_items[index]
        self._load_doc(item)

    def update_file_items(self, file_items, select_index: int = 0):
        """Update loaded file list dynamically without reopening the dialog."""
        self.file_items = file_items
        self.file_combo.blockSignals(True)
        self.file_combo.clear()
        for item in self.file_items:
            self.file_combo.addItem(item.file_name, item)
        self.file_combo.blockSignals(False)
        if self.file_items:
            idx = min(max(0, select_index), len(self.file_items) - 1)
            self.file_combo.setCurrentIndex(idx)
            self._on_file_selected(idx)
        else:
            if self.doc:
                try:
                    self.doc.close()
                except Exception:
                    pass
                self.doc = None
            self.scene.clear()
            self.toc_tree.clear()
            self.page_label.setText("No external data loaded. Inject files to begin.")

    def _load_doc(self, file_item):
        if self.doc:
            try:
                self.doc.close()
            except:
                pass
            self.doc = None
        
        self.toc_tree.clear()
        
        if file_item.extension == ".pdf":
            try:
                import pymupdf
                self.doc = pymupdf.open(file_item.file_path)
                self.page_idx = 0
                self._load_toc()
                self._render_page()
            except Exception as e:
                QMessageBox.critical(self, "Neural Interface Issue", f"Failed to access cognitive data: {e}")
        elif file_item.extension == ".txt":
            pdf_path = file_item.file_path + ".pdf"
            if not os.path.exists(pdf_path) or os.path.getmtime(pdf_path) < os.path.getmtime(file_item.file_path):
                try:
                    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                    from reportlab.lib.pagesizes import letter
                    from reportlab.lib.colors import HexColor
                    
                    def draw_background(canvas, doc):
                        canvas.saveState()
                        canvas.setFillColor(HexColor("#0a0d14"))
                        canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=1, stroke=0)
                        canvas.restoreState()
                    
                    doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                                            leftMargin=50, rightMargin=50,
                                            topMargin=50, bottomMargin=50)
                    styles = getSampleStyleSheet()
                    
                    mnime_style = ParagraphStyle(
                        'MNIMEStyle',
                        parent=styles["Normal"],
                        fontName='Helvetica',
                        fontSize=11,
                        textColor=HexColor("#00e5ff"),
                        leading=16,
                    )
                    
                    with open(file_item.file_path, 'r', encoding='utf-8', errors='replace') as f:
                        text = f.read()
                        
                    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    paragraphs = text.split('\n')
                    story = []
                    for p in paragraphs:
                        if p.strip():
                            story.append(Paragraph(p, mnime_style))
                        else:
                            story.append(Spacer(1, 12))
                            
                    doc.build(story, onFirstPage=draw_background, onLaterPages=draw_background)
                except Exception as e:
                    QMessageBox.critical(self, "Neural Interface Issue", f"Synthesis conversion failed: {e}")
                    return
            try:
                import pymupdf
                self.doc = pymupdf.open(pdf_path)
                self.page_idx = 0
                self._load_toc()
                self._render_page()
            except Exception as e:
                QMessageBox.critical(self, "Neural Interface Issue", f"Failed to render generated sequence: {e}")
        elif file_item.extension in [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"]:
            self.page_label.setText("Image")
            # Retina Image Loading
            image = QImage(file_item.file_path)
            # Make the image appear twice as sharp on high DPI screens
            image.setDevicePixelRatio(self.view.devicePixelRatioF())
            pixmap = QPixmap.fromImage(image)
            self.view.set_page(None, pixmap)
        else:
            self.page_label.setText("Data format unrecognized. Cognitive rendering offline.")
            self.scene.clear()

    def _load_toc(self):
        if not self.doc: return
        try:
            toc = self.doc.get_toc()
            # toc format: [level, title, page, ...]
            # We'll construct a tree
            items_by_level = {}
            for item in toc:
                level, title, page = item[:3]
                tree_item = QTreeWidgetItem([title])
                tree_item.setData(0, Qt.ItemDataRole.UserRole, page - 1) # 0-indexed page
                
                if level == 1:
                    self.toc_tree.addTopLevelItem(tree_item)
                else:
                    parent = items_by_level.get(level - 1)
                    if parent:
                        parent.addChild(tree_item)
                    else:
                        self.toc_tree.addTopLevelItem(tree_item)
                        
                items_by_level[level] = tree_item
            
            if not toc:
                self.toc_tree.addTopLevelItem(QTreeWidgetItem(["No Bookmarks Found"]))
        except:
            pass

    def _on_toc_clicked(self, item, col):
        page = item.data(0, Qt.ItemDataRole.UserRole)
        if page is not None and self.doc:
            self.page_idx = page
            self._render_page()

    def _render_page(self, render_scale: float | None = None, fit_view: bool = True):
        """Render the current page at *render_scale* px/pt.

        If *render_scale* is None the method picks a sensible default:
        - On first call (before any fit-to-view has happened) we use the
          view's physical pixel width divided by the PDF page width in points
          so the initial bitmap exactly matches the available screen pixels.
        - After fit-to-view the zoom_changed signal triggers a re-render with
          the precise scale from get_render_scale().
        """
        if not self.doc or self.page_idx < 0 or self.page_idx >= len(self.doc):
            return
        self.page_label.setText(f"Page {self.page_idx + 1} of {len(self.doc)}")

        page = self.doc[self.page_idx]
        from core.render_utils import render_page
        from PyQt6.QtWidgets import QApplication

        # If fit_view is true, this is an initial render, set transform to identity
        if fit_view:
            self.view.resetTransform()
            viewer_w = max(self.view.viewport().width(), 1)
            viewer_h = max(self.view.viewport().height(), 1)
            scale_w = viewer_w / max(page.rect.width, 1)
            scale_h = viewer_h / max(page.rect.height, 1)
            self.view.scale(min(scale_w, scale_h), min(scale_w, scale_h))

        qpixmap, scale, clip = render_page(page, self.view, self.view.devicePixelRatioF(), self.view.BASE_DPI / 72.0)
        
        self.view.set_page(page, qpixmap, render_scale=scale, fit_view=fit_view, clip=clip)

    def _on_zoom_changed(self):
        """Re-render the current page at the resolution matching the new zoom."""
        if not self.doc:
            return
        new_scale = self.view.get_render_scale()
        # Only re-render if the scale changed meaningfully (>5 % difference)
        # to avoid unnecessary re-renders on tiny zoom steps.
        if abs(new_scale - self.view._render_scale) / max(self.view._render_scale, 0.001) > 0.05:
            # Preserve the current scroll position across the re-render
            h_bar = self.view.horizontalScrollBar()
            v_bar = self.view.verticalScrollBar()
            h_ratio = h_bar.value() / max(h_bar.maximum(), 1)
            v_ratio = v_bar.value() / max(v_bar.maximum(), 1)

            self._render_page(render_scale=new_scale, fit_view=False)

            def restore_scroll():
                h_bar.setValue(int(h_ratio * h_bar.maximum()))
                v_bar.setValue(int(v_ratio * v_bar.maximum()))
            QTimer.singleShot(0, restore_scroll)

    def _prev_page(self):
        if self.page_idx > 0:
            self.page_idx -= 1
            self._render_page()

    def _next_page(self):
        if self.doc and self.page_idx < len(self.doc) - 1:
            self.page_idx += 1
            self._render_page()

    def _print_document(self):
        """Print with MNIME's native print engine (Win32 GDI, up to 300 DPI).

        Falls back to the Windows shell / Chrome hand-off if the native job fails.
        """
        index = self.file_combo.currentIndex()
        if index < 0:
            return
        file_item = self.file_items[index]

        from PyQt6.QtWidgets import QApplication
        from core import print_engine

        hwnd = int(self.winId())
        title = file_item.file_name
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                if file_item.extension == ".pdf" and self.doc:
                    print_engine.print_pdf(hwnd, self.doc, title)
                    return
                if file_item.extension in (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"):
                    print_engine.print_image(hwnd, file_item.file_path, title)
                    return
            finally:
                QApplication.restoreOverrideCursor()
        except print_engine.PrintCancelled:
            return
        except Exception as e:
            QMessageBox.warning(
                self, "Print",
                f"Direct printing failed ({e}). Falling back to the system print handler."
            )
        self._print_via_shell()

    def _print_via_shell(self):
        """Fallback: hand the file to Windows (or Chrome / default viewer) for printing.

        Uses the file's registered 'print' verb (e.g. Adobe/Edge/Photos). If no
        app handles that verb, the file is opened in its default viewer so the
        user can print from there (Ctrl+P).
        """
        index = self.file_combo.currentIndex()
        if index < 0:
            return
        file_item = self.file_items[index]
        path = os.path.abspath(file_item.file_path)

        if not os.path.isfile(path):
            QMessageBox.warning(self, "Print Error", "The file could not be found on disk.")
            return
        if file_item.extension not in (".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".txt", ".docx"):
            QMessageBox.information(self, "Print", "This file type cannot be printed from the reader.")
            return

        try:
            os.startfile(path, "print")
            return
        except OSError:
            pass  # No handler registered for the 'print' verb

        # Fallback 1: Google Chrome, which can print PDFs and images via Ctrl+P
        import subprocess
        local_app = os.environ.get("LOCALAPPDATA", "")
        chrome_candidates = [
            os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(local_app, "Google", "Chrome", "Application", "chrome.exe"),
        ]
        for chrome in chrome_candidates:
            if os.path.isfile(chrome):
                try:
                    subprocess.Popen([chrome, path])
                    QMessageBox.information(
                        self, "Print",
                        "The file was opened in Google Chrome. Press Ctrl+P there to print."
                    )
                    return
                except OSError:
                    break

        # Fallback 2: default viewer
        try:
            os.startfile(path)
            QMessageBox.information(
                self, "Print",
                "Google Chrome was not found. The file was opened in your default "
                "viewer; use its Print option (Ctrl+P)."
            )
        except OSError as e:
            QMessageBox.warning(self, "Print Error", f"Could not hand the file to Windows: {e}")


    def eventFilter(self, obj, event):
        if event.type() == event.Type.MouseMove:
            from PyQt6.QtWidgets import QApplication, QWidget
            if QApplication.overrideCursor() is not None or QWidget.mouseGrabber() is not None:
                return super().eventFilter(obj, event)
            pos = self.mapFromGlobal(event.globalPosition().toPoint())
            edge = self._get_edge(pos)
            if edge == Qt.Edge.LeftEdge or edge == Qt.Edge.RightEdge:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif edge == Qt.Edge.TopEdge or edge == Qt.Edge.BottomEdge:
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif edge == (Qt.Edge.TopEdge | Qt.Edge.LeftEdge) or edge == (Qt.Edge.BottomEdge | Qt.Edge.RightEdge):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif edge == (Qt.Edge.TopEdge | Qt.Edge.RightEdge) or edge == (Qt.Edge.BottomEdge | Qt.Edge.LeftEdge):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        return super().eventFilter(obj, event)

    def _get_edge(self, pos: QPoint) -> Qt.Edge:
        edge = Qt.Edge(0)
        # 10px layout margin + 8px grab area
        margin = 18
        
        if pos.x() <= margin:
            edge |= Qt.Edge.LeftEdge
        elif pos.x() >= self.width() - margin:
            edge |= Qt.Edge.RightEdge
            
        if pos.y() <= margin:
            edge |= Qt.Edge.TopEdge
        elif pos.y() >= self.height() - margin:
            edge |= Qt.Edge.BottomEdge
            
        return edge

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_edge(event.pos())
            if edge != Qt.Edge(0):
                self.windowHandle().startSystemResize(edge)
            else:
                self.windowHandle().startSystemMove()

    def closeEvent(self, event):
        if self.doc:
            try:
                self.doc.close()
            except:
                pass
        super().closeEvent(event)
