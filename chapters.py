"""Act II - chapters 5 to 10 of Tin Can Chronicles.

Archon Prime's fall reveals the real hand behind the restless machines:
THE CLOCKMAKER, who is winding the Astral Orrery with five Star Gears hidden
across the southern continent. Each chapter is a region with a town (inn,
shop, crystal, people), an outdoor field, a three-floor dungeon with a boss
and two side quests. Chapter 10 is the five-floor Astral Orrery.

Everything is built at import by install(D) where D is data.py's globals():
maps come from mapgen (deterministic seeds), enemies are statted from the
chapter's target level so the difficulty curve is smooth.
"""
import random

import mapgen

# ---------------------------------------------------------------------------
# Chapter specs
# ---------------------------------------------------------------------------
CH = [
    dict(n=5, key="dunes", region="Rust Dunes", biome="sand", music="desert",
         town="Duneholm", house="house_desert", level=16, floor="sand",
         wall=(214, 168, 112), bg_field="desert", bg_dun="clocktower",
         dungeon="Buried Clocktower", water=0.0,
         enemies=["dune_scorp", "rust_beetle", "mirage", "bandit"],
         dun_enemy="clock_golem", boss="sand_wyrm", gear="gear1",
         leader=("Chief Ysra", "The dunes ate a clock tower whole a month "
                 "ago. Now it ticks under the sand at night."),
         boss_intro=["*The floor of the clock tower heaves upward...*",
                     "SAND WYRM: SKREEEEE-tick. Tick. TICK."]),
    dict(n=6, key="thorn", region="Thornwood", biome="grass", music="forest",
         town="Mossfall", house="house_tree", level=19, floor="cave",
         wall=(110, 150, 96), bg_field="forest", bg_dun="roothollow",
         dungeon="Root Hollow", water=0.18,
         enemies=["thorn_wolf", "mosskin", "vine_snake", "pixie"],
         dun_enemy="root_horror", boss="brambleheart", gear="gear2",
         leader=("Elder Willowmere", "The great tree's roots have turned "
                 "to iron. Something with a heart of gears lives below."),
         boss_intro=["*The roots part around a beating crimson light...*",
                     "BRAMBLEHEART: Grow... wind... GROW... WIND..."]),
    dict(n=7, key="ash", region="Ashen Slopes", biome="ash", music="volcano",
         town="Forgeholm", house="house_forge", level=22, floor="ash",
         wall=(150, 96, 84), bg_field="ashslope", bg_dun="foundry",
         dungeon="Magma Foundry", water=0.0,
         enemies=["magma_toad", "ember_hound", "ash_wraith", "forge_drone"],
         dun_enemy="slag_golem", boss="forge_titan", gear="gear3",
         leader=("Forgemaster Bruna", "The old foundry restarted itself. "
                 "No dwarf alive lit those furnaces."),
         boss_intro=["*Every anvil in the foundry rings at once.*",
                     "FORGE TITAN: COMMISSION RECEIVED. SUBJECTS: SCRAP."]),
    dict(n=8, key="marsh", region="Mirror Marsh", biome="marsh",
         music="marsh", town="Murkwater", house="house_stilt", level=25,
         floor="crystal", wall=(96, 120, 150), bg_field="marsh",
         bg_dun="observatory", dungeon="Drowned Observatory", water=0.3,
         enemies=["mire_croc", "glowmoth", "drowned_knight", "marsh_hag"],
         dun_enemy="crystal_eye", boss="hydra_engine", gear="gear4",
         leader=("Ferrywoman Ilse", "The old observatory sank, but its "
                 "lens still turns. It points straight at the sky-clock."),
         boss_intro=["*Three brass heads rise from the flooded dome...*",
                     "HYDRA ENGINE: HISS. HISS. HISSSS - CALIBRATING."]),
    dict(n=9, key="gear", region="Gearhaven Outskirts", biome="metal",
         music="city", town="Gearhaven", house="house_city", level=28,
         floor="metal", wall=(120, 110, 100), bg_field="outskirts",
         bg_dun="undercity", dungeon="The Undercity", water=0.0, big=True,
         enemies=["clock_guard", "rogue_auto", "steam_spider", "sewer_ooze"],
         dun_enemy="assassin_doll", boss="general_spindle", gear="gear5",
         leader=("Mayor Cogsworth", "The city guard marches without "
                 "orders. Their general vanished into the Undercity."),
         boss_intro=["*Ranks of dead automatons salute as you enter.*",
                     "GENERAL SPINDLE: The Clockmaker's hour is near. "
                     "Kneel, or be wound down."]),
]
FINAL = dict(n=10, key="orrery", region="Astral Orrery", level=32,
             floor="crystal", wall=(110, 96, 160), music="orrery",
             bg="orrery",
             enemies=["star_sentinel", "void_cog", "astral_wisp",
                      "time_eater"], dun_enemy="chrono_knight")

NAMES = {
    "dune_scorp": "Dune Scorpion", "rust_beetle": "Rust Beetle",
    "mirage": "Mirage Wisp", "bandit": "Dune Bandit",
    "clock_golem": "Clock Golem", "sand_wyrm": "SAND WYRM",
    "thorn_wolf": "Thorn Wolf", "mosskin": "Mosskin",
    "vine_snake": "Vine Snake", "pixie": "Wild Pixie",
    "root_horror": "Root Horror", "brambleheart": "BRAMBLEHEART",
    "magma_toad": "Magma Toad", "ember_hound": "Ember Hound",
    "ash_wraith": "Ash Wraith", "forge_drone": "Forge Drone",
    "slag_golem": "Slag Golem", "forge_titan": "FORGE TITAN",
    "mire_croc": "Mire Croc", "glowmoth": "Glowmoth",
    "drowned_knight": "Drowned Knight", "marsh_hag": "Marsh Hag",
    "crystal_eye": "Crystal Eye", "hydra_engine": "HYDRA ENGINE",
    "clock_guard": "Clock Guard", "rogue_auto": "Rogue Automaton",
    "steam_spider": "Steam Spider", "sewer_ooze": "Sewer Ooze",
    "assassin_doll": "Assassin Doll", "general_spindle": "GENERAL SPINDLE",
    "star_sentinel": "Star Sentinel", "void_cog": "Void Cog",
    "astral_wisp": "Astral Wisp", "time_eater": "Time Eater",
    "chrono_knight": "Chrono Knight", "orrery_guardian": "ORRERY GUARDIAN",
    "clockmaker": "THE CLOCKMAKER",
}
# elemental flavour: weakness, resistance, special skill element
ELEM = {
    "dune_scorp": ("ice", "fire", "none"), "rust_beetle": ("bolt", None, "none"),
    "mirage": ("ice", "fire", "fire"), "bandit": (None, None, "none"),
    "clock_golem": ("bolt", None, "none"), "sand_wyrm": ("ice", "fire", "wind"),
    "thorn_wolf": ("fire", None, "none"), "mosskin": ("fire", "water", "wind"),
    "vine_snake": ("fire", None, "none"), "pixie": ("bolt", "wind", "wind"),
    "root_horror": ("fire", "water", "none"),
    "brambleheart": ("fire", "water", "wind"),
    "magma_toad": ("ice", "fire", "fire"), "ember_hound": ("ice", "fire", "fire"),
    "ash_wraith": ("water", "fire", "fire"), "forge_drone": ("bolt", "fire", "fire"),
    "slag_golem": ("ice", "fire", "fire"), "forge_titan": ("ice", "fire", "fire"),
    "mire_croc": ("bolt", "water", "water"), "glowmoth": ("fire", None, "bolt"),
    "drowned_knight": ("bolt", "water", "water"),
    "marsh_hag": ("fire", None, "water"), "crystal_eye": (None, "ice", "ice"),
    "hydra_engine": ("bolt", "water", "water"),
    "clock_guard": ("bolt", None, "none"), "rogue_auto": ("water", None, "bolt"),
    "steam_spider": ("ice", "fire", "fire"), "sewer_ooze": ("fire", "water", "water"),
    "assassin_doll": ("fire", None, "none"),
    "general_spindle": ("bolt", None, "bolt"),
    "star_sentinel": (None, "bolt", "bolt"), "void_cog": ("bolt", None, "none"),
    "astral_wisp": ("fire", "ice", "ice"), "time_eater": (None, None, "none"),
    "chrono_knight": ("bolt", None, "none"),
    "orrery_guardian": (None, "fire", "bolt"), "clockmaker": (None, None, "bolt"),
}

# party tier gear (k = 1..6 -> chapter 5..10)
WEAPON_NAMES = {
    "kai": ["Dune Falchion", "Thornsteel", "Magma Brand", "Tidecutter",
            "Gearbreaker", "Chrono Edge"],
    "nara": ["Sunstone Rod", "Willow Wand", "Ember Sceptre", "Mirror Staff",
             "Brass Orrery", "Starfall Rod"],
    "vela": ["Sandstorm Gun", "Vinecaster", "Slag Cannon", "Bog Blaster",
             "Steam Repeater", "Comet Driver"],
}
CHARMS = [("sun_amulet", "Sun Amulet"), ("bark_charm", "Barkskin Charm"),
          ("ember_ward", "Ember Ward"), ("pearl_charm", "Pearl Charm"),
          ("cog_medal", "Cog Medal"), ("star_locket", "Star Locket")]


EARLY_GEAR = {   # k <= 0: the Act I shop weapons for chapters 1-4
    -3: dict(kai=dict(atk=2), nara=dict(atk=2, mag=2), vela=dict(atk=4)),
    -2: dict(kai=dict(atk=8), nara=dict(atk=3, mag=6),
             vela=dict(atk=6, mag=5)),
    -1: dict(kai=dict(atk=15), nara=dict(atk=5, mag=11),
             vela=dict(atk=13, mag=7)),
    0: dict(kai=dict(atk=23), nara=dict(atk=8, mag=18),
            vela=dict(atk=19, mag=11)),
}


def weapon_stats(cid, k):
    if k <= 0:
        return dict(EARLY_GEAR[max(-3, k)][cid])
    if cid == "kai":
        return dict(atk=23 + 7 * k)
    if cid == "nara":
        return dict(atk=8 + 3 * k, mag=18 + 6 * k)
    return dict(atk=19 + 5 * k, mag=11 + 4 * k)


# ---------------------------------------------------------------------------
# Enemy statting from the target level
# ---------------------------------------------------------------------------
def _cum_exp(L):
    return sum(int(18 * l ** 1.9) for l in range(1, L))


def _party_ref(D, L, k):
    """Average party numbers at level L with tier-k gear."""
    C = D["CHARS"]

    def st(cid, s):
        b, g = C[cid]["base"][s], C[cid]["growth"][s]
        return b + g * (L - 1)
    ws = {c: weapon_stats(c, k) for c in C}
    atk = sum(st(c, "atk") + ws[c].get("atk", 0) for c in C) / 3
    mag = sum(st(c, "mag") + ws[c].get("mag", 0) for c in C) / 3
    charm_def = max(0, 7 + 3 * k)
    dfn = sum(st(c, "dfn") for c in C) / 3 + charm_def
    mdf = sum(st(c, "mdf") for c in C) / 3 + charm_def
    hp = sum(st(c, "hp") for c in C) / 3
    return dict(atk=atk, mag=mag, dfn=dfn, mdf=mdf, hp=hp)


def make_enemy(D, eid, L, k, role="normal", n_battles=110):
    P = _party_ref(D, L, k)
    edfn = P["atk"] * 0.55
    hit = P["atk"] * 2 - edfn * 0.9                 # avg party hit
    hits, dmg_frac, spd_add = {"normal": (3.6, 0.13, 0),
                               "tough": (6.5, 0.16, 1),
                               "boss": (85.0, 0.22, 3),
                               "boss_early": (40.0, 0.17, 2),
                               "boss_mid": (60.0, 0.20, 3),
                               "final": (130.0, 0.24, 4)}[role]
    hp = int(hit * hits)
    atk = int((P["hp"] * dmg_frac + P["dfn"] * 0.9) / 2)
    mag = int((P["hp"] * dmg_frac * 0.9 + P["mdf"] * 0.8) / 2.5)
    per = (_cum_exp(L + 3) - _cum_exp(L)) / (n_battles * 2.3)
    mult = {"normal": 1.0, "tough": 1.8, "boss": 14.0, "boss_early": 14.0,
            "boss_mid": 14.0, "final": 30.0}[role]
    exp = int(per * mult)
    weak, resist, el = ELEM.get(eid, (None, None, "none"))
    sk_name = {"fire": "Flame Breath", "ice": "Frost Bite",
               "bolt": "Arc Lash", "water": "Tidal Spit",
               "wind": "Gale Rush", "none": "Crushing Blow"}[el]
    skills = {sk_name: dict(kind="mag" if el != "none" else "phys",
                            power=1.0, elem=el, target="enemy",
                            weight=0.3)}
    if role in ("boss", "boss_early", "boss_mid", "final", "tough"):
        skills["Rampage" if role == "tough" else "Cataclysm"] = dict(
            kind="mag", power=0.75 if role != "tough" else 0.6,
            elem=el, target="enemies", weight=0.28)
    if role == "final":
        skills["Rewind"] = dict(kind="mag", power=1.35, elem="none",
                                target="enemy", weight=0.2)
    d = dict(name=NAMES.get(eid, eid), hp=hp, atk=atk, dfn=int(edfn),
             mag=mag, mdf=int(P["mag"] * 0.5), spd=int(12 + 0.25 * L +
                                                       spd_add),
             exp=exp, gold=int(exp * (0.7 if role == "normal" else 1.2)),
             sprite=eid, scale=5 if role.startswith("boss") or
             role == "final" else 4,
             skills=skills, drop=("megapotion", 0.06) if role == "normal"
             else None)
    if weak:
        d["weak"] = weak
    if resist:
        d["resist"] = resist
    return d


DW, DH = 46, 34                 # dungeon floor size (tiles)
ARR = (DW // 2, DH - 2)         # where you arrive coming up the stairs
FLOORS = 4                      # floors per regional dungeon
ORRERY_FLOORS = 6

# ---------------------------------------------------------------------------
# Map builders
# ---------------------------------------------------------------------------
def _put(rows, x, y, ch):
    rows[y] = rows[y][:x] + ch + rows[y][x + 1:]


def _rect(rows, x0, y0, x1, y1, ch):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            _put(rows, x, y, ch)


def build_town(c, seed):
    """Town with headroom above every building (art overhangs upward)."""
    rng = random.Random(seed)
    big = c.get("big")
    W, H = (40, 26) if big else (32, 22)
    g = {"sand": "a", "ash": "y", "marsh": "m", "metal": "z"}.get(
        c["biome"], ".")
    rows = [g * W for _ in range(H)]
    _rect(rows, 0, 0, W - 1, 0, "T")
    _rect(rows, 0, H - 1, W - 1, H - 1, "T")
    _rect(rows, 0, 0, 0, H - 1, "T")
    _rect(rows, W - 1, 0, W - 1, H - 1, "T")
    exits, buildings = [], []
    # main street + plaza
    midx = W // 2
    _rect(rows, midx - 1, 6, midx, H - 1, "#")
    _rect(rows, 3, 9, W - 4, 9, "#")
    if big:
        _rect(rows, 3, 18, W - 4, 18, "#")
    # top row of buildings (footprint y=4..5), second row (y=13..14)
    slots = [(3, 4), (11, 4), (W - 17, 4), (W - 9, 4)]
    if big:
        slots += [(3, 13), (11, 13), (W - 17, 13), (W - 9, 13)]
    kinds = ["inn", "shop", "home_a", "home_b"] + (
        ["home_c", "home_d", "home_e", "workshop"] if big else [])
    for (bx, by), kind in zip(slots, kinds):
        bw = 6
        _rect(rows, bx, by, bx + bw - 1, by, "R")
        _rect(rows, bx, by + 1, bx + bw - 1, by + 1, "W")
        dx = bx + bw // 2
        _put(rows, dx, by + 1, "D")
        _rect(rows, dx, by + 2, dx, by + 4 if by == 4 else by + 3, "#")
        # hedge row in the overhang zone above (non-walkable, looks nice)
        for x in range(bx, bx + bw):
            if rows[by - 1][x] == g:
                _put(rows, x, by - 1, "h")
        buildings.append((kind, bx, by, bw, dx))
    for x in range(1, W - 1):                       # path from street up
        pass
    # decoration
    for _ in range(14):
        x, y = rng.randint(2, W - 3), rng.randint(10, H - 3)
        if rows[y][x] == g:
            _put(rows, x, y, rng.choice("fffhVL"))
    _put(rows, midx + 2, 11, "o")                   # well
    crystal = (midx - 3, 11)
    _put(rows, midx - 3, 11, g)
    return rows, buildings, crystal, (midx - 1, H - 1)


def build_field(c, seed, W=46, H=34):
    rng = random.Random(seed)
    biome = c["biome"]
    entries = [(0, H // 2), (W // 2, 0), (W - 1, H // 2)]
    rows = mapgen.field(W, H, seed, biome, entries, water=c.get("water", 0))
    # dungeon mouth: rock outcrop with an O in the south-east
    mx, my = W * 3 // 4, H - 6
    _rect(rows, mx - 3, my - 1, mx + 3, my, "C")
    _put(rows, mx, my, "O")
    _put(rows, mx, my + 1, "#")
    hub = (W // 2, H // 2)
    g = rows[1][1]
    mapgen._carve_path_rows = None
    grid = [list(r) for r in rows]
    mapgen._carve_path(grid, (mx, my + 1), hub, rng)
    rows = ["".join(r) for r in grid]
    # lava pools on the ash field
    if biome == "ash":
        nz = mapgen._noise(W, H, rng, 6)
        for y in range(3, H - 3):
            for x in range(3, W - 3):
                if nz[y][x] < 0.18 and rows[y][x] == "y":
                    _put(rows, x, y, "l")
    # bridges where a path crossed water
    for y in range(H):
        for x in range(W):
            if rows[y][x] == "#":
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H and rows[ny][nx] == "~":
                        pass
    return rows, entries, (mx, my)


def build_dungeon(seed, W=DW, H=DH):
    side = random.Random(seed * 13).choice((5, W - 6))   # far corner
    entry, stair = (W // 2, H - 2), (side, 2)
    rows = mapgen.dungeon(W, H, seed, entry, stair)
    _put(rows, entry[0], H - 1, "O")
    _put(rows, entry[0], entry[1], "_")
    _put(rows, stair[0], 1, "O")
    return rows, (entry[0], H - 1), (stair[0], 1)


def _floor_only(rows, crystals, spots):
    ok = [p for p in crystals if rows[p[1]][p[0]] == "_"]
    if not ok and len(spots) > 5:
        ok = [spots[5]]
    return ok


def rng_off(seed):
    return random.Random(seed * 7).randint(-10, 10)


# ---------------------------------------------------------------------------
# Install everything into data.py's namespace
# ---------------------------------------------------------------------------
# Act I rebalance: (enemy ids, target level, gear tier k, role)
ACT1 = [
    (["slime", "bat"], 2, -3, "normal"), (["wolf", "scrap"], 3, -3, "normal"),
    (["boss"], 5, -3, "boss_early"),
    (["ember_slug", "snapjaw", "buccaneer", "hollow", "gloom_jelly"], 7, -2,
     "normal"), (["rusthook"], 9, -2, "boss_early"),
    (["snow_wolf", "frost_ape"], 11, -1, "normal"), (["colossus"], 13, -1,
                                                    "boss_mid"),
    (["cog_drone", "turret", "sky_sentry"], 14, 0, "normal"),
    (["archon"], 16, 0, "boss_mid"), (["millwright"], 12, -1, "boss_mid"),
]


def rebalance_act1(D):
    """Re-stat the original enemies on the same level curve as Act II,
    keeping their names, sprites, skills and elements."""
    E = D["ENEMIES"]
    for ids, L, k, role in ACT1:
        for eid in ids:
            if eid not in E:
                continue
            new = make_enemy(D, eid, L, k, role, n_battles=22)
            for f in ("hp", "atk", "dfn", "mag", "mdf", "spd", "exp",
                      "gold"):
                E[eid][f] = new[f]
    if "omega" in E:                      # optional superboss stays brutal
        new = make_enemy(D, "omega", 34, 6, "final")
        for f in ("hp", "atk", "dfn", "mag", "mdf", "spd", "exp", "gold"):
            E["omega"][f] = new[f]


def install(D):
    rebalance_act1(D)
    MAPS, ENEMIES, ENTITIES = D["MAPS"], D["ENEMIES"], D["ENTITIES"]
    ITEMS, SHOPS, QUESTS = D["ITEMS"], D["SHOP_STOCKS"], D["QUESTS"]
    INTROS = D["BOSS_INTROS"]
    pal = D["VILLAGER_PAL"]

    # -- consumables used from here on
    ITEMS["megapotion"] = dict(name="Mega Tonic", kind="item", heal=600,
                               price=380, desc="Restores 600 HP.")
    ITEMS["turbo_ether"] = dict(name="Turbo Jar", kind="item", mana=45,
                                price=220, desc="Restores 45 MP.")
    ITEMS["star_bomb"] = dict(name="Star Bomb", kind="item", aoe=420,
                              price=500, desc="420 damage to ALL enemies.")

    # -- higher-level techs
    more = {
        "kai": [(16, "Meteor Edge", 14, "phys", 2.9, "fire", "enemy"),
                (21, "Tempest Arc", 16, "phys", 1.9, "wind", "enemies"),
                (27, "Chrono Slash", 22, "phys", 3.6, "none", "enemy")],
        "nara": [(15, "Glacier Spear", 10, "mag", 2.2, "ice", "enemy"),
                 (20, "Grace", 14, "heal", 120, "none", "allies"),
                 (26, "Absolute Zero", 22, "mag", 1.9, "ice", "enemies")],
        "vela": [(16, "Railstorm", 13, "mag", 1.5, "bolt", "enemies"),
                 (22, "Plasma Lance", 16, "mag", 3.0, "bolt", "enemy"),
                 (28, "Overclock Nova", 26, "mag", 2.3, "fire", "enemies")],
    }
    for cid, lst in more.items():
        for lvl, name, mp, kind, power, elem, tgt in lst:
            D["CHARS"][cid]["techs"].append(
                dict(lvl=lvl, name=name, mp=mp, kind=kind, power=power,
                     elem=elem, target=tgt, desc=f"{name}."))

    prev_exit = None             # where the previous region's east exit is
    main_quests = []
    for c in CH:
        k = c["n"] - 4
        key, L = c["key"], c["level"]
        # ---- gear for this tier
        stock = ["megapotion", "turbo_ether", "hipotion", "star_bomb"
                 if k >= 3 else "cog_bomb", "elixir"]
        for cid in ("kai", "nara", "vela"):
            iid = f"w{k}_{cid}"
            ITEMS[iid] = dict(name=WEAPON_NAMES[cid][k - 1], kind="weapon",
                              for_=cid, price=1600 + 900 * k,
                              desc="Forged in " + c["town"] + ".",
                              **weapon_stats(cid, k))
            stock.append(iid)
        ck, cname = CHARMS[k - 1]
        ITEMS[ck] = dict(name=cname, kind="charm", dfn=7 + 3 * k,
                         mdf=7 + 3 * k, mag=2 + k, price=1200 + 700 * k,
                         desc=f"DEF/MDF +{7 + 3 * k}.")
        stock.append(ck)
        SHOPS[f"{key}_shop"] = stock
        # ---- enemies
        for eid in c["enemies"]:
            ENEMIES[eid] = make_enemy(D, eid, L - 2, k)
        ENEMIES[c["dun_enemy"]] = make_enemy(D, c["dun_enemy"], L - 1, k,
                                             "tough")
        ENEMIES[c["boss"]] = make_enemy(D, c["boss"], L, k, "boss")
        INTROS[c["boss"]] = c["boss_intro"]
        table = [(e, 4) for e in c["enemies"]]
        enc_field = dict(table=table, size=[(1, 3), (2, 4), (3, 3)],
                         rate=0.16, min_steps=3)
        enc_dun = dict(table=table + [(c["dun_enemy"], 2)],
                       size=[(1, 2), (2, 4), (3, 3)], rate=0.11,
                       min_steps=4)
        # ---- maps
        fid, tid, did = f"{key}_field", f"{key}_town", f"{key}_d"
        frows, fent, mouth = build_field(c, 500 + c["n"])
        trows, blds, crystal, tgate = build_town(c, 600 + c["n"])
        W, H = len(frows[0]), len(frows)
        west, north, east = fent
        fexits = [dict(x=north[0], y=north[1], to=tid, tx=tgate[0],
                       ty=tgate[1] - 1, face="up"),
                  dict(x=mouth[0], y=mouth[1], to=did + "1",
                       tx=ARR[0], ty=ARR[1], face="up")]
        if prev_exit is None:
            fexits.append(dict(x=west[0], y=west[1], to="ember_port",
                               tx=16, ty=18, face="up"))
        else:
            pmid, px, py = prev_exit
            fexits.append(dict(x=west[0], y=west[1], to=pmid, tx=px - 1,
                               ty=py, face="left"))
            # previous field's east exit leads here (gated)
            for e in MAPS[pmid]["exits"]:
                if (e["x"], e["y"]) == (px, py):
                    e.update(to=fid, tx=west[0] + 1, ty=west[1])
        nxt = dict(x=east[0], y=east[1], to="none", tx=0, ty=0,
                   face="right", req=c["gear"])
        fexits.append(nxt)
        prev_exit = (fid, east[0], east[1])
        D[fid.upper()] = frows
        MAPS[fid] = dict(name=c["region"], fill="T", music=c["music"],
                         encounters=enc_field, exits=fexits,
                         signs={(mouth[0] + 2, mouth[1] + 1):
                                [f"* {c['dungeon']} *"]},
                         npcs=[], chests=[dict(id=f"{key}_fchest",
                                               x=W // 2 + 4, y=H // 2 + 3,
                                               item="megapotion", qty=2)],
                         crystals=[(west[0] + 3, west[1] - 2)],
                         entities=[], theme=c["biome"],
                         battle_bg=c["bg_field"])
        # town
        Wt, Ht = len(trows[0]), len(trows)
        texits = [dict(x=tgate[0], y=tgate[1], to=fid, tx=north[0],
                       ty=north[1] + 1, face="down"),
                  dict(x=tgate[0] + 1, y=tgate[1], to=fid, tx=north[0],
                       ty=north[1] + 1, face="down")]
        npcs = []
        for kind, bx, by, bw, dx in blds:
            if kind in ("inn", "shop"):
                iid = f"{key}_{kind}"
                texits.append(dict(x=dx, y=by + 1, to=iid, tx=7, ty=7,
                                   face="up"))
                rows = list(D["EMBER_INN" if kind == "inn" else
                              "EMBER_ARMS"])
                D[iid.upper()] = rows
                keeper = dict(id=f"{iid}_k", x=7, y=2, pal=pal, face="down",
                              wander=0)
                if kind == "inn":
                    keeper.update(inn=120 + 40 * k, dialog=[dict(
                        req=None, lines=[f"Innkeep: Welcome to {c['town']}."
                                         f" A bed is {120 + 40 * k} gil."])])
                else:
                    keeper.update(shop=True, stock=SHOPS[f"{key}_shop"],
                                  dialog=[dict(req=None, lines=[
                                      f"Merchant: Finest goods in "
                                      f"{c['region']}. Have a look!"])])
                MAPS[iid] = dict(name=f"{c['town']} {kind.title()}",
                                 fill="W", music=c["music"] + "_town",
                                 encounters=None,
                                 exits=[dict(x=7, y=8, to=tid, tx=dx,
                                             ty=by + 2, face="down")],
                                 signs={}, npcs=[keeper], chests=[],
                                 crystals=[], entities=[])
            else:
                texits.append(dict(x=dx, y=by + 1, to="locked", tx=dx,
                                   ty=by + 1, face="down"))
        # people
        leader_name, leader_line = c["leader"]
        met = f"met_{key}"
        prev_gear = "shard4" if k == 1 else CH[k - 2]["gear"]
        npcs.append(dict(id=f"{key}_leader", x=tgate[0] - 3, y=11, pal=pal,
                         face="down", wander=0, dialog=[
                             dict(req=c["gear"], lines=[
                                 f"{leader_name}: The {c['dungeon']} is "
                                 "silent at last. Thank you, heroes.",
                                 f"{leader_name}: The road beyond "
                                 f"{c['region']} is open to you."]),
                             dict(req=met, lines=[
                                 f"{leader_name}: The {c['dungeon']} lies "
                                 f"south-east, past the {c['region']}.",
                                 f"{leader_name}: Bring back that Star "
                                 "Gear before the Orrery turns again."]),
                             dict(req=None, lines=[
                                 f"{leader_name}: Travellers? In these "
                                 "times? Then listen.",
                                 f"{leader_name}: {leader_line}",
                                 f"{leader_name}: A Star Gear powers it - "
                                 "one of five the Clockmaker needs.",
                                 f"{leader_name}: Stop it, and "
                                 f"{c['town']} owes you everything."],
                                 set=[met], give=dict(gold=400 * k))]))
        # side quest A: bounty
        bounty_e = c["enemies"][0]
        bq = f"q_{key}_bounty"
        npcs.append(dict(id=f"{key}_hunter", x=tgate[0] + 4, y=12, pal=pal,
                         face="down", wander=1, dialog=[
                             dict(req=bq, lines=["Hunter: Paid in full. "
                                                 "The roads are calmer."]),
                             dict(req=f"kills:{bounty_e}:8", lines=[
                                 f"Hunter: Eight {NAMES[bounty_e]}s! "
                                 "Here's your purse.",
                                 f"*You receive {700 * k} gil!*"],
                                 give=dict(gold=700 * k, exp=900 * k),
                                 set=[bq]),
                             dict(req=None, lines=[
                                 f"Hunter: Bounty board says: eight "
                                 f"{NAMES[bounty_e]}s.",
                                 "Hunter: Bring proof - I'll know."])]))
        frags = [f"{key}_frag{i}" for i in (1, 2, 3)]
        for i, fr in enumerate(frags):
            ITEMS[fr] = dict(name=f"Star Fragment ({'ABC'[i]})", kind="key",
                             desc="A sliver of a fallen star. A smith "
                                  "would want this.")
        # side quest B: fetch from dungeon floor 2
        relic = f"{key}_relic"
        ITEMS[relic] = dict(name=f"{c['town']} Heirloom", kind="key",
                            desc="Someone in town is missing this.")
        fq = f"q_{key}_relic"
        npcs.append(dict(id=f"{key}_elder", x=tgate[0] - 7, y=15, pal=pal,
                         face="down", wander=1, dialog=[
                             dict(req=fq, lines=["Old one: You found it. "
                                                 "Wear that charm in "
                                                 "good health."]),
                             dict(req=f"item:{relic}", lines=[
                                 "Old one: My heirloom! From the "
                                 f"{c['dungeon']}!",
                                 f"*You receive the {cname}!*"],
                                 give=dict(take=relic, item=ck,
                                           exp=600 * k), set=[fq]),
                             dict(req=None, lines=[
                                 "Old one: I dropped my family heirloom "
                                 f"near the {c['dungeon']} before it "
                                 "sank.",
                                 "Old one: The second floor, I'd wager. "
                                 "Bring it home?"])]))
        sq = f"q_{key}_smith"
        npcs.append(dict(id=f"{key}_smith", x=tgate[0] + 7, y=15, pal=pal,
                         face="down", wander=0, dialog=[
                             dict(req=sq, lines=["Smith: That weapon will "
                                                 "outlast us both."]),
                             dict(req=[f"item:{fr}" for fr in frags], lines=[
                                 "Smith: All three Star Fragments! Give me "
                                 "a moment at the anvil...",
                                 "*CLANG. CLANG. CLANG.*",
                                 "Smith: There. Star-tempered. You'll feel "
                                 "the difference.",
                                 "*Everyone's weapon is star-tempered! "
                                 "(+EXP, +gil)*"],
                                 give=dict(take=frags, gold=900 * k,
                                           exp=1500 * k, item="elixir"),
                                 set=[sq]),
                             dict(req=None, lines=[
                                 "Smith: Star Fragments fell into the "
                                 f"{c['dungeon']} - three of them.",
                                 "Smith: Bring me all three and I'll make "
                                 "it worth the trip."])]))
        eq = f"q_{key}_elite"
        npcs.append(dict(id=f"{key}_scout", x=tgate[0] - 5, y=17, pal=pal,
                         face="down", wander=1, dialog=[
                             dict(req=eq, lines=["Scout: Paid and grateful. "
                                                 "Sleep well tonight."]),
                             dict(req=f"elite_{key}", lines=[
                                 f"Scout: You brought down the "
                                 f"{NAMES[c['dun_enemy']]} pack? "
                                 "Incredible!",
                                 f"*You receive {1100 * k} gil!*"],
                                 give=dict(gold=1100 * k, exp=1200 * k),
                                 set=[eq]),
                             dict(req=None, lines=[
                                 f"Scout: A pack led by a "
                                 f"{NAMES[c['dun_enemy']]} roams the "
                                 f"{c['region']}.",
                                 "Scout: Too strong for us. A reward "
                                 "waits for whoever stops it."])]))
        QUESTS.append(dict(id=sq, title=f"{c['town']} Star Fragments",
                           flag=sq, active="Bring three Star Fragments "
                           f"from the {c['dungeon']} to the smith.",
                           done="The smith tempered your weapons."))
        QUESTS.append(dict(id=eq, title=f"Hunt: {NAMES[c['dun_enemy']]} "
                           "pack", flag=eq, active="Defeat the elite pack "
                           f"roaming the {c['region']}.",
                           done="The scout paid you."))
        npcs.append(dict(id=f"{key}_kid", x=tgate[0] + 2, y=17, pal=pal,
                         face="down", wander=2, dialog=[dict(req=None, lines=[
                             f"Kid: My dad says the {c['boss'].replace('_', ' ')}"
                             " eats gears for breakfast!",
                             "Kid: ...do YOU eat gears for breakfast?"])]))
        g = trows[2][2]                         # plain town ground
        for n in npcs:                         # never stand inside decor
            if trows[n["y"]][n["x"]] not in "#.amzy":
                _put(trows, n["x"], n["y"], g)
        D[tid.upper()] = trows
        MAPS[tid] = dict(name=c["town"], fill="T",
                         music=c["music"] + "_town",
                         house=c["house"],
                         encounters=None, exits=texits,
                         signs={(tgate[0] + 2, tgate[1] - 2):
                                [f"Welcome to {c['town']}!"]},
                         npcs=npcs, chests=[], crystals=[crystal],
                         entities=[])
        # dungeon floors
        for fl in range(1, FLOORS + 1):
            mid = f"{did}{fl}"
            rows, ent, stair = build_dungeon(700 + 10 * c["n"] + fl)
            D[mid.upper()] = rows
            rng = random.Random(800 + 10 * c["n"] + fl)
            cells = mapgen.floor_cells(rows)
            spots = mapgen.pick_far(rows, (ent[0], ent[1] - 1), cells,
                                    rng, 10)
            exits = []
            back = (fid, mouth[0], mouth[1] + 1) if fl == 1 else \
                (f"{did}{fl - 1}", None, None)
            if fl == 1:
                exits.append(dict(x=ent[0], y=ent[1], to=fid, tx=mouth[0],
                                  ty=mouth[1] + 1, face="down"))
            else:
                pst = MAPS[f"{did}{fl - 1}"]["_stair"]
                exits.append(dict(x=ent[0], y=ent[1], to=f"{did}{fl - 1}",
                                  tx=pst[0], ty=pst[1] + 1, face="down"))
            ents, chests = [], []
            for i, (sx, sy) in enumerate(spots[:3]):
                grp = rng.sample(c["enemies"], 2) + (
                    [c["dun_enemy"]] if fl >= 2 else [])
                ents.append(dict(id=f"{mid}_e{i}", sprite=grp[0],
                                 pos=(sx, sy), wander=2, group=grp))
            loot = ["megapotion", "turbo_ether", "elixir", "star_bomb",
                    "hipotion"]
            frag_floor = {1: frags[0], 3: frags[1], 4: frags[2]}
            for i, (sx, sy) in enumerate(spots[3:8]):
                if fl == 2 and i == 0:
                    item = relic
                elif i == 0 and fl in frag_floor:
                    item = frag_floor[fl]
                else:
                    item = loot[(fl + i) % len(loot)]
                chests.append(dict(id=f"{mid}_c{i}", x=sx, y=sy, item=item,
                                   qty=1))
            crystals = [(ent[0] - 2, ent[1] - 2)]
            if fl < FLOORS:
                exits.append(dict(x=stair[0], y=stair[1],
                                  to=f"{did}{fl + 1}", tx=ARR[0], ty=ARR[1],
                                  face="up"))
            else:
                # boss guards the far stairs, which lead back outside
                ents.append(dict(id=f"{key}_boss", sprite=c["boss"],
                                 pos=(stair[0], stair[1] + 2), wander=0,
                                 boss=True, group=[c["boss"]],
                                 on_defeat=c["gear"]))
                exits.append(dict(x=stair[0], y=stair[1], to=fid,
                                  tx=mouth[0], ty=mouth[1] + 1,
                                  face="down", req=c["gear"]))
                crystals.append((stair[0] - 3, stair[1] + 4))
            crystals = _floor_only(rows, crystals, spots)
            MAPS[mid] = dict(name=f"{c['dungeon']} {fl}F", fill="C",
                             music="ruins" if fl < FLOORS else "lair",
                             encounters=enc_dun, enc_tile="_",
                             exits=exits, signs={}, npcs=[], chests=chests,
                             crystals=crystals, entities=[], floor=c["floor"],
                             wall_tint=c["wall"], _stair=stair,
                             battle_bg=c["bg_dun"])
            ENTITIES[mid] = ents
            MAPS[mid]["entities"] = ents
        # elite monster roaming the field (side quest)
        rng = random.Random(900 + c["n"])
        gch = frows[2][2] if frows[2][2] not in "T#" else "."
        far = mapgen.pick_far(frows, (west[0] + 1, west[1]),
                              mapgen.floor_cells(frows, frows[H // 2 + 4][4])
                              or mapgen.floor_cells(frows, "."), rng, 1,
                              min_d=18)
        if far:
            elite = dict(id=f"{key}_elite", sprite=c["dun_enemy"],
                         pos=far[0], wander=1,
                         group=[c["dun_enemy"], c["dun_enemy"],
                                c["enemies"][1]], on_defeat=f"elite_{key}")
            ENTITIES[fid] = [elite]
            MAPS[fid]["entities"] = [elite]
        main_quests.append(dict(
            id=f"q_main{c['n']}", title=f"The {c['dungeon']}",
            flag=c["gear"],
            active=f"Find the Star Gear in the {c['dungeon']} "
                   f"({c['region']}).",
            done=f"{c['town']} is safe. The road beyond is open."))
        QUESTS.append(dict(id=bq, title=f"Bounty: {NAMES[bounty_e]}s",
                           flag=bq, active=f"Defeat 8 {NAMES[bounty_e]}s "
                           f"for the hunter in {c['town']}.",
                           done="The bounty is paid."))
        QUESTS.append(dict(id=fq, title=f"{c['town']} Heirloom", flag=fq,
                           active=f"Recover a lost heirloom from the "
                           f"{c['dungeon']}, 2F.", done="Returned home."))

    # ---- Chapter 10: the Astral Orrery (five floors)
    f = FINAL
    L, k = f["level"], 6
    for eid in f["enemies"]:
        ENEMIES[eid] = make_enemy(D, eid, L - 2, k)
    ENEMIES[f["dun_enemy"]] = make_enemy(D, f["dun_enemy"], L - 1, k, "tough")
    ENEMIES["orrery_guardian"] = make_enemy(D, "orrery_guardian", L - 1, k,
                                            "boss")
    ENEMIES["clockmaker"] = make_enemy(D, "clockmaker", L + 1, k, "final")
    INTROS["orrery_guardian"] = ["*The great rings of the Orrery lock "
                                 "into place around you.*",
                                 "ORRERY GUARDIAN: ALIGNMENT IN PROGRESS. "
                                 "INTRUDERS WILL BE DE-SYNCHRONISED."]
    INTROS["clockmaker"] = ["THE CLOCKMAKER: Three children and their "
                            "toys. You broke my gears one by one...",
                            "THE CLOCKMAKER: ...and wound my clock for me. "
                            "The hour has come. Let time END!"]
    table = [(e, 4) for e in f["enemies"]] + [(f["dun_enemy"], 2)]
    enc = dict(table=table, size=[(2, 4), (3, 4)], rate=0.08, min_steps=6)
    last_field, gx, gy = prev_exit
    # the last field's east exit becomes the Orrery gate
    for e in MAPS[last_field]["exits"]:
        if (e["x"], e["y"]) == (gx, gy):
            e.update(to="orrery_1", tx=ARR[0], ty=ARR[1], face="up",
                     req="gear5")
    for fl in range(1, ORRERY_FLOORS + 1):
        mid = f"orrery_{fl}"
        rows, ent, stair = build_dungeon(990 + fl)
        D[mid.upper()] = rows
        rng = random.Random(1990 + fl)
        spots = mapgen.pick_far(rows, (ent[0], ent[1] - 1),
                                mapgen.floor_cells(rows), rng, 7)
        exits = [dict(x=ent[0], y=ent[1],
                      to=last_field if fl == 1 else f"orrery_{fl - 1}",
                      tx=(gx - 1) if fl == 1 else
                      MAPS[f"orrery_{fl - 1}"]["_stair"][0],
                      ty=gy if fl == 1 else 2, face="down")]
        ents = []
        for i, (sx, sy) in enumerate(spots[:3]):
            grp = rng.sample(f["enemies"], 2) + [f["dun_enemy"]]
            ents.append(dict(id=f"{mid}_e{i}", sprite=grp[0], pos=(sx, sy),
                             wander=2, group=grp))
        chests = [dict(id=f"{mid}_c{i}", x=sx, y=sy,
                       item=("elixir", "megapotion")[i], qty=2)
                  for i, (sx, sy) in enumerate(spots[3:5])]
        crystals = [(ent[0] - 2, ent[1] - 2)]
        if fl == 3:
            ents.append(dict(id="orrery_guardian", sprite="orrery_guardian",
                             pos=(stair[0], stair[1] + 2), wander=0,
                             boss=True, group=["orrery_guardian"],
                             on_defeat="guardian_slain"))
        if fl == ORRERY_FLOORS:
            ents.append(dict(id="clockmaker", sprite="clockmaker",
                             pos=(stair[0], stair[1] + 2), wander=0,
                             boss=True, group=["clockmaker"],
                             on_defeat="game_clear"))
        else:
            exits.append(dict(x=stair[0], y=stair[1], to=f"orrery_{fl + 1}",
                              tx=ARR[0], ty=ARR[1], face="up",
                              req="guardian_slain" if fl == 3 else None))
        crystals = _floor_only(rows, crystals, spots)
        MAPS[mid] = dict(name=f"Astral Orrery {fl}F", fill="C",
                         music="orrery", encounters=enc, enc_tile="_",
                         exits=exits, signs={}, npcs=[], chests=chests,
                         crystals=crystals, entities=ents, floor=f["floor"],
                         wall_tint=f["wall"], _stair=stair, battle_bg="orrery")
        ENTITIES[mid] = ents
    main_quests.append(dict(id="q_main10", title="The Astral Orrery",
                            flag="game_clear",
                            active="Climb the Astral Orrery and stop the "
                                   "Clockmaker.",
                            done="Time flows on. The world is yours."))
    # main quests go right after the original four, so quest_line finds them
    for i, q in enumerate(main_quests):
        QUESTS.insert(4 + i, q)

    # ---- Act II hook in Emberport: the ship can now sail south
    D["SHIPS2"]["ember_port"]["alts"] = [
        dict(label="North - the Snow Coast", to="east_road", tx=40, ty=5,
             face="down", req="shard2",
             lines=["(The Sea Lantern braves the north wind...)"]),
        dict(label="South - the Rust Coast", to="dunes_field", tx=2,
             ty=17, face="right", req="shard4",
             lines=["Captain Row: Archon's last words still ring in my "
                    "ears - 'the Clockmaker wakes'.",
                    "Captain Row: Five Star Gears down south. Hold on "
                    "to something!",
                    "*The Sea Lantern sails into the rust-red haze...*"])]
    for npc in MAPS["ember_port"]["npcs"]:
        if npc["id"] == "captain":
            npc["dialog"].insert(0, dict(req="shard4", lines=[
                "Captain Row: You beat Archon Prime! But its dying words...",
                "Captain Row: 'THE CLOCKMAKER WAKES. THE ORRERY TURNS.'",
                "Captain Row: Five Star Gears lie on the southern "
                "continent. The Sea Lantern will take you - the pier, "
                "whenever you're ready."]))

    # ---- arrival tiles: make sure every exit target is walkable floor
    for mid, m in MAPS.items():
        rows = D.get(mid.upper())
        if rows is None:
            continue
    for mid, m in list(MAPS.items()):
        for e in m["exits"]:
            tgt = D.get(e["to"].upper()) if e["to"] in MAPS else None
            if tgt is None:
                continue
            tx, ty = e["tx"], e["ty"]
            if 0 <= ty < len(tgt) and 0 <= tx < len(tgt[0]) and \
                    tgt[ty][tx] in "CT":
                _put(tgt, tx, ty, "_" if tgt[ty][tx] == "C" else ".")
