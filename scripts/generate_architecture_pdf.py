"""
MNIME - System Architecture & Subsystem Schematics PDF Generator
Generates a high-fidelity, interactive architectural specification PDF manual with 
document bookmarks, layer schematics, module references, and auto-generated cover preview.
"""

import os
import sys
import math
from pathlib import Path
from typing import List, Dict, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    Table, TableStyle, NextPageTemplate, PageBreak
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfgen import canvas as pdfgen_canvas

import pymupdf

# ─── Color Palette ────────────────────────────────────────────────────────────
BG_DARK        = colors.HexColor("#0b0f19")
BG_CARD        = colors.HexColor("#111827")
BG_CARD_LIGHT  = colors.HexColor("#161f30")
BG_SECTION     = colors.HexColor("#0d1526")
ACCENT_CYAN    = colors.HexColor("#00e5ff")
ACCENT_BLUE    = colors.HexColor("#00a8e8")
ACCENT_DIM     = colors.HexColor("#005f8c")
TEXT_PRIMARY   = colors.HexColor("#e8eaf6")
TEXT_SECONDARY = colors.HexColor("#90a4ae")
TEXT_MUTED     = colors.HexColor("#546e7a")
NEON_GREEN     = colors.HexColor("#39ff14")
BORDER_COLOR   = colors.HexColor("#1f2737")
BORDER_BRIGHT  = colors.HexColor("#2a374f")
GOLD           = colors.HexColor("#ffd700")
WHITE          = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 16 * mm
CONTENT_W = PAGE_W - 2 * MARGIN


# ─── Two-Pass Numbered Canvas for Dynamic Total Page Count ────────────────────

class NumberedCanvas(pdfgen_canvas.Canvas):
    """Two-pass canvas for total page count and dynamic running headers/footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            if self._pageNumber > 1:
                self.draw_header_footer(num_pages)
            pdfgen_canvas.Canvas.showPage(self)
        pdfgen_canvas.Canvas.save(self)

    def draw_header_footer(self, total_pages):
        self.saveState()
        w, h = self._pagesize

        # Running Header
        self.setFillColor(BG_SECTION)
        self.rect(0, h - 13 * mm, w, 13 * mm, fill=1, stroke=0)
        self.setFillColor(ACCENT_CYAN)
        self.rect(0, h - 1.5, w, 1.5, fill=1, stroke=0)

        self.setFillColor(TEXT_SECONDARY)
        self.setFont("Helvetica-Bold", 7.5)
        self.drawString(MARGIN, h - 8.5 * mm, "MNIME")
        self.setFont("Helvetica", 7.5)
        self.setFillColor(TEXT_MUTED)
        self.drawString(MARGIN + 38, h - 8.5 * mm, "|   System Architecture & Subsystem Schematics")

        self.setFillColor(ACCENT_CYAN)
        self.setFont("Helvetica-Bold", 7.5)
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(w - MARGIN, h - 8.5 * mm, page_str)

        # Running Footer
        self.setFillColor(BG_SECTION)
        self.rect(0, 0, w, 9 * mm, fill=1, stroke=0)
        self.setFillColor(BORDER_COLOR)
        self.rect(0, 9 * mm, w, 0.8, fill=1, stroke=0)

        self.setFillColor(TEXT_MUTED)
        self.setFont("Helvetica", 7)
        self.drawString(MARGIN, 3.5 * mm, "Source: Architecture Blueprint   |   Bellevue College AISD   |   kyledeanml/MNIME")

        self.setFillColor(ACCENT_BLUE)
        self.drawRightString(w - MARGIN, 3.5 * mm, "Windows 11 (x64)   |   Release 2.1")
        self.restoreState()


class GlowLine(Flowable):
    """Cyan glowing rule."""
    def __init__(self, width: float, thickness: float = 0.8):
        super().__init__()
        self.width = width
        self.thickness = thickness
        self._height = thickness + 4

    def wrap(self, aW, aH):
        return self.width, self._height

    def draw(self):
        c = self.canv
        for alpha, expand in [(0.06, 5), (0.15, 2.5), (0.4, 1.2), (1.0, 0)]:
            c.setStrokeColor(ACCENT_CYAN)
            c.setLineWidth(self.thickness + expand * 2)
            c.setStrokeAlpha(alpha)
            c.line(0, self._height / 2, self.width, self._height / 2)
        c.setStrokeAlpha(1.0)


class SectionTag(Flowable):
    """A pill-shaped label for section headers."""
    def __init__(self, text: str, width: float = CONTENT_W):
        super().__init__()
        self.text = text
        self.width = width
        self._height = 10 * mm

    def wrap(self, aW, aH):
        return self.width, self._height

    def draw(self):
        c = self.canv
        h = self._height
        # background
        c.setFillColor(BG_SECTION)
        c.setStrokeColor(ACCENT_CYAN)
        c.setLineWidth(0.6)
        c.roundRect(0, 0, self.width, h, 4, fill=1, stroke=1)
        # accent bar left
        c.setFillColor(ACCENT_CYAN)
        c.rect(0, 0, 3.5, h, fill=1, stroke=0)
        # text
        c.setFillColor(ACCENT_CYAN)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(10, h / 2 - 3, self.text.upper())


class CoverPage(Flowable):
    """High-aesthetic front cover with interactive styling and 5D Penteract projection."""
    def __init__(self, w: float, h: float, version: str = "2.1", date_str: str = "October 2026"):
        super().__init__()
        self.w = w
        self.h = h
        self.version = version
        self.date_str = date_str

    def wrap(self, aW, aH):
        return self.w, self.h

    def draw(self):
        c = self.canv
        w, h = self.w, self.h

        # 1. Dark Base
        c.setFillColor(BG_DARK)
        c.rect(0, 0, w, h, fill=1, stroke=0)

        # 2. Geometric Grid Pattern
        c.setStrokeColor(BORDER_COLOR)
        c.setLineWidth(0.4)
        c.setStrokeAlpha(0.35)
        for x in range(0, int(w), 24):
            c.line(x, 0, x, h)
        for y in range(0, int(h), 24):
            c.line(0, y, w, y)
        c.setStrokeAlpha(1.0)

        # 3. Glowing Laser Top Bar
        c.setFillColor(ACCENT_CYAN)
        c.rect(0, h - 4, w, 4, fill=1, stroke=0)

        # 4. Central Vector 5D Projection & Neon Green Orbiting Document
        cx = w / 2
        cy_logo = h * 0.63
        
        # Glow halo
        for radius, alpha in [(110, 0.03), (85, 0.06), (60, 0.12), (40, 0.2)]:
            c.setFillColor(ACCENT_CYAN)
            c.setFillAlpha(alpha)
            c.circle(cx, cy_logo, radius, fill=1, stroke=0)
        c.setFillAlpha(1.0)

        # Render 5-cube projection lines (Penteract representation)
        r = 52.0
        layers = [
            (r * 1.00, ACCENT_CYAN, 1.0, 1.2),
            (r * 0.72, ACCENT_BLUE, 0.85, 0.9),
            (r * 0.44, ACCENT_DIM, 0.60, 0.7),
            (r * 0.22, WHITE, 0.90, 0.6)
        ]
        
        for radius, col, stroke_alpha, lw in layers:
            pts = []
            for i in range(8):
                angle = math.radians(45 * i - 22.5)
                px = cx + radius * math.cos(angle)
                py = cy_logo + radius * math.sin(angle)
                pts.append((px, py))
            
            c.setStrokeColor(col)
            c.setStrokeAlpha(stroke_alpha)
            c.setLineWidth(lw)
            for i in range(8):
                c.line(pts[i][0], pts[i][1], pts[(i + 1) % 8][0], pts[(i + 1) % 8][1])
                c.line(pts[i][0], pts[i][1], pts[(i + 3) % 8][0], pts[(i + 3) % 8][1])
            
            # Inner cross lines
            for i in range(4):
                c.line(pts[i][0], pts[i][1], pts[i + 4][0], pts[i + 4][1])
                
        # Orbiting neon-green document file
        doc_angle = math.radians(35)
        doc_orbit_r = r * 1.35
        dx = cx + doc_orbit_r * math.cos(doc_angle)
        dy = cy_logo + doc_orbit_r * math.sin(doc_angle) * 0.65
        
        c.setStrokeAlpha(1.0)
        c.setFillColor(colors.HexColor("#0d2416"))
        c.setStrokeColor(NEON_GREEN)
        c.setLineWidth(1.4)
        c.rect(dx - 14, dy - 18, 28, 36, fill=1, stroke=1)
        
        # Document text lines
        c.setFillColor(NEON_GREEN)
        c.setStrokeColor(NEON_GREEN)
        c.line(dx - 8, dy + 8, dx + 6, dy + 8)
        c.line(dx - 8, dy + 2, dx + 8, dy + 2)
        c.line(dx - 8, dy - 4, dx + 4, dy - 4)
        c.line(dx - 8, dy - 10, dx + 8, dy - 10)

        # 5. Typography: Main Title & Subtitle
        c.setFont("Helvetica-Bold", 36)
        c.setFillColor(WHITE)
        c.drawCentredString(cx, h * 0.44, "M N I M E")

        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(ACCENT_CYAN)
        c.drawCentredString(cx, h * 0.40, "PROJECT ARCHITECTURE & SUBSYSTEM SCHEMATICS")

        c.setFont("Helvetica", 9.5)
        c.setFillColor(TEXT_SECONDARY)
        c.drawCentredString(cx, h * 0.375, "Structural Topology, Neural Concurrency & Subsystem Dataflow")

        # 6. Metadata Card
        card_w = 460
        card_h = 105
        card_x = (w - card_w) / 2
        card_y = h * 0.16

        c.setFillColor(BG_CARD)
        c.setStrokeColor(BORDER_BRIGHT)
        c.setLineWidth(1.0)
        c.roundRect(card_x, card_y, card_w, card_h, 6, fill=1, stroke=1)

        # Left glow pill
        c.setFillColor(ACCENT_CYAN)
        c.roundRect(card_x + 12, card_y + card_h - 22, 60, 14, 3, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(BG_DARK)
        c.drawCentredString(card_x + 42, card_y + card_h - 18, f"v{self.version}")

        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(WHITE)
        c.drawString(card_x + 80, card_y + card_h - 18, "Production Architecture Blueprint  |  Windows 11 (x64)")

        # Metadata rows
        meta_items = [
            ("Lead Architect:", "Kyle Bauer / kyledeanml (Bellevue College AISD)"),
            ("Interface Subsystem:", "PyQt6 6.7+ Frameless Obsidian Desktop Engine (60 FPS)"),
            ("Document Engine:", "PyMuPDF (C-Accelerated Fitz Core) & Win32 GDI Spooler"),
            ("Neural Subsystem:", "MNIME-Core 1.5B (GGUF Q4_K_M) + Neural Assimilation Engine"),
            ("Vector Persistence:", "FAISS Vector Store + Persistent %LOCALAPPDATA% Global Index")
        ]

        row_y = card_y + card_h - 38
        for label, val in meta_items:
            c.setFont("Helvetica-Bold", 7.5)
            c.setFillColor(ACCENT_CYAN)
            c.drawString(card_x + 16, row_y, label)

            c.setFont("Helvetica", 7.5)
            c.setFillColor(TEXT_PRIMARY)
            c.drawString(card_x + 115, row_y, val)
            row_y -= 13

        # 7. Bottom Badges
        badges = ["60 FPS Native UI", "0% Network Traffic", "TIES Weight Assimilation", "Dual Vector Memory", "Win32 Taskbar GDI"]
        badge_x = (w - (len(badges) * 88)) / 2
        by = h * 0.09
        for b in badges:
            c.setFillColor(BG_CARD_LIGHT)
            c.setStrokeColor(BORDER_COLOR)
            c.setLineWidth(0.6)
            c.roundRect(badge_x, by, 80, 15, 3, fill=1, stroke=1)
            c.setFont("Helvetica-Bold", 6.8)
            c.setFillColor(TEXT_SECONDARY)
            c.drawCentredString(badge_x + 40, by + 4.5, b)
            badge_x += 88

        # Bottom accent
        c.setFillColor(ACCENT_CYAN)
        c.rect(0, 0, w, 2.5, fill=1, stroke=0)


# ─── Style Definitions ────────────────────────────────────────────────────────

def build_styles() -> Dict[str, ParagraphStyle]:
    s = {}
    s["title"] = ParagraphStyle(
        "title", fontName="Helvetica-Bold", fontSize=18, textColor=WHITE,
        spaceAfter=4, spaceBefore=6, leading=22
    )
    s["h1"] = ParagraphStyle(
        "h1", fontName="Helvetica-Bold", fontSize=13, textColor=ACCENT_CYAN,
        spaceAfter=4, spaceBefore=12, leading=16
    )
    s["h2"] = ParagraphStyle(
        "h2", fontName="Helvetica-Bold", fontSize=10, textColor=WHITE,
        spaceAfter=3, spaceBefore=7, leading=13
    )
    s["body"] = ParagraphStyle(
        "body", fontName="Helvetica", fontSize=8.5, textColor=TEXT_PRIMARY,
        spaceAfter=4, leading=12
    )
    s["body_muted"] = ParagraphStyle(
        "body_muted", fontName="Helvetica", fontSize=8, textColor=TEXT_SECONDARY,
        spaceAfter=3, leading=11
    )
    s["table_hdr"] = ParagraphStyle(
        "table_hdr", fontName="Helvetica-Bold", fontSize=8, textColor=ACCENT_CYAN,
        leading=10
    )
    s["table_cell"] = ParagraphStyle(
        "table_cell", fontName="Helvetica", fontSize=7.5, textColor=TEXT_PRIMARY,
        leading=10
    )
    s["table_cell_code"] = ParagraphStyle(
        "table_cell_code", fontName="Courier-Bold", fontSize=7.5, textColor=ACCENT_CYAN,
        leading=10
    )
    s["table_cell_green"] = ParagraphStyle(
        "table_cell_green", fontName="Courier-Bold", fontSize=7.5, textColor=NEON_GREEN,
        leading=10
    )
    s["card_title"] = ParagraphStyle(
        "card_title", fontName="Helvetica-Bold", fontSize=9, textColor=ACCENT_CYAN,
        leading=11
    )
    s["card_desc"] = ParagraphStyle(
        "card_desc", fontName="Helvetica", fontSize=7.8, textColor=TEXT_SECONDARY,
        leading=11
    )
    return s


# ─── Document Generator ───────────────────────────────────────────────────────

def generate_pdf(output_pdf: str, cover_png: str):
    styles = build_styles()
    doc = BaseDocTemplate(
        output_pdf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN
    )

    frame_cover = Frame(0, 0, PAGE_W, PAGE_H, id="cover_frame", topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0)
    frame_content = Frame(MARGIN, MARGIN, CONTENT_W, PAGE_H - 2 * MARGIN, id="content_frame", topPadding=14 * mm, bottomPadding=10 * mm, leftPadding=0, rightPadding=0)

    def draw_content_bg(canvas, document):
        canvas.saveState()
        w, h = canvas._pagesize
        canvas.setFillColor(BG_DARK)
        canvas.rect(0, 0, w, h, fill=1, stroke=0)
        canvas.setFillColor(BORDER_COLOR)
        canvas.setFillAlpha(0.25)
        for x in range(int(MARGIN), int(w - MARGIN), 20):
            for y in range(int(MARGIN), int(h - MARGIN), 20):
                canvas.circle(x, y, 0.45, fill=1, stroke=0)
        canvas.restoreState()

    template_cover = PageTemplate(id="cover", frames=[frame_cover])
    template_content = PageTemplate(id="content", frames=[frame_content], onPage=draw_content_bg)
    doc.addPageTemplates([template_cover, template_content])

    story = []

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 1: COVER
    # ═════════════════════════════════════════════════════════════════════════
    story.append(CoverPage(PAGE_W, PAGE_H, version="2.1"))
    story.append(NextPageTemplate("content"))
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 2: SYSTEM TOPOLOGY & LAYER ARCHITECTURE
    # ═════════════════════════════════════════════════════════════════════════
    story.append(SectionTag("1. SYSTEM TOPOLOGY & LAYER SCHEMATIC"))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(
        "MNIME is engineered as a decoupled, multi-threaded desktop architecture designed for ultra-low latency, "
        "complete offline privacy, and zero telemetry. The system cleanly separates the presentation interface, document processing pipelines, "
        "neural intelligence, and semantic vector memory into four distinct functional tiers.",
        styles["body"]
    ))
    story.append(Spacer(1, 3 * mm))

    # Architecture 4-Tier Cards Table
    tiers = [
        ("Layer 1: Presentation & Human Interface (PyQt6 6.7+)",
         "ui/main_window.py, ui/carousel_view.py, ui/action_bar.py, ui/nerds.py, ui/file_dialog.py",
         "Obsidian dark metallic frameless shell. Provides 60 FPS non-blocking interaction, physics-driven particle vortex VFX, "
         "O(1) index drag-and-drop carousel ordering, custom file picker dialog, real-time performance telemetry HUD (Nerds), and magnetic detachable NLP chat console."),
        
        ("Layer 2: Document Processing & OS Integration Core",
         "core/pdf_engine.py, core/print_engine.py, core/app_icon.py, core/ipc.py, core/text_safety.py",
         "High-performance PyMuPDF (Fitz) C-level engine executing document merges, split, compress, image-to-PDF, and Word DOCX reconstruction. "
         "Includes single-instance named pipe IPC, prompt sanitization, high-DPI Windows print spooling, and Win32 taskbar registration."),
        
        ("Layer 3: Neural & Cognitive Subsystem",
         "core/nlp_engine.py, core/fusion_engine.py, models/MNIME-Core-1.5B-Q4_K_M.gguf",
         "Singleton inference coordinator powered by llama.cpp. Executes quantized 1.5B parameter language modeling, dynamic LoRA adapter attachment, "
         "and the Neural Assimilation Engine for background asynchronous weight delta ingestion and TIES model merging."),
        
        ("Layer 4: Vector Memory & Semantic Indexing",
         "core/search_engine.py, %LOCALAPPDATA%\\MNIME\\global_vector_store",
         "Dual-tier retrieval-augmented generation (RAG). Binds in-memory FAISS indices for active documents with a persistent, cross-session "
         "global vector database. Features automatic fallback to Windows 11 OCR (WinSDK) for scanned image documents.")
    ]

    tier_flowables = []
    for title, modules, desc in tiers:
        card_content = [
            [Paragraph(f"<b>{title}</b>", styles["card_title"])],
            [Paragraph(f"<font color='{ACCENT_BLUE.hexval()}'>Key Modules:</font> <code>{modules}</code>", styles["table_cell"])],
            [Paragraph(desc, styles["card_desc"])]
        ]
        card_table = Table(card_content, colWidths=[CONTENT_W - 8])
        card_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
            ("BOX", (0, 0), (-1, -1), 0.8, BORDER_COLOR),
            ("LINELEFT", (0, 0), (0, -1), 3.0, ACCENT_CYAN),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        tier_flowables.append([card_table])
        tier_flowables.append([Spacer(1, 2 * mm)])

    t_tiers = Table(tier_flowables, colWidths=[CONTENT_W])
    t_tiers.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(t_tiers)
    story.append(Spacer(1, 3 * mm))

    # Concurrency Callout Box
    concurrency_box = [
        [Paragraph("<b>CONCURRENCY & THREAD ISOLATION MODEL</b>", styles["card_title"])],
        [Paragraph(
            "Heavy workloads (PyMuPDF document transformations, FAISS embedding indexing, and llama.cpp text generation) never execute on the main GUI thread. "
            "Instead, each job is wrapped in an isolated <code>core.worker.Worker(QThread)</code> instance with a thread-safe <code>progress_callback</code> signal. "
            "This architecture guarantees an uninterrupted 60 FPS UI rendering loop even during multi-gigabyte document operations.",
            styles["card_desc"]
        )]
    ]
    t_conc = Table(concurrency_box, colWidths=[CONTENT_W])
    t_conc.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_SECTION),
        ("BOX", (0, 0), (-1, -1), 1.0, ACCENT_CYAN),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_conc)

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 3: COMPONENT DIRECTORY & MODULE INDEX
    # ═════════════════════════════════════════════════════════════════════════
    story.append(SectionTag("2. COMPONENT DIRECTORY & MODULE INDEX"))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph(
        "Every file in the repository serves a distinct operational purpose within the MNIME ecosystem. "
        "The following index details component roles, subsystem categorizations, and thread affinities.",
        styles["body"]
    ))
    story.append(Spacer(1, 2 * mm))

    # Comprehensive Table
    modules_data = [
        ("Path / Component", "Subsystem", "Thread Affinity", "Architectural Role"),
        ("MNIME.py", "Bootstrapper", "Main Thread", "App entry point. Applies Dark Obsidian stylesheet & instantiates MainWindow."),
        ("core/pdf_engine.py", "Core Processing", "Worker Thread", "PyMuPDF C-level engine: Merge, Split, Compress, DOCX, JPG/TXT conversion."),
        ("core/nlp_engine.py", "Neural Cognition", "Worker Thread", "Singleton GGUF llama.cpp inference engine with dynamic LoRA adapter hot-swapping."),
        ("core/fusion_engine.py", "Neural Cognition", "Async Worker", "Neural Assimilation Engine: TIES weight-fusion & donor parameter absorption."),
        ("core/search_engine.py", "Semantic Memory", "Worker Thread", "FAISS vector store, bge-small-en embeddings, and WinSDK OCR pipeline."),
        ("core/worker.py", "Concurrency", "Worker Thread", "Generic QThread wrapper with real-time Qt progress signaling & error boundary."),
        ("core/file_item.py", "Data Model", "Main Thread", "File item encapsulating path, metadata, thumbnail pixmap cache & status flags."),
        ("core/ipc.py", "OS Integration", "Main Thread", "Named pipe server enforcing single-instance execution & passing file args."),
        ("core/app_icon.py", "OS Integration", "Main Thread", "Win32 AppUserModelID taskbar registration, GDI ICO embedding & desktop links."),
        ("core/text_safety.py", "Security & NLP", "Synchronous", "Input sanitization, prompt injection defense, and conversational fallback routing."),
        ("core/print_engine.py", "OS Integration", "Worker Thread", "High-DPI GDI printer rendering and physical document output spooler."),
        ("ui/main_window.py", "Presentation", "Main Thread", "Primary coordinator. Handles drag-and-drop, view routing, and window geometry."),
        ("ui/carousel_view.py", "Presentation", "Main Thread", "Horizontal file gallery with O(1) drag-and-drop visual reordering."),
        ("ui/file_card.py", "Presentation", "Main Thread", "Card widget displaying thumbnail, filename, progress bar, and status badge."),
        ("ui/file_dialog.py", "Presentation", "Main Thread", "Dark metallic custom file browser replacing native OS dialog popups."),
        ("ui/nlp_view.py", "Presentation", "Main Thread", "Conversational RAG chat interface with detachable floating translucent mode."),
        ("ui/nerds.py", "Telemetry HUD", "Main Thread", "Real-time telemetry HUD displaying CPU, RAM, VRAM, and processing latency."),
        ("ui/merge_particles.py", "VFX Animation", "Main Thread (Timer)", "Physics-based vortex simulation rendering glowing particle animations during tasks."),
        ("ui/action_bar.py", "Presentation", "Main Thread", "Primary execution trigger buttons, mode actions, and master progress bar."),
        ("ui/tabs_bar.py", "Presentation", "Main Thread", "Navigation bar hosting mode switches, NLP master toggle, and LoRA triggers."),
        ("ui/reader_dialog.py", "Document Suite", "Main Thread", "Frameless 4.0x high-DPI document reader with smooth wheel zoom."),
        ("ui/pdf_editor.py", "Document Suite", "Main Thread", "Visual page-by-page PDF editor (crop, rotate, delete, reorder)."),
        ("training/mnime_v4 & v5*", "Model Training", "Cloud / Local NAE", "15k V4 philosophy + 20k V5 anti-bias datasets; NAE streaming fp16 fusion."),
        ("custom_installer.py", "Packaging", "Main Thread", "Custom standalone PyQt6 installer with flying-file visual progress bar."),
        ("MNIME.spec", "Build System", "PyInstaller", "Specification for single-folder standalone Windows binary distribution.")
    ]

    col_widths = [CONTENT_W * 0.28, CONTENT_W * 0.18, CONTENT_W * 0.18, CONTENT_W * 0.36]
    table_rows = []

    # Header
    hdr = modules_data[0]
    table_rows.append([
        Paragraph(f"<b>{hdr[0]}</b>", styles["table_hdr"]),
        Paragraph(f"<b>{hdr[1]}</b>", styles["table_hdr"]),
        Paragraph(f"<b>{hdr[2]}</b>", styles["table_hdr"]),
        Paragraph(f"<b>{hdr[3]}</b>", styles["table_hdr"]),
    ])

    for row in modules_data[1:]:
        # Select style by subsystem
        if "Core" in row[1] or "Neural" in row[1]:
            c_style = styles["table_cell_code"]
        elif "Presentation" in row[1]:
            c_style = styles["table_cell_green"]
        else:
            c_style = styles["table_cell"]

        table_rows.append([
            Paragraph(f"<code>{row[0]}</code>", c_style),
            Paragraph(f"<font color='{TEXT_SECONDARY.hexval()}'>{row[1]}</font>", styles["table_cell"]),
            Paragraph(f"<font color='{ACCENT_BLUE.hexval()}'>{row[2]}</font>", styles["table_cell"]),
            Paragraph(row[3], styles["table_cell"])
        ])

    t_modules = Table(table_rows, colWidths=col_widths, repeatRows=1)
    t_modules.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BG_SECTION),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BG_DARK, BG_CARD]),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 1.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    story.append(t_modules)
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    # PAGE 4: SUBSYSTEM DEEP-DIVES & EXECUTION PIPELINES
    # ═════════════════════════════════════════════════════════════════════════
    story.append(SectionTag("3. SUBSYSTEM DEEP-DIVES & EXECUTION PIPELINES"))
    story.append(Spacer(1, 3 * mm))

    # Deep Dive 1: Neural Assimilation Engine
    dive_1 = [
        [Paragraph("<b>DEEP DIVE A — THE NEURAL ASSIMILATION ENGINE (WEIGHT FUSION)</b>", styles["card_title"])],
        [Paragraph(
            "The <b>Neural Assimilation Engine</b> (<code>core/fusion_engine.py</code>) empowers MNIME to evolve dynamically beyond static model architectures. "
            "Operating on full-precision (fp16/bf16) HuggingFace safetensors directories (e.g. <code>training/v4_out/MNIME-Core-V4-merged</code>), the engine executes streaming tensor fusion:<br/><br/>"
            "1. <b>Parameter Delta Isolation:</b> The engine extracts gradient deltas relative to base matrix weights: "
            "<code>&Delta;W = W_donor - W_base</code> (optionally isolating task vectors against a common ancestor).<br/>"
            "2. <b>TIES Sparsity Pruning:</b> Insignificant delta values below a density threshold are pruned to zero, preserving base model integrity.<br/>"
            "3. <b>Sign Consensus Resolution:</b> For parameter conflicts across merged matrices, the engine computes majority sign consensus to eliminate destructive interference.<br/>"
            "4. <b>Multi-Format Export:</b> The fused weights are written as complete safetensors folders and converted via llama.cpp to high-precision GGUF (Q8_0 and Q4_K_M).",
            styles["card_desc"]
        )]
    ]
    t_dive1 = Table(dive_1, colWidths=[CONTENT_W])
    t_dive1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER_COLOR),
        ("LINELEFT", (0, 0), (0, -1), 3.5, NEON_GREEN),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(t_dive1)
    story.append(Spacer(1, 3 * mm))

    # Deep Dive 2: Dual-Tier Vector Memory
    dive_2 = [
        [Paragraph("<b>DEEP DIVE B — DUAL-TIER PERSISTENT VECTOR MEMORY & OCR</b>", styles["card_title"])],
        [Paragraph(
            "Semantic intelligence in MNIME relies on a two-tier memory hierarchy coordinated by <code>core/search_engine.py</code>:<br/><br/>"
            "• <b>Tier 1 (Ephemeral Session Index):</b> Files queued in the active carousel are converted to text chunks and embedded into an in-memory FAISS index. "
            "This provides sub-10ms similarity search across currently loaded documents.<br/>"
            "• <b>Tier 2 (Global Persistent Vector Store):</b> Every parsed document chunk is simultaneously indexed into a persistent global FAISS database located in "
            "<code>%LOCALAPPDATA%\\MNIME\\global_vector_store</code>. Chat queries synthesize knowledge across historical sessions.<br/>"
            "• <b>Native WinSDK OCR Fallback:</b> For image-only PDFs or low-DPI scans lacking text layers, the search engine activates Windows 11's native WinSDK OCR engine, "
            "extracting clean textual layers locally with zero external cloud dependencies.",
            styles["card_desc"]
        )]
    ]
    t_dive2 = Table(dive_2, colWidths=[CONTENT_W])
    t_dive2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER_COLOR),
        ("LINELEFT", (0, 0), (0, -1), 3.5, ACCENT_CYAN),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(t_dive2)
    story.append(Spacer(1, 3 * mm))

    # Deep Dive 3: Windows 11 Platform Engineering & Zero-Cloud Security
    dive_3 = [
        [Paragraph("<b>DEEP DIVE C — WINDOWS 11 INTEGRATION & ZERO-CLOUD ASSURANCE</b>", styles["card_title"])],
        [Paragraph(
            "MNIME conforms strictly to Windows 11 platform standards while maintaining absolute cryptographic data isolation:<br/><br/>"
            "• <b>Win32 Taskbar & Shell Integration:</b> Sets explicit <code>AppUserModelID</code> (<code>MNIME.DocumentSuite.2.1</code>) via Win32 ctypes, "
            "preventing grouped grouping with generic python.exe taskbar icons and embedding native multi-resolution ICO assets.<br/>"
            "• <b>Named Pipe IPC Protocol:</b> A local IPC server running on the main Qt thread intercepts subsequent launches of MNIME, forwarding CLI file paths to "
            "the running instance and bringing the window to foreground without spinning duplicate processes.<br/>"
            "• <b>Zero Cloud Egress:</b> The entire execution stack (PyMuPDF, llama.cpp, FAISS, WinSDK OCR) executes in local memory with zero socket calls, "
            "zero external telemetry, and complete resistance to network sniffing.",
            styles["card_desc"]
        )]
    ]
    t_dive3 = Table(dive_3, colWidths=[CONTENT_W])
    t_dive3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER_COLOR),
        ("LINELEFT", (0, 0), (0, -1), 3.5, GOLD),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(t_dive3)
    story.append(Spacer(1, 3 * mm))

    # Build Document
    print(f"Compiling PDF document: {output_pdf}")
    doc.build(story, canvasmaker=NumberedCanvas)
    print("ReportLab compilation completed successfully.")

    # Apply PyMuPDF bookmarks & generate cover PNG preview
    finalize_pdf_and_cover(output_pdf, cover_png)


def finalize_pdf_and_cover(pdf_path: str, cover_png: str):
    """Applies interactive table of contents outline and renders 300 DPI cover preview."""
    doc = pymupdf.open(pdf_path)

    toc = [
        [1, "MNIME Project Architecture & Schematics", 1],
        [1, "1. System Topology & Layer Schematic", 2],
        [1, "2. Component Directory & Module Index", 3],
        [1, "3. Subsystem Deep-Dives & Execution Pipelines", 4],
        [2, "Deep Dive A: Neural Assimilation Engine", 4],
        [2, "Deep Dive B: Dual-Tier Vector Memory & OCR", 4],
        [2, "Deep Dive C: Windows 11 Integration & Security", 4],
    ]
    doc.set_toc(toc)

    # Render Cover Preview (Page 1) at 300 DPI
    page = doc[0]
    zoom = 300.0 / 72.0
    mat = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    os.makedirs(os.path.dirname(os.path.abspath(cover_png)), exist_ok=True)
    pix.save(cover_png)
    print(f"Cover preview rendered: {cover_png} ({pix.width}x{pix.height}px)")

    # Save finalized PDF with bookmarks
    temp_path = pdf_path + ".tmp"
    doc.save(temp_path, incremental=False, deflate=True)
    doc.close()
    os.replace(temp_path, pdf_path)
    print(f"Architecture PDF successfully saved with bookmarks: {pdf_path}")


def main():
    root_dir = Path(__file__).resolve().parent.parent
    output_pdf = root_dir / "MNIME_Architecture.pdf"
    cover_png = root_dir / "docs" / "architecture_cover.png"

    if len(sys.argv) > 1:
        output_pdf = Path(sys.argv[1])
    if len(sys.argv) > 2:
        cover_png = Path(sys.argv[2])

    generate_pdf(str(output_pdf), str(cover_png))


if __name__ == "__main__":
    main()
