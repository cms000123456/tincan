"""16-bit console style map tiles.

Builds richer versions of the base materials (grass, dirt, water, wood,
plaster, roofs, rock, cave floor, snow) with multi-step colour ramps,
hue-shifted shading and ordered dithering, plus several variants per
ground material so large areas don't look like wallpaper.

upgrade(T, A) takes the dicts from assets.make_tiles() and returns
(T, A, VAR, OVER):
  T/A   tiles and animated tiles, with base materials replaced. Composite
        tiles (lamp on grass, bed on floor, ...) are re-based: every pixel
        that still showed the old base material is swapped for the new one.
  VAR   char -> [variant surfaces], picked per map cell.
  OVER  overlay pieces (road / shore edges).
Tiles may be taller than 16px (trees): draw them bottom-aligned.
"""
import math
import random

import pygame

# 4x4 Bayer matrix, values 0..15
BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def shade(c, k):
    """k<0 darkens toward a cool violet, k>0 lightens toward warm cream
    (hue-shifted ramps read as 'painted' rather than flat)."""
    if k < 0:
        return mix(c, (22, 18, 56), min(1.0, -k))
    return mix(c, (255, 246, 200), min(1.0, k))


def dither(x, y, t):
    """True if a pixel at x,y should take the 'next' colour at mix t."""
    return BAYER[y % 4][x % 4] < t * 16


def _noise_field(rng, n=16, cell=4):
    """Tileable smooth value noise in [0,1] (wraps at n)."""
    g = n // cell
    pts = [[rng.random() for _ in range(g)] for _ in range(g)]
    out = [[0.0] * n for _ in range(n)]
    for y in range(n):
        for x in range(n):
            fx, fy = x / cell, y / cell
            x0, y0 = int(fx) % g, int(fy) % g
            x1, y1 = (x0 + 1) % g, (y0 + 1) % g
            tx, ty = fx - int(fx), fy - int(fy)
            tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
            a = pts[y0][x0] + (pts[y0][x1] - pts[y0][x0]) * tx
            b = pts[y1][x0] + (pts[y1][x1] - pts[y1][x0]) * tx
            out[y][x] = a + (b - a) * ty
    return out


def _mottle(s, rng, c0, c1, lo=0.45, hi=0.75, cell=4):
    """Fill with c0, dithering toward c1 where the noise is high."""
    nf = _noise_field(rng, 16, cell)
    for y in range(16):
        for x in range(16):
            t = (nf[y][x] - lo) / (hi - lo)
            s.set_at((x, y), c1 if dither(x, y, max(0, min(1, t))) else c0)


# --- palettes ---------------------------------------------------------------
GRASS = dict(d2=(34, 84, 46), d1=(52, 112, 52), m=(78, 148, 58),
             l1=(112, 178, 70), l2=(160, 208, 96))
DIRT = dict(d2=(120, 82, 54), d1=(158, 116, 74), m=(194, 152, 100),
            l1=(218, 184, 128), l2=(238, 214, 162))
WATER = dict(d2=(22, 44, 124), d1=(34, 72, 172), m=(48, 104, 206),
             l1=(92, 154, 236), l2=(200, 232, 255))
WOOD = dict(d2=(70, 40, 30), d1=(110, 68, 40), m=(150, 98, 56),
            l1=(184, 128, 74), l2=(214, 164, 104))
ROCK = dict(d2=(28, 24, 40), d1=(50, 44, 66), m=(76, 70, 94),
            l1=(108, 102, 128), l2=(146, 140, 166))
CAVE = dict(d1=(70, 66, 88), m=(90, 86, 108), l1=(112, 108, 130))
SNOW = dict(d2=(150, 168, 214), d1=(190, 204, 238), m=(228, 236, 250),
            l1=(246, 250, 255), l2=(255, 255, 255))


def _grass(seed, tufts=6, flowers=0):
    rng = random.Random(seed)
    s = pygame.Surface((16, 16))
    # every variant shares this base so tile seams never show
    _mottle(s, random.Random(100), GRASS["m"], shade(GRASS["m"], -0.07),
            0.6, 0.95, cell=8)
    for _ in range(tufts):
        x, y = rng.randint(1, 11), rng.randint(3, 12)
        # three-blade tuft: light tips, dark roots
        for dx, h in ((0, 1), (1, 2), (2, 1)):
            s.set_at((x + dx, y + 1), GRASS["d1"])
            s.set_at((x + dx, y + 1 - h), GRASS["l1"])
        s.set_at((x + 1, y - 1), GRASS["l2"])
    for _ in range(flowers):
        x, y = rng.randint(1, 13), rng.randint(1, 13)
        c = rng.choice(((255, 236, 120), (255, 150, 170), (240, 240, 255),
                        (170, 190, 255)))
        s.set_at((x, y + 1), GRASS["d1"])
        for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            s.set_at((x + dx, y + dy), c)
        s.set_at((x, y), (255, 255, 230))
    return s


FROST = dict(d2=(92, 100, 120), d1=(128, 134, 140), m=(168, 164, 140),
             l1=(214, 214, 206), l2=(250, 252, 255))


def _tallgrass(phase, GRASS=GRASS, overlay=False):
    rng = random.Random(41)
    s = pygame.Surface((16, 16), pygame.SRCALPHA if overlay else 0)
    if not overlay:
        s.fill(GRASS["d1"])
    for i in range(8):
        x = i * 2 + rng.randint(0, 1)
        h = rng.randint(7, 11)
        lean = (1 if (i + phase) % 2 else 0)
        for k in range(h):
            yy = 15 - k
            xx = x + (lean if k > h * 0.6 else 0)
            c = GRASS["m"] if k < h - 3 else (GRASS["l1"] if k < h - 1
                                                else GRASS["l2"])
            s.set_at((xx % 16, yy), c)
        s.set_at((x % 16, 15), GRASS["d2"])
    for x in range(16):                       # dark root band
        if dither(x, 14, 0.5 if not overlay else 0.25):
            s.set_at((x, 14), GRASS["d2"])
    return s


def _dirt(seed, pebbles=3):
    rng = random.Random(seed)
    s = pygame.Surface((16, 16))
    base = random.Random(200)
    _mottle(s, base, DIRT["m"], shade(DIRT["m"], 0.12), 0.6, 0.95, cell=8)
    nf = _noise_field(base, 16, 8)
    for y in range(16):
        for x in range(16):
            if nf[y][x] < 0.25 and dither(x, y, 0.3):
                s.set_at((x, y), shade(DIRT["m"], -0.1))
    for _ in range(pebbles):
        x, y = rng.randint(2, 12), rng.randint(2, 12)
        s.set_at((x, y), DIRT["l2"])
        s.set_at((x + 1, y), DIRT["l1"])
        s.set_at((x, y + 1), DIRT["d1"])
        s.set_at((x + 1, y + 1), DIRT["d2"])
    return s


def _water(frame, nframes=4):
    s = pygame.Surface((16, 16))
    ph = frame / nframes * 2 * math.pi
    for y in range(16):
        for x in range(16):
            # two crossing wave fields, both periodic over the tile
            v = (math.sin((x / 16) * 2 * math.pi + ph + y * 0.6) +
                 math.sin((y / 16) * 4 * math.pi - ph * 0.5 + x * 0.25)) / 2
            if v > 0.78:
                c = WATER["l1"]
            elif v > 0.45:
                c = WATER["m"] if dither(x, y, 0.5) else WATER["l1"]
            elif v < -0.7:
                c = WATER["d1"]
            else:
                c = WATER["m"]
            s.set_at((x, y), c)
    # sparkles drift with the frame
    for sx, sy in ((3, 4), (11, 11), (13, 2)):
        xx = (sx + frame * 2) % 16
        if (frame + sx) % 3:
            s.set_at((xx, sy), WATER["l2"])
    return s


def _bridge():
    s = pygame.Surface((16, 16))
    for i in range(4):                        # planks across the span
        y = i * 4
        s.fill(WOOD["m"], (0, y, 16, 4))
        s.fill(WOOD["l1"], (0, y, 16, 1))
        s.fill(WOOD["d1"], (0, y + 3, 16, 1))
        s.set_at((3 + (i % 2) * 8, y + 1), WOOD["d2"])   # nail
        s.set_at((10 - (i % 2) * 5, y + 2), WOOD["d1"])  # grain
    for x0 in (0, 14):                        # side rails
        s.fill(WOOD["d2"], (x0, 0, 2, 16))
        s.fill(WOOD["l1"], (x0, 0, 1, 16))
    return s


def _wood_floor(seed):
    rng = random.Random(seed)
    s = pygame.Surface((16, 16))
    for i in range(4):
        y = i * 4
        base = shade(WOOD["m"], rng.uniform(-0.08, 0.06))
        s.fill(base, (0, y, 16, 4))
        s.fill(shade(base, 0.18), (0, y, 16, 1))
        s.fill(WOOD["d1"], (0, y + 3, 16, 1))
        seam = (5 + i * 7) % 16
        s.fill(WOOD["d2"], (seam, y, 1, 3))
        for _ in range(2):                    # grain flecks
            s.set_at((rng.randint(0, 15), y + rng.randint(1, 2)),
                     shade(base, -0.15))
    return s


def _plaster_wall():
    s = pygame.Surface((16, 16))
    pl, pl_d = (226, 208, 176), (196, 176, 146)
    rng = random.Random(13)
    _mottle(s, rng, pl, shade(pl, -0.07), 0.55, 0.9)
    beam, beam_l, beam_d = WOOD["d1"], WOOD["m"], WOOD["d2"]
    s.fill(beam, (0, 0, 16, 2))
    s.fill(beam_l, (0, 0, 16, 1))
    for x0 in (0, 14):
        s.fill(beam, (x0, 0, 2, 13))
        s.fill(beam_l, (x0, 0, 1, 13))
    for x in range(2, 14):                    # shadow under top beam
        s.set_at((x, 2), pl_d)
    s.fill(beam, (2, 7, 12, 1))               # mid rail
    s.fill(beam_d, (2, 8, 12, 1))
    # stone foundation
    st, st_l, st_d = (150, 146, 156), (184, 180, 190), (96, 92, 110)
    s.fill(st, (0, 13, 16, 3))
    s.fill(st_l, (0, 13, 16, 1))
    for x in (4, 10):
        s.fill(st_d, (x, 13, 1, 3))
    s.fill(st_d, (0, 15, 16, 1))
    return s


def _roof(base):
    s = pygame.Surface((16, 16))
    for row in range(4):
        y = row * 4
        off = 2 if row % 2 else 0
        for col in range(-1, 5):
            x = col * 4 + off
            s.fill(base, (x, y, 4, 4))
            s.fill(shade(base, 0.22), (x, y, 4, 1))       # lit top edge
            s.fill(shade(base, -0.35), (x + 3, y, 1, 4))  # side gap
            s.fill(shade(base, -0.2), (x, y + 3, 4, 1))   # lower lip
    for x in range(16):                                   # dither-ish wear
        for y in range(16):
            if dither(x, y, 0.06):
                s.set_at((x, y), shade(base, -0.1))
    s.fill(shade(base, -0.5), (0, 15, 16, 1))
    return s


def _rock_wall(seed):
    """Chunky boulders with lit tops: cave walls."""
    rng = random.Random(seed)
    s = pygame.Surface((16, 16))
    s.fill(ROCK["d2"])
    stones = [(0, 0, 9, 7), (9, 0, 7, 6), (0, 7, 6, 9), (6, 6, 10, 6),
              (6, 12, 10, 4)]
    for (x, y, w, h) in stones:
        x += rng.randint(-1, 0)
        r = pygame.Rect(x + 1, y + 1, w - 1, h - 1)
        pygame.draw.rect(s, ROCK["m"], r, border_radius=2)
        pygame.draw.rect(s, ROCK["d1"], (r.x, r.bottom - 2, r.w, 2),
                         border_bottom_left_radius=2,
                         border_bottom_right_radius=2)
        s.fill(ROCK["l1"], (r.x + 1, r.y, r.w - 2, 1))
        s.set_at((r.x + 1, r.y + 1), ROCK["l2"])
    return s


def _cave_floor(seed):
    rng = random.Random(seed)
    s = pygame.Surface((16, 16))
    _mottle(s, random.Random(300), CAVE["m"], shade(CAVE["m"], -0.1),
            0.6, 0.95, cell=8)
    for _ in range(2):                        # pebbles
        x, y = rng.randint(2, 12), rng.randint(2, 12)
        s.set_at((x, y), CAVE["l1"])
        s.set_at((x + 1, y + 1), CAVE["d1"])
    if rng.random() < 0.35:                   # hairline crack
        x, y = rng.randint(3, 8), rng.randint(3, 10)
        for k in range(4):
            s.set_at((x + k, y + (k // 2)), CAVE["d1"])
    return s


def _snow(seed):
    rng = random.Random(seed)
    s = pygame.Surface((16, 16))
    _mottle(s, random.Random(400), SNOW["m"], mix(SNOW["m"], SNOW["d1"], 0.5),
            0.62, 0.97, cell=8)
    for _ in range(rng.randint(0, 2)):        # small drift shadow
        x, y = rng.randint(2, 10), rng.randint(3, 12)
        for k in range(3):
            s.set_at((x + k, y), mix(SNOW["m"], SNOW["d1"], 0.6))
        s.set_at((x + 1, y - 1), SNOW["l2"])
    for _ in range(2):                        # glints
        s.set_at((rng.randint(2, 13), rng.randint(2, 13)), SNOW["l2"])
    return s


def _tree(grass):
    """16x24 tree: canopy overhangs the tile above (bottom-aligned)."""
    s = pygame.Surface((16, 24), pygame.SRCALPHA)
    s.blit(grass, (0, 8))
    # ground shadow
    for x in range(2, 15):
        for y in (21, 22):
            if dither(x, y, 0.7):
                s.set_at((x, y), GRASS["d2"])
    # trunk
    s.fill(WOOD["d1"], (6, 15, 4, 7))
    s.fill(WOOD["m"], (7, 15, 1, 7))
    s.fill(WOOD["d2"], (9, 15, 1, 7))
    s.fill(WOOD["d1"], (5, 21, 6, 1))
    # canopy: dark silhouette, then lighter blobs offset up-left
    dark, mid, lit, hi = (22, 64, 40), (40, 100, 48), (66, 140, 58), \
        (120, 184, 84)
    for (cx, cy, r) in ((8, 9, 7), (4, 11, 4), (12, 11, 4)):
        pygame.draw.circle(s, (14, 40, 30), (cx, cy), r + 1)
    for (cx, cy, r) in ((8, 9, 7), (4, 11, 4), (12, 11, 4)):
        pygame.draw.circle(s, dark, (cx, cy), r)
    for (cx, cy, r) in ((7, 8, 5), (4, 10, 3), (11, 10, 3)):
        pygame.draw.circle(s, mid, (cx, cy), r)
    for (cx, cy, r) in ((6, 6, 3), (10, 8, 2), (3, 9, 2)):
        pygame.draw.circle(s, lit, (cx, cy), r)
    for (x, y) in ((5, 4), (6, 5), (9, 7), (3, 8), (7, 4)):
        s.set_at((x, y), hi)
    # leaf texture: dithered darker speckle in the mid band
    for y in range(2, 16):
        for x in range(1, 15):
            if s.get_at((x, y))[:3] == mid and dither(x, y, 0.2):
                s.set_at((x, y), dark)
    return s


def _boat(water):
    s = water.copy()
    hull = pygame.Rect(2, 3, 12, 11)
    pygame.draw.ellipse(s, WOOD["d2"], hull)
    pygame.draw.ellipse(s, WOOD["m"], hull.inflate(-2, -2))
    pygame.draw.ellipse(s, WOOD["d1"], hull.inflate(-6, -4))
    s.fill(WOOD["l1"], (5, 6, 6, 1))
    s.fill(WOOD["l1"], (5, 10, 6, 1))
    s.fill((236, 232, 220), (7, 2, 2, 3))     # furled sail on the mast
    s.fill(WOOD["d2"], (7, 5, 2, 4))
    return s


def _edge(grass_pal, depth=3, seed=5):
    """Grass fringe hanging over the top edge of a road tile (16 x depth)."""
    rng = random.Random(seed)
    s = pygame.Surface((16, depth), pygame.SRCALPHA)
    for x in range(16):
        h = 1 + (rng.random() < 0.55) + (rng.random() < 0.2)
        for y in range(min(h, depth)):
            s.set_at((x, y), grass_pal["m"] if y < h - 1 else
                     grass_pal["d1"])
        if h < depth:
            s.set_at((x, h), (*DIRT["d1"], 150))
    return s


def _shore(depth=3):
    """Foam line where water meets land above it."""
    s = pygame.Surface((16, depth), pygame.SRCALPHA)
    for x in range(16):
        s.set_at((x, 0), (*WATER["l2"], 255))
        if x % 3:
            s.set_at((x, 1), (*WATER["l1"], 255))
        if dither(x, 2, 0.5):
            s.set_at((x, 2), (*WATER["l1"], 200))
    return s


def _bank(depth=2):
    """Dark lip where water meets land at its sides/bottom."""
    s = pygame.Surface((16, depth), pygame.SRCALPHA)
    s.fill((*WATER["d2"], 255), (0, 0, 16, 1))
    for x in range(16):
        if dither(x, 1, 0.5):
            s.set_at((x, 1), (*WATER["d1"], 255))
    return s


def _rotations(top):
    """top-edge strip -> dict of the four edge pieces."""
    return {"top": top,
            "bot": pygame.transform.flip(top, False, True),
            "lef": pygame.transform.rotate(top, 90),
            "rig": pygame.transform.rotate(top, -90)}


def _rebase(tile, old_base, new_base):
    """Replace pixels where `tile` still shows `old_base` with `new_base`."""
    out = tile.copy()
    h = min(16, out.get_height())
    for y in range(h):
        for x in range(16):
            if out.get_at((x, y))[:3] == old_base.get_at((x, y))[:3]:
                out.set_at((x, y), new_base.get_at((x, y)))
    return out


def _cut_base(tile, old_base):
    """Make pixels that still show `old_base` transparent (prop overlay)."""
    out = pygame.Surface(tile.get_size(), pygame.SRCALPHA)
    out.blit(tile, (0, 0))
    for y in range(16):
        for x in range(16):
            if out.get_at((x, y))[:3] == old_base.get_at((x, y))[:3]:
                out.set_at((x, y), (0, 0, 0, 0))
    return out


def _counter():
    """Shop counter: polished top, panelled front, shadow at the foot."""
    s = pygame.Surface((16, 16))
    s.blit(_wood_floor(41), (0, 0))
    s.fill(WOOD["d2"], (0, 1, 16, 1))
    s.fill(WOOD["l2"], (0, 2, 16, 1))          # polished top edge
    s.fill(WOOD["l1"], (0, 3, 16, 4))
    s.fill(shade(WOOD["l1"], 0.25), (2, 4, 5, 1))
    s.fill(WOOD["d1"], (0, 7, 16, 1))
    s.fill(WOOD["m"], (0, 8, 16, 6))           # front panels
    for x in (0, 8):
        s.fill(WOOD["d1"], (x, 8, 1, 6))
        s.fill(WOOD["l1"], (x + 2, 9, 4, 1))
    s.fill(WOOD["d2"], (0, 14, 16, 2))
    return s


def upgrade(T, A):
    old = {k: T[k] for k in (".", "#", "_", "i", "W") if k in T}
    PROPS = {}
    # composites become transparent overlays so they can stand on any
    # (textured) ground; V stalagmites also appear on snow
    for k, b in (("V", "_"), ("U", "_"), ("g", "_"), ("H", "."), ("K", "."),
                 ("x", "."), ("s", "#")):
        if k in T and b in old:
            PROPS[k] = _cut_base(T[k], old[b])
    VAR = {}
    VAR["."] = [_grass(s, tufts=n) for s, n in
                ((1, 6), (2, 4), (3, 7), (4, 5), (5, 3), (6, 6))]
    VAR["#"] = [_dirt(s) for s in (11, 12, 13)]
    VAR["_"] = [_cave_floor(s) for s in (21, 22, 23, 24)]
    VAR["w"] = [_snow(s) for s in (31, 32, 33, 34)]
    VAR["i"] = [_wood_floor(s) for s in (41, 42)]
    VAR["C"] = [_rock_wall(s) for s in (51, 52, 53)]
    grass, dirt, cave, wood = VAR["."][0], VAR["#"][0], VAR["_"][0], \
        VAR["i"][0]
    wall = _plaster_wall()

    # re-base composites before their bases are replaced
    rebase = {".": ("f", "x", "o", "K", "H"),
              "#": ("s",),
              "_": ("V", "U", "g"),
              "i": ("e", "d"),
              "W": ("D", "Y", "c")}
    newb = {".": grass, "#": dirt, "_": cave, "i": wood, "W": wall}
    for b, keys in rebase.items():
        if b not in old:
            continue
        for k in keys:
            if k in T:
                T[k] = _rebase(T[k], old[b], newb[b])
    for k, b in (("L", "."), ("t", "_")):
        if k in A and b in old:
            A[k] = [_rebase(f, old[b], newb[b]) for f in A[k]]

    T["."], T["#"], T["_"], T["w"], T["i"] = grass, dirt, cave, \
        VAR["w"][0], wood
    T["f"] = _grass(8, tufts=3, flowers=4)
    T["W"] = wall
    T["R"] = _roof((186, 70, 62))
    T["r"] = _roof((66, 88, 150))
    T["C"] = VAR["C"][0]
    T["B"] = _bridge()
    T["c"] = _counter()
    T["T"] = _tree(grass)
    A[","] = [_tallgrass(0), _tallgrass(1)]
    A["~"] = [_water(f) for f in range(4)]
    T["S"] = _boat(A["~"][0])

    OVER = {"road": {".": _rotations(_edge(GRASS)),
                     "w": _rotations(_edge(SNOW))},
            "shore": _shore(), "bank": _rotations(_bank()),
            "props": PROPS}
    return T, A, VAR, OVER


# ---------------------------------------------------------------------------
# Context pieces for the main world (chosen per cell in world.py)
# ---------------------------------------------------------------------------
def _rock_face(seed):
    """Front face of a cave wall (floor below it): lit lip, strata, dark
    foot - gives dungeons a sense of height."""
    rng = random.Random(seed)
    s = pygame.Surface((16, 16))
    s.fill(ROCK["m"])
    for y in range(16):                       # vertical light falloff
        t = y / 15
        for x in range(16):
            c = mix(ROCK["l1"], ROCK["d1"], t)
            if dither(x, y, (t * 3) % 1):
                c = mix(c, ROCK["d1"], 0.35)
            s.set_at((x, y), c)
    for _ in range(4):                        # vertical cracks / strata
        x = rng.randint(1, 14)
        y0 = rng.randint(2, 6)
        for y in range(y0, min(15, y0 + rng.randint(4, 8))):
            s.set_at((x, y), ROCK["d2"])
            if x + 1 < 16:
                s.set_at((x + 1, y), mix(ROCK["l1"], ROCK["m"], 0.5))
    s.fill(ROCK["l2"], (0, 0, 16, 1))         # lit top lip
    s.fill(ROCK["l1"], (0, 1, 16, 1))
    for x in range(16):                       # dark foot where it meets floor
        s.set_at((x, 15), ROCK["d2"])
        if dither(x, 14, 0.5):
            s.set_at((x, 14), ROCK["d2"])
    return s


def _rock_top(seed):
    """Top of a solid rock mass (seen from above): dark, quiet texture."""
    rng = random.Random(seed)
    s = pygame.Surface((16, 16))
    s.fill(mix(ROCK["d2"], ROCK["d1"], 0.45))
    for _ in range(5):                        # sparse grit
        x, y = rng.randint(1, 14), rng.randint(1, 14)
        s.set_at((x, y), ROCK["d1"])
        s.set_at((x + 1, y + 1), ROCK["d2"])
    return s


def _pine(ground, snowy):
    """16x24 conifer, optionally snow-laden, bottom-aligned like _tree."""
    s = pygame.Surface((16, 24), pygame.SRCALPHA)
    s.blit(ground, (0, 8))
    shadow = (SNOW["d2"] if snowy else GRASS["d2"])
    for x in range(3, 14):
        if dither(x, 22, 0.7):
            s.set_at((x, 22), shadow)
    s.fill(WOOD["d1"], (7, 18, 2, 4))
    s.fill(WOOD["m"], (7, 18, 1, 4))
    dark, mid, lit = (18, 58, 44), (30, 88, 58), (52, 120, 70)
    # three stacked tiers, widest at the bottom
    for top, half, h in ((1, 3, 6), (5, 5, 6), (10, 7, 8)):
        for k in range(h):
            w = max(1, int(half * (k + 1) / h))
            y = top + k
            s.fill((10, 34, 30), (8 - w - 1, y, 2 * w + 2, 1))
            s.fill(dark, (8 - w, y, 2 * w, 1))
            s.fill(mid, (8 - w, y, w + 1, 1))
            if k % 2 == 0:
                s.set_at((8 - w + 1, y), lit)
        if snowy:                              # snow resting on each tier
            for k in range(0, h, 2):
                w = max(1, int(half * (k + 1) / h))
                for x in range(8 - w, 8 + w):
                    if dither(x, top + k, 0.55):
                        s.set_at((x, top + k), SNOW["l1"])
            s.fill(SNOW["l2"], (8 - half, top + h - 1, half, 1))
    s.set_at((8, 0), (10, 34, 30))
    if snowy:
        s.set_at((8, 1), SNOW["l2"])
    return s


def _strip(w, h, alpha, fade=True, vertical=False):
    """Soft shadow strip (dark, alpha fading away from the caster)."""
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    n = w if vertical else h
    for i in range(n):
        a = int(alpha * (1 - i / n)) if fade else alpha
        if vertical:
            s.fill((12, 10, 30, a), (i, 0, 1, h))
        else:
            s.fill((12, 10, 30, a), (0, i, w, 1))
    return s


def _ridge(base):
    """Ridge cap drawn on the top row of a roof."""
    s = pygame.Surface((16, 4), pygame.SRCALPHA)
    s.fill(shade(base, 0.35), (0, 0, 16, 2))
    s.fill(shade(base, -0.45), (0, 2, 16, 1))
    for x in range(0, 16, 4):
        s.set_at((x, 0), shade(base, 0.55))
    return s


def _cloud_layer(w=256, h=192, seed=9, cell=32):
    """Tileable cloud-shadow layer, ordered-dithered (no alpha banding)."""
    rng = random.Random(seed)
    gx, gy = w // cell, h // cell
    pts = [[rng.random() for _ in range(gx)] for _ in range(gy)]
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    col = (16, 18, 44, 46)
    for y in range(h):
        fy = y / cell
        y0, ty = int(fy) % gy, fy - int(fy)
        y1 = (y0 + 1) % gy
        ty = ty * ty * (3 - 2 * ty)
        for x in range(w):
            fx = x / cell
            x0, tx = int(fx) % gx, fx - int(fx)
            x1 = (x0 + 1) % gx
            tx = tx * tx * (3 - 2 * tx)
            a = pts[y0][x0] + (pts[y0][x1] - pts[y0][x0]) * tx
            bb = pts[y1][x0] + (pts[y1][x1] - pts[y1][x0]) * tx
            v = a + (bb - a) * ty
            d = (v - 0.62) / 0.25          # only the densest parts shade
            if d > 0 and dither(x, y, min(1.0, d) * 0.5):
                s.set_at((x, y), col)
    return s


def _inner_wall(paper, stripe):
    """Interior wall seen from the front: wallpaper, dado rail, wood
    wainscot and a baseboard."""
    s = pygame.Surface((16, 16))
    s.fill(paper)
    for x in range(0, 16, 4):                 # wallpaper stripes
        s.fill(stripe, (x + 1, 0, 1, 8))
    for x in range(16):                       # soft shade under the ceiling
        s.set_at((x, 0), shade(paper, -0.35))
        if dither(x, 1, 0.5):
            s.set_at((x, 1), shade(paper, -0.18))
    s.fill(WOOD["l1"], (0, 8, 16, 1))         # dado rail
    s.fill(WOOD["d1"], (0, 9, 16, 1))
    s.fill(WOOD["m"], (0, 10, 16, 5))         # wainscot panels
    for x in (0, 8):
        s.fill(WOOD["d1"], (x, 10, 1, 5))
        s.fill(WOOD["l1"], (x + 1, 11, 6, 1))
    s.fill(WOOD["d2"], (0, 15, 16, 1))        # baseboard
    return s


def _inner_top():
    """Top of an interior wall (seen from above): dark beam."""
    s = pygame.Surface((16, 16))
    s.fill((58, 40, 34))
    s.fill((78, 56, 44), (0, 0, 16, 1))
    for x in range(16):
        if dither(x, 7, 0.25):
            s.set_at((x, 7), (48, 32, 28))
    return s


def world_pieces(T, VAR):
    """Extra context tiles/overlays for world.py."""
    grass, snow = VAR["."][0], VAR["w"][0]
    return {
        "rock_face": [_rock_face(s) for s in (61, 62, 63)],
        "rock_top": [_rock_top(s) for s in (71, 72)],
        "pine": _pine(grass, False),
        "pine_snow": _pine(snow, True),
        "tree_snow": _tree_on(snow),
        "ridge": {"R": _ridge((186, 70, 62)), "r": _ridge((66, 88, 150))},
        "eave": _strip(16, 5, 120),            # under a roof, on the wall
        "cast_top": _strip(16, 5, 90),         # ground below a building
        "cast_left": _strip(4, 16, 70, vertical=True),
        "clouds": _cloud_layer(),
        "tallgrass_snow": [_tallgrass(0, FROST, True),
                           _tallgrass(1, FROST, True)],
        "tallgrass_over": [_tallgrass(0, GRASS, True),
                           _tallgrass(1, GRASS, True)],
        "inner_wall": {"warm": _inner_wall((214, 196, 160), (198, 176, 140)),
                       "sea": _inner_wall((170, 196, 210), (150, 178, 196)),
                       "frost": _inner_wall((196, 206, 228), (176, 188, 214))},
        "inner_top": _inner_top(),
    }


def _tree_on(ground):
    t = _tree(ground)
    return t


# ---------------------------------------------------------------------------
# Props: chests, save crystals, barrel
# ---------------------------------------------------------------------------
GOLD = ((120, 80, 20), (200, 150, 50), (250, 214, 110), (255, 246, 200))


def _chest(open_):
    s = pygame.Surface((14, 12), pygame.SRCALPHA)
    ol = (26, 18, 26)
    if not open_:
        pygame.draw.rect(s, ol, (0, 0, 14, 12), border_radius=3)
        pygame.draw.rect(s, WOOD["m"], (1, 1, 12, 10), border_radius=2)
        s.fill(WOOD["l1"], (1, 1, 12, 3))          # lid, lit
        s.fill(WOOD["l2"], (2, 1, 10, 1))
        s.fill(WOOD["d1"], (1, 4, 12, 1))          # lid seam
        s.fill(WOOD["d1"], (1, 10, 12, 1))
        for x in (3, 10):                          # iron bands
            s.fill((70, 70, 90), (x, 1, 1, 10))
        s.fill(GOLD[1], (6, 3, 2, 4))              # lock
        s.set_at((6, 3), GOLD[3])
        s.set_at((7, 6), GOLD[0])
    else:
        pygame.draw.rect(s, ol, (0, 3, 14, 9), border_radius=2)
        pygame.draw.rect(s, WOOD["m"], (1, 4, 12, 7), border_radius=1)
        s.fill((40, 24, 20), (2, 4, 10, 3))        # dark inside
        s.fill(WOOD["d1"], (1, 7, 12, 1))
        for x in (3, 10):
            s.fill((70, 70, 90), (x, 7, 1, 4))
        pygame.draw.rect(s, ol, (0, 0, 14, 4), border_radius=2)  # lid up
        s.fill(WOOD["l1"], (1, 1, 12, 2))
    return s


def _crystal(frame):
    s = pygame.Surface((14, 18), pygame.SRCALPHA)
    bob = (0, 1, 1, 0)[frame % 4]
    # pedestal
    s.fill((60, 56, 80), (2, 15, 10, 3))
    s.fill((110, 106, 134), (3, 15, 8, 1))
    s.fill((36, 32, 52), (2, 17, 10, 1))
    y0 = 1 + bob
    body = [(7, y0), (12, y0 + 6), (7, y0 + 12), (2, y0 + 6)]
    pygame.draw.polygon(s, (20, 40, 70), body)               # outline
    inner = [(7, y0 + 1), (11, y0 + 6), (7, y0 + 11), (3, y0 + 6)]
    pygame.draw.polygon(s, (70, 170, 220), inner)
    pygame.draw.polygon(s, (130, 220, 250), [(7, y0 + 1), (11, y0 + 6),
                                             (7, y0 + 6)])   # lit facet
    pygame.draw.polygon(s, (40, 110, 170), [(3, y0 + 6), (7, y0 + 11),
                                            (7, y0 + 6)])    # shade facet
    gx = (5, 6, 8, 6)[frame % 4]
    s.set_at((gx, y0 + 4), (255, 255, 255))
    s.set_at((gx, y0 + 5), (220, 250, 255))
    return s


def _barrel():
    s = pygame.Surface((11, 13), pygame.SRCALPHA)
    ol = (26, 18, 26)
    pygame.draw.ellipse(s, ol, (0, 0, 11, 13))
    pygame.draw.ellipse(s, WOOD["m"], (1, 1, 9, 11))
    s.fill(WOOD["l1"], (3, 2, 2, 9))
    s.fill(WOOD["d1"], (8, 2, 1, 9))
    for y in (3, 9):
        s.fill((70, 70, 90), (1, y, 9, 1))
    pygame.draw.ellipse(s, WOOD["l2"], (2, 1, 7, 3))
    return s


def upgrade_props(P):
    P["chest_closed"] = _chest(False)
    P["chest_open"] = _chest(True)
    P["crystal"] = [_crystal(f) for f in range(4)]
    P["barrel"] = _barrel()
    return P
