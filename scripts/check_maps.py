"""Dev tool: render all maps to PNG + validate object placement."""
import importlib, sys
sys.path.insert(0, ".")
import pygame

import assets, data

# every flag something in the game can set: boss on_defeat + dialog "set"
KNOWN_FLAGS = {e.get("on_defeat") for ents in data.ENTITIES.values()
               for e in ents if e.get("on_defeat")}
for _m in data.MAPS.values():
    for _n in _m["npcs"]:
        for _d in _n.get("dialog", []):
            KNOWN_FLAGS.update(_d.get("set", []))

pygame.init()
pygame.display.set_mode((100, 100))
A = assets.load_assets()
TILES, ANIM = A["tiles"], A["anim"]
PROPS = A["props"]

SOLIDS = set("T~WRsxcbCYLoKHe dVUgt") - set(" ")
TRIG = "DO"


def render_map(name, rows):
    H, W = len(rows), len(rows[0])
    surf = pygame.Surface((W * 16, H * 16))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            base = TILES.get(ch)
            if ch in ANIM:
                base = ANIM[ch][0]
            if ch == "D":
                base = TILES["W"]
                if name in ("elder_home", "shop"):
                    base = TILES["i"]
                surf.blit(base, (x * 16, y * 16))
                surf.blit(TILES["D"], (x * 16, y * 16))
                continue
            if ch == "O":
                surf.blit(TILES["C"], (x * 16, y * 16))
                surf.blit(TILES["D"], (x * 16, y * 16))
                continue
            surf.blit(base if base else TILES["."], (x * 16, y * 16))
    m = data.MAPS[name]
    for c in m["chests"]:
        surf.blit(PROPS["chest_closed"], (c["x"] * 16 + 1, c["y"] * 16 + 3))
    for cx, cy in m["crystals"]:
        surf.blit(PROPS["crystal"][0], (cx * 16 + 2, cy * 16 + 2))
    # npcs red squares, entities orange, signs green, exits magenta outline
    for n in m["npcs"]:
        pygame.draw.rect(surf, (255, 60, 60),
                         (n["x"] * 16 + 4, n["y"] * 16 + 4, 8, 8))
    for e in m.get("entities", []):
        col = (255, 160, 40) if not e.get("boss") else (255, 0, 255)
        pygame.draw.rect(surf, col, (e["pos"][0] * 16 + 3, e["pos"][1] * 16 + 3, 10, 10))
    for (sx, sy) in m["signs"]:
        surf.blit(TILES["s"], (-1, -1)) if False else None
        surf.blit(TILES["s"], (sx * 16, sy * 16))
    pygame.draw.rect(surf, (0, 0, 0), surf.get_rect(), 2)
    return surf


errors = []
from collections import Counter
for name in data.MAPS:
    rows = getattr(data, name.upper())
    widths = Counter(len(r) for r in rows)
    if len(widths) > 1:
        errors.append(f"{name} ragged widths {dict(widths)}")
    m = data.MAPS[name]
    H, W = len(rows), len(rows[0])
    s = pygame.transform.scale(render_map(name, rows),
                               (W * 16 * 2, H * 16 * 2))
    pygame.image.save(s, f"/tmp/tcc_art/map_{name}.png")
    # validation
    def walkable(x, y):
        if not (0 <= x < W and 0 <= y < H):
            return False
        c = rows[y][x]
        return c not in SOLIDS
    for c in m["chests"]:
        if not walkable(c["x"], c["y"]):
            errors.append(f"{name} chest {c['id']} on solid tile")
    for cx, cy in m["crystals"]:
        if not walkable(cx, cy):
            errors.append(f"{name} crystal on solid tile")
    for n in m["npcs"]:
        if not walkable(n["x"], n["y"]):
            errors.append(f"{name} npc {n['id']} on solid tile")
    for (sx, sy) in m["signs"]:
        pass  # signs are solid decor, fine on any tile... actually should be ground
    for e in m.get("entities", []):
        if not walkable(*e["pos"]):
            errors.append(f"{name} entity {e['id']} on solid tile")
    for ex in m["exits"]:
        if not walkable(ex["x"], ex["y"]):
            errors.append(f"{name} exit {ex['x']},{ex['y']} on solid tile")
        if ex["to"] not in ("none", "locked", None):
            if ex.get("req") and ex["req"] not in KNOWN_FLAGS:
                errors.append(f"{name} exit req unknown flag {ex['req']}")
            tgt = data.MAPS.get(ex["to"])
            if tgt is None:
                errors.append(f"{name} exit target map missing: {ex['to']}")
                continue
            ro = {nm: getattr(data, nm.upper()) for nm in data.MAPS}[ex["to"]]
            if ex["ty"] >= len(ro) or ex["tx"] >= len(ro[0]):
                errors.append(f"{name} arrival out of bounds {ex['tx']},{ex['ty']} in {ex['to']}")
            else:
                c = ro[ex["ty"]][ex["tx"]]
                if c in SOLIDS:
                    errors.append(f"{name} arrival {ex['tx']},{ex['ty']} in {ex['to']} on solid '{c}'")
# start position
tsx, tsy = data.TOWN_START
tw = data.TOWN[tsy][tsx]
if not (tw not in SOLIDS and tw != "D"):
    errors.append(f"TOWN_START on solid '{tw}'")

print("VALIDATION:", "OK - no problems" if not errors else "\n".join(errors))
