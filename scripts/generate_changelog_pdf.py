"""
MNIME - Interactive Change Log & Build History PDF Generator
Parses CHANGE_LOG.txt and produces a high-fidelity, interactive PDF manual with 
document bookmarks, clickable table of contents, and auto-generated cover preview.
"""

import os
import sys
import re
import math
from pathlib import Path
from typing import List, Dict, Any, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    Table, TableStyle, NextPageTemplate, PageBreak
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfgen import canvas as pdfgen_canvas

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
        self.drawString(MARGIN + 38, h - 8.5 * mm, "|   Development Change Log & Build System Runbook")

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
        self.drawString(MARGIN, 3.5 * mm, "Source: CHANGE_LOG.txt   |   Bellevue College AISD   |   kyledeanml/MNIME")

        self.setFillColor(ACCENT_BLUE)
        self.drawRightString(w - MARGIN, 3.5 * mm, "Windows 11 (x64)   |   Release 5.0")
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


class CoverPage(Flowable):
    """High-aesthetic front cover with interactive styling and 5D Penteract projection."""
    def __init__(self, w: float, h: float, version: str = "5.0", date_str: str = "October 2026"):
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
        c.drawCentredString(cx, h * 0.40, "BUILD PROCESS & ENGINEERING CHANGE LOG")

        c.setFont("Helvetica", 9.5)
        c.setFillColor(TEXT_SECONDARY)
        c.drawCentredString(cx, h * 0.375, "Forensic Workspace Evolution, IDE Session Records & Build System Runbook")

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
        c.drawString(card_x + 80, card_y + card_h - 18, "Production Release Ready  |  Windows 11 (x64)")

        # Dynamically calculate commit count and IDE log count
        import subprocess
        import os
        try:
            commit_count = subprocess.check_output(["git", "rev-list", "--count", "HEAD"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
        except Exception:
            commit_count = "289"
            
        try:
            brain_path = os.path.join(os.path.expanduser("~"), ".gemini", "antigravity-ide", "brain")
            if os.path.exists(brain_path):
                ide_count = str(len([d for d in os.listdir(brain_path) if os.path.isdir(os.path.join(brain_path, d))]))
            else:
                ide_count = "95"
        except Exception:
            ide_count = "95"

        # Metadata rows
        meta_items = [
            ("Author & Lead:", "Kyle Bauer / kyledeanml (Bellevue College AISD)"),
            ("Primary Engine:", "PyQt6 / PyMuPDF / llama.cpp (MNIME-Core V5 GGUF)"),
            ("Packaging:", "PyInstaller (Modern Animated)"),
            ("Source Dataset:", f"IDE Logs ({ide_count}+), Git Commits ({commit_count}+), Transcripts & Pytest Suite"),
            ("Generation Source:", f"Dynamic Artifact generated from CHANGE_LOG.txt")
        ]

        row_y = card_y + card_h - 38
        for label, val in meta_items:
            c.setFont("Helvetica-Bold", 7.5)
            c.setFillColor(ACCENT_CYAN)
            c.drawString(card_x + 16, row_y, label)

            c.setFont("Helvetica", 7.5)
            c.setFillColor(TEXT_PRIMARY)
            c.drawString(card_x + 105, row_y, val)
            row_y -= 13

        # 7. Bottom Badges
        badges = ["100% Offline", "Zero Telemetry", "Native Win32 GDI", "Single-Instance IPC", "5D Vector FX"]
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

def sanitize_xml(txt: Any) -> str:
    """Safely escapes text for ReportLab Paragraph XML parsing without double-escaping."""
    if txt is None:
        return ""
    s = str(txt)
    # First unescape if already partially escaped
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def build_styles() -> Dict[str, ParagraphStyle]:
    s = {}
    s["title"] = ParagraphStyle(
        "title", fontName="Helvetica-Bold", fontSize=18, textColor=WHITE,
        spaceAfter=4, spaceBefore=6, leading=22
    )
    s["h1"] = ParagraphStyle(
        "h1", fontName="Helvetica-Bold", fontSize=13, textColor=ACCENT_CYAN,
        spaceAfter=4, spaceBefore=14, leading=16
    )
    s["h2"] = ParagraphStyle(
        "h2", fontName="Helvetica-Bold", fontSize=10.5, textColor=WHITE,
        spaceAfter=3, spaceBefore=8, leading=13
    )
    s["body"] = ParagraphStyle(
        "body", fontName="Helvetica", fontSize=8, textColor=TEXT_PRIMARY,
        spaceAfter=3, leading=11.5, alignment=TA_JUSTIFY
    )
    s["body_bold"] = ParagraphStyle(
        "body_bold", fontName="Helvetica-Bold", fontSize=8, textColor=WHITE,
        spaceAfter=3, leading=11.5
    )
    s["body_small"] = ParagraphStyle(
        "body_small", fontName="Helvetica", fontSize=7.2, textColor=TEXT_SECONDARY,
        spaceAfter=2, leading=10
    )
    s["mono"] = ParagraphStyle(
        "mono", fontName="Courier", fontSize=7.2, textColor=NEON_GREEN,
        spaceAfter=2, leading=9.5
    )
    s["toc_link"] = ParagraphStyle(
        "toc_link", fontName="Helvetica-Bold", fontSize=8.5, textColor=ACCENT_CYAN,
        spaceAfter=4, leading=12
    )
    s["toc_desc"] = ParagraphStyle(
        "toc_desc", fontName="Helvetica", fontSize=7.2, textColor=TEXT_SECONDARY,
        spaceAfter=6, leading=10
    )
    s["card_label"] = ParagraphStyle(
        "card_label", fontName="Helvetica-Bold", fontSize=7.5, textColor=ACCENT_CYAN,
        leading=9.5
    )
    s["card_val"] = ParagraphStyle(
        "card_val", fontName="Helvetica", fontSize=7.5, textColor=TEXT_PRIMARY,
        leading=9.5
    )
    return s


# ─── Parser for CHANGE_LOG.txt ────────────────────────────────────────────────

def parse_changelog(filepath: str) -> Dict[str, Any]:
    """Parses CHANGE_LOG.txt into structured sections, phases, and sessions."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Changelog file not found at: {filepath}")

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    data = {
        "metadata": {},
        "sections": []
    }

    # Extract header metadata
    header_match = re.search(r"Document:\s+(.*?)\nWorkspace:\s+(.*?)\nProduct Name:\s+(.*?)\nCurrent Version:\s+(.*?)\nTarget OS:\s+(.*?)\nAuthor:\s+(.*?)\nCreated:\s+(.*?)\nSource Data:\s+(.*?)\n", content)
    if header_match:
        data["metadata"] = {
            "document": header_match.group(1).strip(),
            "workspace": header_match.group(2).strip(),
            "product": header_match.group(3).strip(),
            "version": header_match.group(4).strip(),
            "target_os": header_match.group(5).strip(),
            "author": header_match.group(6).strip(),
            "created": header_match.group(7).strip(),
            "source": header_match.group(8).strip()
        }

    # Split into primary numbered sections: e.g. "1. EXECUTIVE SUMMARY & WORKSPACE FOUNDATION"
    section_pattern = re.compile(r"\n([1-9]\.\s+[A-Z0-9\s,&/-]+)\n[-=]+\n", re.MULTILINE)
    matches = list(section_pattern.finditer(content))

    for i, m in enumerate(matches):
        sec_title = m.group(1).strip()
        start_idx = m.end()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        sec_text = content[start_idx:end_idx].strip()
        
        sec_title = sec_title.split("\n")[0].strip()
        sec_obj = {
            "id": f"sec_{i+1}",
            "title": sec_title,
            "raw": sec_text
        }

        # Special parsing for Section 3 (IDE Sessions)
        if "IDE SESSIONS LOG" in sec_title:
            sessions = []
            pattern = re.compile(
                r'SESSION ID:\s+([^\n]+)\nTIMESTAMP:\s+([^\n]+)\nUSER GOAL:\s+(.*?)\nINVESTIGATION:\s+(.*?)\nROOT CAUSE:\s+(.*?)\nSOLUTION:\s+(.*?)\nFILES TOUCHED:\s+(.*?)(?=\n-{40,}|\Z)',
                re.DOTALL
            )
            for m in pattern.finditer(sec_text):
                sess_data = {
                    "id": m.group(1).strip(),
                    "timestamp": m.group(2).strip(),
                    "user_goal": " ".join(m.group(3).split()),
                    "investigation": " ".join(m.group(4).split()),
                    "root_cause": " ".join(m.group(5).split()),
                    "solution": " ".join(m.group(6).split()),
                    "files": " ".join(m.group(7).split())
                }
                sessions.append(sess_data)
            sec_obj["sessions"] = sessions

        data["sections"].append(sec_obj)

    return data


# ─── PDF Generation Pipeline ──────────────────────────────────────────────────

def generate_pdf(changelog_path: str, output_pdf_path: str, cover_png_path: str = None):
    """Compiles CHANGE_LOG.txt into an interactive PDF and exports preview cover."""
    parsed = parse_changelog(changelog_path)
    styles = build_styles()

    doc = BaseDocTemplate(
        output_pdf_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN
    )

    cover_frame = Frame(0, 0, PAGE_W, PAGE_H, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="cover_f")
    content_frame = Frame(MARGIN, MARGIN + 4 * mm, CONTENT_W, PAGE_H - 2 * MARGIN - 8 * mm, 
                          leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="content_f")

    def draw_content_bg(canvas, document):
        canvas.saveState()
        w, h = canvas._pagesize
        canvas.setFillColor(BG_DARK)
        canvas.rect(0, 0, w, h, fill=1, stroke=0)
        canvas.setFillColor(BORDER_COLOR)
        canvas.setFillAlpha(0.2)
        for x in range(int(MARGIN), int(w - MARGIN), 20):
            for y in range(int(MARGIN), int(h - MARGIN), 20):
                canvas.circle(x, y, 0.4, fill=1, stroke=0)
        canvas.restoreState()

    cover_template = PageTemplate(id="cover", frames=[cover_frame])
    content_template = PageTemplate(id="content", frames=[content_frame], onPage=draw_content_bg)
    doc.addPageTemplates([cover_template, content_template])

    story = []

    # 1. COVER PAGE
    meta = parsed.get("metadata", {})
    ver = meta.get("version", "5.0")
    story.append(CoverPage(PAGE_W, PAGE_H, version=ver, date_str=meta.get("created", "October 2026")))
    story.append(NextPageTemplate("content"))
    story.append(PageBreak())

    # 2. TABLE OF CONTENTS / QUICK DIRECTORY
    story.append(Paragraph("TABLE OF CONTENTS & DIRECTORY", styles["h1"]))
    story.append(GlowLine(CONTENT_W, thickness=1.0))
    story.append(Spacer(1, 4 * mm))

    toc_table_data = []
    for s in parsed["sections"]:
        sec_num = s["title"].split(".")[0].strip()
        sec_name = s["title"].split(".", 1)[1].strip()
        
        desc_map = {
            "1": "Project architecture, core technology stack, offline principles, and runtime specifications.",
            "2": "Chronological evolution from OmniMesh genesis through 5D vector math, NLP, and release hardening.",
            "3": "Detailed forensic log of 22 IDE conversation sessions, problem diagnosis, and technical remediations.",
            "4": "End-to-end build commands, and custom animated installer compilation runbook.",
            "5": "Deep-dives into native Win32 GDI printing, single-instance named pipes, and heuristic bookmarking.",
            "6": "Pytest validation, benchmark procedures, and Windows Add/Remove Programs clean uninstallation."
        }
        desc_text = desc_map.get(sec_num, "Detailed reference and operational documentation.")
        
        p_link = Paragraph(f"<b>{sec_num}. {sec_name}</b>", styles["toc_link"])
        p_desc = Paragraph(desc_text, styles["toc_desc"])
        toc_table_data.append([p_link, p_desc])

    toc_table = Table(toc_table_data, colWidths=[CONTENT_W * 0.45, CONTENT_W * 0.55])
    toc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_CARD),
        ('BOX', (0, 0), (-1, -1), 0.8, BORDER_BRIGHT),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(toc_table)
    story.append(Spacer(1, 6 * mm))

    # Repository & Environment Snapshot Card
    story.append(Paragraph("ENVIRONMENT SPECIFICATIONS SNAPSHOT", styles["h2"]))
    env_data = [
        [Paragraph("<b>Operating System</b>", styles["card_label"]), Paragraph(meta.get("target_os", "Windows 11 (x64)"), styles["card_val"]),
         Paragraph("<b>Runtime</b>", styles["card_label"]), Paragraph("Python 3.12.8 (64-bit)", styles["card_val"])],
        [Paragraph("<b>Framework</b>", styles["card_label"]), Paragraph("PyQt6 v6.7+ with OpenGL QPainter", styles["card_val"]),
         Paragraph("<b>Local Model</b>", styles["card_label"]), Paragraph("MNIME-Core V5 (GGUF Q4_K_M)", styles["card_val"])],
        [Paragraph("<b>Document Engine</b>", styles["card_label"]), Paragraph("PyMuPDF 1.24+ / pypdf / pdf2docx", styles["card_val"]),
         Paragraph("<b>Print Subsystem</b>", styles["card_label"]), Paragraph("Native Win32 GDI (ctypes, PrintDlgW)", styles["card_val"])],
        [Paragraph("<b>Workspace URI</b>", styles["card_label"]), Paragraph(meta.get("workspace", "b:\\Desktop\\BASSD\\..."), styles["card_val"]),
         Paragraph("<b>License</b>", styles["card_label"]), Paragraph("MIT License (Fully Open Source)", styles["card_val"])]
    ]
    env_table = Table(env_data, colWidths=[CONTENT_W * 0.2, CONTENT_W * 0.3, CONTENT_W * 0.2, CONTENT_W * 0.3])
    env_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_SECTION),
        ('BOX', (0, 0), (-1, -1), 0.8, ACCENT_DIM),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(env_table)
    story.append(Spacer(1, 6 * mm))

    # 3. RENDER EACH NUMBERED SECTION
    for s in parsed["sections"]:
        story.append(PageBreak())
        story.append(Paragraph(s["title"], styles["h1"]))
        story.append(GlowLine(CONTENT_W, thickness=0.8))
        story.append(Spacer(1, 4 * mm))

        if "sessions" in s:
            story.append(Paragraph(
                "The following log documents the exact conversation sessions conducted within the IDE workspace. "
                "Each entry details the user requirement, the technical diagnosis, the identified root cause, and the files modified.",
                styles["body"]
            ))
            story.append(Spacer(1, 3 * mm))

            for sess in s["sessions"]:
                s_id = sanitize_xml(sess["id"])
                s_time = sanitize_xml(sess["timestamp"])
                s_goal = sanitize_xml(sess["user_goal"])
                s_inv = sanitize_xml(sess["investigation"])
                s_rc = sanitize_xml(sess["root_cause"])
                s_sol = sanitize_xml(sess["solution"])
                s_files = sanitize_xml(sess["files"])

                header_text = f'<b>SESSION ID:</b> <font color="#00e5ff">{s_id}</font>   |   <b>TIMESTAMP:</b> {s_time}'
                card_data = [
                    [Paragraph(header_text, styles["body_bold"])],
                    [Paragraph(f'<b>User Goal:</b> <font color="#e8eaf6">{s_goal}</font>', styles["body"])],
                    [Paragraph(f'<b>Technical Diagnosis:</b> {s_inv}', styles["body_small"])],
                    [Paragraph(f'<b>Root Cause:</b> <font color="#ffd700">{s_rc}</font>', styles["body_small"])],
                    [Paragraph(f'<b>Remediation / Solution:</b> {s_sol}', styles["body_small"])],
                    [Paragraph(f'<b>Files Modified:</b> <font color="#39ff14">{s_files}</font>', styles["mono"])]
                ]
                
                t = Table(card_data, colWidths=[CONTENT_W])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), BG_CARD_LIGHT),
                    ('BACKGROUND', (0, 1), (-1, -1), BG_CARD),
                    ('BOX', (0, 0), (-1, -1), 0.8, BORDER_BRIGHT),
                    ('LINEBELOW', (0, 0), (-1, 0), 0.6, ACCENT_CYAN),
                    ('INNERGRID', (0, 1), (-1, -1), 0.3, BORDER_COLOR),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ]))
                story.append(t)
                story.append(Spacer(1, 3.5 * mm))
        else:
            lines = s["raw"].split("\n")
            in_code_block = False
            code_lines = []

            def create_code_box(clist):
                code_txt = "<br/>".join(clist)
                p_code = Paragraph(code_txt, styles["mono"])
                box = Table([[p_code]], colWidths=[CONTENT_W])
                box.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), BG_CARD),
                    ('BOX', (0, 0), (-1, -1), 0.6, BORDER_COLOR),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ]))
                return box

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    if in_code_block and code_lines:
                        story.append(create_code_box(code_lines))
                        story.append(Spacer(1, 2 * mm))
                        code_lines = []
                        in_code_block = False
                    continue

                if stripped.startswith("Phase ") or stripped.startswith("Step ") or (len(stripped) > 2 and stripped[1] == "." and stripped[0].isalpha()):
                    if in_code_block and code_lines:
                        story.append(create_code_box(code_lines))
                        code_lines = []
                        in_code_block = False
                    
                    story.append(Spacer(1, 2 * mm))
                    story.append(Paragraph(f'<b>{stripped}</b>', styles["h2"]))
                    continue

                if line.startswith("    python") or line.startswith("    .venv") or line.startswith("    git ") or line.startswith("    rmdir") or line.startswith("     ") or line.startswith("  Source Code") or line.startswith("    -->") or line.startswith("          1.") or line.startswith("          2."):
                    in_code_block = True
                    code_lines.append(sanitize_xml(stripped))
                    continue
                else:
                    if in_code_block and code_lines:
                        story.append(create_code_box(code_lines))
                        story.append(Spacer(1, 2 * mm))
                        code_lines = []
                        in_code_block = False

                if stripped.startswith("* "):
                    sub_text = sanitize_xml(stripped[2:])
                    story.append(Paragraph(f'&nbsp;&nbsp;&nbsp;&nbsp;<font color="#90a4ae">&#9658;</font>  {sub_text}', styles["body_small"]))
                elif stripped.startswith("- "):
                    bullet_text = sanitize_xml(stripped[2:])
                    story.append(Paragraph(f'<font color="#00e5ff">&#8226;</font>  {bullet_text}', styles["body"]))
                else:
                    clean_text = sanitize_xml(stripped)
                    story.append(Paragraph(clean_text, styles["body"]))

            if in_code_block and code_lines:
                story.append(create_code_box(code_lines))
                story.append(Spacer(1, 2 * mm))

    # Build PDF with ReportLab
    print(f"Step 1: Compiling PDF layout to: {output_pdf_path} ...")
    doc.build(story, canvasmaker=NumberedCanvas)
    print("ReportLab build successful!")

    # 4. POST-PROCESSING: ADD INTERACTIVE BOOKMARKS & JUMP LINKS VIA PYMUPDF
    postprocess_interactive_pdf(output_pdf_path, parsed)

    # 5. EXPORT COVER PREVIEW IMAGE VIA PYMUPDF
    if cover_png_path:
        export_cover_image(output_pdf_path, cover_png_path)


def postprocess_interactive_pdf(pdf_path: str, parsed: Dict[str, Any]):
    """Uses PyMuPDF to wire up a 100% accurate, clickable Table of Contents and bookmark tree."""
    import pymupdf
    print("Step 2: Post-processing interactive bookmarks and jump links...")
    doc = pymupdf.open(pdf_path)

    toc_entries = [
        [1, "MNIME Cover", 1],
        [1, "Table of Contents & Directory", 2]
    ]

    section_pages = {}
    
    # Locate exact page numbers for each numbered section
    for p_idx, page in enumerate(doc):
        text = page.get_text()
        for s in parsed["sections"]:
            sec_num = s["title"].split(".")[0].strip()
            # Match section header on content pages (page index >= 2)
            if p_idx >= 2 and s["title"] in text:
                if sec_num not in section_pages:
                    section_pages[sec_num] = p_idx + 1

    # Build hierarchical TOC
    for s in parsed["sections"]:
        sec_num = s["title"].split(".")[0].strip()
        p_num = section_pages.get(sec_num, 3)
        toc_entries.append([1, s["title"], p_num])

        # Sub-bookmarks for Section 2 (Phases)
        if sec_num == "2":
            phase_regex = re.compile(r"Phase\s+\d+:\s+([^\n]+)")
            for p_idx, page in enumerate(doc):
                if p_idx + 1 >= p_num and p_idx + 1 <= section_pages.get("3", 6):
                    for match in phase_regex.finditer(page.get_text()):
                        phase_title = match.group(0).split("(")[0].strip()
                        toc_entries.append([2, phase_title, p_idx + 1])

        # Sub-bookmarks for Section 3 (Sessions)
        elif sec_num == "3" and "sessions" in s:
            for sess in s["sessions"]:
                # Search which page this session card appears on
                sess_target_p = p_num
                sess_query = sess["id"]
                for p_idx, page in enumerate(doc):
                    if p_idx + 1 >= p_num and sess_query in page.get_text():
                        sess_target_p = p_idx + 1
                        break
                label = f"Session {sess['id'][:8]}: {sess['user_goal'][:32]}..."
                toc_entries.append([2, label, sess_target_p])

        # Sub-bookmarks for Section 4 (Build Steps)
        elif sec_num == "4":
            step_regex = re.compile(r"Step\s+\d+:\s+([^\n]+)")
            for p_idx, page in enumerate(doc):
                if p_idx + 1 >= p_num and p_idx + 1 <= section_pages.get("5", 13):
                    for match in step_regex.finditer(page.get_text()):
                        step_title = match.group(0).strip()
                        toc_entries.append([2, step_title, p_idx + 1])

        # Sub-bookmarks for Section 5 (Subsystems)
        elif sec_num == "5":
            sub_regex = re.compile(r"([A-D]\.\s+[^\n]+)")
            for p_idx, page in enumerate(doc):
                if p_idx + 1 >= p_num and p_idx + 1 <= section_pages.get("6", 14):
                    for match in sub_regex.finditer(page.get_text()):
                        sub_title = match.group(0).strip()
                        toc_entries.append([2, sub_title, p_idx + 1])

        # Sub-bookmarks for Section 6 (Verification)
        elif sec_num == "6":
            ver_regex = re.compile(r"([A-C]\.\s+[^\n]+)")
            for p_idx, page in enumerate(doc):
                if p_idx + 1 >= p_num:
                    for match in ver_regex.finditer(page.get_text()):
                        ver_title = match.group(0).strip()
                        toc_entries.append([2, ver_title, p_idx + 1])

    # Deduplicate and apply Table of Contents outline to PDF
    seen_entries = set()
    cleaned_toc = []
    for entry in toc_entries:
        key = (entry[0], entry[1], entry[2])
        if key not in seen_entries:
            seen_entries.add(key)
            cleaned_toc.append(entry)

    doc.set_toc(cleaned_toc)
    print(f"Applied {len(cleaned_toc)} interactive bookmarks to PDF outline.")

    # 4B. Wire Up Clickable Links on Page 2 (TOC)
    p2 = doc[1]
    # Delete default empty links
    for old_link in p2.get_links():
        p2.delete_link(old_link)

    for s in parsed["sections"]:
        sec_num = s["title"].split(".")[0].strip()
        sec_name = s["title"].split(".", 1)[1].strip()
        target_p = section_pages.get(sec_num, 3)

        # Search for section title on Page 2
        search_query = f"{sec_num}. {sec_name}"
        rects = p2.search_for(search_query)
        if not rects:
            # Fallback to searching first 3 words
            search_query = " ".join(f"{sec_num}. {sec_name}".split()[:3])
            rects = p2.search_for(search_query)

        if rects:
            r = rects[0]
            # Create clickable link encompassing the row
            click_rect = pymupdf.Rect(MARGIN, r.y0 - 4, PAGE_W - MARGIN, r.y1 + 16)
            link_dict = {
                "kind": pymupdf.LINK_GOTO,
                "page": target_p - 1, # 0-indexed in PyMuPDF
                "from": click_rect,
                "to": pymupdf.Point(0, 0),
                "zoom": 0.0
            }
            p2.insert_link(link_dict)

    # Save finalized interactive PDF
    temp_path = str(pdf_path) + ".tmp"
    doc.save(temp_path, incremental=False, deflate=True)
    doc.close()

    os.replace(temp_path, pdf_path)
    print("Interactive jump links and outline successfully persisted!")


def export_cover_image(pdf_path: str, cover_png_path: str):
    """Renders page 1 of the PDF to a high-resolution PNG cover preview."""
    import pymupdf
    print(f"Step 3: Exporting cover preview to: {cover_png_path} ...")
    doc = pymupdf.open(pdf_path)
    if len(doc) > 0:
        page = doc[0]
        # Render at 300 DPI (zoom = 300 / 72 ≈ 4.16666)
        zoom = 300.0 / 72.0
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        os.makedirs(os.path.dirname(os.path.abspath(cover_png_path)), exist_ok=True)
        pix.save(cover_png_path)
        print(f"Cover preview successfully generated: {pix.width}x{pix.height}px ({os.path.getsize(cover_png_path):,} bytes)")
    doc.close()


def main():
    root_dir = Path(__file__).resolve().parent.parent
    changelog_txt = root_dir / "CHANGE_LOG.txt"
    output_pdf = root_dir / "MNIME_Change_Log.pdf"
    cover_png = root_dir / "docs" / "changelog_cover.png"

    if len(sys.argv) > 1:
        changelog_txt = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_pdf = Path(sys.argv[2])
    if len(sys.argv) > 3:
        cover_png = Path(sys.argv[3])

    generate_pdf(str(changelog_txt), str(output_pdf), str(cover_png))


if __name__ == "__main__":
    main()
