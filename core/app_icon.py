"""
Application Icon and Windows Taskbar/Quickbar Integration Module.
Handles Windows AppUserModelID registration, multi-resolution ICO generation,
QIcon creation, and Windows shortcut creation for taskbar/quickbar pinning.
"""

import os
import sys
import ctypes
import subprocess
from typing import Optional
from PyQt6.QtGui import QIcon, QPixmap

from core.logging_setup import get_logger

log = get_logger("app_icon")

APP_USER_MODEL_ID = "MNIME.Desktop"


def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, working across dev and PyInstaller onedir/onefile builds."""
    if hasattr(sys, "_MEIPASS"):
        meipass_path = os.path.join(sys._MEIPASS, relative_path)
        if os.path.exists(meipass_path):
            return meipass_path

    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        exe_path = os.path.join(exe_dir, relative_path)
        if os.path.exists(exe_path):
            return exe_path
        internal_path = os.path.join(exe_dir, "_internal", relative_path)
        if os.path.exists(internal_path):
            return internal_path

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dev_path = os.path.join(project_root, relative_path)
    if os.path.exists(dev_path):
        return dev_path

    return os.path.join(os.getcwd(), relative_path)


def get_ico_path() -> str:
    return get_resource_path("MN.ico")


def get_png_path() -> str:
    return get_resource_path("MNIME_reimagined_alpha.png")


def setup_app_user_model_id() -> bool:
    """
    Sets the explicit Application User Model ID on Windows.
    This prevents Windows from grouping the app under python.exe and
    ensures the taskbar / quickbar displays the custom MNIME logo.
    """
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
            return True
        except Exception as e:
            log.warning("Failed to set AppUserModelID: %s", e)
            return False
    return False


def ensure_ico_file() -> Optional[str]:
    """
    Ensures that a multi-resolution Windows ICO file exists.
    If MN.ico does not exist, it converts MNIME_reimagined_alpha.png using Pillow.
    """
    ico_path = get_ico_path()
    if os.path.exists(ico_path):
        return ico_path

    png_path = get_png_path()
    if not os.path.exists(png_path):
        return None

    try:
        from PIL import Image

        img = Image.open(png_path)
        w, h = img.size

        # Center-crop to 1:1 square to maintain the circular emblem's aspect ratio
        crop_dim = min(w, h)
        left = (w - crop_dim) // 2
        top = (h - crop_dim) // 2
        square_crop = img.crop((left, top, left + crop_dim, top + crop_dim))

        # Save standard Windows icon sizes (16, 24, 32, 48, 64, 128, 256)
        icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        square_crop.save(ico_path, format="ICO", sizes=icon_sizes)
        return ico_path
    except Exception as e:
        log.warning("Could not create ICO file: %s", e)
        return None


_CACHED_APP_ICON: Optional[QIcon] = None
_CACHED_LOGO_PIXMAPS: dict = {}


def get_app_icon() -> QIcon:
    """
    Returns the QIcon for the application (cached).
    Uses the pure programmatic vector logo (origami geometric pattern).
    """
    global _CACHED_APP_ICON
    if _CACHED_APP_ICON is not None and not _CACHED_APP_ICON.isNull():
        return _CACHED_APP_ICON

    _CACHED_APP_ICON = get_tray_icon()
    return _CACHED_APP_ICON


def _draw_logo_pixmap(size: int = 64, rotation: float = 0.0, is_tray: bool = False) -> QPixmap:
    """
    Draws the logo and returns a QPixmap.
    """
    from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor
    from PyQt6.QtCore import Qt, QPointF
    import math
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    center = QPointF(size / 2, size / 2)
    
    points_2d = []
    edges = []
    
    if is_tray:
        # Draw a clean 3D cube (8 vertices) for the tray icon to prevent blurriness
        radius = size * 0.48
        points_nd = []
        for i in range(8):
            x = -0.5 if (i & 1) == 0 else 0.5
            y = -0.5 if (i & 2) == 0 else 0.5
            z = -0.5 if (i & 4) == 0 else 0.5
            points_nd.append([x, y, z])
            
        for i in range(8):
            for j in range(i + 1, 8):
                if (i ^ j) in (1, 2, 4):
                    edges.append((i, j))
                    
        rot_xy = rotation * 1.2
        rot_yz = rotation * 0.7
        rot_xz = rotation * 0.9
        
        c_xy, s_xy = math.cos(rot_xy), math.sin(rot_xy)
        c_yz, s_yz = math.cos(rot_yz), math.sin(rot_yz)
        c_xz, s_xz = math.cos(rot_xz), math.sin(rot_xz)
        
        for p in points_nd:
            x, y, z = p[0], p[1], p[2]
            
            x1 = x * c_xy - y * s_xy
            y1 = x * s_xy + y * c_xy
            x, y = x1, y1
            
            y1 = y * c_yz - z * s_yz
            z1 = y * s_yz + z * c_yz
            y, z = y1, z1
            
            x1 = x * c_xz - z * s_xz
            z1 = x * s_xz + z * c_xz
            x, z = x1, z1
            
            z_factor = 1.0 / (2.0 - z)
            x2 = x * z_factor
            y2 = y * z_factor
            
            scale = radius * 1.8
            px = center.x() + x2 * scale
            py = center.y() + y2 * scale
            points_2d.append(QPointF(px, py))
            
    else:
        # INSANE 5D PENTERACT for the main app! (32 vertices, 80 edges)
        radius = size * 0.38
        points_nd = []
        for i in range(32):
            x = -0.5 if (i & 1) == 0 else 0.5
            y = -0.5 if (i & 2) == 0 else 0.5
            z = -0.5 if (i & 4) == 0 else 0.5
            w = -0.5 if (i & 8) == 0 else 0.5
            v = -0.5 if (i & 16) == 0 else 0.5
            points_nd.append([x, y, z, w, v])
            
        for i in range(32):
            for j in range(i + 1, 32):
                if (i ^ j) in (1, 2, 4, 8, 16):
                    edges.append((i, j))
                    
        rot_xy = rotation * 1.2
        rot_zw = rotation * 0.7
        rot_xw = rotation * 0.9
        rot_yv = rotation * 0.5
        rot_zv = rotation * 1.1
        
        c_xy, s_xy = math.cos(rot_xy), math.sin(rot_xy)
        c_zw, s_zw = math.cos(rot_zw), math.sin(rot_zw)
        c_xw, s_xw = math.cos(rot_xw), math.sin(rot_xw)
        c_yv, s_yv = math.cos(rot_yv), math.sin(rot_yv)
        c_zv, s_zv = math.cos(rot_zv), math.sin(rot_zv)
        
        for p in points_nd:
            x, y, z, w, v = p[0], p[1], p[2], p[3], p[4]
            
            y1 = y * c_yv - v * s_yv
            v1 = y * s_yv + v * c_yv
            y, v = y1, v1
            
            z1 = z * c_zv - v * s_zv
            v1 = z * s_zv + v * c_zv
            z, v = z1, v1
            
            x1 = x * c_xy - y * s_xy
            y1 = x * s_xy + y * c_xy
            x, y = x1, y1
            
            z1 = z * c_zw - w * s_zw
            w1 = z * s_zw + w * c_zw
            z, w = z1, w1
            
            x1 = x * c_xw - w * s_xw
            w1 = x * s_xw + w * c_xw
            x, w = x1, w1
            
            # Triple Projection: 5D -> 4D -> 3D -> 2D
            v_factor = 1.0 / (2.0 - v)
            x = x * v_factor
            y = y * v_factor
            z = z * v_factor
            w = w * v_factor
            
            w_factor = 1.0 / (2.0 - w)
            x = x * w_factor
            y = y * w_factor
            z = z * w_factor
            
            z += math.sin(rotation * 2.0) * 0.1
            
            z_factor = 1.0 / (2.0 - z)
            x2 = x * z_factor
            y2 = y * z_factor
            
            scale = radius * 3.4
            px = center.x() + x2 * scale
            py = center.y() + y2 * scale
            points_2d.append(QPointF(px, py))

    from ui.icons import get_svg_pixmap
    
    # The happy little neon green file swirling in its own independent arching orbit!
    # Calculate an XZ circular orbit (Z-depth)
    orbit_radius = radius * (0.70 if is_tray else 0.52)
    happy_z = math.cos(rotation * 2.7)
    happy_x = center.x() + orbit_radius * math.sin(rotation * 2.7)
    happy_y = center.y() + orbit_radius * math.sin(rotation * 1.4) * math.cos(rotation * 0.9)
    
    base_size = radius * (0.35 if is_tray else 0.22)
    depth_scale = 1.0 + (happy_z * 0.35) # Scale based on depth for 3D perspective
    green_icon_w = int(base_size * depth_scale)
    green_icon_h = green_icon_w
    
    green_file_pixmap = get_svg_pixmap("file_text", size=green_icon_w, color="#39ff14")
    
    # Draw BEHIND the Penteract if Z < 0
    if happy_z < 0 and not green_file_pixmap.isNull():
        painter.drawPixmap(int(happy_x - green_icon_w / 2), int(happy_y - green_icon_h / 2), green_file_pixmap)

    # Draw the glowing mesh
    # 1. Outer glow (Metallic) - Halved thickness, lower opacity
    outer_glow_width = max(0.5, 2.0 * (size / 64.0))
    painter.setPen(QPen(QColor(160, 170, 180, 40), outer_glow_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    for e in edges:
        painter.drawLine(points_2d[e[0]], points_2d[e[1]])
            
    # 2. Bright inner core lines (Silver/Chrome) - Halved thickness, lower opacity
    inner_core_width = max(0.5, 0.75 * (size / 64.0))
    painter.setPen(QPen(QColor(230, 240, 250, 120), inner_core_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    for e in edges:
        painter.drawLine(points_2d[e[0]], points_2d[e[1]])
        
    # Add a glowing central node
    painter.setBrush(QColor(255, 255, 255, 255))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(center, radius * 0.15, radius * 0.15)
    
    # Node dots
    icon_w = int(radius * (0.35 if is_tray else 0.20))
    icon_h = int(radius * (0.35 if is_tray else 0.20))
    file_pixmap = get_svg_pixmap("file", size=icon_w, color="#00e5ff")
    if not file_pixmap.isNull():
        for p in points_2d:
            painter.drawPixmap(int(p.x() - icon_w / 2), int(p.y() - icon_h / 2), file_pixmap)
    else:
        painter.setBrush(QColor(0, 229, 255, 255))
        painter.setPen(Qt.PenStyle.NoPen)
        for p in points_2d:
            painter.drawEllipse(p, radius * 0.10, radius * 0.10)

    # Draw IN FRONT of the Penteract if Z >= 0
    if happy_z >= 0 and not green_file_pixmap.isNull():
        painter.drawPixmap(int(happy_x - green_icon_w / 2), int(happy_y - green_icon_h / 2), green_file_pixmap)

    painter.end()
    return pixmap

def get_tray_icon(size: int = 256, rotation: float = 0.0):
    from PyQt6.QtGui import QIcon
    return QIcon(_draw_logo_pixmap(size, rotation, is_tray=True))

def get_logo_pixmap(size: int = 48, rotation: float = 0.0):
    """
    Returns a smooth QPixmap of the logo sized to (size, size).
    Cached only if rotation is 0.0.
    """
    if rotation == 0.0 and size in _CACHED_LOGO_PIXMAPS:
        return _CACHED_LOGO_PIXMAPS[size]

    pixmap = _draw_logo_pixmap(size, rotation)
    if rotation == 0.0:
        _CACHED_LOGO_PIXMAPS[size] = pixmap
    return pixmap

