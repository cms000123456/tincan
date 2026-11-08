"""Global constants for Tin Can Chronicles."""
import os

TILE = 16
SCALE = 3
VIEW_W, VIEW_H = 20, 11                 # viewport in tiles
GAMEW, GAMEH = VIEW_W * TILE, VIEW_H * TILE   # 320 x 176 low-res world surface
WINW, WINH = GAMEW * SCALE, GAMEH * SCALE     # 960 x 528 window
FPS = 60

# Frames a leader takes to walk one tile (followers trail this many frames apart)
STEP_FRAMES = 9
STEP_SECONDS = STEP_FRAMES / FPS
FOLLOWER_GAP = 10        # frames between followers on the leader's path history

# --- Input mapping -----------------------------------------------------------
KEYMAP = {
    "up":    ("up", "w"),
    "down":  ("down", "s"),
    "left":  ("left", "a"),
    "right": ("right", "d"),
    # a = confirm / Z classic style, b = cancel
    "a": ("z", "return"),
    "b": ("x", "escape"),
    "menu": ("c", "tab"),
    "mute": ("m",),
    "help": ("f1",),
}

# --- Palette -----------------------------------------------------------------
PAL = {
    "panel":    (16, 24, 58, 225),
    "panel_hi": (214, 228, 255),
    "panel_lo": (60, 80, 140),
    "text":     (240, 240, 245),
    "text_dim": (170, 180, 205),
    "amber":    (255, 205, 84),
    "red":      (255, 92, 80),
    "green":    (116, 220, 120),
    "blue":     (110, 170, 255),
    "cyan":     (120, 230, 240),
    "purple":   (200, 130, 255),
    "shadow":   (10, 10, 26),
    "black":    (0, 0, 0),
}

# --- File paths ---------------------------------------------------------------
SAVE_PATH = os.environ.get("TINCAN_SAVE") or os.path.join(
    os.path.expanduser("~"), ".tincan_chronicles_save.json")

# Element colors used in battle for techs / flashes
ELEMENT_COLOR = {
    "fire":  (255, 150, 60),
    "ice":   (150, 210, 255),
    "water": (90, 150, 255),
    "bolt":  (255, 240, 130),
    "wind":  (170, 255, 200),
    "none":  (255, 255, 255),
}
