"""
client/core/eye_tracker.py

Threaded local camera eye-tracking engine using OpenCV and MediaPipe.
Calculates Eye Aspect Ratio (EAR) to detect blinking/fatigue and slows down WPM.
"""

import cv2
import numpy as np
import mediapipe as mp
from PyQt6.QtCore import QThread, pyqtSignal


class EyeTrackerThread(QThread):
    # Emits additional WPM penalty (e.g. 0 to 150) to be subtracted from base WPM
    slowdown_penalty_updated = pyqtSignal(int)

    def __init__(self, camera_index=0, ear_threshold=0.21, penalty_wpm=100):
        super().__init__()
        self.camera_index = camera_index
        self.ear_threshold = ear_threshold  # Threshold below which eyes are considered closed/squinting
        self.penalty_wpm = penalty_wpm      # Max WPM to subtract when user is fatigued/closing eyes
        self._running = True

        # MediaPipe Face Mesh landmark indices for Left & Right Eyes
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]

    def _calculate_ear(self, landmarks, eye_indices, img_w, img_h):
        """
        Calculates Eye Aspect Ratio (EAR):
        EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)
        """
        coords = []
        for idx in eye_indices:
            lm = landmarks[idx]
            coords.append(np.array([lm.x * img_w, lm.y * img_h]))

        # Vertical distances
        v1 = np.linalg.norm(coords[1] - coords[5])
        v2 = np.linalg.norm(coords[2] - coords[4])
        # Horizontal distance
        h = np.linalg.norm(coords[0] - coords[3])

        if h == 0:
            return 0.0

        ear = (v1 + v2) / (2.0 * h)
        return ear

    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        # Set low resolution for optimal processing on Raspberry Pi
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

        mp_face_mesh = mp.solutions.face_mesh
        face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        while self._running:
            ret, frame = cap.read()
            if not ret:
                self.msleep(100)
                continue

            # Convert BGR image to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_frame)

            current_penalty = 0

            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                h, w, _ = frame.shape

                left_ear = self._calculate_ear(landmarks, self.LEFT_EYE, w, h)
                right_ear = self._calculate_ear(landmarks, self.RIGHT_EYE, w, h)
                avg_ear = (left_ear + right_ear) / 2.0

                # If EAR drops below threshold, eyes are closing or squinting
                if avg_ear < self.ear_threshold:
                    current_penalty = self.penalty_wpm
                else:
                    current_penalty = 0
            else:
                # If face/eyes are completely lost, apply half penalty to slow down safely
                current_penalty = int(self.penalty_wpm / 2)

            self.slowdown_penalty_updated.emit(current_penalty)
            self.msleep(30)  # ~30 FPS polling rate

        cap.release()
        face_mesh.close()

    def stop(self):
        self._running = False
        self.wait()