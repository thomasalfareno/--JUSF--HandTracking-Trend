import cv2
import math
import time
import numpy as np


class Visualizer:
    TYPES = ['circle', 'wave', 'bar', 'concert']

    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height
        self.current_type_index = 0
        self.base_color = (0, 255, 255)
        self.pulse_phase = 0.0

    @property
    def current_type(self):
        return self.TYPES[self.current_type_index]

    def cycle_type(self):
        self.current_type_index = (self.current_type_index + 1) % len(self.TYPES)

    def draw(self, frame, volume_level, hand_x=None, hand_y=None, love_mode=False, band_volumes=None, concert_mode=False):
        self.pulse_phase += 0.15
        if band_volumes is not None:
            bass, mid, treble = band_volumes
        else:
            bass = volume_level * 0.95
            mid = volume_level * 1.0
            treble = volume_level * 1.05

        if concert_mode:
            colors = [(0, 200, 255), (255, 0, 200), (0, 255, 100)]
            glow_colors = [(0, 80, 120), (120, 0, 80), (0, 120, 40)]
        elif love_mode:
            colors = [(180, 105, 255), (200, 130, 255), (230, 160, 255)]
            glow_colors = [(120, 20, 180), (130, 30, 190), (150, 50, 210)]
        else:
            colors = [(255, 255, 0), (0, 255, 128), (255, 0, 255)]
            glow_colors = [(120, 120, 0), (0, 120, 60), (120, 0, 120)]

        if hand_x is None or hand_y is None:
            hand_x, hand_y = (self.width // 2, self.height // 2)

        if self.current_type == 'circle':
            self._draw_circle_wave_multi(frame, hand_x, hand_y, bass, mid, treble, colors, glow_colors)
        elif self.current_type == 'wave':
            self._draw_oscilloscope_multi(frame, bass, mid, treble, colors, glow_colors)
        elif self.current_type == 'bar':
            self._draw_spectrum_bars_multi(frame, bass, mid, treble, colors, glow_colors)
        elif self.current_type == 'concert':
            self._draw_concert_visualizer(frame, hand_x, hand_y, bass, mid, treble, colors, glow_colors)

    def _draw_single_ring(self, frame, cx, cy, volume, base_radius, max_amp, phase_shift, color, glow_color, num_points, wave_freq):
        radius = base_radius + int(volume * 20)
        amplitude = 8 + int(volume * max_amp)
        points = []
        glow_points = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            wave = math.sin(angle * wave_freq + self.pulse_phase + phase_shift) * math.cos(angle * 3)
            r = radius + wave * amplitude
            x = int(cx + r * math.cos(angle))
            y = int(cy + r * math.sin(angle))
            points.append([x, y])
            rg = r + 4
            xg = int(cx + rg * math.cos(angle))
            yg = int(cy + rg * math.sin(angle))
            glow_points.append([xg, yg])
        pts = np.array(points, dtype=np.int32)
        pts_glow = np.array(glow_points, dtype=np.int32)
        cv2.polylines(frame, [pts_glow], True, glow_color, 4, cv2.LINE_AA)
        cv2.polylines(frame, [pts], True, color, 2, cv2.LINE_AA)

    def _draw_circle_wave_multi(self, frame, cx, cy, bass, mid, treble, colors, glow_colors):
        self._draw_single_ring(frame, cx, cy, bass, base_radius=30, max_amp=20, phase_shift=0.0, color=colors[0], glow_color=glow_colors[0], num_points=48, wave_freq=6)
        self._draw_single_ring(frame, cx, cy, mid, base_radius=55, max_amp=35, phase_shift=1.5, color=colors[1], glow_color=glow_colors[1], num_points=64, wave_freq=8)
        self._draw_single_ring(frame, cx, cy, treble, base_radius=80, max_amp=50, phase_shift=3.0, color=colors[2], glow_color=glow_colors[2], num_points=80, wave_freq=10)
        cv2.circle(frame, (cx, cy), max(2, int(bass * 10)), colors[0], -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), max(5, int(bass * 15)), glow_colors[0], 2, cv2.LINE_AA)

    def _draw_single_oscilloscope_line(self, frame, volume, base_y, color, glow_color, thickness, wave_speed, freq_mul):
        num_points = 80
        step = self.width // (num_points - 1)
        max_amplitude = 8 + int(volume * 60)
        points = []
        for i in range(num_points):
            x = i * step
            freq1 = math.sin(i * freq_mul + self.pulse_phase * wave_speed * 10)
            freq2 = math.cos(i * freq_mul * 2 - self.pulse_phase * wave_speed * 5)
            y = base_y + int((freq1 + freq2) * 0.5 * max_amplitude)
            points.append([x, y])
        pts = np.array(points, dtype=np.int32)
        cv2.polylines(frame, [pts], False, glow_color, thickness + 3, cv2.LINE_AA)
        cv2.polylines(frame, [pts], False, color, thickness, cv2.LINE_AA)
        cv2.polylines(frame, [pts], False, (255, 255, 255), 1, cv2.LINE_AA)

    def _draw_oscilloscope_multi(self, frame, bass, mid, treble, colors, glow_colors):
        self._draw_single_oscilloscope_line(frame, bass, base_y=self.height - 100, color=colors[0], glow_color=glow_colors[0], thickness=3, wave_speed=0.08, freq_mul=0.1)
        self._draw_single_oscilloscope_line(frame, mid, base_y=self.height - 80, color=colors[1], glow_color=glow_colors[1], thickness=2, wave_speed=0.15, freq_mul=0.25)
        self._draw_single_oscilloscope_line(frame, treble, base_y=self.height - 60, color=colors[2], glow_color=glow_colors[2], thickness=1, wave_speed=0.25, freq_mul=0.45)

    def _draw_spectrum_bars_multi(self, frame, bass, mid, treble, colors, glow_colors):
        num_bars = 24
        bar_width = 16
        gap = 8
        start_x = (self.width - (num_bars * (bar_width + gap) - gap)) // 2
        base_y = self.height - 60
        for i in range(num_bars):
            if i < 8:
                volume = bass
                color = colors[0]
                glow_color = glow_colors[0]
                bar_phase = i * 0.6 + self.pulse_phase * 1.5
            elif i < 16:
                volume = mid
                color = colors[1]
                glow_color = glow_colors[1]
                bar_phase = i * 0.4 + self.pulse_phase * 1.0
            else:
                volume = treble
                color = colors[2]
                glow_color = glow_colors[2]
                bar_phase = i * 0.8 + self.pulse_phase * 2.2
            max_h = 15 + int(volume * 140)
            h = int((math.sin(bar_phase) * 0.35 + 0.65) * max_h)
            h = max(4, h)
            x1 = start_x + i * (bar_width + gap)
            y1 = base_y - h
            x2 = x1 + bar_width
            y2 = base_y
            cv2.rectangle(frame, (x1 - 2, y1 - 2), (x2 + 2, y2), glow_color, -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)
            cv2.rectangle(frame, (x1, y1), (x2, y1 + 3), (255, 255, 255), -1)

    def _draw_concert_visualizer(self, frame, cx, cy, bass, mid, treble, colors, glow_colors):
        """Draw a dramatic concert-style visualizer combining rings + mirrored bars + pulses."""
        h, w = frame.shape[:2]

        # Inner pulsing circle
        inner_r = int(20 + bass * 40)
        pulse = abs(math.sin(self.pulse_phase * 2))
        inner_color = tuple(int(c * (0.5 + 0.5 * pulse)) for c in colors[0])
        cv2.circle(frame, (cx, cy), inner_r, inner_color, -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), inner_r + 3, glow_colors[0], 2, cv2.LINE_AA)

        # Multi-ring with faster animation
        self._draw_single_ring(frame, cx, cy, bass, base_radius=35, max_amp=25, phase_shift=0.0, color=colors[0], glow_color=glow_colors[0], num_points=60, wave_freq=8)
        self._draw_single_ring(frame, cx, cy, mid, base_radius=65, max_amp=40, phase_shift=2.0, color=colors[1], glow_color=glow_colors[1], num_points=80, wave_freq=12)
        self._draw_single_ring(frame, cx, cy, treble, base_radius=95, max_amp=55, phase_shift=4.0, color=colors[2], glow_color=glow_colors[2], num_points=96, wave_freq=16)

        # Bottom mirrored bars
        num_bars = 32
        bar_width = 12
        gap = 5
        total_w = num_bars * (bar_width + gap) - gap
        start_x = (w - total_w) // 2
        base_y = h - 40

        for i in range(num_bars):
            ratio = i / num_bars
            if ratio < 0.33:
                volume = bass
                color = colors[0]
            elif ratio < 0.66:
                volume = mid
                color = colors[1]
            else:
                volume = treble
                color = colors[2]

            bar_phase = i * 0.5 + self.pulse_phase * 2.0
            max_h = 10 + int(volume * 100)
            bar_h = int((math.sin(bar_phase) * 0.3 + 0.7) * max_h)
            bar_h = max(3, bar_h)

            x1 = start_x + i * (bar_width + gap)
            x2 = x1 + bar_width

            # Bottom bars
            cv2.rectangle(frame, (x1, base_y - bar_h), (x2, base_y), color, -1)
            # Top reflected (smaller)
            reflected_h = int(bar_h * 0.3)
            cv2.rectangle(frame, (x1, base_y), (x2, base_y + reflected_h),
                          tuple(int(c * 0.3) for c in color), -1)

        # Radiating lines from center on beats
        if bass > 0.5:
            num_rays = 12
            for i in range(num_rays):
                angle = (2 * math.pi * i / num_rays) + self.pulse_phase
                length = int(30 + bass * 80)
                ex = int(cx + length * math.cos(angle))
                ey = int(cy + length * math.sin(angle))
                ray_alpha = bass * 0.5
                ray_color = tuple(int(c * ray_alpha) for c in colors[0])
                cv2.line(frame, (cx, cy), (ex, ey), ray_color, 1, cv2.LINE_AA)
