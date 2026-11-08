"""Render promotional screenshots for the README into docs/.

    python scripts/promo.py

Runs the real game headless, places the party in a series of scenes and
saves screen grabs, then composes a banner and a screenshot collage.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("TINCAN_SAVE", os.path.join(ROOT, "docs", ".promo_save"))

import random  # noqa: E402

import pygame  # noqa: E402

import assets  # noqa: E402
import data  # noqa: E402
import game as game_mod  # noqa: E402
from settings import WINW, WINH  # noqa: E402

OUT = os.path.join(ROOT, "docs")
DT = 1 / 60


def steps(g, n, held=frozenset()):
    for _ in range(n):
        g.step(DT, frozenset(), held)


def level_party(g, lvl):
    for m in g.party.members:
        m.level = max(m.level, lvl)
        m.update_stats(final=False)
        m.hp, m.mp = m.maxhp, m.maxmp


def world_shot(g, name, mid, x, y, face="down", walk=None, frames=40,
               dialog=None):
    g.start_world(mid, x, y, face)
    ws = g.scene
    ws.world.walker.input_locked = False
    steps(g, 30)
    if walk:
        for d, n in walk:
            steps(g, n, frozenset({d}))
    steps(g, frames)
    if dialog:
        ws.show_dialog(dialog)
        steps(g, 160)
    save(g, name)


def battle_shot(g, name, group, boss=False, frames=150, dmg=0.0):
    g.start_battle_scene(group, boss=boss)
    bs = g.scene
    steps(g, frames)
    if dmg:
        for a in bs.actors_p:
            a.ref.hp = max(1, int(a.ref.hp * (1 - dmg)))
    steps(g, 2)
    save(g, name)


def save(g, name):
    path = os.path.join(OUT, f"{name}.png")
    pygame.image.save(g.screen, path)
    print("saved", os.path.relpath(path, ROOT))
    return path


def arrival(mid):
    for om in data.MAPS.values():
        for e in om["exits"]:
            if e["to"] == mid:
                return e["tx"], e["ty"]
    return 5, 5


def banner(g):
    """1280x400 banner: title scene art, logo, tagline and the party."""
    import sprites
    W, H = 1280, 400
    out = pygame.Surface((W, H))
    img = sprites.load_backdrop(W)
    out.blit(img, (0, -int(img.get_height() * 0.30)))
    shade = pygame.Surface((W, H), pygame.SRCALPHA)
    for x in range(W):                       # darker on the logo side
        a = int(215 * max(0.0, 1 - x / (W * 0.6)) ** 1.1)
        pygame.draw.line(shade, (8, 10, 30, a), (x, 0), (x, H))
    out.blit(shade, (0, 0))
    T = game_mod.TitleScene
    T._outlined(out, "TIN CAN", 300, 70, 84, (255, 214, 92), True, 4)
    T._outlined(out, "CHRONICLES", 300, 165, 66, (240, 240, 255), True, 4)
    T._outlined(out, "a 16-bit JRPG of gears and stars", 300, 262, 26,
                (200, 214, 255), False, 3)
    T._outlined(out, "10 chapters  -  6 hours  -  Python + Pygame", 300,
                306, 22, (255, 214, 92), False, 3)
    # the party, chunky 4x pixels, standing bottom-right
    x = W - 330
    for m in g.party.members:
        spr = m.sheet[("down", "idle")]
        big = pygame.transform.scale(spr, (spr.get_width() * 4,
                                           spr.get_height() * 4))
        sh = pygame.Surface((big.get_width(), 22), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 110), sh.get_rect())
        out.blit(sh, (x, H - 40))
        out.blit(big, (x, H - 28 - big.get_height()))
        x += big.get_width() + 18
    return out


def collage(paths, cols=3, w=420, gap=12, bg=(14, 16, 34)):
    imgs = [pygame.image.load(p) for p in paths]
    h = int(w * WINH / WINW)
    rows = (len(imgs) + cols - 1) // cols
    out = pygame.Surface((cols * w + (cols + 1) * gap,
                          rows * h + (rows + 1) * gap))
    out.fill(bg)
    for i, im in enumerate(imgs):
        cx, cy = i % cols, i // cols
        x, y = gap + cx * (w + gap), gap + cy * (h + gap)
        out.blit(pygame.transform.smoothscale(im, (w, h)), (x, y))
        pygame.draw.rect(out, (120, 130, 200), (x - 2, y - 2, w + 4, h + 4),
                         2)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    random.seed(7)
    g = game_mod.Game(headless=True)
    shots = []
    # title
    steps(g, 200)
    shots.append(save(g, "title"))
    # Act I
    world_shot(g, "town", "town", 15, 10, "down", walk=[("down", 12)])
    shots.append(os.path.join(OUT, "town.png"))
    world_shot(g, "dialogue", "town", 15, 10, "down", dialog=[
        "Elder Bram: The mountain has stopped humming. "
        "*Something in the Cavern of Cogs* is awake."])
    world_shot(g, "overworld", "overworld", 24, 9, "up",
               walk=[("up", 18)])
    shots.append(os.path.join(OUT, "overworld.png"))
    level_party(g, 6)
    battle_shot(g, "battle", ["slime", "scrap", "slime"], dmg=0.3)
    shots.append(os.path.join(OUT, "battle.png"))
    x, y = arrival("frostline")
    world_shot(g, "frostline", "frostline", x, y, "up", walk=[("up", 30)])
    shots.append(os.path.join(OUT, "frostline.png"))
    # Act II
    level_party(g, 20)
    for key in ("dunes_field", "thorn_town", "ash_field", "marsh_field",
                "gear_town"):
        x, y = arrival(key)
        world_shot(g, key, key, x, y, "up",
                   walk=[("up", 40), ("right", 30)])
        shots.append(os.path.join(OUT, f"{key}.png"))
    level_party(g, 30)
    battle_shot(g, "boss", ["forge_titan"], boss=True, frames=200, dmg=0.2)
    shots.append(os.path.join(OUT, "boss.png"))
    x, y = arrival("orrery_1")
    world_shot(g, "orrery", "orrery_1", x, y, "up", walk=[("up", 50)])
    shots.append(os.path.join(OUT, "orrery.png"))

    pygame.image.save(banner(g),
                      os.path.join(OUT, "banner.png"))
    pick = ["town", "overworld", "battle", "dunes_field", "thorn_town",
            "boss", "ash_field", "marsh_field", "orrery"]
    pygame.image.save(collage([os.path.join(OUT, p + ".png") for p in pick]),
                      os.path.join(OUT, "collage.png"))
    print("banner + collage done")
    try:
        os.remove(os.environ["TINCAN_SAVE"])
    except OSError:
        pass


if __name__ == "__main__":
    main()
