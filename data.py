"""Game data: characters, techs, items, enemies, maps, quests, dialogue.

Map legend (16px tiles):
  . grass      , tallgrass   T tree    f flowers   ~ water   # path
  B bridge     W wall        R roof    D door      s prop-sign  x fence
  i wood floor c counter     b barrel  C cave wall  _ cave floor
  O cave opening (walkable trigger)    w snow ground  V rock/stalagmite
  Y window     L lamp        o well    K market stall   H hay
  e bookshelf  d bed         n rug (walkable)  U mushroom g gear heap
  S ship (solid, interactable)         t wall torch (solid, glows)

Solid tiles: T ~ W R s x c b C Y L o K H e d V U g S t
Walkable triggers: D (house door), O (cave mouth), ship (interact)
"""

import random as _random

# ---------------------------------------------------------------------------
# Party characters
# ---------------------------------------------------------------------------
CHARS = {
    "kai": {
        "name": "Kai", "desc": "A hot-blooded youth and a fine swordsman.",
        "accent": "headband",
        "base": {"hp": 92, "mp": 10, "atk": 9, "dfn": 7, "mag": 5, "mdf": 6,
                 "spd": 14},
        "growth": {"hp": 12, "mp": 2, "atk": 2.1, "dfn": 1.6, "mag": 1,
                   "mdf": 1, "spd": 0.8},
        "weapon": "rusted_blade",
        "palette": dict(H=(255, 120, 60), h=(200, 70, 30), S=(250, 210, 170),
                        E=(40, 30, 40), O=(60, 90, 190), o=(40, 62, 140),
                        T=(250, 210, 90), B=(60, 50, 60)),
        "techs": [
            dict(lvl=3, name="Ember Slash", mp=2, kind="phys", power=1.05,
                 elem="fire", target="enemy",
                 desc="A burning blade strike. One enemy."),
            dict(lvl=5, name="Crescent Fang", mp=4, kind="phys", power=1.6,
                 elem="none", target="enemy",
                 desc="A slicing crescent. One enemy."),
            dict(lvl=7, name="Cyclone Sweep", mp=5, kind="phys", power=0.95,
                 elem="wind", target="enemies",
                 desc="A whirlwind of steel. All enemies."),
            dict(lvl=10, name="Solar Cross", mp=9, kind="phys", power=2.4,
                 elem="fire", target="enemy",
                 desc="A pillar of flame. One enemy."),
            dict(lvl=13, name="Sunder", mp=12, kind="phys", power=1.5,
                 elem="none", target="enemies",
                 desc="Cleaves the earth. All enemies."),
        ],
    },
    "nara": {
        "name": "Nara", "desc": "A bright scholar-princess of the shrine.",
        "accent": "blush",
        "base": {"hp": 70, "mp": 22, "atk": 6, "dfn": 6, "mag": 9, "mdf": 8,
                 "spd": 12},
        "growth": {"hp": 9, "mp": 4.5, "atk": 1, "dfn": 1.3, "mag": 2.3,
                   "mdf": 1.5, "spd": 0.7},
        "weapon": "oak_rod",
        "palette": dict(H=(250, 230, 120), h=(205, 180, 80), S=(255, 224, 196),
                        E=(40, 30, 40), O=(130, 200, 235), o=(90, 155, 195),
                        T=(255, 255, 255), B=(90, 70, 80)),
        "techs": [
            dict(lvl=2, name="Mend", mp=2, kind="heal", power=34,
                 elem="none", target="ally", desc="Restore HP to one ally."),
            dict(lvl=4, name="Shimmer Veil", mp=4, kind="mag", power=1.0,
                 elem="ice", target="enemy", desc="A veil of cold light."),
            dict(lvl=6, name="Soothing Rain", mp=5, kind="heal", power=28,
                 elem="none", target="allies",
                 desc="Restore some HP to all allies."),
            dict(lvl=9, name="Frost Lance", mp=5, kind="mag", power=1.6,
                 elem="ice", target="enemy", desc="Impaling ice. One enemy."),
            dict(lvl=12, name="Radiant Lull", mp=8, kind="heal", power=46,
                 elem="none", target="allies",
                 desc="Restore strong HP to all allies."),
        ],
    },
    "vela": {
        "name": "Vela", "desc": "An eccentric engineer who builds her own luck.",
        "accent": "goggles",
        "base": {"hp": 76, "mp": 18, "atk": 7, "dfn": 6, "mag": 8, "mdf": 7,
                 "spd": 13},
        "growth": {"hp": 10, "mp": 3.5, "atk": 1.6, "dfn": 1.3, "mag": 2,
                   "mdf": 1.3, "spd": 0.8},
        "weapon": "slagthrower",
        "palette": dict(H=(150, 120, 235), h=(100, 78, 185), S=(250, 210, 170),
                        E=(40, 30, 40), O=(232, 238, 242), o=(180, 188, 196),
                        T=(255, 150, 60), B=(70, 70, 80)),
        "techs": [
            dict(lvl=2, name="Flame Toss", mp=2, kind="mag", power=0.95,
                 elem="fire", target="enemy", desc="Lobs a fire canister."),
            dict(lvl=5, name="Shock Coil", mp=4, kind="mag", power=1.1,
                 elem="bolt", target="enemy",
                 desc="A snarling arc of lightning."),
            dict(lvl=7, name="Napalm Rain", mp=6, kind="mag", power=0.9,
                 elem="fire", target="enemies",
                 desc="Showers fire on all enemies."),
            dict(lvl=10, name="Storm Coil", mp=7, kind="mag", power=1.0,
                 elem="bolt", target="enemies",
                 desc="Thunder rolls over all enemies."),
            dict(lvl=13, name="Omega Beam", mp=10, kind="mag", power=2.6,
                 elem="bolt", target="enemy", desc="Terrible science, focused."),
        ],
    },
}

# Double ("combo") techs: usable by one member if the other is battle-ready.
COMBOS = [
    dict(name="Blazing Waltz", a="kai", b="vela", mp=6, kind="waltz",
         elem="fire",
         desc="Kai & Vela: burning arcs strike ALL enemies."),
    dict(name="Radiant Guard", a="kai", b="nara", mp=5, kind="guard",
         elem="none",
         desc="Kai & Nara: shield-light restores ALL allies."),
    dict(name="Frost Tempest", a="nara", b="vela", mp=7, kind="tempest",
         elem="ice",
         desc="Nara & Vela: glacial gale batter ALL enemies."),
]

VILLAGER_PAL = dict(H=(80, 60, 40), h=(56, 42, 28), S=(240, 200, 160),
                    E=(40, 30, 40), O=(120, 170, 90), o=(86, 130, 64),
                    T=(230, 210, 170), B=(70, 56, 40))
VILLAGER2_PAL = dict(VILLAGER_PAL, H=(40, 40, 48), h=(28, 28, 34),
                     O=(200, 110, 90), o=(150, 80, 64))
KID_PAL = dict(VILLAGER_PAL, H=(230, 190, 100), h=(180, 145, 70),
               O=(150, 120, 200), o=(110, 88, 155))
ELDER_PAL = dict(H=(220, 220, 220), h=(160, 160, 165), S=(240, 200, 160),
                 E=(40, 30, 40), O=(160, 120, 80), o=(120, 90, 60),
                 T=(240, 240, 240), B=(60, 50, 45))
SHOPKEEP_PAL = dict(VILLAGER_PAL, H=(160, 110, 60), h=(120, 80, 42),
                    O=(90, 110, 170), o=(64, 80, 128))
SAILOR_PAL = dict(VILLAGER_PAL, H=(30, 30, 30), h=(24, 24, 26),
                  O=(235, 235, 235), o=(200, 200, 205),
                  T=(235, 60, 60), B=(50, 46, 60))
CAPTAIN_PAL = dict(VILLAGER_PAL, H=(180, 60, 50), h=(140, 44, 38),
                   O=(40, 60, 100), o=(28, 42, 72), T=(230, 190, 70),
                   S=(245, 215, 180))
SNOWFOLK_PAL = dict(VILLAGER_PAL, H=(200, 220, 245), h=(160, 185, 220),
                    O=(90, 130, 170), o=(64, 96, 128))
HERMIT_PAL = dict(VILLAGER_PAL, H=(150, 190, 210), h=(110, 150, 175),
                  O=(120, 140, 130), o=(90, 105, 98))

# ---------------------------------------------------------------------------
# Items & equipment
# ---------------------------------------------------------------------------
ITEMS = {
    "potion":   dict(name="Tonic", kind="item", heal=70, price=25,
                     desc="Restores 70 HP."),
    "hipotion": dict(name="Big Tonic", kind="item", heal=220, price=110,
                     desc="Restores 220 HP."),
    "elixir":   dict(name="Elixir", kind="item", heal=999, mana=99, price=320,
                     desc="Fully restores HP and MP."),
    "ether":    dict(name="Spark Jar", kind="item", mana=16, price=60,
                     desc="Restores 16 MP."),
    "cog_bomb": dict(name="Cog Bomb", kind="item", aoe=70, price=90,
                     desc="Battle item: 70 damage to ALL enemies."),
    # -- weapons: Kai --
    "rusted_blade": dict(name="Rusted Blade", kind="weapon", for_="kai",
                         atk=2, price=20, desc="Kai's trusty old sword."),
    "iron_blade":   dict(name="Iron Blade", kind="weapon", for_="kai",
                         atk=8, price=300, desc="Keen steel for Kai."),
    "corsair_saber": dict(name="Corsair Saber", kind="weapon", for_="kai",
                          atk=15, price=700,
                          desc="A blade that crossed the sea."),
    "storm_cleaver": dict(name="Storm Cleaver", kind="weapon", for_="kai",
                          atk=23, price=1500,
                          desc="Cleaves wind itself."),
    # -- weapons: Nara --
    "oak_rod":   dict(name="Oak Rod", kind="weapon", for_="nara",
                      atk=2, mag=2, price=20, desc="A blessed oak rod."),
    "moon_rod":  dict(name="Moon Rod", kind="weapon", for_="nara",
                      atk=3, mag=6, price=300, desc="A rod of lunar light."),
    "tide_rod":  dict(name="Tide Rod", kind="weapon", for_="nara",
                      atk=5, mag=11, price=750,
                      desc="Hums with the pull of tides."),
    "astral_rod": dict(name="Astral Rod", kind="weapon", for_="nara",
                       atk=8, mag=18, price=1600,
                       desc="Guided by far-off stars."),
    # -- weapons: Vela --
    "slagthrower": dict(name="Slagthrower", kind="weapon", for_="vela",
                        atk=4, price=20, desc="Vela's cobbled spark-gun."),
    "railthrower": dict(name="Railthrower", kind="weapon", for_="vela",
                        atk=6, mag=5, price=300,
                        desc="Terrible science, compact."),
    "harpoon_cannon": dict(name="Harpoon Cannon", kind="weapon", for_="vela",
                           atk=13, mag=7, price=750,
                           desc="Spears sparks over the sea."),
    "sky_repeater": dict(name="Sky Repeater", kind="weapon", for_="vela",
                         atk=19, mag=11, price=1600,
                         desc="A chatter of stars."),
    # -- charms (anyone) --
    "leather_guard": dict(name="Leather Guard", kind="charm", dfn=3,
                          price=150, desc="Tough hides. DEF +3."),
    "focus_coil":    dict(name="Focus Coil", kind="charm", mag=2, mdf=4,
                          price=300, desc="Hums with power. MAG+2 MDF+4."),
    "iron_heart":    dict(name="Iron Heart", kind="charm", dfn=7,
                          price=600, desc="Steady as stone. DEF +7."),
    "aurora_charm":  dict(name="Aurora Charm", kind="charm", mag=6, mdf=9,
                          price=1400, desc="Shimmers with northern lights."),
    "titan_chain":   dict(name="Titan Chain", kind="charm", dfn=10, mag=3,
                          mdf=5, price=0,
                          desc="Forged by Osk. A marvel."),
    # -- key items --
    "lantern":  dict(name="Sea Lantern", kind="key",
                     desc="Marla's lantern. It glows softly."),
    "core_gear": dict(name="Core Gear", kind="key",
                      desc="A pristine gear from the Deep Mill."),
    "aether_shard": dict(name="Aether Shard", kind="key",
                         desc="It hums, pointing somewhere high."),
}

SHOP_STOCKS = {
    "shop": ["potion", "ether", "cog_bomb", "iron_blade", "moon_rod",
             "railthrower", "leather_guard", "focus_coil"],
    "ember_arms": ["potion", "hipotion", "ether", "cog_bomb", "corsair_saber",
                   "tide_rod", "harpoon_cannon", "iron_heart", "focus_coil"],
    "frost_shop": ["hipotion", "elixir", "ether", "cog_bomb", "storm_cleaver",
                   "astral_rod", "sky_repeater", "aurora_charm", "iron_heart"],
}

# ---------------------------------------------------------------------------
# Enemies
# ---------------------------------------------------------------------------
ENEMIES = {
    "slime": dict(name="Goo Slug", hp=34, atk=7, dfn=5, mag=3, mdf=6, spd=9,
                  exp=7, gold=9, sprite="slime", scale=4, skills=None,
                  drop=("potion", 0.12)),
    "bat":   dict(name="Crank Bat", hp=26, atk=8, dfn=4, mag=5, mdf=5, spd=16,
                  exp=8, gold=8, sprite="bat", scale=4, skills=None,
                  drop=("ether", 0.08)),
    "wolf":  dict(name="Frost Fang", hp=52, atk=11, dfn=7, mag=4, mdf=6,
                  spd=13, exp=15, gold=16, sprite="wolf", scale=4,
                  skills=None, drop=None),
    "scrap": dict(name="Scrapling", hp=62, atk=13, dfn=12, mag=9, mdf=8,
                  spd=10, exp=24, gold=32, sprite="scrap", scale=4,
                  drop=("hipotion", 0.15),
                  skills={"Arc Spark": dict(kind="mag", power=1.0,
                                            elem="bolt", target="enemy",
                                            weight=0.3)}),
    "boss":  dict(name="GEARLORD VX", hp=260, atk=17, dfn=14, mag=13, mdf=12,
                  spd=12, exp=90, gold=320, sprite="boss", scale=5,
                  weak="bolt", resist="fire", drop=None,
                  skills={
                      "Piston Punch": dict(kind="phys", power=0.9,
                                           elem="none", target="enemy",
                                           weight=0.35),
                      "Steam Burst": dict(kind="mag", power=0.75,
                                          elem="fire", target="enemies",
                                          weight=0.30)}),
    # ---- Chapter 2: the coast ----
    "ember_slug": dict(name="Ember Slug", hp=52, atk=11, dfn=8, mag=6, mdf=6,
                       spd=9, exp=20, gold=24, sprite="ember_slug", scale=4,
                       drop=("potion", 0.15), skills=None),
    "snapjaw": dict(name="Snapjaw", hp=64, atk=12, dfn=13, mag=4, mdf=8,
                    spd=10, exp=28, gold=32, sprite="snapjaw", scale=4,
                    drop=("potion", 0.12), skills=None),
    "buccaneer": dict(name="Buccaneer", hp=80, atk=15, dfn=9, mag=8, mdf=8,
                      spd=12, exp=42, gold=50, sprite="buccaneer", scale=4,
                      drop=("cog_bomb", 0.14),
                      skills={"Rum Smash": dict(kind="phys", power=0.8,
                                                elem="none", target="enemy",
                                                weight=0.3)}),
    "hollow": dict(name="Hollow", hp=70, atk=12, dfn=8, mag=16, mdf=14,
                   spd=11, exp=46, gold=40, sprite="hollow", scale=4,
                   drop=("ether", 0.15),
                   skills={"Soul Chill": dict(kind="mag", power=0.9,
                                              elem="none", target="enemy",
                                              weight=0.35)}),
    "gloom_jelly": dict(name="Gloom Jelly", hp=100, atk=13, dfn=10, mag=12,
                        mdf=16, spd=9, exp=58, gold=52, sprite="jelly",
                        scale=4, drop=("hipotion", 0.14),
                        skills={"Tangle": dict(kind="phys", power=0.7,
                                               elem="none", target="enemies",
                                               weight=0.4)}),
    # ---- Chapter 3: the north ----
    "snow_wolf": dict(name="Howler Wolf", hp=92, atk=17, dfn=9, mag=6, mdf=8,
                      spd=15, exp=58, gold=46, sprite="snow_wolf", scale=4,
                      drop=("potion", 0.2), skills=None),
    "frost_ape": dict(name="Frost Ape", hp=145, atk=20, dfn=14, mag=10,
                      mdf=12, spd=11, exp=90, gold=85, sprite="frost_ape",
                      scale=4, drop=("hipotion", 0.2),
                      skills={"Ice Crash": dict(kind="mag", power=0.85,
                                                elem="ice",
                                                target="enemies",
                                                weight=0.4)}),
    # ---- Chapter 4: the sky ----
    "cog_drone": dict(name="Cog Drone", hp=130, atk=20, dfn=18, mag=12,
                      mdf=15, spd=10, exp=100, gold=110, sprite="cog_drone",
                      scale=4, drop=("hipotion", 0.18),
                      skills={"Arc Spark": dict(kind="mag", power=1.0,
                                                elem="bolt", target="enemy",
                                                weight=0.35)}),
    "turret": dict(name="Sky Turret", hp=115, atk=22, dfn=12, mag=17,
                   mdf=18, spd=8, exp=105, gold=100, sprite="sentry",
                   scale=4, drop=("ether", 0.2),
                   skills={"Suppress": dict(kind="mag", power=0.8,
                                            elem="none", target="enemies",
                                            weight=0.45)}),
    "sky_sentry": dict(name="Sky Sentry", hp=190, atk=25, dfn=20, mag=15,
                       mdf=16, spd=12, exp=160, gold=155, sprite="sky_sentry",
                       scale=4, drop=("elixir", 0.1),
                       skills={"Skyfall": dict(kind="mag", power=1.0,
                                               elem="bolt",
                                               target="enemies",
                                               weight=0.4)}),
    # ---- bosses ----
    "rusthook": dict(
        name="CAPTAIN RUSTHOOK", hp=480, atk=22, dfn=15, mag=15, mdf=13,
        spd=11, exp=350, gold=520, sprite="rusthook", scale=5, weak="bolt",
        drop=("lantern", 1.0),
        skills={
            "Anchor Slam": dict(kind="phys", power=0.85, elem="none",
                                target="enemies", weight=0.35),
            "Claw Crush": dict(kind="phys", power=1.15, elem="none",
                               target="enemy", weight=0.35)}),
    "colossus": dict(
        name="RIME COLOSSUS", hp=640, atk=26, dfn=18, mag=22, mdf=17,
        spd=10, exp=520, gold=720, sprite="colossus", scale=5,
        weak="fire",
        skills={
            "Glacial Roar": dict(kind="mag", power=0.95, elem="ice",
                                 target="enemies", weight=0.4),
            "Avalanche Fist": dict(kind="phys", power=1.2, elem="none",
                                   target="enemy", weight=0.4)}),
    "archon": dict(
        name="ARCHON PRIME", hp=980, atk=30, dfn=22, mag=25, mdf=21,
        spd=14, exp=1100, gold=1500, sprite="archon", scale=5, weak="none",
        skills={
            "Judgewave": dict(kind="mag", power=1.0, elem="none",
                              target="enemies", weight=0.4),
            "Ion Lance": dict(kind="phys", power=1.6, elem="none",
                              target="enemy", weight=0.4)}),
    "millwright": dict(
        name="THE MILLWRIGHT", hp=420, atk=25, dfn=21, mag=12, mdf=14,
        spd=10, exp=420, gold=800, sprite="millwright", scale=5, weak="none",
        drop=("core_gear", 1.0),
        skills={"Piston Barrage": dict(kind="phys", power=0.75,
                                       elem="none", target="enemies",
                                       weight=0.4)}),
    "omega": dict(
        name="OMEGA COG", hp=1500, atk=37, dfn=27, mag=30, mdf=26,
        spd=15, exp=2200, gold=3000, sprite="omega", scale=6, resist="fire",
        weak="none",
        skills={
            "Cataclysm": dict(kind="mag", power=1.15, elem="none",
                              target="enemies", weight=0.35),
            "Mach Fist": dict(kind="phys", power=2.0, elem="none",
                              target="enemy", weight=0.35)}),
}

# zone-based random encounter tables (list = pick zone by rect)
ENCOUNTERS = {
    "overworld": dict(table=[("slime", 4), ("bat", 3), ("wolf", 2)],
                      size=[(1, 5), (2, 4), (3, 2)],
                      rate=0.10, min_steps=5),
    "east_road": [
        dict(name="forestsouth", rect=(1, 6, 26, 27),
             table=[("snapjaw", 4), ("bat", 3), ("buccaneer", 3),
                    ("ember_slug", 3)],
             size=[(1, 4), (2, 4), (3, 2)], rate=0.10, min_steps=5),
        dict(name="snowfields", rect=(27, 1, 45, 14),
             table=[("snow_wolf", 4), ("frost_ape", 3), ("bat", 2)],
             size=[(1, 4), (2, 4), (3, 2)], rate=0.10, min_steps=5),
        dict(name="coast", rect=(1, 28, 45, 37),
             table=[("buccaneer", 4), ("snapjaw", 4), ("ember_slug", 2)],
             size=[(1, 3), (2, 4), (3, 3)], rate=0.11, min_steps=5),
    ],
}

# Fixed monster entities in maps (optionally gated by 'require' flag)
ENTITIES = {
    "cavern": [
        dict(id="c1", sprite="slime", pos=(13, 13), wander=2,
             group=["slime", "slime"]),
        dict(id="c2", sprite="bat", pos=(10, 14), wander=3,
             group=["bat", "bat"]),
        dict(id="c3", sprite="scrap", pos=(19, 18), wander=2, group=["scrap"]),
        dict(id="c4", sprite="slime", pos=(7, 13), wander=2,
             group=["slime", "slime", "bat"]),
        dict(id="boss", sprite="boss", pos=(14, 5), wander=0, boss=True,
             group=["boss"], on_defeat="shard1"),
    ],
    "umbra_wreck": [
        dict(id="w1", sprite="jelly", pos=(13, 15), wander=2,
             group=["gloom_jelly", "hollow"]),
        dict(id="w2", sprite="snapjaw", pos=(8, 12), wander=3,
             group=["snapjaw", "buccaneer"]),
        dict(id="w3", sprite="hollow", pos=(20, 10), wander=2,
             group=["hollow", "hollow", "gloom_jelly"]),
        dict(id="w4", sprite="buccaneer", pos=(10, 7), wander=2,
             group=["buccaneer", "snapjaw", "buccaneer"]),
        dict(id="wboss", sprite="rusthook", pos=(15, 4), wander=0, boss=True,
             group=["rusthook", "buccaneer"], on_defeat="shard2"),
    ],
    "glacial_vault": [
        dict(id="g1", sprite="hollow", pos=(9, 15), wander=2,
             group=["snow_wolf", "snow_wolf", "frost_ape"]),
        dict(id="g2", sprite="frost_ape", pos=(21, 13), wander=3,
             group=["frost_ape", "snow_wolf"]),
        dict(id="g3", sprite="hollow", pos=(15, 9), wander=2,
             group=["frost_ape", "frost_ape", "snow_wolf"]),
        dict(id="gboss", sprite="colossus", pos=(15, 4), wander=0, boss=True,
             group=["colossus"], on_defeat="shard3"),
    ],
    "sky_bastion": [
        dict(id="s1", sprite="turret", pos=(9, 16), wander=0,
             group=["cog_drone", "turret"]),
        dict(id="s2", sprite="turret", pos=(24, 16), wander=0,
             group=["turret", "turret"]),
        dict(id="s3", sprite="sky_sentry", pos=(12, 8), wander=3,
             group=["sky_sentry", "cog_drone"]),
        dict(id="s4", sprite="sky_sentry", pos=(21, 10), wander=3,
             group=["cog_drone", "sky_sentry"]),
        dict(id="s5", sprite="hollow", pos=(17, 14), wander=2,
             group=["sky_sentry", "turret", "cog_drone"]),
        dict(id="aboss", sprite="boss", pos=(17, 4), wander=0, boss=True,
             group=["archon"], on_defeat="shard4"),
        dict(id="omega", sprite="omega", pos=(7, 4), wander=1, boss=True,
             group=["omega"], require="shard4",
             on_defeat="omega_slain"),
    ],
    "deep_mill": [
        dict(id="m1", sprite="scrap", pos=(9, 16), wander=2,
             group=["scrap", "scrap", "cog_drone"]),
        dict(id="m2", sprite="hollow", pos=(18, 13), wander=2,
             group=["cog_drone", "cog_drone"]),
        dict(id="mboss", sprite="boss", pos=(14, 4), wander=0, boss=True,
             group=["millwright"], on_defeat="mill_slain"),
    ],
}

# ship travel (interact with the ship sprite)
SHIPS = {
    "ember_port": dict(x=16, y=21, to="umbra_wreck", tx=15, ty=23,
                       face="up", req=None,
                       lines=["(You board the Sea Lantern.)",
                              "Row steers the little ship into the bay...",
                              "*The wreck looms out of the fog.*"]),
}
# after chapter 2 the ship can also sail to the north coast
SHIPS2 = dict(ember_port=dict(
    x=16, y=21, alt=dict(to="east_road", tx=40, ty=5, face="down",
                         lines=["(The Sea Lantern braves the north wind...)"],
                         req="shard2")))

BOSS_INTRO = None
BOSS_INTROS = {
    "rusthook": ["*A wall of barnacles rises from the deck...*",
                 "RUSTHOOK: Yo-ho! Fresh chum for me claws!"],
    "colossus": ["*The vault's ice begins to breathe...*",
                 "RIME COLOSSUS: COLD. COLDER. COLDEST."],
    "archon": ["*The Aether core blazes above the throne...*",
               "ARCHON PRIME: RULING LOGIC: EXTINGUISH."],
    "millwright": ["*Old gears grind awake in the dark.*",
                   "MILLWRIGHT: INVENTORY UNBALANCED. CORRECTING."],
    "omega": ["*The ancient core unfolds into a god-machine.*",
              "OMEGA COG: WITNESS PERFECTION."],
    "boss": ["*Something huge hefts itself off the cavern floor...*",
             "GEARLORD VX: OBSERVATION - INTRUDERS. VERDICT: SCRAP THEM."],
}

# ---------------------------------------------------------------------------
# Quests (shown in the menu)
# ---------------------------------------------------------------------------
QUESTS = [
    dict(id="q_main1", title="Scrap the Gearlord", flag="shard1",
         active="Clear the Cavern of Cogs, north of Cinderhollow.",
         done="The beacon sleeps. A road has opened EAST of Cinder Road."),
    dict(id="q_main2", title="Emberport's Debt", flag="shard2",
         active="Sail from Emberport's pier to the Umbra Wreck and "
                "sink Captain Rusthook.",
         done="The Sea Lantern sails north once more."),
    dict(id="q_main3", title="The Thaw", flag="shard3",
         active="Face the Rime Colossus inside the Glacial Vault.",
         done="The colossus sleeps for good."),
    dict(id="q_main4", title="Storm the Bastion", flag="shard4",
         active="The Aether gate east is open - defeat Archon Prime.",
         done="Peace settles over the clouds."),
    dict(id="q_lantern", title="Marla's Lantern", flag="q_lantern",
         active="Raiders stole Marla's lantern. Search the Umbra Wreck.",
         done="The lantern glows over Emberport again."),
    dict(id="q_bounty", title="Bounty: Goo Slugs", flag="q_bounty",
         active="Bram Jr. pays 90 gil for 10 Goo Slugs scrapped.",
         done="The bounty is paid in full."),
    dict(id="q_mill", title="The Deep Mill", flag="q_mill",
         active="Smith Osk wants a Core Gear from the rusting mill.",
         done="Osk forged the Titan Chain."),
]


def quest_line(flags):
    for q in [q for q in QUESTS if q["id"].startswith("q_main")]:
        if q["flag"] not in flags:
            return q["active"]
    return "You are a hero of the realm! Explore freely."


# ---------------------------------------------------------------------------
# MAPS
# ---------------------------------------------------------------------------
# . grass   , tallgrass   T tree   f flowers   ~ water   # path   B bridge
# W wall    R roof (red) r roof (slate)  D door  Y window  s prop-sign
# x fence   i wood floor c counter      b barrel  C cave wall  _ cave floor
# O cave opening  w snow   V rock    L lamp   o well   K stall   H hay
# e bookshelf  d bed  n rug  U mushroom  g gear heap  S ship  t torch

TOWN = [
    "TTTTTTTTTTT##TTTTTTTTTTTTTTTTTTT",
    "Tf.........##..................fT",
    "T" + ".." + "R"*8 + "##" + "r"*9 + ".." + "R"*6 + "." + "T",
    "T" + ".." + "WYWDWWWY" + "##" + "WWYWDWYWY" + ".." + "WYWDWY" + "." + "T",
    "T.....#....##....#.........#...T",
    "T.....#....##....#.........#...T",
    "T.############################.T",
    "T.....#..........#.........#...T",
    "T.............##...............T",
    "T...f.........##..........f....T",
    "T.............##...............T",
    "T.b...........##...............T",
    "T.............##...............T",
    "T.....f.......##.......f.......T",
    "T.............##...f...........T",
    "T.............##...............T",
    "T.b...........##.....b.........T",
    "T.............##...............T",
    "T....f........##...............T",
    "T.............##...............T",
    "T.............######..s........T",
    "T..............................T",
    "T...f..................f.......T",
    "T..............................T",
    "T..............................T",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
]

ELDER_HOME = [
    "WWWWWWWWWWWWWWW",
    "WiiiiiiiiiiiiiW",
    "WiiiiiiiiiiiiiW",
    "WiiiiccccciiiiW",
    "WiiiiiiiiiiiiiW",
    "WibiiiiiiiiiiiW",
    "WiiiiiiiiiiiiiW",
    "WWWWWWWDWWWWWWW",
]

INN = [
    "WWWWWWWWWWWWWWW",
    "WdddddddddddddW",
    "WiiiiiiiiiiiiiW",
    "WiiiiiiiiiiiiiW",
    "WiiiicccciiiiiW",
    "WiiiiiiiiiiiiiW",
    "WiiiiiiiiiiiiiW",
    "WiiiiiiiiiiiiiW",
    "WWWWWWWDWWWWWWW",
]

SHOP = [
    "WWWWWWWWWWWWWWW",
    "WiiiiiiiiiiiiiW",
    "WiiiiiiiiiiiiiW",
    "WiiccccccccciiW",
    "WiiiiiiiiiiiiiW",
    "WibiiiiiiiiiibW",
    "WiiiiiiiiiiiiiW",
    "WiiiiiiiiiiiiiW",
    "WWWWWWWDWWWWWWW",
]

OVERWORLD = [
    "T"*12 + "f" + "T"*23,                                              # 0
    "Tf................................T",                              # 1
    "T.....................TTTTTTTTTTTT",                              # 2
    "T.....................CCOOCCCCCTTTTT"[0:36],                       # 3
    "T.....................CCOOCCCCCTTTTT"[0:36],                       # 4
    "T.......................##.........T",                             # 5
    "T..f.....................##........T",                             # 6
    "T.,,,,,,,,,..............##........T",                             # 7
    "T.,,,,,,,,,..............##........T",                             # 8
    "T.,,,,,,,,,..............##........T",                             # 9
    "T............##############........T",                             # 10
    "T.............##...................T",                             # 11
    "T.~~~~~~......##...................T",                             # 12
    "T.~~~~~~......##..,,,,,...........T",                              # 13
    "T..~~~~.......##..,,,,,...........T",                              # 14
    "T..~~~~.......##..,,,,,...........T",                              # 15
    "T..~~~~.......##..................T",                              # 16
    "T.............##..................T",                               # 17
    "T...b.........##..................T",                               # 18
    "T.............##..................T",                               # 19
    "T..f..........##..................T",                               # 20
    "T.............##...............###T",                              # 21
    "T.............##................T",                                # 22
    "T....s........##................T",                                # 23
    "T.............##................T",                                # 24
    "T.............##................T",                                # 25
    "TTTTTTTTTTTTTT##TTTTTTTTTTTTTTTTTT"[0:36],                         # 26
]

# east exit at row 21 cols 32-34 leads to the great East Road


# carve the east gate into OVERWORLD + exits to it
def _carve_overworld_exit():
    OVERWORLD[21] = OVERWORLD[21][:21] + (OVERWORLD[21][21:34].replace(".",
        "#")) + ".." + OVERWORLD[21][35:]
    for y in (20, 21, 22):
        pass


_carve_overworld_exit()

EAST_ROAD = [
    # 46 cols x 38 rows. Built from segments for exact widths.
    # w = snow ground, ',' tall grass, trees T, water ~, road #
]

def _R(width, *chunks):
    s = "".join(c * n for c, n in chunks)
    assert len(s) == width, f"row width {len(s)} != {width}: {s!r}"
    return s

W46 = 46
W30 = 30
W32 = 32
W34 = 34

ER = []
ER = []
ER.append(_R(46, ("T", 46)))                                                # 0
ER.append(_R(46, ("T", 1), ("w", 44), ("T", 1)))
ER.append(_R(46, ("T", 1), ("V", 2), ("w", 24), ("T", 3), ("w", 15), ("T", 1)))
for _ in range(4):                                                          # 3-6
    ER.append(_R(46, ("T", 1), ("w", 26), (",", 4), ("w", 13), ("T", 2)))
ER.append(_R(46, ("T", 1), ("w", 24), ("V", 3), (",", 4), ("w", 12), ("T", 2)))
ER.append(_R(46, ("T", 1), ("w", 43), ("#", 1), ("T", 1)))                  # 8 gate
ER.append(_R(46, ("T", 1), ("w", 43), ("#", 1), ("T", 1)))                  # 9
for _ in range(7):                                                          # 10-16
    ER.append(_R(46, ("T", 1), ("w", 23), ("#", 1), ("w", 20), ("T", 1)))
ER.append(_R(46, ("T", 1), ("w", 6), ("V", 3), ("w", 12), ("#", 21), ("T", 3)))
for _ in range(5):                                                          # 20-24
    ER.append(_R(46, ("T", 1), ("w", 18), ("#", 1), ("w", 24), ("T", 2)))
ER.append(_R(46, ("T", 1), ("w", 18), ("#", 1), ("w", 21), ("#", 1),
             ("w", 3), ("T", 1)))                                       # 25 sky arm
ER.append(_R(46, ("T", 1), ("w", 40), ("O", 1), ("w", 3), ("T", 1)))       # 26 mouth
for _ in range(6):                                                          # 27-32
    ER.append(_R(46, ("T", 1), (".", 18), ("#", 1), ("w", 24), ("T", 2)))
ER.append(_R(46, ("T", 1), (".", 18), ("O", 1), ("w", 24), ("T", 2)))       # 33 mouth
for _ in range(3):                                                          # 34-36
    ER.append(_R(46, ("T", 1), (".", 18), ("#", 1), ("w", 24), ("T", 2)))
ER.append(_R(46, ("T", 19), ("#", 2), ("T", 24), ("T", 1)))
EAST_ROAD = ER

# ---- Emberport (32 x 22) ------------------------------------------------
E = []
E.append(_R(32, ("T", 17), ("#", 2), ("T", 13)))                        # 0 gate
E.append(_R(32, ("T", 1), ("f", 1), (".", 29), ("T", 1)))               # 1
E.append(_R(32, ("T", 3), ("R", 8), (".", 2), ("r", 9), (".", 9), ("T", 1)))   # 2
E.append(_R(32, ("T", 3), ("WYWDWWWY", 1), (".", 2), ("WWYWDWYWY", 1),
             (".", 9), ("T", 1)))                                       # 3
E.append(_R(32, ("T", 1), (".", 21), ("#", 2), (".", 7), ("T", 1)))     # 4
E.append(_R(32, ("T", 6), ("#", 1), (".", 14), ("#", 2), (".", 8), ("T", 1)))  # 5
E.append(_R(32, ("T", 6), ("#", 1), (".", 14), ("#", 2), (".", 8), ("T", 1)))  # 6
E.append(_R(32, ("T", 1), (".", 1), ("#", 28), (".", 1), ("T", 1)))     # 7
E.append(_R(32, ("T", 6), ("#", 1), (".", 9), ("#", 1), (".", 14), ("T", 1)))  # 8
E.append(_R(32, ("T", 6), ("#", 1), (".", 9), ("#", 1), (".", 14), ("T", 1)))  # 9
E.append(_R(32, ("T", 6), ("#", 1), (".", 9), ("#", 1), (".", 14), ("T", 1)))  # 10
E.append(_R(32, ("T", 1), (".", 30), ("T", 1)))                         # 11
for _y in range(12, 22):                                                # 12-21 water + pier
    # pier cols 15,16,17; ship 'S' sits at (16,20)
    E.append(_R(32, ("T", 1), ("~", 14), ("B", 3), ("~", 13), ("T", 1)))
E[-1] = _R(32, ("T", 1), ("~", 14), ("B", 1), ("S", 1), ("B", 1), ("~", 13),
           ("T", 1))
EMBER_PORT = E

# ---- Frostline (30 x 20) ------------------------------------------------
F = []
F.append(_R(30, ("T", 30)))                                             # 0
F.append(_R(30, ("T", 1), ("w", 28), ("T", 1)))                         # 1
F.append(_R(30, ("T", 3), ("R", 8), (".", 3), ("r", 9), (".", 6), ("T", 1)))   # 2
F.append(_R(30, ("T", 3), ("WYWDWWWY", 1), (".", 3), ("WWYWDWYWY", 1),
             (".", 6), ("T", 1)))                                       # 3
F.append(_R(30, ("T", 6), ("#", 1), ("w", 10), ("#", 1), ("w", 11), ("T", 1))) # 4
F.append(_R(30, ("T", 6), ("#", 1), ("w", 10), ("#", 1), ("w", 11), ("T", 1))) # 5
F.append(_R(30, ("T", 1), ("#", 28), ("T", 1)))                         # 6
for _ in range(6):                                                      # 7-12
    F.append(_R(30, ("T", 6), ("#", 1), ("w", 10), ("#", 1), ("w", 11),
                 ("T", 1)))
F.append(_R(30, ("T", 1), ("w", 28), ("T", 1)))                         # 13
F.append(_R(30, ("T", 1), ("U", 1), ("w", 27), ("T", 1)))               # 14
F.append(_R(30, ("T", 1), ("w", 28), ("T", 1)))                         # 15
for _ in range(3):                                                      # 16-18
    F.append(_R(30, ("T", 1), ("w", 28), ("T", 1)))
F.append(_R(30, ("T", 15), ("#", 2), ("T", 13)))                        # 19 gate
FROSTLINE = F
# the Glacial Vault gate in Frostline's southern treeline
FROSTLINE[19] = FROSTLINE[19][:22] + "##" + FROSTLINE[19][24:]

# ---- Umbra Wreck (30 x 26) ----------------------------------------------
U = [
    _R(30, ("C", 30)),
    _R(30, ("C", 2), ("i", 26), ("C", 2)),
    _R(30, ("C", 2), ("i", 4), ("b", 1), ("i", 17), ("b", 1), ("i", 3),
       ("C", 2)),
]
for _ in range(3):     # rows 4-6 open deck with boss
    U.append(_R(30, ("C", 2), ("i", 26), ("C", 2)))
for _ in range(15):    # rows 7-21 hold + pillars
    U.append(_R(30, ("C", 2), ("i", 4), ("C", 1), ("i", 16), ("C", 1),
                 ("i", 4), ("C", 2)))
U.pop()
U = U[:12]
# rebuild: deck rows 0-6 with boss chamber; hold rows 7-23; entrance row 25
U = []
U.append(_R(30, ("C", 13), ("O", 4), ("C", 13)))                        # 0 sky
U.append(_R(30, ("C", 2), ("i", 26), ("C", 2)))                         # 1
U.append(_R(30, ("C", 2), ("i", 4), ("b", 1), ("i", 17), ("b", 1),
             ("i", 3), ("C", 2)))                                       # 2
for _ in range(5):                                                      # 3-7 deck
    U.append(_R(30, ("C", 2), ("i", 26), ("C", 2)))
U.append(_R(30, ("C", 2), ("i", 8), ("C", 12), ("i", 6), ("C", 2)))     # 8 wall
for _ in range(15):                                                     # 9-23 hold
    U.append(_R(30, ("C", 2), ("i", 4), ("C", 1), ("i", 16), ("C", 1),
                 ("i", 4), ("C", 2)))
U = U[:-3] if False else U
# hold continues; bottom row entrance
U = U[:25]
U.append(_R(30, ("C", 15), ("O", 1), ("C", 14)))                        # 25 gate
UMBRA_WRECK = U
# ---- Glacial Vault (30 x 24) ----
V = []
V.append(_R(30, ("C", 30)))                                            # 0
V.append(_R(30, ("C", 2), ("_", 26), ("C", 2)))                        # 1
for _ in range(3):                                                     # 2-4 boss room
    V.append(_R(30, ("C", 2), ("_", 26), ("C", 2)))
V.append(_R(30, ("C", 2), ("_", 8), ("C", 12), ("_", 6), ("C", 2)))    # 5 wall
for _ in range(17):                                                    # 6-22 halls
    V.append(_R(30, ("C", 2), ("_", 4), ("C", 1), ("_", 16), ("C", 1),
                 ("_", 4), ("C", 2)))
V.pop()
V = V[:23]
for _ in range(2):                                                     # 22-23
    V.append(_R(30, ("C", 2), ("_", 26), ("C", 2)))
V.append(_R(30, ("C", 14), ("O", 2), ("C", 14)))                       # 24 gate
GLACIAL_VAULT = V

# ---- Sky Bastion (34 x 26; throne up top, gate at bottom) ----
S = []
S.append(_R(34, ("W", 34)))                                            # 0
S.append(_R(34, ("W", 2), ("_", 30), ("W", 2)))                        # 1
for _ in range(3):                                                     # 2-4 boss room
    S.append(_R(34, ("W", 2), ("_", 30), ("W", 2)))
S.append(_R(34, ("W", 2), ("_", 8), ("W", 14), ("_", 8), ("W", 2)))    # 5 wall
for _ in range(6):                                                     # 6-11 halls
    S.append(_R(34, ("W", 2), ("_", 4), ("W", 1), ("_", 26), ("W", 1)))
S.append(_R(34, ("W", 2), ("_", 8), ("W", 14), ("_", 8), ("W", 2)))    # 12 wall
for _ in range(6):                                                     # 13-18 halls
    S.append(_R(34, ("W", 2), ("_", 4), ("W", 1), ("_", 26), ("W", 1)))
S.append(_R(34, ("W", 2), ("_", 8), ("W", 14), ("_", 8), ("W", 2)))    # 19 wall
for _ in range(4):                                                     # 20-23 entry
    S.append(_R(34, ("W", 2), ("_", 30), ("W", 2)))
S.append(_R(34, ("W", 17), ("#", 2), ("W", 15)))                       # 24
S.append(_R(34, ("W", 17), ("#", 2), ("W", 15)))                       # 25 gate
SKY_BASTION = S

# ---- Deep Mill (28 x 22) ----
M = []
M.append(_R(28, ("C", 28)))                                            # 0
M.append(_R(28, ("C", 2), ("i", 24), ("C", 2)))                        # 1
for _ in range(3):                                                     # 2-4 boss room
    M.append(_R(28, ("C", 2), ("i", 24), ("C", 2)))
M.append(_R(28, ("C", 2), ("i", 6), ("C", 12), ("i", 6), ("C", 2)))    # 5 wall
for _ in range(13):                                                    # 6-18 halls
    M.append(_R(28, ("C", 2), ("i", 3), ("C", 1), ("i", 16), ("C", 1),
                 ("i", 3), ("C", 2)))
M.pop()
M = M[:20]
for _ in range(2):                                                     # 19-20
    M.append(_R(28, ("C", 2), ("i", 24), ("C", 2)))
M.append(_R(28, ("C", 14), ("O", 1), ("C", 13)))                       # 21 gate
DEEP_MILL = M
# fix wreck entry + sky ship arrival targets
SHIPS["ember_port"]["ty"] = 23

# carve the umbra top hole shut (decor safety)
UMBRA_WRECK[0] = "C" * 30

MAPS = {
    "town": dict(
        name="Cinderhollow", fill="T", music="town", encounters=None,
        exits=[
            dict(x=11, y=0, to="overworld", tx=14, ty=24, face="up"),
            dict(x=12, y=0, to="overworld", tx=14, ty=24, face="up"),
            dict(x=6, y=3, to="elder_home", tx=7, ty=6, face="up"),
            dict(x=17, y=3, to="shop", tx=7, ty=7, face="up"),
            dict(x=27, y=3, to="locked", tx=27, ty=3, face="down"),
        ],
        signs={
            (2, 4): ["** ELDER BRAM **", "The father of every plan."],
            (22, 4): ["* RUSTY NAIL GENERAL STORE *"],
            (22, 20): ["NORTH ROAD: Cavern of Cogs,", "past the old fields."],
        },
        npcs=[
            dict(id="v1", x=5, y=10, pal=VILLAGER_PAL, face="down", wander=1,
                 dialog=[dict(req="shard1",
                              lines=["Farmer: The mountain hums kindly again.",
                                     "Farmer: They say a new road opened - and "
                                     "trouble beyond it. Watch the grass."]),
                         dict(req="met_elder",
                              lines=["Farmer: Goo Slugs got into my turnips again!",
                                     "Farmer: Walk in tall grass and you'll meet 'em."]),
                         dict(req=None,
                              lines=["Farmer: Elder Bram called for you three.",
                                     "Farmer: He's in the westmost house."])]),
            dict(id="v2", x=10, y=12, pal=VILLAGER2_PAL, face="down", wander=1,
                 dialog=[dict(req=None,
                              lines=["Matron: Rest at blue crystals - they "
                                     "mend and remember."])]),
            dict(id="v3", x=22, y=14, pal=KID_PAL, face="down", wander=2,
                 dialog=[dict(req=None,
                              lines=["Kid: Grownups never let me near the cavern.",
                                     "Kid: 'Cause - monsters eat kids. Obviously."])]),
            dict(id="v4", x=12, y=18, pal=VILLAGER_PAL, face="down", wander=0,
                 dialog=[dict(req=None,
                              lines=["Old Timer: The fields north are safe. The cavern? "
                                     "Not so much."])]),
            dict(id="bounty", x=17, y=19, pal=SHOPKEEP_PAL, face="down",
                 wander=0,
                 dialog=[
                     dict(req="q_bounty",
                          lines=["Bram Jr.: Bounty's paid. You're a natural."]),
                     dict(req="kills:slime:10",
                          lines=["Bram Jr.: Ten slugs?! My hero! Pay the man!",
                                 "*You receive 90 gil!*"], 
                          give=dict(gold=90, exp=140), set=["q_bounty"]),
                     dict(req=None,
                          lines=["Bram Jr.: BOUNTY! Ten Goo Slugs for 90 gil.",
                                 "Bram Jr.: They count squished - in the "
                                 "cavern or the grass.",
                                 "*Current: " + str(0) + "*"]),
                 ]),
        ],
        chests=[dict(id="town_chest", x=30, y=1, item="potion", qty=1)],
        crystals=[], entities=[],
    ),
    "elder_home": dict(
        name="Elder's Home", fill="W", music="town", encounters=None,
        exits=[dict(x=7, y=7, to="town", tx=6, ty=5, face="down")],
        signs={}, chests=[],
        crystals=[(12, 2)],
        entities=[],
        npcs=[
            dict(id="elder", x=7, y=2, pal=ELDER_PAL, face="down", wander=0,
                 accent="beard",
                 dialog=[
                     dict(req="!met_elder",
                          lines=["Bram: Kai, Nara, Vela... the whole gang.",
                                 "Bram: GEARLORD VX is a BEACON, they say. Scrap",
                                 "Bram: it, and find out WHY it woke.",
                                 "Bram: Take 120 gil. The shop has fine steel.",
                                 "*You receive 120 gil!*"],
                          give=dict(gold=120), set=["met_elder", "quest_active"]),
                     dict(req="!shard1",
                          lines=["Bram: The cavern is north - take the old road.",
                                 "Bram: Blue crystals mend wounds and save."]),
                     dict(req="!reward_given",
                          lines=["Bram: The whole town heard the gears go silent!",
                                 "Bram: Here - 350 gil. The thanks of Cinderhollow.",
                                 "*You receive 350 gil!*"],
                          give=dict(gold=350), set=["reward_given"]),
                     dict(req=None,
                          lines=["Bram: Rest easy, heroes.",
                                 "Bram: And do visit. Old war stories are free."]),
                 ])],
    ),
    "shop": dict(
        name="Rusty Nail Store", fill="W", music="town", encounters=None,
        exits=[dict(x=7, y=8, to="town", tx=17, ty=5, face="down")],
        signs=[], chests=[], crystals=[], entities=[],
        npcs=[dict(id="shopkeep", x=6, y=2, pal=SHOPKEEP_PAL, face="down",
                   wander=0, shop=True, stock=SHOP_STOCKS["shop"],
                   accent="apron",
                   dialog=[dict(req=None,
                                lines=["Keeper: Welcome to the Rusty Nail!",
                                       "Keeper: Everything sharpened, "
                                       "water-proofed, or explosive."])])],
    ),
    "overworld": dict(
        name="Cinder Road", fill="T", music="over",
        encounters=ENCOUNTERS["overworld"],
        exits=[
            dict(x=14, y=26, to="town", tx=11, ty=1, face="down"),
            dict(x=15, y=26, to="town", tx=11, ty=1, face="down"),
            dict(x=24, y=3, to="cavern", tx=14, ty=23, face="up"),
            dict(x=25, y=3, to="cavern", tx=14, ty=23, face="up"),
            dict(x=24, y=4, to="cavern", tx=14, ty=23, face="up"),
            dict(x=25, y=4, to="cavern", tx=14, ty=23, face="up"),
            dict(x=34, y=21, to="east_road", tx=2, ty=18, face="right",
                 req="shard1"),
            dict(x=33, y=21, to="east_road", tx=2, ty=18, face="right",
                 req="shard1"),
        ],
        signs={
            (5, 23): ["NORTH: Cavern of Cogs.",
                      "EAST: the new road - sealed by the Elder... for now."],
        },
        npcs=[], chests=[dict(id="ow_potion", x=30, y=20, item="potion",
                              qty=1)],
        crystals=[], entities=[],
    ),
    "cavern": dict(
        name="Cavern of Cogs", fill="C", music="cavern", encounters=None,
        exits=[
            dict(x=14, y=24, to="overworld", tx=24, ty=5, face="down"),
            dict(x=15, y=24, to="overworld", tx=24, ty=5, face="down"),
        ],
        signs={},
        npcs=[],
        chests=[
            dict(id="cav_blade", x=20, y=21, item="iron_blade", qty=1),
            dict(id="cav_coil", x=27, y=11, item="focus_coil", qty=1),
            dict(id="cav_guard", x=3, y=21, item="leather_guard", qty=1),
            dict(id="boss_chest", x=19, y=3, item="aether_shard", qty=1),
        ],
        crystals=[(12, 23), (12, 10)],
        entities=ENTITIES["cavern"],
    ),
    "east_road": dict(
        name="The Great East Road", fill="T", music="road",
        encounters=ENCOUNTERS["east_road"],
        exits=[
            dict(x=2, y=18, to="overworld", tx=32, ty=21, face="left"),
            dict(x=1, y=18, to="overworld", tx=32, ty=21, face="left"),
            dict(x=44, y=8, to="frostline", tx=15, ty=18, face="down"),
            dict(x=19, y=35, to="ember_port", tx=19, ty=1, face="down"),
            dict(x=20, y=35, to="ember_port", tx=19, ty=1, face="down"),
            dict(x=19, y=31, to="deep_mill", tx=14, ty=19, face="up"),
            dict(x=41, y=24, to="sky_bastion", tx=17, ty=23, face="up",
                 req="shard3"),
        ],
        signs={
            (26, 18): ["JUNCTION: north-east to FROSTLINE.",
                       "south to EMBERPORT."],
            (43, 25): ["* Aether Gate *",
                       "It drinks light from three shards of glass."],
        },
        npcs=[],
        chests=[dict(id="er_iron", x=41, y=7, item="iron_heart", qty=1)],
        crystals=[], entities=[],
    ),
    "ember_port": dict(
        name="Emberport", fill="T", music="port", encounters=None,
        exits=[
            dict(x=17, y=0, to="east_road", tx=19, ty=34, face="up"),
            dict(x=18, y=0, to="east_road", tx=19, ty=34, face="up"),
            dict(x=6, y=3, to="ember_arms", tx=7, ty=7, face="up"),
            dict(x=17, y=3, to="ember_inn", tx=7, ty=7, face="up"),
        ],
        signs={},
        npcs=[
            dict(id="captain", x=10, y=7, pal=CAPTAIN_PAL, face="down",
                 wander=0,
                 dialog=[
                     dict(req="shard2",
                          lines=["Captain Row: The Sea Lantern sails north "
                                 "for you. Frostline awaits.",
                                 "Captain Row: Pier's at your feet - hop on."]),
                     dict(req="q_lantern",
                          lines=["Captain Row: And Marla got her lantern back? "
                                 "Good. We sail soon."]),
                     dict(req="met_row",
                          lines=["Captain Row: The wreck swallows crews - "
                                 "Rusthook sits inside. Sink him for us.",
                                 "Captain Row: Reward's a purse and my "
                                 "undying... something."]),
                     dict(req=None,
                          lines=["Captain Row: Welcome to Emberport - "
                                 "last good port on the coast.",
                                 "Captain Row: Sea raiders - the Marrow "
                                 "crew - took the bay. Sunk our lights.",
                                 "Captain Row: Their nest is the UMBRA "
                                 "WRECK, a hulk in the fog. Our ship's "
                                 "yours if you're nuts enough."],
                          set=["met_row"])],
                 ),
            dict(id="marla", x=24, y=7, pal=VILLAGER2_PAL, face="down",
                 wander=0,
                 dialog=[
                     dict(req="q_lantern",
                          lines=["Marla: My lantern lights the bay again.",
                                 "Marla: Ships come home safe now. Thank "
                                 "you."]),
                     dict(req="item:lantern",
                          lines=["Marla: My HEART! Back where it belongs.",
                                 "*You receive 500 gil!*"],
                          give=dict(gold=500, exp=180, take="lantern"),
                          set=["q_lantern"]),
                     dict(req="shard2",
                          lines=["Marla: The raiders fled! The bay sails "
                                 "again."]),
                     dict(req=None,
                          lines=["Marla: Raiders stole my sea lantern. "
                                 "Without it, ships wreck on the bar.",
                                 "Marla: The captain won't sail - and I "
                                 "can't sleep in the dark."])],
                 ),
            dict(id="sailor", x=20, y=9, pal=SAILOR_PAL, face="down",
                 wander=1,
                 dialog=[dict(req=None,
                              lines=["Sailor: Rough waters out to the wreck.",
                                     "Sailor: Snapjaws chew barnacles. "
                                     "And ankles."])]),
            dict(id="portkid", x=27, y=4, pal=KID_PAL, face="down", wander=1,
                 dialog=[dict(req=None,
                              lines=["Dock kid: The GEARLORD's legs looked "
                                     "like church towers, Pa says."])]),
        ],
        chests=[dict(id="ep_hipot", x=28, y=11, item="hipotion", qty=1),
                dict(id="ep_potion", x=2, y=11, item="potion", qty=2)],
        crystals=[(3, 11)],
        entities=[],
    ),
    "ember_arms": dict(
        name="Anchor & Anvil", fill="W", music="port", encounters=None,
        exits=[dict(x=7, y=8, to="ember_port", tx=6, ty=4, face="down")],
        signs=[], chests=[], crystals=[], entities=[],
        npcs=[dict(id="arms_ember", x=6, y=2, pal=SHOPKEEP_PAL, face="down",
                   wander=0, shop=True, stock=SHOP_STOCKS["ember_arms"],
                   accent="apron",
                   dialog=[
                       dict(req="q_mill",
                            lines=["Osk: That Titan Chain suits you. Best "
                                   "work I've done."]),
                       dict(req="item:core_gear",
                            lines=["Osk: Is that... a Core Gear from the "
                                   "Deep Mill? Hand it here!",
                                   "*Osk hammers through the night...*",
                                   "Osk: The Titan Chain. Wear it well.",
                                   "*You receive the Titan Chain!*"],
                            give=dict(take="core_gear", item="titan_chain"),
                            set=["q_mill"]),
                       dict(req=None,
                            lines=["Osk: Sea salt rusts blades, so I "
                                   "carry the good stuff.",
                                   "Osk: Bring me a Core Gear from the Deep "
                                   "Mill and I'll forge you something "
                                   "special."])])],
    ),
    "ember_inn": dict(
        name="Sleeping Gull", fill="W", music="port", encounters=None,
        exits=[dict(x=7, y=8, to="ember_port", tx=17, ty=4, face="down")],
        signs=[], chests=[], crystals=[], entities=[],
        npcs=[dict(id="inn_ember", x=7, y=2, pal=SAILOR_PAL, face="down",
                   wander=0, inn=40,
                   dialog=[dict(req=None,
                                lines=["Innkeep: Warm bed, 40 gil. Sea "
                                       "stories included.",
                                       "Innkeep: Wait - the stories are a "
                                       "hazard. But the bed's fine."])])],
    ),
    "umbra_wreck": dict(
        name="Umbra Wreck", fill="C", music="wreck", encounters=None,
        exits=[dict(x=15, y=24, to="ember_port", tx=16, ty=18, face="down")],
        signs={},
        npcs=[],
        chests=[dict(id="w_lantern", x=25, y=2, item="lantern", qty=1),
                dict(id="w_gold", x=5, y=23, gold=250)],
        crystals=[(7, 22)],
        entities=ENTITIES["umbra_wreck"],
    ),
    "frostline": dict(
        name="Frostline", fill="T", music="snow", encounters=None,
        exits=[
            dict(x=15, y=19, to="east_road", tx=44, ty=9, face="up"),
            dict(x=16, y=19, to="east_road", tx=44, ty=9, face="up"),
            dict(x=22, y=19, to="glacial_vault", tx=14, ty=23, face="up"),
            dict(x=23, y=19, to="glacial_vault", tx=15, ty=23, face="up"),
            dict(x=6, y=3, to="frost_shop", tx=7, ty=7, face="up"),
            dict(x=18, y=3, to="frost_inn", tx=7, ty=7, face="up"),
        ],
        signs={(25, 18): ["SOUTH GATE: the Glacial Vault.",
                          "Warden's orders - travellers only."]},
        npcs=[
            dict(id="elder_frost", x=17, y=10, pal=SNOWFOLK_PAL, face="down",
                 wander=0,
                 dialog=[
                     dict(req="shard3",
                          lines=["Warden Lumi: The vault sleeps. The town "
                                 "sleeps easier. Good."]),
                     dict(req="met_lumi",
                          lines=["Warden Lumi: The vault's heart is a "
                                 "COLOSSUS. It guards a shard of glass.",
                                 "Warden Lumi: South lies our gate. The "
                                 "winds are thin up north - dress up."]),
                     dict(req=None,
                          lines=["Warden Lumi: Welcome to Frostline. I keep "
                                 "the VAULT south of here.",
                                 "Warden Lumi: It's not a vault of gold - "
                                 "it's a vault of WINTER. Beating it frees "
                                 "the pass."],
                          set=["met_lumi"])],
                 ),
            dict(id="snowkid", x=10, y=15, pal=KID_PAL, face="down", wander=1,
                 dialog=[dict(req=None,
                              lines=["Snow kid: Frost apes do NOT like "
                                     "fire. Or being called fluffy."])]),
        ],
        chests=[dict(id="fl_hipot", x=24, y=15, item="hipotion", qty=2)],
        crystals=[(23, 13)],
        entities=[],
    ),
    "frost_shop": dict(
        name="Glacier Goods", fill="W", music="snow", encounters=None,
        exits=[dict(x=7, y=8, to="frostline", tx=6, ty=4, face="down")],
        signs=[], chests=[], crystals=[], entities=[],
        npcs=[dict(id="arms_frost", x=6, y=2, pal=SNOWFOLK_PAL, face="down",
                   wander=0, shop=True, stock=SHOP_STOCKS["frost_shop"],
                   dialog=[dict(req=None,
                                lines=["Trader: Northern stock - warm "
                                       "science and colder wit."])])],
    ),
    "frost_inn": dict(
        name="Fireside Vault", fill="W", music="snow", encounters=None,
        exits=[dict(x=7, y=8, to="frostline", tx=18, ty=5, face="down")],
        signs=[], chests=[], crystals=[], entities=[],
        npcs=[dict(id="inn_frost", x=7, y=2, pal=SNOWFOLK_PAL, face="down",
                   wander=0, inn=60,
                   dialog=[dict(req=None,
                                lines=["Innkeep: 60 gil melts the frost "
                                       "right off your joints."])])],
    ),
    "glacial_vault": dict(
        name="Glacial Vault", fill="C", music="vault", encounters=None,
        exits=[dict(x=14, y=24, to="frostline", tx=22, ty=18, face="up"),
               dict(x=15, y=24, to="frostline", tx=23, ty=18, face="up")],
        signs={},
        npcs=[],
        chests=[dict(id="gv_chain", x=25, y=20, item="focus_coil", qty=1),
                dict(id="gv_hipot", x=4, y=20, item="hipotion", qty=2)],
        crystals=[(21, 22), (6, 22)],
        entities=ENTITIES["glacial_vault"],
    ),
    "sky_bastion": dict(
        name="Sky Bastion", fill="C", music="sky", encounters=None,
        exits=[dict(x=17, y=25, to="east_road", tx=41, ty=25, face="down"),
               dict(x=18, y=25, to="east_road", tx=41, ty=25, face="down")],
        signs={},
        npcs=[
            dict(id="core", x=8, y=7, pal=HERMIT_PAL, face="down", wander=0,
                 require="shard4",
                 dialog=[
                     dict(req="omega_slain",
                          lines=["The Core: Even silence obeys you now.",
                                 "*The Core gifts you 3000 gil!*",
                                 "THE END - thank you for playing!"]),
                     dict(req="shard4",
                          lines=["The Core: I am the AETHER CORE.",
                                 "The Core: My WARDEN - Omega Cog - tests "
                                 "those who end stories early.",
                                 "The Core: Wake it, if you dare. It is "
                                 "beyond the throne, west side.",
                                 "*Omega Cog may now be challenged!*" if False
                                 else ""]),
                 ])],
        chests=[dict(id="sb_cleaver", x=25, y=11, item="storm_cleaver", qty=1),
                dict(id="sb_rod", x=8, y=11, item="astral_rod", qty=1),
                dict(id="sb_rep", x=26, y=21, item="sky_repeater", qty=1),
                dict(id="sb_charm", x=7, y=21, item="aurora_charm", qty=1)],
        crystals=[(29, 22), (4, 22), (17, 17)],
        entities=ENTITIES["sky_bastion"],
    ),
    "deep_mill": dict(
        name="The Deep Mill", fill="C", music="vault", encounters=None,
        exits=[dict(x=14, y=20, to="east_road", tx=19, ty=32, face="down")],
        signs={},
        npcs=[],
        chests=[],
        crystals=[(3, 19)],
        entities=ENTITIES["deep_mill"],
    ),
}
# ---- smoke anchors (chimneys) ----
# ---- Cavern of Cogs (30 x 25) ----
CAVERN = [
    "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
    "C________" + "C" * 14 + "________C",
    "C_______C____________C_______C",
    "C_______C____________C_______C",
    "C_______C____________C_______C",
    "C_______C____________C_______C",
    "C_______C____________C_______C",
    "C_______C____________C_______C",
    "C_______C____________C_______C",
    "C_______CCCCCCOOCCCCCC_______C",
    "C____________________________C",
    "C______________________CCCC__C",
    "C______________________CCCC__C",
    "C______________________CCCC__C",
    "C____________________________C",
    "C__CCCC______________________C",
    "C__CCCC______________________C",
    "C____________________________C",
    "C______________________CCCC_C",
    "CC______________________CCCC_C",
    "CC___________________________C",
    "C____________________________C",
    "C____________________________C",
    "C____________________________C",
    "CCCCCCCCCCCCCCOOCCCCCCCCCCCCCC",
]

TOWN_START = (17, 9)

# interior clones (rows) for the new shops/inns
EMBER_ARMS = [r for r in SHOP]
EMBER_INN = [
    "WWWWWWWWWWWWWWW",
    "WdddddddddddddW",
    "WiiiiiiiiiiiiiW",
    "WiiiicccciiiiiW",
    "WiiiiiiiiiiiiiW",
    "WiiiiiiiiiiiiiW",
    "WiiiiiiiiiiiiiW",
    "WiiiiiiiiiiiiiW",
    "WWWWWWWDWWWWWWW",
]
FROST_SHOP = [r for r in SHOP]
FROST_INN = [
    "WWWWWWWWWWWWWWW",
    "WdddddddddddddW",
    "WiiiiiiiiiiiiiW",
    "WiiiicccciiiiiW",
    "WiiiiiiiiiiiiiW",
    "WiiiiiiiiiiiiiW",
    "WiiiiiiiiiiiiiW",
    "WiiiiiiiiiiiiiW",
    "WWWWWWWDWWWWWWW",
]

SMOKE = {"town": [(6, 2), (17, 2), (27, 2)],
         "ember_port": [(6, 2), (17, 2)],
         "frostline": [(7, 2), (17, 2)]}

# ---- decorations placed programmatically ----
DECOR = [
    ("town", 13, 9, "L"), ("town", 16, 9, "L"),
    ("town", 10, 15, "o"),
    ("town", 13, 5, "K"),
    ("town", 8, 12, "H"),
    ("overworld", 6, 19, "H"), ("overworld", 7, 19, "H"),
    ("overworld", 13, 20, "L"),
    ("cavern", 1, 10, "t"), ("cavern", 28, 10, "t"),
    ("cavern", 1, 17, "t"), ("cavern", 28, 17, "t"),
    ("cavern", 2, 23, "t"), ("cavern", 27, 23, "t"),
    ("cavern", 8, 17, "V"), ("cavern", 20, 12, "V"), ("cavern", 24, 14, "V"),
    ("cavern", 16, 20, "U"), ("cavern", 5, 23, "U"),
    ("cavern", 3, 14, "g"), ("cavern", 27, 22, "g"),
    ("elder_home", 2, 1, "e"), ("elder_home", 3, 1, "e"),
    ("elder_home", 12, 5, "d"), ("elder_home", 12, 6, "d"),
    ("elder_home", 10, 4, "n"), ("elder_home", 11, 4, "n"),
    ("elder_home", 10, 5, "n"), ("elder_home", 11, 5, "n"),
    ("shop", 2, 1, "e"), ("shop", 3, 1, "e"), ("shop", 4, 1, "e"),
    ("shop", 9, 6, "n"), ("shop", 10, 6, "n"),
    ("shop", 9, 7, "n"), ("shop", 10, 7, "n"),
    ("east_road", 4, 2, "V"), ("east_road", 42, 14, "V"),
    ("east_road", 7, 31, "V"), ("east_road", 33, 30, "V"),
    ("east_road", 26, 18, "s"), ("east_road", 8, 10, "s"),
    ("east_road", 42, 26, "s"),
    ("umbra_wreck", 7, 23, "U"), ("umbra_wreck", 22, 10, "g"),
    ("glacial_vault", 9, 19, "V"), ("glacial_vault", 20, 17, "V"),
    ("sky_bastion", 5, 10, "g"), ("sky_bastion", 27, 10, "g"),
]


def apply_decor():
    for (mid, x, y, ch) in DECOR:
        rs = {"town": TOWN, "overworld": OVERWORLD, "cavern": CAVERN,
              "elder_home": ELDER_HOME, "shop": SHOP,
              "ember_port": EMBER_PORT, "frostline": FROSTLINE,
              "east_road": EAST_ROAD, "umbra_wreck": UMBRA_WRECK,
              "glacial_vault": GLACIAL_VAULT, "sky_bastion": SKY_BASTION,
              "deep_mill": DEEP_MILL,
              "ember_arms": EMBER_ARMS, "ember_inn": EMBER_INN,
              "frost_shop": FROST_SHOP, "frost_inn": FROST_INN}[mid]
        if not (0 <= y < len(rs) and 0 <= x < len(rs[0])):
            raise ValueError(f"decor OOB: {mid} {x},{y} '{ch}'")
        cur = rs[y][x]
        if cur not in ".fi_ w":
            raise ValueError(f"decor {mid} {x},{y} '{ch}' lands on '{cur}'")
        rs[y] = rs[y][:x] + ch + rs[y][x + 1:]


apply_decor()

INTRO = [
    ("Long ago, the mountain below Cinderhollow town hummed with strange "
     "machines that ground out wonders, and wonders that ground out machines..."),
    ("Then one night the humming stopped. The Cavern of Cogs woke up - and "
     "things that slime and screech and scrape now prowl the roads."),
    ("Three youngsters - KAI, NARA and VELA - set out to calm the restless "
     "gears. Their story begins on the town square..."),
]


# ---- normalize row widths (pad borders with solid fill) ----
def _normalize_maps():
    for mid, m in MAPS.items():
        rs = globals().get(mid.upper())
        if rs is None:
            continue
        width = max(len(r) for r in rs)
        fill = m.get("fill", "T")
        for i in range(len(rs)):
            if len(rs[i]) < width:
                rs[i] = rs[i] + fill * (width - len(rs[i]))


_normalize_maps()


# ---- grow scenery into the original outdoor maps (see mapgen.py) ----
def _decorate_maps():
    import mapgen
    solid = set("T~WRsxcbCYLoKHedVUgtShjl")
    plan = {"overworld": ("grass", 1.0, True), "east_road": ("mixed", 1.0, True),
            "town": ("grass", 0.35, False), "frostline": ("snow", 0.4, False),
            "ember_port": ("grass", 0.5, False)}
    for c in chapters.CH:
        plan[c["key"] + "_field"] = (c["biome"], 1.2, True)
        plan[c["key"] + "_town"] = (c["biome"], 0.25, False)
    for mid, (biome, dens, patches) in plan.items():
        rows = globals()[mid.upper()]
        new = mapgen.decorate(mid, rows, MAPS[mid], seed=sum(map(ord, mid)), biome=biome,
                              all_maps=MAPS, solid=solid, density=dens,
                              grass_patches=patches)
        rows[:] = new


import chapters  # noqa: E402  (Act II content, built from mapgen)
chapters.install(globals())
import story  # noqa: E402
story.apply(globals())
_decorate_maps()
