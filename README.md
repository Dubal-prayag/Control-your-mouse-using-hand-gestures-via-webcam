# 🖐️ HAND_GESTURE_MOUSE_CONTROL

> Control your mouse with hand gestures via webcam. **No physical mouse needed.**

![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-green?style=flat-square)
![Platform](https://img.shields.io/badge/Windows%20%7C%20Linux%20%7C%20Mac-supported-0078D6?style=flat-square)

---

## ✋ Gestures

| Gesture | Action |
|---|---|
| ☝️ Index finger only | Move cursor |
| 🤏 Thumb + Index pinch | Left click |
| 🤏 Thumb + Middle pinch | Right click |
| ✌️ Index + Middle UP | Scroll (hand up = up, hand down = down) |
| 🖖 Index + Middle + Ring, hold 2s | Screenshot |

---

## ⌨️ Hotkeys

| Key | Action |
|---|---|
| `Q` / `E` | Pinch threshold looser / tighter |
| `W` | Reset pinch threshold |
| `A` / `D` | Scroll faster / slower |
| `S` | Reset scroll speed |
| `ESC` | Exit |

---

## ⚡ Why scroll works here (and not elsewhere)

`pyautogui.scroll()` on Windows sends `WHEEL_DELTA = 120` per call — one hard coarse jump. It cannot be made smooth.

**new feature fix:** Uses `ctypes.windll.user32.mouse_event()` directly with a small delta (15–40 units) per frame → true butter-smooth scrolling. PyAutoGUI is bypassed entirely for scrolling on Windows.

| Platform | Scroll engine |
|---|---|
| Windows | `ctypes` `MOUSEEVENTF_WHEEL` direct |
| macOS | `pyautogui.scroll()` (works fine natively) |
| Linux | `xdotool click` with fallback to pyautogui |

---

## ⚙️ How It Works

```
Webcam  →  MediaPipe (21 keypoints/hand)  →  Gesture Classifier  →  Mouse Event  →  Screen
```

- **MediaPipe** detects 21 hand landmarks per frame in `VIDEO` mode
- **Gesture classifier** uses normalised pinch distances + finger extension checks
- **Confirmation engine** requires N stable frames before firing clicks (prevents flicker)
- **Scroll engine** blends velocity from hand speed + base delta so there's always a guaranteed minimum scroll even with slow movement
- **Mouse smoothing** adapts between slow (precision) and fast (responsiveness) modes based on hand speed

---

## 🚀 Get Started

**1. Get the MediaPipe model**
```bash
curl -o hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
```

**2. Install dependencies**
```bash
pip install mediapipe opencv-python pyautogui numpy
```

**3. Run**
```bash
python virtual_mouse_new.py
```

> **Requirements:** Python 3.8+, a working webcam, decent lighting. `xdotool` required on Linux for best scroll support.

---

## 🧠 Tech Stack

| Library | Role |
|---|---|
| `mediapipe >= 0.10` | 21-keypoint hand landmark detection |
| `opencv-python` | Webcam capture & frame rendering |
| `ctypes` | Native Windows smooth scroll via Win32 API |
| `pyautogui` | Click, cursor move, screenshot |
| `numpy` | Geometry math & smoothing |

---

## 🎛️ Tuning (edit at top of file)

| Parameter | Default | What it does |
|---|---|---|
| `CLICK_THRESH` | `0.30` | Pinch distance to trigger a click |
| `SCROLL_DELTA_BASE` | `35` | Min scroll units sent per frame |
| `SCROLL_DELTA_MAX` | `110` | Max scroll units per frame (≈ 1 notch) |
| `SCROLL_SPEED_MUL` | `3500` | How much hand speed amplifies scroll |
| `SCROLL_MOMENTUM` | `0.78` | Velocity kept per frame after gesture ends |
| `SMOOTH_SLOW` | `0.10` | Cursor smoothing when hand is still |
| `SMOOTH_FAST` | `0.45` | Cursor smoothing when hand is moving |
| `CONFIRM_FRAMES_CLICK` | `4` | Stable frames needed before click fires |
| `SHOT_HOLD` | `2.0s` | How long to hold screenshot gesture |

---

## 📁 Files

```
virtual_mouse_new.py          ← this file (main entry point)
virtual_mouse_fullscreen.py   ← fullscreen variant
hand_pose_controller.py       ← gesture → action logic
hand_tracker_edge.py          ← edge-based hand tracking
hand_tracker_renderer.py      ← landmark overlay rendering
mouse_controller.py           ← mouse event abstraction
manager_hand_solo.py          ← single-hand session manager
hand_landmarker.task          ← MediaPipe model (download separately)
```

---

**Made by [Dubal Prayag](https://github.com/Dubal-prayag)** · *Built with ❤️ and a lot of hand-waving*
