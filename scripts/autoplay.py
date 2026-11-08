"""Autoplay integration test: title -> intro -> town -> elder -> shop ->
overworld -> random battle -> cavern entrance. Headless (SDL dummy)."""
import os
import random
import sys

sys.path.insert(0, ".")
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame  # noqa: E402

import game as game_mod  # noqa: E402
import data  # noqa: E402

random.seed(3)

DT = 1 / 60.0


class Driver:
    def __init__(self, g):
        self.g = g
        self.fails = []
        self.phase = "title_a"

    # helpers ------------------------------------------------------------------
    def step(self, n=1, pressed=frozenset(), held=frozenset()):
        """'pressed' applies to the FIRST frame only; 'held' to all."""
        for i in range(n):
            self.g.step(DT, pressed if i == 0 else frozenset(), held)
            if self.g.scene is None:
                return

    def tap(self):
        self.step(1, {"a"})
        self.step(1)

    def check(self, cond, msg):
        print(("  OK  " if cond else "  FAIL") + " - " + msg)
        if not cond:
            self.fails.append(msg)

    def pos(self):
        w = self.g.world_scene.world.walker
        return w.gx, w.gy


def walk_to(dr, target, max_frames=600):
    """BFS path then walk it leg by leg, robust to NPC wander blocking."""
    g = dr.g
    ws = g.world_scene
    world = ws.world
    for attempt in range(4):
        for _ in range(140):          # let pending transitions/fades finish
            if ws.state == "play":
                break
            ws.update(DT, set(), set())
        from collections import deque
        sx, sy = dr.pos()
        if (sx, sy) == target:
            return True
        Q = deque([((sx, sy), [])])
        seen = {(sx, sy)}
        path = None
        while Q:
            (x, y), p = Q.popleft()
            if (x, y) == target:
                path = p
                break
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                nx, ny = x + dx, y + dy
                if (nx, ny) in seen:
                    continue
                seen.add((nx, ny))
                if world.step_ok(nx, ny):
                    Q.append(((nx, ny), p + [(dx, dy)]))
        if path is None:
            return False
        walker = world.walker
        for dx, dy in path:
            if ws.state != "play":
                return True
            dirname = ("down" if dy > 0 else "up" if dy < 0 else
                       "right" if dx > 0 else "left")
            # kick off one step, then let it finish (held released)
            ws.update(DT, set(), {dirname})
            for _ in range(60):
                ws.update(DT, set(), set())
                if not walker.moving:
                    break
            if (walker.gx, walker.gy) == (sx, sy):
                # step blocked - retry whole path
                break
        if dr.pos() == target:
            return True
    return dr.pos() == target


def main():
    import save
    if os.path.exists(save.SAVE_PATH):
        os.remove(save.SAVE_PATH)
    g = game_mod.Game(headless=True)
    dr = Driver(g)

    print("== title ==")
    dr.step(5)
    dr.step(1, {"a"})          # New Game
    dr.step(30)                # intro
    print("== intro ==")
    for _ in range(len(data.INTRO)):
        dr.tap()
        dr.step(10)
    dr.step(30)
    dr.check(g.scene.__class__.__name__ == "WorldScene", "entered world")
    ws = g.world_scene
    dr.check(ws.world.map_id == "town", "starting map is town")
    dr.check(len(ws.world.party.members) == 3, "party has 3 members")

    print("== walk to elder ==")
    walk_to(dr, (6, 5))
    walk_to(dr, (6, 4))
    dr.step(20)
    dr.check(ws.state == "play", "still playing before door")
    walk_to(dr, (6, 3))        # step onto elder door
    for _ in range(120):
        ws.update(DT, set(), set())
        if ws.state == "play" and ws.world.map_id != "town":
            break
    dr.check(g.world_scene.world.map_id == "elder_home", "entered elder home")

    print("== elder dialog ==")
    walk_to(dr, (7, 4))
    dr.step(20)
    ws.update(DT, {"a"}, set())      # interact elder
    dr.step(5)
    dr.check(ws.state == "dialog", "dialog opened")
    for _ in range(20):
        if ws.state != "dialog":
            break
        dr.tap()
        dr.step(8)
        if dr.g.world_scene.state == "dialog":
            ws.overlay.update(DT, {"a"})
            dr.step(4)
    # finish remaining pages
    for _ in range(30):
        if ws.state != "dialog":
            break
        dr.step(30, {"a"})
        dr.step(4)
    dr.check(g.flags.get("met_elder", False), "met_elder flag set")
    dr.check(g.party.gold >= 150, f"gold granted ({g.party.gold})")

    print("== save at crystal ==")
    walk_to(dr, (10, 2))
    walk_to(dr, (11, 2))
    dr.step(10)
    ws.update(DT, {"a"}, set())
    for _ in range(20):
        if ws.state != "dialog":
            break
        dr.step(30, {"a"})
        dr.step(3)
    dr.check(os.path.exists(save.SAVE_PATH), "save file created")

    # return to door
    walk_to(dr, (7, 6))
    walk_to(dr, (7, 7))
    for _ in range(80):
        ws.update(DT, set(), set())
        if ws.world.map_id == "town":
            break
    dr.check(g.world_scene.world.map_id == "town", "back in town")

    print("== shop ==")
    walk_to(dr, (17, 6))
    walk_to(dr, (17, 5))
    walk_to(dr, (17, 4))
    walk_to(dr, (17, 3))
    for _ in range(140):
        ws.update(DT, set(), set())
        if ws.state == "play" and ws.world.map_id == "shop":
            break
    dr.check(g.world_scene.world.map_id == "shop", "entered shop")

    walk_to(dr, (6, 5))
    walk_to(dr, (6, 4))
    dr.step(10)
    ws.update(DT, {"a"}, set())
    dr.step(10)
    for _ in range(10):
        if ws.state != "dialog":
            break
        print("   dlg:", ws.state, type(ws.overlay).__name__)
        dr.step(30, {"a"})
        dr.step(5)
    dr.check(ws.state == "shop", "shop opened")
    gold_before = g.party.gold
    print("   DBG buy press: state:", ws.state, "overlay:",
          type(ws.overlay).__name__ if ws.overlay else None,
          "idx:", getattr(ws.overlay, "idx", "?"))
    ws.update(DT, {"a"}, set())    # buy potion (idx 0)
    print("   after buy: gold:", g.party.gold, "inv:", dict(g.party.inventory),
          "note:", getattr(ws.overlay, "note", None))
    dr.step(10)
    dr.check(g.party.gold == gold_before - 25,
             f"potion bought for 25 gil (gold {gold_before} -> "
             f"{g.party.gold}, inv={dict(g.party.inventory)})")
    ws.update(DT, {"b"}, set())    # close shop
    dr.step(5)
    dr.check(ws.state == "play", "shop closed")

    print("== leave to overworld ==")
    walk_to(dr, (7, 7))
    walk_to(dr, (7, 8))
    for _ in range(140):
        ws.update(DT, set(), set())
        if ws.state == "play" and ws.world.map_id == "town":
            break
    dr.check(g.world_scene.world.map_id == "town", "left shop")
    walk_to(dr, (12, 5))
    walk_to(dr, (12, 1))
    walk_to(dr, (12, 0))
    for _ in range(140):
        ws.update(DT, set(), set())
        if ws.state == "play" and ws.world.map_id == "overworld":
            break
    dr.check(g.world_scene.world.map_id == "overworld", "entered overworld")

    print("== random battle ==")
    lv_before = tuple(m.level for m in g.world_scene.world.party.members)
    exp_before = sum(m.exp for m in g.party.members)
    g.flags["slain"] = {}
    g.start_random_battle(ws, data.ENCOUNTERS["overworld"])
    for _ in range(60):
        ws.update(DT, set(), set())
        if g.scene is not ws:
            break
    dr.check(g.scene.__class__.__name__ == "BattleScene", "battle started")
    # autoplay battle THROUGH the unified game loop (update + draw, like a
    # real run) so scene interface breakage can never hide from the test
    frames = 0
    while frames < 120000:
        frames += 1
        sc = g.scene
        if sc.__class__.__name__ == "BattleScene":
            pressed = {"a"} if (sc.phase == "victory" or
                                sc.menu is not None or
                                sc.targeting is not None) else \
                       ({"b"} if sc.submenu is not None else set())
            if sc.phase == "gameover":
                pressed = {"a"}
                g.step(DT, pressed, set())
                print("  NOTE: party died - game over path")
                break
            g.step(DT, pressed, set())
        else:
            break
    bs = g.battle_scene if g.battle_scene else None
    dr.check(g.scene is ws or (bs is not None and bs.phase == "gameover"),
             f"battle resolved via unified loop ({frames} frames, "
             f"hp={[m.hp for m in g.party.members]})")
    if g.scene is not ws:
        g.end_battle(g.battle_scene)
    exp_after = sum(m.exp for m in g.party.members)
    dr.check(exp_after > exp_before or tuple(
        m.level for m in g.party.members) != lv_before, "exp gained")
    dr.check(g.scene.__class__.__name__ == "WorldScene", "back to world")

    print("== head to cavern mouth ==")
    walk_to(dr, (14, 12))
    walk_to(dr, (14, 11))
    walk_to(dr, (24, 10))
    walk_to(dr, (24, 6))
    walk_to(dr, (24, 5))
    walk_to(dr, (24, 4))
    for _ in range(140):
        ws.update(DT, set(), set())
        if ws.state == "play" and ws.world.map_id == "cavern":
            break
    dr.check(g.world_scene.world.map_id == "cavern", "entered cavern")

    print("== results ==")
    if dr.fails:
        print("FAILURES:")
        for f in dr.fails:
            print("  -", f)
        sys.exit(1)
    print("AUTOPLAY: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
