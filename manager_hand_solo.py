# object_detection_improved.py
import cv2
import mediapipe as mp
import numpy as np
from collections import deque

# --- CONFIG ---
MODEL_NAME = "efficientdet_lite2.tflite"   # download link below
MODEL_PATH = f"models/{MODEL_NAME}"
SCORE_THRESHOLD = 0.50     # only keep detections >= this score
MIN_AREA_RATIO = 0.02      # ignore boxes smaller than this fraction of image area
HISTORY_LEN = 5            # frames to remember
MIN_COUNT_IN_HISTORY = 2   # require label to appear this many times in HISTORY_LEN frames
ONLY_CLASSES = None        # e.g. ["person"] to restrict; or None to allow all
# ---------------

# Mediapipe Tasks API imports
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

BaseOptions = mp.tasks.BaseOptions
ObjectDetectorOptions = mp.tasks.vision.ObjectDetectorOptions
ObjectDetector = mp.tasks.vision.ObjectDetector
VisionRunningMode = mp.tasks.vision.RunningMode

options = ObjectDetectorOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    max_results=8,
    running_mode=VisionRunningMode.IMAGE
)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise IOError("Cannot open webcam (index 0). Try different index or check camera permissions.")

history = deque(maxlen=HISTORY_LEN)  # store list of labels per frame

with ObjectDetector.create_from_options(options) as detector:
    print("✅ Improved Object Detection started. Press ESC to exit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        h, w = frame.shape[:2]
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)

        detection_result = detector.detect(mp_image)

        # collect labels for this frame (after per-detection filtering)
        labels_this_frame = []

        if detection_result.detections:
            for detection in detection_result.detections:
                cat = detection.categories[0]
                label = cat.category_name
                score = float(cat.score)

                # score threshold
                if score < SCORE_THRESHOLD:
                    continue

                # optional class filter
                if ONLY_CLASSES is not None and label not in ONLY_CLASSES:
                    continue

                # bounding box and area filtering
                bbox = detection.bounding_box
                x = int(bbox.origin_x); y = int(bbox.origin_y)
                wbox = int(bbox.width); hbox = int(bbox.height)
                # clamp coordinates
                x = max(0, min(x, w-1)); y = max(0, min(y, h-1))
                wbox = max(2, min(wbox, w - x))
                hbox = max(2, min(hbox, h - y))

                area_ratio = (wbox * hbox) / float(w * h)
                if area_ratio < MIN_AREA_RATIO:
                    continue

                # keep this detection (save info for drawing later)
                labels_this_frame.append((label, score, (x, y, wbox, hbox)))

        # append only the label names to history (for smoothing)
        history.append([lbl for (lbl, *_rest) in labels_this_frame])

        # For display: only draw boxes for detections whose label appears frequently enough in recent history
        # (reduce transient false positives)
        def label_count_in_history(lbl):
            return sum(1 for frame_labels in history for l in frame_labels if l == lbl)

        # draw
        for label, score, (x, y, wbox, hbox) in labels_this_frame:
            if label_count_in_history(label) < MIN_COUNT_IN_HISTORY:
                # skip drawing until label has shown up consistently
                continue

            # draw box and label
            cv2.rectangle(frame, (x, y), (x + wbox, y + hbox), (0, 255, 0), 2)
            txt = f"{label} ({score:.2f})"
            cv2.putText(frame, txt, (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # helpful debug/info
        cv2.putText(frame, f"Model:{MODEL_NAME}  Thr:{SCORE_THRESHOLD}", (8, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 0), 2)

        cv2.imshow("AI Object Detection (Improved)", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()
print("👋 Exited.")
