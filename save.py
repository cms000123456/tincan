"""Save/load to a JSON file in the user's home dir."""

import json
import os

import data
from settings import SAVE_PATH


def save_game(game):
    s = {
        "party": [],
        "gold": game.party.gold,
        "inventory": dict(game.party.inventory),
        "flags": dict(game.flags),
        "map": game.world_scene.world.map_id,
        "pos": [game.world_scene.world.walker.gx, game.world_scene.world.walker.gy],
        "face": game.world_scene.world.walker.face,
    }
    for m in game.party.members:
        s["party"].append({
            "id": m.id, "level": m.level, "exp": m.exp,
            "hp": m.hp, "mp": m.mp, "weapon": m.weapon, "charm": m.charm,
        })
    with open(SAVE_PATH, "w") as f:
        json.dump(s, f)


def has_save():
    return os.path.exists(SAVE_PATH)


def load_game():
    if not has_save():
        return None
    try:
        with open(SAVE_PATH) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def apply_save(game, s):
    from party import Character
    for md, raw in zip(game.party.members, s["party"]):
        md.level = raw["level"]
        md.exp = raw["exp"]
        md.weapon = raw["weapon"]
        md.charm = raw["charm"]
        md.update_stats(final=False)
        md.hp = int(raw["hp"])
        md.mp = int(raw["mp"])
    game.party.gold = int(s["gold"])
    game.party.inventory = dict(s["inventory"])
    game.flags = dict(s.get("flags", {}))
    game.flags.setdefault("opened_chests", {})
    game.flags.setdefault("slain", {})
    game.start_world(s["map"], s["pos"][0], s["pos"][1], s["face"])
