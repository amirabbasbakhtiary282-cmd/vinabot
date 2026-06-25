# -*- coding: utf-8 -*-
"""
ماژول ویجت‌های رابط کاربری وینا
هولوگرام سه‌بعدی، ذرات نور، موج صدا، حباب چت، دکمه نئونی
"""

import math
import random
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import NumericProperty, ListProperty, BooleanProperty, StringProperty
from kivy.graphics import (
    Color, Ellipse, Rectangle, Line, PushMatrix, PopMatrix,
    Rotate, Scale, Translate, Mesh, Triangle
)
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.core.window import Window


class HologramWidget(Widget):
    """ویجت هولوگرام سه‌بعدی چرخان"""
    rotation_angle = NumericProperty(0)
    pulse_alpha = NumericProperty(0.8)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.angle = 0
        self.pulse_dir = 1
        self.cube_vertices = self._generate_cube_vertices()
        self.ring_angles = [0, 0, 0]
        Clock.schedule_interval(self._update, 1.0 / 30)

    def _generate_cube_vertices(self):
        """تولید رئوس مکعب"""
        s = 40
        return [
            (-s, -s, -s), (s, -s, -s), (s, s, -s), (-s, s, -s),
            (-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s)
        ]

    def _update(self, dt):
        """بروزرسانی انیمیشن"""
        self.angle += 1.5
        self.ring_angles[0] += 1.0
        self.ring_angles[1] += 1.5
        self.ring_angles[2] += 0.8

        self.pulse_alpha += 0.02 * self.pulse_dir
        if self.pulse_alpha > 1.0:
            self.pulse_dir = -1
        elif self.pulse_alpha < 0.4:
            self.pulse_dir = 1

        self.canvas.clear()
        self._draw_hologram()

    def _draw_hologram(self):
        """ترسیم هولوگرام"""
        cx, cy = self.center_x, self.center_y
        angle_rad = math.radians(self.angle)

        with self.canvas:
            Color(0, 1, 0.25, 0.3)
            Ellipse(pos=(cx - 70, cy - 70), size=(140, 140))

            Color(0, 1, 0.25, self.pulse_alpha * 0.5)
            Ellipse(pos=(cx - 50, cy - 50), size=(100, 100))

            self._draw_cube(cx, cy, angle_rad)

            for i in range(3):
                self._draw_ring(cx, cy, 55 + i * 12, self.ring_angles[i], i)

    def _draw_cube(self, cx, cy, angle):
        """ترسیم مکعب سه‌بعدی"""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        cos_b = math.cos(angle * 0.7)
        sin_b = math.sin(angle * 0.7)

        projected = []
        for x, y, z in self.cube_vertices:
            rx = x * cos_a - z * sin_a
            rz = x * sin_a + z * cos_a
            ry = y * cos_b - rz * sin_b
            ry_proj = y * sin_b + rz * cos_b

            scale = 200 / (200 + ry_proj)
            px = cx + rx * scale
            py = cy + ry * scale
            projected.append((px, py))

        edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7)
        ]

        Color(0, 1, 0.25, 0.9)
        for i, j in edges:
            Line(points=[projected[i][0], projected[i][1],
                         projected[j][0], projected[j][1]],
                 width=1.5)

        for px, py in projected:
            Color(0.24, 1, 0.08, 0.8)
            Ellipse(pos=(px - 3, py - 3), size=(6, 6))

    def _draw_ring(self, cx, cy, radius, angle, index):
        """ترسیم حلقه متداخل"""
        points = []
        segments = 60
        tilt = [0.3, 0.5, 0.7][index]
        colors = [
            (0, 1, 0.25, 0.6),
            (0.24, 1, 0.08, 0.5),
            (0.69, 1, 0.69, 0.4)
        ]

        angle_rad = math.radians(angle)
        with self.canvas:
            Color(*colors[index])
            for i in range(segments + 1):
                t = (2 * math.pi * i) / segments
                x = radius * math.cos(t)
                y = radius * math.sin(t) * tilt
                rx = x * math.cos(angle_rad) - y * math.sin(angle_rad)
                ry = x * math.sin(angle_rad) + y * math.cos(angle_rad)
                points.extend([cx + rx, cy + ry])
            Line(points=points, width=1.5)


class ParticleSystem(Widget):
    """سیستم ذرات نور سبز"""
    num_particles = NumericProperty(100)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.particles = []
        self._init_particles()
        Clock.schedule_interval(self._update, 1.0 / 30)

    def _init_particles(self):
        """مقداردهی اولیه ذرات"""
        self.particles = []
        for _ in range(self.num_particles):
            self.particles.append({
                'x': random.uniform(0, self.width or Window.width),
                'y': random.uniform(0, self.height or Window.height),
                'size': random.uniform(1, 4),
                'speed': random.uniform(0.3, 1.5),
                'alpha': random.uniform(0.2, 0.8),
                'drift': random.uniform(-0.5, 0.5),
            })

    def _update(self, dt):
        """بروزرسانی ذرات"""
        self.canvas.clear()
        w = self.width or Window.width
        h = self.height or Window.height

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

            with self.canvas:
                Color(0, 1, 0.25, p['alpha'])
                Ellipse(
                    pos=(p['x'] - p['size'] / 2, p['y'] - p['size'] / 2),
                    size=(p['size'], p['size'])
                )

    def on_size(self, *args):
        if self.particles:
            for p in self.particles:
                p['x'] = random.uniform(0, self.width)
                p['y'] = random.uniform(0, self.height)


class SoundWaveWidget(Widget):
    """ویجت موج صدا"""
    bar_count = NumericProperty(30)
    is_active = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.levels = [0.0] * self.bar_count
        self.target_levels = [0.0] * self.bar_count
        Clock.schedule_interval(self._update, 1.0 / 20)

    def _update(self, dt):
        """بروزرسانی موج"""
        self.canvas.clear()
        if not self.width:
            return

        bar_width = self.width / (self.bar_count * 1.5)
        gap = bar_width * 0.5
        total_width = self.bar_count * (bar_width + gap)
        start_x = (self.width - total_width) / 2

        for i in range(self.bar_count):
            if self.is_active:
                self.target_levels[i] = random.uniform(0.2, 1.0)
            else:
                self.target_levels[i] = 0.05 + 0.05 * math.sin(
                    Clock.get_time() * 2 + i * 0.3
                )

            self.levels[i] += (self.target_levels[i] - self.levels[i]) * 0.3

            bar_height = self.levels[i] * self.height * 0.8
            x = start_x + i * (bar_width + gap)
            y = (self.height - bar_height) / 2

            alpha = 0.4 + self.levels[i] * 0.6
            with self.canvas:
                Color(0, 1, 0.25, alpha)
                Rectangle(
                    pos=(x, y),
                    size=(bar_width, bar_height)
                )
                Color(0.24, 1, 0.08, alpha * 0.5)
                Rectangle(
                    pos=(x, y),
                    size=(bar_width, min(bar_height * 0.3, 5))
                )

    def set_levels(self, levels):
        """تنظیم سطوح صدا"""
        for i, level in enumerate(levels[:self.bar_count]):
            self.target_levels[i] = min(1.0, level / 32768.0 if level > 1 else level)


class NeonButton(Button):
    """دکمه نئونی با افکت درخشش"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0.23, 0, 1)
        self.color = (0, 1, 0.25, 1)
        self.bold = True
        self.font_size = 16

        self.bind(on_press=self._on_press)
        self.bind(on_release=self._on_release)
        self.bind(on_touch_down=self._on_touch_down)

    def _on_press(self, instance):
        """افکت فشردن"""
        anim = Animation(
            background_color=(0, 0.4, 0, 1),
            duration=0.1
        )
        anim.start(instance)

    def _on_release(self, instance):
        """افکت رها کردن"""
        anim = Animation(
            background_color=(0, 0.23, 0, 1),
            duration=0.2
        )
        anim.start(instance)

    def _on_touch_down(self, instance, touch):
        """افکت لمس"""
        if instance.collide_point(*touch.pos):
            anim = Animation(
                font_size=instance.font_size + 2,
                duration=0.1
            ) + Animation(
                font_size=instance.font_size,
                duration=0.1
            )
            anim.start(instance)


class ChatBubble(BoxLayout):
    """حباب چت"""
    message_text = StringProperty('')
    is_user = BooleanProperty(True)
    timestamp = StringProperty('')

    def __init__(self, message='', is_user=True, time_str='', **kwargs):
        super().__init__(**kwargs)
        self.message_text = message
        self.is_user = is_user
        self.timestamp = time_str
        self.orientation = 'horizontal'
        self.padding = [10, 5, 10, 5]
        self.size_hint_y = None
        self.height = 60

    def start_typing_animation(self):
        """شروع انیمیشن تایپ"""
        self.typing_text = ''
        self.full_text = self.message_text
        self.char_index = 0
        Clock.schedule_interval(self._type_next_char, 0.03)

    def _type_next_char(self, dt):
        """تایپ حرف بعدی"""
        if self.char_index < len(self.full_text):
            self.typing_text += self.full_text[self.char_index]
            self.char_index += 1
            self.message_text = self.typing_text
        else:
            return False
        return True


class NeonLabel(Label):
    """لیبل نئونی"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.markup = True
        if 'color' not in kwargs:
            self.color = (0, 1, 0.25, 1)


class GlitchWidget(Widget):
    """افکت گلیچ"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.glitch_active = False
        self.glitch_timer = 0

    def trigger_glitch(self, duration=0.3):
        """فعال‌سازی گلیچ"""
        self.glitch_active = True
        self.glitch_timer = duration
        Clock.schedule_interval(self._update_glitch, 1.0 / 30)

    def _update_glitch(self, dt):
        """بروزرسانی گلیچ"""
        if not self.glitch_active:
            return False

        self.glitch_timer -= dt
        if self.glitch_timer <= 0:
            self.glitch_active = False
            self.canvas.clear()
            return False

        self.canvas.clear()
        with self.canvas:
            for _ in range(3):
                x = random.uniform(0, self.width)
                y = random.uniform(0, self.height)
                w = random.uniform(10, self.width)
                h = random.uniform(1, 5)
                Color(0, 1, 0.25, random.uniform(0.3, 0.8))
                Rectangle(pos=(x, y), size=(w, h))

        return True


class NeonProgressBar(Widget):
    """نوار پیشرفت نئونی"""
    progress = NumericProperty(0)
    max_progress = NumericProperty(100)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_interval(lambda dt: self._draw(), 0.1)

    def _draw(self):
        self.canvas.clear()
        if not self.width:
            return

        with self.canvas:
            Color(0, 0.15, 0, 1)
            Rectangle(pos=self.pos, size=(self.width, 8))

            fill_width = (self.progress / self.max_progress) * self.width
            Color(0, 1, 0.25, 0.9)
            Rectangle(pos=self.pos, size=(fill_width, 8))

            Color(0.24, 1, 0.08, 0.5)
            Rectangle(
                pos=(self.pos[0], self.pos[1] + 6),
                size=(fill_width, 2)
            )
