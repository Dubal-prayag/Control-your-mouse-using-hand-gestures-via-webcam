# Control your mouse using hand gestures via webcam

A Python **virtual mouse** that lets you control the system cursor using hand gestures detected from your webcam.  
It uses MediaPipe Hand Landmarker for 3D hand landmarks, OpenCV for real‑time video, and PyAutoGUI (plus a low‑level Windows API fix) for buttery‑smooth cursor movement, clicking, scrolling, and screenshots.[web:9][web:12][web:15]

---

## Features

- Cursor control with index finger pointing.
- Left and right click using pinch gestures.
- Ultra‑smooth scroll with a custom scroll engine (fixes choppy `pyautogui.scroll` on Windows by calling the OS wheel event directly).[web:3][web:10]
- Screenshot gesture that captures the entire screen after a short hand hold.
- On‑screen HUD showing mode, FPS, scroll speed, and a live gesture cheat sheet.
- Tunable sensitivity and scroll speed at runtime via keyboard hotkeys.

---

## Gestures

- ☝ **Index finger only** → Move mouse.
- 🤏 **Thumb + Index pinch** → Left click.
- 🤏 **Thumb + Middle pinch** → Right click.
- ✌ **Index + Middle extended (ring + pinky curled)** → Scroll (hand up = scroll up, hand down = scroll down).
- 🖖 **Index + Middle + Ring extended, hold ~2 seconds** → Take screenshot.

---

## Hotkeys

- `Q` / `E` – Make pinch detection looser / tighter.
- `W` – Reset pinch threshold.
- `A` / `D` – Increase / decrease scroll speed.
- `S` – Reset scroll speed.
- `ESC` – Exit the app.

All hotkey changes are shown as small pop‑up toasts in the camera window.

---

## Requirements

- Python 3.9+ (tested on Windows; code is written to also handle Linux and macOS).  
- A working webcam.  
- Packages:
  - `opencv-python`
  - `mediapipe>=0.10`
  - `pyautogui`
  - `numpy`
  - `xdotool` (Linux only, optional but recommended for smoother scroll).[web:6][web:16]

---
