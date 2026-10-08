"""
Merge particle animation system for MNIME.
Provides:
1. Continuous gravitational file particle pull toward the Merge button on hover.
2. Hyper-speed particle collapse on click.
3. Dramatic cinematic flash & shockwave transition (like the metal splash screen)
   as the application transitions to the completed merge screen.
"""

import math
import random
import time
from typing import List, Optional, Callable

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import (
    QPainter, QColor, QRadialGradient, QLinearGradient, QPixmap,
    QPainterPath, QPen, QCursor
)
from PyQt6.QtCore import Qt, QPoint, QPointF, QTimer


_MINI_FILE_CACHE: dict = {}


def _get_mini_file_pixmap(size: int = 16, color_hex: str = "#00e5ff") -> QPixmap:
    """Pre-render a miniature crisp neon file icon for particle rendering."""
    key = (size, color_hex)
    if key in _MINI_FILE_CACHE:
        return _MINI_FILE_CACHE[key]

    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    s = size / 24.0
    poly = [
        QPointF(5 * s, 2 * s),
        QPointF(15 * s, 2 * s),
        QPointF(21 * s, 8 * s),
        QPointF(21 * s, 22 * s),
        QPointF(5 * s, 22 * s),
    ]
    path = QPainterPath()
    path.moveTo(poly[0])
    for pt in poly[1:]:
        path.lineTo(pt)
    path.closeSubpath()

    # Dark slate fill
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(13, 17, 23, 235))
    p.drawPath(path)

    # Neon outline
    pen = QPen(QColor(color_hex), 1.3)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(path)

    # Fold triangle
    fold = QPainterPath()
    fold.moveTo(15 * s, 2 * s)
    fold.lineTo(15 * s, 8 * s)
    fold.lineTo(21 * s, 8 * s)
    p.drawPath(fold)

    # Fold fill highlight
    fold_fill = QPainterPath()
    fold_fill.moveTo(15 * s, 2 * s)
    fold_fill.lineTo(15 * s, 8 * s)
    fold_fill.lineTo(21 * s, 8 * s)
    fold_fill.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(0, 210, 255, 60))
    p.drawPath(fold_fill)

    # Text content lines
    p.setPen(QPen(QColor(color_hex), 1.1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(int(8 * s), int(12 * s), int(18 * s), int(12 * s))
    p.drawLine(int(8 * s), int(16 * s), int(18 * s), int(16 * s))

    p.end()
    _MINI_FILE_CACHE[key] = pm
    return pm


class StreamParticle:
    """A single particle flowing into the merge button vortex."""

    def __init__(self, target: QPointF, min_dist: float, max_dist: float, initial_scatter: bool = False):
        self.target = target
        self.max_dist = max_dist
        self.min_dist = min_dist

        # If initial_scatter is True, distribute evenly across distances so vortex is immediately active
        if initial_scatter:
            self.dist = random.uniform(min_dist, max_dist)
        else:
            self.dist = random.uniform(max_dist * 0.75, max_dist)

        self.angle = random.uniform(0.0, 2.0 * math.pi)
        self.spiral_speed = random.uniform(-2.2, 2.2)
        self.base_speed = random.uniform(220.0, 420.0)

        # 40% chance of mini file icon, 60% chance of photon spark
        self.is_file = (random.random() < 0.40)
        self.rotation = random.uniform(0.0, 360.0)
        self.rotation_speed = random.uniform(-250.0, 250.0)

        self.spark_size = random.uniform(2.5, 5.0)
        colors = ["#00e5ff", "#00d2ff", "#38bdf8", "#7dd3fc", "#ffffff"]
        self.color_hex = random.choice(colors)

        self.trail: List[QPointF] = []
        self.alive = True

    def reset_outer(self):
        """Respawn on the outer perimeter to sustain continuous flow."""
        self.dist = random.uniform(self.max_dist * 0.85, self.max_dist)
        self.angle = random.uniform(0.0, 2.0 * math.pi)
        self.spiral_speed = random.uniform(-2.2, 2.2)
        self.trail.clear()
        self.alive = True

    def update(self, dt: float, hyper: bool, stopping: bool, processing: bool = False) -> bool:
        """
        Updates particle position along gravitational vortex curve.
        Returns False if dead and shouldn't respawn.
        """
        if not self.alive:
            return False

        # Gravitational acceleration: moves faster as it nears center
        speed_mult = 1.0 + (280.0 / (self.dist + 35.0))
        if hyper:
            speed_mult *= 3.2

        current_speed = self.base_speed * speed_mult
        self.dist -= current_speed * dt

        # Angular spiral velocity increases near singularity
        angle_mult = 1.0 + (120.0 / (self.dist + 40.0))
        self.angle += self.spiral_speed * angle_mult * dt

        # Calculate coordinates
        x = self.target.x() + self.dist * math.cos(self.angle)
        y = self.target.y() + self.dist * math.sin(self.angle)
        current_pt = QPointF(x, y)

        self.trail.append(current_pt)
        if len(self.trail) > 3:
            self.trail.pop(0)

        # Tumble rotation
        self.rotation += self.rotation_speed * dt

        # Singularity threshold: reached center
        if self.dist <= 12.0:
            if (stopping or hyper) and not processing:
                self.alive = False
                return False
            else:
                self.reset_outer()
                return True

        return True


class MergeParticleOverlay(QWidget):
    """
    Master particle and cinematic transition overlay for MNIME.
    Handles:
    - Inward gravitational pull of file particles on Merge button hover.
    - Violent hyper-collapse on Merge button click.
    - Dramatic full-window white-cyan flash & shockwave transition into output screen.
    """

    FLASH_DURATION_MS = 600

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.target = QPointF(float(parent.width() / 2), float(parent.height() / 2))
        self.particles: List[StreamParticle] = []

        self.hover_active = False
        self.stopping = False
        self.hyper = False

        # Flash transition state
        self.flash_active = False
        self.flash_start_time = 0.0
        self.flash_peak_called = False
        self.on_peak_callback: Optional[Callable[[], None]] = None

        self.last_tick = time.time()

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.setGeometry(parent.rect())
        self.hide()

        self.timer = QTimer(self)
        self.timer.setInterval(16)  # ~60 fps
        self.timer.timeout.connect(self._on_tick)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.parent():
            self.setGeometry(self.parent().rect())

    # -------------------------------------------------------------------------
    # 1. Hover Pull Management
    # -------------------------------------------------------------------------
    def start_hover_pull(self, target_pos: QPoint):
        """Start pulling files and sparks into target_pos continuously."""
        if self.flash_active:
            return

        self.target = QPointF(float(target_pos.x()), float(target_pos.y()))
        self.hover_active = True
        self.stopping = False
        self.hyper = False

        # Calculate wide pull-in radius (from carousel down to bottom bar)
        w, h = self.width(), self.height()
        max_dist = max(320.0, min(580.0, math.hypot(w, h) * 0.52))
        min_dist = 60.0

        # Create stream particles (spread out so vortex activates immediately)
        particle_count = 19
        self.particles = [
            StreamParticle(self.target, min_dist, max_dist, initial_scatter=True)
            for _ in range(particle_count)
        ]

        self.last_tick = time.time()
        self.setGeometry(self.parent().rect())
        self.raise_()
        self.show()

        if not self.timer.isActive():
            self.timer.start()

    def update_target_pos(self, target_pos: QPoint):
        """Update center coordinates if cursor moves inside button."""
        self.target = QPointF(float(target_pos.x()), float(target_pos.y()))
        for p in self.particles:
            p.target = self.target

    def stop_hover_pull(self):
        """Mouse left Merge button: let existing particles drain in gracefully."""
        if getattr(self, 'processing', False):
            return  # Do not drain if we are currently running the background task!
        self.hover_active = False
        self.stopping = True

    def trigger_hyper_collapse(self):
        """User clicked Merge: keep particles sucking into center indefinitely at 3x speed!"""
        self.hyper = True
        self.stopping = False
        self.processing = True

    def clear_all(self):
        """Immediately stops all animations, clears all particles, and hides overlay."""
        self.processing = False
        self.hover_active = False
        self.stopping = True
        self.hyper = False
        self.flash_active = False
        self.particles.clear()
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        self.hide()

    # -------------------------------------------------------------------------
    # 2. Dramatic Flash Transition (like splash screen)
    # -------------------------------------------------------------------------
    def trigger_dramatic_flash(self, target_pos: Optional[QPoint] = None, on_peak_callback: Optional[Callable[[], None]] = None):
        """
        Fires an intense white-cyan screen flash with shockwave and lens flare.
        Invokes on_peak_callback at peak intensity to reveal the output view underneath.
        """
        if target_pos is not None:
            self.target = QPointF(float(target_pos.x()), float(target_pos.y()))

        # End all streaming particles immediately for the flash
        self.processing = False
        self.hover_active = False
        self.stopping = True
        self.particles.clear()

        self.on_peak_callback = on_peak_callback
        self.flash_active = True
        self.flash_peak_called = False
        self.flash_start_time = time.time()

        self.setGeometry(self.parent().rect())
        self.raise_()
        self.show()

        if not self.timer.isActive():
            self.last_tick = time.time()
            self.timer.start()

    # -------------------------------------------------------------------------
    # Frame Tick & Logic
    # -------------------------------------------------------------------------
    def _on_tick(self):
        now = time.time()
        dt = min(0.05, now - self.last_tick)
        self.last_tick = now

        # Update streaming particles
        alive_count = 0
        is_processing = getattr(self, 'processing', False)
        for p in self.particles:
            if p.update(dt, self.hyper, self.stopping, is_processing):
                alive_count += 1

        # Check flash transition progress
        flash_in_progress = False
        if self.flash_active:
            flash_elapsed = (now - self.flash_start_time) * 1000.0
            flash_progress = flash_elapsed / self.FLASH_DURATION_MS

            # Peak intensity at 18% of duration: swap screens underneath flash
            if flash_progress >= 0.18 and not self.flash_peak_called:
                self.flash_peak_called = True
                if self.on_peak_callback:
                    try:
                        self.on_peak_callback()
                    except Exception as e:
                        print(f"Error in on_peak_callback: {e}")

            if flash_progress >= 1.0:
                self.flash_active = False
            else:
                flash_in_progress = True

        # Stop conditions: no active hover, no living particles, and no flash
        if not self.hover_active and alive_count == 0 and not flash_in_progress:
            self.timer.stop()
            self.hide()
            self.particles.clear()
            return

        self.update()

    # -------------------------------------------------------------------------
    # Rendering
    # -------------------------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # ---------------------------------------------------------------------
        # Layers 1 & 2: Streaming Particles & Core (ONLY on File Selection Screen)
        # ---------------------------------------------------------------------
        if not self.flash_active:
            # Layer 1: Ambient Button Gravitational Singularity Core
            if self.hover_active or any(p.alive for p in self.particles):
                pulse = 0.5 + 0.5 * math.sin(time.time() * 9.0)
                core_radius = 20.0 + 8.0 * pulse
                if self.hyper:
                    core_radius = 35.0

                grad = QRadialGradient(self.target, core_radius)
                grad.setColorAt(0.0, QColor(255, 255, 255, 220))
                grad.setColorAt(0.35, QColor(0, 229, 255, 170))
                grad.setColorAt(0.7, QColor(0, 119, 182, 70))
                grad.setColorAt(1.0, QColor(0, 210, 255, 0))

                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(grad)
                painter.drawEllipse(self.target, core_radius, core_radius)

            # Layer 2: Inward Pulling Particles & Mini File Icons
            for p in self.particles:
                if not p.alive or not p.trail:
                    continue

                current_pt = p.trail[-1]

                # Opacity depends on distance from center
                if p.dist < 20.0:
                    alpha = int(255 * (p.dist / 20.0))
                elif p.dist > p.max_dist * 0.85:
                    alpha = int(255 * (1.0 - (p.dist - p.max_dist * 0.85) / (p.max_dist * 0.15)))
                else:
                    alpha = 240
                alpha = max(0, min(255, alpha))

                # Draw Motion Trail (light streaks)
                if len(p.trail) >= 2 and alpha > 25:
                    for i in range(len(p.trail) - 1):
                        trail_alpha = int((alpha * 0.4) * ((i + 1) / len(p.trail)))
                        trail_pen = QPen(QColor(0, 210, 255, trail_alpha), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                        painter.setPen(trail_pen)
                        painter.drawLine(p.trail[i], p.trail[i + 1])

                # Draw Particle Core
                if p.is_file:
                    mini_pm = _get_mini_file_pixmap(15, p.color_hex)
                    scale = max(0.25, min(1.0, p.dist / 45.0))
                    painter.save()
                    painter.translate(current_pt.x(), current_pt.y())
                    painter.rotate(p.rotation)
                    painter.scale(scale, scale)
                    painter.setOpacity(alpha / 255.0)
                    painter.drawPixmap(-8, -8, mini_pm)
                    painter.restore()
                else:
                    r = p.spark_size * max(0.4, min(1.2, p.dist / 50.0))
                    spark_color = QColor(p.color_hex)
                    spark_color.setAlpha(alpha)

                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QColor(0, 210, 255, int(alpha * 0.45)))
                    painter.drawEllipse(current_pt, r * 1.8, r * 1.8)
                    painter.setBrush(spark_color)
                    painter.drawEllipse(current_pt, r, r)

        # ---------------------------------------------------------------------
        # Layer 3: DRAMATIC CINEMATIC FLASH TRANSITION
        # ---------------------------------------------------------------------
        if self.flash_active:
            now = time.time()
            flash_elapsed = (now - self.flash_start_time) * 1000.0
            p = min(1.0, flash_elapsed / self.FLASH_DURATION_MS)

            # Intensity curve: rapid rise in first 18%, smooth exponential decay in remaining 82%
            if p < 0.18:
                intensity = p / 0.18
            else:
                decay = (p - 0.18) / 0.82
                intensity = (1.0 - decay) ** 2.2

            # 3A. Full-window white/cyan flash wash
            flash_alpha = int(235 * intensity)
            if flash_alpha > 0:
                painter.fillRect(self.rect(), QColor(255, 255, 255, flash_alpha))

            # 3B. Radiant Cyan Radial Bloom from Center
            bloom_radius = max(self.width(), self.height()) * 0.75
            bloom_alpha = int(200 * intensity)
            if bloom_alpha > 0:
                bloom_grad = QRadialGradient(self.target, bloom_radius)
                bloom_grad.setColorAt(0.0, QColor(255, 255, 255, bloom_alpha))
                bloom_grad.setColorAt(0.2, QColor(0, 229, 255, int(bloom_alpha * 0.85)))
                bloom_grad.setColorAt(0.6, QColor(0, 119, 182, int(bloom_alpha * 0.4)))
                bloom_grad.setColorAt(1.0, QColor(0, 210, 255, 0))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(bloom_grad)
                painter.drawRect(self.rect())

            # 3C. Expanding Shockwave Ring across entire window
            sw_progress = p ** 0.85
            sw_radius = sw_progress * max(self.width(), self.height()) * 0.95
            sw_alpha = int(230 * (1.0 - p))
            if sw_alpha > 0:
                sw_pen = QPen(QColor(0, 229, 255, sw_alpha), max(1.5, 4.0 * (1.0 - p)))
                painter.setPen(sw_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(self.target, sw_radius, sw_radius)

            # 3D. Anamorphic Horizontal Lens Flare Beam across the window
            beam_alpha = int(220 * intensity)
            if beam_alpha > 0:
                beam_h = 10.0 * (1.0 - p * 0.5)
                beam_y = self.target.y() - beam_h / 2.0
                beam_grad = QLinearGradient(0, self.target.y(), self.width(), self.target.y())
                beam_grad.setColorAt(0.0, QColor(0, 210, 255, 0))
                beam_grad.setColorAt(0.3, QColor(0, 229, 255, int(beam_alpha * 0.6)))
                beam_grad.setColorAt(0.5, QColor(255, 255, 255, beam_alpha))
                beam_grad.setColorAt(0.7, QColor(0, 229, 255, int(beam_alpha * 0.6)))
                beam_grad.setColorAt(1.0, QColor(0, 210, 255, 0))

                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(beam_grad)
                painter.drawRect(0, int(beam_y), self.width(), int(beam_h))

            # 3E. Central Starburst Spark Core
            star_alpha = int(255 * intensity)
            if star_alpha > 0:
                star_r = 16.0 * (1.0 - p * 0.5)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(255, 255, 255, star_alpha))
                painter.drawEllipse(self.target, star_r, star_r)

        painter.end()
