import math
import random
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPolygonF

class MinimizeParticle:
    def __init__(self, start_rect: QRect, target: QPoint):
        # Spawn randomly within the original window bounds
        self.x = random.uniform(start_rect.x(), start_rect.x() + start_rect.width())
        self.y = random.uniform(start_rect.y(), start_rect.y() + start_rect.height())
        
        self.target_x = target.x()
        self.target_y = target.y()
        
        # Initial scattered velocity to make them "explode" slightly before collapsing
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(2, 15)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        
        self.size = random.uniform(1.0, 3.0)
        
        colors = ["#00e5ff", "#00d2ff", "#38bdf8", "#7dd3fc", "#ffffff"]
        self.color_hex = random.choice(colors)
        
        self.base_color = QColor(self.color_hex)
        
        self.trail_color = QColor(self.base_color)
        self.trail_color.setAlpha(100)
        self.trail_pen = QPen(self.trail_color)
        self.trail_pen.setWidthF(self.size * 0.8)
        self.trail_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        
        self.glow_color = QColor(self.base_color)
        self.glow_color.setAlpha(60)
        
        self.active = True
        self.trail = []

    def update(self):
        if not self.active:
            return
            
        self.trail.append((self.x, self.y))
        if len(self.trail) > 10:
            self.trail.pop(0)
            
        # Distance to target
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.hypot(dx, dy)
        
        if dist < 20:
            self.active = False
            return
            
        # Gravitational pull towards target that gets stronger
        # Start gentle, then accelerate rapidly
        pull_strength = min(30.0, 1500.0 / (dist + 10))
        self.vx += (dx / dist) * pull_strength
        self.vy += (dy / dist) * pull_strength
        
        # Air friction
        self.vx *= 0.92
        self.vy *= 0.92
        
        self.x += self.vx
        self.y += self.vy

class MinimizeAnimationOverlay(QWidget):
    """A full-screen transparent overlay that runs the particle collapse animation."""
    def __init__(self, start_rect: QRect, target_point: QPoint, on_finished):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        self.on_finished = on_finished
        
        # Generate particles
        self.particles = [MinimizeParticle(start_rect, target_point) for _ in range(150)]
        
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._update_animation)
        self.anim_timer.start(16)
        
        # Fail-safe killer
        self.kill_timer = QTimer(self)
        self.kill_timer.setSingleShot(True)
        self.kill_timer.timeout.connect(self._finish)
        self.kill_timer.start(1200)

    def _update_animation(self):
        active_count = 0
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = -float('inf'), -float('inf')
        
        for p in self.particles:
            p.update()
            if p.active:
                active_count += 1
                if p.x < min_x: min_x = p.x
                if p.y < min_y: min_y = p.y
                if p.x > max_x: max_x = p.x
                if p.y > max_y: max_y = p.y
                
        if active_count == 0:
            self._finish()
            return

        margin = 60 # Increased margin to account for trails and glow without calculating them
        rect = QRect(int(min_x - margin), int(min_y - margin), int(max_x - min_x + margin*2), int(max_y - min_y + margin*2))
        
        if hasattr(self, '_last_rect'):
            update_rect = rect.united(self._last_rect)
        else:
            update_rect = rect
            
        self._last_rect = rect
        self.update(update_rect)
            
    def _finish(self):
        self.anim_timer.stop()
        if self.on_finished:
            self.on_finished()
        self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        for p in self.particles:
            if not p.active:
                continue
                
            # Draw trail
            if len(p.trail) > 1:
                painter.setPen(p.trail_pen)
                points = [QPointF(x, y) for x, y in p.trail]
                painter.drawPolyline(QPolygonF(points))
                
            # Draw particle head
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(p.base_color)
            painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)
            
            # Subtle glow
            painter.setBrush(p.glow_color)
            painter.drawEllipse(QPointF(p.x, p.y), p.size * 2.5, p.size * 2.5)

class RestoreParticle:
    def __init__(self, start: QPoint, target_rect: QRect):
        self.x = start.x()
        self.y = start.y()
        
        self.target_x = random.uniform(target_rect.x(), target_rect.x() + target_rect.width())
        self.target_y = random.uniform(target_rect.y(), target_rect.y() + target_rect.height())
        
        center_dx = target_rect.center().x() - start.x()
        center_dy = target_rect.center().y() - start.y()
        base_angle = math.atan2(center_dy, center_dx)
        
        angle = base_angle + random.uniform(-1.5, 1.5)
        speed = random.uniform(20, 60)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        
        self.size = random.uniform(1.0, 3.0)
        
        colors = ["#00e5ff", "#00d2ff", "#38bdf8", "#7dd3fc", "#ffffff"]
        self.color_hex = random.choice(colors)
        
        self.base_color = QColor(self.color_hex)
        
        self.trail_color = QColor(self.base_color)
        self.trail_color.setAlpha(100)
        self.trail_pen = QPen(self.trail_color)
        self.trail_pen.setWidthF(self.size * 0.8)
        self.trail_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        
        self.glow_color = QColor(self.base_color)
        self.glow_color.setAlpha(60)
        
        self.active = True
        self.trail = []

    def update(self):
        if not self.active:
            return
            
        self.trail.append((self.x, self.y))
        if len(self.trail) > 10:
            self.trail.pop(0)
            
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.hypot(dx, dy)
        
        if dist < 30:
            self.active = False
            return
            
        pull_strength = min(40.0, 2000.0 / (dist + 10))
        self.vx += (dx / dist) * pull_strength
        self.vy += (dy / dist) * pull_strength
        
        self.vx *= 0.88
        self.vy *= 0.88
        
        self.x += self.vx
        self.y += self.vy

class RestoreAnimationOverlay(QWidget):
    def __init__(self, start_point: QPoint, target_rect: QRect, on_finished):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        self.on_finished = on_finished
        self.particles = [RestoreParticle(start_point, target_rect) for _ in range(1)]
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._update_animation)
        self.anim_timer.start(16)
        
        self.kill_timer = QTimer(self)
        self.kill_timer.setSingleShot(True)
        self.kill_timer.timeout.connect(self._finish)
        self.kill_timer.start(1000)

    def _update_animation(self):
        active_count = 0
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = -float('inf'), -float('inf')
        
        for p in self.particles:
            p.update()
            if p.active:
                active_count += 1
                if p.x < min_x: min_x = p.x
                if p.y < min_y: min_y = p.y
                if p.x > max_x: max_x = p.x
                if p.y > max_y: max_y = p.y
                
        if active_count == 0:
            self._finish()
            return
            
        margin = 60 # Increased margin to account for trails and glow without calculating them
        rect = QRect(int(min_x - margin), int(min_y - margin), int(max_x - min_x + margin*2), int(max_y - min_y + margin*2))
        
        if hasattr(self, '_last_rect'):
            update_rect = rect.united(self._last_rect)
        else:
            update_rect = rect
            
        self._last_rect = rect
        self.update(update_rect)
            
    def _finish(self):
        self.anim_timer.stop()
        if self.on_finished:
            self.on_finished()
        self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        for p in self.particles:
            if not p.active:
                continue
                
            if len(p.trail) > 1:
                painter.setPen(p.trail_pen)
                points = [QPointF(x, y) for x, y in p.trail]
                painter.drawPolyline(QPolygonF(points))
                
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(p.base_color)
            painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)
            
            painter.setBrush(p.glow_color)
            painter.drawEllipse(QPointF(p.x, p.y), p.size * 2.5, p.size * 2.5)
