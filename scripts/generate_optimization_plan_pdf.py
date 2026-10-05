"""
MNIME - Idle Footprint & Performance Optimization Plan PDF Generator
Produces a handoff brief (MNIME_Optimization_Plan.pdf) intended to be given to an
implementing model. Contains measured baseline, ranked findings with file/line
references, phased roadmap with acceptance criteria, and code sketches.
"""

import os
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Preformatted, KeepTogether
)

# ─── Palette (matches generate_architecture_pdf.py) ───────────────────────────
BG_DARK = colors.HexColor("#0b0f19")
BG_CARD = colors.HexColor("#111827")
BG_CODE = colors.HexColor("#070a12")
BG_SECTION = colors.HexColor("#0d1526")
ACCENT_CYAN = colors.HexColor("#00e5ff")
ACCENT_BLUE = colors.HexColor("#00a8e8")
TEXT_PRIMARY = colors.HexColor("#e8eaf6")
TEXT_SECONDARY = colors.HexColor("#90a4ae")
TEXT_MUTED = colors.HexColor("#546e7a")
NEON_GREEN = colors.HexColor("#39ff14")
AMBER = colors.HexColor("#ffb300")
RED = colors.HexColor("#ff5370")
BORDER = colors.HexColor("#1f2737")

PAGE_W, PAGE_H = A4
MARGIN = 16 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_PATH = os.path.join(ROOT, "MNIME_Optimization_Plan.pdf")

# ─── Styles ───────────────────────────────────────────────────────────────────
S_TITLE = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=26, leading=31,
                         textColor=TEXT_PRIMARY, spaceAfter=4)
S_SUB = ParagraphStyle("sub", fontName="Helvetica", fontSize=12, leading=16,
                       textColor=ACCENT_CYAN, spaceAfter=14)
S_H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15, leading=19,
                      textColor=ACCENT_CYAN, spaceBefore=10, spaceAfter=6)
S_H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11, leading=14,
                      textColor=TEXT_PRIMARY, spaceBefore=8, spaceAfter=3)
S_BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=8.8, leading=12.2,
                        textColor=TEXT_PRIMARY, spaceAfter=4)
S_SMALL = ParagraphStyle("small", parent=S_BODY, fontSize=7.8, leading=10.4,
                         textColor=TEXT_SECONDARY)
S_BULLET = ParagraphStyle("bullet", parent=S_BODY, leftIndent=10, bulletIndent=2,
                          spaceAfter=2)
S_CELL = ParagraphStyle("cell", parent=S_BODY, fontSize=7.8, leading=10, spaceAfter=0)
S_CELL_B = ParagraphStyle("cellb", parent=S_CELL, fontName="Helvetica-Bold",
                          textColor=ACCENT_CYAN)
S_CODE = ParagraphStyle("code", fontName="Courier", fontSize=7.2, leading=8.9,
                        textColor=colors.HexColor("#c3e88d"))


def P(text, style=S_BODY):
    return Paragraph(text, style)


def code(text):
    t = Table([[Preformatted(text.strip("\n"), S_CODE)]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_CODE),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("LINEBEFORE", (0, 0), (0, -1), 2, ACCENT_BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def bullets(items, style=S_BULLET):
    return [Paragraph(i, style, bulletText="\u2022") for i in items]


def table(rows, widths, header=True):
    data = []
    for r_i, row in enumerate(rows):
        st = S_CELL_B if (header and r_i == 0) else S_CELL
        data.append([c if not isinstance(c, str) else Paragraph(c, st) for c in row])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), BG_SECTION))
    t.setStyle(TableStyle(style))
    return t


def callout(text, color=AMBER, label="NOTE"):
    t = Table([[Paragraph(f"<font color='{color.hexval()}'><b>{label}</b></font>&nbsp;&nbsp;{text}",
                          S_BODY)]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_SECTION),
        ("LINEBEFORE", (0, 0), (0, -1), 3, color),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


SEV_COLORS = {"CRITICAL": RED, "HIGH": AMBER, "MEDIUM": ACCENT_BLUE, "LOW": TEXT_SECONDARY}


def finding(fid, sev, title, where, problem, fix, gain, risk, extra=None):
    """A finding card: header row + labelled rows. Kept together on one page where possible."""
    col = SEV_COLORS[sev]
    head = Paragraph(
        f"<font color='{col.hexval()}'><b>{fid} [{sev}]</b></font>&nbsp;&nbsp;<b>{title}</b>", S_BODY)
    rows = [[head, ""]]
    for label, val in (("Where", where), ("Problem", problem), ("Fix", fix),
                       ("Expected gain", gain), ("Risk", risk)):
        rows.append([Paragraph(f"<b>{label}</b>", S_CELL_B), Paragraph(val, S_CELL)])
    t = Table(rows, colWidths=[24 * mm, CONTENT_W - 24 * mm])
    t.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)),
        ("BACKGROUND", (0, 0), (-1, 0), BG_SECTION),
        ("BACKGROUND", (0, 1), (-1, -1), BG_CARD),
        ("LINEBEFORE", (0, 0), (0, -1), 3, col),
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    parts = [t]
    if extra is not None:
        parts += [Spacer(1, 3), extra]
    parts.append(Spacer(1, 8))
    return KeepTogether(parts)


# ─── Page decoration ──────────────────────────────────────────────────────────

def on_page(canv, doc):
    canv.saveState()
    canv.setFillColor(BG_DARK)
    canv.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    if doc.page > 1:
        canv.setFillColor(BG_SECTION)
        canv.rect(0, PAGE_H - 12 * mm, PAGE_W, 12 * mm, fill=1, stroke=0)
        canv.setFillColor(ACCENT_CYAN)
        canv.rect(0, PAGE_H - 1.5, PAGE_W, 1.5, fill=1, stroke=0)
        canv.setFont("Helvetica-Bold", 7.5)
        canv.setFillColor(TEXT_SECONDARY)
        canv.drawString(MARGIN, PAGE_H - 8 * mm, "MNIME")
        canv.setFont("Helvetica", 7.5)
        canv.setFillColor(TEXT_MUTED)
        canv.drawString(MARGIN + 30, PAGE_H - 8 * mm,
                        "|   Idle Footprint & Performance Optimization Plan")
        canv.setFillColor(ACCENT_CYAN)
        canv.setFont("Helvetica-Bold", 7.5)
        canv.drawRightString(PAGE_W - MARGIN, PAGE_H - 8 * mm, f"Page {doc.page}")
    canv.setFillColor(BG_SECTION)
    canv.rect(0, 0, PAGE_W, 9 * mm, fill=1, stroke=0)
    canv.setFont("Helvetica", 7)
    canv.setFillColor(TEXT_MUTED)
    canv.drawString(MARGIN, 3.5 * mm, "Handoff brief for implementing model   |   kyledeanml/MNIME")
    canv.setFillColor(ACCENT_BLUE)
    canv.drawRightString(PAGE_W - MARGIN, 3.5 * mm, f"Windows 11 (x64)   |   {date(2026, 10, 5).isoformat()}")
    canv.restoreState()


class PlanDoc(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=17 * mm, bottomMargin=14 * mm,
                         title="MNIME Idle Footprint & Performance Optimization Plan",
                         author="MNIME", subject="Optimization handoff brief")
        frame = Frame(MARGIN, 14 * mm, CONTENT_W, PAGE_H - 31 * mm, id="f",
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=on_page)])
        self._bm = 0

    def afterFlowable(self, flowable):
        """Add PDF outline bookmarks for H1/H2 headings."""
        if isinstance(flowable, Paragraph) and flowable.style.name in ("h1", "h2"):
            text = flowable.getPlainText()
            key = f"bm{self._bm}"
            self._bm += 1
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=0 if flowable.style.name == "h1" else 1)


# ─── Content ──────────────────────────────────────────────────────────────────

def build_story():
    s = []
    W = CONTENT_W

    # ---------------- Cover ----------------
    s += [Spacer(1, 30 * mm),
          P("MNIME", ParagraphStyle("brand", fontName="Helvetica-Bold", fontSize=11,
                                    textColor=ACCENT_CYAN, leading=14)),
          P("Idle Footprint &amp; Performance Optimization Plan", S_TITLE),
          P("Handoff brief for an implementing model (Gemini 3.1 Pro). Ranked findings, "
            "measured baseline, phased roadmap, acceptance criteria, and code sketches.", S_SUB),
          Spacer(1, 6)]
    s.append(table([
        ["Measured now (installed build, idle in tray)", "Target after this plan"],
        ["<b>136.0 MB</b> working set, <b>62.4 MB</b> private bytes", "Working set under 25 MB when idle in tray (Phase 2)"],
        ["<b>0.02 CPU-seconds</b> burned in 60s idle (~0.001% of one core)", "~0% idle CPU; no timers firing while hidden (Phase 1)"],
        ["2 threads, 1,183 handles, no ML libraries loaded", "Reader open/close returns to baseline within 5 MB (Phase 3)"],
        ["torch / transformers / langchain bundled for embeddings", "torch-free build; embeddings via llama.cpp or ONNX (Phase 4)"],
        ["Single monolithic Python+Qt process resident forever", "Optional native tray stub: ~1-3 MB resident (Phase 5, wild)"],
    ], [W * 0.5, W * 0.5]))
    s += [Spacer(1, 10),
          callout("The baseline above was sampled from the running process "
                  "<i>C:\\Users\\kyled\\AppData\\Local\\Programs\\MNIME\\MNIME.exe</i> (PID 25468) via "
                  "Get-Process on 2026-10-05 after 4h 12m uptime. Loaded heavy modules: mupdfcpp64.dll "
                  "(25.1 MB image), _mupdf.pyd (12.5), Qt6Core (9.9), Qt6Gui (9.2), python312 (6.6), "
                  "Qt6Widgets (6.2), Qt6Pdf (4.4), Qt6Network (1.7), Qt6Svg (0.6). No torch, llama, "
                  "ggml, faiss, or CUDA DLLs were resident, so the 136 MB footprint is UI, Python heap, and "
                  "MuPDF, not the model.", ACCENT_CYAN, "MEASURED"),
          PageBreak()]

    # ---------------- 0. Instructions ----------------
    s.append(P("0. Instructions for the Implementing Model", S_H1))
    s += bullets([
        "Platform is Windows 11 x64, Python 3.12, PyQt6 6.11, PyMuPDF 1.28.2, llama-cpp-python 0.3.35, "
        "built with PyInstaller onedir (<i>MNIME.spec</i>). Use Windows commands (PowerShell), not Linux.",
        "Work phase by phase in the order of Section 4. Do not start a phase before the previous "
        "phase's acceptance criteria pass. One commit per phase; append a CHANGE_LOG.txt entry.",
        "<b>Measure before and after every change</b> using the protocol in Section 2. Record numbers in "
        "<i>docs/perf/baseline.json</i> and <i>docs/perf/phase_N.json</i>.",
        "Preserve all visual features. Animations must still play whenever their widget is actually "
        "visible on screen. The goal is to stop work nobody can see, not to remove the aesthetic.",
        "Keep the IPC protocol in <i>core/ipc.py</i> backward compatible. Keep QSettings keys stable.",
        "Every Win32 call goes through ctypes with argtypes/restype declared, wrapped in try/except, and "
        "is a no-op on non-Windows platforms.",
        "Preserve existing comments and docstrings unrelated to the change. Do not use emojis.",
        "Never touch <i>training/</i>, <i>models/</i>, or <i>V3_Training_Pipeline/</i>.",
    ])

    s.append(P("Reality check on the Chrome comparison", S_H2))
    s.append(P(
        "A backgrounded Chrome tab showing ~1.5 MB is a renderer process that Chrome has frozen and whose "
        "working set has been trimmed (or the tab was discarded entirely); the browser, GPU, and network "
        "processes still hold the real memory. A Python 3.12 + Qt6 process cannot get its "
        "<i>committed private bytes</i> anywhere near 1.5 MB, since python312.dll plus the Qt core DLLs alone "
        "map ~32 MB of image. Chrome uses two tricks that MNIME can copy: "
        "(1) <b>trim the working set when idle</b> (Phase 2: Task Manager's default Memory column drops to "
        "tens of MB), and (2) <b>keep only a tiny process resident</b> and spawn the heavy one on demand "
        "(Phase 5: genuinely ~1-3 MB resident)."))

    # ---------------- 1. Architecture snapshot ----------------
    s.append(P("1. Current Runtime Shape (as of this audit)", S_H1))
    s.append(table([
        ["Component", "File", "Idle behaviour observed in code"],
        ["Splash screen", "MNIME.py L112-273, L391-405", "300-particle sim on a 16 ms QTimer; closed via close() but never stopped or deleted"],
        ["Carousel logo", "ui/carousel_view.py L24-52", "Re-renders a new 240 px 5D penteract QPixmap every 33 ms, visible or not"],
        ["Tabs bar status", "ui/tabs_bar.py L170-200+", "1 s QTimer calls setStyleSheet() unconditionally (full re-polish each tick)"],
        ["Global event filter", "ui/main_window.py L124-125", "MainWindow.eventFilter installed on QCoreApplication: every event app-wide hits Python"],
        ["Main window", "ui/main_window.py L111-113", "Frameless + WA_TranslucentBackground: ARGB backing store, DWM alpha composition"],
        ["Reader", "ui/reader_dialog.py", "Frameless translucent QDialog, parent=None, no WA_DeleteOnClose; renders whole page bitmap per zoom step"],
        ["Cross-reference viewer", "ui/document_viewer.py", "Fixed 2.0x render, extra QImage.copy(); separate render path from reader"],
        ["File thumbnails", "core/file_item.py L69-151", "Keeps PNG bytes AND decoded QPixmap per file, for all files (up to 5,000)"],
        ["LLM", "core/nlp_engine.py L103-185", "Lazy load (good) but never unloads on idle; n_ctx 4096, all layers on GPU"],
        ["Embeddings", "core/search_engine.py L140-160", "langchain_huggingface -> sentence_transformers -> torch (300-600 MB when loaded)"],
        ["Build", "MNIME.spec L65-83", "collect_all() on langchain, sentence_transformers (pulls torch), faiss, llama_cpp"],
    ], [W * 0.18, W * 0.27, W * 0.55]))
    s.append(PageBreak())

    # ---------------- 2. Measurement protocol ----------------
    s.append(P("2. Measurement Protocol (Phase 0, do this first)", S_H1))
    s.append(P("Create <i>scripts/measure_idle.ps1</i>. It samples a process by name for a fixed window and "
               "emits JSON. Run every scenario three times on the installed build and on source "
               "(<i>.venv\\Scripts\\python.exe MNIME.py</i>); report the median."))
    s.append(code(r"""
param([string]$Name = "MNIME", [int]$Seconds = 60, [string]$Scenario = "S1")
$p  = Get-Process -Name $Name | Sort-Object WorkingSet64 -Descending | Select-Object -First 1
$c0 = $p.TotalProcessorTime.TotalSeconds
Start-Sleep -Seconds $Seconds
$p.Refresh()
$c1 = $p.TotalProcessorTime.TotalSeconds
[pscustomobject]@{
  scenario   = $Scenario
  ws_mb      = [math]::Round($p.WorkingSet64 / 1MB, 1)
  private_mb = [math]::Round($p.PrivateMemorySize64 / 1MB, 1)
  peak_ws_mb = [math]::Round($p.PeakWorkingSet64 / 1MB, 1)
  threads    = $p.Threads.Count
  handles    = $p.HandleCount
  cpu_pct    = [math]::Round(100 * ($c1 - $c0) / $Seconds / [Environment]::ProcessorCount, 3)
  cpu_s      = [math]::Round($c1 - $c0, 2)
} | ConvertTo-Json
"""))
    s.append(table([
        ["ID", "Scenario", "What to record"],
        ["S0", "Cold start, splash finishes, app sits in tray 60 s", "ws, private, cpu_s over 60 s"],
        ["S1", "Idle in tray 10 min (no files)", "cpu_s must trend to ~0; ws/private drift"],
        ["S2", "Open a 300-page PDF from Explorer, page through 50 pages, Ctrl+wheel to 400%", "peak ws, peak private"],
        ["S3", "Close reader, wait 10 s", "delta vs. S1 (leak indicator)"],
        ["S4", "Repeat S2+S3 twenty times (script with pywinauto or manual)", "private must not climb per cycle"],
        ["S5", "One NLP query, then idle 10 min", "private/VRAM before and after idle TTL"],
        ["S6", "Add 500 mixed files, then Clear", "peak and post-clear private"],
        ["S7", "Open Cross-Reference on 2 PDFs, close", "same as S3"],
    ], [W * 0.07, W * 0.55, W * 0.38]))
    s.append(Spacer(1, 6))
    s.append(P("Python-side instrumentation (behind env var <i>MNIME_PROFILE=1</i>, zero cost otherwise):", S_H2))
    s += bullets([
        "<i>tracemalloc</i> snapshot diff on reader open vs. close, top 25 allocation sites to the log.",
        "Log <i>pymupdf.TOOLS.store_size</i> and <i>store_maxsize</i> on reader open/close (MuPDF keeps a "
        "global resource store independent of Python objects).",
        "A debug hotkey (Ctrl+Shift+F12) that logs every active QTimer: "
        "<i>[t for w in QApplication.allWidgets() for t in w.findChildren(QTimer) if t.isActive()]</i> "
        "with interval and owner class.",
    ])
    s.append(P("Automated guard test (add to <i>tests/test_idle_timers.py</i>):", S_H2))
    s.append(code("""
def test_no_active_timers_when_hidden(qtbot):
    win = MainWindow(); qtbot.addWidget(win)
    win.show(); qtbot.wait(200); win.hide(); qtbot.wait(200)
    active = [(type(t.parent()).__name__, t.interval())
              for w in QApplication.allWidgets() for t in w.findChildren(QTimer)
              if t.isActive()]
    assert active == [], f"Timers still running while hidden: {active}"
"""))
    s.append(PageBreak())

    # ---------------- 3. Findings ----------------
    s.append(P("3. Findings, Ranked by Impact", S_H1))
    s.append(P("Line numbers are from the audited tree. Re-verify before editing.", S_SMALL))

    s.append(P("3.1 Idle CPU and allocation churn (root cause of the 817 CPU-seconds)", S_H2))
    s.append(finding(
        "F1", "CRITICAL", "Splash screen is never destroyed; its 60 Hz timer runs for the app lifetime",
        "MNIME.py L130-169 (timers), L391-405 (fade + on_fade_finished)",
        "on_fade_finished() calls splash.close(), which only hides the widget. anim_timer (16 ms) keeps "
        "calling _update_animation() over 300 Particle objects forever, and the closure keeps <i>splash</i> "
        "alive, so its full-screen translucent backing store (w x h x 4 bytes: ~8 MB at 1080p, ~33 MB at 4K) "
        "may also be retained. Every tick also passes through the app-wide event filter (F8).",
        "In on_fade_finished: stop anim_timer and phase_timer, set splash.particles = [], call "
        "splash.deleteLater(), and drop the Python reference. Also set WA_DeleteOnClose on the splash. "
        "Additionally stop the timer early once all particles are inactive and logo_scale reached 1.0.",
        "Largest single idle-CPU win; up to ~8-33 MB backing store freed.",
        "Very low. Splash is purely cosmetic after fade.",
        code("""
def on_fade_finished():
    splash.anim_timer.stop()
    splash.phase_timer.stop()
    splash.particles = []
    splash.close()
    splash.deleteLater()
    app.main_window.hide()
""")))
    s.append(finding(
        "F2", "CRITICAL", "Carousel penteract logo re-renders a fresh QPixmap at 30 fps while hidden in tray",
        "ui/carousel_view.py L24-52; core/app_icon.py L120-332 (_draw_logo_pixmap)",
        "AnimatedLogoWidget starts a 33 ms timer in __init__ and never checks visibility. Each tick builds "
        "a new 240 px ARGB QPixmap: 32 vertices through 5 rotations and 3 projections in pure Python, 160 "
        "drawLine calls, 33 drawPixmap blits, plus SVG cache lookups. ~108,000 pixmaps per hour while "
        "the window sits in the tray. If the logo sits inside <i>center_container</i>, the "
        "QGraphicsDropShadowEffect at carousel_view.py L258-262 also re-blurs the whole container every "
        "frame (verify the parent chain).",
        "(a) Start the timer in showEvent and stop it in hideEvent; also stop when "
        "<i>self.window().isMinimized()</i> or the carousel has items and the logo is hidden. "
        "(b) Paint directly in paintEvent with a QPainter on the widget instead of allocating a QPixmap "
        "per frame. (c) Hoist the vertex/edge tables to module constants (computed once, not per frame). "
        "(d) Optional: move the drop shadow to a static pre-rendered frame image.",
        "Second-largest idle-CPU win; eliminates continuous pixmap churn and heap fragmentation.",
        "Low. Visual output identical when visible."))
    s.append(finding(
        "F3", "HIGH", "Tabs bar re-applies stylesheets every second",
        "ui/tabs_bar.py L170-200+ (_update_reload_button_status)",
        "A 1 s QTimer polls NLPEngine and calls setStyleSheet() on the NLP checkbox every tick even when "
        "nothing changed. setStyleSheet triggers a full style re-polish and allocates new rule objects.",
        "Track the last state tuple (is_loading, is_loaded) and return early if unchanged. Better: give "
        "NLPEngine a small QObject notifier that emits <i>state_changed</i> (queued from the load thread) "
        "and delete the polling timer. Use one static stylesheet with a dynamic property selector "
        "(QCheckBox[nlpState=\"loading\"]) and only call style().unpolish/polish on change.",
        "Removes a permanent 1 Hz re-polish; small CPU, less allocator churn.",
        "Low."))
    s.append(finding(
        "F8", "MEDIUM", "Application-wide Python event filter",
        "ui/main_window.py L124-125, eventFilter at L200",
        "QCoreApplication.instance().installEventFilter(self) routes every event of every object "
        "(timers, paints, reader mouse moves) through a Python call. Multiplies the cost of F1-F3.",
        "Install the filter only on the main window, its container frame, and the carousel; or "
        "early-return on <i>event.type()</i> not in a small frozenset at the very top of eventFilter.",
        "Lower per-event overhead everywhere, including the reader.",
        "Medium: edge-resize cursor logic depends on it; verify resize cursors on all four edges."))
    s.append(finding(
        "F11", "LOW", "Unbounded icon pixmap cache fed by per-frame sizes",
        "ui/icons.py L251-284; core/app_icon.py L268-273",
        "_PIXMAP_CACHE is keyed by (name, size, color). The orbiting green file icon requests a size that "
        "changes every frame with depth_scale, so the cache accumulates many near-duplicate pixmaps.",
        "Quantize the requested size to steps of 2 px, and cap the cache with an LRU (OrderedDict, 256 "
        "entries).",
        "Bounded memory; a few MB in long sessions.",
        "Very low."))

    s.append(P("3.2 Document viewer memory (the user's primary focus)", S_H2))
    s.append(finding(
        "F6", "HIGH", "Reader lifecycle, render resolution, and bitmap budget",
        "ui/reader_dialog.py L37-100 (view), L102-150 (dialog), L398-452 (render/zoom), L601-607 (close)",
        "<b>(1) Lifecycle:</b> created with parent=None and no WA_DeleteOnClose; teardown relies on Python "
        "GC after <i>_active_reader</i> is cleared, while bound-method signal connections can keep the C++ "
        "object alive. closeEvent closes the doc but leaves the scene pixmap, TOC items, and Page reference. "
        "<b>(2) Over-render:</b> get_render_scale() multiplies the view scale by 96/72 (=1.333), so bitmaps "
        "carry ~78% more pixels than needed at 100% DPI, while devicePixelRatio is ignored (blurry at "
        "150-200%). <b>(3) No pixel cap:</b> Ctrl+wheel to high zoom on a large-format page renders the "
        "entire page, e.g. 10x on A3 is ~11,700 x 16,500 px, ~770 MB ARGB. <b>(4) No debounce:</b> every "
        "wheel notch can trigger a full re-render. <b>(5) Images:</b> QPixmap(path) decodes full resolution "
        "(a 48 MP photo is ~192 MB). <b>(6) Translucency:</b> frameless + WA_TranslucentBackground costs a "
        "full ARGB backing store (1200x900 at 150% scale is ~9.7 MB) and DWM alpha composition. "
        "<b>(7) Watermark:</b> WatermarkFrame paints a 260-character 80 pt string repeatedly on every repaint.",
        "(1) setAttribute(WA_DeleteOnClose); in closeEvent: scene.clear(), view.current_page = None, "
        "toc_tree.clear(), doc.close(), then <i>pymupdf.TOOLS.store_shrink(100)</i>. "
        "(2) render_scale = view.transform().m11() * view.devicePixelRatioF(); call "
        "pixmap.setDevicePixelRatio(dpr) and divide item scale accordingly. "
        "(3) Cap a single bitmap at 16 MP (~64 MB). Above the cap, render only the visible region with "
        "<i>page.get_pixmap(matrix=m, clip=visible_rect)</i> and position the item at the clip origin "
        "(tile rendering). (4) Debounce zoom re-render with a 120 ms single-shot QTimer; show the scaled "
        "stale pixmap meanwhile. (5) Use QImageReader with setScaledSize(viewport x dpr) for images; re-read "
        "at higher resolution only on zoom. (6) Make the window opaque and use Windows 11 native rounded "
        "corners (DwmSetWindowAttribute, DWMWA_WINDOW_CORNER_PREFERENCE = 33, DWMWCP_ROUND = 2), or keep "
        "translucency but only for the main window. (7) Render the watermark once into a small tile and "
        "use drawTiledPixmap.",
        "Typical reader session: 40-70% less peak memory; full return to baseline after close; no "
        "pathological zoom spikes.",
        "Medium: tile rendering changes scroll math; cover with a manual test at 25%, 100%, 400%, 1000%."))
    s.append(code("""
# Shared page renderer (use from both ReaderDialog and DocumentViewer)
MAX_PIXELS = 16_000_000

def render_page(page, view, dpr):
    scale = view.transform().m11() * dpr
    w, h = page.rect.width * scale, page.rect.height * scale
    clip = None
    if w * h > MAX_PIXELS:                       # render only what is visible
        vis = view.mapToScene(view.viewport().rect()).boundingRect()
        clip = pymupdf.Rect(vis.left(), vis.top(), vis.right(), vis.bottom()) & page.rect
    pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), clip=clip, alpha=False)
    img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
    qpm = QPixmap.fromImage(img)                 # fromImage already copies; no img.copy()
    del img, pix                                 # release MuPDF buffer immediately
    qpm.setDevicePixelRatio(dpr)
    return qpm, scale, clip
"""))
    s.append(Spacer(1, 8))
    s.append(finding(
        "F12", "LOW", "Cross-reference viewer duplicates the render path with a fixed 2.0x scale",
        "ui/document_viewer.py L38, L323-335, L415-422",
        "Renders at a fixed zoom_factor of 2.0 regardless of DPI or view size, adds an extra img.copy() "
        "(peak ~10 bytes/pixel), and has no WA_DeleteOnClose. Text-selection rubber band maps scene "
        "coordinates by dividing by zoom_factor, which must be kept consistent if scaling changes.",
        "Reuse the shared renderer above; keep scene units in PDF points (as ReaderPageView already does) "
        "so _extract_text no longer divides by zoom_factor. Remove img.copy(). Add WA_DeleteOnClose and "
        "store_shrink on close.",
        "One render policy to maintain; lower peak memory in cross-reference sessions.",
        "Low: re-test rubber-band text extraction on rotated and cropped pages."))
    s.append(finding(
        "F7", "MEDIUM", "Thumbnails stored twice and every card is a live widget",
        "core/file_item.py L44-45, L69-151; ui/file_card.py L199-219; ui/carousel_view.py L57-117",
        "Each FileItem keeps PNG bytes rendered at 2x card size and a decoded QPixmap. With the advertised "
        "5,000-file limit that approaches hundreds of MB. ClippedCardsArea instantiates and shows a FileCard "
        "QFrame for every item, even far off-screen.",
        "Drop <i>thumbnail_bytes</i> once the QPixmap exists (or never keep it: decode straight from the "
        "MuPDF pixmap via QImage). Add a disk thumbnail cache in %LOCALAPPDATA%\\MNIME\\thumbs keyed by "
        "(path, size, mtime) as JPEG. Virtualize the carousel: only create FileCard widgets for visible "
        "indices plus 10 on either side, recycling widgets as the offset changes; keep decoded pixmaps "
        "in an LRU of ~100.",
        "Memory scales with the viewport instead of the queue length.",
        "Medium: drag-reorder logic reads cards_area._cards; adapt it to index math."))

    s.append(P("3.3 Model and dependency weight", S_H2))
    s.append(finding(
        "F4", "HIGH", "LLM stays resident forever after first use",
        "core/nlp_engine.py L103-185; callers ui/main_window.py L903, L1334; core/pdf_engine.py L293, L546",
        "Once loaded, the llama.cpp context stays until the NLP toggle is turned off or the app exits: "
        "~1.0 GB file-backed weights, ~110-120 MB f16 KV cache at n_ctx 4096 for a Qwen2.5-1.5B class model, "
        "and a GPU driver context (often 150-300 MB private) when layers are offloaded.",
        "Add an idle TTL: a QTimer (or threading.Timer) reset on every inference; unload after "
        "<i>nlp_idle_unload_minutes</i> (QSettings, default 5). Also unload when the main window goes to "
        "tray and no NLP/reader window is open (setting, default on). Keep use_mmap on (default) so weights "
        "stay reclaimable. Optionally set type_k/type_v to q8_0 to halve KV cache if the installed "
        "llama-cpp-python build supports it.",
        "Hundreds of MB to over 1 GB returned after idle; VRAM freed for other apps.",
        "Low: first query after idle pays reload (~1-3 s). Show the existing amber loading state."))
    s.append(finding(
        "F5", "HIGH", "torch is pulled in just to embed text",
        "core/search_engine.py L140-160, L183-330, L348-372; MNIME.spec L65-72",
        "HuggingFaceEmbeddings loads sentence_transformers, which loads torch (300-600 MB RSS once "
        "imported, plus GBs of install size). langchain, langchain_community, pydantic, SQLAlchemy, aiohttp "
        "and pandas (used once at L252 for a DataFrame) come along.",
        "Replace with llama.cpp embeddings: convert bge-small-en-v1.5 to GGUF (Q8_0 ~35 MB) and load with "
        "<i>Llama(model_path, embedding=True, n_ctx=512)</i>; llama_cpp is already a dependency. Alternative: "
        "onnxruntime + tokenizers. Replace the langchain FAISS wrapper with raw faiss.IndexFlatIP plus a "
        "JSON/SQLite docstore. Bump the store path to <i>global_vector_store_v2</i> and rebuild once (vectors "
        "differ numerically). Apply the same idle TTL as F4.",
        "Removes the single largest potential RAM spike and shrinks dist/ by GBs; faster first index.",
        "Medium: verify retrieval parity on a fixed 20-query set (recall@5 within 2 points)."))
    s.append(finding(
        "F9", "MEDIUM", "Eager construction of rarely used heavy widgets",
        "ui/main_window.py L552 (OutputView), L558 (NLPView), L571 (MergeParticleOverlay)",
        "All are built at startup even though most sessions start minimized to tray. The particle overlay "
        "is a full-window translucent widget.",
        "Construct lazily on first use behind small accessor properties; destroy the particle overlay "
        "after its flash completes.",
        "Lower startup time and baseline private bytes.",
        "Low."))
    s.append(finding(
        "F10", "MEDIUM", "Build ships unused weight",
        "MNIME.spec L65-86",
        "collect_all() on sentence_transformers drags torch; Qt6Pdf.dll is resident in the idle process "
        "(likely via the qpdf image-format plugin) although MNIME renders with PyMuPDF.",
        "After F5, drop sentence_transformers/langchain from collect_all and add torch, torchvision, "
        "torchaudio, transformers, pandas to excludes. Filter the qpdf plugin and Qt6Pdf from a.binaries. "
        "Set optimize=2 to strip docstrings and asserts from bundled bytecode.",
        "Smaller install, fewer mapped DLLs, faster cold start.",
        "Low: run the full test suite against the frozen build."))

    s.append(P("3.4 Idle trim: the Chrome trick", S_H2))
    s.append(finding(
        "F13", "HIGH", "Nothing is released or deprioritized when MNIME goes to the tray",
        "New module core/idle_trim.py; hooks in ui/main_window.py _animate_minimize_to_tray, _show_from_tray",
        "MNIME spends most of its life hidden in the tray at full priority holding everything it ever "
        "touched.",
        "When the main window is hidden and no other top-level window is visible for 30 s: confirm zero "
        "active animation timers, clear QPixmapCache and icon caches (except the tray icon), "
        "pymupdf.TOOLS.store_shrink(100), gc.collect(), CRT _heapmin(), then "
        "SetProcessWorkingSetSizeEx(h, -1, -1, 0). Put the process into Windows 11 Efficiency mode "
        "(EcoQoS + IDLE_PRIORITY_CLASS, the same mechanism Edge and Chrome use) and set low memory "
        "priority. Revert all of this the moment any window is shown or an IPC open arrives.",
        "Task Manager Memory column drops from ~225 MB to an expected 10-25 MB; idle power and thermal "
        "impact near zero.",
        "Low. Trimming is cosmetic for commit charge but real under memory pressure; restore may soft-fault "
        "pages back (tens to a few hundred ms). The 30 s delay avoids trimming during quick toggles."))
    s.append(code("""
# core/idle_trim.py
import ctypes, gc, sys
from ctypes import wintypes

class _PPTS(ctypes.Structure):
    _fields_ = [("Version", wintypes.ULONG), ("ControlMask", wintypes.ULONG),
                ("StateMask", wintypes.ULONG)]

ProcessMemoryPriority, ProcessPowerThrottling = 0, 4
THROTTLE_EXECUTION_SPEED = 0x1
IDLE_PRIORITY_CLASS, NORMAL_PRIORITY_CLASS = 0x40, 0x20
MEMORY_PRIORITY_LOW, MEMORY_PRIORITY_NORMAL = 2, 5

def _k32():
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.SetProcessWorkingSetSizeEx.argtypes = [wintypes.HANDLE, ctypes.c_size_t,
                                             ctypes.c_size_t, wintypes.DWORD]
    k.SetProcessInformation.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                        ctypes.c_void_p, wintypes.DWORD]
    k.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    return k

def trim_now():
    gc.collect()
    try:
        import pymupdf; pymupdf.TOOLS.store_shrink(100)
    except Exception: pass
    try:
        from PyQt6.QtGui import QPixmapCache; QPixmapCache.clear()
    except Exception: pass
    if sys.platform != "win32": return
    try: ctypes.CDLL("ucrtbase")._heapmin()
    except Exception: pass
    try:
        k = _k32()
        k.SetProcessWorkingSetSizeEx(k.GetCurrentProcess(), ctypes.c_size_t(-1).value,
                                     ctypes.c_size_t(-1).value, 0)
    except Exception: pass

def set_efficiency_mode(on: bool):
    if sys.platform != "win32": return
    try:
        k = _k32(); h = k.GetCurrentProcess()
        st = _PPTS(1, THROTTLE_EXECUTION_SPEED, THROTTLE_EXECUTION_SPEED if on else 0)
        k.SetProcessInformation(h, ProcessPowerThrottling, ctypes.byref(st), ctypes.sizeof(st))
        mp = wintypes.ULONG(MEMORY_PRIORITY_LOW if on else MEMORY_PRIORITY_NORMAL)
        k.SetProcessInformation(h, ProcessMemoryPriority, ctypes.byref(mp), ctypes.sizeof(mp))
        k.SetPriorityClass(h, IDLE_PRIORITY_CLASS if on else NORMAL_PRIORITY_CLASS)
    except Exception: pass
"""))
    s.append(callout("While in Efficiency mode, background QThreads (indexing, conversions) also run at idle "
                     "priority. Call set_efficiency_mode(False) before starting any worker from the tray "
                     "(for example an IPC-triggered open), and re-enter it when the worker finishes and the "
                     "window is still hidden.", AMBER, "CAUTION"))
    s.append(PageBreak())

    # ---------------- Wild tier ----------------
    s.append(P("3.5 Wild Tier: Architectural Moves", S_H2))
    s.append(P("These change the process model. Implement each behind a QSettings feature flag "
               "(default off) after Phases 1-4 land, so the measured gains of the safe phases are not "
               "confounded."))
    s.append(table([
        ["ID", "Idea", "How", "Payoff", "Cost / risk"],
        ["W1", "<b>Native tray stub</b> (the real Chrome-class number)",
         "~300 LOC C (MSVC or zig cc) or Rust (<i>windows</i> crate) exe <i>mnime_tray.exe</i> owns the tray icon, "
         "the named pipe (same IPC_PIPE_NAME and payload format), file association, and Run-on-Startup. "
         "It spawns <i>MNIME.exe</i> on tray click or file open; MNIME.exe exits fully after N minutes hidden "
         "and persists its queue to %LOCALAPPDATA%\\MNIME\\session.json.",
         "Resident idle footprint ~1-3 MB working set. Python heap fragmentation becomes irrelevant because "
         "the process ends.",
         "Cold start of the Python app (~1-2 s) on first open after idle. Mitigate with a native layered "
         "splash window in the stub and a 10-minute warm period."],
        ["W2", "<b>Reader as its own process</b> (process-per-document, like browser tabs)",
         "<i>MNIME.exe --reader file.pdf</i> imports only QtWidgets + pymupdf + reader_dialog; no main window, "
         "carousel, NLP, or icons beyond the title bar. Cross-reference/NLP requests go back over the "
         "existing local socket.",
         "Closing a document returns 100% of its memory to the OS. Explorer double-click opens fast "
         "with a lean process (~45-60 MB expected).",
         "Two entry paths to maintain; window activation across processes needs AllowSetForegroundWindow."],
        ["W3", "<b>Out-of-process NLP worker</b>",
         "Spawn <i>mnime_nlp</i> (same exe, <i>--nlp-worker</i>) holding llama.cpp + embeddings; stream tokens "
         "over a pipe; kill on idle TTL.",
         "Guaranteed full RAM and VRAM release (GPU contexts do not always fully release in-process). "
         "A model crash cannot take down the UI.",
         "Serialization of context docs; startup latency hidden behind the existing loading state."],
        ["W4", "<b>Pre-baked visuals</b>",
         "Render the penteract loop once at build time to an animated WebP (240 px, 120 frames) and play it "
         "with QMovie, which decodes one frame at a time. Same for the splash particle field if desired.",
         "Animation cost drops from Python math per frame to a codec frame decode; identical look.",
         "Lose procedural randomness; keep the procedural path behind a setting for the STATS/demo mode."],
        ["W5", "<b>Nuitka build</b> instead of PyInstaller",
         "Compile with <i>nuitka --standalone --enable-plugin=pyqt6</i>; benchmark startup and private bytes "
         "against the PyInstaller build.",
         "Faster cold start (helps W1/W2), modest RAM reduction.",
         "Experimental; plugin compatibility for llama_cpp and pymupdf must be verified."],
        ["W6", "<b>Thumbnail atlas</b>",
         "One memory-mapped file of JPEG thumbnails with an offset index; decode only visible cards.",
         "5,000-file queues cost almost nothing until scrolled into view.",
         "Cache invalidation on file change (mtime/size key)."],
    ], [W * 0.05, W * 0.15, W * 0.36, W * 0.22, W * 0.22]))
    s.append(PageBreak())

    # ---------------- 4. Roadmap ----------------
    s.append(P("4. Phased Roadmap and Acceptance Criteria", S_H1))
    s.append(table([
        ["Phase", "Scope", "Acceptance criteria (measured with Section 2)"],
        ["0  Measure", "measure_idle.ps1, MNIME_PROFILE instrumentation, timer-dump hotkey, test_idle_timers.py",
         "Baseline JSON for S0-S7 committed under docs/perf/."],
        ["1  Stop the bleeding", "F1, F2, F3, F8, F11",
         "S1: cpu_s at most 0.6 over 10 min (under 0.1% of one core). test_idle_timers passes. "
         "All animations still visible when windows are shown."],
        ["2  Idle trim", "F13, F4 (idle TTL)",
         "S0/S1: working set under 25 MB 60 s after reaching the tray. Restore from tray feels instant "
         "(under 300 ms to first paint). S5: model unloaded within TTL + 10 s."],
        ["3  Viewer diet", "F6, F12, F7",
         "S2: peak private delta under 120 MB for the 300-page PDF including 400% zoom. "
         "S3: within 5 MB of pre-open baseline after 10 s. S4: no monotonic growth over 20 cycles "
         "(slope under 0.5 MB per cycle). S6: post-clear private within 10 MB of baseline."],
        ["4  Dependency diet", "F5, F9, F10",
         "torch absent from dist/ and from loaded modules after an NLP query. Retrieval recall@5 within "
         "2 points of current on the 20-query set. dist/ size reported before/after."],
        ["5  Wild (flagged)", "W1, then W2, W3; W4-W6 optional",
         "W1: resident footprint under 3 MB working set when idle. W2: closing a reader process returns "
         "its full private bytes. Feature flags default off until validated."],
    ], [W * 0.17, W * 0.30, W * 0.53]))

    s.append(P("5. Expected Outcome Summary", S_H1))
    s.append(table([
        ["Metric", "Today", "After Phase 2", "After Phase 4", "With W1"],
        ["Idle CPU (one core)", "~5.4%", "~0%", "~0%", "0% (Python exited)"],
        ["Idle working set", "225 MB", "10-25 MB", "10-25 MB", "1-3 MB"],
        ["Idle private bytes", "200 MB", "~90-140 MB (paged out)", "~70-110 MB", "~1-2 MB"],
        ["Reader peak (300 pp, 400%)", "unbounded at high zoom", "unchanged", "under +120 MB, capped", "isolated (W2)"],
        ["NLP after idle", "resident forever", "unloaded after TTL", "unloaded, no torch", "worker exited"],
    ], [W * 0.24, W * 0.17, W * 0.21, W * 0.20, W * 0.18]))
    s.append(Spacer(1, 6))
    s.append(P("Post-phase figures are engineering estimates to be confirmed with the Section 2 protocol, "
               "not measurements. Report actual numbers back against this table.", S_SMALL))

    s.append(P("6. Files the Implementing Model Will Touch", S_H1))
    s.append(table([
        ["File", "Phases", "Change summary"],
        ["MNIME.py", "1", "Splash teardown (F1)"],
        ["ui/carousel_view.py", "1, 3", "Visibility-gated logo painting (F2); card virtualization (F7)"],
        ["core/app_icon.py", "1", "Module-level geometry tables; paint-into-painter API (F2)"],
        ["ui/tabs_bar.py, core/nlp_engine.py", "1, 2", "State-change signal instead of polling (F3); idle TTL (F4)"],
        ["ui/main_window.py", "1, 2, 4", "Narrow event filter (F8); tray idle hooks (F13); lazy widgets (F9)"],
        ["ui/icons.py", "1", "Bounded LRU cache (F11)"],
        ["core/idle_trim.py (new)", "2", "Working-set trim, efficiency mode (F13)"],
        ["ui/reader_dialog.py, ui/document_viewer.py", "3", "Shared renderer, DPR, pixel cap, debounce, lifecycle (F6, F12)"],
        ["core/file_item.py, ui/file_card.py", "3", "Single thumbnail representation, disk cache (F7)"],
        ["core/search_engine.py, ui/nerds.py", "4", "llama.cpp/ONNX embeddings, raw faiss docstore (F5)"],
        ["MNIME.spec, requirements.txt", "4", "Excludes, optimize=2, drop torch stack (F10)"],
        ["scripts/measure_idle.ps1, tests/test_idle_timers.py (new)", "0", "Measurement and guard test"],
    ], [W * 0.40, W * 0.12, W * 0.48]))
    return s


def main():
    doc = PlanDoc(OUT_PATH)
    doc.build(build_story())
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
