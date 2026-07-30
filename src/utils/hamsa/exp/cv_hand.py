import os
import sys
import time
from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np

# =========================
# PATH
# =========================
BASE_DIR = os.path.dirname(__file__)

sys.path.append(os.path.join(BASE_DIR, "../cpp"))
sys.path.append(os.path.join(BASE_DIR, "../"))

import scservo_py
from hamsa import hand

# =========================
# CONFIG
# =========================
CAMERA_ID = 0
WINDOW_NAME = "hand"

SEND_INTERVAL = 0.03
ROBOT_MOVE_TIME = 200
INIT_MOVE_TIME = 1000

EMA_ALPHA_CURL = 0.2
EMA_ALPHA_WIGGLE = 0.15

# =========================
# MEDIAPIPE
# =========================
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

# =========================
# EMA FILTER
# =========================
class EMA:
    def __init__(self, alpha=0.2):
        self.alpha = alpha
        self.value = None

    def update(self, x):
        if self.value is None:
            self.value = x
        else:
            self.value = (
                self.alpha * x
                + (1.0 - self.alpha) * self.value
            )

        return self.value

# =========================
# FILTER SET
# =========================
filters = {
    "thumb": EMA(EMA_ALPHA_CURL),

    "index_curl": EMA(EMA_ALPHA_CURL),
    "middle_curl": EMA(EMA_ALPHA_CURL),
    "ring_curl": EMA(EMA_ALPHA_CURL),
    "pinky_curl": EMA(EMA_ALPHA_CURL),

    "index_wiggle": EMA(EMA_ALPHA_WIGGLE),
    "middle_wiggle": EMA(EMA_ALPHA_WIGGLE),
    "ring_wiggle": EMA(EMA_ALPHA_WIGGLE),
    "pinky_wiggle": EMA(EMA_ALPHA_WIGGLE),
}

# =========================
# DATA
# =========================
@dataclass
class FingerState:
    thumb: float

    index_curl: float
    middle_curl: float
    ring_curl: float
    pinky_curl: float

    index_wiggle: float
    middle_wiggle: float
    ring_wiggle: float
    pinky_wiggle: float

    def as_dict(self):
        return self.__dict__

# =========================
# UTILS
# =========================
def normalize(v):
    return v / (np.linalg.norm(v) + 1e-6)

def clip01(v):
    return np.clip(v, 0.0, 1.0)

# =========================
# FEATURE EXTRACTION
# =========================
def curl_finger_value(lm, tip, mcp):

    hand_y = normalize(np.array([
        lm[9].x - lm[0].x,
        lm[9].y - lm[0].y
    ]))

    finger = normalize(np.array([
        lm[tip].x - lm[mcp].x,
        lm[tip].y - lm[mcp].y
    ]))

    v = np.dot(finger, hand_y)

    return clip01((v + 1.0) * 0.5)

def thumb_value(lm):

    v1 = np.array([
        lm[2].x - lm[1].x,
        lm[2].y - lm[1].y
    ])

    v2 = np.array([
        lm[4].x - lm[2].x,
        lm[4].y - lm[2].y
    ])

    cos_angle = np.dot(v1, v2) / (
        np.linalg.norm(v1) *
        np.linalg.norm(v2) +
        1e-6
    )

    angle = np.arccos(
        np.clip(cos_angle, -1.0, 1.0)
    )

    v = 1.0 - (angle / 1.5)

    return clip01(v)

def wiggle_finger_value(
    lm,
    tip,
    mcp,
    reverse=False
):

    hand_x = normalize(np.array([
        lm[17].x - lm[5].x,
        lm[17].y - lm[5].y
    ]))

    if reverse:
        hand_x = -hand_x

    finger = normalize(np.array([
        lm[tip].x - lm[mcp].x,
        lm[tip].y - lm[mcp].y
    ]))

    v = np.dot(finger, hand_x)

    v = np.tanh(v * 4.0)

    return clip01((v + 1.0) * 0.5)

# =========================
# ROBOT CONTROL
# =========================
def set_default_pose():

    T = INIT_MOVE_TIME

    hand.curl_thumb(1, T)
    hand.curl_index(1, T)
    hand.curl_middle(1, T)
    hand.curl_ring(1, T)
    hand.curl_pinky(1, T)

    hand.wiggle_pinky(0, T)
    hand.wiggle_ring(0, T)
    hand.wiggle_middle(0.5, T)
    hand.wiggle_index(0.5, T)
    hand.wiggle_thumb(0, T)

def send_to_robot(f):

    T = ROBOT_MOVE_TIME

    hand.curl_thumb(f["thumb"], T)

    hand.curl_index(f["index_curl"], T)
    hand.curl_middle(f["middle_curl"], T)
    hand.curl_ring(f["ring_curl"], T)
    hand.curl_pinky(f["pinky_curl"], T)

    hand.wiggle_index(f["index_wiggle"], T)
    hand.wiggle_middle(f["middle_wiggle"], T)
    hand.wiggle_ring(f["ring_wiggle"], T)
    hand.wiggle_pinky(f["pinky_wiggle"], T)

# =========================
# HAND ANALYSIS
# =========================
def extract_raw_values(lm):

    return {
        "thumb":
            thumb_value(lm),

        # curl
        "index_curl":
            curl_finger_value(lm, 8, 6),

        "middle_curl":
            curl_finger_value(lm, 12, 10),

        "ring_curl":
            curl_finger_value(lm, 16, 14),

        "pinky_curl":
            curl_finger_value(lm, 20, 18),

        # wiggle
        "index_wiggle":
            wiggle_finger_value(lm, 8, 5),

        "middle_wiggle":
            wiggle_finger_value(lm, 12, 9),

        "ring_wiggle":
            wiggle_finger_value(lm, 16, 13),

        "pinky_wiggle":
            wiggle_finger_value(lm, 20, 17),
    }

def apply_filters(raw):

    return {
        k: filters[k].update(v)
        for k, v in raw.items()
    }

# =========================
# DEBUG DRAW
# =========================
def draw_debug(frame, fingers):

    lines = [
        f"thumb : {fingers['thumb']:.2f}",

        f"index  c:{fingers['index_curl']:.2f} "
        f"w:{fingers['index_wiggle']:.2f}",

        f"middle c:{fingers['middle_curl']:.2f} "
        f"w:{fingers['middle_wiggle']:.2f}",

        f"ring   c:{fingers['ring_curl']:.2f} "
        f"w:{fingers['ring_wiggle']:.2f}",

        f"pinky  c:{fingers['pinky_curl']:.2f} "
        f"w:{fingers['pinky_wiggle']:.2f}",
    ]

    y = 25

    for line in lines:

        cv2.putText(
            frame,
            line,
            (10, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )

        y += 28

# =========================
# WINDOW CLOSED CHECK
# =========================
def is_window_closed(window_name):

    try:
        visible = cv2.getWindowProperty(
            window_name,
            cv2.WND_PROP_VISIBLE
        )

        return visible < 1

    except cv2.error:
        return True

# =========================
# MAIN
# =========================
def main():

    cap = cv2.VideoCapture(CAMERA_ID)

    if not cap.isOpened():
        print("camera open failed")
        return

    cv2.namedWindow(WINDOW_NAME)

    hands = mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )

    set_default_pose()

    time.sleep(1.0)

    last_send = 0.0

    try:

        while True:

            if is_window_closed(WINDOW_NAME):
                break

            ret, frame = cap.read()

            if not ret:
                print("camera read failed")
                break

            frame = cv2.flip(frame, 1)

            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            result = hands.process(rgb)

            if result.multi_hand_landmarks:

                hand_landmarks = result.multi_hand_landmarks[0]

                mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS
                )

                lm = hand_landmarks.landmark
                raw = extract_raw_values(lm)
                fingers = apply_filters(raw)
                now = time.time()

                if now - last_send >= SEND_INTERVAL:

                    # send_to_robot(fingers)

                    last_send = now

                draw_debug(frame, fingers)

            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKey(1) & 0xFF

            if key == 27:
                break

    finally:
        cap.release()
        hands.close()
        cv2.destroyAllWindows()

# =========================
# ENTRY
# =========================
if __name__ == "__main__":
    main()