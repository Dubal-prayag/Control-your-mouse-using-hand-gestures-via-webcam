"""
Virtual Mouse + Improved Scroll Gesture (Fullscreen) - Updated for new Mediapipe Tasks API

Gestures:
- Index finger (alone)       -> Move mouse (absolute mapping)
- Thumb + Index (pinch)      -> Left click
- Thumb + Middle (pinch)     -> Right click
- Index + Middle extended    -> Scroll (move hand up/down to scroll PDF)
"""
import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import time

# ---------- CONFIG ----------
CAMERA_INDEX = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

SMOOTHING = 0.25            # 0..1 smoothness for mouse movement
CLICK_THRESHOLD = 0.045     # normalized distance threshold for pinches
CLICK_DEBOUNCE = 0.35       # seconds between allowed clicks
SHOW_FPS = True

# Scroll tuning (pixel-based)
SCROLL_THRESHOLD_PX = 30    # accumulate this many px of vertical motion before sending a scroll step
SCROLL_STEP_AMOUNT = 120    # pyautogui.scroll units per step (increase for faster scroll)
SCROLL_SENSITIVITY = 1.0
# ---------------------------

# Screen size (for absolute mapping)
screen_w, screen_h = pyautogui.size()

# Camera
cap = cv2.VideoCapture(CAMERA_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
if not cap.isOpened():
    raise IOError(f"Cannot open camera index {CAMERA_INDEX}. Try a different index.")

# runtime vars
prev_mouse_x, prev_mouse_y = 0.0, 0.0
last_click_time = 0.0
prev_time = time.time()

# scroll vars
last_scroll_avg_px = None
scroll_accumulator = 0.0

# Fullscreen window
WIN_NAME = "Virtual Mouse (Fullscreen + Improved Scroll) - New Mediapipe"
cv2.namedWindow(WIN_NAME, cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty(WIN_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

print("✅ Started. Gestures:")
print(" - Index finger: Move mouse")
print(" - Thumb + Index: Left click")
print(" - Thumb + Middle: Right click")
print(" - Index + Middle (both extended): Scroll up/down")
print("Press ESC to exit.")

# Mediapipe Tasks API - Fixed imports
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

BaseOptions = python.BaseOptions
HandLandmarker = vision.HandLandmarker
HandLandmarkerOptions = vision.HandLandmarkerOptions
VisionRunningMode = vision.RunningMode

# Legacy for drawing
mp_hands = mp.solutions.hands
HAND_CONNECTIONS = mp_hands.HAND_CONNECTIONS
mp_draw = mp.solutions.drawing_utils

# Create hand landmarker
base_options = BaseOptions(model_asset_path='hand_landmarker.task')
with HandLandmarker.create_from_options(
    HandLandmarkerOptions(
        base_options=base_options,
        running_mode=VisionRunningMode.VIDEO,
        num_hands=1
    )
) as hand_landmarker:

    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Frame not received; retrying...")
            continue

        frame = cv2.flip(frame, 1)  # mirror for natural movement
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int(time.time() * 1000)

        results = hand_landmarker.detect_for_video(mp_image, timestamp_ms)

        # show FPS
        if SHOW_FPS:
            cur_time = time.time()
            fps = 1.0 / (cur_time - prev_time) if cur_time != prev_time else 0.0
            prev_time = cur_time
            cv2.putText(frame, f"FPS: {fps:.1f}", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2)

        if results.hand_landmarks:
            lm_list = results.hand_landmarks[0]  # first hand
            lm = lm_list  # list of NormalizedLandmark

            # normalized tips
            idx_tip = lm[8]   # index tip
            mid_tip = lm[12]  # middle tip
            thumb_tip = lm[4] # thumb tip

            # also PIP joints to detect extension
            idx_pip = lm[6]
            mid_pip = lm[10]

            # Determine if index and middle are extended (tip is above pip vertically)
            # Note: normalized y increases downward, so tip.y < pip.y means extended (finger up)
            idx_extended = idx_tip.y < idx_pip.y
            mid_extended = mid_tip.y < mid_pip.y

            # Distances to thumb (normalized)
            dist_idx_thumb = np.hypot(idx_tip.x - thumb_tip.x, idx_tip.y - thumb_tip.y)
            dist_mid_thumb = np.hypot(mid_tip.x - thumb_tip.x, mid_tip.y - thumb_tip.y)

            now = time.time()

            # Scroll mode: both index and middle extended and NOT pinched
            is_scroll_mode = idx_extended and mid_extended and (dist_idx_thumb > CLICK_THRESHOLD) and (dist_mid_thumb > CLICK_THRESHOLD)

            if is_scroll_mode:
                # Compute average vertical position in camera pixels
                avg_y_norm = (idx_tip.y + mid_tip.y) / 2.0
                avg_y_px = avg_y_norm * h

                if last_scroll_avg_px is None:
                    last_scroll_avg_px = avg_y_px

                # positive delta_px means hand moved UP on camera (smaller y), so scroll up
                delta_px = (last_scroll_avg_px - avg_y_px) * SCROLL_SENSITIVITY
                scroll_accumulator += delta_px

                # when accumulator crosses threshold, send scroll steps
                if abs(scroll_accumulator) >= SCROLL_THRESHOLD_PX:
                    steps = int(scroll_accumulator / SCROLL_THRESHOLD_PX)  # can be positive or negative
                    # pyautogui.scroll: positive -> up, negative -> down
                    pyautogui.scroll(int(steps * SCROLL_STEP_AMOUNT))
                    scroll_accumulator -= steps * SCROLL_THRESHOLD_PX

                last_scroll_avg_px = avg_y_px

                # Visual feedback
                direction = "Up" if delta_px > 0 else ("Down" if delta_px < 0 else "None")
                cv2.putText(frame, f"SCROLL MODE: {direction}", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,255), 2)
                cv2.putText(frame, f"acc:{scroll_accumulator:.1f}px", (30, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200,200,0), 2)

                # While scrolling, we DO NOT move the mouse to avoid pointer drift
            else:
                # reset scroll tracking when not in scroll mode
                last_scroll_avg_px = None
                scroll_accumulator = 0.0

                # Move mouse using index tip (absolute mapping)
                target_x = np.interp(idx_tip.x, [0,1], [0, screen_w])
                target_y = np.interp(idx_tip.y, [0,1], [0, screen_h])
                cur_x = prev_mouse_x + (target_x - prev_mouse_x) * SMOOTHING
                cur_y = prev_mouse_y + (target_y - prev_mouse_y) * SMOOTHING
                prev_mouse_x, prev_mouse_y = cur_x, cur_y

                try:
                    pyautogui.moveTo(cur_x, cur_y, _pause=False)
                except Exception:
                    pass

                # Click gestures (only when not in scroll mode)
                if dist_idx_thumb < CLICK_THRESHOLD:
                    cv2.putText(frame, "Left Click", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 2)
                    if now - last_click_time > CLICK_DEBOUNCE:
                        pyautogui.click(button='left')
                        last_click_time = now

                elif dist_mid_thumb < CLICK_THRESHOLD:
                    cv2.putText(frame, "Right Click", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,0,0), 2)
                    if now - last_click_time > CLICK_DEBOUNCE:
                        pyautogui.click(button='right')
                        last_click_time = now

                else:
                    cv2.putText(frame, "Tracking (move)", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2)

            # draw hand landmarks
            mp_draw.draw_landmarks(
                frame, 
                [results.hand_landmarks[0]], 
                HAND_CONNECTIONS
            )

            # debug distances
            cv2.putText(frame, f"idx-thumb:{dist_idx_thumb:.3f}", (30, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
            cv2.putText(frame, f"mid-thumb:{dist_mid_thumb:.3f}", (30, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
            cv2.putText(frame, f"idx_ext:{int(idx_extended)} mid_ext:{int(mid_extended)}", (30, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200,200,200), 2)

        else:
            # no hand: reset scroll and show message
            last_scroll_avg_px = None
            scroll_accumulator = 0.0
            cv2.putText(frame, "No hand detected", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 2)

        cv2.imshow(WIN_NAME, frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

# cleanup
cap.release()
cv2.destroyAllWindows()
print("👋 Exited.")

