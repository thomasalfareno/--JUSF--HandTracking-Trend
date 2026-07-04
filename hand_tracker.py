import os
import time
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17)
]


class HandTracker:
    COLORS = {
        'point': (0, 255, 255),
        'line': (255, 0, 255),
        'point_alt': (0, 255, 128),
        'line_alt': (255, 128, 0)
    }

    def __init__(self, max_hands=2, detection_confidence=0.5, tracking_confidence=0.4):
        model_path = self._find_model()
        if model_path is None:
            raise FileNotFoundError(
                'hand_landmarker.task tidak ditemukan!\n'
                'Download dari: https://storage.googleapis.com/mediapipe-models/'
                'hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task\n'
                'Taruh di folder yang sama dengan main.py.'
            )
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=max_hands,
            min_hand_detection_confidence=detection_confidence,
            min_hand_presence_confidence=0.4,
            min_tracking_confidence=tracking_confidence,
            running_mode=vision.RunningMode.VIDEO
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)
        self._start_time_ms = int(time.time() * 1000)
        self._last_result = None
        # EMA smoothing for landmark positions
        self._smooth_alpha = 0.45  # 0=max smooth, 1=no smooth
        self._prev_landmarks = {}  # hand_index -> list of (x, y) smoothed

    def _find_model(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(script_dir, 'hand_landmarker.task'),
            os.path.join(script_dir, 'assets', 'hand_landmarker.task'),
            'hand_landmarker.task'
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def process(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        # Use real-time timestamp for better tracking sync
        current_ms = int(time.time() * 1000) - self._start_time_ms
        self._last_result = self.landmarker.detect_for_video(mp_image, current_ms)
        return self._last_result.hand_landmarks

    def get_handedness(self):
        labels = []
        if self._last_result and self._last_result.handedness:
            for hand_info in self._last_result.handedness:
                if hand_info:
                    labels.append(hand_info[0].category_name)
        return labels

    def get_pixel_landmarks(self, hand_landmarks, frame_w, frame_h, hand_index=0):
        """Get pixel landmarks with EMA smoothing for jitter reduction."""
        raw_points = []
        for lm in hand_landmarks:
            px = lm.x * frame_w
            py = lm.y * frame_h
            raw_points.append((px, py))

        # Apply EMA smoothing
        if hand_index in self._prev_landmarks and len(self._prev_landmarks[hand_index]) == len(raw_points):
            smoothed = []
            prev = self._prev_landmarks[hand_index]
            alpha = self._smooth_alpha
            for i, (rx, ry) in enumerate(raw_points):
                sx = alpha * rx + (1 - alpha) * prev[i][0]
                sy = alpha * ry + (1 - alpha) * prev[i][1]
                smoothed.append((sx, sy))
            self._prev_landmarks[hand_index] = smoothed
        else:
            smoothed = raw_points
            self._prev_landmarks[hand_index] = smoothed

        # Convert to int for pixel coordinates
        return [(int(x), int(y)) for x, y in smoothed]

    def draw_landmarks(self, frame, hands_data):
        h, w = frame.shape[:2]
        for idx, hand_landmarks in enumerate(hands_data):
            points = self.get_pixel_landmarks(hand_landmarks, w, h, hand_index=idx)
            if idx == 0:
                point_color = self.COLORS['point']
                line_color = self.COLORS['line']
            else:
                point_color = self.COLORS['point_alt']
                line_color = self.COLORS['line_alt']
            for start_idx, end_idx in HAND_CONNECTIONS:
                if start_idx < len(points) and end_idx < len(points):
                    pt1 = points[start_idx]
                    pt2 = points[end_idx]
                    cv2.line(frame, pt1, pt2, line_color, 4, cv2.LINE_AA)
                    cv2.line(frame, pt1, pt2, (255, 255, 255), 1, cv2.LINE_AA)
            for i, pt in enumerate(points):
                cv2.circle(frame, pt, 6, point_color, -1, cv2.LINE_AA)
                cv2.circle(frame, pt, 3, (255, 255, 255), -1, cv2.LINE_AA)
                if i in (4, 8, 12, 16, 20):
                    cv2.circle(frame, pt, 8, point_color, 2, cv2.LINE_AA)

    def get_palm_center(self, points):
        palm_indices = [0, 5, 9, 13, 17]
        xs = [points[i][0] for i in palm_indices]
        ys = [points[i][1] for i in palm_indices]
        return (int(np.mean(xs)), int(np.mean(ys)))

    def clear_smoothing(self):
        """Reset smoothing state (call when hands disappear)."""
        self._prev_landmarks.clear()

    def release(self):
        self.landmarker.close()
