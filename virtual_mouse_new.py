"""
╔══════════════════════════════════════════════════════════════════╗
║        Virtual Mouse PRO  —  v7  FINAL                           ║
║        mediapipe >= 0.10  |  Windows / Linux / Mac               ║
╠══════════════════════════════════════════════════════════════════╣
║  ROOT CAUSE FIX (why scroll was broken in every prev version):   ║
║  pyautogui.scroll() on Windows sends WHEEL_DELTA=120 per call    ║
║  = one hard coarse jump. Cannot be made smooth.                  ║
║  v7 uses ctypes.windll.user32.mouse_event() directly with        ║
║  small delta (15–40) per frame = true butter-smooth scrolling.   ║
╠══════════════════════════════════════════════════════════════════╣
║  GESTURES                                                        ║
║   ☝  Index finger only         →  Move mouse                    ║
║   🤏  Thumb + Index pinch       →  Left Click                   ║
║   🤏  Thumb + Middle pinch      →  Right Click                  ║
║   ✌   Index + Middle UP         →  SCROLL (hand up=up, dn=dn)  ║
║   🖖  Index+Middle+Ring 2s      →  Screenshot                   ║
╠══════════════════════════════════════════════════════════════════╣
║  HOTKEYS                                                         ║
║   Q/E  = pinch looser/tighter   W = reset pinch                  ║
║   A/D  = scroll faster/slower   S = reset scroll speed           ║
║   ESC  = exit                                                    ║
╚══════════════════════════════════════════════════════════════════╝
"""

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.vision import HandLandmarkerOptions
import numpy as np
import pyautogui
import time, os, sys, datetime, collections, platform

# ───────────────────────────────────────────────────────────────────
#  PLATFORM-AWARE SMOOTH SCROLL  (this is the core fix)
# ───────────────────────────────────────────────────────────────────
_OS = platform.system()

if _OS == "Windows":
    import ctypes
    # WHEEL_DELTA = 120 = one full notch.
    # We send much smaller deltas per frame for smooth scrolling.
    MOUSEEVENTF_WHEEL = 0x0800
    _u32 = ctypes.windll.user32

    def _do_scroll(delta_units: int):
        """
        delta_units: positive = scroll UP, negative = DOWN.
        Range: ±15 to ±120 per call. We'll send ±20–60.
        Bypasses pyautogui completely — fixes the Windows broken scroll.
        """
        if delta_units == 0:
            return
        _u32.mouse_event(MOUSEEVENTF_WHEEL,
                         ctypes.c_long(0), ctypes.c_long(0),
                         ctypes.c_long(int(delta_units)), 0)

elif _OS == "Darwin":  # macOS
    def _do_scroll(delta_units: int):
        if delta_units == 0:
            return
        # pyautogui works fine on macOS
        pyautogui.scroll(int(delta_units // 10))

else:  # Linux
    def _do_scroll(delta_units: int):
        if delta_units == 0:
            return
        # xdotool is more reliable on Linux
        import subprocess
        btn = 4 if delta_units > 0 else 5
        reps = max(1, abs(delta_units) // 30)
        for _ in range(reps):
            try:
                subprocess.Popen(['xdotool', 'click', '--clearmodifiers', str(btn)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except FileNotFoundError:
                pyautogui.scroll(1 if delta_units > 0 else -1)
                break

# ───────────────────────────────────────────────────────────────────
#  CONFIG  — tune these to your preference
# ───────────────────────────────────────────────────────────────────
CAMERA_INDEX     = 0
FRAME_W, FRAME_H = 1280, 720

# Mouse smoothing
SMOOTH_SLOW      = 0.10   # precision when still
SMOOTH_FAST      = 0.45   # responsiveness when moving
SMOOTH_SPEED_REF = 0.05

# Click (hand-size normalised distances)
CLICK_THRESH     = 0.30   # pinch distance threshold (raise = easier to click)
CLICK_SEP        = 1.5    # other finger must be this much farther
CLICK_DEBOUNCE   = 0.35   # seconds between click fires
CLICK_STEP       = 0.03
CLICK_MIN        = 0.12
CLICK_MAX        = 0.55

# Gesture confirmation
CONFIRM_FRAMES_CLICK  = 4   # frames before click fires (prevents flicker)
CONFIRM_FRAMES_SCROLL = 1   # scroll fires almost instantly (no delay wanted)

# Scroll
# SCROLL_DELTA = raw Windows WHEEL units sent per frame (120 = 1 notch)
# ~30 per frame at 30fps = smooth 1 notch/sec baseline
# Hand speed multiplies this.
SCROLL_DELTA_BASE = 35    # units sent per frame when hand is moving slowly
SCROLL_DELTA_MAX  = 110   # cap per frame (close to 1 full notch)
SCROLL_SPEED_MUL  = 3500  # multiplier: hand_dy_per_sec * this = extra delta
SCROLL_DEADZONE   = 0.004 # ignore hand jitter smaller than this (norm coords)
SCROLL_MOMENTUM   = 0.78  # velocity kept per frame after gesture ends (0–1)
SCROLL_PINCH_MIN  = 0.40  # both finger tips must be this far from thumb

# Screenshot
SHOT_HOLD         = 2.0
SHOT_DEBOUNCE     = 4.0

# Screen mapping zone (fraction of frame used for mouse control)
HX0, HX1 = 0.06, 0.94
HY0, HY1 = 0.08, 0.92

TRAIL_LEN = 22
POPUP_DUR = 1.2

# ───────────────────────────────────────────────────────────────────
#  MEDIAPIPE SETUP
# ───────────────────────────────────────────────────────────────────
HAND_CONN = [
    (0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
    (5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),(15,16),
    (13,17),(17,18),(18,19),(19,20),(0,17),
]

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "hand_landmarker.task")
if not os.path.exists(MODEL):
    print("❌  hand_landmarker.task not found!")
    print("   Run: curl -o hand_landmarker.task https://storage.googleapis.com/"
          "mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task")
    sys.exit(1)

detector = mp_vision.HandLandmarker.create_from_options(
    HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MODEL),
        num_hands=1,
        min_hand_detection_confidence=0.55,
        min_hand_presence_confidence=0.55,
        min_tracking_confidence=0.55,
        running_mode=mp_vision.RunningMode.VIDEO,
    ))

def find_save_dir():
    for p in [os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop"),
              os.path.join(os.path.expanduser("~"), "Desktop"),
              os.path.join(os.path.expanduser("~"), "Pictures"),
              os.path.dirname(os.path.abspath(__file__))]:
        try:
            os.makedirs(p, exist_ok=True)
            t = os.path.join(p, "._wt"); open(t,"w").close(); os.remove(t)
            return p
        except: pass
    return "."

SAVE_DIR = find_save_dir()

pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0.0   # remove pyautogui's hidden 100ms delay
SW, SH = pyautogui.size()

cap = cv2.VideoCapture(CAMERA_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
cap.set(cv2.CAP_PROP_FPS,          60)
cap.set(cv2.CAP_PROP_BUFFERSIZE,    1)    # reduce camera latency
if not cap.isOpened():
    print("❌  Cannot open camera."); sys.exit(1)

# ───────────────────────────────────────────────────────────────────
#  STATE
# ───────────────────────────────────────────────────────────────────
pmx, pmy          = 0.0, 0.0
pnx, pny          = 0.5, 0.3
click_thresh      = CLICK_THRESH
last_click_t      = 0.0
last_shot_t       = 0.0
shot_start        = None
prev_t            = time.time()
frame_ts          = 0
trail             = collections.deque(maxlen=TRAIL_LEN)
mode              = "MOVE"
fps_smooth        = 30.0

popup_txt         = ""
popup_col         = (255, 255, 255)
popup_t           = 0.0

# Scroll state
scroll_vel        = 0.0    # current velocity in WHEEL units/sec
scroll_prev_y     = None   # previous midpoint Y for delta calc
scroll_speed_mul  = float(SCROLL_SPEED_MUL)  # mutable via A/D keys

# Confirmation
conf_g            = None
conf_n            = 0
confirmed         = None

WIN = "Virtual Mouse PRO — v7"
cv2.namedWindow(WIN, cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty(WIN, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

print(f"╔══ Virtual Mouse PRO  v7  [{_OS}] ══╗")
print(f"║  Scroll engine : ctypes direct ({'active' if _OS == 'Windows' else 'platform fallback'})")
print(f"║  Screenshots   : {SAVE_DIR}")
print(f"╚══════════════════════════════════╝")

# ───────────────────────────────────────────────────────────────────
#  GEOMETRY HELPERS
# ───────────────────────────────────────────────────────────────────

def d3(a, b):
    return float(np.sqrt((a.x-b.x)**2 + (a.y-b.y)**2 + (a.z-b.z)**2))

def hs(lm):
    """Hand size = wrist→middle-MCP. Normalises distances for depth."""
    return max(d3(lm[0], lm[9]), 1e-5)

def ext(lm, tip, pip, mcp):
    """True if finger is extended (tip farther from MCP than PIP is)."""
    return d3(lm[tip], lm[mcp]) > d3(lm[pip], lm[mcp])

def map_xy(nx, ny):
    sx = float(np.clip(np.interp(nx, [HX0,HX1], [0, SW]), 0, SW-1))
    sy = float(np.clip(np.interp(ny, [HY0,HY1], [0, SH]), 0, SH-1))
    return sx, sy

def smooth_factor(nx, ny):
    spd = np.hypot(nx - pnx, ny - pny)
    t   = min(spd / SMOOTH_SPEED_REF, 1.0)
    return SMOOTH_SLOW + (1.0 - t) * (SMOOTH_FAST - SMOOTH_SLOW)

# ───────────────────────────────────────────────────────────────────
#  GESTURE CLASSIFIER
# ───────────────────────────────────────────────────────────────────

def classify(lm):
    """
    Returns (gesture, pi, pm) where:
      gesture ∈ 'move' | 'left' | 'right' | 'scroll' | 'screenshot'
      pi = index-thumb normalised distance
      pm = middle-thumb normalised distance
    
    SCROLL requires:
      • index + middle EXTENDED
      • ring + pinky CURLED
      • pi > SCROLL_PINCH_MIN  (index not near thumb)
      • pm > SCROLL_PINCH_MIN  (middle not near thumb)
      → Triple guard prevents any click from bleeding into scroll
    
    CLICK: distance only, no extension check.
      Index pinches → left.  Middle pinches → right.
      The OTHER finger must be CLICK_SEP times farther to avoid false fires.
    """
    sz = hs(lm)
    pi = d3(lm[8],  lm[4]) / sz   # index  tip ↔ thumb tip
    pm = d3(lm[12], lm[4]) / sz   # middle tip ↔ thumb tip

    ie = ext(lm,  8,  6, 5)   # index  extended?
    me = ext(lm, 12, 10, 9)   # middle extended?
    re = ext(lm, 16, 14, 13)  # ring   extended?
    pe = ext(lm, 20, 18, 17)  # pinky  extended?

    # Screenshot: index + middle + ring up, pinky down
    if ie and me and re and not pe:
        return 'screenshot', pi, pm

    # Scroll: index + middle up, ring + pinky down, BOTH tips away from thumb
    if (ie and me and not re and not pe
            and pi > SCROLL_PINCH_MIN
            and pm > SCROLL_PINCH_MIN):
        return 'scroll', pi, pm

    # Left click: index pinching, middle clearly NOT
    if pi < click_thresh and pm > pi * CLICK_SEP:
        return 'left', pi, pm

    # Right click: middle pinching, index clearly NOT
    if pm < click_thresh and pi > pm * CLICK_SEP:
        return 'right', pi, pm

    return 'move', pi, pm

# ───────────────────────────────────────────────────────────────────
#  CONFIRMATION ENGINE
# ───────────────────────────────────────────────────────────────────

def confirm(raw):
    """
    Clicks need CONFIRM_FRAMES_CLICK frames of stability.
    Scroll fires after CONFIRM_FRAMES_SCROLL (= 1 = instant).
    """
    global conf_g, conf_n, confirmed
    frames_needed = (CONFIRM_FRAMES_CLICK
                     if raw in ('left','right','screenshot')
                     else CONFIRM_FRAMES_SCROLL)
    if raw != conf_g:
        conf_g = raw
        conf_n = 1
    else:
        conf_n = min(conf_n + 1, frames_needed + 10)
    confirmed = raw if conf_n >= frames_needed else None
    return confirmed

# ───────────────────────────────────────────────────────────────────
#  SMOOTH SCROLL ENGINE  (v7 core)
# ───────────────────────────────────────────────────────────────────

def scroll_frame(mid_y_raw: float, dt: float) -> float:
    """
    Called every frame when scroll gesture is active.
    
    Strategy: VELOCITY = BASE_DELTA + hand_speed * MULTIPLIER
      • Even if hand is barely moving → BASE_DELTA fires every frame
        so there is always some scroll happening (prevents "nothing works" feeling)
      • Fast hand movement → large delta → fast scroll
      • All deltas are sent via ctypes (Windows) / fallback for smooth result
    
    Returns current scroll velocity for display.
    """
    global scroll_vel, scroll_prev_y

    if scroll_prev_y is None:
        scroll_prev_y = mid_y_raw
        return 0.0

    # Raw delta: positive = hand moved DOWN in frame (y increases downward in CV)
    dy = mid_y_raw - scroll_prev_y
    scroll_prev_y = mid_y_raw

    # Deadzone: ignore sub-noise
    if abs(dy) < SCROLL_DEADZONE:
        dy = 0.0

    # Velocity in normalised coords / sec
    dy_per_sec = dy / max(dt, 0.005)

    # Convert to WHEEL delta units:
    # Negate: hand UP (dy < 0) → scroll UP (positive WHEEL delta)
    vel_target = -dy_per_sec * scroll_speed_mul

    # Blend: new reading + carry-over from last frame
    scroll_vel = scroll_vel * 0.35 + vel_target * 0.65

    # Clamp
    scroll_vel = float(np.clip(scroll_vel, -SCROLL_DELTA_MAX * 60,
                                            SCROLL_DELTA_MAX * 60))

    # Per-frame delta to actually send
    per_frame = scroll_vel * dt

    # Always add BASE_DELTA in the movement direction so there is
    # a minimum guaranteed scroll even with slow hand movement
    if abs(per_frame) < SCROLL_DELTA_BASE:
        # Use the sign of vel_target if hand is moving, else 0
        sign = np.sign(vel_target) if abs(vel_target) > 5 else 0
        per_frame = sign * SCROLL_DELTA_BASE

    # Hard cap per frame
    per_frame = float(np.clip(per_frame,
                               -SCROLL_DELTA_MAX, SCROLL_DELTA_MAX))

    _do_scroll(int(per_frame))
    return scroll_vel


def scroll_coast(dt: float):
    """Momentum decay when scroll gesture ends."""
    global scroll_vel, scroll_prev_y
    scroll_prev_y = None   # reset anchor
    if abs(scroll_vel) > 10:
        scroll_vel *= SCROLL_MOMENTUM
        _do_scroll(int(scroll_vel * dt))
    else:
        scroll_vel = 0.0


def scroll_reset():
    global scroll_vel, scroll_prev_y
    scroll_vel    = 0.0
    scroll_prev_y = None

# ───────────────────────────────────────────────────────────────────
#  UI HELPERS
# ───────────────────────────────────────────────────────────────────

# Colour constants (BGR)
GRN  = (0, 230, 60)
CYN  = (0, 220, 255)
YLW  = (0, 205, 255)
ORG  = (0, 140, 255)
BLU  = (255, 90, 90)
RED  = (50,  50, 255)
PRP  = (200, 60, 200)
WHT  = (220, 220, 220)
GRY  = (120, 120, 120)
DRK  = (14,  14,  14)

MODE_COL = {"MOVE": GRN, "LEFT CLICK": BLU, "RIGHT CLICK": RED,
            "SCROLL": CYN, "SCREENSHOT": YLW}

def panel(frame, x1, y1, x2, y2, alpha=0.72, bg=DRK, border=None):
    """Semi-transparent rectangle."""
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0: return
    ov = np.full_like(roi, bg)
    cv2.addWeighted(ov, alpha, roi, 1-alpha, 0, roi)
    frame[y1:y2, x1:x2] = roi
    if border:
        cv2.rectangle(frame, (x1,y1), (x2,y2), border, 1)

def set_popup(txt, col):
    global popup_txt, popup_col, popup_t
    popup_txt, popup_col, popup_t = txt, col, time.time()

def draw_landmarks(frame, lm, w, h, raw):
    pts = [(int(p.x*w), int(p.y*h)) for p in lm]
    for a, b in HAND_CONN:
        cv2.line(frame, pts[a], pts[b], (0, 185, 0), 2)
    for x, y in pts:
        cv2.circle(frame, (x,y), 4, (0, 215, 50), -1)
        cv2.circle(frame, (x,y), 4, (0, 70, 0),    1)

    # Tip highlights
    tips = {4: YLW, 8: CYN, 12: ORG, 16: PRP, 20: WHT}
    for idx, col in tips.items():
        cv2.circle(frame, pts[idx], 9, col, 2)

    # Extra ring on active tips
    if raw == 'scroll':
        for i in [8, 12]:
            cv2.circle(frame, pts[i], 14, CYN, 2)
    elif raw == 'left':
        for i in [4, 8]:
            cv2.circle(frame, pts[i], 14, BLU, 2)
    elif raw == 'right':
        for i in [4, 12]:
            cv2.circle(frame, pts[i], 14, RED, 2)

def draw_trail(frame, dq):
    pts = list(dq); n = len(pts)
    for i in range(1, n):
        a = i / n
        cv2.line(frame, pts[i-1], pts[i],
                 (int(255*a), int(120*a), int(255*(1-a))), max(1, int(3*a)))
    if pts:
        cv2.circle(frame, pts[-1], 7, CYN, -1)

def draw_hud(frame, w, h, mode_str, vel):
    """Top-right HUD card."""
    px, py, pw, ph = w-215, 10, 205, 170
    panel(frame, px, py, px+pw, py+ph, alpha=0.82, bg=(6,6,6), border=(55,55,55))
    col = MODE_COL.get(mode_str, WHT)

    cv2.putText(frame, "MODE", (px+10, py+22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, GRY, 1)
    cv2.putText(frame, mode_str, (px+10, py+52),
                cv2.FONT_HERSHEY_SIMPLEX, 0.80, col, 2)
    cv2.line(frame, (px+8, py+60), (px+pw-8, py+60), (45,45,45), 1)

    info = [
        f"Pinch thr  : {click_thresh:.2f}",
        f"Scroll spd : {scroll_speed_mul:.0f}",
        f"FPS        : {fps_smooth:.1f}",
        f"Platform   : {_OS[:3]}",
    ]
    for i, txt in enumerate(info):
        cv2.putText(frame, txt, (px+10, py+78+i*18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.36, GRY, 1)

    # Scroll velocity bar
    if mode_str == "SCROLL":
        bx1 = px+10; bx2 = px+pw-10
        by  = py+154
        panel(frame, bx1, by, bx2, by+10, alpha=0.7, bg=(20,20,20))
        mag = min(abs(vel) / (SCROLL_DELTA_MAX * 30), 1.0)
        bw  = int((bx2 - bx1) * mag)
        bc  = GRN if vel > 0 else BLU
        cv2.rectangle(frame, (bx1, by), (bx1+bw, by+10), bc, -1)
        lbl = f"{'UP' if vel>0 else 'DN'}  {int(abs(vel))}"
        cv2.putText(frame, lbl, (px+10, py+174),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.37, bc, 1)

def draw_guide(frame, w, h):
    """Bottom-left cheat sheet."""
    rows = [
        ("☝  Index only       ", "Move",       GRN),
        ("🤏 Thumb + Index    ", "Left Click",  BLU),
        ("🤏 Thumb + Middle   ", "Right Click", RED),
        ("✌  Index+Middle UP  ", "Scroll",      CYN),
        ("🖖 +Ring  hold 2s   ", "Screenshot",  YLW),
        ("Q/E  A/D  W/S  ESC  ", "tune / exit", GRY),
    ]
    bh = len(rows) * 22 + 10
    panel(frame, 6, h-bh-48, 358, h-44, alpha=0.68, bg=(5,5,5), border=(38,38,38))
    for i, (lbl, act, col) in enumerate(rows):
        y = h - bh - 46 + 18 + i*22
        cv2.putText(frame, lbl, (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.41, GRY, 1)
        cv2.putText(frame, act, (198, y), cv2.FONT_HERSHEY_SIMPLEX, 0.41, col, 1)

def draw_status(frame, w, h, raw, gate, pi, pm):
    """Bottom debug bar."""
    panel(frame, 0, h-32, w, h, alpha=0.78, bg=(5,5,5))
    txt = (f"  raw:{raw:10s}  gate:{str(gate):10s}  "
           f"idx-thu:{pi:.2f}  mid-thu:{pm:.2f}  "
           f"thr:{click_thresh:.2f}  spd:{scroll_speed_mul:.0f}  "
           f"vel:{scroll_vel:.0f}  conf:{conf_n}/{CONFIRM_FRAMES_CLICK}")
    cv2.putText(frame, txt, (8, h-12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.37, (140,140,0), 1)

def draw_confirm_bar(frame, raw, n):
    if raw not in ('left','right') or n <= 0 or n >= CONFIRM_FRAMES_CLICK:
        return
    prog = n / CONFIRM_FRAMES_CLICK
    bw   = int(200 * prog)
    panel(frame, 28, 270, 240, 288, alpha=0.65, bg=(10,10,10))
    cv2.rectangle(frame, (30, 272), (30+bw, 286), (0,195,145), -1)
    cv2.putText(frame, f"Confirming {raw.upper()} CLICK...",
                (30, 268), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0,165,125), 1)

def draw_cooldown(frame, now):
    el = now - last_click_t
    if el >= CLICK_DEBOUNCE: return
    bw = int(220 * el / CLICK_DEBOUNCE)
    panel(frame, 28, 244, 262, 258, alpha=0.65, bg=(10,10,10))
    cv2.rectangle(frame, (30, 246), (30+bw, 256), (0,185,225), -1)
    cv2.putText(frame, "cooldown", (30, 264),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0,145,185), 1)

def draw_scroll_sidebar(frame, w, h, vel, mid_y):
    """Right edge scroll indicator."""
    bx = w - 40
    bt = int(h * HY0) + 8
    bb = int(h * HY1) - 8
    bh = bb - bt

    panel(frame, bx-2, bt-4, bx+30, bb+4, alpha=0.68, bg=(8,8,8), border=(42,42,42))

    mid_y  = 0.5 if mid_y is None else mid_y
    dot_y  = int(bt + min(max(mid_y, 0), 1) * bh)
    dot_y  = max(bt+8, min(bb-8, dot_y))

    mag    = min(abs(vel) / (SCROLL_DELTA_MAX * 30), 1.0)
    fill_h = int(mag * bh * 0.45)
    bc     = GRN if vel > 0 else BLU

    if vel > 0:
        cv2.rectangle(frame, (bx, dot_y-fill_h), (bx+26, dot_y), bc, -1)
    elif vel < 0:
        cv2.rectangle(frame, (bx, dot_y), (bx+26, dot_y+fill_h), bc, -1)

    cv2.circle(frame, (bx+13, dot_y), 9, bc if abs(vel) > 1 else GRY, -1)
    cv2.circle(frame, (bx+13, dot_y), 9, (0,0,0), 1)

    if vel > 5:
        cv2.putText(frame, "U", (bx+7, bt+16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, GRN, 1)
    elif vel < -5:
        cv2.putText(frame, "D", (bx+7, bb-6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, BLU, 1)

def draw_shot_arc(frame, w, h, start, now):
    prog = min((now - start) / SHOT_HOLD, 1.0)
    cx, cy, r = w//2, h//2, 65
    cv2.circle(frame, (cx, cy), r, (30,30,30), 9)
    pts = []
    for deg in range(0, int(360*prog), 2):
        rad = np.radians(deg - 90)
        pts.append((int(cx + r*np.cos(rad)), int(cy + r*np.sin(rad))))
    for i in range(1, len(pts)):
        cv2.line(frame, pts[i-1], pts[i], YLW, 5)
    cv2.putText(frame, f"{int(prog*100)}%", (cx-24, cy+11),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, YLW, 2)
    cv2.putText(frame, "Hold — screenshot", (cx-125, cy+r+32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, (170,145,0), 1)

def draw_popup(frame, w, h, now):
    if not popup_txt: return
    el = now - popup_t
    if el > POPUP_DUR: return
    alpha = 1.0 if el < POPUP_DUR*0.65 else max(0, 1-(el-POPUP_DUR*0.65)/(POPUP_DUR*0.35))
    sl = min(el/0.09, 1.0); sl = 1-(1-sl)**3
    py = int(-65 + sl*(h//2-18))
    (tw, th), _ = cv2.getTextSize(popup_txt, cv2.FONT_HERSHEY_SIMPLEX, 1.15, 2)
    px = (w-tw)//2; pad = 16
    panel(frame, px-pad, py-th-pad, px+tw+pad, py+pad, alpha=0.88*alpha, bg=(10,10,10))
    cv2.rectangle(frame, (px-pad, py-th-pad), (px+tw+pad, py+pad),
                  tuple(int(c*alpha) for c in popup_col), 2)
    cv2.putText(frame, popup_txt, (px, py), cv2.FONT_HERSHEY_SIMPLEX, 1.15,
                tuple(int(c*alpha) for c in popup_col), 2)

def draw_zone(frame, w, h):
    cv2.rectangle(frame,
                  (int(HX0*w), int(HY0*h)),
                  (int(HX1*w), int(HY1*h)),
                  (38, 38, 38), 1)

# ───────────────────────────────────────────────────────────────────
#  MAIN LOOP
# ───────────────────────────────────────────────────────────────────

while True:
    ret, frame = cap.read()
    if not ret: continue

    frame   = cv2.flip(frame, 1)
    fh, fw, _ = frame.shape
    now     = time.time()
    dt      = max(now - prev_t, 0.005)
    prev_t  = now
    fps_smooth = fps_smooth * 0.92 + (1.0/dt) * 0.08  # EMA

    mp_img   = mp.Image(image_format=mp.ImageFormat.SRGB,
                        data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    frame_ts += 33
    result   = detector.detect_for_video(mp_img, frame_ts)

    draw_zone(frame, fw, fh)

    raw = 'move'; pi = pm = 0.0; gate = None

    if result.hand_landmarks:
        lm   = result.hand_landmarks[0]
        raw, pi, pm = classify(lm)
        gate = confirm(raw)

        nx, ny = lm[8].x, lm[8].y
        trail.append((int(nx*fw), int(ny*fh)))
        draw_trail(frame, trail)
        draw_landmarks(frame, lm, fw, fh, raw)
        draw_confirm_bar(frame, raw, conf_n)

        # ─── SCREENSHOT ────────────────────────────────────────────
        if gate == 'screenshot':
            mode = "SCREENSHOT"
            scroll_reset()
            if shot_start is None: shot_start = now
            draw_shot_arc(frame, fw, fh, shot_start, now)
            if (now-shot_start) >= SHOT_HOLD and (now-last_shot_t) > SHOT_DEBOUNCE:
                ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                path = os.path.join(SAVE_DIR, f"screenshot_{ts}.png")
                cv2.setWindowProperty(WIN, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
                cv2.waitKey(120)
                pyautogui.screenshot().save(path)
                cv2.setWindowProperty(WIN, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                last_shot_t = now; shot_start = None
                set_popup("Screenshot saved!", YLW)
                print(f"📸  {path}")
            cv2.putText(frame, "SCREENSHOT", (30, 92),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, YLW, 2)

        else:
            shot_start = None

            # ─── SCROLL ────────────────────────────────────────────
            # Use raw (not gate) for scroll → fires after 1 frame, no lag
            if raw == 'scroll':
                mode = "SCROLL"
                mid_y = (lm[8].y + lm[12].y) / 2.0
                scroll_vel = scroll_frame(mid_y, dt)

                lbl = (f"SCROLL UP   v={int(abs(scroll_vel))}" if scroll_vel > 5
                       else f"SCROLL DOWN v={int(abs(scroll_vel))}" if scroll_vel < -5
                       else "SCROLL — move hand up or down")
                col = GRN if scroll_vel > 5 else (BLU if scroll_vel < -5 else CYN)
                cv2.putText(frame, lbl, (30, 92),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.95, col, 2)
                cv2.putText(frame, "Hand UP = scroll up  |  Hand DOWN = scroll down",
                            (30, 122), cv2.FONT_HERSHEY_SIMPLEX, 0.43, GRY, 1)
                draw_scroll_sidebar(frame, fw, fh, scroll_vel, mid_y)

            else:
                # ─── MOMENTUM COAST when leaving scroll ────────────
                scroll_coast(dt)

                # ─── MOUSE MOVE ────────────────────────────────────
                alpha    = smooth_factor(nx, ny)
                pnx, pny = nx, ny
                tx,  ty  = map_xy(nx, ny)
                cx2      = pmx + (tx - pmx) * alpha
                cy2      = pmy + (ty - pmy) * alpha
                pmx, pmy = cx2, cy2
                try: pyautogui.moveTo(cx2, cy2, _pause=False)
                except: pass

                # ─── CLICKS ────────────────────────────────────────
                if gate == 'left':
                    mode = "LEFT CLICK"
                    cv2.putText(frame, "LEFT CLICK", (30, 92),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, BLU, 2)
                    if now - last_click_t > CLICK_DEBOUNCE:
                        pyautogui.click(button='left')
                        last_click_t = now
                        set_popup("Left Click", BLU)

                elif gate == 'right':
                    mode = "RIGHT CLICK"
                    cv2.putText(frame, "RIGHT CLICK", (30, 92),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, RED, 2)
                    if now - last_click_t > CLICK_DEBOUNCE:
                        pyautogui.click(button='right')
                        last_click_t = now
                        set_popup("Right Click", RED)

                else:
                    mode = "MOVE"
                    cv2.putText(frame, "Tracking", (30, 92),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, GRN, 2)

                draw_cooldown(frame, now)

        draw_status(frame, fw, fh, raw, gate, pi, pm)

    else:
        # No hand detected
        trail.clear(); shot_start = None
        conf_g = None; conf_n = 0; confirmed = None
        mode   = "MOVE"
        scroll_coast(dt)
        cv2.putText(frame, "No hand detected", (30, 92),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, RED, 2)
        draw_status(frame, fw, fh, "none", None, 0, 0)

    # ─── Persistent HUD ────────────────────────────────────────────
    draw_guide(frame, fw, fh)
    draw_hud(frame, fw, fh, mode, scroll_vel)
    draw_popup(frame, fw, fh, now)
    if mode == "SCROLL":
        draw_scroll_sidebar(frame, fw, fh, scroll_vel, scroll_prev_y)

    cv2.imshow(WIN, frame)

    # ─── Keyboard ──────────────────────────────────────────────────
    key = cv2.waitKey(1) & 0xFF
    if key == 27: break  # ESC

    # Pinch
    elif key in (ord('q'), ord('Q')):
        click_thresh = min(click_thresh + CLICK_STEP, CLICK_MAX)
        set_popup(f"Pinch looser: {click_thresh:.2f}", YLW)
    elif key in (ord('e'), ord('E')):
        click_thresh = max(click_thresh - CLICK_STEP, CLICK_MIN)
        set_popup(f"Pinch tighter: {click_thresh:.2f}", YLW)
    elif key in (ord('w'), ord('W')):
        click_thresh = CLICK_THRESH
        set_popup(f"Pinch reset: {click_thresh:.2f}", CYN)

    # Scroll speed
    elif key in (ord('a'), ord('A')):
        scroll_speed_mul = min(scroll_speed_mul + 300, 8000)
        set_popup(f"Scroll faster: {scroll_speed_mul:.0f}", CYN)
    elif key in (ord('d'), ord('D')):
        scroll_speed_mul = max(scroll_speed_mul - 300, 300)
        set_popup(f"Scroll slower: {scroll_speed_mul:.0f}", CYN)
    elif key in (ord('s'), ord('S')):
        scroll_speed_mul = float(SCROLL_SPEED_MUL)
        set_popup(f"Scroll reset: {scroll_speed_mul:.0f}", CYN)

cap.release()
cv2.destroyAllWindows()
detector.close()
print("Exited.")