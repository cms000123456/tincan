"""Hand-written story for Tin Can Chronicles.

SCENES: one-shot cutscenes that play when you are on a map and their
condition holds (first visit, after a boss...). Each is
    dict(id=flag_set_when_seen, req=None|str|list, card=(n, title)?, lines=[])
`card` shows a chapter title card before the lines.

apply(D) also rewrites the Act II town leaders and adds townsfolk with
their own lines, so every region has a voice of its own.

The thread through Act II: the Clockmaker is ORLO VENN, Elder Bram's
apprentice who built the singing machines under Cinderhollow and vanished
thirty years ago when his daughter Lira fell ill. Every Star Gear holds a
memory of his; the party sees one after each boss.
"""

# ---------------------------------------------------------------------------
# Chapter cards (Act I chapters too)
# ---------------------------------------------------------------------------
CARDS = {
    1: "The Restless Gears", 2: "Emberport's Debt", 3: "The Thaw",
    4: "Storm the Bastion", 5: "The Ticking Sands", 6: "Iron Roots",
    7: "The Furnace Wakes", 8: "Mirror, Mirror", 9: "City of Clockwork",
    10: "The Astral Orrery",
}
ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII",
         8: "VIII", 9: "IX", 10: "X"}


def card(n):
    return (ROMAN[n], CARDS[n])


SCENES = {
    # ---------------------------------------------------------------- Act I
    "town": [dict(id="sc_card1", card=card(1), lines=[])],
    "east_road": [
        dict(id="sc_card2", req="shard1", card=card(2), lines=[
            "Vela: The beacon in the Gearlord's chest pointed EAST. "
            "Toward the coast.",
            "Nara: Emberport, then. Sailors hear every rumour first.",
            "Kai: And they sell fish on sticks. I'm in."]),
    ],
    "frostline": [
        dict(id="sc_card3", req="shard2", card=card(3), lines=[
            "Kai: B-b-brr. Who builds a town INSIDE a snowball?",
            "Nara: People who don't want visitors. Mind your manners."]),
    ],
    "sky_bastion": [
        dict(id="sc_card4", req="shard3", card=card(4), lines=[
            "*Wind howls between floating stones. Far above, something "
            "vast is thinking.*",
            "Vela: Every machine we've broken was built by the same "
            "hand. Same rivets. Same humour.",
            "Nara: Then let's go and ask that hand what it wants."]),
    ],
    "ember_port": [
        dict(id="sc_act2", req="shard4", lines=[
            "*The harbour lamps gutter. Every clock in Emberport stops "
            "at once.*",
            "???: Splendid. Truly splendid work, children.",
            "*A tall figure of light flickers over the water - a long "
            "coat, a mask shaped like a clock face.*",
            "THE CLOCKMAKER: You cleared Archon Prime out of my way. I "
            "could never have reached the southern Star Gears with that "
            "old tyrant watching.",
            "Kai: Who are you?!",
            "THE CLOCKMAKER: A tinkerer. A father. Soon, the last thing "
            "that ever happens.",
            "THE CLOCKMAKER: Five Star Gears turn my Orrery. When it "
            "chimes, time stops - and no one ever has to lose anything "
            "again.",
            "*The light folds into itself and is gone.*",
            "Vela: ...Okay. I hate him. Captain Row has a ship.",
            "Nara: The south. We go south.",
            "*New: the Sea Lantern can sail SOUTH to the Rust Coast.*"]),
    ],

    # ---------------------------------------------------- Ch 5 Rust Dunes
    "dunes_field": [
        dict(id="sc_card5", card=card(5), lines=[
            "*Red sand to the horizon. Somewhere under it, something "
            "ticks.*",
            "Vela: Hear that? Tick... tick... It's coming from BELOW us.",
            "Kai: Sand that ticks. Sure. Why not.",
            "Nara: There's a town on the ridge - Duneholm. North of "
            "here. They'll know."]),
    ],
    "dunes_town": [
        dict(id="sc_dunes_town", lines=[
            "*Wind chimes made from old cogs clatter over the gate.*",
            "Nara: Every door has a gear nailed above it. For luck, "
            "I think.",
            "Vela: Or as a warning. Let's find whoever's in charge."]),
    ],
    "dunes_d1": [
        dict(id="sc_dunes_d1", lines=[
            "*Sand pours through cracked windows. The tower is still "
            "ticking, deep below.*",
            "Vela: A whole clock tower, swallowed. Look at these gears "
            "- they're still WINDING.",
            "Kai: Down it is."]),
    ],
    "dunes_d4": [
        dict(id="sc_gear1", req="gear1", lines=[
            "*The Star Gear rises from the wyrm's coils, warm as a "
            "hearth.*",
            "*When Nara touches it, the room fades - and a memory plays.*",
            "*A cluttered workshop. A young man with soot on his nose. "
            "A little girl on a stool, swinging her feet.*",
            "GIRL: Papa, if you build a big enough clock, can you make "
            "tomorrow wait?",
            "YOUNG MAN: Ha! Lira, if I could build that, I'd never let "
            "you grow up.",
            "*The memory crackles out.*",
            "Nara: That workshop... the window looked out on a "
            "mountain. OUR mountain.",
            "Vela: And the maker's mark on this gear - a little star "
            "in a cog. It's on half the machines under Cinderhollow.",
            "Kai: So the Clockmaker's from home? That's... worse."]),
    ],

    # ---------------------------------------------------- Ch 6 Thornwood
    "thorn_field": [
        dict(id="sc_card6", card=card(6), lines=[
            "*Ancient trees crowd the path. Their bark creaks like "
            "metal.*",
            "Nara: Listen. The forest is... breathing in rhythm.",
            "Vela: Pistons. The roots are pumping. Somebody plumbed a "
            "forest.",
            "Kai: Mossfall's up north. Let's go before the trees decide "
            "we're fertiliser."]),
    ],
    "thorn_town": [
        dict(id="sc_thorn_town", lines=[
            "*Houses sit high in the branches. Rope bridges sway "
            "overhead.*",
            "Kai: Treehouses! Real ones!",
            "Nara: Kai. Focus. The leaves here are turning grey."]),
    ],
    "thorn_d1": [
        dict(id="sc_thorn_d1", lines=[
            "*The roots here are iron, and they are warm.*",
            "Nara: The great tree is being turned into a machine from "
            "the inside out.",
            "Vela: And it's being done with love. Look at the welds. "
            "Whoever did this was careful.",
            "Kai: Careful doesn't make it okay."]),
    ],
    "thorn_d4": [
        dict(id="sc_gear2", req="gear2", lines=[
            "*Brambleheart's crimson light dims. Inside it, the second "
            "Star Gear.*",
            "*Another memory: a sickroom. The girl, Lira, older now and "
            "very pale.*",
            "YOUNG MAN: The Mossfall elders say the great tree's sap "
            "heals anything. I'll bring some back. I promise.",
            "LIRA: Don't run, Papa. You always trip.",
            "*Rain on a window. A door closing.*",
            "Nara: The sap didn't save her. That's why he turned the "
            "tree into gears - he was punishing it.",
            "Vela: Or still trying to make it work.",
            "Kai: Either way, the tree's free now. One more reason to "
            "stop him."]),
    ],

    # ---------------------------------------------------- Ch 7 Ashen Slopes
    "ash_field": [
        dict(id="sc_card7", card=card(7), lines=[
            "*Ash falls like grey snow. The mountain's breath is "
            "thunder.*",
            "Kai: Hot. Hot hot hot.",
            "Vela: Smell that? Coal smoke and machine oil. Forgeholm's "
            "furnaces are running full blast.",
            "Nara: The dwarves would never waste fuel like that. "
            "Something's wrong."]),
    ],
    "ash_town": [
        dict(id="sc_ash_town", lines=[
            "*Every chimney is cold. The dwarves sit outside their "
            "homes, staring at the foundry glow.*",
            "Vela: The town's furnaces are out... but the foundry's "
            "burning hotter than ever.",
            "Kai: Somebody stole their fire."]),
    ],
    "ash_d1": [
        dict(id="sc_ash_d1", lines=[
            "*Rivers of molten iron. Hammers fall with no hands to lift "
            "them.*",
            "Vela: It's building parts. Thousands. Rings and spokes, "
            "huge ones... for something in the sky.",
            "Nara: The Orrery. He's forging it here."]),
    ],
    "ash_d4": [
        dict(id="sc_gear3", req="gear3", lines=[
            "*The Forge Titan kneels and cools. The third Star Gear "
            "glows in its chest.*",
            "*Memory: a funeral bell. The young man, older now, beard "
            "gone grey, standing before the dwarves of Forgeholm.*",
            "GREY MAN: Help me build it. A clock to stop the stars. "
            "No one else would ever have to bury a child.",
            "FORGEMASTER: Orlo, no forge can mend that. Go home.",
            "*He doesn't go home.*",
            "Vela: Orlo. He has a name.",
            "Nara: Orlo... Elder Bram used to talk about an apprentice "
            "called Orlo. The one who built the singing machines.",
            "Kai: The ones that went crazy and started this whole mess. "
            "He's been gone thirty years."]),
    ],

    # ---------------------------------------------------- Ch 8 Mirror Marsh
    "marsh_field": [
        dict(id="sc_card8", card=card(8), lines=[
            "*Still black water reflects a sky that isn't there - "
            "brass rings turning among the stars.*",
            "Nara: Look at the reflection. That's the Orrery. The marsh "
            "can see it.",
            "Vela: So the observatory's lens is pointed right at it. "
            "Murkwater first - I want a boat that doesn't leak.",
            "Kai: And dry socks."]),
    ],
    "marsh_town": [
        dict(id="sc_marsh_town", lines=[
            "*Stilt houses creak over the water. Lanterns hang from "
            "every post, though it's midday.*",
            "Nara: They keep the lanterns lit so they can't see the "
            "sky in the water.",
            "Kai: Can't blame them."]),
    ],
    "marsh_d1": [
        dict(id="sc_marsh_d1", lines=[
            "*Water drips from a dome of shattered crystal. Star charts "
            "float in the flood.*",
            "Vela: These charts are in his handwriting. Same as the "
            "notes we found in the tower.",
            "Nara: He came here every night. For years."]),
    ],
    "marsh_d4": [
        dict(id="sc_gear4", req="gear4", lines=[
            "*The Hydra Engine's three heads sink beneath the water. "
            "The fourth Star Gear drifts up into Kai's hands.*",
            "*Memory: the observatory, whole and shining. Orlo at the "
            "great lens, laughing for the first time in years.*",
            "ORLO: There! The Astral Orrery - the star-clock that "
            "turns the heavens! If I can reach it, I can stop it... "
            "stop EVERYTHING, before the next goodbye.",
            "*Behind him, a letter on the desk, unopened. In a child's "
            "hand: 'Papa - come home soon. Love, L.'*",
            "Nara: ...He never read it.",
            "Kai: He's not stopping time to save her. She's already "
            "gone. He's stopping it so nobody else gets to move on.",
            "Vela: One gear left. Gearhaven."]),
    ],

    # ---------------------------------------------------- Ch 9 Gearhaven
    "gear_field": [
        dict(id="sc_card9", card=card(9), lines=[
            "*Smokestacks, bridges and a city wall of riveted brass. "
            "Clock guards march along the battlements.*",
            "Vela: Gearhaven. Biggest workshop city in the world. I "
            "used to dream about this place.",
            "Kai: Do the guards usually point their spears at "
            "visitors?",
            "Vela: ...Not in the dream."]),
    ],
    "gear_town": [
        dict(id="sc_gear_town", lines=[
            "*Shutters closed. Streets empty. Somewhere, a parade drum "
            "beats for no one.*",
            "Nara: The whole city's hiding from its own guard.",
            "Vela: The Mayor's house should be near the square."]),
    ],
    "gear_d1": [
        dict(id="sc_gear_d1", lines=[
            "*Old pipes, older tunnels. Painted on the wall: a star in "
            "a cog, and the words 'FOR LIRA'.*",
            "Kai: He built this place too?",
            "Vela: The Undercity was his first workshop. Spindle was "
            "his first automaton - built to guard his daughter."]),
    ],
    "gear_d4": [
        dict(id="sc_gear5", req="gear5", lines=[
            "*General Spindle's sword falls. The last Star Gear rolls "
            "free.*",
            "GENERAL SPINDLE: Orders... protect the girl... protect... "
            "where... is... the girl...",
            "*Its eyes go dark.*",
            "*Above the city, the sky splits open. Brass rings the "
            "size of mountains turn among the clouds.*",
            "THE CLOCKMAKER: All five. Thank you, children. You've "
            "carried every gear to the foot of my door.",
            "THE CLOCKMAKER: Come up, if you like. Watch the last "
            "second there will ever be.",
            "Kai: We're coming, Orlo.",
            "*...For a moment the light flickers, as if the name "
            "hurt.*",
            "Nara: The way east of the city should be open now. The "
            "Orrery is waiting."]),
    ],

    # ---------------------------------------------------- Ch 10 Orrery
    "orrery_1": [
        dict(id="sc_card10", card=card(10), lines=[
            "*Stars beneath your feet. Gears the size of towns grind "
            "past in total silence.*",
            "Nara: We're standing inside the sky.",
            "Vela: Six floors, if the tower in the dunes was a model. "
            "And something big guarding the middle.",
            "Kai: Then let's climb. Together."]),
    ],
    "orrery_4": [
        dict(id="sc_orrery4", lines=[
            "THE CLOCKMAKER: You beat my guardian. Lira would have "
            "liked you, I think. She liked stubborn people.",
            "Nara: Then stop this. For her.",
            "THE CLOCKMAKER: Everything I have done is for her."]),
    ],
    "orrery_6": [
        dict(id="sc_orrery6", lines=[
            "*At the top of the Orrery, a small workshop floats among "
            "the stars - the same one from the memories.*",
            "*A stool. A pair of tiny shoes. An unopened letter, "
            "yellow with age.*",
            "Vela: He rebuilt it. Up here, where time can't touch it.",
            "Kai: Orlo! We found your letter. In the observatory. "
            "You never read it.",
            "THE CLOCKMAKER: ...Letters end. Everything ends. That is "
            "the whole problem with time.",
            "Nara: Then we'll read it to you. After."]),
    ],
}


# ---------------------------------------------------------------------------
# Act II town leaders - replace the template lines
# ---------------------------------------------------------------------------
LEADERS = {
    "dunes": dict(
        intro=["Chief Ysra: You came off the Rust Coast road? Then the "
               "sand has let you live. Sit.",
               "Chief Ysra: A month ago the old clock tower sank into "
               "the dunes in a single night. Now it ticks under our "
               "feet when the moon is up.",
               "Chief Ysra: Our goats won't graze. Our children dream "
               "of numbers. And things crawl out of the sand to the "
               "south-east.",
               "Chief Ysra: Find what is ticking down there. Stop it, "
               "and Duneholm will sing your names.",
               "*Chief Ysra presses a pouch of gil into your hands.*"],
        met=["Chief Ysra: The Buried Clocktower lies south-east, past "
             "the red dunes. Look for a mouth of black rock.",
             "Chief Ysra: Rest at the inn. The sand is patient - so must "
             "you be."],
        done=["Chief Ysra: Listen. No ticking. Only wind.",
              "Chief Ysra: The road east of the dunes is open. The "
              "forest folk of Mossfall may need you more than we do."]),
    "thorn": dict(
        intro=["Elder Willowmere: Shh. Do you hear the great tree? It "
               "used to sing. Now it... clanks.",
               "Elder Willowmere: Its roots turned to iron from the "
               "bottom up. The leaves are next, then us.",
               "Elder Willowmere: There is a hollow under the roots, "
               "south-east of here. A red light beats inside it like a "
               "heart.",
               "Elder Willowmere: Take this, with Mossfall's thanks in "
               "advance."],
        met=["Elder Willowmere: The Root Hollow is south-east, beyond "
             "the thorn thickets.",
             "Elder Willowmere: Be gentle with the tree. It didn't "
             "choose this."],
        done=["Elder Willowmere: Look up! Green shoots on every branch.",
              "Elder Willowmere: The tree remembers you now. Walk east "
              "in peace - the Ashen Slopes are beyond."]),
    "ash": dict(
        intro=["Forgemaster Bruna: Strangers. Good. Strangers can't be "
               "any more useless than we are.",
               "Forgemaster Bruna: Three weeks ago the Magma Foundry lit "
               "itself. Pulled every ember from our town like a drain.",
               "Forgemaster Bruna: Thirty years I've run that foundry. "
               "Now my own hammers chase me out of it.",
               "Forgemaster Bruna: It's south-east, up the slope. Bring "
               "our fire home. Here - for supplies."],
        met=["Forgemaster Bruna: Magma Foundry. South-east, up the "
             "slope. Can't miss the glow.",
             "Forgemaster Bruna: Mind the slag. And don't touch any "
             "anvil that hums."],
        done=["Forgemaster Bruna: Smell that? Our own coal, in our own "
              "furnaces. Ha!",
              "Forgemaster Bruna: I knew that man, you know. Orlo. Sent "
              "him away years ago. Maybe I should have listened longer.",
              "Forgemaster Bruna: Mirror Marsh is east. Bring an extra "
              "pair of boots."]),
    "marsh": dict(
        intro=["Ferrywoman Ilse: Don't look in the water. Not at night. "
               "You'll see the sky-clock looking back.",
               "Ferrywoman Ilse: The observatory sank into the marsh, "
               "but its lens still turns. Every night it tracks those "
               "brass rings across the stars.",
               "Ferrywoman Ilse: People who go in there come back "
               "talking in numbers. Or don't come back.",
               "Ferrywoman Ilse: It's south-east, past the reeds. Here - "
               "the ferry fund can spare this."],
        met=["Ferrywoman Ilse: The Drowned Observatory, south-east. "
             "Follow the dead lanterns.",
             "Ferrywoman Ilse: Keep your eyes on your feet, not the "
             "water."],
        done=["Ferrywoman Ilse: The water's just water again. I saw my "
              "own face in it this morning. Forgot I had one.",
              "Ferrywoman Ilse: Gearhaven is east. Whatever's left of "
              "this, it ends there."]),
    "gear": dict(
        intro=["Mayor Cogsworth: Quickly, inside - before a patrol sees "
               "you!",
               "Mayor Cogsworth: Our clock guard was built to protect "
               "this city. Now it marches day and night and arrests "
               "anyone who speaks of time.",
               "Mayor Cogsworth: Their commander, General Spindle, went "
               "down into the Undercity a month ago. The guard has "
               "obeyed only it ever since.",
               "Mayor Cogsworth: The Undercity entrance is south-east of "
               "the walls. Please. Take the city's purse. All of it."],
        met=["Mayor Cogsworth: The Undercity. South-east of the walls. "
             "Spindle waits at the bottom.",
             "Mayor Cogsworth: They say Spindle was the first automaton "
             "ever made in Gearhaven. Older than the city charter."],
        done=["Mayor Cogsworth: The guard stopped mid-step - then went "
              "home and took their boots off. I've never seen anything "
              "so strange or so wonderful.",
              "Mayor Cogsworth: The gate east of the outskirts leads up "
              "to... that. In the sky. Good luck, heroes."]),
}

# two townsfolk per region: (name, before-gear lines, after-gear lines)
FOLK = {
    "dunes": [
        ("Goatherd Pell",
         ["Goatherd Pell: My goats stand in a circle at midnight, "
          "facing the dunes. All of them. Every night.",
          "Goatherd Pell: Goats shouldn't know how to tell time."],
         ["Goatherd Pell: My goats are back to eating my hat. "
          "Wonderful, normal goats."]),
        ("Sand-reader Oma",
         ["Sand-reader Oma: The sand speaks of a man with a clock "
          "for a face. Grieving. Still grieving.",
          "Sand-reader Oma: Grief that won't end turns into "
          "machinery, child. Remember that."],
         ["Sand-reader Oma: The sand says you carry his first memory "
          "now. Be kind with it."]),
    ],
    "thorn": [
        ("Ranger Fen",
         ["Ranger Fen: I've patrolled Thornwood twenty years. Last "
          "week a squirrel bit me and it had GEARS in its teeth.",
          "Ranger Fen: Gears. In a squirrel."],
         ["Ranger Fen: The squirrels are just squirrels again. Still "
          "bitey, though."]),
        ("Mossling Pip",
         ["Mossling Pip: Are you the heroes? My mum says heroes eat "
          "their vegetables. Do you?",
          "Kai: ...Mostly."],
         ["Mossling Pip: The tree sang to me this morning! It said "
          "thank you. I think it meant you."]),
    ],
    "ash": [
        ("Smith Dagny",
         ["Smith Dagny: My granddad built half those hammers in the "
          "foundry. Now they're beating his name into slag.",
          "Smith Dagny: Bring them back to us, and I'll forge you "
          "something fine one day."],
         ["Smith Dagny: First fire in three weeks! I cried into my "
          "beard. Don't tell anyone."]),
        ("Old Brakk",
         ["Old Brakk: I remember a skinny human, years back. Begged "
          "the Forgemaster for help with some star-clock.",
          "Old Brakk: She said no. He said, 'Then I'll build it "
          "alone.' Never forgot his face."],
         ["Old Brakk: So it was him all along. Poor, stubborn fool."]),
    ],
    "marsh": [
        ("Lantern-keeper Wim",
         ["Lantern-keeper Wim: One hundred and twelve lanterns. I "
          "light them all, every hour, so the water can't show the "
          "sky.",
          "Lantern-keeper Wim: I am very, very tired."],
         ["Lantern-keeper Wim: I slept. A whole night! The lanterns "
          "can rest too."]),
        ("Fisher Nell",
         ["Fisher Nell: I caught a fish yesterday that ticked. I put "
          "it back. You would too."],
         ["Fisher Nell: Normal fish today. Slimy, silent, perfect."]),
    ],
    "gear": [
        ("Clerk Tibbet",
         ["Clerk Tibbet: Whisper, please. The guard arrests anyone "
          "who mentions the hour.",
          "Clerk Tibbet: Yesterday I said 'half past' and had to hide "
          "in a barrel until sundown."],
         ["Clerk Tibbet: It is TWELVE O'CLOCK! There, I said it! "
          "Oh, that felt good."]),
        ("Inventor Juno",
         ["Inventor Juno: You're Vela? THE Vela? Who built a "
          "railthrower out of a mangle? I've read all your patents!",
          "Vela: I... have patents?",
          "Inventor Juno: Well, I filed them for you. You're welcome."],
         ["Inventor Juno: The guild wants to name a wrench after you, "
          "Vela. It's a very nice wrench."]),
    ],
}


def _free_cells(rows, taken, y0, y1, ground):
    out = []
    for y in range(y0, y1):
        for x in range(2, len(rows[0]) - 2):
            if rows[y][x] not in ground:
                continue
            if any(abs(x - tx) + abs(y - ty) < 3 for tx, ty in taken):
                continue
            # keep the 3x3 around the cell open so no corridor gets plugged
            ring = [rows[y + dy][x + dx] for dx in (-1, 0, 1)
                    for dy in (-1, 0, 1)]
            if all(c in ground for c in ring):
                out.append((x, y))
    return out


def apply(D):
    MAPS = D["MAPS"]
    D["SCENES"] = SCENES
    for key, L in LEADERS.items():
        tid = f"{key}_town"
        if tid not in MAPS:
            continue
        gear = next(c["gear"] for c in __import__("chapters").CH
                    if c["key"] == key)
        for n in MAPS[tid]["npcs"]:
            if n["id"] == f"{key}_leader":
                old_intro = n["dialog"][-1]
                n["dialog"] = [
                    dict(req=gear, lines=L["done"]),
                    dict(req=f"met_{key}", lines=L["met"]),
                    dict(req=None, lines=L["intro"],
                         set=old_intro.get("set", []),
                         give=old_intro.get("give", {}))]
        # townsfolk
        rows = D[tid.upper()]
        taken = [(n["x"], n["y"]) for n in MAPS[tid]["npcs"]]
        taken += [(e["x"], e["y"]) for e in MAPS[tid]["exits"]]
        taken += [tuple(c) for c in MAPS[tid].get("crystals", [])]
        cells = _free_cells(rows, taken, 10, len(rows) - 2, ".amzy")
        pal = MAPS[tid]["npcs"][0]["pal"]
        for i, (name, before, after) in enumerate(FOLK.get(key, [])):
            if not cells:
                break
            x, y = cells[(len(cells) * (2 * i + 1)) // 4 % len(cells)]
            cells = [c for c in cells if abs(c[0] - x) + abs(c[1] - y) >= 3]
            MAPS[tid]["npcs"].append(dict(
                id=f"{key}_folk{i}", x=x, y=y, pal=pal, face="down",
                wander=1, dialog=[dict(req=gear, lines=after),
                                  dict(req=None, lines=before)]))
