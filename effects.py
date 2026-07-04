import os
import cv2
import math
import time
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont


class Particle:

    def __init__(self, x, y, color=None, vx=None, vy=None, lifetime=1.0, size=3, shape='circle'):
        self.x = float(x)
        self.y = float(y)
        self.color = color or (0, 255, 255)
        self.vx = vx if vx is not None else random.uniform(-3, 3)
        self.vy = vy if vy is not None else random.uniform(-5, -1)
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.size = size
        self.shape = shape
        self.alive = True
        self.rotation = random.uniform(0, 360)
        self.rot_speed = random.uniform(-5, 5)

    def update(self, dt):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.5 * dt * 60
        self.rotation += self.rot_speed
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    @property
    def alpha(self):
        return max(0.0, self.lifetime / self.max_lifetime)

    def draw(self, frame):
        if not self.alive:
            return
        a = self.alpha
        if a < 0.05:
            return
        color = tuple(int(c * a) for c in self.color)
        pos = (int(self.x), int(self.y))
        s = max(1, int(self.size * a))
        if self.shape == 'circle':
            cv2.circle(frame, pos, s, color, -1, cv2.LINE_AA)
        elif self.shape == 'heart':
            self._draw_mini_heart(frame, pos, s, color)
        elif self.shape == 'spark':
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                end = (pos[0] + dx * s * 2, pos[1] + dy * s * 2)
                cv2.line(frame, pos, end, color, 1, cv2.LINE_AA)
        elif self.shape == 'confetti':
            self._draw_confetti(frame, pos, s, color, a)
        elif self.shape == 'star':
            self._draw_star(frame, pos, s, color, a)

    def _draw_mini_heart(self, frame, center, size, color):
        cx, cy = center
        s = max(2, size)
        cv2.circle(frame, (cx - s // 2, cy - s // 3), s // 2, color, -1, cv2.LINE_AA)
        cv2.circle(frame, (cx + s // 2, cy - s // 3), s // 2, color, -1, cv2.LINE_AA)
        pts = np.array([[cx - s, cy - s // 3], [cx + s, cy - s // 3], [cx, cy + s]], dtype=np.int32)
        cv2.fillPoly(frame, [pts], color, cv2.LINE_AA)

    def _draw_confetti(self, frame, pos, s, color, alpha):
        """Draw a small rotating rectangle (confetti piece)."""
        w = max(2, s * 2)
        h = max(1, s)
        angle = self.rotation
        rect_pts = cv2.boxPoints(((pos[0], pos[1]), (w, h), angle))
        rect_pts = np.int32(rect_pts)
        cv2.fillConvexPoly(frame, rect_pts, color, cv2.LINE_AA)

    def _draw_star(self, frame, pos, s, color, alpha):
        """Draw a small star/sparkle."""
        cx, cy = pos
        s = max(2, s)
        # Four-pointed star
        pts = [
            (cx, cy - s * 2), (cx - s // 2, cy - s // 2),
            (cx - s * 2, cy), (cx - s // 2, cy + s // 2),
            (cx, cy + s * 2), (cx + s // 2, cy + s // 2),
            (cx + s * 2, cy), (cx + s // 2, cy - s // 2),
        ]
        pts_arr = np.array(pts, dtype=np.int32)
        cv2.fillConvexPoly(frame, pts_arr, color, cv2.LINE_AA)


class ParticleSystem:

    def __init__(self, max_particles=400):
        self.particles = []
        self.max_particles = max_particles

    def emit(self, x, y, count=10, color=None, shape='circle', spread=3.0):
        for _ in range(count):
            vx = random.uniform(-spread, spread)
            vy = random.uniform(-spread * 1.5, -spread * 0.3)
            size = random.randint(2, 5)
            lifetime = random.uniform(0.5, 1.5)
            p = Particle(x, y, color=color, vx=vx, vy=vy, lifetime=lifetime, size=size, shape=shape)
            self.particles.append(p)
        while len(self.particles) > self.max_particles:
            self.particles.pop(0)

    def emit_heart_burst(self, x, y, count=15):
        colors = [(180, 105, 255), (147, 20, 255), (128, 128, 255), (200, 150, 255)]
        for _ in range(count):
            color = random.choice(colors)
            self.emit(x, y, count=1, color=color, shape='heart', spread=4.0)

    def emit_confetti(self, width, count=5):
        """Emit confetti from top of screen."""
        confetti_colors = [
            (0, 255, 255), (255, 0, 255), (0, 255, 128),
            (255, 255, 0), (180, 105, 255), (0, 200, 255),
            (255, 128, 0), (128, 255, 128), (255, 100, 100),
        ]
        for _ in range(count):
            x = random.randint(0, width)
            color = random.choice(confetti_colors)
            vx = random.uniform(-2, 2)
            vy = random.uniform(1, 4)
            lifetime = random.uniform(2.0, 4.0)
            size = random.randint(3, 7)
            p = Particle(x, -10, color=color, vx=vx, vy=vy, lifetime=lifetime, size=size, shape='confetti')
            p.vy = random.uniform(1.5, 3.5)  # override gravity direction (fall down)
            self.particles.append(p)
        while len(self.particles) > self.max_particles:
            self.particles.pop(0)

    def emit_sparkle_burst(self, x, y, count=8):
        """Emit sparkle/star burst for concert effects."""
        sparkle_colors = [(255, 255, 255), (255, 255, 200), (200, 255, 255), (255, 200, 255)]
        for _ in range(count):
            color = random.choice(sparkle_colors)
            vx = random.uniform(-6, 6)
            vy = random.uniform(-8, -2)
            lifetime = random.uniform(0.3, 0.8)
            size = random.randint(2, 4)
            p = Particle(x, y, color=color, vx=vx, vy=vy, lifetime=lifetime, size=size, shape='star')
            self.particles.append(p)
        while len(self.particles) > self.max_particles:
            self.particles.pop(0)

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
            # Override gravity for confetti (slow fall)
            if p.shape == 'confetti':
                p.vy = min(p.vy, 3.5)
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, frame):
        for p in self.particles:
            p.draw(frame)


class HandTrail:

    def __init__(self, max_points=25):
        self.trails = {}
        self.max_points = max_points
        self.trail_lifetime = 0.4

    def add_point(self, hand_index, x, y):
        if hand_index not in self.trails:
            self.trails[hand_index] = []
        self.trails[hand_index].append((x, y, time.time()))
        if len(self.trails[hand_index]) > self.max_points:
            self.trails[hand_index].pop(0)

    def clear(self, hand_index=None):
        if hand_index is not None:
            self.trails.pop(hand_index, None)
        else:
            self.trails.clear()

    def draw(self, frame, love_mode=False, concert_mode=False):
        now = time.time()
        if concert_mode:
            colors = [(0, 255, 255), (255, 0, 255)]
            trail_glow = True
        elif love_mode:
            colors = [(180, 105, 255), (147, 20, 255)]
            trail_glow = False
        else:
            colors = [(0, 255, 255), (255, 0, 255)]
            trail_glow = False

        for hand_idx, trail in self.trails.items():
            trail[:] = [(x, y, t) for x, y, t in trail if now - t < self.trail_lifetime]
            if len(trail) < 2:
                continue
            base_color = colors[hand_idx % 2]
            for i in range(1, len(trail)):
                x1, y1, t1 = trail[i - 1]
                x2, y2, t2 = trail[i]
                age = now - t2
                alpha = max(0.0, 1.0 - age / self.trail_lifetime)
                color = tuple(int(c * alpha) for c in base_color)
                thickness = max(1, int(4 * alpha))
                if trail_glow:
                    # Extra glow for concert mode
                    glow_color = tuple(int(c * alpha * 0.4) for c in base_color)
                    cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), glow_color, thickness + 6, cv2.LINE_AA)
                cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, thickness + 2, cv2.LINE_AA)
                cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 255, 255), 1, cv2.LINE_AA)


class EffectsManager:
    LYRICS = []

    @staticmethod
    def _parse_lrc_file(lrc_path):
        """Parse a .lrc file and return a list of (start_time, text) tuples."""
        import re
        lyrics = []
        try:
            with open(lrc_path, 'r', encoding='utf-8') as f:
                content = f.read()
            pattern = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\]\s*(.*?)(?=\[|\Z)', re.DOTALL)
            matches = pattern.findall(content)
            raw_entries = []
            for m, s, cs, text in matches:
                minutes = int(m)
                seconds = int(s)
                centiseconds = int(cs)
                if len(cs) == 2:
                    frac = centiseconds / 100.0
                else:
                    frac = centiseconds / 1000.0
                timestamp = minutes * 60 + seconds + frac
                clean_text = ' '.join(text.strip().split())
                if clean_text:
                    raw_entries.append((timestamp, clean_text))
            for ts, text in raw_entries:
                if ts >= 1.0:
                    lyrics.append((ts, text))
        except Exception as e:
            print(f'[WARN] Gagal membaca file LRC: {e}')
        return lyrics

    def __init__(self):
        self.particles = ParticleSystem()
        self.trail = HandTrail()
        self.love_mode = False
        self.concert_mode = False
        self._love_tint_alpha = 0.0
        self._concert_tint_alpha = 0.0
        self.lyric_font_chin = None
        self.lyric_font_ind = None
        self.glitch_level = 0.0
        self.chromatic_offset = 0

        # Concert mode effects state
        self._strobe_active = False
        self._strobe_timer = 0.0
        self._strobe_flash = False
        self._spotlight_angles = [random.uniform(0, math.pi * 2) for _ in range(4)]
        self._spotlight_speeds = [random.uniform(0.3, 0.8) for _ in range(4)]
        self._spotlight_colors = [(255, 50, 50), (50, 50, 255), (50, 255, 50), (255, 255, 50)]
        self._laser_phase = 0.0
        self._bass_pulse = 0.0
        self._confetti_timer = 0.0

        # Find bilingual LRC paths in assets/
        chin_path = None
        ind_path = None
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
        if os.path.exists(assets_dir):
            for f in os.listdir(assets_dir):
                f_lower = f.lower()
                if f_lower.endswith('chin.lrc'):
                    chin_path = os.path.join(assets_dir, f)
                elif f_lower.endswith('.lrc') and not f_lower.endswith('chin.lrc'):
                    ind_path = os.path.join(assets_dir, f)

        # Load and align lyrics
        self.LYRICS = []
        if chin_path or ind_path:
            chin_entries = self._parse_lrc_file(chin_path) if chin_path else []
            ind_entries = self._parse_lrc_file(ind_path) if ind_path else []
            combined = []
            used_ind = set()
            for ts_chin, text_chin in chin_entries:
                closest_ind = None
                closest_diff = 1.0
                closest_idx = -1
                for idx, (ts_ind, text_ind) in enumerate(ind_entries):
                    diff = abs(ts_chin - ts_ind)
                    if diff < closest_diff:
                        closest_diff = diff
                        closest_ind = text_ind
                        closest_idx = idx
                if closest_idx != -1:
                    used_ind.add(closest_idx)
                    combined.append((ts_chin, text_chin, closest_ind))
                else:
                    combined.append((ts_chin, text_chin, ""))
            for idx, (ts_ind, text_ind) in enumerate(ind_entries):
                if idx not in used_ind:
                    combined.append((ts_ind, "", text_ind))
            combined.sort(key=lambda x: x[0])
            for i, (start, chin_text, ind_text) in enumerate(combined):
                if i + 1 < len(combined):
                    end = combined[i+1][0]
                else:
                    end = start + 10.0
                self.LYRICS.append((start, end, chin_text, ind_text))
            print(f'[OK] Lirik bilingual dimuat: {len(self.LYRICS)} baris')
        else:
            print('[WARN] Tidak ditemukan file .lrc di assets/')

    def set_love_mode(self, active):
        self.love_mode = active

    def set_concert_mode(self, active):
        self.concert_mode = active

    def trigger_strobe(self):
        """Trigger strobe flash effect (e.g. from ROCK gesture)."""
        self._strobe_active = True
        self._strobe_timer = time.time()

    def update(self, dt, volume_level=0.0, fist_active=False):
        self.particles.update(dt)

        # Love mode tint
        target_tint = 1.0 if self.love_mode else 0.0
        self._love_tint_alpha += (target_tint - self._love_tint_alpha) * 0.05

        # Concert mode tint
        target_concert = 1.0 if self.concert_mode else 0.0
        self._concert_tint_alpha += (target_concert - self._concert_tint_alpha) * 0.08

        # Glitch level
        self.glitch_level = volume_level * 0.4
        if fist_active:
            self.glitch_level = 0.95
            self.chromatic_offset = random.randint(8, 20)
        elif self.glitch_level > 0.15:
            self.chromatic_offset = random.randint(2, 8)
        else:
            self.chromatic_offset = 0

        # Love mode ambient hearts
        if self.love_mode and random.random() < 0.1:
            x = random.randint(50, 590)
            y = random.randint(50, 430)
            self.particles.emit(x, y, count=1, color=(180, 105, 255), shape='heart', spread=1.5)

        # Concert mode effects
        if self.concert_mode:
            self._laser_phase += dt * 2.0
            self._bass_pulse = volume_level

            # Spotlight rotation
            for i in range(len(self._spotlight_angles)):
                self._spotlight_angles[i] += self._spotlight_speeds[i] * dt

            # Confetti rain
            self._confetti_timer += dt
            if self._confetti_timer > 0.08:
                self._confetti_timer = 0
                self.particles.emit_confetti(640, count=3)

            # Beat-synced sparkle bursts
            if volume_level > 0.6 and random.random() < 0.3:
                x = random.randint(50, 590)
                y = random.randint(50, 350)
                self.particles.emit_sparkle_burst(x, y, count=4)

        # Strobe effect timer
        if self._strobe_active:
            elapsed = time.time() - self._strobe_timer
            if elapsed > 1.5:
                self._strobe_active = False
                self._strobe_flash = False

    def draw(self, frame):
        h, w = frame.shape[:2]
        self.trail.draw(frame, love_mode=self.love_mode, concert_mode=self.concert_mode)
        self.particles.draw(frame)

        # Love mode tint
        if self._love_tint_alpha > 0.01:
            overlay = frame.copy()
            tint = np.full_like(frame, (100, 20, 80), dtype=np.uint8)
            cv2.addWeighted(tint, self._love_tint_alpha * 0.15, overlay, 1.0, 0, overlay)
            frame[:] = overlay

        # Concert mode effects
        if self._concert_tint_alpha > 0.01:
            self._draw_spotlights(frame)
            self._draw_laser_beams(frame)
            self._draw_bass_vignette(frame)

        # Strobe flash
        if self._strobe_active:
            elapsed = time.time() - self._strobe_timer
            if int(elapsed * 12) % 2 == 0:
                flash_alpha = max(0.0, 0.5 * (1.0 - elapsed / 1.5))
                if flash_alpha > 0.01:
                    white = np.full_like(frame, 255, dtype=np.uint8)
                    cv2.addWeighted(white, flash_alpha, frame, 1.0 - flash_alpha * 0.5, 0, frame)

    def _draw_spotlights(self, frame):
        """Draw rotating concert spotlights from top of screen."""
        h, w = frame.shape[:2]
        overlay = frame.copy()

        num_spots = len(self._spotlight_angles)
        # Spotlights originate from top corners and top center
        origins = [
            (0, 0), (w, 0), (w // 2, 0), (w // 4, 0)
        ]

        for i in range(num_spots):
            angle = self._spotlight_angles[i]
            color = self._spotlight_colors[i]
            ox, oy = origins[i % len(origins)]

            # Calculate beam endpoint
            beam_length = max(w, h) * 1.2
            swing_angle = math.sin(angle) * 0.6 + math.pi / 2  # Swing around downward
            ex = int(ox + beam_length * math.cos(swing_angle))
            ey = int(oy + beam_length * math.sin(swing_angle))

            # Draw beam as a filled triangle (cone of light)
            spread = 35  # beam width at the end
            perp_x = int(spread * math.cos(swing_angle + math.pi / 2))
            perp_y = int(spread * math.sin(swing_angle + math.pi / 2))

            pts = np.array([
                [ox, oy],
                [ex + perp_x, ey + perp_y],
                [ex - perp_x, ey - perp_y]
            ], dtype=np.int32)

            # Draw with transparency
            beam_color = tuple(int(c * 0.3 * self._concert_tint_alpha) for c in color)
            cv2.fillPoly(overlay, [pts], beam_color, cv2.LINE_AA)

            # Bright core line
            core_color = tuple(int(c * 0.6 * self._concert_tint_alpha) for c in color)
            cv2.line(overlay, (ox, oy), (ex, ey), core_color, 2, cv2.LINE_AA)

        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)

    def _draw_laser_beams(self, frame):
        """Draw scanning laser beams from center."""
        h, w = frame.shape[:2]
        cx, cy = w // 2, 30  # Lasers from top center

        num_lasers = 6
        base_phase = self._laser_phase
        laser_colors = [
            (0, 255, 0), (0, 200, 255), (255, 0, 200),
            (0, 255, 128), (255, 255, 0), (200, 0, 255)
        ]

        alpha = self._concert_tint_alpha
        if alpha < 0.05:
            return

        for i in range(num_lasers):
            angle = base_phase + i * (math.pi * 2 / num_lasers)
            swing = math.sin(angle) * 0.8  # -0.8 to 0.8 rad swing
            beam_angle = math.pi / 2 + swing  # centered downward

            length = max(w, h)
            ex = int(cx + length * math.cos(beam_angle))
            ey = int(cy + length * math.sin(beam_angle))

            color = tuple(int(c * 0.25 * alpha) for c in laser_colors[i % len(laser_colors)])
            cv2.line(frame, (cx, cy), (ex, ey), color, 1, cv2.LINE_AA)

            # Slight glow
            glow_color = tuple(int(c * 0.1 * alpha) for c in laser_colors[i % len(laser_colors)])
            cv2.line(frame, (cx, cy), (ex, ey), glow_color, 3, cv2.LINE_AA)

    def _draw_bass_vignette(self, frame):
        """Draw pulsing vignette on bass hits."""
        if self._bass_pulse < 0.3:
            return
        h, w = frame.shape[:2]
        intensity = min(1.0, self._bass_pulse * 1.5) * self._concert_tint_alpha

        # Create radial gradient vignette
        overlay = frame.copy()
        border = int(40 * intensity)
        if border < 5:
            return

        # Top/bottom vignette bars
        vignette_color = (20, 0, 40)
        cv2.rectangle(overlay, (0, 0), (w, border), vignette_color, -1)
        cv2.rectangle(overlay, (0, h - border), (w, h), vignette_color, -1)
        cv2.rectangle(overlay, (0, 0), (border, h), vignette_color, -1)
        cv2.rectangle(overlay, (w - border, 0), (w, h), vignette_color, -1)

        blend = 0.3 * intensity
        cv2.addWeighted(overlay, blend, frame, 1.0 - blend, 0, frame)

    def apply_screen_glitches(self, frame):
        h, w = frame.shape[:2]
        if self.glitch_level < 0.05:
            return
        shake = int(self.glitch_level * 15)
        if shake > 0:
            dx = random.randint(-shake, shake)
            dy = random.randint(-shake, shake)
            M = np.float32([[1, 0, dx], [0, 1, dy]])
            frame[:] = cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REFLECT)
        num_slices = int(self.glitch_level * 12)
        for _ in range(num_slices):
            slice_y = random.randint(0, h - 30)
            slice_h = random.randint(10, 40)
            shift_x = random.randint(-20, 20)
            M = np.float32([[1, 0, shift_x], [0, 1, 0]])
            slice_part = frame[slice_y:slice_y + slice_h, 0:w]
            actual_h = slice_part.shape[0]
            if actual_h > 0:
                frame[slice_y:slice_y + actual_h, 0:w] = cv2.warpAffine(slice_part, M, (w, actual_h), borderMode=cv2.BORDER_REFLECT)
        shift = self.chromatic_offset
        if shift > 1:
            r_chan = frame[:, :, 2]
            b_chan = frame[:, :, 0]
            shifted_r = np.roll(r_chan, -shift, axis=1)
            shifted_b = np.roll(b_chan, shift, axis=1)
            frame[:, :, 2] = shifted_r
            frame[:, :, 0] = shifted_b
        if self.glitch_level > 0.6:
            for _ in range(random.randint(1, 4)):
                rx = random.randint(0, w - 80)
                ry = random.randint(0, h - 20)
                rw = random.randint(40, 150)
                rh = random.randint(2, 8)
                color = random.choice([(255, 255, 255), (0, 0, 0), (255, 0, 128)])
                cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), color, -1)

    def draw_lyrics(self, frame, song_time):
        h, w = frame.shape[:2]
        current_chin = ''
        current_ind = ''
        for start, end, chin_text, ind_text in self.LYRICS:
            if start <= song_time < end:
                current_chin = chin_text
                current_ind = ind_text
                break
        if not current_chin and not current_ind:
            return

        shake = int(self.glitch_level * 10)
        ly_chin = h - 125
        ly_ind = h - 95
        if shake > 0:
            dy = random.randint(-shake, shake)
            ly_chin += dy
            ly_ind += dy

        if self.concert_mode:
            pulse = abs(math.sin(time.time() * 3.0))
            color_chin = (int(200 + 55 * pulse), int(200 + 55 * pulse), 255)
            color_ind = (int(150 + 105 * pulse), 255, int(150 + 105 * pulse))
        elif self.love_mode:
            color_chin = (180, 105, 255)
            color_ind = (230, 160, 255)
        else:
            color_chin = (0, 255, 255)
            color_ind = (255, 255, 0)

        shadow_color = (0, 0, 0)
        if self.lyric_font_chin is None or self.lyric_font_ind is None:
            font_paths = [
                'C:\\Windows\\Fonts\\msyh.ttc',
                'C:\\Windows\\Fonts\\simhei.ttf',
                'C:\\Windows\\Fonts\\msyhbd.ttc',
                'C:\\Windows\\Fonts\\simsun.ttc'
            ]
            for path in font_paths:
                if os.path.exists(path):
                    try:
                        self.lyric_font_chin = ImageFont.truetype(path, 16)
                        self.lyric_font_ind = ImageFont.truetype(path, 13)
                        break
                    except Exception:
                        pass

        if self.lyric_font_chin is not None and self.lyric_font_ind is not None:
            try:
                img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(img_rgb)
                draw = ImageDraw.Draw(pil_img)
                text_w_c = 0
                text_w_i = 0

                if current_chin:
                    bbox_c = self.lyric_font_chin.getbbox(current_chin)
                    text_w_c = bbox_c[2] - bbox_c[0]
                    lx_c = w // 2 - text_w_c // 2
                    if shake > 0:
                        lx_c += random.randint(-shake, shake)
                    if self.concert_mode:
                        glow_rgb = (100, 100, 255)
                        for gx, gy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            draw.text((lx_c + gx, ly_chin + gy), current_chin, font=self.lyric_font_chin, fill=glow_rgb)
                    draw.text((lx_c + 2, ly_chin + 2), current_chin, font=self.lyric_font_chin, fill=shadow_color)
                    color_rgb_c = (color_chin[2], color_chin[1], color_chin[0])
                    draw.text((lx_c, ly_chin), current_chin, font=self.lyric_font_chin, fill=color_rgb_c)

                if current_ind:
                    bbox_i = self.lyric_font_ind.getbbox(current_ind)
                    text_w_i = bbox_i[2] - bbox_i[0]
                    lx_i = w // 2 - text_w_i // 2
                    if shake > 0:
                        lx_i += random.randint(-shake, shake)
                    if self.concert_mode:
                        glow_rgb = (100, 255, 100)
                        for gx, gy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            draw.text((lx_i + gx, ly_ind + gy), current_ind, font=self.lyric_font_ind, fill=glow_rgb)
                    draw.text((lx_i + 2, ly_ind + 2), current_ind, font=self.lyric_font_ind, fill=shadow_color)
                    color_rgb_i = (color_ind[2], color_ind[1], color_ind[0])
                    draw.text((lx_i, ly_ind), current_ind, font=self.lyric_font_ind, fill=color_rgb_i)

                frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

                if current_chin or current_ind:
                    max_w = max(text_w_c, text_w_i)
                    cv2.line(frame, (w // 2 - max_w // 2, ly_ind + 22), (w // 2 + max_w // 2, ly_ind + 22), color_ind, 1, cv2.LINE_AA)
                return
            except Exception as e:
                print(f'[WARN] Gagal menggambar dengan PIL: {e}')
                pass

        # Fallback to OpenCV putText
        text_w_c = 0
        text_w_i = 0
        if current_chin:
            lx_c = w // 2 - len(current_chin) * 5
            if shake > 0:
                lx_c += random.randint(-shake, shake)
            cv2.putText(frame, current_chin, (lx_c + 2, ly_chin + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, shadow_color, 2, cv2.LINE_AA)
            cv2.putText(frame, current_chin, (lx_c, ly_chin), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color_chin, 1, cv2.LINE_AA)
            text_w_c = len(current_chin) * 9

        if current_ind:
            lx_i = w // 2 - len(current_ind) * 4
            if shake > 0:
                lx_i += random.randint(-shake, shake)
            cv2.putText(frame, current_ind, (lx_i + 2, ly_ind + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.38, shadow_color, 2, cv2.LINE_AA)
            cv2.putText(frame, current_ind, (lx_i, ly_ind), cv2.FONT_HERSHEY_SIMPLEX, 0.38, color_ind, 1, cv2.LINE_AA)
            text_w_i = len(current_ind) * 8

        if current_chin or current_ind:
            line_w = max(text_w_c, text_w_i)
            cv2.line(frame, (w // 2 - line_w // 2, ly_ind + 12), (w // 2 + line_w // 2, ly_ind + 12), color_ind, 1, cv2.LINE_AA)

    def draw_concert_hud(self, frame):
        """Draw concert mode indicator on screen."""
        if self._concert_tint_alpha < 0.01:
            return
        h, w = frame.shape[:2]
        pulse = abs(math.sin(time.time() * 4.0))
        alpha = self._concert_tint_alpha

        # Animated "CONCERT MODE" text
        text = '[ CONCERT MODE ]'
        color = (
            int((50 + 205 * pulse) * alpha),
            int((200 * pulse) * alpha),
            int(255 * alpha)
        )
        # Position at top center
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        tx = w // 2 - text_size[0] // 2
        ty = 25
        cv2.putText(frame, text, (tx + 1, ty + 1), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)
