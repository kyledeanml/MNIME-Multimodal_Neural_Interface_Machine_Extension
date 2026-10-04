"""
Stats — Empirical Telemetry, Performance Benchmarking & Dynamic Visualization UI.
Designed for the MNIME desktop ecosystem. Matches the frameless translucent dark metallic
and neon cyan aesthetic of the NLP interface.
"""

import os
import sys
import time
import json
import math
import ctypes
from typing import List, Tuple, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QDialog, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QProgressBar, QComboBox, QFrame, QSizePolicy,
    QFileDialog, QTabWidget, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint, QRectF, QEvent, QObject
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QLinearGradient, QFont, QPolygonF,
    QPainterPath, QCursor
)

from ui.icons import get_icon


# ─── System Memory Sampling (Zero Dependency) ───────────────────────────────

def get_process_memory_mb() -> float:
    """Retrieve current process Working Set (RAM) in Megabytes."""
    if sys.platform == "win32":
        try:
            import ctypes.wintypes
            class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
                _fields_ = [
                    ('cb', ctypes.wintypes.DWORD),
                    ('PageFaultCount', ctypes.wintypes.DWORD),
                    ('PeakWorkingSetSize', ctypes.c_size_t),
                    ('WorkingSetSize', ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t),
                    ('PeakPagefileUsage', ctypes.c_size_t),
                    ('PrivateUsage', ctypes.c_size_t),
                ]
            psapi = ctypes.windll.psapi
            kernel32 = ctypes.windll.kernel32
            psapi.GetProcessMemoryInfo.argtypes = [
                ctypes.wintypes.HANDLE,
                ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
                ctypes.wintypes.DWORD
            ]
            psapi.GetProcessMemoryInfo.restype = ctypes.wintypes.BOOL

            counters = PROCESS_MEMORY_COUNTERS_EX()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
            if psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                return counters.WorkingSetSize / (1024.0 * 1024.0)
        except Exception:
            pass
    return 0.0


# ─── Dynamic Line Chart Widget ──────────────────────────────────────────────

class DynamicLineChart(QWidget):
    """
    High-performance, 60 FPS anti-aliased dynamic line chart widget.
    Features neon glowing curves, vertical gradient area fill, auto-scaling,
    horizontal reference gridlines, peak/average markers, and hover tooltips.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(240)
        self.setMouseTracking(True)

        self._points: List[Tuple[float, float]] = []  # (x, y)
        self._metric_name: str = "Throughput"
        self._unit: str = "tok/s"
        self._color: QColor = QColor("#00e5ff")
        self._peak: float = 0.0
        self._avg: float = 0.0
        self._hover_pos: Optional[QPoint] = None

    def set_metric(self, name: str, unit: str, color_hex: str = "#00e5ff"):
        self._metric_name = name
        self._unit = unit
        self._color = QColor(color_hex)
        self.update()

    def add_point(self, x: float, y: float):
        self._points.append((float(x), float(y)))
        if y > self._peak:
            self._peak = y
        total_y = sum(p[1] for p in self._points)
        self._avg = total_y / len(self._points) if self._points else 0.0
        self.update()

    def set_data(self, points: List[Tuple[float, float]], name: str, unit: str, color_hex: str = "#00e5ff"):
        self._points = [(float(p[0]), float(p[1])) for p in points]
        self._metric_name = name
        self._unit = unit
        self._color = QColor(color_hex)
        self._peak = max((p[1] for p in self._points), default=0.0)
        self._avg = (sum(p[1] for p in self._points) / len(self._points)) if self._points else 0.0
        self.update()

    def clear(self):
        self._points.clear()
        self._peak = 0.0
        self._avg = 0.0
        self.update()

    def mouseMoveEvent(self, event):
        self._hover_pos = event.pos()
        self.update()

    def leaveEvent(self, event):
        self._hover_pos = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = self.width()
        h = self.height()

        # Canvas Margins
        pad_left = 58
        pad_right = 30
        pad_top = 35
        pad_bottom = 35

        plot_w = max(10, w - pad_left - pad_right)
        plot_h = max(10, h - pad_top - pad_bottom)

        # Background Box
        bg_rect = QRectF(0, 0, w, h)
        painter.fillRect(bg_rect, QColor("#0d131f"))

        # Plot Area Border
        plot_rect = QRectF(pad_left, pad_top, plot_w, plot_h)
        painter.setPen(QPen(QColor("#1c2538"), 1))
        painter.drawRect(plot_rect)

        # Scale Bounds
        max_y = max(self._peak * 1.15, 10.0)
        min_y = 0.0

        max_x = max((p[0] for p in self._points), default=1.0)
        min_x = min((p[0] for p in self._points), default=0.0)
        if max_x <= min_x:
            max_x = min_x + 1.0

        # Horizontal Gridlines (4 intervals)
        painter.setFont(QFont("Consolas", 8))
        grid_steps = 4
        for i in range(grid_steps + 1):
            val = min_y + (max_y - min_y) * (i / grid_steps)
            py = pad_top + plot_h - (i / grid_steps) * plot_h

            # Line
            painter.setPen(QPen(QColor("#162032"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(int(pad_left), int(py), int(pad_left + plot_w), int(py))

            # Y-axis Label
            painter.setPen(QPen(QColor("#64748b")))
            painter.drawText(
                QRectF(0, py - 8, pad_left - 8, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"{val:.1f}" if max_y < 100 else f"{int(val)}"
            )

        # Empty State
        if len(self._points) < 2:
            painter.setPen(QPen(QColor("#384860")))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            painter.drawText(
                plot_rect,
                Qt.AlignmentFlag.AlignCenter,
                "Telemetry Standby — Run benchmark or start NLP to stream real-time metrics"
            )
            return

        # Map points to pixel coordinates
        poly_pts = []
        for x, y in self._points:
            norm_x = (x - min_x) / (max_x - min_x)
            norm_y = (y - min_y) / (max_y - min_y)
            px = pad_left + norm_x * plot_w
            py = pad_top + plot_h - norm_y * plot_h
            poly_pts.append(QPoint(int(px), int(py)))

        # Area Gradient Fill Under Curve
        if poly_pts:
            fill_path = QPainterPath()
            fill_path.moveTo(poly_pts[0].x(), pad_top + plot_h)
            fill_path.lineTo(poly_pts[0].x(), poly_pts[0].y())
            for pt in poly_pts[1:]:
                fill_path.lineTo(pt.x(), pt.y())
            fill_path.lineTo(poly_pts[-1].x(), pad_top + plot_h)
            fill_path.closeSubpath()

            grad = QLinearGradient(0, pad_top, 0, pad_top + plot_h)
            grad_color = QColor(self._color)
            grad_color.setAlpha(65)
            grad.setColorAt(0.0, grad_color)
            grad_color.setAlpha(0)
            grad.setColorAt(1.0, grad_color)

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(fill_path)

        # Neon Glow Polyline
        # Outer glow
        glow_pen = QPen(self._color)
        glow_pen.setWidth(5)
        glow_col = QColor(self._color)
        glow_col.setAlpha(45)
        glow_pen.setColor(glow_col)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(len(poly_pts) - 1):
            painter.drawLine(poly_pts[i], poly_pts[i + 1])

        # Core crisp line
        core_pen = QPen(self._color)
        core_pen.setWidth(2)
        painter.setPen(core_pen)
        for i in range(len(poly_pts) - 1):
            painter.drawLine(poly_pts[i], poly_pts[i + 1])

        # Draw Peak Reference Line
        if self._peak > 0:
            peak_y = pad_top + plot_h - ((self._peak - min_y) / (max_y - min_y)) * plot_h
            painter.setPen(QPen(QColor("#39ff14"), 1, Qt.PenStyle.DotLine))
            painter.drawLine(int(pad_left), int(peak_y), int(pad_left + plot_w), int(peak_y))

            painter.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            painter.setPen(QColor("#39ff14"))
            painter.drawText(int(pad_left + plot_w - 95), int(peak_y - 4), f"PEAK: {self._peak:.2f} {self._unit}")

        # Draw Average Reference Line
        if self._avg > 0:
            avg_y = pad_top + plot_h - ((self._avg - min_y) / (max_y - min_y)) * plot_h
            painter.setPen(QPen(QColor("#ffd700"), 1, Qt.PenStyle.DotLine))
            painter.drawLine(int(pad_left), int(avg_y), int(pad_left + plot_w), int(avg_y))

            painter.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            painter.setPen(QColor("#ffd700"))
            painter.drawText(int(pad_left + 8), int(avg_y - 4), f"AVG: {self._avg:.2f} {self._unit}")

        # Draw Leading Beacon Dot
        last_pt = poly_pts[-1]
        painter.setPen(Qt.PenStyle.NoPen)
        # Pulsing halo
        halo = QColor(self._color)
        halo.setAlpha(100)
        painter.setBrush(QBrush(halo))
        painter.drawEllipse(last_pt, 7, 7)
        # Core white/cyan dot
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawEllipse(last_pt, 3, 3)

        # Header Status Banner
        latest_val = self._points[-1][1] if self._points else 0.0
        badge_text = (
            f"METRIC: {self._metric_name.upper()}  |  "
            f"LIVE: {latest_val:.2f} {self._unit}  |  "
            f"PEAK: {self._peak:.2f} {self._unit}  |  "
            f"AVG: {self._avg:.2f} {self._unit}  |  "
            f"SAMPLES: {len(self._points)}"
        )
        painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        painter.setPen(QColor("#00e5ff"))
        painter.drawText(int(pad_left), int(pad_top - 10), badge_text)

        # X-axis Labels
        painter.setFont(QFont("Consolas", 8))
        painter.setPen(QColor("#64748b"))
        painter.drawText(int(pad_left), int(h - 12), f"T=0 ({min_x:.0f})")
        painter.drawText(
            QRectF(pad_left, h - 25, plot_w, 20),
            Qt.AlignmentFlag.AlignCenter,
            "Evaluation Timeline / Stream Sequence"
        )
        painter.drawText(
            QRectF(w - pad_right - 100, h - 25, 100, 20),
            Qt.AlignmentFlag.AlignRight,
            f"T={max_x:.1f}s"
        )


# ─── Benchmark Worker Thread ────────────────────────────────────────────────

class StatsBenchmarkWorker(QThread):
    """
    Asynchronous empirical benchmark execution worker.
    Supports LLM Generation Throughput, Document C-Engine Speed,
    and FAISS Semantic Vector Search benchmarks.
    """
    log_message = pyqtSignal(str, str)  # (text, level)
    point_generated = pyqtSignal(float, float, str)  # (x, y, metric_type)
    stats_updated = pyqtSignal(dict)
    finished = pyqtSignal(dict)

    def __init__(self, mode: str = "nlp", num_tokens: int = 150):
        super().__init__()
        self.mode = mode
        self.num_tokens = num_tokens
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        if self.mode == "nlp":
            self._run_nlp_benchmark()
        elif self.mode == "pdf":
            self._run_pdf_engine_benchmark()
        elif self.mode == "vector":
            self._run_vector_benchmark()
        elif self.mode == "all":
            self._run_full_suite()

    def _run_nlp_benchmark(self):
        self.log_message.emit("INITIALIZING EMPIRICAL NLP INFERENCE BENCHMARK...", "INFO")
        start_ram = get_process_memory_mb()
        self.log_message.emit(f"Initial Process Working Set RAM: {start_ram:.2f} MB", "INFO")

        try:
            from llama_cpp import Llama
        except ImportError:
            self.log_message.emit("Error: llama-cpp-python is not installed.", "ERROR")
            self.finished.emit({})
            return

        from core.app_icon import get_resource_path
        model_path = get_resource_path(os.path.join("models", "MNIME-Core-V5-Q4_K_M.gguf"))
        if not os.path.exists(model_path):
            self.log_message.emit(f"Model file not found at: {model_path}", "ERROR")
            self.finished.emit({})
            return

        self.log_message.emit("Loading MNIME-Core-V5-Q4_K_M.gguf (auto GPU offload enabled)...", "INFO")
        t0_load = time.time()
        try:
            llm = Llama(
                model_path=model_path,
                n_gpu_layers=-1,
                n_ctx=2048,
                verbose=False
            )
        except Exception as e:
            self.log_message.emit(f"Failed to load GGUF model: {e}", "ERROR")
            self.finished.emit({})
            return

        load_sec = time.time() - t0_load
        post_load_ram = get_process_memory_mb()
        self.log_message.emit(f"Model loaded successfully in {load_sec:.2f}s (RAM: {post_load_ram:.2f} MB)", "SUCCESS")

        prompt = (
            "Explain the technical advantages of running an integrated 1.5B quantized language model "
            "directly on-device with C-accelerated document parsing versus sending files to a remote API."
        )
        self.log_message.emit(f"Evaluating prompt ({len(prompt)} chars)...", "INFO")

        t_start_eval = time.time()
        t_first_token = None
        tokens_received = 0
        token_timestamps = []

        try:
            stream = llm(
                f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n",
                max_tokens=self.num_tokens,
                stop=["<|im_end|>", "<|endoftext|>"],
                stream=True
            )

            for chunk in stream:
                if self._is_cancelled:
                    break
                now = time.time()
                if t_first_token is None:
                    t_first_token = now - t_start_eval
                    self.log_message.emit(f"Time to First Token (TTFT): {t_first_token:.3f}s", "METRIC")

                token_text = chunk["choices"][0]["text"]
                tokens_received += 1
                token_timestamps.append(now)

                # Compute instantaneous throughput over a sliding window
                elapsed = now - t_start_eval
                window = 6
                if len(token_timestamps) > window:
                    inst_throughput = window / (token_timestamps[-1] - token_timestamps[-window - 1])
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

        except Exception as e:
            self.log_message.emit(f"Inference error during benchmark: {e}", "ERROR")

        total_elapsed = time.time() - t_start_eval
        avg_throughput = (tokens_received / total_elapsed) if total_elapsed > 0 else 0.0
        peak_throughput = max((
            window / (token_timestamps[i] - token_timestamps[i - window])
            for window in [5]
            for i in range(window, len(token_timestamps))
        ), default=avg_throughput)

        self.log_message.emit(f"\n--- NLP INFERENCE BENCHMARK COMPLETE ---", "SUCCESS")
        self.log_message.emit(f"Tokens Generated: {tokens_received}", "METRIC")
        self.log_message.emit(f"Sustained Throughput: {avg_throughput:.2f} tokens/second", "METRIC")
        self.log_message.emit(f"Peak Throughput: {peak_throughput:.2f} tokens/second", "METRIC")
        self.log_message.emit(f"TTFT (Prefill Latency): {t_first_token:.3f}s" if t_first_token else "TTFT: N/A", "METRIC")
        self.log_message.emit(f"Final RAM Working Set: {get_process_memory_mb():.2f} MB", "INFO")

        res_data = {
            "mode": "nlp",
            "tokens": tokens_received,
            "throughput_avg": avg_throughput,
            "throughput_peak": peak_throughput,
            "ttft_ms": (t_first_token * 1000) if t_first_token else 0.0,
            "load_sec": load_sec,
            "ram_mb": get_process_memory_mb()
        }
        if self.mode != "all":
            self.finished.emit(res_data)
        return res_data

    def _run_pdf_engine_benchmark(self):
        self.log_message.emit("INITIALIZING C-ACCELERATED DOCUMENT ENGINE BENCHMARK...", "INFO")
        try:
            import pymupdf as fitz
        except ImportError:
            self.log_message.emit("Error: pymupdf is not installed.", "ERROR")
            self.finished.emit({})
            return

        # Generate a synthetic multi-page document in memory
        num_pages = 40
        self.log_message.emit(f"Synthesizing {num_pages}-page vector test document in memory...", "INFO")
        doc = fitz.open()
        t0 = time.time()
        for i in range(num_pages):
            page = doc.new_page(width=595, height=842)
            page.insert_text((50, 60), f"MNIME Engine Empirical Benchmark — Synthetic Page {i+1}", fontsize=14)
            page.insert_textbox(
                fitz.Rect(50, 90, 545, 750),
                ("High-performance on-device PDF document processing engine benchmark test. " * 30),
                fontsize=10
            )
            elapsed = time.time() - t0
            pages_sec = (i + 1) / max(elapsed, 0.001)
            self.point_generated.emit(elapsed, pages_sec, "tok_sec")
            self.stats_updated.emit({
                "throughput": pages_sec,
                "ttft": 0.0,
                "ram_mb": get_process_memory_mb(),
                "tokens": i + 1
            })

        gen_sec = time.time() - t0
        self.log_message.emit(f"Generated {num_pages} pages in {gen_sec:.3f}s ({num_pages/gen_sec:.1f} pages/s)", "METRIC")

        # Test Rasterization at 200 DPI
        self.log_message.emit("Benchmarking C-level pixmap rasterization throughput (200 DPI)...", "INFO")
        t_rast_start = time.time()
        for i, page in enumerate(doc):
            if self._is_cancelled: break
            pix = page.get_pixmap(dpi=200)
            elapsed = time.time() - t_rast_start
            speed = (i + 1) / max(elapsed, 0.001)
            self.point_generated.emit(elapsed, speed, "tok_sec")

        rast_sec = time.time() - t_rast_start
        rast_speed = num_pages / max(rast_sec, 0.001)
        self.log_message.emit(f"Rasterized {num_pages} pages in {rast_sec:.3f}s ({rast_speed:.1f} pages/s)", "METRIC")

        # Test Compaction & Deflation
        self.log_message.emit("Benchmarking garbage=4, deflate=True stream compaction...", "INFO")
        t_save = time.time()
        buf = doc.tobytes(garbage=4, deflate=True, clean=True)
        save_sec = time.time() - t_save
        doc.close()

        self.log_message.emit(f"Compaction completed in {save_sec:.3f}s (Output buffer: {len(buf)/1024:.1f} KB)", "SUCCESS")
        res_data = {
            "mode": "pdf",
            "pages": num_pages,
            "generation_speed": num_pages / gen_sec,
            "raster_speed": rast_speed,
            "compaction_sec": save_sec,
            "ram_mb": get_process_memory_mb()
        }
        if self.mode != "all":
            self.finished.emit(res_data)
        return res_data

    def _run_vector_benchmark(self) -> dict:
        self.log_message.emit("INITIALIZING FAISS VECTOR RETRIEVAL BENCHMARK...", "INFO")
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("TQDM_DISABLE", "1")
        os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
        try:
            from core.search_engine import get_embedding_model_path, SearchEngine
            from langchain_community.vectorstores import FAISS

            emb_path = get_embedding_model_path()
            self.log_message.emit(f"Loading local embedding model: {os.path.basename(emb_path)}...", "INFO")
            t_load = time.time()
            embeddings = SearchEngine.get_embeddings()
            self.log_message.emit(f"Embedding model ready in {time.time() - t_load:.2f}s", "SUCCESS")
        except Exception as e:
            self.log_message.emit(f"Vector search engine error: {e}", "ERROR")
            if self.mode != "all":
                self.finished.emit({})
            return {}

        self.log_message.emit("Synthesizing technical knowledge corpus & building FAISS L2 index...", "INFO")
        test_corpus = [
            "MNIME guarantees absolute user privacy through 100% offline, local neural execution. No network requests or telemetry pings leave the workstation.",
            "The FAISS vector similarity index operates directly in system RAM using optimized dense L2 distance and inner-product projections for sub-millisecond retrieval.",
            "Under Q4_K_M quantization, the 1.5B neural model provides high-fidelity document synthesis while keeping the working set under 2 GB.",
            "The document engine utilizes PyMuPDF C-bindings for rapid rasterization, rendering pages at over 120 pages per second at 200 DPI.",
            "Semantic bookmarking analyzes heading hierarchies and structural vectors to automate document table of contents generation.",
            "Smart index sampling extracts probe terms across sampled document pages to prune dense indexing latency without sacrificing recall.",
            "Windows OCR integration automatically kicks in when PDF pages contain rasterized or scanned image content without embedded font glyphs.",
            "Local neural inference runs with automated GPU layer offloading and AVX2 vector instructions for multi-threaded execution.",
            "High-concurrency document processing leverages zero-copy buffer views and compact binary serialization.",
            "Dynamic memory management purges model weights and vector stores on tool switch to prevent RAM fragmentation."
        ] * 4  # 40 dense vector chunks

        t_index = time.time()
        try:
            vectorstore = FAISS.from_texts(test_corpus, embeddings)
            index_sec = time.time() - t_index
            self.log_message.emit(f"FAISS vectorstore built: {len(test_corpus)} vectors indexed in {index_sec:.3f}s", "SUCCESS")
        except Exception as e:
            self.log_message.emit(f"Failed to build FAISS index: {e}", "ERROR")
            if self.mode != "all":
                self.finished.emit({})
            return {}

        queries = [
            "What are the privacy guarantees of local document processing?",
            "How does the FAISS vector index optimize memory footprint?",
            "What is the time-to-first-token latency under Q4_K_M quantization?",
            "Describe the architecture of the C-accelerated PDF engine.",
            "How are semantic bookmarks generated with the bundled model?",
            "Explain smart sampling heuristics during dense index creation.",
            "How is OCR handled for scanned PDF pages?",
            "What hardware acceleration modes are supported for inference?"
        ] * 3  # 24 test queries

        latencies = []
        t0 = time.time()
        for i, q in enumerate(queries):
            if self._is_cancelled:
                break
            t_q = time.time()
            res = SearchEngine.search(vectorstore, q, k=3)
            q_ms = (time.time() - t_q) * 1000
            latencies.append(q_ms)
            elapsed = time.time() - t0
            q_throughput = 1000.0 / max(q_ms, 0.001)
            cur_ram = get_process_memory_mb()
            self.point_generated.emit(elapsed, q_throughput, "tok_sec")
            self.point_generated.emit(elapsed, cur_ram, "ram_mb")
            self.stats_updated.emit({
                "throughput": q_throughput,
                "ttft": q_ms,
                "ram_mb": cur_ram,
                "tokens": i + 1
            })
            time.sleep(0.02)

        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
        min_lat = min(latencies, default=0.0)
        max_lat = max(latencies, default=0.0)
        avg_throughput = (len(latencies) / (time.time() - t0)) if (time.time() - t0) > 0 else 0.0

        self.log_message.emit("\n--- FAISS VECTOR RETRIEVAL BENCHMARK COMPLETE ---", "SUCCESS")
        self.log_message.emit(f"Executed {len(queries)} semantic vector searches over {len(test_corpus)} vectors.", "SUCCESS")
        self.log_message.emit(f"Average Query Latency: {avg_lat:.2f} ms ({avg_throughput:.1f} queries/s)", "METRIC")
        self.log_message.emit(f"Latency Range: min {min_lat:.2f} ms | peak {max_lat:.2f} ms", "METRIC")
        self.log_message.emit(f"Active Process RAM Working Set: {get_process_memory_mb():.2f} MB", "INFO")

        res_data = {
            "mode": "vector",
            "queries": len(queries),
            "vectors": len(test_corpus),
            "avg_latency_ms": avg_lat,
            "min_latency_ms": min_lat,
            "max_latency_ms": max_lat,
            "throughput_avg": avg_throughput,
            "ram_mb": get_process_memory_mb()
        }
        if self.mode != "all":
            self.finished.emit(res_data)
        return res_data

    def _run_full_suite(self):
        self.log_message.emit("=== EXECUTING COMPREHENSIVE MNIME BENCHMARK SUITE ===", "INFO")
        pdf_res = self._run_pdf_engine_benchmark()
        if self._is_cancelled:
            return
        time.sleep(0.5)
        vec_res = self._run_vector_benchmark()
        if self._is_cancelled:
            return
        time.sleep(0.5)
        nlp_res = self._run_nlp_benchmark()
        self.log_message.emit("\n=== COMPREHENSIVE BENCHMARK SUITE COMPLETED ===", "SUCCESS")
        self.finished.emit({
            "mode": "all",
            "pdf": pdf_res,
            "vector": vec_res,
            "nlp": nlp_res,
            "ram_mb": get_process_memory_mb()
        })


# ─── Stats Dialog UI ─────────────────────────────────────────────────────────

class StatsForNerdsDialog(QDialog):
    """
    Sleek, obsidian and neon-cyan Stats telemetry dashboard.
    Matches the expanded NLP interface aesthetic with real-time dynamic
    line chart generation, KPI badges, system resource breakdown, and interactive benchmarking.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MNIME — Stats")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(960, 740)

        self._drag_pos: Optional[QPoint] = None
        self._worker: Optional[StatsBenchmarkWorker] = None
        self._history_results: List[Dict[str, Any]] = []

        self._setup_ui()
        self._setup_dragging()
        self._start_system_monitor()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(15, 15, 15, 15)

        # Outer Glassmorphic Obsidian Frame
        self.frame = QFrame(self)
        self.frame.setStyleSheet("""
            QFrame {
                background-color: rgba(11, 15, 25, 248);
                border: 2px solid #00d2ff;
                border-radius: 14px;
            }
        """)

        # Drop shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 210, 255, 120))
        shadow.setOffset(0, 0)
        self.frame.setGraphicsEffect(shadow)

        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(22, 18, 22, 20)
        frame_layout.setSpacing(12)

        # ─── Header Bar (Draggable Region) ───────────────────────────────────
        self.header_widget = QWidget()
        self.header_widget.setCursor(Qt.CursorShape.SizeAllCursor)
        self.header_widget.setToolTip("Click and drag to move Stats window")
        header = QHBoxLayout(self.header_widget)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(12)

        # Pulsing icon / title group
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(1)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("stats", "#00e5ff").pixmap(20, 20))
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        title_row.addWidget(icon_lbl)

        main_title = QLabel("STATS")
        main_title.setStyleSheet("""
            color: #00e5ff;
            font-size: 20px;
            font-weight: 900;
            letter-spacing: 2px;
            border: none;
            background: transparent;
        """)
        title_row.addWidget(main_title)
        title_row.addStretch()
        title_vbox.addLayout(title_row)

        subtitle = QLabel("MULTIMODAL NEURAL INTERFACE MACHINE EXTENSION")
        subtitle.setStyleSheet("""
            color: #94a3b8;
            font-size: 9.5px;
            font-weight: 700;
            letter-spacing: 1.5px;
            border: none;
            background: transparent;
        """)
        title_vbox.addWidget(subtitle)

        # Elegant Cursive Pronunciation
        phonetic = QLabel("nigh.mh")
        phonetic.setStyleSheet("""
            color: #00e5ff;
            font-family: "Segoe Script", "Brush Script MT", "Lucida Handwriting", cursive;
            font-style: italic;
            font-size: 13.5px;
            border: none;
            background: transparent;
            margin-top: 1px;
        """)
        title_vbox.addWidget(phonetic)

        header.addLayout(title_vbox)
        header.addStretch()

        # Window Controls (Close button)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(22, 33, 50, 180);
                color: #00e5ff;
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #1f2d42;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: white;
                border: 1px solid #ff7b72;
            }
        """)
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)

        frame_layout.addWidget(self.header_widget)

        # ─── KPI Telemetry Badges ─────────────────────────────────────────────
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(10)

        self.kpi_throughput = self._create_kpi_card("THROUGHPUT", "0.00", "tok/s", "#00e5ff")
        self.kpi_ttft = self._create_kpi_card("TTFT (LATENCY)", "0.0", "ms", "#38bdf8")
        self.kpi_ram = self._create_kpi_card("RAM FOOTPRINT", "0.0", "MB", "#39ff14")
        self.kpi_tokens = self._create_kpi_card("TOKENS / SAMPLES", "0", "units", "#ffd700")

        kpi_layout.addWidget(self.kpi_throughput)
        kpi_layout.addWidget(self.kpi_ttft)
        kpi_layout.addWidget(self.kpi_ram)
        kpi_layout.addWidget(self.kpi_tokens)
        frame_layout.addLayout(kpi_layout)

        # ─── System Resource Consumption Telemetry Panel ───────────────────────
        self.res_panel = QFrame()
        self.res_panel.setStyleSheet("""
            QFrame {
                background-color: rgba(13, 19, 32, 220);
                border: 1px solid #1e293b;
                border-left: 3px solid #00e5ff;
                border-radius: 8px;
            }
        """)
        res_vbox = QVBoxLayout(self.res_panel)
        res_vbox.setContentsMargins(14, 8, 14, 8)
        res_vbox.setSpacing(6)

        # Header row with title and active mode indicator badge
        res_header = QHBoxLayout()
        res_title = QLabel("SYSTEM RESOURCE CONSUMPTION BREAKDOWN")
        res_title.setStyleSheet("color: #00e5ff; font-size: 10px; font-weight: 900; letter-spacing: 1.2px; border: none;")
        res_header.addWidget(res_title)
        res_header.addStretch()

        self.mode_badge = QLabel("MODE: LIGHTWEIGHT (~1.0 GB RAM)")
        self.mode_badge.setStyleSheet("""
            color: #38bdf8;
            background-color: rgba(14, 165, 233, 0.12);
            border: 1px solid #0284c7;
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 9.5px;
            font-weight: 800;
            letter-spacing: 0.8px;
        """)
        res_header.addWidget(self.mode_badge)
        res_vbox.addLayout(res_header)

        # Telemetry columns: Total RAM, Base Runtime, Model Weights, Vector Index, Raster Buffer, Compute
        res_grid = QHBoxLayout()
        res_grid.setSpacing(10)

        self.sub_total_ram = self._create_res_item("TOTAL WORKING SET", "1,024 MB (1.00 GB)", "#ffffff")
        self.sub_base_ram = self._create_res_item("BASE FRAMEWORK", "~1.00 GB (PyQt6 + C-Engine)", "#94a3b8")
        self.sub_model_ram = self._create_res_item("NLP MODEL & KV", "0 MB (Unloaded)", "#64748b")
        self.sub_vector_ram = self._create_res_item("VECTOR / FAISS", "~25 MB (Dense L2)", "#94a3b8")
        self.sub_render_ram = self._create_res_item("DOC RENDERING", "~15–40 MB (Page Pixmaps)", "#94a3b8")
        self.sub_compute = self._create_res_item("HARDWARE ACCEL", "Auto GPU (-1) / AVX2", "#39ff14")

        res_grid.addLayout(self.sub_total_ram)
        res_grid.addLayout(self.sub_base_ram)
        res_grid.addLayout(self.sub_model_ram)
        res_grid.addLayout(self.sub_vector_ram)
        res_grid.addLayout(self.sub_render_ram)
        res_grid.addLayout(self.sub_compute)

        res_vbox.addLayout(res_grid)
        frame_layout.addWidget(self.res_panel)

        # ─── Dynamic Line Chart & Control Deck ────────────────────────────────
        chart_deck = QHBoxLayout()
        chart_deck.setSpacing(12)

        # Left: Line Chart Widget
        chart_vbox = QVBoxLayout()
        chart_vbox.setSpacing(6)

        # Chart Metric Tabs / Controls
        metric_bar = QHBoxLayout()
        metric_bar.setSpacing(6)

        self.btn_metric_toks = self._create_pill_btn("Throughput (tok/s)", active=True)
        self.btn_metric_toks.clicked.connect(lambda: self._switch_metric("tok_sec"))

        self.btn_metric_ram = self._create_pill_btn("RAM Working Set (MB)", active=False)
        self.btn_metric_ram.clicked.connect(lambda: self._switch_metric("ram_mb"))

        self.btn_metric_clear = QPushButton("Clear Plot")
        self.btn_metric_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_metric_clear.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748b;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover { color: #f87171; border-color: #f87171; }
        """)
        self.btn_metric_clear.clicked.connect(self._clear_chart)

        metric_bar.addWidget(self.btn_metric_toks)
        metric_bar.addWidget(self.btn_metric_ram)
        metric_bar.addStretch()
        metric_bar.addWidget(self.btn_metric_clear)

        chart_vbox.addLayout(metric_bar)

        self.chart = DynamicLineChart(self)
        self.chart.setStyleSheet("border: 1px solid #1e293b; border-radius: 8px;")
        chart_vbox.addWidget(self.chart, stretch=1)

        chart_deck.addLayout(chart_vbox, stretch=3)

        # Right: Interactive Benchmark Controls
        controls_panel = QFrame()
        controls_panel.setStyleSheet("""
            QFrame {
                background-color: rgba(14, 21, 35, 200);
                border: 1px solid #1f2d42;
                border-radius: 8px;
            }
        """)
        panel_layout = QVBoxLayout(controls_panel)
        panel_layout.setContentsMargins(14, 14, 14, 14)
        panel_layout.setSpacing(10)

        panel_title = QLabel("BENCHMARK CONTROL")
        panel_title.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 900; letter-spacing: 1px; border: none;")
        panel_layout.addWidget(panel_title)

        test_lbl = QLabel("Test Routine:")
        test_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; border: none;")
        panel_layout.addWidget(test_lbl)

        self.test_combo = QComboBox()
        self.test_combo.addItems([
            "MNIME-Core NLP Generation",
            "PDF Engine C-Throughput",
            "FAISS Vector Retrieval",
            "Comprehensive Full Suite"
        ])
        self.test_combo.setStyleSheet("""
            QComboBox {
                background-color: #162032;
                color: #e2e8f0;
                border: 1px solid #2d3b55;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
            }
            QComboBox QAbstractItemView {
                background-color: #0b0f19;
                color: #00e5ff;
                selection-background-color: #005f8c;
            }
        """)
        panel_layout.addWidget(self.test_combo)

        length_lbl = QLabel("Target Token Depth:")
        length_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; border: none;")
        panel_layout.addWidget(length_lbl)

        self.length_combo = QComboBox()
        self.length_combo.addItems(["Quick (50 tokens)", "Standard (150 tokens)", "Stress (300 tokens)"])
        self.length_combo.setCurrentIndex(1)
        self.length_combo.setStyleSheet("""
            QComboBox {
                background-color: #162032;
                color: #e2e8f0;
                border: 1px solid #2d3b55;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
            }
        """)
        panel_layout.addWidget(self.length_combo)

        panel_layout.addStretch()

        self.run_btn = QPushButton("RUN BENCHMARK")
        self.run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_btn.setFixedHeight(38)
        self.run_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #005f8c, stop:1 #00a8e8);
                color: #ffffff;
                border: 1px solid #00e5ff;
                border-radius: 7px;
                font-weight: 900;
                font-size: 12px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0077b6, stop:1 #00d2ff);
            }
            QPushButton:disabled {
                background: #1e293b;
                color: #64748b;
                border: 1px solid #334155;
            }
        """)
        self.run_btn.clicked.connect(self._start_benchmark)
        panel_layout.addWidget(self.run_btn)

        self.export_btn = QPushButton("Export Telemetry (JSON)")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setFixedHeight(28)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94a3b8;
                border: 1px solid #273549;
                border-radius: 6px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #38bdf8;
                border-color: #38bdf8;
            }
        """)
        self.export_btn.clicked.connect(self._export_telemetry)
        panel_layout.addWidget(self.export_btn)

        chart_deck.addWidget(controls_panel, stretch=1)
        frame_layout.addLayout(chart_deck, stretch=3)

        # ─── Terminal Log Output ──────────────────────────────────────────────
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setFixedHeight(120)
        self.terminal.setStyleSheet("""
            QTextEdit {
                background-color: rgba(9, 13, 20, 230);
                color: #38bdf8;
                border: 1px solid #1c2738;
                border-radius: 8px;
                padding: 8px 12px;
                font-family: "Consolas", monospace;
                font-size: 11px;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: #253347;
                border-radius: 4px;
            }
        """)
        frame_layout.addWidget(self.terminal)

        root_layout.addWidget(self.frame)

        # Initial Welcome Message in Terminal
        self._append_log("MNIME Stats & Performance Telemetry Console ready.", "INFO")
        self._append_log("Bundled Model: MNIME-Core-V5-Q4_K_M.gguf | GPU Layer Offloading: Auto (-1)", "INFO")

    def _create_res_item(self, header: str, value: str, val_color: str) -> QVBoxLayout:
        vbox = QVBoxLayout()
        vbox.setSpacing(2)
        hdr = QLabel(header)
        hdr.setStyleSheet("color: #64748b; font-size: 8px; font-weight: 800; letter-spacing: 0.8px; border: none;")
        val = QLabel(value)
        val.setObjectName("res_value")
        val.setStyleSheet(f"color: {val_color}; font-size: 10.5px; font-weight: 700; font-family: 'Consolas', monospace; border: none;")
        vbox.addWidget(hdr)
        vbox.addWidget(val)
        return vbox

    def _set_res_val(self, layout: QVBoxLayout, value: str, color_hex: Optional[str] = None):
        lbl = layout.itemAt(1).widget()
        if isinstance(lbl, QLabel):
            lbl.setText(value)
            if color_hex:
                lbl.setStyleSheet(f"color: {color_hex}; font-size: 10.5px; font-weight: 700; font-family: 'Consolas', monospace; border: none;")

    def _create_kpi_card(self, title: str, val: str, unit: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setFixedHeight(64)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(14, 21, 35, 190);
                border: 1px solid #1f2d42;
                border-left: 3px solid {color_hex};
                border-radius: 8px;
            }}
        """)
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(12, 6, 12, 6)
        vbox.setSpacing(1)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 800; letter-spacing: 1px; border: none;")
        vbox.addWidget(lbl_t)

        val_hbox = QHBoxLayout()
        val_hbox.setSpacing(4)

        val_lbl = QLabel(val)
        val_lbl.setObjectName("val_label")
        val_lbl.setStyleSheet(f"color: #ffffff; font-size: 18px; font-weight: 900; font-family: 'Consolas'; border: none;")
        val_hbox.addWidget(val_lbl)

        unit_lbl = QLabel(unit)
        unit_lbl.setStyleSheet(f"color: {color_hex}; font-size: 10px; font-weight: 700; border: none; margin-top: 4px;")
        val_hbox.addWidget(unit_lbl)
        val_hbox.addStretch()

        vbox.addLayout(val_hbox)
        return card

    def _update_kpi(self, card: QFrame, val_str: str):
        lbl = card.findChild(QLabel, "val_label")
        if lbl:
            lbl.setText(val_str)

    def _create_pill_btn(self, text: str, active: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_pill_btn(btn, active)
        return btn

    def _style_pill_btn(self, btn: QPushButton, active: bool):
        if active:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #005f8c;
                    color: #00e5ff;
                    border: 1px solid #00e5ff;
                    border-radius: 6px;
                    padding: 5px 12px;
                    font-size: 10.5px;
                    font-weight: bold;
                }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #162032;
                    color: #94a3b8;
                    border: 1px solid #1f2d42;
                    border-radius: 6px;
                    padding: 5px 12px;
                    font-size: 10.5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    color: #e2e8f0;
                    border-color: #38bdf8;
                }
            """)

    def _switch_metric(self, metric_type: str):
        self._style_pill_btn(self.btn_metric_toks, metric_type == "tok_sec")
        self._style_pill_btn(self.btn_metric_ram, metric_type == "ram_mb")
        if metric_type == "tok_sec":
            self.chart.set_metric("Throughput", "tok/s", "#00e5ff")
        else:
            self.chart.set_metric("RAM Footprint", "MB", "#39ff14")

    def _clear_chart(self):
        self.chart.clear()
        self._update_kpi(self.kpi_throughput, "0.00")
        self._update_kpi(self.kpi_ttft, "0.0")
        self._update_kpi(self.kpi_tokens, "0")

    def _start_system_monitor(self):
        self._sys_timer = QTimer(self)
        self._sys_timer.timeout.connect(self._sample_system_telemetry)
        self._sys_timer.start(1000)

    def _sample_system_telemetry(self):
        ram_mb = get_process_memory_mb()
        self._update_kpi(self.kpi_ram, f"{ram_mb:.1f}")

        # Update detailed resource breakdown
        ram_gb = ram_mb / 1024.0
        self._set_res_val(self.sub_total_ram, f"{ram_mb:.0f} MB ({ram_gb:.2f} GB)")

        # Differentiate Lightweight baseline (~1.0 GB) vs Active NLP (~1.8–1.9 GB)
        if ram_mb >= 1400.0:
            self.mode_badge.setText("MODE: NLP ACTIVE (~1.8–1.9 GB RAM)")
            self.mode_badge.setStyleSheet("""
                color: #39ff14;
                background-color: rgba(57, 255, 20, 0.12);
                border: 1px solid #22c55e;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 9.5px;
                font-weight: 800;
                letter-spacing: 0.8px;
            """)
            self._set_res_val(self.sub_model_ram, "~850 MB (Active Q4_K_M)", "#39ff14")
        else:
            self.mode_badge.setText("MODE: LIGHTWEIGHT (~1.0 GB RAM)")
            self.mode_badge.setStyleSheet("""
                color: #38bdf8;
                background-color: rgba(14, 165, 233, 0.12);
                border: 1px solid #0284c7;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 9.5px;
                font-weight: 800;
                letter-spacing: 0.8px;
            """)
            self._set_res_val(self.sub_model_ram, "0 MB (Unloaded / Standby)", "#64748b")

    def _append_log(self, text: str, tag: str = "INFO"):
        tag_colors = {
            "INFO": "#38bdf8",
            "METRIC": "#39ff14",
            "SUCCESS": "#00e5ff",
            "ERROR": "#f87171"
        }
        col = tag_colors.get(tag, "#38bdf8")
        timestamp = time.strftime("%H:%M:%S")
        formatted = f'<font color="#64748b">[{timestamp}]</font> <font color="{col}"><b>[{tag}]</b></font> {text}'
        self.terminal.append(formatted)

    def _start_benchmark(self):
        self.run_btn.setEnabled(False)
        self.run_btn.setText("BENCHMARK RUNNING...")
        self.chart.clear()

        idx = self.test_combo.currentIndex()
        modes = ["nlp", "pdf", "vector", "all"]
        mode = modes[idx]

        token_counts = [50, 150, 300]
        num_tokens = token_counts[self.length_combo.currentIndex()]

        self._worker = StatsBenchmarkWorker(mode=mode, num_tokens=num_tokens)
        self._worker.log_message.connect(self._append_log)
        self._worker.point_generated.connect(self._on_point_generated)
        self._worker.stats_updated.connect(self._on_stats_updated)
        self._worker.finished.connect(self._on_benchmark_finished)
        self._worker.start()

    def _on_point_generated(self, x: float, y: float, mtype: str):
        if mtype == "tok_sec" and self.btn_metric_toks.styleSheet().find("#005f8c") != -1:
            self.chart.add_point(x, y)
        elif mtype == "ram_mb" and self.btn_metric_ram.styleSheet().find("#005f8c") != -1:
            self.chart.add_point(x, y)

    def _on_stats_updated(self, stats: dict):
        if "throughput" in stats:
            self._update_kpi(self.kpi_throughput, f"{stats['throughput']:.2f}")
        if "ttft" in stats and stats["ttft"] > 0:
            self._update_kpi(self.kpi_ttft, f"{stats['ttft']:.1f}")
        if "ram_mb" in stats:
            self._update_kpi(self.kpi_ram, f"{stats['ram_mb']:.1f}")
        if "tokens" in stats:
            self._update_kpi(self.kpi_tokens, str(stats["tokens"]))

    def _on_benchmark_finished(self, results: dict):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("RUN BENCHMARK")
        if results:
            self._history_results.append({
                "timestamp": time.time(),
                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "results": results
            })

    def _export_telemetry(self):
        if not self._history_results:
            self._append_log("No benchmark telemetry recorded yet to export.", "INFO")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Benchmark Telemetry",
            "mnime_telemetry.json",
            "JSON Files (*.json)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self._history_results, f, indent=2)
                self._append_log(f"Telemetry successfully exported to {path}", "SUCCESS")
            except Exception as e:
                self._append_log(f"Failed to export telemetry: {e}", "ERROR")

    # ─── Frameless Window Dragging & Event Handling ──────────────────────────
    def _setup_dragging(self):
        """Install event filtering on frame, header, and child labels for smooth window moving."""
        self.installEventFilter(self)
        self.frame.installEventFilter(self)
        if hasattr(self, "header_widget") and self.header_widget:
            self.header_widget.installEventFilter(self)
        for child in self.frame.findChildren(QLabel):
            child.installEventFilter(self)

    def _is_interactive(self, widget: Optional[QWidget]) -> bool:
        """Check if widget is an interactive control that should consume its own mouse events."""
        if widget is None:
            return False
        from PyQt6.QtWidgets import QPushButton, QComboBox, QTextEdit, QScrollBar, QAbstractSpinBox
        curr = widget
        while curr and curr != self:
            if isinstance(curr, (QPushButton, QComboBox, QTextEdit, QScrollBar, QAbstractSpinBox, DynamicLineChart)):
                return True
            curr = curr.parentWidget()
        return False

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                pos = event.globalPosition().toPoint()
                child = self.childAt(self.mapFromGlobal(pos))
                if not self._is_interactive(child):
                    wh = self.windowHandle()
                    if wh and hasattr(wh, "startSystemMove") and wh.startSystemMove():
                        return True
                    self._drag_pos = pos - self.pos()
                    self.grabMouse()
                    return True
        elif event.type() == QEvent.Type.MouseMove:
            if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos') and self._drag_pos is not None:
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                return True
        elif event.type() == QEvent.Type.MouseButtonRelease:
            if hasattr(self, '_drag_pos') and self._drag_pos is not None:
                self._drag_pos = None
                if self.mouseGrabber() == self:
                    self.releaseMouse()
                return True
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.globalPosition().toPoint()
            child = self.childAt(self.mapFromGlobal(pos))
            if not self._is_interactive(child):
                wh = self.windowHandle()
                if wh and hasattr(wh, "startSystemMove") and wh.startSystemMove():
                    event.accept()
                    return
                self._drag_pos = pos - self.pos()
                self.grabMouse()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos') and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        if self.mouseGrabber() == self:
            self.releaseMouse()
        super().mouseReleaseEvent(event)


# ─── Standalone Runner Window ───────────────────────────────────────────────

class StatsForNerdsWindow(QMainWindow):
    """Standalone window launcher for benchmark.py integration."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MNIME — Stats Telemetry")
        self.dialog = StatsForNerdsDialog(self)
        self.setCentralWidget(self.dialog.frame)
        self.resize(960, 740)
        self.setStyleSheet("QMainWindow { background-color: #0b0f19; }")


StatsWindow = StatsForNerdsWindow
StatsDialog = StatsForNerdsDialog


def show_stats(parent=None) -> StatsForNerdsDialog:
    """Helper to open the Stats dialog floating/non-modal."""
    dialog = StatsForNerdsDialog(parent)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    return dialog


show_nerds = show_stats
show_stats_for_nerds = show_stats
