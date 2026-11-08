"""World model + scene: tile movement, party followers, NPCs, encounters."""

import math
import random
from collections import deque

import pygame

import data
from settings import (TILE, STEP_SECONDS, FOLLOWER_GAP, PAL, SCALE,
                      GAMEW, GAMEH)

SOLIDS = set("T~WRsxcbCYLoKHe dVUgtShjl") - set(" ")  # S ship, h bush,
# j stump, l lava
# rug 'n' is walkable decor
SOLIDS.discard("n")


def feet_pos(img, px, py):
    """Blit position for a character sprite standing on the tile at px,py.
    Feet sit 10px into the tile, centred (matches the original 18x22 art)."""
    return px + 8 - img.get_width() // 2, py + 10 - img.get_height()


def tile_at(rows, x, y):
    if 0 <= y < len(rows) and 0 <= x < len(rows[0]):
        return rows[y][x]
    return "T"


def is_solid(rows, x, y):
    return tile_at(rows, x, y) in SOLIDS


class NPC:
    def __init__(self, d):
        self.id = d["id"]
        self.data = d
        self.x, self.y = d["x"], d["y"]
        self.px, self.py = self.x * TILE, self.y * TILE
        self.face = d.get("face", "down")
        self.home = (self.x, self.y)
        self.wander = d.get("wander", 0)
        self.shop = d.get("shop", False)
        self.inn = int(d.get("inn", 0))
        self.timer = random.random() * 2.0
        self.walk_t = 0.0

    def glide(self, dt):
        """Slide the drawn position toward the logical tile."""
        tx, ty = self.x * TILE, self.y * TILE
        sp = TILE / 0.28 * dt
        moving = (self.px, self.py) != (tx, ty)
        self.px += max(-sp, min(sp, tx - self.px))
        self.py += max(-sp, min(sp, ty - self.py))
        self.walk_t = self.walk_t + dt if moving else 0.0
        return moving

    def frame(self):
        if self.walk_t <= 0:
            return "idle"
        return ("a", "idle", "b", "idle")[int(self.walk_t / 0.07) % 4]

    def update(self, dt, world):
        self.glide(dt)
        if self.wander <= 0:
            return
        self.timer -= dt
        if self.timer <= 0:
            self.timer = random.uniform(2.0, 4.5)
            dx, dy = random.choice(
                [(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0), (0, 0)])
            if (dx, dy) == (0, 0):
                return
            nx, ny = self.x + dx, self.y + dy
            if abs(nx - self.home[0]) <= self.wander \
                    and abs(ny - self.home[1]) <= self.wander:
                self.face = "right" if dx > 0 else "left" if dx < 0 else \
                    "down" if dy > 0 else "up"
                if world.npc_free(nx, ny, self.id):
                    self.x, self.y = nx, ny


class Monster:
    def __init__(self, world, d):
        self.world = world
        self.id = d["id"]
        self.sprite = d["sprite"]
        self.x, self.y = d["pos"]
        self.home = (self.x, self.y)
        self.wander = d.get("wander", 0)
        self.group = list(d.get("group", ["slime"]))
        self.boss = d.get("boss", False)
        self.on_defeat = d.get("on_defeat")
        self.require = d.get("require")
        self.timer = random.random() * 2.0
        self.bob = random.random() * 6.0
        self.px, self.py = self.x * TILE, self.y * TILE

    def update(self, dt, world):
        tx, ty = self.x * TILE, self.y * TILE
        sp = TILE / 0.3 * dt
        self.px += max(-sp, min(sp, tx - self.px))
        self.py += max(-sp, min(sp, ty - self.py))
        if self.wander <= 0:
            return
        self.timer -= dt
        if self.timer <= 0:
            self.timer = random.uniform(1.2, 2.8)
            dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)])
            if (dx, dy) == (0, 0):
                return
            nx, ny = self.x + dx, self.y + dy
            if abs(nx - self.home[0]) <= self.wander \
                    and abs(ny - self.home[1]) <= self.wander \
                    and world.npc_free(nx, ny, None, monster=self):
                self.x, self.y = nx, ny


class PartyWalker:
    """Leader + follower trail."""

    def __init__(self, party, sheets, x, y, face="down"):
        self.party = party
        self.sheets = party.members[0].sheet   # leader's own sheet
        self.gx, self.gy = x, y
        self.px, self.py = x * TILE, y * TILE
        self.face = face
        self.moving = False
        self.tx, self.ty = x, y
        self.progress = 0.0
        self.carry = 0.0                # overshoot carried into next step
        self.duration = STEP_SECONDS
        self.history = deque(maxlen=FOLLOWER_GAP * 5)
        self.step_count = 0
        self.encounter_steps = 0
        self.arrived_here = False  # spawn on trigger tile guard
        self.input_locked = False
        # seed the trail so the party starts in a line behind the leader
        dx, dy = {"down": (0, -1), "up": (0, 1), "left": (1, 0),
                  "right": (-1, 0)}[face]
        for j in range(FOLLOWER_GAP * 5):
            self.history.append((self.px + dx * j, self.py + dy * j, face))

    def begin_step(self, dx, dy):
        self.tx, self.ty = self.gx + dx, self.gy + dy
        self.moving = True
        self.progress, self.carry = self.carry, 0.0
        self.step_count += 1
        self.face = "right" if dx > 0 else "left" if dx < 0 else \
            "down" if dy > 0 else "up"

    def update(self, dt, world):
        # only record the trail when it changes (keeps the line while standing)
        if not self.history or (self.px, self.py) != self.history[0][:2]:
            self.history.appendleft((self.px, self.py, self.face))
        if self.moving:
            self.progress += dt / self.duration
            if self.progress >= 1.0:
                self.carry = min(0.9, self.progress - 1.0)
                self.gx, self.gy = self.tx, self.ty
                self.px, self.py = self.gx * TILE, self.gy * TILE
                self.moving = False
                self.progress = 0.0
                world.on_arrive(self.gx, self.gy)
            else:
                self.px = int(self.gx * TILE + (self.tx - self.gx) * TILE *
                              self.progress)
                self.py = int(self.gy * TILE + (self.ty - self.gy) * TILE *
                              self.progress)

    def anim_frame(self):
        if not self.moving:
            return "idle"
        # SNES-style cycle over two tiles: left foot, stand, right, stand
        return ("a", "idle", "b", "idle")[(self.step_count * 2 +
                                          int(self.progress * 2)) % 4]

    def draw(self, surf, ox, oy, frame):
        img = self.sheets[(self.face, frame)]
        bob = -1 if frame == "a" else 0
        surf.blit(img, feet_pos(img, int(self.px) - ox, int(self.py) - oy + bob))

    def follower_pos(self, idx):
        """Position of follower idx (0-based)."""
        i = FOLLOWER_GAP * (idx + 1)
        if i < len(self.history):
            px, py, face = self.history[i]
        else:
            px, py, face = self.px, self.py, self.face
        return px, py, face


class World:
    """Game world state for one map."""

    def __init__(self, game, party, sheets, map_id, x, y, face="down"):
        self.game = game
        self._smoke_t = game.play_time
        self.party = party
        self.sheets = sheets
        self.assets = game.assets
        self.load_map(map_id, x, y, face, save_ok=False)

    # -- map loading ----------------------------------------------------------
    def load_map(self, map_id, x, y, face="down", save_ok=True):
        self.map_id = map_id
        self.m = data.MAPS[map_id]
        self.rows = getattr(data, map_id.upper())
        self.h = len(self.rows)
        self.w = len(self.rows[0])
        self.exits = {(e["x"], e["y"]): e for e in self.m["exits"]}
        self.npcs = [NPC(d) for d in self.m["npcs"]]
        self.monsters = []
        slain = self.game.flags.get("slain", {})
        for d in self.m.get("entities", []):
            if d["id"] in slain:
                continue  # stays defeated
            if d.get("require") and not self.game.flags.get(d["require"]):
                continue  # hidden until unlocked
            self.monsters.append(Monster(self, d))
        walker = getattr(self, "walker", None)
        if walker is None or not save_ok:
            self.walker = PartyWalker(party=self.party, sheets=self.sheets,
                                      x=x, y=y, face=face)
        else:
            self.walker.gx, self.walker.gy = x, y
            self.walker.px, self.walker.py = x * TILE, y * TILE
            self.walker.tx, self.walker.ty = x, y
            self.walker.face = face
            self.walker.moving = False
            self.walker.history.clear()
        self.walker.arrived_here = (x, y) in self.exits
        self.music = self.m.get("music", "town")
        self._scan_buildings()

    # -- buildings drawn as single pieces of art -----------------------------
    BCHARS = "RrWYD"

    def _scan_buildings(self):
        """Group roof/wall tiles of outdoor maps into buildings."""
        self.buildings, self.bcells = [], set()
        if self.m.get("fill") == "W":
            return                            # interiors keep their tiles
        seen = set()
        exits = {(e["x"], e["y"]): e["to"] for e in self.m["exits"]}
        for y in range(self.h):
            for x in range(self.w):
                if (x, y) in seen or self.rows[y][x] not in self.BCHARS:
                    continue
                comp, stack = [], [(x, y)]
                seen.add((x, y))
                while stack:
                    cx, cy = stack.pop()
                    comp.append((cx, cy))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        n = (cx + dx, cy + dy)
                        if n not in seen and \
                                tile_at(self.rows, *n) in self.BCHARS:
                            seen.add(n)
                            stack.append(n)
                xs = [c[0] for c in comp]
                ys = [c[1] for c in comp]
                dest = next((exits[c] for c in comp if c in exits), "")
                roofs = "".join(self.rows[cy][cx] for cx, cy in comp)
                if "shop" in dest or "arms" in dest:
                    style = "shop"
                elif "inn" in dest:
                    style = "inn"
                elif dest == "elder_home":
                    style = "elder_house"
                elif self.m.get("house"):
                    style = self.m["house"]
                    if style == "house_city" and (min(xs) // 8) % 2:
                        style = "house_city2"     # vary the city skyline
                elif self.map_id == "frostline":
                    style = "house_snow"
                elif self.map_id == "ember_port":
                    style = "house_port"
                else:
                    style = "house_blue" if roofs.count("r") > \
                        roofs.count("R") else "house_red"
                self.buildings.append(dict(x=min(xs), y=min(ys),
                                           w=max(xs) - min(xs) + 1,
                                           h=max(ys) - min(ys) + 1,
                                           style=style))
                self.bcells.update(comp)

    def _ground_char(self, x, y):
        """Ground to show under objects/buildings at a cell."""
        if self.map_id in self.SNOWY:
            return "w"
        return self._ground_mask().get((x, y), ".")

    # -- collision ------------------------------------------------------------
    def npc_free(self, x, y, ignore_npc=None, monster=None):
        for n in self.npcs:
            if n.x == x and n.y == y and n.id != ignore_npc:
                return False
        for m in self.monsters:
            if m is not monster and m.x == x and m.y == y:
                return False
        return self.step_ok(x, y, for_npc=True)

    def step_ok(self, x, y, for_npc=False):
        """True if a step to (x, y) is permitted. Doors D/O are steppable."""
        if not (0 <= x < self.w and 0 <= y < self.h):
            return False
        ch = self.rows[y][x]
        if ch in SOLIDS:
            return False
        for c in self.m["chests"]:
            if c["x"] == x and c["y"] == y:
                return False
        for cx, cy in self.m.get("crystals", []):
            if (cx, cy) == (x, y):
                return False
        for (sx, sy) in self.m["signs"]:
            if (sx, sy) == (x, y):
                return False
        if not for_npc:
            for n in self.npcs:
                if n.x == x and n.y == y:
                    return False
            for mo in self.monsters:
                if mo.x == x and mo.y == y:
                    return False
        return True

    def can_step(self, x, y):
        return self.step_ok(x, y)

    def on_arrive(self, x, y):
        """Tile-step completed."""
        w = self.walker
        if self.walker.arrived_here:
            if (x, y) in self.exits:
                return  # don't re-trigger the arrival exit
            self.walker.arrived_here = False
        ex = self.exits.get((x, y))
        if ex:
            self.game.use_exit(self, ex, x, y)
            return
        # encounter step
        ch = self.rows[y][x]
        encs = self.m.get("encounters")
        if isinstance(encs, list):
            enc = None
            for z in encs:
                x0, y0, x1, y1 = z["rect"]
                if x0 <= x <= x1 and y0 <= y <= y1:
                    enc = z
                    break
        else:
            enc = encs
        if enc and (ch == "," or ch == self.m.get("enc_tile")):
            w.encounter_steps += 1
            if w.encounter_steps >= enc["min_steps"] and \
                    random.random() < enc["rate"]:
                w.encounter_steps = 0
                self.game.start_random_battle(self, enc)
                return
        # monster bump
        for mo in self.monsters:
            if abs(mo.x - x) + abs(mo.y - y) <= 1:
                self.game.start_entity_battle(self, mo)
                return


    def refresh_monsters(self, game):
        slain = game.flags.get("slain", {})
        ents = [d for d in self.m.get("entities", []) if d["id"] not in slain]
        self.monsters = [Monster(self, d) for d in ents]

    def facing_tile(self):
        w = self.walker
        dx, dy = {"down": (0, 1), "up": (0, -1), "left": (-1, 0),
                  "right": (1, 0)}[w.face]
        return w.gx + dx, w.gy + dy

    def interact_target(self):
        """What's in front (incl. across counters)? -> (kind, obj)"""
        fx, fy = self.facing_tile()
        # look-through counters
        if tile_at(self.rows, fx, fy) == "c":
            dx, dy = {"down": (0, 1), "up": (0, -1), "left": (-1, 0),
                      "right": (1, 0)}[self.walker.face]
            fx, fy = fx + dx, fy + dy
        if not (0 <= fx < self.w and 0 <= fy < self.h):
            return None
        for n in self.npcs:
            if (n.x, n.y) == (fx, fy):
                return ("npc", n)
        for mo in self.monsters:
            if (mo.x, mo.y) == (fx, fy):
                return ("monster", mo)
        for c in self.m["chests"]:
            if (c["x"], c["y"]) == (fx, fy):
                return ("chest", c)
        for (sx, sy) in self.m["signs"]:
            if (sx, sy) == (fx, fy):
                return ("sign", self.m["signs"][(sx, sy)])
        for cx, cy in self.m.get("crystals", []):
            if (cx, cy) == (fx, fy):
                return ("crystal", (cx, cy))
        ch = tile_at(self.rows, fx, fy)
        ex = self.exits.get((fx, fy))
        if ex and ex["to"] in ("locked", "none"):
            return ("locked", ex)
        if ch == "D" and not ex:
            return None
        if ch == "b":
            return ("barrel", (fx, fy))
        if ch == "S" and self.map_id in self.game.ships_cfg and \
                (fx, fy) == (self.game.ships_cfg[self.map_id]["x"],
                             self.game.ships_cfg[self.map_id]["y"]):
            return ("ship", self.game.ships_cfg[self.map_id])
        return None

    # -- drawing ---------------------------------------------------------------
    def _variant(self, ch, x, y):
        vs = self.assets.get("var", {}).get(ch)
        if not vs:
            return None
        # cheap stable hash so neighbouring cells rarely repeat
        return vs[((x * 73856093) ^ (y * 19349663)) % len(vs)]

    _FLOORS = "._#iw"

    def _prop_tile(self, ch, x, y):
        """Prop overlay composed onto the (textured) local floor."""
        floor = "."
        for dx, dy in ((0, 1), (-1, 0), (1, 0), (0, -1)):
            c = tile_at(self.rows, x + dx, y + dy)
            if c in self._FLOORS:
                floor = c
                break
        if floor == "." and self._snowy(x, y):
            floor = "w"
        tx = self._textured(floor, x, y)
        key = (ch, floor, (x * 16) % 64, (y * 16) % 64)
        cache = self.assets.setdefault("_propcells", {})
        if key not in cache:
            base = (tx or self.assets["tiles"].get(
                floor, self.assets["tiles"]["."])).copy()
            if ch == "b":
                b = self.assets["props"]["barrel"]
                base.blit(b, ((16 - b.get_width()) // 2, 16 - b.get_height()))
            else:
                base.blit(self.assets["over"]["props"][ch], (0, 0))
            cache[key] = base
        return cache[key]

    def _barrel_tile(self, x, y, ch="b"):
        """Prop (barrel, stalagmite) standing on the surrounding floor."""
        floor = "."
        for dx, dy in ((0, 1), (-1, 0), (1, 0), (0, -1)):
            c = tile_at(self.rows, x + dx, y + dy)
            if c in self._FLOORS:
                floor = c
                break
        cache = self.assets.setdefault("_onfloor", {})
        key = (ch, floor)
        if key not in cache:
            base = self.assets["tiles"].get(floor,
                                            self.assets["tiles"]["."]).copy()
            if ch == "b":
                b = self.assets["props"]["barrel"]
            else:
                b = self.assets["over"]["props"][ch]
            base.blit(b, ((16 - b.get_width()) // 2,
                          16 - b.get_height()))
            cache[key] = base
        return cache[key]

    SNOWY = ("frostline",)
    OUTDOOR = ("town", "overworld", "east_road", "ember_port", "frostline")

    def _ground_mask(self):
        """Per-cell ground type: nearest open ground wins (multi-source
        BFS), so trees deep in a snowy forest are snowy too."""
        gm = getattr(self, "_gmask", None)
        if gm is not None and gm[0] == self.map_id:
            return gm[1]
        import collections
        mask, q = {}, collections.deque()
        for y in range(self.h):
            for x in range(self.w):
                c = self.rows[y][x]
                if c in ".wamzy":
                    mask[(x, y)] = c
                    q.append((x, y))
        while q:
            x, y = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if 0 <= n[0] < self.w and 0 <= n[1] < self.h and \
                        n not in mask:
                    mask[n] = mask[(x, y)]
                    q.append(n)
        self._gmask = (self.map_id, mask)
        return mask

    def _snowy(self, x, y):
        """Snow map, or the nearest open ground here is snow."""
        if self.map_id in self.SNOWY:
            return True
        if self._ground_mask().get((x, y)) == "w":
            return True
        encs = self.m.get("encounters")
        if isinstance(encs, list):
            for z in encs:
                x0, y0, x1, y1 = z["rect"]
                if "snow" in z["name"] and x0 <= x <= x1 and y0 <= y <= y1:
                    return True
        return "w" in [tile_at(self.rows, x + dx, y + dy)
                       for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0))]

    def _context_tile(self, ch, x, y):
        """Neighbour-aware pieces: cliff faces, pines, snowy trees."""
        wp = self.assets.get("over", {}).get("world")
        if not wp:
            return None
        h = (x * 73856093) ^ (y * 19349663)
        if ch == "W" and self.m.get("fill") == "W":
            # interiors: front-facing wall above floor, beam top elsewhere
            below = tile_at(self.rows, x, y + 1)
            if y + 1 < self.h and below not in "WD":
                theme = {"port": "sea", "snow": "frost"}.get(
                    self.m.get("music"), "warm")
                return wp["inner_wall"][theme]
            return wp["inner_top"]
        if ch == "C":
            below = tile_at(self.rows, x, y + 1)
            if y + 1 < self.h and below != "C":
                img = wp["rock_face"][h % len(wp["rock_face"])]
            else:
                img = wp["rock_top"][h % len(wp["rock_top"])]
            tint = self.m.get("wall_tint")
            if tint:
                cache = self.assets.setdefault("_tinted", {})
                key = (id(img), tint)
                if key not in cache:
                    t = img.copy()
                    t.fill(tuple(min(255, int(c * 1.6)) for c in tint),
                           None, pygame.BLEND_RGB_MULT)
                    cache[key] = t
                img = cache[key]
            return img
        if ch == "T":
            if self._snowy(x, y):
                return wp["pine_snow"]
            if h % 3 == 0:
                return wp["pine"]
        return None

    OBJ_TILES = {"V": "rock", "o": "well", "L": "lamp", "b": "crates",
                 "h": "bush", "j": "stump"}

    def _object_for(self, ch, x, y):
        """Generated world object standing on this cell, or None."""
        ob = self.assets.get("objects")
        if not ob or self.m.get("fill") == "W" and ch != "b":
            return None
        h = (x * 73856093) ^ (y * 19349663)
        if ch == "T":
            g = self._ground_char(x, y)
            if g == "a":
                return ob.get("tree_palm") if h % 3 else ob.get("tree_dead")
            if g in "y":
                return ob.get("tree_dead")
            if g == "m":
                return ob.get("tree_dead") if h % 2 else ob.get("tree_round")
            if self._snowy(x, y):
                return ob.get("tree_snow")
            if self.map_id in ("ember_port",) or self._near_water(x, y):
                return ob.get("tree_palm") if h % 2 else ob.get("tree_round")
            return ob.get("tree_pine") if h % 3 == 0 else \
                ob.get("tree_round")
        name = self.OBJ_TILES.get(ch)
        if name == "rock" and self._snowy(x, y):
            name = "rock_snow"
        return ob.get(name) if name else None

    def _near_water(self, x, y):
        return any(tile_at(self.rows, x + dx, y + dy) == "~"
                   for dx in (-2, 0, 2) for dy in (-2, 0, 2))

    def _textured(self, ch, x, y):
        tex = self.assets.get("tex", {})
        key = {".": "grass", "w": "snow", "f": "grass", "a": "sand",
               "m": "marsh", "z": "metal", "y": "ash", "l": "lava",
               "_": self.m.get("floor", "cave")}.get(ch)
        t = tex.get(key) if key else None
        if t is None:
            return None
        n = t.get_width()
        return t.subsurface(((x * 16) % n, (y * 16) % n, 16, 16))

    def _base_tile(self, ch, t, x=0, y=0):
        if (x, y) in getattr(self, "bcells", ()) or (
                ch in "ToLVbhj" and self._object_for(ch, x, y) is not None):
            g = self._ground_char(x, y)
            if ch in "Vb" and self.m.get("fill") in ("C", "W"):
                g = "_" if self.m.get("fill") == "C" else "i"
            if ch in "Vb":
                for dx, dy in ((0, 1), (-1, 0), (1, 0), (0, -1)):
                    c = tile_at(self.rows, x + dx, y + dy)
                    if c in "._#iw":
                        g = c
                        break
            tx = self._textured(g, x, y)
            if tx is not None:
                return tx
            return self.assets["tiles"].get(g, self.assets["tiles"]["."])
        if ch == "f":
            tx = self._textured(self._ground_char(x, y), x, y)
            if tx is not None:
                return tx
        if ch in "._wamzyl":
            tx = self._textured(ch, x, y)
            if tx is not None:
                return tx
        if ch == ",":
            wp = self.assets.get("over", {}).get("world")
            if wp and self.assets.get("tex"):
                g = self._ground_char(x, y)
                dry = g in "wayz"            # frosted / sun-dried grass
                frames = wp["tallgrass_snow" if dry else "tallgrass_over"]
                f = int(t * 1.5) % len(frames)
                key = (",", g, f, (x * 16) % 64, (y * 16) % 64)
                cache = self.assets.setdefault("_propcells", {})
                if key not in cache:
                    base = self._textured(g, x, y).copy()
                    base.blit(frames[f], (0, 0))
                    cache[key] = base
                return cache[key]
        if ch in ("~", "L", "t", ","):
            frames = self.assets["anim"][ch]
            rate = 1.5 if ch == "," else 3
            return frames[int(t * rate) % len(frames)]
        if ch == "O":
            return self._variant("_", x, y) or self.assets["tiles"]["_"]
        if ch == "b" or ch in self.assets.get("over", {}).get("props", {}):
            return self._prop_tile(ch, x, y)
        c = self._context_tile(ch, x, y)
        if c is not None:
            return c
        v = self._variant(ch, x, y)
        if v is not None:
            return v
        if ch == "D":
            is_in = self.m.get("fill") == "W"          # any interior
            return self.assets["tiles"]["i"] if is_in else \
                self.assets["tiles"]["W"]
        return self.assets["tiles"].get(ch, self.assets["tiles"]["."])

    BUILDING = "WYD"
    ROOF = "Rr"
    GROUND = ".,#wf_in"

    def _shade_cell(self, surf, wp, ch, x, y, px, py):
        """Roof ridges, eaves and shadows cast by buildings (light from
        the upper left, like most 16-bit RPGs)."""
        up = tile_at(self.rows, x, y - 1)
        left = tile_at(self.rows, x - 1, y)
        if ch in self.ROOF and up not in self.ROOF:
            surf.blit(wp["ridge"][ch], (px, py))
        elif ch in self.BUILDING and up in self.ROOF:
            surf.blit(wp["eave"], (px, py))
        elif ch in self.GROUND:
            if up in self.BUILDING or up in self.ROOF:
                surf.blit(wp["cast_top"], (px, py))
            if left in self.BUILDING or left in self.ROOF:
                surf.blit(wp["cast_left"], (px, py))

    def _clouds(self, surf, t, ox, oy):
        wp = self.assets.get("over", {}).get("world")
        if not wp or self.map_id not in self.OUTDOOR:
            return
        c = wp["clouds"]
        cw, ch = c.get_size()
        sx = int(t * 5 - ox) % cw - cw
        sy = int(t * 2 - oy) % ch - ch
        for yy in range(sy, GAMEH, ch):
            for xx in range(sx, GAMEW, cw):
                surf.blit(c, (xx, yy))

    def draw(self, surf, t, ox=0, oy=0):
        self._smoke_t = t
        # tiles
        over = self.assets.get("over", {})
        road_edges = over.get("road") or {".": {
            "top": self.assets["props"].get("edge_top"),
            "bot": self.assets["props"].get("edge_bottom"),
            "lef": self.assets["props"].get("edge_left"),
            "rig": self.assets["props"].get("edge_right"),
        }}
        bank = over.get("bank")
        shore = over.get("shore")
        wp = over.get("world")
        for y in range(self.h):
            row = self.rows[y]
            for x in range(self.w):
                ch = row[x]
                px, py = x * TILE - ox, y * TILE - oy
                if px < -TILE or py < -TILE or px > GAMEW or \
                        py - 8 > GAMEH:
                    continue
                img = self._base_tile(ch, t, x, y)
                # tall tiles (trees) are bottom-aligned and overhang upward
                surf.blit(img, (px, py + TILE - img.get_height()))
                if wp and (x, y) not in self.bcells:
                    self._shade_cell(surf, wp, ch, x, y, px, py)
                if ch == "f" and self.assets.get("objects"):
                    fl = self.assets["objects"].get("flowers")
                    if fl is not None:
                        surf.blit(fl, (px + 8 - fl.get_width() // 2,
                                       py + 14 - fl.get_height()))
                if ch in "~S" and bank:
                    def wet(x, y):
                        return tile_at(self.rows, x, y) in "~SB"
                    if shore is not None and not wet(x, y - 1):
                        surf.blit(shore, (px, py))
                    if not wet(x, y + 1):
                        surf.blit(bank["bot"],
                                  (px, py + TILE - bank["bot"].get_height()))
                    if not wet(x - 1, y):
                        surf.blit(bank["lef"], (px, py))
                    if not wet(x + 1, y):
                        surf.blit(bank["rig"],
                                  (px + TILE - bank["rig"].get_width(), py))
                if ch in "#B":
                    # fringe of the neighbouring ground (grass / snow)
                    # only where the neighbour is NOT a road
                    for side, dx, dy in (("top", 0, -1), ("bot", 0, 1),
                                         ("lef", -1, 0), ("rig", 1, 0)):
                        nc = tile_at(self.rows, x + dx, y + dy)
                        if nc in "#BDO" or nc in "~S":
                            continue
                        if self._ground_char(x + dx, y + dy) in "amzy":
                            continue            # no grass fringe on sand etc.
                        e = (road_edges.get(nc) or road_edges["."])[side]
                        if e is None:
                            continue
                        ex_ = px + (TILE - e.get_width() if side == "rig"
                                    else 0)
                        ey_ = py + (TILE - e.get_height() if side == "bot"
                                    else 0)
                        surf.blit(e, (ex_, ey_))
                if ch == "D":
                    surf.blit(self.assets["tiles"]["D"], (px, py))
                elif ch == "O":
                    # dark cave mouth
                    pygame.draw.rect(
                        surf, (12, 10, 18),
                        (px + 2, py + 3, 12, 13), border_radius=2)
                    pygame.draw.rect(
                        surf, (40, 36, 52), (px + 2, py + 3, 12, 4),
                        border_radius=2)
        # warm glows: wall torches + save crystals
        import data as _data
        glow_w = self.assets["props"].get("glow_warm")
        glow_c = self.assets["props"].get("glow_cyan")
        for y in range(self.h):
            for x in range(self.w):
                ch = self.rows[y][x]
                px, py = x * TILE - ox, y * TILE - oy
                if ch == "t" and glow_w is not None:
                    surf.blit(glow_w, (px - 8, py - 8))
                if ch == "O" and glow_w is not None:
                    pass
        for (cx, cy) in self.m.get("crystals", []):
            if glow_c is not None:
                surf.blit(glow_c, (cx * TILE - 10 - ox, cy * TILE - 10 - oy))
        # chimney smoke (town)
        for (sx, sy) in _data.SMOKE.get(self.map_id, []):
            bx, by = sx * TILE - ox + 6, sy * TILE - oy
            if not (-20 < bx < GAMEW + 20):
                continue
            for k in range(3):
                ph = ((self._smoke_t or 0) * 9 + k * 4.3) % 13.0
                r = 1.5 + ph * 0.28
                gy = by - ph
                col = (206 - int(ph * 3), 206 - int(ph * 3),
                       214 - int(ph * 3))
                pygame.draw.circle(surf, col,
                                   (int(bx + 3 * math.sin(ph / 3 + k)), int(gy)),
                                   max(1, int(r)))

        # signs
        for (sx, sy) in self.m["signs"]:
            surf.blit(self.assets["tiles"]["s"],
                      (sx * TILE - ox, sy * TILE - oy))
        # soft shadows under actors
        props = self.assets["props"]
        sh = props["shadow"]
        w = self.walker
        surf.blit(sh, (w.px - ox, w.py + 10 - oy))
        for i in range(1, len(self.party.members)):
            px, py, face = w.follower_pos(i - 1)
            surf.blit(sh, (px - ox, py + 10 - oy))
        for n in self.npcs:
            surf.blit(sh, (int(n.px) - ox, int(n.py) + 10 - oy))
        for mo in self.monsters:
            surf.blit(sh, (int(mo.px) - ox, int(mo.py) + 8 - oy))

        # y-sorted sprites
        drawables = []
        for c in self.m["chests"]:
            opener = self.game.flags.get("opened_chests", {})
            img = props["chest_open" if c["id"] in opener else "chest_closed"]
            drawables.append((c["y"] * TILE + 8,
                              lambda img=img, cx=c["x"], cy=c["y"], ox=ox,
                              oy=oy:
                              surf.blit(img, (cx * TILE - ox,
                                              cy * TILE + 4 - oy))))
        for cx, cy in self.m.get("crystals", []):
            frames = props["crystal"]
            img = frames[int(t * 4) % len(frames)]
            drawables.append((cy * TILE + 8,
                              lambda img=img, cx=cx, cy=cy, ox=ox, oy=oy:
                              surf.blit(img, (cx * TILE + 1 - ox,
                                              cy * TILE + TILE -
                                              img.get_height() + 1 - oy))))
        for n in self.npcs:
            sheet = self.sheets["npc_" + n.id]
            fr = n.frame()
            img = sheet.get((n.face, fr)) or sheet[(n.face, "idle")]
            bob = -1 if fr == "a" else 0
            drawables.append((int(n.py) + 12,
                              lambda img=img, n=n, ox=ox, oy=oy, bob=bob:
                              surf.blit(img, feet_pos(img, int(n.px) - ox,
                                                      int(n.py) + 1 + bob -
                                                      oy))))
        for mo in self.monsters:
            drawables.append((int(mo.py) + 12,
                              lambda mo=mo, ox=ox, oy=oy:
                              self._draw_monster(surf, t, mo, ox, oy)))
        # world objects (trees, rocks...) and buildings, y-sorted with actors
        x0, x1 = max(0, ox // TILE - 2), min(self.w, (ox + GAMEW) // TILE + 3)
        y0, y1 = max(0, oy // TILE - 1), min(self.h, (oy + GAMEH) // TILE + 4)
        for yy in range(y0, y1):
            row = self.rows[yy]
            for xx in range(x0, x1):
                ch = row[xx]
                if ch not in "ToLVbhj" or (xx, yy) in self.bcells:
                    continue
                img = self._object_for(ch, xx, yy)
                if img is None:
                    continue
                bx = xx * TILE + 8 - img.get_width() // 2 - ox
                by = yy * TILE + 15 - img.get_height() - oy
                drawables.append((yy * TILE + 15,
                                  lambda img=img, bx=bx, by=by:
                                  surf.blit(img, (bx, by))))
        import sprites as _sprites
        for b in self.buildings:
            img = _sprites.house(b["style"], b["w"] * TILE)
            if img is None:
                continue
            bx = b["x"] * TILE - ox - 1
            by = (b["y"] + b["h"]) * TILE - img.get_height() + 1 - oy
            if bx > GAMEW or bx + img.get_width() < 0 or by > GAMEH:
                continue
            drawables.append(((b["y"] + b["h"]) * TILE - 1,
                              lambda img=img, bx=bx, by=by:
                              surf.blit(img, (bx, by))))
        ff = w.anim_frame()
        drawables.append((w.py + 14,
                          lambda ff=ff: w.draw(surf, ox, oy, ff)))
        for i in range(1, len(self.party.members)):
            px, py, face = w.follower_pos(i - 1)
            mem = self.party.members[i]
            img = mem.sheet[(face, ff)]
            bob = -1 if ff == "a" else 0
            drawables.append((py + 14,
                              lambda img=img, px=px, py=py, ox=ox, oy=oy,
                              bob=bob:
                              surf.blit(img, feet_pos(img, px - ox,
                                                      py + bob - oy))))
        drawables.sort(key=lambda d: d[0])
        for _, fn in drawables:
            fn()
        self._clouds(surf, t, ox, oy)

    def _draw_monster(self, surf, t, mo, ox, oy):
        aset = self.assets["enemies"]
        spr = aset.get(mo.sprite) or aset["slime"]
        if spr.get_height() < 14:
            img = pygame.transform.scale(spr, (spr.get_width() * 2,
                                               spr.get_height() * 2))
        else:
            img = spr
        mo.bob += 0.05
        off = int(1.5 * (mo.bob % 2))
        surf.blit(img, (int(mo.px) + (TILE - img.get_width()) // 2 - ox,
                        int(mo.py) + 16 - img.get_height() - 4 + off - oy))
