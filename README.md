# 🖐️ Control Your Mouse Using Hand Gestures via Webcam

> Control your mouse with hand gestures using your webcam — **no physical mouse needed.**

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Hand%20Tracking-green?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?style=for-the-badge&logo=windows)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

---

## 📖 Overview

This project enables **touchless mouse control** through real-time hand gesture recognition via your webcam. Using **MediaPipe** for hand landmark detection and **PyAutoGUI** / **ctypes** for mouse control, you can move your cursor, click, scroll, and more — all with just your hand in front of a camera.

Perfect for accessibility use cases, presentations, or just the sheer coolness of it. ✨

---

## 🗂️ Project Structure

```
Hand_Gesture_Mouse_Control/
│
├── hand_landmarker.task          # MediaPipe hand landmark model
├── hand_pose_controller.py       # Core gesture-to-action mapping logic
├── hand_tracker_edge.py          # Edge-detection-based hand tracker
├── hand_tracker_renderer.py      # Renders hand landmarks on webcam feed
├── manager_hand_solo.py          # Single-hand session manager
├── mouse_controller.py           # Mouse event abstraction layer
├── virtual_mouse_new.py          # Main entry point (latest version)
├── virtual_mouse_fullscreen.py   # Fullscreen virtual mouse mode
├── run_mouse_controller.sh       # Shell script to launch the controller
├── README.md
└── TODO.md
```

---

## ✨ Features

- 🖱️ **Cursor Movement** — Move your index finger to control the mouse pointer
- 👆 **Left Click** — Pinch gesture (index + thumb)
- ✌️ **Right Click** — Two-finger gesture
- 📜 **Smooth Scrolling** — Platform-aware smooth scroll (Windows-native via `ctypes`)
- 🖥️ **Fullscreen Mode** — Dedicated fullscreen virtual mouse experience
- ⚡ **Low Latency** — Optimized frame-by-frame gesture detection
- 🧠 **AI-Powered** — Uses MediaPipe's hand landmark model (21 keypoints per hand)

---

## 🛠️ Tech Stack

| Library | Purpose |
|---|---|
| `mediapipe` | Hand landmark detection (21 keypoints) |
| `opencv-python` | Webcam capture & frame rendering |
| `pyautogui` | Cross-platform mouse control |
| `ctypes` | Windows-native scroll events |
| `platform` | OS detection for platform-aware behavior |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- A working webcam
- Windows OS (for full scroll support)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Dubal-prayag/Control-your-mouse-using-hand-gestures-via-webcam.git
cd Control-your-mouse-using-hand-gestures-via-webcam

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install mediapipe opencv-python pyautogui
```

### Running the App

```bash
# Option 1: Run directly
python virtual_mouse_new.py

# Option 2: Run fullscreen mode
python virtual_mouse_fullscreen.py

# Option 3: Use the shell script
bash run_mouse_controller.sh
```

---

## 🤌 Gesture Reference

| Gesture | Action |
|---|---|
| ☝️ Index finger up | Move cursor |
| 🤏 Index + Thumb pinch | Left click |
| ✌️ Index + Middle finger | Right click |
| 🖐️ Open palm (move up/down) | Scroll |
| ✊ Closed fist | Drag / Hold click |

> **Tip:** Ensure good lighting and keep your hand within the webcam frame for best accuracy.

---

## ⚙️ How It Works

```
Webcam Feed
    │
    ▼
MediaPipe Hand Landmark Detection
    │  (21 keypoints per hand)
    ▼
Gesture Classification (hand_pose_controller.py)
    │  (pinch distance, finger angles, etc.)
    ▼
Mouse Event Dispatch (mouse_controller.py)
    │  (move / click / scroll)
    ▼
OS-Level Mouse Control
    │  (PyAutoGUI + ctypes on Windows)
    ▼
Screen Response
```

### Platform-Aware Scrolling

On Windows, standard `pyautogui.scroll()` can feel broken or laggy. This project bypasses it entirely using `ctypes.windll.user32.mouse_event` with `MOUSEEVENTF_WHEEL` for silky-smooth scroll events.

---

## 📋 TODO

See [`TODO.md`](TODO.md) for planned features and known issues.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. Fork the repo
2. Create your branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add your feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 👤 Author

**Dubal Prayag**
- GitHub: [@Dubal-prayag](https://github.com/Dubal-prayag)

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

> *Built with ❤️ and a lot of hand-waving.*
