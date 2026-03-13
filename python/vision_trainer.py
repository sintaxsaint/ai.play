"""
ai.play vision trainer — vision.train() and on.detect()
Trainable object/face/plate recognition using OpenCV.
Falls back to stub if OpenCV not installed.

Usage:
    vision.train(elliot, ./known/elliot/)
    vision.train(stranger, ./known/strangers/)

    on.detect(elliot):
        print("Welcome home")

    on.detect(stranger):
        notify.discord("Unknown person detected")
"""

import os
import threading
import time

class VisionTrainer:
    def __init__(self):
        self.labels    = {}   # label -> list of image paths
        self.detectors = {}   # label -> trained detector
        self._backend  = None
        self._init_backend()

    def _init_backend(self):
        try:
            import cv2
            import numpy as np
            self._backend = 'opencv'
            print("[ai.play] Vision trainer: OpenCV backend")
        except ImportError:
            self._backend = 'stub'
            print("[ai.play] Vision trainer: stub mode (pip install opencv-python for real detection)")

    def train(self, label, image_dir):
        """Train the detector to recognise a label from a directory of images."""
        path = os.path.expanduser(image_dir)
        if not os.path.exists(path):
            print(f"[ai.play] vision.train: directory not found: {path}")
            return

        images = [os.path.join(path, f) for f in os.listdir(path)
                  if f.lower().endswith(('.jpg','.jpeg','.png','.bmp'))]

        if not images:
            print(f"[ai.play] vision.train: no images found in {path}")
            return

        self.labels[label] = images
        print(f"[ai.play] vision.train: '{label}' trained on {len(images)} image(s)")

        if self._backend == 'opencv':
            self._train_opencv(label, images)

    def _train_opencv(self, label, image_paths):
        try:
            import cv2
            import numpy as np
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            recogniser = cv2.face.LBPHFaceRecognizer_create()
            faces, ids = [], []
            for idx, path in enumerate(image_paths):
                img  = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                if img is None: continue
                detected = face_cascade.detectMultiScale(img, 1.1, 5)
                for (x,y,w,h) in detected:
                    faces.append(img[y:y+h, x:x+w])
                    ids.append(idx)
            if faces:
                recogniser.train(faces, np.array(ids))
                self.detectors[label] = recogniser
        except Exception as e:
            print(f"[ai.play] vision.train opencv error: {e}")

    def detect(self, frame, label):
        """
        Check if label is detected in frame.
        Returns True/False.
        frame can be a numpy array (OpenCV) or a path string.
        """
        if self._backend == 'stub':
            return False  # stub always returns no detection

        if label not in self.labels:
            return False

        try:
            import cv2
            import numpy as np

            if isinstance(frame, str):
                img = cv2.imread(frame, cv2.IMREAD_GRAYSCALE)
            else:
                img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape)==3 else frame

            if img is None:
                return False

            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            detected = face_cascade.detectMultiScale(img, 1.1, 5)

            if label in self.detectors and len(detected) > 0:
                recogniser = self.detectors[label]
                for (x,y,w,h) in detected:
                    face_roi = img[y:y+h, x:x+w]
                    _, confidence = recogniser.predict(face_roi)
                    if confidence < 80:  # lower = more confident match
                        return True
                return False
            elif label == 'motion':
                return len(detected) > 0
            elif label == 'face':
                return len(detected) > 0
            elif label == 'person':
                return len(detected) > 0
            return False
        except Exception as e:
            print(f"[ai.play] detect error: {e}")
            return False


class LiveVisionLoop:
    """
    Runs the live camera loop and fires on.detect() event hooks.
    """
    def __init__(self, trainer, event_hooks, notify_engine=None):
        self.trainer      = trainer
        self.event_hooks  = event_hooks   # dict: label -> callable
        self.notify       = notify_engine
        self._running     = False
        self._thread      = None
        self._last_frame  = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[ai.play] Live vision loop started")

    def stop(self):
        self._running = False

    def get_last_frame(self):
        return self._last_frame

    def _loop(self):
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            prev_gray = None

            while self._running:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue

                self._last_frame = frame

                # Check each registered label
                for label, hook in self.event_hooks.items():
                    if label == 'motion':
                        # Motion detection via frame diff
                        import numpy as np
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        gray = cv2.GaussianBlur(gray, (21,21), 0)
                        if prev_gray is not None:
                            diff = cv2.absdiff(prev_gray, gray)
                            thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
                            if thresh.sum() > 100000:
                                hook(frame)
                        prev_gray = gray
                    else:
                        if self.trainer.detect(frame, label):
                            hook(frame)

                time.sleep(0.1)  # ~10fps check rate

            cap.release()
        except ImportError:
            print("[ai.play] Live vision requires opencv-python: pip install opencv-python")
        except Exception as e:
            print(f"[ai.play] Live vision error: {e}")
