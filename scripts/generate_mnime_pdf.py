"""
MNIME — Full Specification Sheet & User Manual
PDF Generator using ReportLab
"""

import os
import html
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    Table, TableStyle, HRFlowable, KeepTogether, NextPageTemplate,
    PageBreak, ListFlowable, ListItem
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfgen import canvas as pdfgen_canvas
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Circle
from reportlab.graphics import renderPDF

# ─── Color Palette ────────────────────────────────────────────────────────────
BG_DARK        = colors.HexColor("#0b0f19")
BG_CARD        = colors.HexColor("#111827")
BG_SECTION     = colors.HexColor("#0d1526")
ACCENT_CYAN    = colors.HexColor("#00e5ff")
ACCENT_BLUE    = colors.HexColor("#00a8e8")
ACCENT_DIM     = colors.HexColor("#005f8c")
TEXT_PRIMARY   = colors.HexColor("#e8eaf6")
TEXT_SECONDARY = colors.HexColor("#90a4ae")
TEXT_MUTED     = colors.HexColor("#546e7a")
NEON_GREEN     = colors.HexColor("#39ff14")
BORDER_COLOR   = colors.HexColor("#1f2737")
GOLD           = colors.HexColor("#ffd700")
WHITE          = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

OUTPUT_PATH = r"B:\Desktop\BASSD\BELCO\AAS-T_AISD\zFAL26\MNIME\MNIME_Spec_Manual.pdf"


# ─── Custom Flowables ──────────────────────────────────────────────────────────

class DarkBackground(Flowable):
    """Full-page dark background rect."""
    def __init__(self, w, h, color=BG_DARK):
        super().__init__()
        self.w = w
        self.h = h
        self.color = color

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self.w, self.h, fill=1, stroke=0)


class GlowLine(Flowable):
    """A glowing cyan horizontal rule."""
    def __init__(self, width, thickness=0.8):
        super().__init__()
        self.width = width
        self.thickness = thickness
        self._height = thickness + 4

    def wrap(self, aW, aH):
        return self.width, self._height

    def draw(self):
        c = self.canv
        # glow layers
        for i, (alpha, expand) in enumerate([(0.08, 6), (0.15, 3), (0.4, 1.5), (1.0, 0)]):
            c.setStrokeColor(ACCENT_CYAN)
            c.setLineWidth(self.thickness + expand * 2)
            c.setStrokeAlpha(alpha)
            c.line(0, self._height / 2, self.width, self._height / 2)
        c.setStrokeAlpha(1.0)


class SectionTag(Flowable):
    """A pill-shaped label for section headers."""
    def __init__(self, text, width=CONTENT_W):
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


class FeatureBadge(Flowable):
    """A small inline badge."""
    def __init__(self, text, color=ACCENT_CYAN, bg=BG_SECTION):
        super().__init__()
        self.text = text
        self.color = color
        self.bg = bg
        self._height = 6 * mm
        self._width = len(text) * 5.5 + 10

    def wrap(self, aW, aH):
        return self._width, self._height

    def draw(self):
        c = self.canv
        h = self._height
        w = self._width
        c.setFillColor(self.bg)
        c.setStrokeColor(self.color)
        c.setLineWidth(0.5)
        c.roundRect(0, 0, w, h, 3, fill=1, stroke=1)
        c.setFillColor(self.color)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(5, h / 2 - 2.5, self.text)


class PenteractLogo(Flowable):
    """Procedurally drawn 5D Penteract projection logo."""
    def __init__(self, size=60):
        super().__init__()
        self.size = size

    def wrap(self, aW, aH):
        return self.size, self.size

    def draw(self):
        import math
        c = self.canv
        cx = self.size / 2
        cy = self.size / 2
        r = self.size * 0.38

        # Draw concentric hexagons as penteract approximation
        layers = [
            (r * 1.0, ACCENT_CYAN, 0.9, 1.0),
            (r * 0.7, ACCENT_BLUE, 0.7, 0.8),
            (r * 0.42, ACCENT_DIM, 0.5, 0.6),
        ]
        for radius, col, stroke_alpha, fill_alpha in layers:
            pts = []
            for i in range(6):
                angle = math.radians(60 * i - 30)
                pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))

            path = c.beginPath()
            path.moveTo(pts[0][0], pts[0][1])
            for px, py in pts[1:]:
                path.lineTo(px, py)
            path.close()

            c.setStrokeColor(col)
            c.setStrokeAlpha(stroke_alpha)
            c.setFillColor(BG_DARK)
            c.setLineWidth(0.8)
            c.drawPath(path, fill=1, stroke=1)

            # Connect center to vertices
            c.setStrokeColor(col)
            c.setStrokeAlpha(stroke_alpha * 0.6)
            c.setLineWidth(0.4)
            for px, py in pts:
                c.line(cx, cy, px, py)

        # Center dot
        c.setFillColor(ACCENT_CYAN)
        c.setFillAlpha(1.0)
        c.circle(cx, cy, 2.5, fill=1, stroke=0)

        # Reset alpha
        c.setStrokeAlpha(1.0)
        c.setFillAlpha(1.0)


class CoverPage(Flowable):
    """Full cover page drawn on canvas."""
    def __init__(self, w, h):
        super().__init__()
        self.w = w
        self.h = h

    def wrap(self, aW, aH):
        return self.w, self.h

    def draw(self):
        import math
        c = self.canv
        w, h = self.w, self.h

        # Dark background
        c.setFillColor(BG_DARK)
        c.rect(0, 0, w, h, fill=1, stroke=0)

        # Subtle grid lines
        c.setStrokeColor(BORDER_COLOR)
        c.setLineWidth(0.3)
        c.setStrokeAlpha(0.4)
        for x in range(0, int(w), 25):
            c.line(x, 0, x, h)
        for y in range(0, int(h), 25):
            c.line(0, y, w, y)
        c.setStrokeAlpha(1.0)

        # Top accent bar
        c.setFillColor(ACCENT_CYAN)
        c.rect(0, h - 4, w, 4, fill=1, stroke=0)

        # Large glow circle behind logo
        cx, cy_logo = w / 2, h * 0.62
        for radius, alpha in [(90, 0.04), (70, 0.07), (50, 0.12), (35, 0.18)]:
            c.setFillColor(ACCENT_CYAN)
            c.setFillAlpha(alpha)
            c.circle(cx, cy_logo, radius, fill=1, stroke=0)
        c.setFillAlpha(1.0)

        # Draw penteract manually
        logo_size = 100
        lx = cx - logo_size / 2
        ly = cy_logo - logo_size / 2
        r = logo_size * 0.38

        layers = [
            (r * 1.0, ACCENT_CYAN, 1.0, 1.0),
            (r * 0.68, ACCENT_BLUE, 0.85, 0.9),
            (r * 0.40, ACCENT_DIM, 0.65, 0.7),
        ]
        for radius, col, stroke_alpha, _ in layers:
            pts = []
            for i in range(6):
                angle = math.radians(60 * i - 30)
                pts.append((cx + radius * math.cos(angle), cy_logo + radius * math.sin(angle)))

            path = c.beginPath()
            path.moveTo(pts[0][0], pts[0][1])
            for px, py in pts[1:]:
                path.lineTo(px, py)
            path.close()

            c.setStrokeColor(col)
            c.setStrokeAlpha(stroke_alpha)
            c.setFillColor(BG_DARK)
            c.setFillAlpha(0.0)
            c.setLineWidth(1.2)
            c.drawPath(path, fill=0, stroke=1)

            c.setStrokeAlpha(stroke_alpha * 0.5)
            c.setLineWidth(0.5)
            for px, py in pts:
                c.line(cx, cy_logo, px, py)

            # cross lines
            for i in range(len(pts)):
                for j in range(i + 1, len(pts)):
                    c.line(pts[i][0], pts[i][1], pts[j][0], pts[j][1])

        c.setFillColor(ACCENT_CYAN)
        c.setFillAlpha(1.0)
        c.circle(cx, cy_logo, 4, fill=1, stroke=0)
        c.setStrokeAlpha(1.0)

        # Product name — Official Typography: Light metallic silver with touch of lavender
        c.setFillColor(colors.HexColor("#f0ecfc"))
        c.setFont("Helvetica-Bold", 38)
        c.drawCentredString(cx, h * 0.50, "M   N   I   M   E")

        # Full name
        c.setFillColor(ACCENT_CYAN)
        c.setFont("Helvetica", 8.5)
        c.drawCentredString(cx, h * 0.465, "MULTIMODAL NEURAL INTERFACE MACHINE EXTENSION")

        # Phonetic pronunciation in elegant cursive/oblique — soft lavender
        c.setFillColor(colors.HexColor("#c8b6e2"))
        c.setFont("Helvetica-Oblique", 9)
        c.drawCentredString(cx, h * 0.450, "nigh.mh")

        # Divider
        c.setStrokeColor(ACCENT_CYAN)
        c.setLineWidth(0.6)
        c.line(cx - 80, h * 0.435, cx + 80, h * 0.435)

        # Tagline
        c.setFillColor(TEXT_SECONDARY)
        c.setFont("Helvetica", 9)
        c.drawCentredString(cx, h * 0.412, "Full Specification Sheet & User Manual")

        # Version pill
        pill_w, pill_h = 80, 16
        pill_x = cx - pill_w / 2
        pill_y = h * 0.385
        c.setFillColor(ACCENT_DIM)
        c.setStrokeColor(ACCENT_CYAN)
        c.setLineWidth(0.6)
        c.roundRect(pill_x, pill_y, pill_w, pill_h, 8, fill=1, stroke=1)
        c.setFillColor(ACCENT_CYAN)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(cx, pill_y + 5, "FINAL RELEASE — v2.1")

        # Stats row
        stats = [("100%", "Offline"), ("4.0x", "Retina"), ("60 FPS", "UI"), ("1.5B", "NLP Params")]
        stat_w = w / len(stats)
        sy = h * 0.31
        for i, (val, label) in enumerate(stats):
            sx = stat_w * i + stat_w / 2
            # card bg
            c.setFillColor(BG_CARD)
            c.setStrokeColor(BORDER_COLOR)
            c.setLineWidth(0.5)
            c.roundRect(sx - 30, sy - 4, 60, 28, 4, fill=1, stroke=1)
            c.setFillColor(ACCENT_CYAN)
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(sx, sy + 12, val)
            c.setFillColor(TEXT_SECONDARY)
            c.setFont("Helvetica", 7)
            c.drawCentredString(sx, sy + 2, label)

        # Bottom bar
        c.setFillColor(BG_SECTION)
        c.rect(0, 0, w, 28, fill=1, stroke=0)
        c.setFillColor(TEXT_MUTED)
        c.setFont("Helvetica", 7)
        c.drawString(MARGIN, 10, "Private & Offline — Zero External Uploads")
        c.drawRightString(w - MARGIN, 10, "Python 3.12+ / PyQt6 / Windows 10+")

        # Bottom accent
        c.setFillColor(ACCENT_CYAN)
        c.rect(0, 0, w, 2, fill=1, stroke=0)


# ─── Page Templates ────────────────────────────────────────────────────────────

def draw_page_background(canvas, doc):
    canvas.saveState()
    w, h = canvas._pagesize
    # BG
    canvas.setFillColor(BG_DARK)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    # subtle dot grid
    canvas.setFillColor(BORDER_COLOR)
    canvas.setFillAlpha(0.35)
    for x in range(int(MARGIN), int(w - MARGIN), 18):
        for y in range(int(MARGIN * 2), int(h - MARGIN), 18):
            canvas.circle(x, y, 0.5, fill=1, stroke=0)
    canvas.setFillAlpha(1.0)
    # Top bar
    canvas.setFillColor(BG_SECTION)
    canvas.rect(0, h - 14 * mm, w, 14 * mm, fill=1, stroke=0)
    canvas.setFillColor(ACCENT_CYAN)
    canvas.rect(0, h - 1.5, w, 1.5, fill=1, stroke=0)
    # Header text
    canvas.setFillColor(TEXT_SECONDARY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(MARGIN, h - 9 * mm, "MNIME — Multimodal Neural Interface Machine Extension")
    canvas.setFillColor(ACCENT_CYAN)
    canvas.drawRightString(w - MARGIN, h - 9 * mm, f"Page {doc.page}")
    # Bottom bar
    canvas.setFillColor(BG_SECTION)
    canvas.rect(0, 0, w, 10 * mm, fill=1, stroke=0)
    canvas.setFillColor(ACCENT_CYAN)
    canvas.rect(0, 0, w, 1.5, fill=1, stroke=0)
    canvas.setFillColor(TEXT_MUTED)
    canvas.setFont("Helvetica", 6.5)
    canvas.drawCentredString(w / 2, 4 * mm, "Confidential — For Internal Use — kyledeanml/MNIME")
    canvas.restoreState()


def draw_cover_background(canvas, doc):
    canvas.saveState()
    canvas.restoreState()


# ─── Styles ────────────────────────────────────────────────────────────────────

def build_styles():
    s = {}

    s["h1"] = ParagraphStyle(
        "h1", fontName="Helvetica-Bold", fontSize=20, textColor=WHITE,
        spaceAfter=4, spaceBefore=14, leading=24
    )
    s["h2"] = ParagraphStyle(
        "h2", fontName="Helvetica-Bold", fontSize=13, textColor=ACCENT_CYAN,
        spaceAfter=3, spaceBefore=10, leading=16
    )
    s["h3"] = ParagraphStyle(
        "h3", fontName="Helvetica-Bold", fontSize=10, textColor=TEXT_PRIMARY,
        spaceAfter=2, spaceBefore=6, leading=13
    )
    s["body"] = ParagraphStyle(
        "body", fontName="Helvetica", fontSize=8.5, textColor=TEXT_PRIMARY,
        spaceAfter=4, leading=13, alignment=TA_JUSTIFY
    )
    s["body_small"] = ParagraphStyle(
        "body_small", fontName="Helvetica", fontSize=7.5, textColor=TEXT_SECONDARY,
        spaceAfter=3, leading=11, alignment=TA_JUSTIFY
    )
    s["mono"] = ParagraphStyle(
        "mono", fontName="Courier", fontSize=8, textColor=NEON_GREEN,
        backColor=BG_SECTION, spaceAfter=3, leading=12,
        leftIndent=6, rightIndent=6, borderPad=4
    )
    s["caption"] = ParagraphStyle(
        "caption", fontName="Helvetica-Oblique", fontSize=7, textColor=TEXT_MUTED,
        spaceAfter=6, leading=10, alignment=TA_CENTER
    )
    s["label"] = ParagraphStyle(
        "label", fontName="Helvetica-Bold", fontSize=7.5, textColor=ACCENT_CYAN,
        spaceAfter=1, leading=10
    )
    s["toc_title"] = ParagraphStyle(
        "toc_title", fontName="Helvetica-Bold", fontSize=16, textColor=WHITE,
        spaceAfter=8, spaceBefore=0, alignment=TA_CENTER
    )
    s["toc_entry"] = ParagraphStyle(
        "toc_entry", fontName="Helvetica", fontSize=9, textColor=TEXT_PRIMARY,
        spaceAfter=5, leading=13, leftIndent=0
    )
    s["toc_entry_sub"] = ParagraphStyle(
        "toc_entry_sub", fontName="Helvetica", fontSize=8, textColor=TEXT_SECONDARY,
        spaceAfter=3, leading=11, leftIndent=12
    )
    s["note"] = ParagraphStyle(
        "note", fontName="Helvetica-Oblique", fontSize=7.5, textColor=ACCENT_BLUE,
        spaceAfter=4, leading=11, leftIndent=8,
        borderColor=ACCENT_DIM, borderWidth=0.5, borderPad=4,
        backColor=BG_SECTION
    )
    s["warning"] = ParagraphStyle(
        "warning", fontName="Helvetica-Bold", fontSize=7.5, textColor=GOLD,
        spaceAfter=4, leading=11, leftIndent=8,
        borderColor=GOLD, borderWidth=0.5, borderPad=4,
        backColor=BG_SECTION
    )
    s["table_hdr"] = ParagraphStyle(
        "table_hdr", fontName="Helvetica-Bold", fontSize=7.5, textColor=ACCENT_CYAN,
        leading=10, spaceAfter=0, spaceBefore=0
    )
    s["table_cell_key"] = ParagraphStyle(
        "table_cell_key", fontName="Helvetica-Bold", fontSize=7, textColor=TEXT_SECONDARY,
        leading=9.5, spaceAfter=0, spaceBefore=0
    )
    s["table_cell_val"] = ParagraphStyle(
        "table_cell_val", fontName="Helvetica", fontSize=7, textColor=TEXT_PRIMARY,
        leading=9.5, spaceAfter=0, spaceBefore=0
    )
    s["table_cell_code"] = ParagraphStyle(
        "table_cell_code", fontName="Courier-Bold", fontSize=6.5, textColor=NEON_GREEN,
        leading=8.5, spaceAfter=0, spaceBefore=0
    )
    s["table_cell_muted"] = ParagraphStyle(
        "table_cell_muted", fontName="Helvetica", fontSize=6.5, textColor=TEXT_MUTED,
        leading=8.5, spaceAfter=0, spaceBefore=0
    )
    s["table_cell_arch_role"] = ParagraphStyle(
        "table_cell_arch_role", fontName="Helvetica", fontSize=6.5, textColor=TEXT_PRIMARY,
        leading=8.5, spaceAfter=0, spaceBefore=0
    )
    s["table_cell_arch_deps"] = ParagraphStyle(
        "table_cell_arch_deps", fontName="Helvetica", fontSize=6.5, textColor=TEXT_MUTED,
        leading=8.5, spaceAfter=0, spaceBefore=0
    )
    return s


# ─── Helper builders ──────────────────────────────────────────────────────────

def section_header(title, styles):
    return [
        Spacer(1, 4 * mm),
        SectionTag(title),
        Spacer(1, 2 * mm),
    ]


def spec_table(rows, col_widths=None):
    if col_widths is None:
        col_widths = [CONTENT_W * 0.33, CONTENT_W * 0.67]
    th_st = ParagraphStyle("th_st", fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=ACCENT_CYAN)
    key_st = ParagraphStyle("key_st", fontName="Helvetica-Bold", fontSize=7, leading=9.5, textColor=TEXT_SECONDARY)
    val_st = ParagraphStyle("val_st", fontName="Helvetica", fontSize=7, leading=9.5, textColor=TEXT_PRIMARY)

    formatted_rows = []
    for r_idx, row in enumerate(rows):
        formatted_row = []
        for c_idx, cell in enumerate(row):
            if isinstance(cell, Flowable):
                formatted_row.append(cell)
            else:
                esc = html.escape(str(cell))
                if r_idx == 0:
                    formatted_row.append(Paragraph(f"<b>{esc}</b>", th_st))
                else:
                    if c_idx == 0:
                        formatted_row.append(Paragraph(f"<b>{esc}</b>", key_st))
                    else:
                        formatted_row.append(Paragraph(esc, val_st))
        formatted_rows.append(formatted_row)

    t = Table(formatted_rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), BG_SECTION),
        ("GRID",           (0, 0), (-1, -1), 0.35, BORDER_COLOR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BG_DARK, BG_CARD]),
        ("TOPPADDING",     (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 3),
        ("LEFTPADDING",    (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 5),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def build_body(styles):
    S = styles
    story = []

    # ── COVER ─────────────────────────────────────────────────────────────────
    story.append(CoverPage(PAGE_W, PAGE_H))
    story.append(NextPageTemplate("content"))
    story.append(PageBreak())

    # ── TABLE OF CONTENTS ─────────────────────────────────────────────────────
    story.append(Paragraph("TABLE OF CONTENTS", S["toc_title"]))
    story.append(GlowLine(CONTENT_W))
    story.append(Spacer(1, 5 * mm))

    toc_entries = [
        ("1", "Product Overview", None),
        ("2", "Technical Specifications", None),
        ("3", "Architecture & Module Reference", None),
        ("4", "Feature Reference", [
            "4.1  Combine PDF",
            "4.2  JPG to PDF",
            "4.3  TXT to PDF",
            "4.4  PDF to JPG",
            "4.5  Split PDF",
            "4.6  Compress PDF",
            "4.7  PDF to DOCX",
            "4.8  Bookmark",
            "4.9  Edit Suite",
            "4.10 NLP Chat & RAG Engine",
            "4.11 Reference Engine",
        ]),
        ("5", "NLP Engine — MNIME-Core", None),
        ("6", "Semantic Search Engine", None),
        ("7", "User Interface Guide", [
            "7.1  Tabs Bar",
            "7.2  Drop Zone",
            "7.3  Gallery Carousel",
            "7.4  Action Bar",
            "7.5  Document Reader",
            "7.6  Edit UI",
            "7.7  NLP Floating Chat",
        ]),
        ("8", "Installation & Setup", [
            "8.1  Standalone Installer",
            "8.2  Run from Source",
            "8.3  Build Pipeline",
        ]),
        ("9", "Keyboard Shortcuts & Tips", None),
        ("10", "Performance Notes", None),
        ("11", "Dependency Stack", None),
        ("12", "Error Handling & Validation", None),
        ("13", "Changelog", None),
        ("14", "License & Attribution", None),
    ]

    for num, title, subs in toc_entries:
        row_data = [[
            Paragraph(f'<font color="#00e5ff"><b>{num}</b></font>', S["body"]),
            Paragraph(title, S["toc_entry"]),
        ]]
        t = Table(row_data, colWidths=[10 * mm, CONTENT_W - 10 * mm])
        t.setStyle(TableStyle([
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(t)
        if subs:
            for sub in subs:
                story.append(Paragraph(sub, S["toc_entry_sub"]))
        story.append(HRFlowable(width=CONTENT_W, thickness=0.3, color=BORDER_COLOR, spaceAfter=2))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 1 — PRODUCT OVERVIEW
    # ─────────────────────────────────────────────────────────────────────────
    story += section_header("1  Product Overview", S)
    story.append(Paragraph(
        "MNIME — <b>Multimodal Neural Interface Machine Extension</b> — is a modern, private, "
        "and ultra-fast desktop document-processing application engineered with Python and PyQt6. "
        "It runs <b>100% locally and offline</b> on the host machine with zero external network "
        "uploads, giving users full conversational interaction over their documents via a "
        "bundled, fine-tuned local NLP model.",
        S["body"]
    ))
    story.append(Spacer(1, 3 * mm))

    ov_data = [
        ["Attribute", "Value"],
        ["Full Name", "Multimodal Neural Interface Machine Extension"],
        ["Version",   "Final Release (v2.1)"],
        ["Platform",  "Windows 10 / 11 (64-bit)"],
        ["Language",  "Python 3.12+"],
        ["UI Framework", "PyQt6 6.11"],
        ["License",   "Open Source (see Section 14)"],
        ["Author",    "kyledeanml / KyleDeanAI"],
        ["Repository", "https://github.com/kyledeanml/MNIME"],
        ["NLP Model",  "KyleDeanAI/MNIME-Core-1.5B-Q4_K_M (HuggingFace)"],
        ["Network",   "Fully Offline — Zero external API calls"],
    ]
    story.append(spec_table(ov_data))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Design Philosophy", S["h2"]))
    story.append(Paragraph(
        "MNIME is purpose-built around three pillars: <b>privacy</b> (nothing ever leaves the machine), "
        "<b>performance</b> (C-accelerated document engines, background workers, O(1) UI operations), "
        "and <b>aesthetics</b> (a free-floating dark metallic interface with physics-based animations and "
        "a mathematically precise 5D Penteract projection logo). The application avoids all web service "
        "dependencies, making it suitable for air-gapped, regulated, or sensitive document environments.",
        S["body"]
    ))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 2 — TECHNICAL SPECIFICATIONS
    # ─────────────────────────────────────────────────────────────────────────
    story += section_header("2  Technical Specifications", S)

    spec_data = [
        ["Specification", "Detail"],
        ["Minimum OS",          "Windows 10 64-bit (Build 1903+)"],
        ["Recommended OS",      "Windows 11 64-bit"],
        ["Python Version",      "3.12 or higher"],
        ["CPU",                 "Any modern x86-64 processor (multi-core recommended)"],
        ["RAM — Lightweight Mode", "~1.0 GB (NLP disabled, base runtime)"],
        ["RAM — NLP Active",    "~1.8–1.9 GB (model weights loaded in VRAM/RAM)"],
        ["GPU (Optional)",      "NVIDIA CUDA-capable GPU for NLP layer offloading"],
        ["GPU VRAM (Optional)", "4 GB+ recommended for full GGUF layer offload"],
        ["Validation / Dev Bench", "AMD Ryzen 9 7950X, 64 GB DDR5 6000 MHz, RTX 3060 Ventus 12 GB"],
        ["Disk Space",          "~2 GB (application + bundled model)"],
        ["Display",             "1280×720 minimum; 1920×1080+ recommended"],
        ["File Queue Limit",    "Up to 5,000 files per session"],
        ["PDF Rendering DPI",   "4.0x Retina (288 DPI equivalent)"],
        ["NLP Context Window",  "4,096 tokens"],
        ["NLP Threads",         "8 CPU threads (llama.cpp)"],
        ["NLP GPU Layers",      "Auto-detect (n_gpu_layers = -1)"],
        ["Embedding Model",     "BAAI/bge-small-en-v1.5 (FAISS-backed)"],
        ["Vector Index",        "FAISS (CPU), chunk size 1,500 / overlap 200"],
        ["Image Conversion DPI", "200 DPI default (PDF → JPG)"],
        ["UI Framerate Target", "60 FPS (QThread non-blocking)"],
        ["Installer Format",    "Custom PyQt6 animated installer"],
        ["Install Location",    r"%LOCALAPPDATA%\Programs\MNIME"],
    ]
    story.append(spec_table(spec_data))
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 3 — ARCHITECTURE & MODULE REFERENCE
    # ─────────────────────────────────────────────────────────────────────────
    story += section_header("3  Architecture & Module Reference", S)

    story.append(Paragraph(
        "MNIME is structured into two top-level packages — <b>core/</b> (backend processing engine) "
        "and <b>ui/</b> (PyQt6 frontend) — plus a root-level entry point. All heavy operations "
        "run in <b>QThread</b> workers to keep the UI at 60 FPS.",
        S["body"]
    ))
    story.append(Spacer(1, 3 * mm))

    arch_data = [
        ["Module", "Role", "Key Dependencies"],
        ["MNIME.py",               "Entry point. Initializes Qt app, sets AppUserModelID, applies global stylesheet, instantiates MainWindow.", "PyQt6, core.app_icon"],
        ["core/pdf_engine.py",     "All document transformations: merge, split, JPG↔PDF, TXT→PDF, compress, DOCX export, bookmark.", "pymupdf, pypdf, pdf2docx, Pillow, concurrent.futures"],
        ["core/nlp_engine.py",     "Singleton NLP engine. Loads/unloads GGUF model, generates chat responses, smart bookmarks, smart filenames.", "llama-cpp-python"],
        ["core/search_engine.py",  "FAISS-backed semantic search. Indexes PDFs/text files, performs similarity search, runs Windows OCR on image-only pages.", "langchain, faiss-cpu, sentence-transformers, winsdk"],
        ["core/file_item.py",      "Data model for a queued file. Stores path, extension, metadata, thumbnail pixmap.", "pymupdf, Pillow"],
        ["core/fusion_engine.py",  "Neural Assimilation Engine. Background weight-fusion system for dynamic model merging & parameter absorption.", "numpy, torch, llama-cpp-python"],
        ["core/worker.py",         "Generic QThread worker with progress_callback signal. Wraps all engine calls.", "PyQt6.QtCore"],
        ["core/app_icon.py",       "Windows AppUserModelID registration, ICO generation, taskbar/desktop shortcut creation.", "winreg, ctypes"],
        ["ui/main_window.py",      "Central coordinator. Frameless dark metallic window, mode routing, drag-and-drop handler, VFX trigger.", "PyQt6, all ui/ modules"],
        ["ui/tabs_bar.py",         "Icon-only mode switcher. Hosts NLP checkbox master toggle and Reload NLP button.", "PyQt6"],
        ["ui/carousel_view.py",    "Horizontal reorderable file card carousel with drop zone. O(1) index-based drag reorder.", "PyQt6"],
        ["ui/file_card.py",        "Individual card widget: thumbnail, filename, status badge, progress bar, remove (X) button.", "PyQt6"],
        ["ui/file_dialog.py",      "Custom dark-mode file explorer dialog replacing OS popup. Directory tree + file list.", "PyQt6"],
        ["ui/action_bar.py",       "Primary action button + animated progress bar.", "PyQt6"],
        ["ui/nlp_view.py",         "Conversational NLP chat interface. Sends queries to NLPEngine, displays streamed responses.", "PyQt6"],
        ["ui/output_view.py",      "Processing log / status view with timestamped entries.", "PyQt6"],
        ["ui/reader_dialog.py",    "Frameless independent document reader at 4.0x DPI. Ctrl+Scroll zoom, auto-fit.", "PyQt6, pymupdf"],
        ["ui/pdf_editor.py",       "PDF crop/rotate editor UI.", "PyQt6, pymupdf"],
        ["ui/image_editor.py",     "Image crop/rotate editor UI.", "PyQt6, Pillow"],
        ["ui/document_viewer.py",  "Embedded document viewer used in Reference mode.", "PyQt6, pymupdf"],
        ["ui/merge_particles.py",  "Physics-based particle simulation (file vortex) displayed during processing.", "PyQt6"],
        ["ui/minimize_animation.py","Custom minimize animation for frameless window.", "PyQt6"],
        ["ui/cursor_fx.py",        "Custom cursor effect applied globally.", "PyQt6"],
        ["ui/icons.py",            "Resolution-independent SVG icon registry. Returns QIcon at any DPI.", "PyQt6"],
        ["custom_installer.py",    "Standalone animated PyQt6 installer with flying-file progress bar.", "PyQt6, PyInstaller"],
        ["MNIME.spec",             "PyInstaller spec for main application bundle.", "PyInstaller"],
    ]

    arch_col_w = [CONTENT_W * 0.25, CONTENT_W * 0.48, CONTENT_W * 0.27]
    arch_flowables = [
        [
            Paragraph(f"<b>{html.escape(arch_data[0][0])}</b>", S["table_hdr"]),
            Paragraph(f"<b>{html.escape(arch_data[0][1])}</b>", S["table_hdr"]),
            Paragraph(f"<b>{html.escape(arch_data[0][2])}</b>", S["table_hdr"]),
        ]
    ]
    for row in arch_data[1:]:
        arch_flowables.append([
            Paragraph(html.escape(row[0]), S["table_cell_code"]),
            Paragraph(html.escape(row[1]), S["table_cell_arch_role"]),
            Paragraph(html.escape(row[2]), S["table_cell_arch_deps"]),
        ])
    t = Table(arch_flowables, colWidths=arch_col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), BG_SECTION),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BG_DARK, BG_CARD]),
        ("GRID",           (0, 0), (-1, -1), 0.3, BORDER_COLOR),
        ("TOPPADDING",     (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 2),
        ("LEFTPADDING",    (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 4),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 4 — FEATURE REFERENCE
    # ─────────────────────────────────────────────────────────────────────────
    story += section_header("4  Feature Reference", S)

    features = [
        ("4.1", "Combine PDF", "MERGE", [
            ("Inputs", "PDF files, JPG/PNG/BMP/WEBP images, TXT files (mixed)"),
            ("Output", "Single merged PDF document"),
            ("Max Files", "5,000 files per session"),
            ("Engine", "PyMuPDF (primary) → pypdf + Pillow (fallback)"),
            ("Algorithm", "Sequential insert_pdf() with garbage=3, deflate=True compaction"),
            ("Performance", "C-level PyMuPDF routines, up to 50x faster than pure-Python"),
        ]),
        ("4.2", "JPG to PDF", "JPG → PDF", [
            ("Inputs", "JPG, JPEG, PNG, WEBP, BMP image files"),
            ("Output", "Single unified PDF document"),
            ("Engine", "PyMuPDF sequential convert_to_pdf() → Pillow fallback"),
            ("Parallelism", "Sequential (MuPDF is not thread-safe); runs off the UI thread"),
            ("Save", "garbage=3, deflate=True optimization"),
        ]),
        ("4.3", "TXT to PDF", "TXT → PDF", [
            ("Inputs", ".txt plain text files"),
            ("Output", "Searchable native vector PDF"),
            ("Engine", "PyMuPDF insert_textbox() (Helvetica, 12pt, 50pt margins)"),
            ("Notes", "Can be combined with PDFs and images in Combine mode"),
        ]),
        ("4.4", "PDF to JPG", "PDF → JPG", [
            ("Inputs", "Single PDF document"),
            ("Output", "One JPG image per page"),
            ("DPI", "200 DPI default (zoom = DPI / 72)"),
            ("Engine", "PyMuPDF get_pixmap() sequential rendering"),
            ("Parallelism", "Sequential (MuPDF is not thread-safe); runs off the UI thread"),
            ("Naming", "<basename>_page_<NNN>.jpg"),
        ]),
        ("4.5", "Split PDF", "SPLIT", [
            ("Inputs", "Single PDF document"),
            ("Output", "One PDF file per page, saved to output directory"),
            ("NLP Smart Naming", "If NLP is loaded, each page's text is sent to MNIME-Core to generate a concise, context-aware filename (under 40 chars, underscored). Page number appended for uniqueness."),
            ("Fallback Naming", "<basename>_page_<NNN>.pdf"),
            ("Parallelism", "Sequential page loop (MuPDF is not thread-safe); NLP lock retained"),
        ]),
        ("4.6", "Compress PDF", "COMPRESS", [
            ("Inputs", "Single PDF document"),
            ("Output", "Compressed PDF (overwrite-safe output path)"),
            ("Engine", "PyMuPDF save(garbage=4, deflate=True, clean=True) → pypdf fallback"),
            ("Method", "Stream deflation, xref compaction, duplicate object elimination"),
        ]),
        ("4.7", "PDF to DOCX", "PDF → DOCX", [
            ("Inputs", "Single PDF document"),
            ("Output", ".docx Microsoft Word document"),
            ("Engine", "pdf2docx (full layout fidelity) → pypdf + python-docx (text fallback)"),
            ("Fidelity", "Preserves text layout, columns, and formatting via pdf2docx"),
        ]),
        ("4.8", "Bookmark", "BOOKMARK", [
            ("Inputs", "Single PDF document"),
            ("Output", "Bookmarked PDF with structured table of contents"),
            ("Heuristics", "Font-size analysis across sampled pages to detect body text baseline; headings identified by size ≥ 1.15x baseline OR bold ≥ 1.05x. Explicit chapter/section regex matched first."),
            ("NLP Mode", "If NLP is loaded, each detected heading is enriched via MNIME-Core into a verbose, context-aware bookmark title (≤60 chars)"),
            ("Fallback", "If no headings detected, all pages bookmarked using largest text found"),
        ]),
        ("4.9", "Edit Suite", "EDIT", [
            ("Scope", "Images and PDF documents"),
            ("Operations", "Crop (drag selection), rotate (90° CW/CCW), apply to all pages or single page"),
            ("Rendering", "4.0x Retina pixmap rendering for razor-sharp editing canvas"),
            ("Windows", "Independent frameless dark metallic editor windows"),
        ]),
        ("4.10", "NLP Chat & RAG", "NLP", [
            ("Interface", "Conversational chat panel with message history"),
            ("Model", "MNIME-Core-1.5B-Q4_K_M.gguf (Qwen2.5 1.5B fine-tuned)"),
            ("RAG", "Queries first run through FAISS semantic search; top-5 chunks fed as context to the model"),
            ("Context Window", "4,096 tokens"),
            ("Max Response", "1,024 tokens"),
            ("Prompt Format", "ChatML (<|im_start|> / <|im_end|>)"),
            ("Pop-out", "Double-click to spawn magnetic translucent floating chat window"),
        ]),
        ("4.11", "Reference Engine", "REFERENCE", [
            ("Purpose", "Highlight a section in one open document to auto-synthesize a comparative brief against all other open documents"),
            ("Method", "Selected text sent to NLPEngine.synthesize_reference() with semantic search results as context"),
            ("Output", "Comparative analysis: alignment, conflicts, and relationships across documents"),
            ("System Role", "Advanced legal and document analysis NLP persona"),
        ]),
    ]

    for num, title, mode_label, attrs in features:
        story.append(KeepTogether([
            Paragraph(f"{num}  {title}", S["h2"]),
            spec_table([["Property", "Value"]] + attrs),
            Spacer(1, 3 * mm),
        ]))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 5 — NLP ENGINE
    # ─────────────────────────────────────────────────────────────────────────
    story += section_header("5  NLP Engine — MNIME-Core", S)

    story.append(Paragraph(
        "The MNIME NLP engine is a singleton (<b>NLPEngine</b>) that wraps <b>llama-cpp-python</b> "
        "to load and run the bundled GGUF model. It is designed for zero-configuration operation: "
        "the bundled model is auto-detected, GPU layers are fully auto-offloaded, and all memory "
        "is aggressively cleaned on toggle-off or application close.",
        S["body"]
    ))
    story.append(Spacer(1, 3 * mm))

    nlp_data = [
        ["Property", "Detail"],
        ["Base Model",       "Qwen2.5-1.5B-Instruct"],
        ["Fine-tuning",      "Progressive multi-stage alignment: V3 doc synthesis + V4 philosophy + V5 anti-bias"],
        ["Neural Engine",    "Neural Assimilation Engine (NAE): streaming fp16 TIES weight fusion"],
        ["Quantization",     "Q4_K_M (4-bit, K-Quant Mixed) with high-fidelity Q8_0 and fp16 archives"],
        ["Format",           "GGUF (llama.cpp compatible)"],
        ["Parameters",       "~1.5 Billion"],
        ["Context Length",   "4,096 tokens (n_ctx)"],
        ["CPU Threads",      "8 (n_threads)"],
        ["GPU Layers",       "-1 (auto-offload all layers that fit in VRAM)"],
        ["Flash Attention",  "Enabled if supported by build; falls back gracefully"],
        ["Memory Locking",   "Disabled (use_mlock=False) for broad compatibility"],
        ["Singleton Pattern","One global instance (NLPEngine.get_instance()), thread-locked"],
        ["Cleanup",          "atexit, SIGINT, SIGTERM, and crash handler all call unload_model()"],
        ["Smart Bookmark",   "max_tokens=25, stop on newline — fast constrained title generation"],
        ["Smart Filename",   "max_tokens=20, thread-locked for safety"],
        ["Chat Response",    "max_tokens=1,024, stop on <|im_end|>"],
        ["Reference Brief",  "max_tokens=1,024, structured comparative analysis prompt"],
        ["HuggingFace",      "KyleDeanAI/MNIME-Core-1.5B-Q4_K_M"],
    ]
    story.append(spec_table(nlp_data))

    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("Loading & Lifecycle", S["h3"]))
    story.append(Paragraph(
        "The model is <b>not loaded at startup</b>. Click the <b>Reload NLP</b> button (refresh icon "
        "in the Tabs Bar) to load it into memory. This keeps startup instant. Uncheck the "
        "<b>NLP checkbox</b> to immediately unload the model and free all VRAM/RAM. The Reload NLP "
        "button glows cyan while the model is unloaded as a visual reminder.",
        S["body"]
    ))
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 6 — SEMANTIC SEARCH ENGINE
    # ─────────────────────────────────────────────────────────────────────────
    story += section_header("6  Semantic Search Engine", S)

    story.append(Paragraph(
        "The <b>SearchEngine</b> class provides FAISS-backed vector search over all queued documents. "
        "It supports PDFs (with Windows OCR fallback for image-only pages), plain text, Markdown, "
        "JSON, CSV, and common source code formats.",
        S["body"]
    ))
    story.append(Spacer(1, 3 * mm))

    se_data = [
        ["Property", "Detail"],
        ["Vector Index",     "FAISS (CPU)"],
        ["Embedding Model",  "BAAI/bge-small-en-v1.5 (via langchain-huggingface)"],
        ["Chunking",         "RecursiveCharacterTextSplitter — chunk_size=1500, overlap=200"],
        ["Smart Sampling",   "Extracts top-20 probe terms from a 10% content sample; indexes only chunks containing those terms"],
        ["Fallback",         "If smart sampling yields no chunks, falls back to full indexing"],
        ["PDF Text",         "PyMuPDF page.get_text() per page"],
        ["OCR",              "Windows OCR API (winsdk) on image-only PDF pages (2x pixmap)"],
        ["Search",           "vectorstore.similarity_search(query, k=5) — returns top-5 chunks with source"],
        ["Supported Formats","PDF, TXT, MD, JSON, CSV, PY, JS, TS, HTML, CSS, CPP, C, H, Java"],
        ["Index Lifetime",   "Built on demand for NLP mode; cleared from memory with model unload"],
    ]
    story.append(spec_table(se_data))
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 7 — USER INTERFACE GUIDE
    # ─────────────────────────────────────────────────────────────────────────
    story += section_header("7  User Interface Guide", S)

    story.append(Paragraph("7.1  Tabs Bar", S["h2"]))
    story.append(Paragraph(
        "The Tabs Bar runs horizontally across the top of the main window. It is divided into three "
        "groups: <b>Left</b> (Edit, Bookmark, Reference), <b>Center</b> (JPG→PDF, TXT→PDF, Combine, "
        "Split, Compress, PDF→JPG, PDF→DOCX), and <b>Right</b> (NLP checkbox, NLP chat, Reload NLP).",
        S["body"]
    ))

    tabs_data = [
        ["Icon Mode", "Tab Label", "Description"],
        ["EDIT",        "Edit",        "Open image or PDF in the Edit Suite (crop/rotate)"],
        ["BOOKMARK",    "Bookmark",    "Add smart or heuristic bookmarks to a PDF"],
        ["REFERENCE",   "Reference",   "Cross-reference documents with NLP synthesis"],
        ["JPG → PDF",   "JPG → PDF",   "Convert image files to a unified PDF"],
        ["TXT → PDF",   "TXT → PDF",   "Convert plain text files to native vector PDF"],
        ["MERGE",       "Combine PDF", "Merge multiple PDFs and images into one document"],
        ["SPLIT",       "Split PDF",   "Split a PDF into individual page files"],
        ["COMPRESS",    "Compress",    "Reduce PDF file size"],
        ["PDF → JPG",   "PDF → JPG",   "Export PDF pages as high-res JPG images"],
        ["PDF → DOCX",  "PDF → DOCX",  "Convert PDF to editable Word document"],
        ["NLP (checkbox)", "NLP",      "Master toggle — uncheck to unload model instantly"],
        ["NLP (button)", "NLP Chat",  "Open the conversational NLP interface"],
        ["RELOAD NLP",  "Reload NLP",  "Load / reload the GGUF model into memory. Glows cyan when model is unloaded."],
        ["STATS",       "Stats",       "Open Stats telemetry dashboard with live dynamic line charts."],
    ]
    tabs_col_w = [CONTENT_W * 0.22, CONTENT_W * 0.20, CONTENT_W * 0.58]
    tabs_flowables = [
        [
            Paragraph(f"<b>{html.escape(tabs_data[0][0])}</b>", S["table_hdr"]),
            Paragraph(f"<b>{html.escape(tabs_data[0][1])}</b>", S["table_hdr"]),
            Paragraph(f"<b>{html.escape(tabs_data[0][2])}</b>", S["table_hdr"]),
        ]
    ]
    for row in tabs_data[1:]:
        tabs_flowables.append([
            Paragraph(html.escape(row[0]), S["table_cell_code"]),
            Paragraph(f"<b>{html.escape(row[1])}</b>", S["table_cell_key"]),
            Paragraph(html.escape(row[2]), S["table_cell_val"]),
        ])
    t = Table(tabs_flowables, colWidths=tabs_col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), BG_SECTION),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BG_DARK, BG_CARD]),
        ("GRID",           (0, 0), (-1, -1), 0.3, BORDER_COLOR),
        ("TOPPADDING",     (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 4),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("7.2  Drop Zone", S["h2"]))
    story.append(Paragraph(
        "The right side of the main window features a <b>Drop Zone</b> centered on the MNIME Penteract "
        "logo. Drag any supported file type directly onto the logo to queue it. A subtle drag-over "
        "highlight provides real-time feedback. Alternatively, click the neon-outlined <b>ADD FILES</b> "
        "button to open the custom file browser dialog.",
        S["body"]
    ))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("7.3  Gallery Carousel", S["h2"]))
    story.append(Paragraph(
        "Once files are queued, they populate the <b>Gallery Carousel</b> on the left side as "
        "interactive file cards. Each card displays a thumbnail (rendered by PyMuPDF for PDFs, "
        "Pillow for images), filename, and status badge. Cards can be scrolled horizontally and "
        "dragged left/right to reorder — implemented via O(1) index-based layout shifts rather "
        "than full widget rebuilds. A neon-red <b>X</b> button in the top bar clears the entire queue.",
        S["body"]
    ))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("7.4  Action Bar", S["h2"]))
    story.append(Paragraph(
        "The <b>Action Bar</b> at the bottom of the window contains the primary action button "
        "(label changes with mode, e.g. <i>MERGE FILES</i>, <i>COMPRESS PDF</i>) and a progress "
        "bar that appears during processing. All operations run in a <b>QThread</b> worker, so the "
        "UI remains fully interactive and animated at 60 FPS throughout.",
        S["body"]
    ))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("7.5  Document Reader", S["h2"]))
    story.append(Paragraph(
        "MNIME includes a built-in frameless <b>Document Reader</b> that opens as an independent, "
        "resizable dark metallic window. Documents are rendered at <b>4.0x Retina pixel density</b> "
        "(288 DPI equivalent) for ultra-sharp, anti-aliased vector text. Use <b>Ctrl + Mouse Scroll</b> "
        "to zoom smoothly. The reader auto-fits the document to the window width with margin padding "
        "on open, and supports native smooth diagonal resizing.",
        S["body"]
    ))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("7.6  Edit UI", S["h2"]))
    story.append(Paragraph(
        "The Edit UI (accessible via the <b>EDIT</b> tab) opens a dedicated editor window. For images, "
        "it provides crop and rotation controls. For PDFs, it allows cropping and rotating individual "
        "pages or all pages simultaneously. The editor renders at 4.0x Retina density for precision "
        "alignment. Changes are saved back to the source file or a new output path.",
        S["body"]
    ))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("7.7  NLP Floating Chat", S["h2"]))
    story.append(Paragraph(
        "Double-clicking the NLP console panel spawns a <b>magnetic, translucent floating chat window</b> "
        "that mirrors the main window's dark metallic aesthetic. The window is perfectly synced with "
        "the main application state and stays on top for convenient side-by-side document interaction. "
        "It can be repositioned freely and snaps back into the main window on double-click.",
        S["body"]
    ))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 8 — INSTALLATION & SETUP
    # ─────────────────────────────────────────────────────────────────────────
    story += section_header("8  Installation & Setup", S)

    story.append(Paragraph("8.1  Standalone Installer (Recommended)", S["h2"]))
    story.append(Paragraph(
        "Two pre-built installers are provided in the <b>installer/</b> folder:",
        S["body"]
    ))

    inst_data = [
        ["Installer", "Description", "Install Location"],
        ["MNIME_installer.exe",    "Premium animated installer with custom PyQt6 UI — branded dark window, animated flying-file progress bar, and automatic shortcut creation.", r"%LOCALAPPDATA%\Programs\MNIME"],
    ]
    inst_col_w = [CONTENT_W * 0.25, CONTENT_W * 0.48, CONTENT_W * 0.27]
    inst_flowables = [
        [
            Paragraph(f"<b>{html.escape(inst_data[0][0])}</b>", S["table_hdr"]),
            Paragraph(f"<b>{html.escape(inst_data[0][1])}</b>", S["table_hdr"]),
            Paragraph(f"<b>{html.escape(inst_data[0][2])}</b>", S["table_hdr"]),
        ]
    ]
    for row in inst_data[1:]:
        inst_flowables.append([
            Paragraph(html.escape(row[0]), S["table_cell_code"]),
            Paragraph(html.escape(row[1]), S["table_cell_val"]),
            Paragraph(html.escape(row[2]), S["table_cell_muted"]),
        ])
    t = Table(inst_flowables, colWidths=inst_col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), BG_SECTION),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BG_DARK, BG_CARD]),
        ("GRID",           (0, 0), (-1, -1), 0.3, BORDER_COLOR),
        ("TOPPADDING",     (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 3),
        ("LEFTPADDING",    (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 4),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("8.2  Run from Source", S["h2"]))

    steps = [
        ("<b>Download the NLP Model</b>: Go to <font color='#00e5ff'>huggingface.co/KyleDeanAI/MNIME-Core-1.5B-Q4_K_M</font>, download the .gguf file, and place it in the <font color='#39ff14'>models/</font> directory.", None),
        ("<b>Run setup.bat</b>: Creates a Python 3.12+ virtual environment and installs all dependencies from requirements.txt.", "setup.bat"),
        ("<b>Launch</b>: Double-click <font color='#39ff14'>run.bat</font>, or from terminal:", ".venv\\Scripts\\python.exe MNIME.py"),
        ("<b>Pin to Taskbar</b>: Run <font color='#39ff14'>create_shortcut.bat</font> to generate a Desktop shortcut, then right-click → Pin to taskbar.", None),
    ]
    for i, (desc, cmd) in enumerate(steps, 1):
        story.append(Paragraph(f"<b>Step {i}.</b> {desc}", S["body"]))
        if cmd:
            story.append(Paragraph(cmd, S["mono"]))
        story.append(Spacer(1, 1 * mm))

    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("8.3  Build Pipeline", S["h2"]))
    story.append(Paragraph(
        "Run <b>build_app.bat</b>. Ensure the .gguf model "
        "is in <font color='#39ff14'>models/</font> first — it is bundled into the installer.",
        S["body"]
    ))

    build_data = [
        ["Step", "Action"],
        ["1", "Create/update .venv and install all build dependencies"],
        ["2", "Compile main app with PyInstaller using MNIME.spec → dist/MNIME/"],
        ["3", "Build animated installer installer/MNIME_installer.exe via PyInstaller + custom_installer.py"],
    ]
    story.append(spec_table(build_data, [CONTENT_W * 0.08, CONTENT_W * 0.92]))
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 9 — KEYBOARD SHORTCUTS & TIPS
    # ─────────────────────────────────────────────────────────────────────────
    story += section_header("9  Keyboard Shortcuts & Tips", S)

    kb_data = [
        ["Shortcut / Action", "Effect"],
        ["Ctrl + Mouse Scroll", "Zoom in/out in Document Reader and Edit UIs"],
        ["Drag file onto logo", "Queue file for processing"],
        ["Drag card left/right", "Reorder files in the Gallery Carousel"],
        ["Double-click NLP panel", "Spawn magnetic translucent floating chat window"],
        ["Click NLP checkbox", "Toggle NLP master switch (loads/unloads model)"],
        ["Click Reload NLP button", "Load or reload the GGUF model into memory"],
        ["Click X on card", "Remove that file from the queue"],
        ["Click red X (top bar)", "Clear entire file queue"],
        ["Click ADD FILES", "Open custom dark-mode file browser dialog"],
        ["Click primary action button", "Execute the current mode's operation"],
    ]
    story.append(spec_table(kb_data))
    story.append(Spacer(1, 3 * mm))

    tips = [
        "Keep the <b>NLP checkbox unchecked</b> for ultra-lightweight operation when you only need PDF tools.",
        "For <b>Split PDF with Smart Naming</b>, load the NLP model first — the model generates meaningful filenames per page.",
        "For large file batches, MNIME runs document operations on a background worker so the UI stays responsive.",
        "The <b>Compress PDF</b> tool is most effective on PDFs with many embedded images or unoptimized streams.",
        "The <b>Reference Engine</b> works best when multiple documents are already queued in the carousel.",
        "Ctrl+Scroll zoom in the reader is continuous and smooth — there is no discrete zoom step limit.",
    ]
    story.append(Paragraph("Tips", S["h3"]))
    for tip in tips:
        story.append(Paragraph(f"• {tip}", S["body_small"]))
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 10 — PERFORMANCE NOTES
    # ─────────────────────────────────────────────────────────────────────────
    story += section_header("10  Performance Notes", S)

    perf_data = [
        ["Optimization", "Technique"],
        ["C-Accelerated PDF Engine",     "All core PDF operations use PyMuPDF's native C-level routines — up to 50x faster than pure-Python alternatives with negligible RAM footprint"],
        ["O(1) Carousel Operations",     "Drag-and-drop card reorder and removal use surgical layout index shifts; widget tree never torn down even with 5,000 cards loaded"],
        ["Dynamic Memory Management",    "GGUF model and FAISS vector index completely cleared from memory on NLP toggle-off or app close — no background memory hoarding"],
        ["Manual NLP Control",           "Model stays unloaded at startup; user explicitly loads it, keeping startup time instant"],
        ["In-Memory Pixmap Caching",     "Card thumbnails and SVG icons rasterized and pre-scaled once; no CPU resampling during scroll or hover events"],
        ["Hardware-Accelerated Cards",   "Heavy drop shadow textures replaced with pure stylesheet hardware borders — UI scrolls smoothly with 5,000 files"],
        ["60 FPS Non-Blocking UI",       "All processing (PDF ops, NLP inference, indexing) runs in QThread workers; main thread never blocked"],
        ["Image Conversion",    "JPG→PDF and PDF→JPG run sequentially on a background worker (MuPDF is not thread-safe)"],
        ["Split PDF",           "Pages processed sequentially; filenames sanitized for Windows safety"],
        ["Flash Attention",              "Enabled by default for llama-cpp-python if build supports it; graceful fallback if not"],
        ["GPU Auto-Offload",             "n_gpu_layers=-1 tells llama.cpp to offload as many layers as will fit in VRAM automatically"],
    ]
    story.append(spec_table(perf_data))
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 11 — DEPENDENCY STACK
    # ─────────────────────────────────────────────────────────────────────────
    story += section_header("11  Dependency Stack", S)

    dep_data = [
        ["Package", "Version", "Role"],
        ["PyQt6",                "6.11.0",    "Desktop UI framework"],
        ["pymupdf",              "1.28.2",    "Primary PDF/image engine (C-level)"],
        ["pypdf",                "6.19.0",    "PDF fallback engine"],
        ["pdf2docx",             "0.5.13",    "PDF → DOCX conversion"],
        ["python-docx",          "1.2.0",     "DOCX text fallback"],
        ["Pillow",               "12.3.0",    "Image processing fallback"],
        ["llama-cpp-python",     "0.3.35",    "GGUF model inference"],
        ["faiss-cpu",            "1.15.1",    "Vector similarity index"],
        ["langchain",            "0.3.30",    "RAG pipeline orchestration"],
        ["langchain-community",  "0.3.21",    "FAISS vectorstore integration"],
        ["langchain-huggingface","0.3.1",     "Embedding model loading"],
        ["sentence-transformers","6.1.0",     "BAAI/bge-small-en-v1.5 embeddings"],
        ["torch",                "2.14.1",    "Transformer backend"],
        ["transformers",         "5.18.0",    "HuggingFace model utilities"],
        ["numpy",                "2.5.3",     "Numerical operations (≥2.0 required)"],
        ["opencv-python-headless","4.11.0.86","Image processing utilities"],
        ["winsdk",               "latest",    "Windows OCR API for image PDFs"],
        ["scikit-learn",         "1.9.1",     "ML utilities for search"],
        ["pandas",               "2.3.3",     "Data frame operations in search"],
        ["pyinstaller",          "6.22.3",    "Application packaging"],
    ]
    dep_col_w = [CONTENT_W * 0.35, CONTENT_W * 0.17, CONTENT_W * 0.48]
    dep_flowables = [
        [
            Paragraph(f"<b>{html.escape(dep_data[0][0])}</b>", S["table_hdr"]),
            Paragraph(f"<b>{html.escape(dep_data[0][1])}</b>", S["table_hdr"]),
            Paragraph(f"<b>{html.escape(dep_data[0][2])}</b>", S["table_hdr"]),
        ]
    ]
    for row in dep_data[1:]:
        dep_flowables.append([
            Paragraph(html.escape(row[0]), S["table_cell_code"]),
            Paragraph(html.escape(row[1]), S["table_cell_muted"]),
            Paragraph(html.escape(row[2]), S["table_cell_val"]),
        ])
    t = Table(dep_flowables, colWidths=dep_col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), BG_SECTION),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BG_DARK, BG_CARD]),
        ("GRID",           (0, 0), (-1, -1), 0.3, BORDER_COLOR),
        ("TOPPADDING",     (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 4),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 12 — ERROR HANDLING
    # ─────────────────────────────────────────────────────────────────────────
    story += section_header("12  Error Handling & Validation", S)

    story.append(Paragraph(
        "MNIME implements defensive error handling at every layer to prevent crashes and provide "
        "actionable feedback without interrupting the user's workflow.",
        S["body"]
    ))
    story.append(Spacer(1, 3 * mm))

    err_data = [
        ["Scenario", "Behavior"],
        ["Wrong file type for selected mode", "Intelligent intercept before processing; prompt shown without crash"],
        ["Empty file queue on action", "Validated before action; helpful prompt displayed"],
        ["NLP model missing at startup", "Engine initializes silently; error surfaced only when user clicks Reload NLP"],
        ["NLP disabled via checkbox", "Model immediately unloaded; subsequent NLP calls return informative error string"],
        ["PyMuPDF failure on any operation", "Automatic fallback to pypdf + Pillow for merge/compress/convert"],
        ["pdf2docx import failure", "Fallback to pypdf + python-docx text extraction"],
        ["OCR engine unavailable", "Returns empty string; page indexed without text"],
        ["GPU layer offload exceeds VRAM", "llama.cpp automatically reduces layers to CPU"],
        ["Flash Attention unsupported", "TypeError caught; retried without flash_attn kwarg"],
        ["NumPy <2.0 on Python 3.13+", "Requirement pinned to numpy>=2.0.0 to prevent longdouble overflow crash"],
        ["FAISS index empty after smart sampling", "Automatic fallback to full indexing"],
        ["Per-page exception in split/convert", "Per-page try/except; failed pages logged, others continue"],
        ["Application crash", "sys.excepthook overridden to call unload_model() before propagating"],
        ["Process termination (SIGINT/SIGTERM)", "Signal handlers call unload_model() then sys.exit(0)"],
    ]
    story.append(spec_table(err_data))
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 13 — CHANGELOG
    # ─────────────────────────────────────────────────────────────────────────
    story += section_header("13  Changelog", S)

    changelog = [
        ("MNIME Core V5 — Multi-Stage Alignment & Neural Assimilation", [
            "Added: Multi-stage progressive alignment pipeline combining V3 document synthesis, V4 cloud philosophy & adversarial robustness, and V5 sociological anti-bias alignment.",
            "Added: Neural Assimilation Engine (NAE v2.0) featuring streaming fp16/bf16 safetensors TIES-merging, gradient delta isolation, and sign consensus resolution.",
            "Added: Multi-precision model artifacts including full-precision safetensors, 16-bit GGUF (3.09 GB), 8-bit Q8_0 GGUF (1.64 GB), and quantized Q4_K_M GGUF (~1.0 GB).",
            "Improved: Ethical reasoning engine actively deconstructs hate tropes and demographic stereotypes using empirical sociology rather than generic refusal templates.",
        ]),
        ("MNIME Final — Bundled NLP Model", [
            "Changed: The fine-tuned MNIME-Core-1.5B-Q4_K_M.gguf model is now bundled directly inside the application under models/. No external model download required.",
            "Removed: The Settings gear icon and NLP hardware configuration dialog have been removed. Hardware offloading is handled automatically at runtime.",
            "Removed: The finetuning workflow (training/) is no longer part of the repository. The model is shipped as a finished artifact.",
            "Added: Custom animated PyQt6 installer (MNIME_installer.exe).",
        ]),
        ("MNIME — UI & UX Complete Overhaul", [
            "Added: Procedurally generated 5D Penteract branding logo with true mathematical 3D depth-sorting and an independent orbiting neon file.",
            "Added: Advanced High-Resolution 4.0x Retina rendering pipeline for the PDF Reader and Edit UIs.",
            "Added: Fluid Ctrl+Scroll mouse wheel zoom capabilities across all document viewer and editor viewports.",
            "Improved: The Reader UI has been completely decoupled from the main window, featuring its own independent resizable frameless dark metallic window.",
            "Improved: The Image and PDF Edit UIs have been fully upgraded to the MNIME translucent dark metallic theme.",
        ]),
        ("Version 2.1 — Compatibility & Stability", [
            "Fixed: Model loading crash on Python 3.13+ caused by a longdouble overflow in NumPy 1.x getlimits.py.",
            "Updated: NumPy dependency bumped to >=2.0.0. NumPy 2.x resolves the broken _register_known_types initialization on Windows with Python 3.13+.",
            "Updated: pyproject.toml now correctly lists numpy>=2.0.0 and llama-cpp-python>=0.2.75 as explicit dependencies.",
        ]),
        ("Version 2.0 — Initial Public Release", [
            "Full feature set: Merge, Edit, JPG↔PDF, TXT→PDF, Split, Compress, DOCX export, Semantic Bookmarks, NLP/RAG chat, Cross-Reference engine.",
            "Free-floating dark metallic PyQt6 UI with physics particle transitions.",
            "Local offline GGUF model integration via llama-cpp-python.",
            "Custom dark-mode file browser dialog replacing OS file picker.",
            "FAISS-backed semantic search with BAAI/bge-small-en-v1.5 embeddings.",
        ]),
    ]

    for version, items in changelog:
        story.append(Paragraph(version, S["h2"]))
        for item in items:
            story.append(Paragraph(f"• {item}", S["body_small"]))
        story.append(Spacer(1, 3 * mm))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 14 — LICENSE
    # ─────────────────────────────────────────────────────────────────────────
    story += section_header("14  License & Attribution", S)

    story.append(Paragraph("Open Source License", S["h2"]))
    story.append(Paragraph(
        "MNIME is distributed as open source software. See the <b>LICENSE</b> file in the repository "
        "root for the full license text.",
        S["body"]
    ))
    story.append(Spacer(1, 3 * mm))

    attr_data = [
        ["Component", "Author / Source"],
        ["MNIME Application",           "kyledeanml / KyleDeanAI"],
        ["MNIME-Core NLP Model",         "KyleDeanAI — fine-tuned from Qwen2.5-1.5B-Instruct"],
        ["Base Model (Qwen2.5-1.5B)",   "Alibaba Cloud — Qwen Team"],
        ["PyMuPDF",                     "Artifex Software"],
        ["llama-cpp-python",            "Andrei Betlen"],
        ["FAISS",                       "Meta AI Research"],
        ["LangChain",                   "LangChain, Inc."],
        ["BAAI/bge-small-en-v1.5",      "Beijing Academy of Artificial Intelligence"],
        ["PyQt6",                       "Riverbank Computing / The Qt Company"],
        ["pdf2docx",                    "Artifex / dothinking"],
    ]
    story.append(spec_table(attr_data))
    story.append(Spacer(1, 6 * mm))

    story.append(GlowLine(CONTENT_W))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "MNIME — Multimodal Neural Interface Machine Extension",
        ParagraphStyle("footer_big", fontName="Helvetica-Bold", fontSize=10,
                       textColor=ACCENT_CYAN, alignment=TA_CENTER)
    ))
    story.append(Paragraph(
        "Private & Offline — Zero External Uploads — Python 3.12+ / PyQt6 / Windows 10+",
        ParagraphStyle("footer_small", fontName="Helvetica", fontSize=7.5,
                       textColor=TEXT_MUTED, alignment=TA_CENTER, spaceAfter=2)
    ))
    story.append(Paragraph(
        "https://github.com/kyledeanml/MNIME",
        ParagraphStyle("footer_link", fontName="Helvetica", fontSize=7.5,
                       textColor=ACCENT_BLUE, alignment=TA_CENTER)
    ))

    return story


# ─── Build PDF ────────────────────────────────────────────────────────────────

def build_pdf():
    styles = build_styles()

    doc = BaseDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=16 * mm,
        bottomMargin=12 * mm,
        title="MNIME — Full Specification Sheet & User Manual",
        author="kyledeanml / KyleDeanAI",
        subject="MNIME Application Documentation",
        creator="MNIME PDF Generator",
    )

    cover_frame = Frame(0, 0, PAGE_W, PAGE_H, leftPadding=0, rightPadding=0,
                        topPadding=0, bottomPadding=0, id="cover")
    content_frame = Frame(MARGIN, 12 * mm, CONTENT_W, PAGE_H - 28 * mm,
                          leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                          id="content")

    cover_template = PageTemplate(id="cover", frames=[cover_frame],
                                   onPage=draw_cover_background)
    content_template = PageTemplate(id="content", frames=[content_frame],
                                     onPage=draw_page_background)

    doc.addPageTemplates([cover_template, content_template])

    story = build_body(styles)
    doc.build(story)
    print(f"PDF generated: {OUTPUT_PATH}")

    # Render cover preview (Page 1) at 300 DPI
    try:
        import pymupdf
        pdoc = pymupdf.open(OUTPUT_PATH)
        cover_page = pdoc[0]
        pix = cover_page.get_pixmap(matrix=pymupdf.Matrix(300 / 72, 300 / 72), alpha=False)
        cover_path = os.path.join(os.path.dirname(OUTPUT_PATH), "docs", "spec_cover.png")
        os.makedirs(os.path.dirname(cover_path), exist_ok=True)
        pix.save(cover_path)
        pdoc.close()
        print(f"Cover preview rendered: {cover_path} ({pix.width}x{pix.height}px)")
    except Exception as e:
        print(f"Cover preview render skipped: {e}")


if __name__ == "__main__":
    build_pdf()
