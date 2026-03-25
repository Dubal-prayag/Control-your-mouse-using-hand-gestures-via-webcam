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

## Installation

```bash
1. Clone this repository
git clone https://github.com/Dubal-prayag/Control-your-mouse-using-hand-gestures-via-webcam.git
cd Control-your-mouse-using-hand-gestures-via-webcam

2. (Optional) Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate # on Windows

source venv/bin/activate # on Linux / macOS
3. Install dependencies
pip install -r requirements.txt

text

> If you do not have a `requirements.txt` yet, create one with:
> `opencv-python`, `mediapipe>=0.10`, `pyautogui`, `numpy`.

---

## Download the MediaPipe hand model

This project uses the **MediaPipe Hand Landmarker task** model file `hand_landmarker.task`.[web:9][web:15]

From the project root, run:

```bash
curl -o hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
The code expects this file to be in the same folder as virtual_mouse_new.py.

Usage
bash
undefined
From the repo root
python virtual_mouse_new.py

text

- A fullscreen window named **“Virtual Mouse PRO — v7”** will open.
- Stand in front of your webcam and raise your hand.
- Use the gestures listed above to move, click, scroll, and take screenshots.
- Press `ESC` to quit.

If you want a **windowed** version, you can run the alternative script (if present) instead:

```bash
python virtual_mouse_fullscreen.py
How it works (high level)
The camera feed is read using OpenCV and mirrored for a natural “selfie” view.[web:12]

MediaPipe Hand Landmarker detects 21 3D landmarks for your hand in each frame.[web:9][web:15]

The project classifies simple patterns of extended / curled fingers into gestures (move, left click, right click, scroll, screenshot).

Normalised fingertip coordinates are mapped to your screen resolution, with adaptive smoothing so the cursor feels stable when still and responsive when moving.

For scrolling:

On Windows, the app bypasses pyautogui.scroll and calls the low‑level mouse_event wheel API with small deltas for each frame, producing smooth scrolling.[web:3][web:10]

On macOS and Linux, it falls back to pyautogui or xdotool.

Known limitations
Works best in good lighting with a single hand visible.

Gestures may need a bit of practice to trigger consistently.

On Linux, smooth scrolling quality depends on xdotool and the desktop environment.[web:6]

Future improvements
Add multi‑hand support and custom gesture mapping.

Expose settings (thresholds, scroll speed, smoothing) via a config file or GUI.

Package as an installable desktop app.

License
Add your chosen license here (for example, MIT).

text

If you tell me what name and short tagline you want to brand this project with (for example “Virtual Mouse PRO” vs something simpler), I can adjust the title and the intro section to match your personal style.
