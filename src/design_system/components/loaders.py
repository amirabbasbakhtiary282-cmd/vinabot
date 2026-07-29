# -*- coding: utf-8 -*-
"""
کامپوننت‌های بارگذاری/انیمیشن پس‌زمینه‌ی سیستم طراحی وینا

- LoadingSpinner: اسپینر چرخان مدرن (کمان گرادیانی)
- AiOrb: ارب پالسی گرادیانی، نشانگر وضعیت هوش مصنوعی (آماده/فکر/صحبت)
- ParticleSystem: ذرات نور ملایم برای پس‌زمینه
"""

import math
import random

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line
from kivy.properties import BooleanProperty, NumericProperty
from kivy.uix.widget import Widget

from src.design_system.base import ThemedWidgetMixin, theme

MAX_PARTICLES = 36


class LoadingSpinner(Widget, ThemedWidgetMixin):
    """اسپینر چرخان مدرن (کمان گرادیانی)"""

    active = BooleanProperty(True)
    line_width = NumericProperty(3)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._angle = 0
        self._update_event = Clock.schedule_interval(self._update, 1.0 / 60)
        self.bind_theme()

    def on_theme_changed(self):
        pass

    def on_parent(self, widget, parent):
        if parent is None and self._update_event is not None:
            self._update_event.cancel()
            self._update_event = None
        elif parent is not None and self._update_event is None:
            self._update_event = Clock.schedule_interval(self._update, 1.0 / 60)

    def _update(self, dt):
        if not self.active:
            self.canvas.clear()
            return
        self._angle = (self._angle + dt * 220) % 360
        if not self.width or not self.height:
            return

        cx, cy = self.center_x, self.center_y
        radius = min(self.width, self.height) / 2 - self.line_width

        self.canvas.clear()
        with self.canvas:
            Color(*theme.bg_surface_alt[:3], 0.6)
            Line(circle=(cx, cy, radius), width=self.line_width)

            Color(*theme.accent)
            Line(
                circle=(cx, cy, radius, self._angle, self._angle + 100),
                width=self.line_width, cap='round',
            )


class AiOrb(Widget, ThemedWidgetMixin):
    """ارب پالسی گرادیانی که وضعیت وینا (آماده/در حال فکر کردن/صحبت) را نشان می‌دهد"""

    is_active = BooleanProperty(False)
    is_thinking = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._t = 0.0
        self._pulse = 0.0
        self._update_event = Clock.schedule_interval(self._update, 1.0 / 60)
        self.bind_theme()

    def on_theme_changed(self):
        pass

    def on_parent(self, widget, parent):
        if parent is None and self._update_event is not None:
            self._update_event.cancel()
            self._update_event = None
        elif parent is not None and self._update_event is None:
            self._update_event = Clock.schedule_interval(self._update, 1.0 / 60)

    def _update(self, dt):
        self._t += dt
        active = self.is_active or self.is_thinking
        speed = 3.2 if active else 0.8
        self._pulse = (math.sin(self._t * speed) + 1) / 2

        if not self.width or not self.height:
            return

        cx, cy = self.center_x, self.center_y
        base_radius = min(self.width, self.height) * 0.28
        radius = base_radius + base_radius * 0.15 * self._pulse

        accent = theme.accent
        accent2 = theme.accent_secondary

        self.canvas.clear()
        with self.canvas:
            for i in range(3):
                glow_r = radius + (i + 1) * 10
                alpha = (0.14 - i * 0.035) * (1.3 if active else 1.0)
                Color(*accent[:3], max(0, alpha))
                Ellipse(pos=(cx - glow_r, cy - glow_r), size=(glow_r * 2, glow_r * 2))

            steps = 10
            for i in range(steps, 0, -1):
                frac = i / steps
                r = radius * frac
                mix = 1 - frac
                color = [accent[j] + (accent2[j] - accent[j]) * mix * 0.6 for j in range(3)]
                Color(*color, 0.92)
                Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))

            orbit_count = 3
            orbit_speed = 95 if active else 18
            for i in range(orbit_count):
                angle = math.radians(self._t * orbit_speed + i * (360 / orbit_count))
                orbit_r = radius + 22
                px = cx + orbit_r * math.cos(angle)
                py = cy + orbit_r * math.sin(angle) * 0.9
                dot_r = 3.4
                Color(*accent2[:3], 0.88)
                Ellipse(pos=(px - dot_r, py - dot_r), size=(dot_r * 2, dot_r * 2))


class ParticleSystem(Widget, ThemedWidgetMixin):
    """ذرات درخشان و ملایم در پس‌زمینه؛ برای عمق بصری بدون حواس‌پرتی"""

    num_particles = NumericProperty(MAX_PARTICLES)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.particles = []
        self._update_event = Clock.schedule_interval(self._update, 1.0 / 30)
        self.bind(size=self._init_particles)
        Clock.schedule_once(lambda dt: self._init_particles(), 0)
        self.bind_theme()

    def on_theme_changed(self):
        pass

    def on_parent(self, widget, parent):
        if parent is None and self._update_event is not None:
            self._update_event.cancel()
            self._update_event = None
        elif parent is not None and self._update_event is None:
            self._update_event = Clock.schedule_interval(self._update, 1.0 / 30)

    def _init_particles(self, *args):
        w = self.width or Window.width
        h = self.height or Window.height
        self.particles = []
        for _ in range(int(self.num_particles)):
            self.particles.append({
                'x': random.uniform(0, w),
                'y': random.uniform(0, h),
                'size': random.uniform(1, 3),
                'speed': random.uniform(0.12, 0.5),
                'alpha': random.uniform(0.06, 0.28),
                'drift': random.uniform(-0.25, 0.25),
            })

    def _update(self, dt):
        w = self.width or Window.width
        h = self.height or Window.height
        if not w or not h:
            return

        accent = theme.accent
        self.canvas.clear()
        with self.canvas:
            for p in self.particles:
                p['y'] += p['speed']
                p['x'] += p['drift']

                if p['y'] > h:
                    p['y'] = -10
                    p['x'] = random.uniform(0, w)
                if p['x'] < 0:
                    p['x'] = w
                elif p['x'] > w:
                    p['x'] = 0

                Color(*accent[:3], p['alpha'])
                Ellipse(
                    pos=(p['x'] - p['size'] / 2, p['y'] - p['size'] / 2),
                    size=(p['size'], p['size']),
                )
