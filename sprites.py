"""Sprites built from the hand-made pixel art in input/.

Sources are either a single pose on a light background (input/*.png) or a
rectangle on one of the character sheets in input/new/. We key out the
background (flood-connected from the border), crop to the figure,
downsample to the game's low-res scale, and synthesise walk frames.
Missing files simply return None so callers can fall back to the
procedural sprites in assets.py.
"""
import os

import pygame

INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input")
OUTLINE = (26, 22, 36)

# Sprite height (low-res pixels, before the 1px outline is added).
CHAR_H = 27

# id -> source images per facing. "side" is used for left and mirrored for
# right (the art has no true profile views).
CHAR_ART = {
    "kai":   dict(down="pixelart_char_hero_front.png",
                  up="pixelart_char_hero_back.png",
                  side="pixelart_char_hero.png"),
    "nara":  dict(down="pixelart_char_mage_front.png",
                  up="pixelart_char_mage_back.png",
                  side="pixelart_char_mage.png"),
    "vela":  dict(down="pixelart_char_thief_front.png",
                  up="pixelart_char_thief_back.png",
                  side="pixelart_char_thief_front2.png"),
    # NPCs (keyed by npc id)
    "elder": dict(down="pixelart_char_priest_front.png",
                  up="pixelart_char_priest_back.png",
                  side="pixelart_char_priest_front2.png"),
}

# Chibi NPCs cut from the character sheets in input/new/ (front view only).
# npc id -> (sheet, (x, y, w, h) of the figure on that sheet)
_SHEET = "new/IGSimple_kreamerge-neutrino-v2-base-fp8-svd_s1261744962_" \
    "2026-11-08_03-02-18_{:05d}_.png"
SHEET_A, SHEET_B, SHEET_C, SHEET_D = (_SHEET.format(n) for n in (1, 3, 4, 8))
NPC_H = 23
NPC_ART = {
    "v1": (SHEET_B, (101, 415, 158, 210)),           # farmer
    "v2": (SHEET_D, (715, 463, 107, 169)),           # matron
    "v3": (SHEET_B, (560, 397, 155, 229)),           # kid
    "v4": (SHEET_D, (865, 301, 70, 122)),            # old timer
    "bounty": (SHEET_C, (321, 78, 158, 246)),        # Bram Jr.
    "shopkeep": (SHEET_B, (329, 420, 166, 205)),
    "captain": (SHEET_A, (536, 88, 175, 194)),
    "marla": (SHEET_D, (600, 320, 79, 103)),
    "sailor": (SHEET_D, (730, 317, 77, 106)),
    "portkid": (SHEET_B, (329, 712, 168, 234)),
    "arms_ember": (SHEET_C, (768, 96, 159, 228)),    # smith
    "inn_ember": (SHEET_D, (586, 463, 108, 169)),
    "elder_frost": (SHEET_A, (541, 750, 175, 198)),  # Warden Lumi
    "snowkid": (SHEET_B, (784, 409, 162, 217)),
    "arms_frost": (SHEET_B, (772, 736, 181, 210)),   # trader
    "inn_frost": (SHEET_B, (546, 123, 177, 212)),
}


# spare chibi figures for generated NPCs (picked by a stable hash of id)
NPC_POOL = [
    (SHEET_A, (71, 79, 181, 203)),
    (SHEET_A, (305, 93, 169, 189)),
    (SHEET_A, (779, 429, 161, 232)),
    (SHEET_A, (81, 739, 161, 210)),
    (SHEET_A, (320, 746, 156, 202)),
    (SHEET_A, (779, 751, 157, 197)),
    (SHEET_A, (773, 73, 177, 209)),
    (SHEET_A, (92, 482, 160, 179)),
    (SHEET_A, (328, 482, 147, 179)),
    (SHEET_A, (542, 482, 163, 179)),
    (SHEET_B, (82, 97, 184, 238)),
    (SHEET_B, (334, 91, 163, 244)),
    (SHEET_B, (542, 742, 167, 204)),
    (SHEET_B, (767, 89, 170, 246)),
    (SHEET_B, (87, 713, 172, 233)),
    (SHEET_C, (95, 80, 159, 244)),
    (SHEET_C, (545, 713, 157, 225)),
    (SHEET_C, (768, 710, 159, 228)),
    (SHEET_C, (546, 97, 157, 227)),
    (SHEET_C, (95, 387, 159, 244)),
    (SHEET_C, (314, 386, 165, 245)),
    (SHEET_C, (545, 387, 158, 244)),
    (SHEET_C, (768, 402, 159, 229)),
    (SHEET_C, (95, 695, 159, 243)),
    (SHEET_C, (314, 695, 165, 243)),
    (SHEET_D, (74, 115, 118, 160)),
    (SHEET_D, (209, 113, 98, 161)),
    (SHEET_D, (474, 320, 75, 103)),
    (SHEET_D, (75, 464, 108, 167)),
    (SHEET_D, (210, 460, 97, 171)),
    (SHEET_D, (339, 460, 100, 172)),
    (SHEET_D, (465, 460, 98, 172)),
    (SHEET_D, (338, 113, 96, 161)),
    (SHEET_D, (838, 456, 108, 176)),
    (SHEET_D, (75, 764, 117, 148)),
    (SHEET_D, (211, 752, 109, 160)),
    (SHEET_D, (583, 765, 114, 146)),
    (SHEET_D, (719, 756, 95, 156)),
    (SHEET_D, (845, 752, 114, 163)),
    (SHEET_D, (339, 774, 99, 137)),
    (SHEET_D, (466, 783, 101, 129)),
    (SHEET_D, (465, 114, 97, 161)),
    (SHEET_D, (585, 109, 115, 165)),
    (SHEET_D, (718, 108, 102, 167)),
    (SHEET_D, (845, 99, 100, 176)),
    (SHEET_D, (82, 306, 100, 117)),
    (SHEET_D, (214, 303, 85, 120)),
    (SHEET_D, (346, 325, 75, 98)),
]

# enemy sprite key -> (image, battle height, map height) in low-res px.
# Battle sprites are drawn at 3x (same pixel size as the party); map
# sprites are drawn 1:1 for roaming monsters. Images in input/enemies/
# were generated with the local IGSimple API.
ENEMY_ART = {
    "scrap": ("pixelart_char_robot_front.png", 26, 15),
    "slime": ("enemies/slime.png", 18, 13),
    "bat": ("enemies/bat.png", 22, 14),
    "wolf": ("enemies/wolf.png", 22, 14),
    "ember_slug": ("enemies/ember_slug.png", 18, 13),
    "snapjaw": ("enemies/snapjaw.png", 24, 14),
    "buccaneer": ("enemies/buccaneer.png", 28, 17),
    "hollow": ("enemies/hollow.png", 26, 16),
    "jelly": ("enemies/jelly.png", 20, 14),
    "snow_wolf": ("enemies/snow_wolf.png", 24, 15),
    "frost_ape": ("enemies/frost_ape.png", 32, 18),
    "cog_drone": ("enemies/cog_drone.png", 18, 14),
    "sentry": ("enemies/sentry.png", 22, 15),
    "sky_sentry": ("enemies/sky_sentry.png", 30, 18),
    "boss": ("enemies/boss.png", 58, 28),
    "rusthook": ("enemies/rusthook.png", 52, 26),
    "colossus": ("enemies/colossus.png", 58, 28),
    "archon": ("enemies/archon.png", 56, 28),
    "millwright": ("enemies/millwright.png", 48, 24),
    # Act II
    "dune_scorp": ("enemies/dune_scorp.png", 24, 14),
    "rust_beetle": ("enemies/rust_beetle.png", 20, 13),
    "mirage": ("enemies/mirage.png", 24, 15),
    "bandit": ("enemies/bandit.png", 28, 17),
    "clock_golem": ("enemies/clock_golem.png", 32, 18),
    "sand_wyrm": ("enemies/sand_wyrm.png", 60, 30),
    "thorn_wolf": ("enemies/thorn_wolf.png", 24, 14),
    "mosskin": ("enemies/mosskin.png", 20, 14),
    "vine_snake": ("enemies/vine_snake.png", 22, 14),
    "pixie": ("enemies/pixie.png", 24, 15),
    "root_horror": ("enemies/root_horror.png", 32, 18),
    "brambleheart": ("enemies/brambleheart.png", 62, 30),
    "magma_toad": ("enemies/magma_toad.png", 20, 13),
    "ember_hound": ("enemies/ember_hound.png", 24, 14),
    "ash_wraith": ("enemies/ash_wraith.png", 26, 16),
    "forge_drone": ("enemies/forge_drone.png", 20, 14),
    "slag_golem": ("enemies/slag_golem.png", 34, 19),
    "forge_titan": ("enemies/forge_titan.png", 60, 30),
    "mire_croc": ("enemies/mire_croc.png", 22, 13),
    "glowmoth": ("enemies/glowmoth.png", 24, 15),
    "drowned_knight": ("enemies/drowned_knight.png", 30, 17),
    "marsh_hag": ("enemies/marsh_hag.png", 28, 17),
    "crystal_eye": ("enemies/crystal_eye.png", 26, 16),
    "hydra_engine": ("enemies/hydra_engine.png", 60, 30),
    "clock_guard": ("enemies/clock_guard.png", 30, 18),
    "rogue_auto": ("enemies/rogue_auto.png", 28, 17),
    "steam_spider": ("enemies/steam_spider.png", 22, 14),
    "sewer_ooze": ("enemies/sewer_ooze.png", 20, 13),
    "assassin_doll": ("enemies/assassin_doll.png", 30, 18),
    "general_spindle": ("enemies/general_spindle.png", 56, 28),
    "star_sentinel": ("enemies/star_sentinel.png", 30, 18),
    "void_cog": ("enemies/void_cog.png", 22, 14),
    "astral_wisp": ("enemies/astral_wisp.png", 22, 14),
    "time_eater": ("enemies/time_eater.png", 30, 18),
    "chrono_knight": ("enemies/chrono_knight.png", 32, 19),
    "orrery_guardian": ("enemies/orrery_guardian.png", 62, 30),
    "clockmaker": ("enemies/clockmaker.png", 66, 32),
}
ENEMY_ALIAS = {"turret": "sentry"}

_cut_cache = {}


_img_cache = {}


def _load(fname):
    if fname not in _img_cache:
        path = os.path.join(INPUT_DIR, fname)
        img = None
        if os.path.exists(path):
            img = pygame.image.load(path)
            img = img.convert_alpha() if pygame.display.get_surface() else \
                img.convert(32, pygame.SRCALPHA)
        _img_cache[fname] = img
    return _img_cache[fname]


def _cutout(fname, rect=None, tol=22):
    """Return a tightly-cropped SRCALPHA figure (full res) from fname, or
    from `rect` on it (a sheet). Background colour is sampled from the
    corner; `tol` is how far a pixel may stray from it and still count."""
    key = (fname, rect, tol)
    if key in _cut_cache:
        return _cut_cache[key]
    full = _load(fname)
    if full is None:
        _cut_cache[key] = None
        return None
    if rect:
        # pad so the figure is surrounded by background on every side
        r = pygame.Rect(rect).inflate(8, 8).clip(full.get_rect())
        src = full.subsurface(r)
    else:
        src = full
    w, h = src.get_size()
    bgc = src.get_at((0, 0))
    # background-coloured / near-transparent pixels are candidates
    light = pygame.mask.from_threshold(src, (bgc.r, bgc.g, bgc.b, 255),
                                       (tol, tol, tol, 255))
    clear = pygame.mask.from_surface(src, 128)
    clear.invert()
    light.draw(clear, (0, 0))
    # keep only components touching the border (white robes stay intact)
    bg = pygame.mask.Mask((w, h))
    for comp in light.connected_components():
        r = comp.get_bounding_rects()
        if not r:
            continue
        bb = r[0].unionall(r[1:]) if len(r) > 1 else r[0]
        if bb.left == 0 or bb.top == 0 or bb.right >= w or bb.bottom >= h:
            bg.draw(comp, (0, 0))
    fg = bg.copy()
    fg.invert()
    rects = fg.get_bounding_rects()
    if not rects:
        _cut_cache[key] = None
        return None
    # drop specks: use the largest component's box, grown a little
    big = max(fg.connected_components(minimum=200),
              key=lambda m: m.count(), default=fg)
    box = big.get_bounding_rects()
    box = box[0].unionall(box[1:])
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    out.blit(src, (0, 0))
    out.lock()
    # background pixels -> transparent outline colour, so the downsample
    # darkens edges instead of leaving a white fringe
    for y in range(box.top, box.bottom):
        for x in range(box.left, box.right):
            if not big.get_at((x, y)):
                out.set_at((x, y), (*OUTLINE, 0))
    out.unlock()
    cut = out.subsurface(box).copy()
    _cut_cache[key] = cut
    return cut


def _downsample(cut, height, coverage=0.38):
    """Downsample to `height` px tall picking each block's dominant colour.

    Averaging (smoothscale) muddies pixel art; taking the most common
    colour bucket per block keeps edges and flat shading crisp.
    """
    w0, h0 = cut.get_size()
    width = max(1, round(w0 * height / h0))
    raw = pygame.image.tobytes(cut, "RGBA")
    out = pygame.Surface((width, height), pygame.SRCALPHA)
    for oy in range(height):
        y0, y1 = oy * h0 // height, max(oy * h0 // height + 1,
                                         (oy + 1) * h0 // height)
        for ox in range(width):
            x0, x1 = ox * w0 // width, max(ox * w0 // width + 1,
                                            (ox + 1) * w0 // width)
            buckets = {}
            n = 0
            for y in range(y0, y1):
                row = y * w0 * 4
                for x in range(x0, x1):
                    i = row + x * 4
                    if raw[i + 3] < 128:
                        continue
                    n += 1
                    r, g, b = raw[i], raw[i + 1], raw[i + 2]
                    k = (r >> 5, g >> 5, b >> 5)
                    e = buckets.get(k)
                    if e:
                        e[0] += 1
                        e[1] += r
                        e[2] += g
                        e[3] += b
                    else:
                        buckets[k] = [1, r, g, b]
            if n < coverage * (y1 - y0) * (x1 - x0):
                continue
            # block average, snapped to the nearest well-represented colour:
            # crisp like a mode filter, but faces/details survive
            ar = sum(e[1] for e in buckets.values()) / n
            ag = sum(e[2] for e in buckets.values()) / n
            ab = sum(e[3] for e in buckets.values()) / n
            cands = [e for e in buckets.values() if e[0] >= 0.12 * n] or \
                list(buckets.values())
            c, r, g, b = min(cands, key=lambda e: (e[1] / e[0] - ar) ** 2 +
                             (e[2] / e[0] - ag) ** 2 + (e[3] / e[0] - ab) ** 2)
            out.set_at((ox, oy), (r // c, g // c, b // c, 255))
    return out


def _downsample_smooth(cut, height):
    """Box-filter to `height` px tall, then make alpha binary."""
    w0, h0 = cut.get_size()
    width = max(1, round(w0 * height / h0))
    s = cut
    # halve repeatedly first for a proper box filter, then finish
    while s.get_height() >= height * 2:
        s = pygame.transform.smoothscale(
            s, (max(1, s.get_width() // 2), s.get_height() // 2))
    s = pygame.transform.smoothscale(s, (width, height))
    s.lock()
    for y in range(height):
        for x in range(width):
            r, g, b, a = s.get_at((x, y))
            if a < 110:
                s.set_at((x, y), (0, 0, 0, 0))
            else:
                # un-premultiply the dark fringe a touch and make opaque
                s.set_at((x, y), (r, g, b, 255))
    s.unlock()
    return s


def _outline(src):
    from assets import with_outline
    return with_outline(src, OUTLINE)


def _stride(s, lift_left):
    """Walk frame: raise one half of the bottom ~22% of rows by 1px."""
    w, h = s.get_size()
    out = s.copy()
    top = int(h * 0.78)
    half = w // 2
    x0, x1 = (0, half) if lift_left else (half, w)
    band = s.subsurface(pygame.Rect(x0, top, x1 - x0, h - top)).copy()
    out.fill((0, 0, 0, 0), (x0, top, x1 - x0, h - top))
    out.blit(band, (x0, top - 1))
    return out


def _drop_shadow(cut):
    """Remove the soft grey ellipse painted under the feet on the sheets
    (the game draws its own shadow). Only touches the bottom rows."""
    w, h = cut.get_size()
    out = cut.copy()
    out.lock()
    for y in range(int(h * 0.82), h):
        for x in range(w):
            r, g, b, a = out.get_at((x, y))
            if a and max(r, g, b) > 115 and max(r, g, b) - min(r, g, b) < 40:
                out.set_at((x, y), (*OUTLINE, 0))
    out.unlock()
    # re-crop: the shadow was usually the widest/lowest part
    box = out.get_bounding_rect(min_alpha=1)
    return out.subsurface(box).copy()


def _sheet_from_front(img):
    """NPC sheet from a single front view: same art every facing (mirrored
    for right), so turning to talk still reads."""
    sheet = {}
    frames = {"idle": img, "a": _stride(img, True), "b": _stride(img, False)}
    for f, s in frames.items():
        o = _outline(s)
        sheet[("down", f)] = sheet[("up", f)] = sheet[("left", f)] = o
        sheet[("right", f)] = _outline(pygame.transform.flip(s, True, False))
    return sheet


def build_sheet(char_id, height=CHAR_H):
    """-> {(dir, frame): Surface} like assets.build_char_sheet, or None."""
    if char_id not in NPC_ART and char_id not in CHAR_ART and \
            char_id not in ("kai", "nara", "vela"):
        if char_id in ("core",):
            return None
        h = sum(ord(ch) * (i + 7) for i, ch in enumerate(char_id))
        NPC_ART[char_id] = NPC_POOL[h % len(NPC_POOL)]
    if char_id in NPC_ART:
        fname, rect = NPC_ART[char_id]
        # wider tolerance also drops the soft grey drop-shadow under feet
        cut = _cutout(fname, rect, tol=56)
        if cut is None:
            return None
        return _sheet_from_front(_downsample(_drop_shadow(cut), NPC_H))
    art = CHAR_ART.get(char_id)
    if not art:
        return None
    base = {}
    for facing, fname in art.items():
        cut = _cutout(fname)
        if cut is None:
            return None
        base[facing] = _downsample(cut, height)
    sheet = {}
    for facing, key in (("down", "down"), ("up", "up"), ("left", "side")):
        img = base[key]
        frames = {"idle": img, "a": _stride(img, True),
                  "b": _stride(img, False)}
        for f, s in frames.items():
            sheet[(facing, f)] = _outline(s)
            if facing == "left":
                sheet[("right", f)] = _outline(
                    pygame.transform.flip(s, True, False))
    return sheet


def build_portrait(char_id, scale=3):
    """Head-and-shoulders crop from the front art, chunky-pixel scaled."""
    art = CHAR_ART.get(char_id)
    cut = _cutout(art["down"]) if art else None
    if cut is None:
        return None
    w, h = cut.get_size()
    side = int(h * 0.36)
    # centre on the opaque mass of the top rows (ignores staffs to one side)
    band = pygame.mask.from_surface(cut.subsurface((0, 0, w, side)), 127)
    cx = band.centroid()[0] if band.count() else w // 2
    x = max(0, min(w - side, cx - side // 2))
    head = cut.subsurface(pygame.Rect(x, 0, min(side, w), side)).copy()
    small = _downsample(head, 16)
    small = _outline(small)
    return pygame.transform.scale(
        small, (small.get_width() * scale, small.get_height() * scale))


def build_enemies():
    """-> (map sprites, battle sprites), each {sprite key: Surface}."""
    small, big = {}, {}
    for key, (fname, bh, mh) in ENEMY_ART.items():
        cut = _cutout(fname, tol=30)
        if cut is None:
            continue
        big[key] = _outline(_downsample(cut, bh))
        small[key] = _outline(_downsample(cut, mh))
    for a, b in ENEMY_ALIAS.items():
        if b in big:
            big[a], small[a] = big[b], small[b]
    if "boss" in big:
        # the superboss shares the Gearlord's frame, gilded and bigger
        cut = _cutout(ENEMY_ART["boss"][0], tol=30)
        for d, h in ((big, 64), (small, 30)):
            s = _outline(_downsample(cut, h))
            s.fill((255, 226, 120, 255), None, pygame.BLEND_RGBA_MULT)
            d["omega"] = s
    return small, big


# Title-screen backdrop (one of the floating-island scenes in input/new/).
TITLE_ART = "new/IGSimple_kreamerge-neutrino-v2-base-fp8-svd_s265274400_" \
    "2026-11-08_03-00-14_00001_.png"


def load_backdrop(width, fname=TITLE_ART):
    """Scene art scaled to `width` px wide (aspect kept), or None."""
    img = _load(fname)
    if img is None:
        return None
    h = round(img.get_height() * width / img.get_width())
    return pygame.transform.smoothscale(img, (width, h))


# Battle backdrops (generated scenes in input/battle/), pixelated to the
# game's 320x176 grid and shown at 3x so they match the sprites.
BATTLE_BG = {
    "overworld": "field", "cavern": "cave", "umbra_wreck": "wreck",
    "glacial_vault": "ice", "sky_bastion": "sky", "deep_mill": "mill",
    # east_road picks by encounter region name
    "forestsouth": "forest", "snowfields": "snow", "coast": "coast",
}
_bg_cache = {}


def battle_backdrop(key, size):
    """key: map id or encounter-region name -> Surface of `size`, or None."""
    name = BATTLE_BG.get(key)
    if name is None and key and os.path.exists(
            os.path.join(INPUT_DIR, "battle", f"{key}.png")):
        name = key                      # a backdrop named directly
    if name is None:
        return None
    if name in _bg_cache:
        return _bg_cache[name]
    img = _load(f"battle/{name}.png")
    if img is None:
        _bg_cache[name] = None
        return None
    w, h = size
    lw, lh = w // 3, h // 3
    # crop to the window's aspect, centred
    iw, ih = img.get_size()
    if iw * lh > ih * lw:
        cw = ih * lw // lh
        img = img.subsurface(((iw - cw) // 2, 0, cw, ih))
    else:
        ch = iw * lh // lw
        img = img.subsurface((0, (ih - ch) // 2, iw, ch))
    small = pygame.transform.smoothscale(img, (lw, lh)).convert()
    # dim slightly so the 3x sprites and damage numbers pop
    small.fill((222, 222, 230), None, pygame.BLEND_RGB_MULT)
    out = pygame.transform.scale(small, (lw * 3, lh * 3))
    if out.get_size() != (w, h):
        full = pygame.Surface((w, h))
        full.blit(out, (0, 0))
        out = full
    _bg_cache[name] = out
    return out


# ---------------------------------------------------------------------------
# Main-world art (generated scenes in input/world/)
# ---------------------------------------------------------------------------
# object -> height in low-res px (width follows the art)
WORLD_OBJECTS = {
    "tree_round": 34, "tree_pine": 38, "tree_snow": 36, "tree_palm": 36,
    "tree_dead": 32, "bush": 14, "rock": 16, "rock_snow": 16, "stump": 13,
    "flowers": 9, "crates": 17, "well": 24, "lamp": 26,
}
HOUSES = ("house_red", "house_blue", "house_snow", "house_port", "shop",
          "inn", "elder_house", "house_desert", "house_tree", "house_forge",
          "house_stilt", "house_city", "house_city2")
TEXTURES = ("tex_grass", "tex_dirt", "tex_snow", "tex_sand", "tex_cave",
            "tex_wood", "tex_marsh", "tex_metal", "tex_ash", "tex_lava",
            "tex_crystal")
TEX_SIZE = 64            # low-res px: each texture spans 4x4 tiles


def world_objects():
    out = {}
    for name, h in WORLD_OBJECTS.items():
        cut = _cutout(f"world/{name}.png", tol=26)
        if cut is not None:
            out[name] = _outline(_downsample(cut, h))
    return out


_house_cache = {}


def house(name, width):
    """House art scaled to `width` low-res px (aspect kept), cached."""
    key = (name, width)
    if key not in _house_cache:
        cut = _cutout(f"world/{name}.png", tol=26)
        if cut is None:
            _house_cache[key] = None
        else:
            h = max(8, round(cut.get_height() * width / cut.get_width()))
            img = _downsample(cut, h)
            if img.get_width() != width:
                img = pygame.transform.scale(img, (width, h))
            _house_cache[key] = _outline(img)
    return _house_cache[key]


def _seamless(img):
    """Blend the image with a half-offset copy so it tiles cleanly."""
    w, h = img.get_size()
    rolled = pygame.Surface((w, h))
    rolled.blit(img, (-w // 2, -h // 2))
    rolled.blit(img, (w - w // 2, -h // 2))
    rolled.blit(img, (-w // 2, h - h // 2))
    rolled.blit(img, (w - w // 2, h - h // 2))
    # mask: 1 in the middle of the original, 0 at its edges
    out = img.copy()
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    steps = 24
    for i in range(steps):
        a = int(255 * (1 - i / steps))
        inset_x, inset_y = int(w / 2 * i / steps), int(h / 2 * i / steps)
        mask.fill((255, 255, 255, a), (inset_x, inset_y, w - 2 * inset_x,
                                  h - 2 * inset_y))
    top = rolled.convert_alpha() if pygame.display.get_surface() else \
        rolled.convert(32, pygame.SRCALPHA)
    top.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    out.blit(top, (0, 0))
    return out


def textures():
    out = {}
    for name in TEXTURES:
        img = _load(f"world/{name}.png")
        if img is None:
            continue
        # use the centre crop (edges of generations are often weaker)
        w, h = img.get_size()
        crop = img.subsurface((w // 8, h // 8, w * 3 // 4, h * 3 // 4))
        seam = _seamless(crop.copy())
        small = pygame.transform.smoothscale(seam, (TEX_SIZE, TEX_SIZE))
        out[name[4:]] = small.convert() if pygame.display.get_surface() \
            else small
    return out
