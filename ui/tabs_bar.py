"""
Tabs bar widget for switching between different conversion modes:
Merge Files, JPG -> PDF, PDF -> JPG, Compress PDF, PDF -> Word.
"""

from ui.cursor_fx import get_custom_cursor
from enum import Enum
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QButtonGroup, QFrame
from PyQt6.QtCore import pyqtSignal, Qt, QTimer


class ToolMode(Enum):
    EDIT_IMAGE = "EDIT"
    READER = "READER"
    REFERENCE = "REFERENCE"
    BOOKMARK = "BOOKMARK"
    COMBINE_PDF = "MERGE"
    SPLIT_PDF = "SPLIT"
    JPG_TO_PDF = "JPG → PDF"
    PDF_TO_JPG = "PDF → JPG"
    TXT_TO_PDF = "TXT → PDF"
    COMPRESS_PDF = "COMPRESS"
    PDF_TO_DOCX = "PDF → DOCX"
    NLP = "NLP"
    RELOAD_NLP = "RELOAD"
    STATS = "STATS"

class TabsBar(QWidget):
    """Free-floating dark metallic tab navigation bar with dark neon blue highlights."""

    mode_changed = pyqtSignal(ToolMode)
    nlp_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_mode = ToolMode.COMBINE_PDF
        self._buttons = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        left_tabs = [ToolMode.EDIT_IMAGE, ToolMode.BOOKMARK, ToolMode.READER, ToolMode.REFERENCE]
        center_tabs = [
            ToolMode.JPG_TO_PDF,
            ToolMode.TXT_TO_PDF,
            ToolMode.COMBINE_PDF,
            ToolMode.SPLIT_PDF,
            ToolMode.COMPRESS_PDF,
            ToolMode.PDF_TO_JPG,
            ToolMode.PDF_TO_DOCX
        ]
        right_tabs = [
            ToolMode.NLP,
            ToolMode.RELOAD_NLP,
            ToolMode.STATS,
        ]

        def _add_tab(mode):
            from ui.icons import get_icon
            from PyQt6.QtCore import QSize
            
            icon_map = {
                ToolMode.EDIT_IMAGE: "edit",
                ToolMode.BOOKMARK: "bookmark",
                ToolMode.JPG_TO_PDF: "image",
                ToolMode.TXT_TO_PDF: "file-text",
                ToolMode.COMBINE_PDF: "layers",
                ToolMode.SPLIT_PDF: "razor",
                ToolMode.COMPRESS_PDF: "minimize",
                ToolMode.PDF_TO_JPG: "images",
                ToolMode.PDF_TO_DOCX: "document",
                ToolMode.READER: "book",
                ToolMode.REFERENCE: "crossref",
                ToolMode.NLP: "message",
                ToolMode.RELOAD_NLP: "refresh",
                ToolMode.STATS: "stats",
            }
            
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setCursor(get_custom_cursor())
            
            if mode in [ToolMode.NLP, ToolMode.RELOAD_NLP, ToolMode.STATS]:
                btn.setFixedHeight(21)
                btn.setFixedWidth(30)
                btn.setIconSize(QSize(12, 12))
            else:
                btn.setFixedHeight(28)
                btn.setFixedWidth(40)
                btn.setIconSize(QSize(16, 16))
            
            btn.setIcon(get_icon(icon_map.get(mode, "document"), "#00e5ff"))
            btn.setToolTip(mode.value)
            
            btn.setStyleSheet("""
                QToolTip {
                    background-color: #0b0f19;
                    color: #00e5ff;
                    border: 1px solid #00d2ff;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-weight: 900;
                    letter-spacing: 1px;
                }
                QPushButton {
                    background-color: #162438;
                    border: 1px solid #1f2737;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #0077b6;
                    border: 1px solid #00d2ff;
                }
                QPushButton:checked {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #005f8c, stop:1 #00a8e8);
                    border: 1px solid #00e5ff;
                }
            """)
                
            btn.clicked.connect(lambda checked, m=mode: self._on_tab_clicked(m))
            self.button_group.addButton(btn)
            layout.addWidget(btn)
            self._buttons[mode] = btn

        for mode in left_tabs:
            _add_tab(mode)
            
        layout.addStretch()
        
        for i, mode in enumerate(center_tabs):
            if i > 0:
                layout.addSpacing(15)
            _add_tab(mode)
            
        layout.addStretch()
        
        from PyQt6.QtWidgets import QCheckBox, QVBoxLayout, QLabel, QWidget
        from PyQt6.QtCore import QSettings
        
        self.nlp_container = QWidget()
        nlp_layout = QVBoxLayout(self.nlp_container)
        nlp_layout.setContentsMargins(0, 0, 0, 0)
        nlp_layout.setSpacing(2)
        
        self.nlp_checkbox = QCheckBox()
        self.nlp_checkbox.setStyleSheet("""
            QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #00d2ff; border-radius: 3px; background-color: #162438; }
            QCheckBox::indicator:checked { background-color: #00e5ff; }
        """)
        
        self.nlp_label = QLabel("NEURAL\nOFFLINE")
        self.nlp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.nlp_label.setStyleSheet("color: #00e5ff; font-weight: bold; font-size: 9px;")
        
        nlp_layout.addWidget(self.nlp_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
        nlp_layout.addWidget(self.nlp_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        settings = QSettings("MNIME", "MNIMEApp")
        self.nlp_checkbox.setChecked(str(settings.value("nlp_enabled", "true")).lower() == "true")
        self.nlp_checkbox.toggled.connect(self._on_nlp_toggled)
        layout.addWidget(self.nlp_container)
        
        for mode in right_tabs:
            _add_tab(mode)

        # Set initial active tab
        self._buttons[ToolMode.COMBINE_PDF].setChecked(True)

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_reload_button_status)
        self.status_timer.start(1000)

    def _update_reload_button_status(self):
        from core.nlp_engine import NLPEngine
        nlp = NLPEngine.get_instance()
        is_loaded = nlp.is_loaded
        is_loading = nlp.is_loading
        btn = self._buttons.get(ToolMode.RELOAD_NLP)
        if not btn: return

        state_tuple = (is_loaded, is_loading)
        if getattr(self, '_last_nlp_state', None) == state_tuple:
            return
        self._last_nlp_state = state_tuple

        # --- NLP checkbox: active light ---
        if is_loading:
            self.nlp_label.setText("NEURAL\nBOOTING")
            self.nlp_label.setStyleSheet("color: #ffb300; font-weight: bold; font-size: 9px;")
            self.nlp_checkbox.setStyleSheet("""
                QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #ffb300; border-radius: 3px; background-color: #162438; }
                QCheckBox::indicator:checked { background-color: #ffb300; }
            """)
        elif is_loaded:
            self.nlp_label.setText("NEURAL\nACTIVE")
            self.nlp_label.setStyleSheet("color: #00e676; font-weight: bold; font-size: 9px;")
            self.nlp_checkbox.setStyleSheet("""
                QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #00e676; border-radius: 3px; background-color: #162438; }
                QCheckBox::indicator:checked { background-color: #00e676; }
            """)
        else:
            self.nlp_label.setText("NEURAL\nOFFLINE")
            self.nlp_label.setStyleSheet("color: #00e5ff; font-weight: bold; font-size: 9px;")
            self.nlp_checkbox.setStyleSheet("""
                QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #00d2ff; border-radius: 3px; background-color: #162438; }
                QCheckBox::indicator:checked { background-color: #00e5ff; }
            """)

        # --- RELOAD button border: glow cyan when not loaded, dim when loaded ---
        if not is_loaded:
            btn.setStyleSheet("""
                QToolTip {
                    background-color: #0b0f19;
                    color: #00e5ff;
                    border: 1px solid #00d2ff;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-weight: 900;
                    letter-spacing: 1px;
                }
                QPushButton {
                    background-color: #162438;
                    border: 1px solid #00e5ff;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #0077b6;
                    border: 1px solid #00d2ff;
                }
                QPushButton:checked {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #005f8c, stop:1 #00a8e8);
                    border: 1px solid #00e5ff;
                }
            """)
        else:
            btn.setStyleSheet("""
                QToolTip {
                    background-color: #0b0f19;
                    color: #00e5ff;
                    border: 1px solid #00d2ff;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-weight: 900;
                    letter-spacing: 1px;
                }
                QPushButton {
                    background-color: #162438;
                    border: 1px solid #1f2737;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #0077b6;
                    border: 1px solid #00d2ff;
                }
                QPushButton:checked {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #005f8c, stop:1 #00a8e8);
                    border: 1px solid #00e5ff;
                }
            """)

    def _on_nlp_toggled(self, checked):
        from PyQt6.QtCore import QSettings
        from core.nlp_engine import NLPEngine
        settings = QSettings("MNIME", "MNIMEApp")
        settings.setValue("nlp_enabled", checked)
        if checked:
            NLPEngine.get_instance().reload_model_async()
        else:
            NLPEngine.get_instance().unload_model()
        self.nlp_toggled.emit(checked)

    def _on_tab_clicked(self, mode: ToolMode):
        if mode == ToolMode.RELOAD_NLP:
            from core.nlp_engine import NLPEngine
            NLPEngine.get_instance().reload_model_async()
            if self.current_mode in self._buttons:
                self._buttons[self.current_mode].setChecked(True)
            return
            
        # Launcher buttons: open a window but keep the active tool mode selected
        if mode in (ToolMode.STATS, ToolMode.READER):
            self.mode_changed.emit(mode)
            if self.current_mode in self._buttons:
                self._buttons[self.current_mode].setChecked(True)
            return

        if self.current_mode != mode:
            self.current_mode = mode
            self.mode_changed.emit(mode)

    def set_mode(self, mode: ToolMode):
        if mode in self._buttons:
            self._buttons[mode].setChecked(True)
            self._on_tab_clicked(mode)
