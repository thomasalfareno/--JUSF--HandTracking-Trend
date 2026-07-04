import os
import sys
import cv2
import time
import math
import random
import numpy as np
from hand_tracker import HandTracker
from gestures import GestureRecognizer
from visualizer import Visualizer
from music import MusicPlayer
from effects import EffectsManager

WINDOW_NAME = 'Gesture Glitch & Audio Visualizer'
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
AUDIO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'audio.mp3')

HUD_CYAN = (255, 255, 0)
HUD_MAGENTA = (255, 0, 255)
HUD_GREEN = (0, 255, 128)
HUD_WHITE = (255, 255, 255)
HUD_YELLOW = (0, 255, 255)
HUD_PINK = (180, 105, 255)
HUD_RED = (0, 0, 255)
HUD_ORANGE = (0, 165, 255)
HUD_DIM = (120, 120, 120)
HUD_BG = (15, 15, 15)
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_MONO = cv2.FONT_HERSHEY_PLAIN


def draw_text(frame, text, pos, color=HUD_GREEN, scale=0.5, thickness=1, font=FONT):
    x, y = pos
    cv2.putText(frame, text, (x + 1, y + 1), font, scale, (0, 0, 0), thickness + 1, cv2.LINE_AA)
    cv2.putText(frame, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)


def draw_hud_panel(frame, x, y, w, h, alpha=0.35):
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), HUD_BG, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    cv2.rectangle(frame, (x, y), (x + w, y + h), HUD_DIM, 1)


def draw_volume_bar(frame, x, y, w, h, level, color=HUD_CYAN):
    cv2.rectangle(frame, (x, y), (x + w, y + h), HUD_DIM, 1)
    fill_w = int(w * min(1.0, level))
    if fill_w > 0:
        cv2.rectangle(frame, (x, y), (x + fill_w, y + h), color, -1)


def draw_equalizer_overlay(frame, eq_gains, selected_band, hand_angle, active_hand_present):
    h, w = frame.shape[:2]
    px, py, pw, ph = (190, 110, 270, 210)
    overlay = frame.copy()
    cv2.rectangle(overlay, (px, py), (px + pw, py + ph), (10, 10, 15), -1)
    cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
    cv2.rectangle(frame, (px, py), (px + pw, py + ph), HUD_MAGENTA, 2, cv2.LINE_AA)
    cv2.rectangle(frame, (px - 2, py - 2), (px + pw + 2, py + ph + 2), HUD_DIM, 1)
    draw_text(frame, '[ VIRTUAL EQUALIZER ]', (px + 30, py + 25), HUD_GREEN, 0.45, 2)
    draw_text(frame, '3+3 Fingers: Toggle | ThumbUp: Cycle', (px + 10, py + ph - 12), HUD_DIM, 0.3, 1)
    bands = ['BASS', 'MID', 'TREBLE']
    colors = [HUD_CYAN, HUD_GREEN, HUD_PINK]
    sy = py + 50
    sw = 120
    for i, name in enumerate(bands):
        gain = eq_gains[i]
        is_selected = i == selected_band
        col = colors[i] if is_selected else HUD_DIM
        text_color = HUD_WHITE if is_selected else HUD_DIM
        thickness = 2 if is_selected else 1
        label_text = f'> {name}' if is_selected else f'  {name}'
        draw_text(frame, label_text, (px + 15, sy + i * 40 + 15), col, 0.4, thickness)
        tx = px + 80
        ty = sy + i * 40 + 5
        cv2.rectangle(frame, (tx, ty), (tx + sw, ty + 10), HUD_DIM, 1)
        fill_w = int(sw * (gain / 2.0))
        if fill_w > 0:
            cv2.rectangle(frame, (tx, ty), (tx + fill_w, ty + 10), colors[i] if is_selected else HUD_DIM, -1)
        mx = tx + sw // 2
        cv2.line(frame, (mx, ty - 2), (mx, ty + 12), HUD_WHITE if is_selected else HUD_DIM, 1)
        pct_text = f'{int(gain * 100)}%'
        draw_text(frame, pct_text, (tx + sw + 10, ty + 10), text_color, 0.38, thickness)
    dx = px + pw - 45
    dy = py + ph // 2 - 5
    radius = 28
    cv2.circle(frame, (dx, dy), radius, HUD_DIM, 1, cv2.LINE_AA)
    cv2.circle(frame, (dx, dy), 2, HUD_GREEN if active_hand_present else HUD_DIM, -1)
    if active_hand_present and hand_angle is not None:
        lx = int(dx + radius * math.cos(hand_angle))
        ly = int(dy + radius * math.sin(hand_angle))
        cv2.line(frame, (dx, dy), (lx, ly), HUD_GREEN, 2, cv2.LINE_AA)
        deg = int(math.degrees(hand_angle))
        draw_text(frame, f'{deg}d', (dx - 12, dy + radius + 15), HUD_GREEN, 0.33, 1)
        draw_text(frame, 'DIAL', (dx - 14, dy - radius - 8), HUD_CYAN, 0.35, 1)
    else:
        cv2.line(frame, (dx, dy), (dx, dy - radius), HUD_DIM, 1, cv2.LINE_AA)
        draw_text(frame, 'OFF', (dx - 10, dy + radius + 15), HUD_DIM, 0.33, 1)
        draw_text(frame, 'DIAL', (dx - 14, dy - radius - 8), HUD_DIM, 0.35, 1)


BOOT_MESSAGES = [
    ('[ BOOTING GLITCH ENGINE v3.0 ]', HUD_GREEN),
    ('WEBCAM ACCESS: CONNECTED', HUD_CYAN),
    ('MEDIAPIPE LANDMARKER: ONLINE', HUD_CYAN),
    ('EMA HAND SMOOTHING: ENABLED', HUD_YELLOW),
    ('INITIALIZING CONCERT EFFECTS...', HUD_MAGENTA),
    ('SPOTLIGHT ENGINE: LOADED', HUD_ORANGE),
    ('LASER SYSTEM: READY', HUD_GREEN),
    ('CONFETTI GENERATOR: OK', HUD_PINK),
    ('STROBE CONTROLLER: ARMED', HUD_YELLOW),
    ('SYNCING AUDIO ANALYSIS...', HUD_CYAN),
    ('', HUD_GREEN),
    ('SYSTEM SECURE. ALL SYSTEMS GO.', HUD_GREEN)
]


def draw_boot_sequence(frame, elapsed):
    h, w = frame.shape[:2]
    frame[:] = (frame * 0.25).astype(np.uint8)
    draw_text(frame, 'GLITCH CONCERT SYSTEM v3.0', (w // 2 - 160, 40), HUD_GREEN, 0.6, 2)
    scan_y = int(elapsed * 250 % h)
    cv2.line(frame, (0, scan_y), (w, scan_y), (100, 100, 100), 1)
    start_y = 80
    for i, (msg, color) in enumerate(BOOT_MESSAGES):
        appear_time = i * 0.28
        if elapsed >= appear_time:
            char_elapsed = elapsed - appear_time
            chars_to_show = int(char_elapsed * 50)
            visible_text = msg[:chars_to_show]
            if chars_to_show < len(msg) and int(elapsed * 5) % 2 == 0:
                visible_text += '_'
            draw_text(frame, visible_text, (30, start_y + i * 25), color, 0.4, 1)
    progress = min(1.0, elapsed / (len(BOOT_MESSAGES) * 0.28 + 0.5))
    bar_w = w - 60
    draw_text(frame, 'LOADING MODULES', (30, h - 50), HUD_DIM, 0.4, 1)
    draw_volume_bar(frame, 30, h - 35, bar_w, 8, progress, HUD_GREEN)
    draw_text(frame, f'{int(progress * 100)}%', (bar_w + 35, h - 28), HUD_GREEN, 0.4, 1)
    return progress >= 1.0


def draw_main_hud(frame, gesture_recognizer, visualizer, music_player, volume_level, hands_count, fps, current_gesture, glitch_level, eq_active=False, concert_mode=False):
    h, w = frame.shape[:2]
    mode = gesture_recognizer.mode

    # Top-left telemetry panel
    draw_hud_panel(frame, 5, 5, 235, 175)
    draw_text(frame, '[ TELEMETRY STATUS ]', (12, 22), HUD_GREEN, 0.4, 1)
    draw_text(frame, f'FPS: {fps:.0f}', (12, 42), HUD_CYAN, 0.4, 1)
    draw_text(frame, f'HANDS: {hands_count}', (12, 60), HUD_CYAN, 0.4, 1)
    draw_text(frame, f'GESTURE: {current_gesture}', (12, 78), HUD_YELLOW if current_gesture != 'NONE' else HUD_DIM, 0.4, 1)
    mode_color = HUD_PINK if mode == 'LOVE' else HUD_GREEN if mode == 'BUILD' else HUD_DIM
    draw_text(frame, f'MODE: {mode}', (12, 96), mode_color, 0.5, 1)
    draw_text(frame, f'VISUALIZER: {visualizer.current_type.upper()}', (12, 114), HUD_MAGENTA, 0.4, 1)
    dsp_text = 'EQUALIZER' if eq_active else music_player.filter_mode
    draw_text(frame, f'DSP FILTER: {dsp_text}', (12, 130), HUD_YELLOW, 0.4, 1)
    draw_text(frame, f'MASTER VOL: {music_player.hand_volume * 100:.0f}%', (12, 144), HUD_CYAN, 0.4, 1)
    draw_text(frame, f'GLITCH RATE: {glitch_level * 100:.0f}%', (12, 158), HUD_RED if glitch_level > 0.5 else HUD_CYAN, 0.4, 1)
    concert_text = 'ON' if concert_mode else 'OFF'
    concert_col = HUD_ORANGE if concert_mode else HUD_DIM
    draw_text(frame, f'CONCERT: {concert_text}', (12, 172), concert_col, 0.4, 1)

    # Bottom-left gesture commands panel
    draw_hud_panel(frame, 5, h - 210, 230, 205)
    draw_text(frame, '[ GESTURE COMMANDS ]', (12, h - 193), HUD_GREEN, 0.35, 1)
    controls = [
        ('PINCH', 'Volume (up/down)', HUD_CYAN),
        ('FIST', 'VHS Glitch + Muffled', HUD_RED),
        ('VICTORY', 'Lo-Fi Bitcrush', HUD_MAGENTA),
        ('ROCK', 'Strobe Flash!', HUD_ORANGE),
        ('POINT UP', 'Cycle Waveform', HUD_YELLOW),
        ('OPEN PALM', 'Reset DSP', HUD_GREEN),
        ('HEART', 'Love Mode', HUD_PINK),
        ('3+3 FINGERS', 'Toggle Equalizer', HUD_CYAN),
        ('ALL OPEN', 'Concert Mode!', HUD_ORANGE),
        ('THUMB UP', 'Cycle EQ Band', HUD_GREEN),
        ('THUMB DOWN', 'Reset EQ Default', HUD_YELLOW),
    ]
    for i, (gesture, action, color) in enumerate(controls):
        y_pos = h - 170 + i * 16
        draw_text(frame, f'{gesture}', (12, y_pos), color, 0.3, 1)
        draw_text(frame, f'> {action}', (100, y_pos), HUD_DIM, 0.3, 1)

    # Top-right audio source panel
    draw_hud_panel(frame, w - 215, 5, 210, 75)
    draw_text(frame, '[ AUDIO SOURCE ]', (w - 208, 22), HUD_GREEN, 0.4, 1)
    if music_player.is_loaded:
        status = 'PLAYING' if music_player.is_playing() else 'PAUSED'
        status_color = HUD_GREEN if music_player.is_playing() else HUD_YELLOW
        draw_text(frame, f'STATUS: {status}', (w - 208, 42), status_color, 0.4, 1)
        draw_text(frame, f'TIME: {music_player.get_elapsed_str()}', (w - 208, 58), HUD_CYAN, 0.4, 1)
        bar_color = HUD_ORANGE if concert_mode else HUD_PINK if mode == 'LOVE' else HUD_CYAN
        draw_volume_bar(frame, w - 208, 65, 150, 8, volume_level, bar_color)
    else:
        draw_text(frame, 'NO AUDIO LOADED', (w - 208, 42), HUD_DIM, 0.4, 1)
        draw_text(frame, 'Press M to retry', (w - 208, 58), HUD_DIM, 0.35, 1)

    # Bottom-right terminal panel
    draw_hud_panel(frame, w - 165, h - 85, 160, 80)
    draw_text(frame, '[ TERMINAL ]', (w - 158, h - 68), HUD_GREEN, 0.35, 1)
    keys = [('M', 'Toggle Music'), ('T', 'Cycle Waveform'), ('C', 'Concert Mode'), ('Q', 'Terminate Sys')]
    for i, (key, desc) in enumerate(keys):
        draw_text(frame, f'[{key}] {desc}', (w - 158, h - 50 + i * 16), HUD_DIM, 0.35, 1)

    # Mode banners
    if mode == 'LOVE':
        pulse = int(abs(np.sin(time.time() * 4.0)) * 55) + 200
        love_color = (pulse, 60, min(255, pulse + 40))
        draw_text(frame, 'WARNING: YOU CANNOT BE REPLACED', (w // 2 - 145, h - 25), love_color, 0.5, 2)


def main():
    print('=' * 50)
    print('  GESTURE GLITCH & CONCERT VISUALIZER v3.0')
    print('  Spotlights, Lasers, Confetti & Neon Waveforms')
    print('=' * 50)
    try:
        tracker = HandTracker(max_hands=2)
    except FileNotFoundError as e:
        print(f'\n[CRITICAL ERROR] {e}')
        input('\nTekan ENTER untuk keluar...')
        sys.exit(1)
    gesture_rec = GestureRecognizer()
    visualizer = Visualizer(FRAME_WIDTH, FRAME_HEIGHT)
    music = MusicPlayer()
    effects = EffectsManager()
    audio_loaded = False
    if os.path.exists(AUDIO_PATH):
        audio_loaded = music.load(AUDIO_PATH)
    else:
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
        if os.path.exists(assets_dir):
            for f in os.listdir(assets_dir):
                if f.lower().endswith(('.mp3', '.wav', '.ogg', '.mpeg')):
                    alt_path = os.path.join(assets_dir, f)
                    audio_loaded = music.load(alt_path)
                    if audio_loaded:
                        break
    if not audio_loaded:
        print('[WARN] Tidak ada file audio di assets/ — Visualizer akan menggunakan mode simulasi.')
    print(f'[INFO] Membuka kamera index {CAMERA_INDEX}...')
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print('[ERROR] Tidak dapat membuka kamera!')
        sys.exit(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, FRAME_WIDTH, FRAME_HEIGHT)

    boot_start = time.time()
    boot_done = False
    prev_time = time.time()
    fps = 0.0
    fps_counter = 0
    fps_timer = time.time()
    popup_text = ''
    popup_time = 0
    popup_pos = (0, 0)
    popup_color = HUD_GREEN
    eq_menu_open = False
    eq_selected_band = 0
    eq_gains = [1.0, 1.0, 1.0]
    eq_last_angle = None
    concert_mode = False

    while True:
        ret, frame = cap.read()
        if not ret:
            print('[ERROR] Gagal membaca frame kamera!')
            break
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        now = time.time()
        dt = now - prev_time
        prev_time = now
        dt = min(dt, 0.1)

        fps_counter += 1
        if now - fps_timer >= 1.0:
            fps = fps_counter / (now - fps_timer)
            fps_counter = 0
            fps_timer = now

        # Boot sequence
        if not boot_done:
            boot_elapsed = now - boot_start
            boot_done = draw_boot_sequence(frame, boot_elapsed)
            cv2.imshow(WINDOW_NAME, frame)
            key = cv2.waitKey(1) & 255
            if key in (ord('q'), 27):
                break
            if key == ord(' '):
                boot_done = True
            continue

        frame = (frame * 0.55).astype(np.uint8)

        # Hand tracking
        hands_data = tracker.process(frame)
        hands_count = len(hands_data)
        all_points = []
        for idx, hand_lm in enumerate(hands_data):
            points = tracker.get_pixel_landmarks(hand_lm, w, h, hand_index=idx)
            all_points.append(points)

        # Clear smoothing when no hands detected
        if hands_count == 0:
            tracker.clear_smoothing()

        current_gesture = 'NONE'
        cursor_x, cursor_y = (w // 2, h // 2)
        fist_active = False

        # --- Single hand gesture detection ---
        if len(all_points) >= 1:
            points1 = all_points[0]
            single_gesture = gesture_rec.detect_single_hand(points1)
            cursor_x, cursor_y = gesture_rec.get_cursor_position(points1)
            palm1 = tracker.get_palm_center(points1)
            effects.trail.add_point(0, palm1[0], palm1[1])
            if single_gesture != 'NONE':
                current_gesture = single_gesture

        # --- Two hand gesture detection ---
        if len(all_points) >= 2:
            points2 = all_points[1]
            palm1 = tracker.get_palm_center(all_points[0])
            palm2 = tracker.get_palm_center(points2)
            effects.trail.add_point(1, palm2[0], palm2[1])
            two_gesture = gesture_rec.detect_two_hands(all_points[0], points2, palm1, palm2)
            if two_gesture != 'NONE':
                current_gesture = two_gesture

        # =============================================
        # GESTURE HANDLING
        # =============================================

        # --- THREE_THREE: Toggle Equalizer ---
        if current_gesture == gesture_rec.THREE_THREE:
            eq_menu_open = not eq_menu_open
            if eq_menu_open:
                eq_selected_band = 0
                eq_last_angle = None
                popup_text = 'VIRTUAL EQUALIZER: OPENED'
                popup_color = HUD_GREEN
            else:
                popup_text = 'VIRTUAL EQUALIZER: CLOSED'
                popup_color = HUD_RED
            popup_time = now
            popup_pos = (w // 2, h // 2)

        # --- ALL_OPEN: Toggle Concert Mode ---
        elif current_gesture == gesture_rec.ALL_OPEN:
            concert_mode = not concert_mode
            effects.set_concert_mode(concert_mode)
            if concert_mode:
                popup_text = 'CONCERT MODE: ACTIVATED!'
                popup_color = HUD_ORANGE
                # Switch to concert visualizer
                while visualizer.current_type != 'concert':
                    visualizer.cycle_type()
            else:
                popup_text = 'CONCERT MODE: DEACTIVATED'
                popup_color = HUD_DIM
            popup_time = now
            popup_pos = (w // 2, h // 2)

        # --- ROCK: Strobe Flash ---
        elif current_gesture == gesture_rec.ROCK:
            effects.trigger_strobe()
            popup_text = 'STROBE FLASH!'
            popup_time = now
            popup_pos = (cursor_x, cursor_y)
            popup_color = HUD_ORANGE
            effects.particles.emit_sparkle_burst(cursor_x, cursor_y, count=15)

        # --- EQ Menu open: handle EQ-specific gestures ---
        elif eq_menu_open:
            music.set_filter(music.FILTER_NORMAL)

            # THUMB_UP cycles band
            if current_gesture == gesture_rec.THUMB_UP:
                eq_selected_band = (eq_selected_band + 1) % 3
                bands = ['BASS', 'MID', 'TREBLE']
                popup_text = f'EQ SELECT: {bands[eq_selected_band]}'
                popup_color = HUD_YELLOW
                popup_time = now
                popup_pos = (cursor_x, cursor_y)

            # THUMB_DOWN resets EQ gains to default
            elif current_gesture == gesture_rec.THUMB_DOWN:
                eq_gains = [1.0, 1.0, 1.0]
                music.set_eq_gains(1.0, 1.0, 1.0)
                popup_text = 'EQ RESET TO DEFAULT'
                popup_color = HUD_YELLOW
                popup_time = now
                popup_pos = (cursor_x, cursor_y)

            # Hand rotation for EQ dial
            if len(all_points) >= 1:
                points1 = all_points[0]
                wrist = points1[0]
                mcp = points1[9]
                current_angle = math.atan2(mcp[1] - wrist[1], mcp[0] - wrist[0])
                if eq_last_angle is not None:
                    delta_angle = current_angle - eq_last_angle
                    delta_angle = (delta_angle + math.pi) % (2 * math.pi) - math.pi
                    gain_change = delta_angle * (1.2 / math.pi)
                    eq_gains[eq_selected_band] += gain_change
                    eq_gains[eq_selected_band] = max(0.0, min(2.0, eq_gains[eq_selected_band]))
                    music.set_eq_gains(eq_gains[0], eq_gains[1], eq_gains[2])
                    if abs(gain_change) > 0.005:
                        effects.particles.emit(cursor_x, cursor_y, count=1, color=HUD_GREEN, shape='spark')
                eq_last_angle = current_angle
            else:
                eq_last_angle = None

            if current_gesture not in (gesture_rec.THUMB_UP, gesture_rec.THUMB_DOWN, gesture_rec.THREE_THREE):
                current_gesture = 'EQ TUNE'

        # --- Normal mode gestures ---
        else:
            gesture_rec.update_mode(current_gesture)
            eq_last_angle = None

            if current_gesture == gesture_rec.PINCH:
                height_ratio = 1.0 - cursor_y / h
                music.set_hand_volume(height_ratio)
                music.set_filter(music.FILTER_NORMAL)
                popup_text = f'VOLUME SLIDER: {int(height_ratio * 100)}%'
                popup_time = now
                popup_pos = (cursor_x, cursor_y)
                popup_color = HUD_CYAN
                love_mode = gesture_rec.mode == 'LOVE'
                effects.particles.emit(cursor_x, cursor_y, count=3, color=(180, 105, 255) if love_mode else (255, 255, 0), shape='spark')

            elif current_gesture == gesture_rec.FIST:
                fist_active = True
                music.set_filter(music.FILTER_MUFFLED)
                popup_text = 'DSP FILTER: MUFFLED (LOW-PASS)'
                popup_time = now
                popup_pos = (cursor_x, cursor_y)
                popup_color = HUD_RED

            elif current_gesture == gesture_rec.VICTORY:
                music.set_filter(music.FILTER_LOFI)
                popup_text = 'DSP FILTER: LO-FI (BITCRUSH)'
                popup_time = now
                popup_pos = (cursor_x, cursor_y)
                popup_color = HUD_MAGENTA

            elif current_gesture == gesture_rec.OPEN_PALM:
                music.set_filter(music.FILTER_NORMAL)
                music.set_hand_volume(1.0)
                eq_gains = [1.0, 1.0, 1.0]
                music.set_eq_gains(1.0, 1.0, 1.0)
                popup_text = 'DSP RESET: NORMAL'
                popup_time = now
                popup_pos = (cursor_x, cursor_y)
                popup_color = HUD_GREEN

            elif current_gesture == gesture_rec.POINT_UP:
                visualizer.cycle_type()
                popup_text = f'WAVEFORM: {visualizer.current_type.upper()}'
                popup_time = now
                popup_pos = (cursor_x, cursor_y)
                popup_color = HUD_YELLOW

            elif current_gesture == gesture_rec.HEART:
                love_mode = gesture_rec.mode == 'LOVE'
                popup_text = 'DECRYPTING HEART MEMORIES...' if love_mode else 'DECRYPTION SECURE'
                popup_time = now
                popup_pos = (w // 2, h // 2)
                popup_color = HUD_PINK

            elif current_gesture == gesture_rec.THUMB_UP:
                popup_text = 'THUMB UP!'
                popup_time = now
                popup_pos = (cursor_x, cursor_y)
                popup_color = HUD_GREEN

            elif current_gesture == gesture_rec.THUMB_DOWN:
                popup_text = 'THUMB DOWN!'
                popup_time = now
                popup_pos = (cursor_x, cursor_y)
                popup_color = HUD_RED

        # =============================================
        # UPDATE & DRAW
        # =============================================
        mode = gesture_rec.mode
        love_mode = mode == 'LOVE'
        music.update_dsp(dt)
        volume_level = music.get_volume_level()
        effects.set_love_mode(love_mode)
        effects.update(dt, volume_level, fist_active=fist_active)
        band_vols = music.get_band_volume_levels()

        # Draw visualizer
        if visualizer.current_type == 'circle':
            visualizer.draw(frame, volume_level, cursor_x, cursor_y, love_mode, band_volumes=band_vols, concert_mode=concert_mode)
        else:
            visualizer.draw(frame, volume_level, love_mode=love_mode, band_volumes=band_vols, concert_mode=concert_mode)

        # Draw hand landmarks
        tracker.draw_landmarks(frame, hands_data)

        # Draw effects
        effects.draw(frame)

        # Draw EQ overlay
        if eq_menu_open:
            active_hand_present = len(all_points) >= 1
            draw_equalizer_overlay(frame, eq_gains, eq_selected_band, eq_last_angle, active_hand_present)

        # Apply screen glitches
        effects.apply_screen_glitches(frame)

        # Draw lyrics
        if music.is_playing():
            song_time = music.get_pos()
            effects.draw_lyrics(frame, song_time)

        # Draw concert mode HUD indicator
        if concert_mode:
            effects.draw_concert_hud(frame)

        # Draw main HUD
        draw_main_hud(frame, gesture_rec, visualizer, music, volume_level, hands_count, fps, current_gesture, effects.glitch_level, eq_active=eq_menu_open, concert_mode=concert_mode)

        # Draw popup text
        if popup_text and now - popup_time < 1.0:
            alpha = 1.0 - (now - popup_time)
            pc = tuple(int(c * alpha) for c in popup_color)
            px = popup_pos[0] + (random.randint(-5, 5) if effects.glitch_level > 0.5 else 0)
            py = popup_pos[1] + (random.randint(-5, 5) if effects.glitch_level > 0.5 else 0)
            draw_text(frame, popup_text, (px - len(popup_text) * 4, py - 30), pc, 0.45, 1)

        cv2.imshow(WINDOW_NAME, frame)
        key = cv2.waitKey(1) & 255
        if key in (ord('q'), 27):
            break
        elif key == ord('m'):
            if music.is_loaded:
                music.toggle()
            elif os.path.exists(AUDIO_PATH):
                music.load(AUDIO_PATH)
                music.play()
        elif key == ord('t'):
            visualizer.cycle_type()
            popup_text = f'WAVEFORM: {visualizer.current_type.upper()}'
            popup_time = time.time()
            popup_pos = (w // 2, h // 2)
            popup_color = HUD_MAGENTA
        elif key == ord('c'):
            concert_mode = not concert_mode
            effects.set_concert_mode(concert_mode)
            popup_text = f'CONCERT MODE: {"ON" if concert_mode else "OFF"}'
            popup_time = time.time()
            popup_pos = (w // 2, h // 2)
            popup_color = HUD_ORANGE if concert_mode else HUD_DIM

    print('\n[INFO] Menutup sistem...')
    cap.release()
    tracker.release()
    music.cleanup()
    cv2.destroyAllWindows()
    print('[OK] Sistem terminated.')


if __name__ == '__main__':
    main()
