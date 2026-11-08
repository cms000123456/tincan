"""Boss battle + save/load test + screenshot capture of real gameplay."""
import os
import random
import sys

sys.path.insert(0, ".")
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame  # noqa: E402

import data  # noqa: E402
import game as game_mod  # noqa: E402
import scripts.autoplay as ap  # noqa: E402

random.seed(11)
DT = ap.DT


def run():
    g = game_mod.Game(headless=True)
    # story scenes/cards would hold the world in "card"/"dialog" state
    g.flags.update({sc["id"]: True for scs in data.SCENES.values()
                    for sc in scs})
    dr = ap.Driver(g)
    dr.step(5)
    dr.step(1, {"a"})
    dr.step(30)
    for _ in range(len(data.INTRO)):
        dr.tap()
        dr.step(10)
    dr.step(30)
    ws = g.world_scene
    print("world ok:", ws.world.map_id)

    # cheat: level up the party so the boss is beatable by attack-mashing
    # (Gearlord VX is tuned for a level-5 party with shop gear)
    for m in g.party.members:
        while m.level < 6:
            m.gain_exp(m.exp_needed() - m.exp)
        # the Rusty Nail's weapons, as a player would buy before the boss
        m.weapon = {"kai": "iron_blade", "nara": "moon_rod",
                    "vela": "railthrower"}[m.id]
        m.update_stats(final=False)
        m.hp, m.mp = m.maxhp, m.maxmp
    print("party levels:", [m.level for m in g.party.members])

    # cheat to cavern for boss
    ws.world.load_map("cavern", 14, 22, "up")
    for _ in range(40):
        ws.update(DT, set(), set())
    print("map:", ws.world.map_id)

    # bump the boss entity
    boss = [m for m in ws.world.monsters if m.boss][0]
    print("boss present:", boss.id, boss.group)
    g.start_entity_battle(ws, boss)
    for _ in range(60):
        ws.update(DT, set(), set())
        if g.scene is not ws:
            break
    bs = g.scene
    print("battle:", bs.__class__.__name__, "boss:", bs.is_boss)
    frames = 0
    while bs.result is None and frames < 80000:
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
        if bs.phase == "gameover":
            print("BOSS DEFEAT - balance issue: party died at high level")
            bs.result = "gameover"
            g.end_battle(bs)
            break
    print("boss battle result:", bs.result, "in", frames, "frames")
    if bs.result == "won":
        g.end_battle(bs)
    print("boss_slain flag:", g.flags.get("boss_slain"))
    print("slain flags:", list(g.flags.get("slain", {}).keys()))
    print("monsters left in cavern:",
          len([m for m in ws.world.monsters if m.boss is False]))
    ok = (g.flags.get("boss_slain") is True and
          g.scene is g.world_scene)
    print("BOSS TEST:", "PASS" if ok else "FAIL")

    # save & load roundtrip
    import save
    save.save_game(g)
    sdat = save.load_game()
    print("save/load:", "PASS" if sdat and sdat["map"] == "cavern" else "FAIL")


if __name__ == "__main__":
    run()
