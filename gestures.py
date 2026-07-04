import time
import math
import numpy as np


def _distance(p1, p2):
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


class GestureRecognizer:
    NONE = 'NONE'
    OPEN_PALM = 'OPEN_PALM'
    PINCH = 'PINCH'
    FIST = 'FIST'
    POINT_UP = 'POINT_UP'
    VICTORY = 'VICTORY'
    TWO_HAND_SPREAD = 'TWO_HAND_SPREAD'
    TWO_HAND_CLOSE = 'TWO_HAND_CLOSE'
    HEART = 'HEART'
    THUMB_UP = 'THUMB_UP'
    THUMB_DOWN = 'THUMB_DOWN'
    ROCK = 'ROCK'
    THREE_THREE = 'THREE_THREE'
    ALL_OPEN = 'ALL_OPEN'

    MODE_IDLE = 'IDLE'
    MODE_BUILD = 'BUILD'
    MODE_LOVE = 'LOVE'

    def __init__(self):
        self.mode = self.MODE_IDLE
        self._cooldowns = {}
        self._cooldown_duration = 0.5
        self._pinch_active = False
        self._fist_active = False
        self._point_active = False
        self._victory_active = False
        self._thumb_up_active = False
        self._thumb_down_active = False
        self._rock_active = False
        self._three_three_active = False
        self._all_open_active = False
        # Swipe detection
        self._hand_history = []  # list of (x, timestamp)
        self._swipe_cooldown = 0.0

    def _check_cooldown(self, gesture_name):
        now = time.time()
        last = self._cooldowns.get(gesture_name, 0)
        if now - last >= self._cooldown_duration:
            self._cooldowns[gesture_name] = now
            return True
        return False

    def _get_finger_states(self, points):
        """Improved finger state detection using angle-based method for better accuracy."""
        # Thumb: use cross product to determine if thumb is extended outward
        thumb_tip = points[4]
        thumb_ip = points[3]
        thumb_mcp = points[2]
        thumb_cmc = points[1]
        wrist = points[0]
        index_mcp = points[5]

        # Calculate hand orientation (left vs right facing)
        hand_dir_x = index_mcp[0] - wrist[0]

        # Thumb: extended if tip is farther from palm center than IP joint
        palm_cx = (wrist[0] + points[5][0] + points[9][0] + points[13][0] + points[17][0]) / 5
        palm_cy = (wrist[1] + points[5][1] + points[9][1] + points[13][1] + points[17][1]) / 5

        thumb_tip_dist = _distance(thumb_tip, (palm_cx, palm_cy))
        thumb_ip_dist = _distance(thumb_ip, (palm_cx, palm_cy))
        thumb_extended = thumb_tip_dist > thumb_ip_dist * 1.1

        # Other fingers: use angle at PIP joint for more robust detection
        fingers = []
        fingers.append(thumb_extended)

        finger_data = [
            (5, 6, 7, 8),    # Index: MCP, PIP, DIP, TIP
            (9, 10, 11, 12),  # Middle
            (13, 14, 15, 16), # Ring
            (17, 18, 19, 20), # Pinky
        ]

        for mcp_i, pip_i, dip_i, tip_i in finger_data:
            mcp = points[mcp_i]
            pip = points[pip_i]
            dip = points[dip_i]
            tip = points[tip_i]

            # Method: Check if tip is farther from wrist than PIP
            tip_dist = _distance(tip, wrist)
            pip_dist = _distance(pip, wrist)

            # Also check angle: a curled finger has tip closer to MCP
            tip_to_mcp = _distance(tip, mcp)
            pip_to_mcp = _distance(pip, mcp)

            # Finger is extended if tip is farther from wrist AND farther from MCP
            extended = tip_dist > pip_dist * 0.92 and tip_to_mcp > pip_to_mcp * 0.8
            fingers.append(extended)

        return fingers

    def _count_extended_fingers(self, points):
        """Count how many fingers are extended."""
        states = self._get_finger_states(points)
        return sum(states), states

    def detect_single_hand(self, points):
        if len(points) < 21:
            return self.NONE

        palm_size = _distance(points[0], points[9])
        if palm_size < 10:
            palm_size = 10

        finger_states = self._get_finger_states(points)
        thumb, index, middle, ring, pinky = finger_states

        # ---- THUMB UP / DOWN (only thumb extended) ----
        if thumb and not index and not middle and not ring and not pinky:
            if points[4][1] < points[3][1]:
                self._thumb_down_active = False
                if not self._thumb_up_active:
                    self._thumb_up_active = True
                    if self._check_cooldown(self.THUMB_UP):
                        return self.THUMB_UP
            else:
                self._thumb_up_active = False
                if not self._thumb_down_active:
                    self._thumb_down_active = True
                    if self._check_cooldown(self.THUMB_DOWN):
                        return self.THUMB_DOWN
            return self.NONE
        else:
            self._thumb_up_active = False
            self._thumb_down_active = False

        # ---- ROCK 🤘 (index + pinky only) ----
        if index and not middle and not ring and pinky:
            if not self._rock_active:
                self._rock_active = True
                if self._check_cooldown(self.ROCK):
                    return self.ROCK
            return self.NONE
        else:
            self._rock_active = False

        # ---- PINCH (thumb and index close together, continuous) ----
        pinch_dist = _distance(points[4], points[8])
        if pinch_dist < 0.3 * palm_size:
            self._pinch_active = True
            return self.PINCH
        else:
            self._pinch_active = False

        # ---- FIST (all fingers closed) ----
        if not index and not middle and not ring and not pinky:
            if not self._fist_active:
                self._fist_active = True
                if self._check_cooldown(self.FIST):
                    return self.FIST
            return self.FIST  # Keep fist active continuously
        else:
            self._fist_active = False

        # ---- POINT UP (only index extended) ----
        if index and not middle and not ring and not pinky:
            if not self._point_active:
                self._point_active = True
                if self._check_cooldown(self.POINT_UP):
                    return self.POINT_UP
            return self.NONE
        else:
            self._point_active = False

        # ---- VICTORY ✌ (index + middle extended) ----
        if index and middle and not ring and not pinky:
            if not self._victory_active:
                self._victory_active = True
                if self._check_cooldown(self.VICTORY):
                    return self.VICTORY
            return self.NONE
        else:
            self._victory_active = False

        # ---- OPEN PALM (all 4 fingers extended) ----
        if index and middle and ring and pinky:
            return self.OPEN_PALM

        return self.NONE

    def detect_two_hands(self, points1, points2, palm_center1, palm_center2):
        """Detect two-hand gestures including new THREE_THREE and ALL_OPEN."""
        palm_size1 = _distance(points1[0], points1[9])
        palm_size2 = _distance(points2[0], points2[9])
        avg_palm_size = (palm_size1 + palm_size2) / 2.0
        if avg_palm_size < 10:
            avg_palm_size = 10

        palm_dist = _distance(palm_center1, palm_center2)

        # Get finger counts for both hands
        count1, states1 = self._count_extended_fingers(points1)
        count2, states2 = self._count_extended_fingers(points2)
        thumb1, idx1, mid1, ring1, pinky1 = states1
        thumb2, idx2, mid2, ring2, pinky2 = states2

        # ---- ALL_OPEN: 10 fingers all extended (both hands fully open) ----
        if count1 >= 4 and count2 >= 4 and idx1 and mid1 and ring1 and pinky1 and idx2 and mid2 and ring2 and pinky2:
            if not self._all_open_active:
                self._all_open_active = True
                if self._check_cooldown(self.ALL_OPEN):
                    return self.ALL_OPEN
            return self.NONE
        else:
            self._all_open_active = False

        # ---- THREE_THREE: 3 fingers (index+middle+ring) on both hands ----
        # Exactly 3 fingers: index, middle, ring extended; thumb and pinky closed
        three1 = idx1 and mid1 and ring1 and not pinky1
        three2 = idx2 and mid2 and ring2 and not pinky2
        if three1 and three2:
            if not self._three_three_active:
                self._three_three_active = True
                if self._check_cooldown(self.THREE_THREE):
                    return self.THREE_THREE
            return self.NONE
        else:
            self._three_three_active = False

        # ---- HEART: thumbs and index fingers close together ----
        thumb_dist = _distance(points1[4], points2[4])
        index_dist = _distance(points1[8], points2[8])
        if thumb_dist < 0.5 * avg_palm_size and index_dist < 0.5 * avg_palm_size:
            if self._check_cooldown(self.HEART):
                return self.HEART
            return self.NONE

        # ---- TWO_HAND_SPREAD / CLOSE ----
        if palm_dist > 3.0 * avg_palm_size:
            return self.TWO_HAND_SPREAD
        if palm_dist < 1.3 * avg_palm_size:
            return self.TWO_HAND_CLOSE

        return self.NONE

    def update_mode(self, gesture):
        if gesture == self.OPEN_PALM:
            if self.mode != self.MODE_BUILD:
                if self._check_cooldown('mode_build'):
                    self.mode = self.MODE_BUILD
        elif gesture == self.HEART:
            if self.mode != self.MODE_LOVE:
                self.mode = self.MODE_LOVE
            else:
                self.mode = self.MODE_BUILD

    def get_cursor_position(self, points):
        cx = (points[4][0] + points[8][0]) // 2
        cy = (points[4][1] + points[8][1]) // 2
        return (cx, cy)
