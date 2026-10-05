"""
MNIME Desktop - MULTIMODAL NEURAL INTERFACE MACHINE EXTENSION
Next-generation private, high-performance offline document suite.
"""

import os
import sys

# Disable console progress bars globally to avoid worker thread deadlocks with Qt
os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# Ensure the root project directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix for "Could not find the Qt platform plugin 'windows'" and broken image formats
if not getattr(sys, "frozen", False):
    venv_base = os.path.dirname(os.path.dirname(sys.executable))
    plugin_base = os.path.join(venv_base, "Lib", "site-packages", "PyQt6", "Qt6", "plugins")
    if os.path.isdir(plugin_base):
        os.environ["QT_PLUGIN_PATH"] = plugin_base
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(plugin_base, "platforms")

# Logging must be configured before anything else can fail
from core.logging_setup import setup_logging, get_logger
setup_logging()
log = get_logger("app")


def _log_uncaught(exc_type, exc_value, exc_tb):
    log.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = _log_uncaught

# Configure Windows AppUserModelID early so taskbar/quickbar pinning groups correctly
from core.app_icon import setup_app_user_model_id, get_app_icon
setup_app_user_model_id()

# Ensure PDF files show document page previews rather than application logo
from core.windows_integration import ensure_pdf_page_preview
ensure_pdf_page_preview()

import math
import random

from PyQt6.QtWidgets import QApplication, QWidget, QGraphicsOpacityEffect
from PyQt6.QtGui import (QFont, QPainter, QLinearGradient, QColor,
                         QFontMetrics, QPen, QBrush, QPixmap, QPolygonF)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QPointF



class Particle:
    def __init__(self, cx, cy):
        # Spawn around the MNIME text area
        self.x = cx + random.uniform(-50, 50)
        self.y = cy + random.uniform(-50, 50)
        
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(10, 40)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        
        self.trail = []
        self.max_trail = random.randint(10, 25)
        self.size = random.uniform(0.5, 1.5)
        self.cx = cx
        self.cy = cy - 30 # slightly above the text for the merge point
        self.phase = 1
        self.active = True

    def update(self):
        if not self.active:
            return
            
        self.trail.append((self.x, self.y))
        if len(self.trail) > self.max_trail:
            self.trail.pop(0)
            
        if self.phase == 1:
            # Random erratic movement (shoot around)
            self.vx += random.uniform(-8, 8)
            self.vy += random.uniform(-8, 8)
            # Gentle drag
            self.vx *= 0.95
            self.vy *= 0.95
        elif self.phase == 2:
            # Merge into one large file at center
            dx = self.cx - self.x
            dy = self.cy - self.y
            dist = math.hypot(dx, dy)
            if dist < 15:
                self.active = False
                return
            
            # Strong attraction to center
            if dist > 0:
                self.vx += (dx / dist) * 6.0
                self.vy += (dy / dist) * 6.0
            self.vx *= 0.90
            self.vy *= 0.90
            
        self.x += self.vx
        self.y += self.vy

from ui.main_window import MainWindow

class MetalSplashScreen(QWidget):
    """A completely borderless, transparent widget that displays the MNIME title in dark metal with a rotating 5D Penteract."""
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        screen = QApplication.primaryScreen().geometry()
        w, h = screen.width(), screen.height()
        self.setFixedSize(w, h)
        
        self.rotation = 0.0
        self.logo_scale = 0.0
        
        # Initialize massive full-screen Particle System
        self.particles = [Particle(w/2, h/2) for _ in range(300)]
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._update_animation)
        
        # Create tiny glowing file icon pixmap cache for particles
        self.file_pixmap = QPixmap(24, 24)
        self.file_pixmap.fill(Qt.GlobalColor.transparent)
        p = QPainter(self.file_pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        poly = QPolygonF([
            QPointF(4, 2), QPointF(14, 2), QPointF(20, 8),
            QPointF(20, 22), QPointF(4, 22)
        ])
        
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(140, 230, 255, 80))
        p.drawEllipse(0, 0, 24, 24)
        
        p.setPen(QPen(QColor(0, 210, 255, 255), 1.5))
        p.setBrush(QColor(255, 255, 255, 255))
        p.drawPolygon(poly)
        
        p.setPen(QPen(QColor(0, 210, 255, 255), 1.5))
        p.drawLine(QPointF(14, 2), QPointF(14, 8))
        p.drawLine(QPointF(14, 8), QPointF(20, 8))
        
        p.end()

        self.anim_timer.start(16)
        
        self.phase = 1
        self.central_file_scale = 0.0
        
        # Switch to merge phase after 1.5s
        self.phase_timer = QTimer(self)
        self.phase_timer.setSingleShot(True)
        self.phase_timer.timeout.connect(self._trigger_merge)
        self.phase_timer.start(1500)
        
    def _trigger_merge(self):
        self.phase = 2
        for p in self.particles:
            p.phase = 2

    def _update_animation(self):
        self.rotation += 0.03
        if self.logo_scale < 1.0:
            self.logo_scale = min(1.0, self.logo_scale + 0.03)
            
        arrived = 0
        for p in self.particles:
            p.update()
            if not p.active:
                arrived += 1
                
        if self.phase == 2:
            self.central_file_scale = min(1.0, arrived / len(self.particles))
            if arrived == len(self.particles) and self.logo_scale >= 1.0:
                self.anim_timer.stop()
            
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        cx = self.width() // 2
        cy = self.height() // 2
        
        # 0. Draw Particle System
        for p in self.particles:
            if not p.active:
                continue
                
            if len(p.trail) > 1:
                trail_pen = QPen(QColor(140, 230, 255, 60))
                trail_pen.setWidthF(p.size)
                trail_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(trail_pen)
                points = [QPointF(x, y) for x, y in p.trail]
                painter.drawPolyline(QPolygonF(points))
            
            icon_size = max(14.0, p.size * 10.0)
            painter.drawPixmap(
                int(p.x - icon_size / 2),
                int(p.y - icon_size / 2),
                int(icon_size),
                int(icon_size),
                self.file_pixmap
            )
        
        # 1. Draw 5D Penteract in Background (scaled elegantly behind the title)
        if self.logo_scale > 0:
            from core.app_icon import get_logo_pixmap
            logo_size = int(420 * self.logo_scale)
            pixmap = get_logo_pixmap(logo_size, self.rotation)
            
            painter.setOpacity(min(1.0, self.logo_scale))
            painter.drawPixmap(
                int(cx - logo_size / 2),
                int(cy - logo_size / 2 - 30),
                pixmap
            )
            painter.setOpacity(1.0)
        
        # 2. Sleek, modern, and official corporate font
        font = QFont("Segoe UI Black", 85, QFont.Weight.Black)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 5.0)
        painter.setFont(font)
        
        fm = QFontMetrics(font)
        text_rect = fm.boundingRect("MNIME")
        
        x = cx - text_rect.width() // 2
        y = cy + text_rect.height() // 2 - fm.descent()
        
        # 3. Intense neon blue ambient glow
        glow_color = QColor(0, 210, 255, 25)
        painter.setPen(glow_color)
        for offset in [3, 6]:
            painter.drawText(x - offset, y - offset, "MNIME")
            painter.drawText(x + offset, y - offset, "MNIME")
            painter.drawText(x - offset, y + offset, "MNIME")
            painter.drawText(x + offset, y + offset, "MNIME")
        
        # 4. Deep drop shadow for desktop separation
        painter.setPen(QColor(0, 0, 0, 200))
        painter.drawText(x + 5, y + 5, "MNIME")
        
        # 5. Dark Metallic Gradient Core
        gradient = QLinearGradient(x, y - text_rect.height(), x, y)
        gradient.setColorAt(0.0, QColor("#ffffff")) # Bright top edge highlight
        gradient.setColorAt(0.2, QColor("#e1e4e8")) # Light silver
        gradient.setColorAt(0.5, QColor("#8b949e")) # Mid titanium
        gradient.setColorAt(0.6, QColor("#161b22")) # Sharp dark metal cut
        gradient.setColorAt(1.0, QColor("#484f58")) # Bottom rim reflection
        
        pen = QPen()
        pen.setBrush(QBrush(gradient))
        painter.setPen(pen)
        painter.drawText(x, y, "MNIME")
        
        painter.end()

from PyQt6.QtNetwork import QLocalSocket, QLocalServer
from core.ipc import IPC_PIPE_NAME, MAX_IPC_BYTES, build_open_request, parse_open_request

def send_to_existing_instance(file_paths: list) -> bool:
    """Attempt to connect to an already running MNIME instance and send file paths."""
    socket = QLocalSocket()
    socket.connectToServer(IPC_PIPE_NAME)
    if socket.waitForConnected(500):
        socket.write(build_open_request(file_paths))
        socket.flush()
        socket.waitForBytesWritten(1000)
        # Wait up to 1 second for the running instance to acknowledge receipt
        socket.waitForReadyRead(1000)
        socket.disconnectFromServer()
        return True
    return False

def main():
    # Enable high-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("MNIME")
    app.setOrganizationName("MNIME")

    # Extract target files from command line arguments (e.g. Windows file association / Open With)
    import urllib.parse
    raw_args = sys.argv[1:]
    target_files = []
    for arg in raw_args:
        if not arg or arg.startswith("-"):
            continue
        cleaned = arg.strip(' \t\r\n"\'')
        if cleaned.startswith("file:///"):
            cleaned = urllib.parse.unquote(cleaned[8:])
        elif cleaned.startswith("file://"):
            cleaned = urllib.parse.unquote(cleaned[7:])
        cleaned = os.path.normpath(cleaned)
        if os.path.isfile(cleaned):
            target_files.append(os.path.abspath(cleaned))

    # Check for an existing running instance of MNIME
    if send_to_existing_instance(target_files):
        # Successfully forwarded document to running instance, exit second process immediately
        sys.exit(0)

    # Set application icon for taskbar, quickbar, window titlebar, and system dialogs
    app_icon = get_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    # Set modern clean font
    app_font = QFont("Segoe UI", 10)
    app.setFont(app_font)

    # Initialize Main Window
    app.main_window = MainWindow()

    # Start QLocalServer for single-instance IPC
    ipc_server = QLocalServer()
    QLocalServer.removeServer(IPC_PIPE_NAME)
    if ipc_server.listen(IPC_PIPE_NAME):
        def on_new_connection():
            client_socket = ipc_server.nextPendingConnection()
            if not client_socket:
                return

            buf = bytearray()

            def process_incoming():
                buf.extend(client_socket.readAll().data())
                if len(buf) > MAX_IPC_BYTES:
                    log.warning("IPC payload exceeded %d bytes; dropping connection", MAX_IPC_BYTES)
                    buf.clear()
                    client_socket.abort()
                    return
                try:
                    files = parse_open_request(bytes(buf))
                except ValueError:
                    return  # Possibly incomplete; wait for more data or for disconnect
                buf.clear()
                client_socket.write(b"ACK\n")
                client_socket.flush()
                app.main_window.handle_external_open(files)

            def on_disconnected():
                if buf:
                    log.warning("Discarded malformed IPC payload (%d bytes)", len(buf))
                    app.main_window.showNormal()
                    app.main_window.activateWindow()
                    app.main_window.raise_()
                client_socket.deleteLater()

            client_socket.readyRead.connect(process_incoming)
            client_socket.disconnected.connect(on_disconnected)
            if client_socket.bytesAvailable() > 0:
                process_incoming()

        ipc_server.newConnection.connect(on_new_connection)
    else:
        log.warning("IPC server could not listen: %s", ipc_server.errorString())
    app.ipc_server = ipc_server

    # Remove temporary job output on any exit path (tray Quit, OS shutdown, ...)
    app.aboutToQuit.connect(app.main_window._cleanup_temp_dirs)

    # If launched with a document (e.g. user double-clicked a PDF):
    if target_files:
        # Go straight into the reader with the document loaded, bypassing splash delay
        app.main_window.hide()
        app.main_window.handle_external_open(target_files)
    else:
        # Standard launch: Show Splash Screen with particle effects and minimize to tray
        splash = MetalSplashScreen()
        splash.show()

        splash._animation = QPropertyAnimation(splash, b"windowOpacity")
        splash._animation.setDuration(1200)  # 1.2 second fade out
        splash._animation.setStartValue(1.0)
        splash._animation.setEndValue(0.0)

        def on_fade_finished():
            splash.anim_timer.stop()
            splash.phase_timer.stop()
            splash.particles = []
            splash.close()
            splash.deleteLater()
            # Always start minimized to the tray after splash
            app.main_window.hide()

        splash._animation.finished.connect(on_fade_finished)
        QTimer.singleShot(3500, splash._animation.start)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
