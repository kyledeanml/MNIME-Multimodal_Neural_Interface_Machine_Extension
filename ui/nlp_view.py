from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, 
    QLineEdit, QPushButton, QLabel, QProgressBar, QDialog, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt, QThread
from typing import List, Any
from core.file_item import FileItem
from core.search_engine import SearchEngine
from core.nlp_engine import NLPEngine

class ClickableTextBrowser(QTextBrowser):
    doubleClicked = pyqtSignal()
    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)

class ExpandedNLPDialog(QDialog):
    def __init__(self, parent_view, parent=None):
        super().__init__(parent)
        self.parent_view = parent_view
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(850, 650)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        frame = QFrame()
        frame.setStyleSheet("QFrame { background-color: rgba(11, 15, 25, 240); border: 2px solid #00d2ff; border-radius: 12px; }")
        frame_layout = QVBoxLayout(frame)
        
        header_layout = QHBoxLayout()
        title = QLabel("NLP")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #00e5ff; font-size: 18px; font-weight: bold; border: none; background: transparent;")
        
        close_btn = QPushButton("CLOSE")
        close_btn.setAutoDefault(False)
        close_btn.setStyleSheet("QPushButton { background-color: transparent; color: #00e5ff; font-weight: bold; border: none; font-size: 14px; } QPushButton:hover { color: #ffffff; }")
        close_btn.clicked.connect(self.close)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        
        self.history_view = QTextBrowser()
        self.history_view.setStyleSheet("""
            QTextBrowser { background-color: transparent; color: #c9d1d9; border: none; font-size: 16px; }
            QScrollBar:vertical { background: transparent; width: 10px; margin: 0px 0px 0px 0px; }
            QScrollBar::handle:vertical { background: #1f2737; min-height: 20px; border-radius: 5px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Ask a question...")
        self.query_input.setStyleSheet("""
            QLineEdit { background-color: rgba(22, 27, 34, 180); color: #f0f6fc; border: 1px solid #30363d; border-radius: 6px; padding: 15px; font-size: 16px; }
        """)
        self.query_input.returnPressed.connect(self._submit_query)
        
        frame_layout.addLayout(header_layout)
        frame_layout.addWidget(self.history_view)
        frame_layout.addWidget(self.query_input)
        layout.addWidget(frame)
        
        self.query_input.textChanged.connect(self._sync_to_parent)
        self.parent_view.query_input.textChanged.connect(self._sync_from_parent)
        self.query_input.setText(self.parent_view.query_input.text())
        
        self.parent_view.window().installEventFilter(self)
        
    def _sync_to_parent(self, text):
        if self.parent_view.query_input.text() != text:
            self.parent_view.query_input.setText(text)

    def _sync_from_parent(self, text):
        if self.query_input.text() != text:
            self.query_input.setText(text)
        
    def center_on_parent(self):
        parent_rect = self.parent_view.window().geometry()
        x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
        y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
        self.move(x, y)
        
    def eventFilter(self, obj, event):
        if obj is self.parent_view.window() and event.type() in (event.Type.Move, event.Type.Resize):
            self.center_on_parent()
        return super().eventFilter(obj, event)

    def _submit_query(self):
        self.parent_view._submit_query()
        
    def append_html(self, html: str):
        self.history_view.append(html)
        
    def set_input_enabled(self, enabled: bool):
        self.query_input.setEnabled(enabled)
        if enabled:
            self.query_input.setFocus()

    def accept(self):
        # Override accept to prevent the QDialog from automatically closing 
        # when the user presses Enter in the query_input.
        pass

class IndexWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, file_items: List[FileItem]):
        super().__init__()
        self.file_items = file_items

    def run(self):
        try:
            from PyQt6.QtCore import QSettings
            settings = QSettings("MNIME", "MNIMEApp")
            smart_sampling = str(settings.value("nlp_smart_indexing", "true")).lower() == "true"
            
            vectorstore = SearchEngine.build_index(
                self.file_items, 
                use_smart_sampling=smart_sampling, 
                progress_callback=self._emit_progress
            )
            self.finished.emit(vectorstore)
        except Exception as e:
            self.error.emit(str(e))

    def _emit_progress(self, pct: int, msg: str):
        self.progress.emit(pct, msg)


class FallbackStreamWorker(QThread):
    finished = pyqtSignal(str)
    chunk_received = pyqtSignal(str)
    point_generated = pyqtSignal(float, float, str)
    stats_updated = pyqtSignal(dict)

    def __init__(self, text: str):
        super().__init__()
        self.text = text

    def run(self):
        import time
        words = self.text.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            self.chunk_received.emit(chunk)
            time.sleep(0.06)
        self.finished.emit(self.text)


class NLPQueryWorker(QThread):
    finished = pyqtSignal(str)
    chunk_received = pyqtSignal(str)
    point_generated = pyqtSignal(float, float, str)
    stats_updated = pyqtSignal(dict)
    new_fallback_state = pyqtSignal(int)
    fallback_selected = pyqtSignal(str, str)

    def __init__(self, query: str, context_docs: list, fallback_state: int = 0, first_joke_done: bool = False):
        super().__init__()
        self.query = query
        self.context_docs = context_docs
        self.fallback_state = fallback_state
        self.first_joke_done = first_joke_done

    def run(self):
        import time
        import random
        from ui.nerds import get_process_memory_mb
        from core.fallback_responses import CASUAL_DIALOG_TEMPLATES
        try:
            generator = NLPEngine.get_instance().generate_response_stream(self.query, self.context_docs)
            full_response = ""
            buffer = ""
            is_fallback_mode = False

            t_start_eval = time.time()
            t_first_token = None
            tokens_received = 0
            token_timestamps = []

            for chunk in generator:
                now = time.time()
                if t_first_token is None:
                    t_first_token = now - t_start_eval

                if not is_fallback_mode and not full_response:
                    buffer += chunk
                    buffer_upper = buffer.upper()
                    if any(trigger in buffer_upper for trigger in ["KNOCK_KNOCK", "KNOCK KNOCK", "I REJECT THE PREMISE", "DISCOURSE", "I DO NOT PARTICIPATE", "THE ASSERTION THAT"]):
                        is_fallback_mode = True
                        break
                    
                    if len(buffer) > 45:
                        full_response += buffer
                        self.chunk_received.emit(buffer)
                        tokens_received += 1
                        token_timestamps.append(now)
                    continue

                full_response += chunk
                self.chunk_received.emit(chunk)
                tokens_received += 1
                token_timestamps.append(now)

                elapsed = now - t_start_eval
                window = 6
                if len(token_timestamps) > window:
                    inst_throughput = window / max(token_timestamps[-1] - token_timestamps[-window - 1], 0.001)
                else:
                    inst_throughput = tokens_received / max(elapsed, 0.001)

                cur_ram = get_process_memory_mb()
                self.point_generated.emit(elapsed, inst_throughput, "tok_sec")
                self.point_generated.emit(elapsed, cur_ram, "ram_mb")

                self.stats_updated.emit({
                    "throughput": inst_throughput,
                    "ttft": t_first_token * 1000 if t_first_token else 0.0,
                    "ram_mb": cur_ram,
                    "tokens": tokens_received
                })

            if not is_fallback_mode and buffer and not full_response:
                full_response += buffer
                self.chunk_received.emit(buffer)

            if is_fallback_mode:
                if not self.first_joke_done:
                    setup = "Not an answer to your out of scope question"
                    punchline = ""
                else:
                    setup, punchline = random.choice(CASUAL_DIALOG_TEMPLATES)
                self.fallback_selected.emit(setup, punchline)
                self.new_fallback_state.emit(1)
                fallback_text = "Knock, knock."
                
                full_response = ""
                words = fallback_text.split(" ")
                for i, word in enumerate(words):
                    chunk = word + (" " if i < len(words) - 1 else "")
                    full_response += chunk
                    self.chunk_received.emit(chunk)
                    time.sleep(0.08)

            self.finished.emit(full_response.strip())
        except Exception as e:
            self.finished.emit(f"Error: {e}")


class NLPView(QWidget):
    start_over_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vectorstore = None
        self.expanded_dialog = None
        self.fallback_state = 0
        self.current_fallback = None
        self.user_fallback_setup = None
        self.fallback_worker = None
        self.first_joke_done = False
        self._setup_ui()
        
        import atexit, sys
        atexit.register(self.clear_index)
        self._old_excepthook = sys.excepthook
        sys.excepthook = self._crash_hook

    def _crash_hook(self, exctype, value, traceback):
        self.clear_index()
        if self._old_excepthook:
            self._old_excepthook(exctype, value, traceback)

    def clear_index(self):
        if self.vectorstore:
            del self.vectorstore
            self.vectorstore = None
            import gc
            gc.collect()
        self.fallback_state = 0
        self.current_fallback = None
        self.user_fallback_setup = None

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_label = QLabel("Drop files in carousel and click 'INDEX FILES' to start.")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 13px;")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #1f2737; border-radius: 4px; text-align: center; color: white; background-color: #0d1117;}
            QProgressBar::chunk { background-color: #00e5ff; }
        """)
        
        self.start_over_btn = QPushButton("START OVER")
        self.start_over_btn.setStyleSheet("""
            QPushButton { background-color: #162438; color: #00e5ff; border: 1px solid #00d2ff; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 11px; }
            QPushButton:hover { background-color: #0077b6; color: #ffffff; }
        """)
        self.start_over_btn.clicked.connect(self.start_over_clicked.emit)

        self.lora_btn = QPushButton()
        self.lora_btn.setStyleSheet(self.start_over_btn.styleSheet())
        self.lora_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lora_btn.clicked.connect(self._choose_lora)
        self.lora_btn.customContextMenuRequested.connect(lambda _pos: self._clear_lora())
        self._refresh_lora_label()
        
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.status_label)
        top_layout.addWidget(self.progress_bar)
        top_layout.addStretch()
        top_layout.addWidget(self.lora_btn)
        top_layout.addWidget(self.start_over_btn)
        
        self.history_view = ClickableTextBrowser()
        self.history_view.setStyleSheet("""
            QTextBrowser { background-color: #0a0d14; color: #c9d1d9; border: 1px solid #1f2737; border-radius: 6px; padding: 10px; font-size: 14px; }
        """)
        self.history_view.setToolTip("Double click for expanded view")
        self.history_view.doubleClicked.connect(self._on_history_double_clicked)
        
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Ask a question about your documents...")
        self.query_input.setStyleSheet("""
            QLineEdit { background-color: #161b22; color: #f0f6fc; border: 1px solid #30363d; border-radius: 6px; padding: 10px; font-size: 14px; }
        """)
        self.query_input.returnPressed.connect(self._submit_query)
        self.query_input.setEnabled(False)
        
        layout.addLayout(top_layout)
        layout.addWidget(self.history_view)
        layout.addWidget(self.query_input)

    def _refresh_lora_label(self):
        import os
        path = NLPEngine.get_instance().lora_path
        if path and os.path.exists(path):
            self.lora_btn.setText("LORA: ON")
            self.lora_btn.setToolTip(f"Adapter: {path}\nClick to change, right-click to remove.")
        else:
            self.lora_btn.setText("LORA: OFF")
            self.lora_btn.setToolTip("Click to load a LoRA adapter (.gguf).")

    def _choose_lora(self):
        from ui.file_dialog import CustomFileDialog
        dialog = CustomFileDialog(self)
        if not dialog.exec():
            return
        files = [f for f in (dialog.selected_files or []) if f.lower().endswith(".gguf")]
        if not files:
            self.status_label.setText("LoRA adapter must be a .gguf file.")
            return
        NLPEngine.get_instance().set_lora(files[0])
        self.status_label.setText("Reloading model with LoRA adapter...")
        self._refresh_lora_label()

    def _clear_lora(self):
        engine = NLPEngine.get_instance()
        if not engine.lora_path:
            return
        engine.set_lora("")
        self.status_label.setText("LoRA adapter removed. Reloading base model...")
        self._refresh_lora_label()

    def _on_history_double_clicked(self):
        if not self.expanded_dialog:
            self.expanded_dialog = ExpandedNLPDialog(self, self.window())
        self.expanded_dialog.history_view.setHtml(self.history_view.toHtml())
        self.expanded_dialog.set_input_enabled(self.query_input.isEnabled())
        self.expanded_dialog.query_input.setText(self.query_input.text())
        
        # Center on parent window
        self.expanded_dialog.center_on_parent()
        self.expanded_dialog.show()

    def _append_history(self, html_msg: str):
        self.history_view.append(html_msg)
        if self.expanded_dialog and self.expanded_dialog.isVisible():
            self.expanded_dialog.append_html(html_msg)

    def _insert_html_at_end(self, html_msg: str):
        cursor = self.history_view.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.history_view.setTextCursor(cursor)
        self.history_view.insertHtml(html_msg)
        
        if self.expanded_dialog and self.expanded_dialog.isVisible():
            cursor_exp = self.expanded_dialog.history_view.textCursor()
            cursor_exp.movePosition(cursor_exp.MoveOperation.End)
            self.expanded_dialog.history_view.setTextCursor(cursor_exp)
            self.expanded_dialog.history_view.insertHtml(html_msg)
            
    def _set_input_enabled(self, enabled: bool):
        self.query_input.setEnabled(enabled)
        if self.expanded_dialog and self.expanded_dialog.isVisible():
            self.expanded_dialog.set_input_enabled(enabled)

    def start_indexing(self, file_items: List[FileItem]):
        if not file_items:
            self.status_label.setText("No files to index.")
            return

        self.start_over_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Indexing...")
        
        self.worker = IndexWorker(file_items)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_index_finished)
        self.worker.error.connect(self._on_index_error)
        self.worker.start()

    def _on_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.status_label.setText(msg)

    def _on_index_finished(self, vectorstore):
        self.vectorstore = vectorstore
        self.progress_bar.setVisible(False)
        self.status_label.setText("Indexing complete! Ask a question below.")
        self.start_over_btn.setEnabled(True)
        self._set_input_enabled(True)
        self.query_input.setFocus()
        self._append_history("<div style='color:#00e5ff'><b>System:</b> Indexing complete. Ready for queries.</div><br>")

    def _on_index_error(self, err: str):
        import html
        self.progress_bar.setVisible(False)
        self.status_label.setText("Error during indexing.")
        self.start_over_btn.setEnabled(True)
        safe_err = html.escape(str(err))
        self._append_history(f"<div style='color:#ff5555'><b>Error:</b> {safe_err}</div><br>")

    def _start_fallback_stream(self, text: str):
        self.fallback_worker = FallbackStreamWorker(text)
        self.fallback_worker.chunk_received.connect(self._on_query_chunk)
        self.fallback_worker.finished.connect(self._on_query_response)
        
        main_win = self.window()
        if hasattr(main_win, '_stats_dialog') and main_win._stats_dialog is not None:
            main_win._stats_dialog.chart.clear()
            
        self.fallback_worker.start()

    def _set_fallback_state(self, state: int):
        self.fallback_state = state

    def _set_current_fallback(self, setup: str, punchline: str):
        self.current_fallback = (setup, punchline)

    def _submit_query(self):
        import html
        query = self.query_input.text().strip()
        if not query: return
        
        self.query_input.clear()
        safe_query = html.escape(query)
        self._append_history(f"<div style='color:#c9d1d9'><b>You:</b> {safe_query}</div><br>")
        self._set_input_enabled(False)
        self.status_label.setText("Generating answer...")
        
        self._append_history("<div style='color:#00e5ff'><b>MNIME:</b> </div>")
        
        lower_q = query.lower().strip()
        clean_q = lower_q.replace(",", "").replace(".", "").replace("!", "").replace("?", "").strip()

        # Cancellation check for any active joke state
        if self.fallback_state != 0 and clean_q in ["cancel", "stop", "exit", "quit", "nevermind", "never mind", "abort"]:
            self.fallback_state = 0
            self.current_fallback = None
            self.user_fallback_setup = None
            self._start_fallback_stream("Joke cancelled.")
            return

        # Case A: User initiates a knock-knock joke
        if self.fallback_state == 0 and clean_q == "knock knock":
            self.fallback_state = 10
            self._start_fallback_stream("Who's there?")
            return

        # Case A.1: User provides the setup (e.g. "Lettuce")
        if self.fallback_state == 10:
            setup = query.strip().rstrip(".!?")
            self.user_fallback_setup = setup
            self.fallback_state = 11
            self._start_fallback_stream(f"{setup} who?")
            return

        # Case A.2: User provides the punchline (e.g. "Lettuce in, it's cold!")
        if self.fallback_state == 11:
            self.fallback_state = 0
            self.user_fallback_setup = None
            self._start_fallback_stream("Haha! Good one!")
            return

        # Case B: MNIME-initiated joke - Turn 2 (MNIME knocked, user responds)
        if self.fallback_state == 1:
            words = clean_q.split()
            has_knock_cue = any(w in words for w in ["who", "whose", "whos", "there", "that", "it", "door", "knock", "dat", "dis"])
            if len(words) > 5 and not has_knock_cue:
                # Cancel joke and proceed to document query
                self.fallback_state = 0
                self.current_fallback = None
            else:
                if not self.current_fallback:
                    from core.fallback_responses import CASUAL_DIALOG_TEMPLATES
                    import random
                    self.current_fallback = random.choice(CASUAL_DIALOG_TEMPLATES)
                
                setup, punchline = self.current_fallback
                if not punchline:
                    self.fallback_state = 0
                    self.current_fallback = None
                    self.first_joke_done = True
                    self._start_fallback_stream(f"{setup}.")
                else:
                    self.fallback_state = 2
                    self._start_fallback_stream(f"{setup}.")
                return

        # Case B: MNIME-initiated joke - Turn 3 (MNIME gave setup, user asks "setup who?")
        if self.fallback_state == 2:
            words = clean_q.split()
            if len(words) > 6 and "who" not in words:
                # Cancel joke and proceed to document query
                self.fallback_state = 0
                self.current_fallback = None
            else:
                setup, punchline = self.current_fallback if self.current_fallback else ("Noah", "Noah good place to eat?")
                self.fallback_state = 0
                self.current_fallback = None
                self._start_fallback_stream(punchline)
                return

        # ── Normal Document Query Flow ──
        # 1. Semantic Search (open documents + persistent global vector store)
        context_docs = SearchEngine.search(self.vectorstore, query, k=5)
        seen = {d["content"] for d in context_docs}
        for hit in SearchEngine.search_global_memory(query, k=6):
            if hit["content"] not in seen:
                context_docs.append(hit)
                seen.add(hit["content"])
            if len(context_docs) >= 7:
                break
        
        # 2. LLM Generation
        self.query_worker = NLPQueryWorker(query, context_docs, getattr(self, 'fallback_state', 0), getattr(self, 'first_joke_done', False))
        self.query_worker.chunk_received.connect(self._on_query_chunk)
        self.query_worker.finished.connect(self._on_query_response)
        self.query_worker.new_fallback_state.connect(self._set_fallback_state)
        self.query_worker.fallback_selected.connect(self._set_current_fallback)
        
        main_win = self.window()
        if hasattr(main_win, '_stats_dialog'):
            if main_win._stats_dialog is None:
                from ui.nerds import StatsForNerdsDialog
                main_win._stats_dialog = StatsForNerdsDialog(main_win)
            self.query_worker.point_generated.connect(main_win._stats_dialog._on_point_generated)
            self.query_worker.stats_updated.connect(main_win._stats_dialog._on_stats_updated)
            main_win._stats_dialog.chart.clear()

        self.query_worker.start()

    def _on_query_chunk(self, chunk: str):
        import html
        safe_chunk = html.escape(chunk).replace("\n", "<br>").replace(" ", "&nbsp;")
        self._insert_html_at_end(f"<span style='color:#00e5ff'>{safe_chunk}</span>")

    def _on_query_response(self, response: str):
        self._insert_html_at_end("<br><hr><br>")
        self._set_input_enabled(True)
        self.query_input.setFocus()
        self.status_label.setText("Ready.")
