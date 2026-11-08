"""Procedural art (tiles, props, enemies, UI) in a 16-bit console style.
Character art from input/ is handled by sprites.py."""
import math
import random

import pygame

from settings import PAL, GAMEW, GAMEH

_font_cache = {}


def get_font(size, bold=False):
    """16-bit style bitmap font (see pixelfont.py), cached per size."""
    from pixelfont import PixelFont
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = PixelFont(size, bold)
    return _font_cache[key]


def text_w(txt, size, bold=False):
    return get_font(size, bold).size(txt)[0]


def wrap_text(txt, size, maxw, bold=False):
    f = get_font(size, bold)
    lines = []
    for raw in txt.split("\n"):
        cur = ""
        for word in raw.split(" "):
            trial = (cur + " " + word).strip()
            if f.size(trial)[0] <= maxw or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def draw_text(surf, txt, x, y, size=16, color=PAL["text"], bold=False,
              shadow=True, align="left"):
    f = get_font(size, bold)
    img = f.render(txt, False, color)
    if align == "center":
        x -= img.get_width() // 2
    elif align == "right":
        x -= img.get_width()
    if shadow:
        # drop shadow one font-pixel down/right, like console text
        sh = f.render(txt, False, PAL["shadow"])
        surf.blit(sh, (x + f.scale, y + f.scale))
    surf.blit(img, (x, y))
    return img.get_rect(topleft=(x, y))


# --- 16-bit style windows ---------------------------------------------------
PX = 3                         # one "game pixel" at window resolution
WIN_TOP = (52, 76, 186)        # window gradient, top -> bottom
WIN_BOT = (14, 20, 84)
_panel_cache = {}


def _make_panel(w, h):
    """Blue gradient window with a bevelled, pixel-rounded frame."""
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    band = PX * 2
    for y in range(0, h, band):
        t = y / max(1, h - 1)
        col = tuple(int(WIN_TOP[i] + (WIN_BOT[i] - WIN_TOP[i]) * t)
                    for i in range(3))
        s.fill((*col, 236), (0, y, w, band))
    # frame: dark rim, bright bevel, soft inner line (each 1 game pixel)
    rings = [((10, 10, 30, 255), 0), ((236, 240, 252, 255), PX),
             ((150, 166, 214, 255), PX * 2)]
    for col, off in rings:
        r = pygame.Rect(off, off, w - 2 * off, h - 2 * off)
        s.fill(col, (r.x + PX, r.y, r.w - 2 * PX, PX))            # top
        s.fill(col, (r.x + PX, r.bottom - PX, r.w - 2 * PX, PX))  # bottom
        s.fill(col, (r.x, r.y + PX, PX, r.h - 2 * PX))            # left
        s.fill(col, (r.right - PX, r.y + PX, PX, r.h - 2 * PX))   # right
    # knock out the outer corners so the frame reads as rounded
    for cx, cy in ((0, 0), (w - PX, 0), (0, h - PX), (w - PX, h - PX)):
        s.fill((0, 0, 0, 0), (cx, cy, PX, PX))
    # inner corner pixels of the bevel
    for cx, cy in ((PX, PX), (w - 2 * PX, PX), (PX, h - 2 * PX),
                   (w - 2 * PX, h - 2 * PX)):
        s.fill((236, 240, 252, 255), (cx, cy, PX, PX))
    return s


def draw_panel(surf, rect):
    r = pygame.Rect(rect)
    if r.w < PX * 6 or r.h < PX * 6:
        return
    img = _panel_cache.get(r.size)
    if img is None:
        if len(_panel_cache) > 64:
            _panel_cache.clear()
        img = _panel_cache[r.size] = _make_panel(r.w, r.h)
    surf.blit(img, r.topleft)


def draw_bar(surf, rect, frac, fg, bg=(20, 24, 40), border=True):
    r = pygame.Rect(rect)
    if border:
        pygame.draw.rect(surf, (10, 10, 30), r.inflate(4, 4))
        pygame.draw.rect(surf, (200, 210, 236), r.inflate(2, 2), 1)
    pygame.draw.rect(surf, bg, r)
    fw = int(r.w * max(0, min(1, frac)))
    if fw > 0:
        pygame.draw.rect(surf, fg, (r.x, r.y, fw, r.h))
        # glossy highlight + shade, SNES gauge style
        hi = tuple(min(255, c + 70) for c in fg[:3])
        lo = tuple(max(0, c - 60) for c in fg[:3])
        hh = max(1, r.h // 4)
        pygame.draw.rect(surf, hi, (r.x, r.y, fw, hh))
        pygame.draw.rect(surf, lo, (r.x, r.bottom - hh, fw, hh))


_HAND = (
    "..##......",
    ".#OO#.....",
    ".#OO####..",
    "##OOOOOO#.",
    "#OOOOOOOO#",
    "#OOOOOOOO#",
    ".#OOOOOO#.",
    "..######..",
)
_hand_cache = {}


def draw_arrow(surf, x, y, color=PAL["amber"]):
    """Pointing-glove cursor (drawn at 2 window px per pixel)."""
    key = tuple(color)
    img = _hand_cache.get(key)
    if img is None:
        img = pygame.Surface((20, 16), pygame.SRCALPHA)
        fill = (250, 250, 255) if color == PAL["amber"] else color
        for yy, row in enumerate(_HAND):
            for xx, ch in enumerate(row):
                if ch == "#":
                    img.fill((20, 18, 40), (xx * 2, yy * 2, 2, 2))
                elif ch == "O":
                    img.fill(fill, (xx * 2, yy * 2, 2, 2))
        _hand_cache[key] = img
    surf.blit(img, (x - 8, y - 3))


def with_outline(src, color=(26, 22, 36)):
    """Dilate the silhouette 1px and return sprite with a dark contour.
    Result is padded 1px on every side (size +2)."""
    w, h = src.get_size()
    try:
        mask = pygame.mask.from_threshold(
            src, (0, 0, 0, 0), (255, 255, 255, 130))
        mask.invert()
    except pygame.error:
        return src
    sil = mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))
    canvas = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
    for dx in (0, 1, 2):
        for dy in (0, 1, 2):
            if not (dx == 1 and dy == 1):
                canvas.blit(sil, (dx, dy))
    # punch holes where the source itself is transparent (between legs etc.)
    for (hx, hy) in _transparent_cells(src):
        canvas.set_at((hx + 1, hy + 1), (0, 0, 0, 0))
    canvas.blit(src, (1, 1))
    return canvas


def _transparent_cells(src):
    out = []
    w, h = src.get_size()
    for y in range(h):
        for x in range(w):
            r, g, b, al = src.get_at((x, y))
            if al == 0:
                out.append((x, y))
    return out


def draw_gear(surf, cx, cy, r, color, teeth=8):
    pygame.draw.circle(surf, color, (cx, cy), r)
    tr = max(2, r // 4)
    for i in range(teeth):
        a = i * (2 * math.pi / teeth)
        px = cx + int(math.cos(a) * r * 1.12)
        py = cy + int(math.sin(a) * r * 1.12)
        pygame.draw.rect(surf, color, (px - tr // 2, py - tr // 2, tr, tr))
    pygame.draw.circle(surf, (10, 10, 26), (cx, cy), max(1, r // 3))


# ---------------------------------------------------------------------------
# Character sprites: 16x20 grids. Frames: idle, a, b  Directions: down/up/left
# ---------------------------------------------------------------------------
C_BODY = {
    "down": [
        ".....hhhhhhhhhh.....",
        "....hhYYYYYYYYhh....",
        "...hhHHHHHHHHHHhh...",
        "...hHHHHHHHHHHHHh...",
        "..hhHHHHHHHHHHHhh...",
        "..hhHhhhhhhhhhHh....",
        "..ssSSSSSSSSSSSss...",
        "...SSEEWSSSSEWSS....",
        "...SSEESSSSEESS.....",
        "....sSSSSkkSSSs.....",
        "....OOOOOOTOOOO.....",
        "...OOoOTTTOOoOO.....",
        "...SoOOOOOOOOoS.....",
        "....sOOTTTTOOs......",
    ],
    "up": [
        ".....hhhhhhhhhh.....",
        "....hhYYYYYYYYhh....",
        "...hhHHHHHHHHHHhh...",
        "...hHHHHHHHHHHHHh...",
        "..hhHHHHHHHHHHHhh...",
        "..hhHhhhhhhhhhHh....",
        "...OOOOOOOOOOOOO....",
        "..oOOOOOOTOOOOOOo...",
        "..O.OoOOOOoOO...O...",
        "..s..OTTTTO....s....",
        "....OoOOOoOo........",
        "....OoOOOOOOo.......",
        "....OoOOOOOOo.......",
        ".....oOOOOOOo.......",
    ],
    "left": [
        "......hhhhhhh.......",
        ".....hhYYhhhhh......",
        "....hYYHHHHHHh......",
        "....hHHHHHHHHh......",
        "....hHHHHHHHHh......",
        "...hHHHhhhhhhSHh....",
        "....SSEESSSHhs......",
        "....SEEkSSSHs.......",
        ".....SSSSsHs........",
        ".....OOTTTO.........",
        "....OoOOOOOOS.......",
        "....OoOOOOOOs.......",
        "....sOoOOOOo........",
        ".....OOTTTOo........",
    ],
}

def _assert_body():
    import sys  # noqa
    for d, rows in C_BODY.items():
        for r in rows:
            if len(r) != 20:
                raise ValueError(f"C_BODY[{d}] width {len(r)} != 20: {r!r}")


_assert_body()

ACCENTS = {}


def apply_accent(s, direction, acc, pal):
    """Draw per-character accessories over the body grid."""
    T = tuple(pal.get("T", (255, 0, 0)))
    K = (24, 22, 32)
    h = tuple(pal.get("h", (60, 60, 60)))
    Y = tuple(pal.get("Y", tuple(pal.get("H", (255, 255, 255)))))
    if acc == "headband":
        # thin forehead band right where the fringe meets the face
        y = 5
        for x in range(1, s.get_width() - 1):
            r, g, b, al = s.get_at((x, y))
            if al > 0 and ((r, g, b) == tuple(pal["h"]) or
                           (r, g, b) == tuple(pal["H"])):
                s.fill(T, (x, y, 1, 1))
    if acc == "blush":
        for x, y in ((3, 9), (4, 9), (16, 9), (15, 9)):
            s.fill((255, 138, 132), (x, y, 1, 1))
    if acc == "goggles":
        # thin strap + two small lens chips
        s.fill(K, (5, 3, 10, 1))
        lens = (36, 40, 52)
        s.fill(lens, (5, 2, 3, 2))
        s.fill(lens, (11, 2, 3, 2))
        s.fill((255, 220, 120), (6, 2, 1, 1))
        s.fill((255, 220, 120), (12, 2, 1, 1))
    if acc == "bow":
        if direction in ("down", "left", "right"):
            s.fill(T, (15, 2, 3, 1))
            s.fill(T, (15, 3, 2, 3))
            s.fill(K, (17, 4, 1, 1))
        elif direction == "up":
            s.fill(T, (2, 2, 3, 1))
            s.fill(T, (3, 3, 2, 3))
            s.fill(K, (2, 4, 1, 1))
    if acc == "beard":
        if direction == "down":
            s.fill(h, (5, 9, 10, 2))
            s.fill(h, (6, 11, 8, 1))
        else:
            s.fill(h, (3, 8, 6, 2))
            s.fill(h, (4, 10, 5, 1))
    if acc == "apron":
        if direction == "down":
            s.fill(T, (7, 12, 6, 2))
            s.fill(K, (7, 12, 1, 2))
            s.fill(K, (12, 12, 1, 2))
    return s


def _draw_legs(surf, direction, frame, cols):
    """Legs occupy rows 14..19 of the 20-row body grid."""
    O = cols["outfit_d"]
    B = cols["boot"]
    S = cols["S"]

    def leg(x0, lift):
        if lift == 0:
            surf.fill(O, (x0, 14, 3, 4))
            surf.fill(B, (x0, 18, 3, 2))
        else:
            surf.fill(O, (x0, 14, 3, 2))
            surf.fill(B, (x0, 16, 3, 2))

    if direction in ("down", "up"):
        lx, rx = 6, 11
        if frame == "a":
            leg(lx, 0); leg(rx, 1)
        elif frame == "b":
            leg(lx, 1); leg(rx, 0)
        else:
            leg(lx, 0); leg(rx, 0)
    else:
        lx, rx = 7, 10
        leg(lx, 0)
        leg(rx, 1 if frame == "a" else 0)
        if frame != "idle":
            surf.fill(B, (lx - 1, 18, 3, 2))


ACCENTS = {}


def apply_accent(s, direction, acc, pal):
    """Draw per-character accessories over the body grid."""
    T = tuple(pal.get("T", (255, 0, 0)))
    K = (24, 22, 32)
    h = tuple(pal.get("h", (60, 60, 60)))
    Y = tuple(pal.get("Y", tuple(pal.get("H", (255, 255, 255)))))
    if acc == "headband":
        # thin forehead band right where the fringe meets the face
        y = 5
        for x in range(1, s.get_width() - 1):
            r, g, b, al = s.get_at((x, y))
            if al > 0 and ((r, g, b) == tuple(pal["h"]) or
                           (r, g, b) == tuple(pal["H"])):
                s.fill(T, (x, y, 1, 1))
    if acc == "blush":
        for x, y in ((3, 9), (4, 9), (16, 9), (15, 9)):
            s.fill((255, 138, 132), (x, y, 1, 1))
    if acc == "goggles":
        # thin strap + two small lens chips
        s.fill(K, (5, 3, 10, 1))
        lens = (36, 40, 52)
        s.fill(lens, (5, 2, 3, 2))
        s.fill(lens, (11, 2, 3, 2))
        s.fill((255, 220, 120), (6, 2, 1, 1))
        s.fill((255, 220, 120), (12, 2, 1, 1))
    if acc == "bow":
        if direction in ("down", "left", "right"):
            s.fill(T, (15, 2, 3, 1))
            s.fill(T, (15, 3, 2, 3))
            s.fill(K, (17, 4, 1, 1))
        elif direction == "up":
            s.fill(T, (2, 2, 3, 1))
            s.fill(T, (3, 3, 2, 3))
            s.fill(K, (2, 4, 1, 1))
    if acc == "beard":
        if direction == "down":
            s.fill(h, (5, 9, 10, 2))
            s.fill(h, (6, 11, 8, 1))
        else:
            s.fill(h, (3, 8, 6, 2))
            s.fill(h, (4, 10, 5, 1))
    if acc == "apron":
        if direction == "down":
            s.fill(T, (7, 12, 6, 2))
            s.fill(K, (7, 12, 1, 2))
            s.fill(K, (12, 12, 1, 2))
    return s


def _draw_legs(surf, direction, frame, cols):
    """Legs occupy rows 14..19"""
    O = cols["outfit_d"]
    B = cols["boot"]

    def leg(x0, lift):
        if lift == 0:
            surf.fill(O, (x0, 14, 3, 4))
            surf.fill(B, (x0, 18, 3, 2))
        else:
            surf.fill(O, (x0, 14, 3, 2))
            surf.fill(B, (x0, 16, 3, 2))

    if direction in ("down", "up"):
        lx, rx = 4, 9
        if frame == "a":
            leg(lx, 0); leg(rx, 1)
        elif frame == "b":
            leg(lx, 1); leg(rx, 0)
        else:
            leg(lx, 0); leg(rx, 0)
    else:  # side view
        lx, rx = 5, 9
        f = 0 if frame == "idle" else (0 if frame == "a" else 1)
        leg(lx, 0)
        leg(rx, 1 if frame == "a" else 0)
        # forward leg hint when stepping
        if frame != "idle":
            surf.fill(B, (lx - 1, 18, 3, 2))


def build_char_sheet(pal, accent=None):
    """pal: keys H,h,S,E,O,o,T,B (Y optional) -> {(dir,frame): Surface}."""
    pal = dict(pal)
    if "Y" not in pal:   # hair shine = base hair lightened
        H = tuple(pal["H"])
        pal["Y"] = tuple(min(255, c + 46) for c in H)
    cols = {k: tuple(pal[k]) for k in ("H", "h", "S", "E", "O", "T", "B",
                                       "Y")}
    cols["outfit_d"] = tuple(pal["o"])
    cols["boot"] = tuple(pal["B"])
    sheet = {}
    for direction, rows in C_BODY.items():
        for frame in ("idle", "a", "b"):
            s = pygame.Surface((16, 20), pygame.SRCALPHA)
            for y, row in enumerate(rows):
                for x, ch in enumerate(row):
                    if ch != "." and ch in cols:
                        s.fill(cols[ch], (x, y, 1, 1))
            if accent:
                apply_accent(s, direction, accent, pal)
            _draw_legs(s, direction, frame, cols)
            sheet[(direction, frame)] = s
            sheet[("right", frame)] = pygame.transform.flip(s, True, False)
    # dark contour on every frame (pad shifts draw sites by -1)
    for k in list(sheet.keys()):
        sheet[k] = with_outline(sheet[k])
    return sheet


def make_portrait(sheet, scale=4):
    head = sheet[("down", "idle")].subsurface(pygame.Rect(3, 1, 12, 10))
    return pygame.transform.scale(head, (12 * scale, 10 * scale))


# ---------------------------------------------------------------------------
# Tiles (16x16). TILES: char -> Surface, TILES_ANIM: char -> [frames]
# ---------------------------------------------------------------------------
def _noise_dots(s, rng, color, n, area=(1, 1, 14, 14)):
    for _ in range(n):
        x = rng.randint(area[0], area[0] + area[2] - 1)
        y = rng.randint(area[1], area[1] + area[3] - 1)
        s.fill(color, (x, y, 1, 1))


def make_tiles():
    rng = random.Random(7)
    T, A = {}, {}
    GRASS = (96, 152, 60)
    GRASS_D = (74, 122, 46)
    GRASS_L = (118, 178, 74)

    g = pygame.Surface((16, 16))
    g.fill(GRASS)
    _noise_dots(g, rng, GRASS_L, 10)
    _noise_dots(g, rng, GRASS_D, 8)
    T["."] = g
    T["f"] = f = g.copy()
    for i, c in enumerate(((255, 240, 140), (255, 140, 160), (240, 240, 255))):
        x, y = 3 + i * 5, 4 + (i % 2) * 5
        f.fill((70, 130, 50), (x, y + 2, 1, 2))
        f.fill(c, (x, y, 3, 2))
        f.fill((255, 255, 255), (x + 1, y, 1, 1))

    tg = pygame.Surface((16, 16))
    tg.fill((62, 108, 44))
    for i in range(5):
        x = 1 + i * 3 + rng.randint(0, 1)
        h = rng.randint(6, 9)
        y0 = 15 - h
        tg.fill((80, 140, 56), (x, y0, 1, h))
        tg.fill((104, 168, 70), (x, y0, 1, 2))
    _noise_dots(tg, rng, GRASS_D, 6)
    A[","] = [tg, pygame.transform.flip(tg, True, False)]

    tr = pygame.Surface((16, 16), pygame.SRCALPHA)
    tr.blit(g, (0, 0))
    # trunk with root flare
    tr.fill((104, 72, 40), (6, 10, 4, 6))
    tr.fill((84, 56, 32), (6, 10, 1, 6))
    tr.fill((86, 58, 32), (4, 14, 8, 2))
    # canopy: soft blob with dappled light
    pygame.draw.ellipse(tr, (30, 74, 32), (0, -1, 16, 12))
    pygame.draw.ellipse(tr, (44, 106, 44), (1, -1, 13, 10))
    pygame.draw.ellipse(tr, (66, 132, 54), (2, 0, 8, 6))
    tr.fill((84, 148, 64), (3, 1, 3, 1))
    tr.fill((84, 148, 64), (5, 3, 2, 1))
    _noise_dots(tr, random.Random(11), (38, 92, 40), 5, (3, 2, 9, 6))
    T["T"] = tr

    w1 = pygame.Surface((16, 16))
    w1.fill((38, 92, 190))
    for i in range(3):
        x = 2 + i * 5
        w1.fill((70, 130, 220), (x, 3 + (i % 2) * 4, 4, 1))
    w1.fill((24, 64, 140), (0, 15, 16, 1))
    w2 = pygame.Surface((16, 16))
    w2.fill((38, 92, 190))
    for i in range(3):
        x = 7 - i * 2
        w2.fill((70, 130, 220), (x, 2 + (i % 3) * 4, 4, 1))
    w2.fill((24, 64, 140), (0, 0, 16, 1))
    A["~"] = [w1, w2]

    p = pygame.Surface((16, 16))
    p.fill((198, 170, 120))
    _noise_dots(p, rng, (172, 142, 96), 10)
    _noise_dots(p, rng, (224, 198, 152), 6)
    # pebbles only; edges are drawn per-neighbour at map render time
    p.fill((176, 148, 100), (2, 8, 2, 2))
    p.fill((176, 148, 100), (9, 3, 2, 2))
    T["#"] = p

    br = pygame.Surface((16, 16))
    br.blit(p, (0, 0))
    for i in range(3):
        br.fill((110, 78, 44), (0, 2 + i * 4, 16, 2))
    br.fill((96, 66, 36), (0, 0, 16, 1))
    T["B"] = br

    # half-timbered house wall: warm plaster + darker beams + base shadows
    wl = pygame.Surface((16, 16))
    wl.fill((216, 198, 168))
    _noise_dots(wl, random.Random(13), (206, 188, 158), 7)
    beams = (118, 84, 52)
    wl.fill(beams, (0, 0, 16, 2))            # top beam
    wl.fill(beams, (0, 0, 2, 16))            # left post
    wl.fill(beams, (14, 0, 2, 16))           # right post
    wl.fill(beams, (0, 15, 16, 1))           # base
    wl.fill((100, 70, 42), (3, 7, 10, 2))    # mid rail
    wl.fill((158, 152, 140), (0, 5, 2, 8))   # post shading
    wl.fill((160, 150, 138), (14, 6, 2, 8))
    _noise_dots(wl, random.Random(17), (198, 180, 150), 6, (3, 2, 10, 4))
    T["W"] = wl

    def _roof(base, shingle, ridge):
        s = pygame.Surface((16, 16))
        s.fill(base)
        for yy in range(0, 16, 4):
            for xx in range(0, 16, 4):
                s.fill(shingle,
                       (xx + (2 if (yy // 4) % 2 else 0), yy, 3, 3))
        s.fill(ridge, (0, 0, 16, 2))     # ridge cap
        s.fill((max(0, base[0] - 40), max(0, base[1] - 40),
                max(0, base[2] - 40)), (0, 15, 16, 1))
        return s
    T["R"] = _roof((192, 76, 66), (214, 96, 84), (224, 100, 88))
    T["r"] = _roof((70, 92, 150), (94, 118, 172), (110, 136, 190))

    dr = pygame.Surface((16, 16), pygame.SRCALPHA)
    dr.blit(wl, (0, 0))
    dr.fill((96, 66, 38), (0, 14, 16, 2))          # doorstep shadow
    pygame.draw.rect(dr, (70, 46, 26), (2, 2, 12, 13), border_radius=6)
    pygame.draw.rect(dr, (112, 76, 44), (3, 3, 10, 12), border_radius=5)
    dr.fill((86, 58, 34), (3, 3, 10, 1))
    dr.fill((70, 48, 26), (3, 9, 10, 1))
    dr.fill((230, 202, 118), (11, 8, 2, 2))        # knob
    dr.fill((190, 168, 96), (5, 2, 6, 1))          # lintel glint
    T["D"] = dr

    sg = pygame.Surface((16, 16), pygame.SRCALPHA)
    sg.blit(p, (0, 0))
    sg.fill((110, 78, 44), (7, 8, 2, 8))
    pygame.draw.rect(sg, (140, 98, 56), (2, 1, 12, 7), border_radius=2)
    pygame.draw.rect(sg, (90, 62, 34), (2, 1, 12, 7), 1, border_radius=2)
    sg.fill((90, 62, 34), (4, 3, 8, 1))
    sg.fill((90, 62, 34), (4, 5, 6, 1))
    T["s"] = sg

    fl = pygame.Surface((16, 16))
    fl.blit(g, (0, 0))
    for x, c in ((2, (150, 118, 78)), (7, (150, 118, 78)), (12, (150, 118, 78))):
        fl.fill(c, (x, 5, 2, 10))
        fl.fill((172, 142, 96), (x, 5, 2, 2))
    T["x"] = fl

    wd = pygame.Surface((16, 16))
    wd.fill((158, 112, 66))
    for yy in range(0, 16, 3):
        wd.fill((120, 84, 48), (0, yy, 16, 1))
    wd.fill((190, 136, 84), (0, 0, 16, 2))
    T["i"] = wd

    ct = pygame.Surface((16, 16))
    ct.blit(wl, (0, 0))
    ct.fill((128, 92, 52), (0, 2, 16, 14))
    ct.fill((94, 66, 36), (0, 4, 16, 1))
    ct.fill((160, 118, 70), (0, 2, 16, 2))
    T["c"] = ct

    cw = pygame.Surface((16, 16))
    cw.fill((58, 52, 64))
    cw.fill((86, 78, 92), (0, 0, 16, 3))
    for yy in range(0, 16, 4):
        cw.fill((38, 34, 44), (0, yy + 3, 16, 1))
        off = 3 + (9 if (yy // 4) % 2 else -3)
        cw.fill((38, 34, 44), (off, yy, 1, 3))
    T["C"] = cw

    cf = pygame.Surface((16, 16))
    cf.fill((104, 100, 116))
    _noise_dots(cf, rng, (88, 84, 100), 9)
    _noise_dots(cf, rng, (124, 120, 138), 6)
    T["_"] = cf

    # ---- windows: warm glass set into the timber wall ----
    win = pygame.Surface((16, 16), pygame.SRCALPHA)
    win.blit(wl, (0, 0))
    pygame.draw.rect(win, (88, 60, 36), (4, 4, 9, 9), border_radius=2)
    pygame.draw.rect(win, (246, 214, 134), (5, 5, 7, 7), border_radius=1)
    win.fill((255, 236, 170), (6, 5, 2, 2))
    win.fill((88, 60, 36), (8, 5, 1, 7))
    win.fill((88, 60, 36), (5, 8, 7, 1))
    T["Y"] = win

    # wrought-iron lamp post (frames alternate flicker)
    def _lamp(flick):
        s = pygame.Surface((16, 16), pygame.SRCALPHA)
        s.blit(g, (0, 0))
        s.fill((40, 44, 54), (7, 6, 2, 9))
        s.fill((64, 70, 84), (6, 14, 4, 1))
        s.fill((64, 70, 84), (5, 4, 6, 2))
        s.fill((30, 32, 42), (5, 2, 6, 4))
        glass = (255, 216, 120) if not flick else (252, 200, 96)
        s.fill(glass, (6, 3, 4, 2))
        s.fill((90, 96, 110), (7, 1, 2, 1))
        if flick:
            s.fill((255, 236, 170), (6, 2, 1, 1))
        return s
    A["L"] = [_lamp(False), _lamp(True)]

    # stone well with little roof
    wl2 = pygame.Surface((16, 16), pygame.SRCALPHA)
    wl2.blit(g, (0, 0))
    wl2.fill((70, 60, 44), (13, 2, 2, 6))
    wl2.fill((150, 88, 56), (2, 0, 12, 2))
    wl2.fill((190, 128, 84), (2, 0, 12, 1))
    pygame.draw.rect(wl2, (130, 130, 140), (2, 8, 12, 7), border_radius=4)
    pygame.draw.rect(wl2, (150, 150, 160), (3, 8, 4, 2))
    wl2.fill((52, 56, 70), (5, 9, 6, 4))
    wl2.fill((96, 130, 190), (6, 10, 4, 2))
    wl2.fill((170, 178, 192), (2, 9, 1, 4))
    T["o"] = wl2

    # market stall: counter + striped awning
    k = pygame.Surface((16, 16), pygame.SRCALPHA)
    k.blit(g, (0, 0))
    for xx in range(0, 16, 4):
        k.fill((196, 76, 68), (xx, 0, 2, 4))
        k.fill((240, 236, 228), (xx + 2, 0, 2, 4))
    k.fill((60, 48, 40), (0, 4, 1, 10))
    k.fill((60, 48, 40), (15, 4, 1, 10))
    k.fill((156, 104, 62), (0, 8, 16, 7))
    k.fill((116, 74, 44), (0, 8, 16, 1))
    k.fill((116, 74, 44), (0, 14, 16, 1))
    k.fill((90, 140, 70), (3, 6, 3, 3))       # potions on the counter
    k.fill((210, 160, 60), (8, 6, 3, 3))
    k.fill((210, 90, 90), (12, 6, 2, 3))
    T["K"] = k

    # haystack
    h = pygame.Surface((16, 16), pygame.SRCALPHA)
    h.blit(g, (0, 0))
    pygame.draw.ellipse(h, (190, 150, 64), (1, 5, 14, 9))
    pygame.draw.ellipse(h, (214, 176, 84), (3, 6, 8, 4))
    for i, yy in enumerate(range(8, 13, 2)):
        h.fill((160, 122, 48), (2, yy, 12 - (i % 2), 1))
    T["H"] = h

    # bookshelf
    e = pygame.Surface((16, 16), pygame.SRCALPHA)
    e.blit(wd, (0, 0))
    e.fill((92, 60, 34), (0, 0, 16, 16))
    e.fill((58, 38, 22), (0, 0, 16, 2))
    e.fill((58, 38, 22), (0, 7, 16, 2))
    e.fill((58, 38, 22), (1, 1, 1, 14))
    for i, c in enumerate(((190, 70, 60), (70, 110, 190), (220, 180, 80),
                           (90, 160, 90), (200, 110, 160))):
        e.fill(c, (2 + i * 3, 2, 2, 5))
        e.fill(c, (2 + i * 2, 9, 2, 5))
    T["e"] = e

    # single bed
    d = pygame.Surface((16, 16), pygame.SRCALPHA)
    d.blit(wd, (0, 0))
    d.fill((112, 78, 46), (1, 0, 14, 15))
    d.fill((86, 58, 34), (1, 0, 14, 1))
    d.fill((238, 238, 232), (2, 5, 12, 10))    # mattress
    d.fill((255, 255, 255), (2, 1, 12, 4))     # pillow
    d.fill((96, 120, 190), (2, 9, 12, 6))      # blanket
    d.fill((120, 146, 220), (2, 9, 12, 1))
    T["d"] = d

    # round rug (walkable decor)
    n = pygame.Surface((16, 16), pygame.SRCALPHA)
    n.fill((176, 70, 64))
    pygame.draw.circle(n, (210, 96, 88), (8, 8), 7)
    pygame.draw.circle(n, (140, 52, 48), (8, 8), 7, 1)
    pygame.draw.circle(n, (228, 150, 120), (8, 8), 4)
    pygame.draw.circle(n, (176, 70, 64), (8, 8), 2)
    _noise_dots(n, rng, (160, 60, 56), 3, (1, 1, 14, 14))
    T["n"] = n

    # cavern: stalagmite cluster
    v = pygame.Surface((16, 16), pygame.SRCALPHA)
    v.blit(cf, (0, 0))
    v.fill((70, 64, 84), (6, 4, 3, 12))
    v.fill((70, 64, 84), (10, 8, 2, 9))
    v.fill((70, 64, 84), (3, 10, 2, 6))
    v.fill((94, 90, 112), (6, 4, 1, 12))
    v.fill((94, 90, 112), (10, 8, 1, 9))
    v.fill((44, 40, 56), (6, 15, 3, 1))
    T["V"] = v

    # glowing mushroom cluster
    u = pygame.Surface((16, 16), pygame.SRCALPHA)
    u.blit(cf, (0, 0))
    pygame.draw.rect(u, (150, 188, 210), (7, 10, 1, 3))
    pygame.draw.rect(u, (150, 188, 210), (4, 11, 1, 2))
    pygame.draw.rect(u, (150, 188, 210), (10, 12, 1, 2))
    pygame.draw.ellipse(u, (120, 170, 220), (5, 6, 5, 4))
    pygame.draw.ellipse(u, (150, 220, 240), (8, 10, 3, 2))
    pygame.draw.ellipse(u, (96, 150, 200), (2, 9, 3, 2))
    u.fill((220, 250, 255), (6, 7, 1, 1))
    u.fill((220, 250, 255), (9, 10, 1, 1))
    T["U"] = u

    # heap of old gears
    gg = pygame.Surface((16, 16), pygame.SRCALPHA)
    gg.blit(cf, (0, 0))
    for cx, cy, r in ((5, 11, 3), (10, 12, 2), (8, 5, 4)):
        col = (128, 134, 150)
        pygame.draw.circle(gg, col, (cx, cy), r)
        pygame.draw.circle(gg, (96, 100, 118), (cx, cy), r, 1)
        for aa in range(6):
            ang = aa * 3.14159 / 3
            px = cx + int(math.cos(ang) * (r + 1))
            py = cy + int(math.sin(ang) * (r + 1))
            gg.fill(col, (px - 1, py - 1, 2, 2))
        pygame.draw.circle(gg, (70, 66, 84), (cx, cy), max(1, r // 3))
    gg.fill((210, 160, 70), (8, 4, 1, 3))     # rust glint
    T["g"] = gg

    # wall torch (two flame frames) -- drawn with glow at render time
    def _torch(f):
        s = pygame.Surface((16, 16), pygame.SRCALPHA)
        s.blit(cf, (0, 0))
        s.fill((104, 70, 44), (7, 8, 2, 8))
        s.fill((80, 54, 34), (7, 8, 1, 8))
        s.fill((150, 148, 164), (5, 7, 6, 2))
        if f == 0:
            s.fill((255, 190, 70), (6, 4, 4, 4))
            s.fill((255, 236, 150), (7, 5, 2, 3))
        else:
            s.fill((255, 170, 60), (6, 3, 4, 5))
            s.fill((255, 240, 170), (7, 4, 2, 3))
            s.fill((255, 250, 220), (7, 5, 1, 2))
        return s
    A["t"] = [_torch(0), _torch(1)]

    return T, A


def make_props():
    """chest closed/open, save crystal frames, barrel."""
    P = {}
    ch = pygame.Surface((14, 11), pygame.SRCALPHA)
    ch.fill((140, 92, 48), (0, 4, 14, 7))
    ch.fill((112, 72, 36), (0, 4, 14, 1))
    pygame.draw.rect(ch, (170, 118, 62), (0, 0, 14, 4), border_radius=3)
    ch.fill((90, 58, 28), (0, 0, 14, 1))
    ch.fill((220, 180, 90), (6, 3, 2, 3))
    ch.fill((220, 180, 90), (0, 6, 14, 1))
    ch = with_outline(ch, (30, 22, 30))
    P["chest_closed"] = ch

    op = pygame.Surface((14, 9), pygame.SRCALPHA)
    op.fill((98, 62, 30), (0, 0, 14, 9))
    pygame.draw.rect(op, (170, 118, 62), (0, 5, 14, 4))
    op.fill((60, 40, 20), (1, 1, 12, 3))
    op.fill((220, 180, 90), (6, 5, 2, 2))
    op = with_outline(op, (30, 22, 30))
    P["chest_open"] = op

    b = pygame.Surface((9, 11), pygame.SRCALPHA)
    b.fill((112, 106, 128), (1, 0, 7, 11))
    b.fill((146, 140, 160), (1, 1, 2, 9))
    b.fill((88, 82, 100), (6, 1, 2, 9))
    b.fill((170, 164, 184), (1, 3, 7, 1))
    b.fill((170, 164, 184), (1, 8, 7, 1))
    P["barrel"] = b

    cr = []
    for i, glint in enumerate((2, 5, 8, 5)):
        c = pygame.Surface((12, 14), pygame.SRCALPHA)
        c.fill((88, 84, 96), (1, 12, 10, 2))
        c.fill((120, 116, 130), (3, 11, 6, 1))
        pts = [(6, 0), (11, 5), (6, 10), (1, 5)]
        pygame.draw.polygon(c, (110, 220, 230), pts)
        pygame.draw.polygon(c, (60, 160, 180), pts, 1)
        pygame.draw.polygon(c, (180, 255, 255), [(6, 1), (9, 5), (6, 9)])
        c.fill((255, 255, 255), (glint, 3, 1, 3))
        cr.append(with_outline(c, (30, 22, 30)))
    P["crystal"] = cr

    # radial glows for torches (warm) and crystals (cyan)
    def _glow(r, col, alpha):
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for i in range(r, 0, -1):
            aa = int(alpha * (1 - i / r))
            pygame.draw.circle(s, (*col, aa), (r, r), i)
        return s
    P["glow_warm"] = _glow(24, (255, 170, 70), 46)
    P["glow_cyan"] = _glow(24, (130, 220, 240), 40)

    # soft edges for road tiles drawn neighbour-aware
    edge = pygame.Surface((16, 1), pygame.SRCALPHA)
    edge.fill((148, 118, 74, 200))
    edgev = pygame.Surface((1, 16), pygame.SRCALPHA)
    edgev.fill((148, 118, 74, 200))
    P["edge_top"] = edge
    P["edge_bottom"] = edge
    P["edge_left"] = edgev
    P["edge_right"] = edgev

    # actor drop shadow blob
    sh = pygame.Surface((16, 8), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (8, 12, 24, 80), (0, 0, 16, 8))
    P["shadow"] = sh
    return P


# ---------------------------------------------------------------------------
# Enemy sprites
# ---------------------------------------------------------------------------
E_GRIDS = {
    "slime": [
        "....gggg....",
        "..ggGGGGgg..",
        ".gGGWWGGGGg.",
        ".gGGGGGGGGg.",
        ".gGBWGGWBGg.",
        ".gGGGGGGGGg.",
        ".gGGBBGGGBg.",
        ".gGGGGGGGGg.",
        "..gGGGGGGg..",
        "...gggggg...",
    ],
    "bat": [
        ".b........b.",
        ".bb......bb.",
        ".bBb.bb.bBb.",
        "bBBBbbbbBBBb",
        "bBBBBbbBBBBb",
        ".bBWBbbBWBb.",
        "..bBBbbBBb..",
        "...bbbBbb...",
        "....b..b....",
    ],
    "wolf": [
        "..gg......gg....",
        "..ggg....gggg...",
        "..gWWg..gggggg..",
        "..ggggggggggg...",
        ".Bgggggggggggg..",
        ".Bggggggggggggg.",
        "..gggggggggggg..",
        "..ggggGgGggggg..",
        "..gggg.gg.ggg...",
        "..gg...gg...gg..",
    ],
    "scrap": [
        "...ssssss...",
        "..sSSSSSSs..",
        "..sSWSSWSs..",
        "..sSSSSSSs..",
        "..sSrRRrSs..",
        "...ssssss...",
        "..s.____.s..",
        "..sSSSSSSs..",
        "..sSSSSSSs..",
        "..sSrrrrSs..",
        "..sSSSSSSs..",
        "...ssssss...",
        "...dd..dd...",
        "..ddd..ddd..",
    ],
    "boss": [
        "........gggggg..........",
        "......ggYYGGYYgg........",
        "....ggGGGGGGGGGGgg......",
        "...gGGGGGGGGGGGGGGg.....",
        "...gGGGGGGGGGGGGGGg.....",
        "...ggRRRyYYYYyRRRgg.....",
        "...ggRRRyYYYYyRRRgg.....",
        "....ggGGGGGGGGGGgg......",
        "......ggGGGGGGgg........",
        ".......ssssssss.........",
        "....GGGGGGGGGGGGGG......",
        "...GGGGGGGGGGGGGGGGG....",
        "..dGGGGGgGGGGgGGGGGd....",
        "..dGGGGGgggYgggGGGGd....",
        "..dGGGGGGgYYgGGGGGGd....",
        "..dGGGGGGgYYgGGGGGGd....",
        "..dGGGGGGggggGGGGGGd....",
        "..dGGGGGGGGGGGGGGGGd....",
        "..dGGGGGGGGGGGGGGGGd....",
        "...ggGGGGGGGGGGGGgg.....",
        "...gggg.GGGGGG.gggg.....",
        "..gggg...gggg...gggg....",
        "..BBBB...gggg...BBBB....",
        ".BBBBBB........BBBBBB...",
        ".........gggg...........",
    ],
}

E_GRIDS.update({
    "snapjaw": [
        "...cc........cc...",
        "..cCCc......cCCc..",
        "..cPCcc....ccPCc..",
        "...ccCCCccCCCcc...",
        "...cCRRRRRRRRc....",
        "..cCRRYYRRYYRRc...",
        "..cCRRRRRRRRRRc...",
        "...cRRRRRRRRc.....",
        "...cRRRRRRRRc.....",
        "..dcCCCCCCCCd..",
        "..d..c....c..d...",
        ".....c....c......",
    ],
    "buccaneer": [
        "....ppppppp....",
        "...pPPPPPPPk...",
        "..pPPKPPPPPk...",
        "..kSSsSskSSk...",
        "...SEkSSSES....",
        "...sSSSSSSs....",
        "....KKKKK......",
        "...CCCCCCCC....",
        "..OCCTTTTCc....",
        "..S.CCCCC.S....",
        "..s.OTTTO.s....",
        "....OOOOO......",
        "....oOOOo......",
        "....OO.OO......",
        "...BBB.BBB.....",
        "...BBB.BBB.....",
    ],
    "jelly": [
        "....jjjj....",
        "..jjJJJJjj..",
        ".jJJWWJJJJj.",
        ".jJJJJJJJJj.",
        "..jJEBBEJj..",
        "..jJJbbJJj..",
        "...jjjjjj...",
        ".j.JjJjJj.J.",
        "j..J.j.J..j.",
        ".j..JjJ..j..",
        "..J.j.j.J...",
        "...j...j....",
    ],
    "hollow": [
        "...hhhhhhh...",
        "..hHHHHHHHh..",
        ".hHHHHHHHHHh.",
        ".hHKKHHKKHHh.",
        ".hHKKHHKKHHh.",
        ".hHHHHKKHHHh.",
        ".hHHHHHHHHHh.",
        ".hHHHHHHHHHh.",
        ".hHhHHHHhHHh.",
        "..hHhhhhHHh..",
        "...hHhhHHh...",
        "..hh.hhh.hh..",
    ],
    "frost_ape": [
        "..hhhhhh....hhhhhh..",
        ".hHHHHHh..hHHHHHh...",
        "hHHHHHHHhhHHHHHHHh..",
        "hHWWHHHHHHHHHHWWHh..",
        ".hHHHKKHHHHKKHHHh...",
        "..hHHHHHHHHHHHHh....",
        ".hWWWWHHHHHHWWWWh...",
        "hWWWWWWWWWWWWWWWW...",
        "hWWWWWWWWWWWWWWWWh..",
        ".hWWWWWWWWWWWWWW....",
        "..hWWWWWWWWWWWW.....",
        "..hWW..hWW.hWW......",
        ".hh....hh...hh......",
        "hh....hh....hh......",
    ],
    "sentry": [
        "...ssssss....",
        "..sSSSSSSs...",
        "..sWSSSSSs...",
        "..SSEEEEES...",
        "..sSSSSSSs...",
        "..sSrrrrSs...",
        "...ssssss....",
        "...d.rr.d....",
        "..dd.||.dd...",
        "..d.ssss.d...",
        "....d..d.....",
        "...dd..dd....",
        "..ddd..ddd...",
    ],
    "rusthook": [
        "....gggggggggggg....",
        "...gGGGGGGGGGGGGg...",
        "..gGGGGGGGGGGGGGGg..",
        ".ggGGHHHHHHHHHHGGgg.",
        ".gGHHRRRRRRRRRRHHGg.",
        ".gGHHRRRRRRRRRRHHGg.",
        ".ggGGRRRRRRRRRRGGgg.",
        "..ggGGGGGGGGGGGGgg..",
        "....gGGGGGGGGGGg....",
        ".....gGGRRRRGGg.....",
        "=....GGGGGGGGGG....=",
        "hh..GGGGGGGGGGGG..hh",
        "hHH.GGGGGGGGGGGG.HHh",
        "hHH.gGGGGGGGGGGg.HHh",
        ".HH..gggggggggg..HH.",
        "......cCCc..cCCc....",
        ".....cCCcc..ccCCc...",
        "....cCCc......ccCc..",
        "...cCC.c......c.CCc.",
        "...cc............cc.",
    ],
    "colossus": [
        "....hhhhhhhhhhhhhh....",
        "...hFFFFFFFFFFFFFFh...",
        "..hFFWFFFFFFFFFFFFh...",
        ".hFFWWFFkkFFkkFFFFFFh.",
        ".hFFFFFIFFFFIFFFFFFFh.",
        ".hFFFFFIFFFFIFFFFFFFh.",
        ".hFFFFFFkkkkkFFFFFFFh.",
        "..hFFFFFFFFFFFFFFFFh..",
        "...hFFFFFFFFFFFFFFh...",
        "..dFFFFFFFFFFFFFFFFFFd",
        "..dFFhFFFFFFFFFFFFhFd.",
        ".dFFhhFFkkkkkkFFFFhhFd",
        ".dFGhhFFFFFFFFFFFFhhGE",
        ".dFGgFFIIIIIIIIFFgGGd.",
        ".dFGgFFFFFFFFFFFFFFGg.",
        ".dGFgFFFhhFFFFhhFFFGE.",
        "..dGgFFhhhhFFhhhhFGE..",
        "..dGgFFFFFFFFFFFFGE...",
        "..dGgFFFFFFFFFFFGE....",
        ".hGGg.hhFhhhhFhh.GGh..",
        ".hGGg...hhFFFF.....GG.",
        ".hhh....hh..hh....hh..",
        "hh......hhhhhhh....he.",
    ],
    "archon": [
        "0WWW0........0WWW0",
        "WWWWWW......WWWWWW",
        "WWWWWWW....WWWWWWW",
        ".WWWWWWggggWWWWWW.",
        ".WWWWWGGGGGGWWWWW.",
        ".WWWWGGGGGGGGWWWW.",
        ".WWWGWWWWWWWWGWWW.",
        ".WWYGWWRWRWRYGWWW.",
        ".WWGGWRRYYRRWGGWW.",
        ".WWGGWRRYYRRWGGWW.",
        ".WWWGWRRRRRRWGWWW.",
        ".WWWWGWWWWWWGWWWW.",
        ".WWWWGGGGGGGGWWWW.",
        "..WWWGGGGGGGGWWW..",
        "..WWGGGGGGGGGGWW..",
        "..0WGGGGGGGGGGW0..",
        "....GGGdWWdGGG....",
        "...GGGGdYYdGGGG...",
        "..GGGGGdYYdGGGGG..",
        "..GGGG.dGGd.GGGG..",
        "...GG..dYYd..GG...",
        "...G..GdYYd.G..G..",
        "......GdGGd.G.....",
        "......G.00.G......",
    ],
    "millwright": [
        "....gggggg....",
        "...gGGGGGGg...",
        "..gGGGGGGGGg..",
        "..gGRRWGRRGg..",
        "..gGSSSSSSGg..",
        "...gGGGGGGg...",
        "....dWWWWd....",
        "..d.GGGGGG.d..",
        "..dGgGGGGgGd..",
        "..dGgGyyGgGd..",
        "..dGggggggGd..",
        "...d.GGGG.d...",
        "....dGGGGd....",
        "....gggggg....",
        "...gg....gg...",
        "..gV....Vg....",
        "..VV....VV....",
    ],
})

E_PAL = {
    "slime": {"g": (30, 90, 86), "G": (56, 176, 168), "W": (230, 250, 250),
              "B": (20, 40, 60), "R": (230, 250, 250), "Y": (255, 220, 90),
              "y": (255, 220, 90), "S": (-1, -1, -1), "d": (-1, -1, -1),
              "s": (-1, -1, -1), "b": (-1, -1, -1), "_": (-1, -1, -1), "r": (-1, -1, -1)},
    "bat": {"b": (70, 40, 100), "B": (130, 80, 190), "W": (255, 80, 90),
            "R": (255, 80, 90), "Y": (255, 220, 90), "y": (255, 220, 90),
            "G": (-1, -1, -1), "g": (-1, -1, -1), "S": (-1, -1, -1),
            "d": (-1, -1, -1), "s": (-1, -1, -1), "_": (-1, -1, -1), "r": (-1, -1, -1)},
    "wolf": {"g": (90, 96, 118), "G": (120, 128, 152), "W": (240, 244, 255),
             "B": (30, 32, 48), "R": (255, 80, 90), "Y": (255, 220, 90),
             "y": (255, 220, 90), "S": (-1, -1, -1), "d": (-1, -1, -1),
             "s": (-1, -1, -1), "b": (-1, -1, -1), "_": (-1, -1, -1), "r": (-1, -1, -1)},
    "scrap": {"s": (60, 66, 80), "S": (150, 160, 178), "d": (40, 44, 56),
              "W": (120, 220, 255), "r": (200, 90, 70), "R": (255, 120, 100),
              "_": (90, 96, 110), "G": (-1, -1, -1), "g": (-1, -1, -1),
              "b": (-1, -1, -1), "B": (-1, -1, -1), "y": (-1, -1, -1)},
    "boss": {"g": (56, 60, 78), "G": (140, 148, 168), "R": (255, 70, 60),
             "Y": (255, 220, 90), "y": (255, 220, 90), "B": (30, 32, 44),
             "W": (255, 255, 255), "s": (70, 74, 92), "d": (40, 44, 56),
             "S": (-1, -1, -1), "b": (-1, -1, -1), "r": (-1, -1, -1),
             "_": (-1, -1, -1)},
}


E_GRIDS.update({
    "ember_slug": E_GRIDS["slime"],
    "snow_wolf": E_GRIDS["wolf"],
    "cog_drone": E_GRIDS["scrap"],
    "gloom_jelly": E_GRIDS["jelly"],
})

E_PAL_NEW = {
    "snapjaw": {"c": (60, 30, 30), "C": (120, 70, 60), "P": (240, 190, 140),
                "R": (230, 120, 70), "Y": (255, 230, 150), "d": (70, 40, 40)},
    "buccaneer": {"p": (150, 40, 40), "P": (220, 90, 80), "k": (40, 20, 30),
                  "S": (250, 214, 180), "E": (30, 24, 30), "s": (220, 180, 150),
                  "K": (70, 60, 90), "C": (140, 60, 60), "T": (230, 200, 80),
                  "O": (240, 230, 200), "c": (60, 40, 60), "o": (70, 50, 80),
                  "B": (54, 48, 70)},
    "jelly": {"j": (60, 70, 130), "J": (120, 140, 220), "W": (230, 236, 255),
              "E": (20, 20, 40), "B": (240, 160, 220), "b": (240, 160, 220)},
    "hollow": {"h": (120, 130, 170), "H": (216, 224, 255), "K": (30, 30, 50)},
    "frost_ape": {"h": (140, 160, 200), "H": (220, 232, 250),
                  "W": (244, 248, 255), "K": (40, 50, 70)},
    "sentry": {"s": (52, 56, 70), "S": (150, 158, 176), "W": (120, 220, 255),
               "E": (255, 90, 80), "r": (90, 80, 100), "d": (36, 40, 52)},
    "rusthook": {"g": (60, 50, 70), "G": (150, 120, 170), "H": (210, 160, 90),
                 "R": (230, 110, 90), "c": (70, 80, 120), "C": (130, 150, 200),
                 "h": (70, 60, 90), "=": (200, 200, 220),
                 "d": (30, 30, 44)},
    "colossus": {"h": (90, 120, 170), "F": (200, 226, 255),
                 "W": (250, 252, 255), "k": (50, 70, 110), "I": (140, 210, 250),
                 "d": (50, 44, 70), "G": (170, 205, 240), "E": (240, 220, 130)},
    "archon": {"0": (180, 150, 60), "W": (230, 200, 90), "g": (250, 230, 150),
               "G": (200, 170, 80), "R": (240, 60, 60), "Y": (255, 230, 110),
               "d": (60, 48, 30), "E": (40, 32, 20)},
    "millwright": {"g": (70, 74, 92), "G": (150, 156, 176), "R": (255, 120, 90),
                   "W": (120, 220, 255), "S": (90, 96, 116), "d": (44, 44, 58),
                   "y": (255, 220, 90), "V": (160, 166, 184)},
    "ember_slug": {"g": (120, 50, 30), "G": (230, 120, 80), "W": (255, 220, 160),
                   "B": (60, 24, 18), "R": (255, 160, 120)},
    "gloom_jelly": {"j": (60, 70, 130), "J": (120, 140, 220),
                    "W": (230, 236, 255), "E": (20, 20, 40)},
    "snow_wolf": {"g": (200, 214, 240), "G": (232, 240, 255), "W": (255, 255, 255),
                  "B": (60, 70, 110), "R": (255, 160, 160)},
    "cog_drone": {"s": (40, 44, 58), "S": (130, 136, 158), "d": (28, 30, 40),
                  "W": (255, 120, 90), "r": (255, 140, 90), "R": (255, 90, 70),
                  "_": (80, 86, 104)},
}


def make_enemies():
    out = {}
    for key, lines in list(E_GRIDS.items()):
        pal = E_PAL.get(key) or {}
        pal.update({k: v for k, v in E_PAL_NEW.get(key, {}).items() if
                    v is not None})
        if key not in E_PAL and key not in E_PAL_NEW:
            continue
        w = max(len(l) for l in lines)
        s = pygame.Surface((w, len(lines)), pygame.SRCALPHA)
        for y, line in enumerate(lines):
            for x, ch in enumerate(line):
                c = pal.get(ch, (-1, -1, -1))
                if ch != "." and c[0] >= 0:
                    s.fill(c, (x, y, 1, 1))
        out[key] = with_outline(s)
    out["sky_sentry"] = out["sentry"]   # entity alias
    out["turret"] = out["sentry"]       # battle alias
    out["omega"] = out["boss"]          # superboss shares the boss form
    # tint omega gold
    om = out["omega"].copy()
    om.fill((255, 220, 90, 90), None, pygame.BLEND_RGBA_MULT)
    out["omega"] = om
    # palette-variant battle sprites
    for name, pal in E_PAL_NEW.items():
        if name in E_GRIDS and name not in out:
            lines = E_GRIDS[name]
            w = max(len(l) for l in lines)
            s = pygame.Surface((w, len(lines)), pygame.SRCALPHA)
            palc = {k: v for k, v in pal.items() if v is not None}
            for y, line in enumerate(lines):
                for x, ch in enumerate(line):
                    c = palc.get(ch, (-1, -1, -1))
                    if ch != "." and c[0] >= 0:
                        s.fill(c, (x, y, 1, 1))
            out[name] = with_outline(s)
    return out


def load_assets():
    import tiles16
    tiles, anim, var, over = tiles16.upgrade(*make_tiles())
    over["world"] = tiles16.world_pieces(tiles, var)
    props = tiles16.upgrade_props(make_props())
    enemies = make_enemies()
    import sprites
    small, enemies_battle = sprites.build_enemies()
    enemies.update(small)
    return {"tiles": tiles, "anim": anim, "props": props, "enemies": enemies,
            "enemies_battle": enemies_battle, "var": var, "over": over,
            "objects": sprites.world_objects(), "tex": sprites.textures()}
