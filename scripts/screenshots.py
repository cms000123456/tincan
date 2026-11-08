"""Capture real gameplay screenshots (title, world, dialog, battle, menu)."""
import os
import sys

sys.path.insert(0, ".")
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame  # noqa: E402

import data  # noqa: E402
import game as game_mod  # noqa: E402
import scripts.autoplay as ap  # noqa: E402

os.makedirs("/tmp/tcc_shots", exist_ok=True)
random = ap.random
random.seed(5)
DT = ap.DT

g = game_mod.Game(headless=True)
dr = ap.Driver(g)

def snap(name):
    pygame.image.save(g.screen, f"/tmp/tcc_shots/{name}.png")
    print("snap:", name)

# --- title
dr.step(40)
snap("01_title")

# --- intro
dr.step(1, {"a"})
dr.step(30)
snap("02_intro")

# --- world: town
for _ in range(len(data.INTRO)):
    dr.tap()
    dr.step(12)
dr.step(40)
snap("03_town")
ws = g.world_scene

# --- dialog: talk to the Matron (10,12)
# find the matron's current wandering tile and stand to her right
matron = [n for n in ws.world.npcs if n.id == "v2"][0]
matron.wander = 0
matron.x, matron.y = matron.home
ap.walk_to(dr, (matron.x + 1, matron.y))
dr.step(10)
ws.world.walker.face = "left"
ws.update(DT, {"a"}, set())
dr.step(2)
print("dialog state:", ws.state)
snap("04_dialog npc")
for _ in range(6):
    if ws.state != "dialog":
        break
    dr.tap()
    dr.step(30)

# --- menu overlay
dr.step(1, {"menu"})
dr.step(8)
snap("05_menu")
dr.step(3)

# close menu with b
ws.update(DT, {"b"}, set())
dr.step(3)
assert ws.state == "play", ws.state

# --- battle screenshot
print("pre-battle state:", ws.state, "scene is ws:", g.scene is ws)
g.start_random_battle(ws, data.ENCOUNTERS["overworld"])
print("post state:", ws.state)
for i in range(120):
    ws.update(DT, set(), set())
    if g.scene is not ws:
        break
print("after loop i:", i, "scene:", g.scene.__class__.__name__, "ws.state:", ws.state)
bs = g.scene
if bs is ws:
    raise SystemExit("battle never started")
for _ in range(60):
    bs.update(DT, set())
bs.draw(g.screen)
snap("06_battle_start")
# let a party member get ready & open command menu
frames = 0
while bs.menu is None and frames < 4000:
    frames += 1
    bs.update(DT, set())
bs.draw(g.screen)
snap("07_battle_menu")
# choose attack + targeting
bs.update(DT, {"a"})
dr2 = 0
while bs.targeting is None and bs.submenu is None and dr2 < 200 and \
        bs.result is None:
    dr2 += 1
    bs.update(DT, set())
bs.draw(g.screen)
snap("08_battle_target")
bs.update(DT, {"a"})
for _ in range(30):
    bs.update(DT, set())
bs.draw(g.screen)
snap("09_battle_action")
frames = 0
while bs.result is None and frames < 60000:
    frames += 1
    pressed = set()
    if bs.phase == "victory":
        pressed = {"a"}
    elif bs.menu is not None:
        pressed = {"a"}
    elif bs.targeting is not None:
        pressed = {"a"}
    elif bs.submenu is not None:
        pressed = {"b"}
    bs.update(DT, pressed)
if bs.phase == "victory":
    bs.update(DT, set())
    bs.draw(g.screen)
    snap("10_victory")
elif bs.phase == "gameover":
    snap("10_gameover")
print("done; battle frames:", frames)
