"""Game orchestration: title, intro, world scene, overlays, battles."""

import os
import random
import sys

import pygame

import assets
import audio
import battle
import data
import dialogue
import menu as menu_mod
import save
import world as world_mod
from settings import (KEYMAP, PAL, TILE, SCALE, GAMEW, GAMEH, WINW, WINH,
                      FPS)

def _kcode(n):
    """key name -> pygame key code constant"""
    if n.isalpha() and len(n) == 1:
        return getattr(pygame, "K_" + n.lower())
    return getattr(pygame, "K_" + n.upper())


K = {a: [_kcode(n) for n in names] for a, names in KEYMAP.items()}


def held_actions(keys_state):
    out = set()
    for a, codes in K.items():
        for c in codes:
            if keys_state[c]:
                out.add(a)
                break
    return out


def pressed_actions(events):
    out = set()
    for e in events:
        if e.type == pygame.KEYDOWN:
            for a, codes in K.items():
                if e.key in codes:
                    out.add(a)
    return out


class HelpOverlay:
    """F1 manual. Pauses whatever is underneath, works on every scene."""

    def __init__(self, game):
        self.game = game
        self.done = False

    def update(self, dt, pressed):
        if pressed:
            self.done = True
            self.game.audio.sfx("cancel")

    def draw(self, surf):
        r = pygame.Rect(30, 24, WINW - 60, WINH - 48)
        assets.draw_panel(surf, r)
        assets.draw_text(surf, "HOW TO PLAY", WINW // 2, r.y + 14, 36,
                         PAL["amber"], bold=True, align="center")
        cols = [
            ("GETTING AROUND", [
                "Arrows / WASD . move",
                "Z . . confirm, talk, read",
                "X . . cancel",
                "C / Tab / Esc . pause menu",
                "M . . mute music",
                "F1 . . this help",
            ], PAL["text"]),
            ("IN TOWN", [
                "*Talk to everyone* - the Elder has work.",
                "The *Rusty Nail* sells gear and tonics.",
                "*Blue crystals* heal the party AND save.",
                "Pause menu: Items, Status, Quest, Save.",
            ], PAL["text"]),
            ("IN BATTLE", [
                "Bars fill with time - act when full!",
                "*Attack* hits one enemy, arrows pick it.",
                "*Tech* casts spells and burns MP.",
                "The GEARLORD resists fire - use lightning!",
                "*Item* heals an ally. *Run* escapes.",
            ], PAL["text"]),
            ("GOOD TO KNOW", [
                "Tall grass hides monsters. Walk it!",
                "Roaming monsters pounce when you get close.",
                "Chests stay opened. Level ups learn techs.",
                "Saves: crystals or the pause menu.",
            ], PAL["text_dim"]),
        ]
        colw = (r.w - 100) // 2
        for i, (title, lines, col) in enumerate(cols):
            crow = i // 2
            ccol = i % 2
            cx = r.x + 30 + ccol * (colw + 40)
            cy = r.y + 58 + crow * 196
            assets.draw_text(surf, title, cx, cy, 24, PAL["amber"],
                             bold=True)
            cy += 28
            for ln in lines:
                for sub in assets.wrap_text(ln, 21, colw):
                    assets.draw_text(surf, sub, cx, cy, 21, col)
                    cy += 21
        if self.game.frame % 56 < 30:
            assets.draw_text(surf, "- press Z or Esc to continue -", WINW
                             // 2, r.bottom - 30, 21, PAL["text_dim"],
                             align="center")


class Game:
    def __init__(self, headless=False):
        global pygame
        if headless:
            import os
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.init()
        flags = 0
        if not headless:
            pygame.display.set_caption("Tin Can Chronicles")
        self.screen = pygame.display.set_mode((WINW, WINH), flags)
        self.clock = pygame.time.Clock()
        self.frame = 0
        self.assets = assets.load_assets()
        if not headless:
            icon = pygame.transform.scale(
                self.assets["enemies"]["scrap"], (32, 32))
            pygame.display.set_icon(icon)
        self.party = None
        self.flags = {"opened_chests": {}, "slain": {}}
        self._build_sheets()
        self.audio = audio.get_audio()
        self.scene = TitleScene(self)
        self.world_scene = None
        self.battle_scene = None
        self.play_time = 0.0
        self.help_open = False
        self.help = None
        self.ships_cfg = data.SHIPS

    # -- asset prep -------------------------------------------------------------
    def _build_sheets(self):
        import party
        import sprites
        self.party = party.Party()
        for m in self.party.members:
            m.sheet = sprites.build_sheet(m.id) or assets.build_char_sheet(
                data.CHARS[m.id]["palette"],
                accent=data.CHARS[m.id].get("accent"))
            m.portrait = sprites.build_portrait(m.id) or \
                assets.make_portrait(m.sheet)
        self.char_sheets = {m.id: m.sheet for m in self.party.members}
        self.npc_defs = {}
        for mid, m in data.MAPS.items():
            for d in m["npcs"]:
                if d["id"] not in self.npc_defs:
                    self.npc_defs[d["id"]] = d["pal"]
        self.npc_sheets = {}
        for mid, m in data.MAPS.items():
            for n in m["npcs"]:
                if n["id"] in self.npc_sheets:
                    continue
                pal = n["pal"]
                self.npc_sheets["npc_" + n["id"]] = \
                    sprites.build_sheet(n["id"]) or assets.build_char_sheet(
                        pal, accent=n.get("accent"))
        self.sheets = dict(self.char_sheets, **self.npc_sheets)

    # -- world / battles --------------------------------------------------------
    def use_exit(self, world_or_scene, ex, x, y):
        """Route exit triggers from the world to the active WorldScene."""
        if self.world_scene is not None:
            self.world_scene.use_exit(ex, x, y)

    def start_world(self, map_id, x, y, face="down"):
        self.world_scene = WorldScene(self, map_id, x, y, face)
        self.scene = self.world_scene
        self.audio.play_music(self.world_scene.world.music)

    def start_battle_scene(self, group, entity=None, boss=False):
        bs = battle.BattleScene(self, group, entity=entity, boss_ok=boss)
        self.battle_scene = bs
        self.scene = bs

    def start_entity_battle(self, _src, monster):
        if self.scene is not self.world_scene:
            return
        if self.world_scene.state != "play":
            return
        ws = self.world_scene
        ws.state = "battle_fade"
        ws.battle_fade_t = 0.0
        ws.pending_battle = ("entity", monster)

    def start_random_battle(self, _src, enc):
        ws = self.world_scene
        if self.scene is not ws or ws.state != "play":
            return
        group = []
        sizes = enc["size"]
        total = sum(w for _, w in enc["table"])
        size_total = sum(w for _, w in sizes)
        r = random.uniform(0, size_total)
        acc = 0.0
        size = 1
        for s, w in sizes:
            acc += w
            if r <= acc:
                size = s
                break
        for _ in range(size):
            rr = random.uniform(0, total)
            acc2 = 0.0
            pick = enc["table"][0][0]
            for eid, w in enc["table"]:
                acc2 += w
                if rr <= acc2:
                    pick = eid
                    break
            group.append(pick)
        if not group:
            group = ["slime"]
        self.audio.sfx("encounter")
        self.world_scene.state = "battle_fade"
        self.world_scene.battle_fade_t = 0.0
        self.world_scene.pending_battle = ("random", group)

    def end_battle(self, scene):
        result = scene.result
        if result is None:
            return
        if result == "ran":
            self.battle_scene = None
            self.scene = self.world_scene
            if self.world_scene is not None:
                self.world_scene.state = "play"
                self.audio.play_music(self.world_scene.world.music)
            return
        if result == "gameover":
            self.battle_scene = None
            self.scene = TitleScene(self, game_over=True)
            self.world_scene = None
            self.audio.stop_music()
            return
        # victory
        ent = scene.entity
        if ent is not None and self.world_scene is not None:
            self.flags.setdefault("slain", {})
            self.flags["slain"][ent.id] = True
            if ent.boss:
                self.flags["boss_slain"] = True
            if getattr(ent, "on_defeat", None):
                self.flags[ent.on_defeat] = True     # story progression
                if ent.on_defeat == "game_clear":
                    self.battle_scene = None
                    self.scene = EndingScene(self)
                    self.audio.play_music("sky")
                    return
        self.battle_scene = None
        self.scene = self.world_scene
        if self.world_scene is not None:
            self.world_scene.state = "play"
            self.world_scene.world.refresh_monsters(self)
            self.audio.play_music(self.world_scene.world.music)

    # -- main loop ----------------------------------------------------------------
    def step(self, dt, pressed=frozenset(), held=frozenset()):
        """One simulated frame (also used by tests)."""
        self.frame += 1
        if "mute" in pressed:
            self.audio.toggle()
        self.play_time += dt
        if self.help_open and self.help is not None:
            self.scene.draw(self.screen)
            self.help.update(dt, set(pressed))
            self.help.draw(self.screen)
            if self.help.done:
                self.help_open = False
                self.help = None
            return
        if "help" in pressed:
            self.help_open = True
            self.help = HelpOverlay(self)
            self.audio.sfx("cursor")
            return
        self.scene.update(dt, set(pressed), set(held))
        self.scene.draw(self.screen)

    def run(self, frames=None):
        running = True
        while running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            events = pygame.event.get()
            for e in events:
                if e.type == pygame.QUIT:
                    running = False
            pressed = pressed_actions(events)
            keys = pygame.key.get_pressed()
            held = held_actions(keys)
            self.step(dt, pressed, held)
            pygame.display.flip()
            if frames is not None and self.frame >= frames:
                running = False
        if frames is None:
            pygame.quit()


# ---------------------------------------------------------------------------
class Scene:
    def __init__(self, game):
        self.game = game

    def update(self, dt, pressed, held):
        pass

    def draw(self, surf):
        pass


class TitleScene(Scene):
    def __init__(self, game, game_over=False):
        super().__init__(game)
        self.opt_idx = 0
        self.t = 0.0
        self.gameover = game_over
        game.audio.play_music("town")
        self.backdrop = TitleScene._backdrop()

    _bd_cache = []

    @staticmethod
    def _backdrop():
        """Scene art + a darkening scrim, built once and reused."""
        if not TitleScene._bd_cache:
            import sprites
            img = sprites.load_backdrop(WINW)
            if img is not None:
                # dim overall, more at top/bottom, so text stays readable
                scrim = pygame.Surface(img.get_size(), pygame.SRCALPHA)
                scrim.fill((8, 10, 30, 70))
                img.blit(scrim, (0, 0))
            TitleScene._bd_cache.append(img)
        return TitleScene._bd_cache[0]

    @staticmethod
    def _vignette():
        if not hasattr(TitleScene, "_vig"):
            v = pygame.Surface((WINW, WINH), pygame.SRCALPHA)
            for y in range(WINH):
                # 0 at the middle of the title, rising toward the menu/edges
                d = abs(y - 200) / (WINH - 200)
                a = int(40 + 140 * min(1.0, d) ** 1.5)
                # ease into a darker band behind the menu (no hard edge)
                k = min(1.0, max(0.0, (y - 250) / 90))
                a = max(a, int(125 * k * k * (3 - 2 * k)))
                v.fill((6, 8, 24, a), (0, y, WINW, 1))
            TitleScene._vig = v
        return TitleScene._vig

    _txt_cache = {}

    @staticmethod
    def _outlined(surf, txt, x, y, size, color, bold=False, w=3):
        """Centred text with a thick dark outline (cached; it's static)."""
        key = (txt, size, color, bold, w)
        img = TitleScene._txt_cache.get(key)
        if img is None:
            f = assets.get_font(size, bold)
            fg = f.render(txt, True, color)
            ol = f.render(txt, True, (12, 10, 28))
            img = pygame.Surface((fg.get_width() + 2 * w,
                                  fg.get_height() + 2 * w), pygame.SRCALPHA)
            for dx in range(-w, w + 1):
                for dy in range(-w, w + 1):
                    if dx * dx + dy * dy <= w * w and (dx or dy):
                        img.blit(ol, (w + dx, w + dy))
            img.blit(fg, (w, w))
            TitleScene._txt_cache[key] = img
        surf.blit(img, (x - img.get_width() // 2, y - w))

    def options(self):
        opts = ["New Game"]
        if save.has_save():
            opts.append("Continue")
        opts.append("How to Play")
        return opts

    def update(self, dt, pressed, held):
        self.t += dt
        opts = self.options()
        if "up" in pressed:
            self.opt_idx = (self.opt_idx - 1) % len(opts)
            self.game.audio.sfx("cursor")
        if "down" in pressed:
            self.opt_idx = (self.opt_idx + 1) % len(opts)
            self.game.audio.sfx("cursor")
        if "a" in pressed:
            self.game.audio.sfx("confirm")
            if opts[self.opt_idx] == "New Game":
                self.game.scene = IntroScene(self.game)
            elif opts[self.opt_idx] == "How to Play":
                g = self.game
                g.scene = HelpScene(self.game)
            else:
                sdat = save.load_game()
                if sdat:
                    g = self.game
                    g.flags = sdat.get("flags", {"opened_chests": {},
                                                 "slain": {}})
                    g.flags.setdefault("opened_chests", {})
                    g.flags.setdefault("slain", {})
                    for md, raw in zip(g.party.members, sdat["party"]):
                        md.level = raw["level"]
                        md.exp = int(raw["exp"])
                        md.weapon = raw["weapon"]
                        md.charm = raw.get("charm")
                        md.update_stats(final=False)
                        md.hp = int(raw["hp"])
                        md.mp = int(raw["mp"])
                        md.hp = max(1, md.hp) if not sdat else md.hp
                    g.party.gold = int(sdat["gold"])
                    g.party.inventory = dict(sdat["inventory"])
                    g.start_world(sdat["map"], sdat["pos"][0],
                                  sdat["pos"][1],
                                  sdat.get("face", "down"))

    def draw(self, surf):
        # backdrop
        import math
        if self.backdrop is not None:
            # slow vertical pan across the (taller than the window) scene
            span = max(0, self.backdrop.get_height() - WINH)
            oy = int(span * (0.5 - 0.5 * math.cos(self.t * 0.06)))
            surf.blit(self.backdrop, (0, -oy))
            surf.blit(self._vignette(), (0, 0))
        else:
            surf.fill((10, 12, 26))
            for i in range(9):
                x = int(120 + i * 95 + 60 * math.sin(self.t * 0.3 + i))
                y = int(300 + 90 * math.cos(self.t * 0.22 + i * 1.3))
                assets.draw_gear(surf, x, y, 14 + (i % 3) * 8,
                                 (34, 40, 66), 10)
        self._outlined(surf, "TIN CAN", WINW // 2, 110, 92, PAL["amber"],
                       bold=True)
        self._outlined(surf, "CHRONICLES", WINW // 2, 190, 74,
                       (235, 235, 245), bold=True)
        sub = "a tiny j-rpg of gears and girls"
        self._outlined(surf, sub, WINW // 2, 268, 26, (215, 222, 240), w=2)
        opts = self.options()
        y0 = 330
        for i, o in enumerate(opts):
            c = PAL["text"]
            if i == self.opt_idx:
                assets.draw_arrow(surf, WINW // 2 - 70, y0 + i * 44 - 4)
                c = PAL["amber"]
            assets.draw_text(surf, o, WINW // 2 - 50, y0 + i * 44 - 8, 32, c)
        ctr = 450
        assets.draw_text(surf, "ARROWS/WASD move   Z confirm   X cancel   "
                          "C menu   F1 help   M mute", WINW // 2, ctr, 22,
                         PAL["text_dim"], align="center")
        if self.gameover:
            assets.draw_text(surf, "The party fell... but the gears still turn.",
                             WINW // 2, 415, 24, PAL["red"],
                             align="center")


class EndingScene(Scene):
    """Scrolling epilogue after the Clockmaker falls."""
    LINES = [
        "The Astral Orrery shudders, and its great rings fall still.",
        "",
        "Five Star Gears go dark. The Clockmaker's mask cracks,",
        "and beneath it is only Orlo Venn - an old, tired tinkerer",
        "who wanted to stop time before it took everything he loved.",
        "",
        "Nara opens the yellowed letter and reads it aloud:",
        "'Papa - come home soon. Don't be sad if I'm sleeping.",
        "Clocks are for counting good days, not stopping them.",
        "Love, Lira.'",
        "",
        "Orlo weeps for a long time. Then he asks to go home.",
        "",
        "Kai, Nara and Vela bring him back to Cinderhollow,",
        "where Elder Bram is waiting at the gate with the kettle on.",
        "The mountain hums softly again - a kinder sort of hum.",
        "",
        "In Duneholm the sand stops ticking.",
        "In Mossfall the great tree blooms.",
        "In Forgeholm the dwarves light their own furnaces.",
        "In Murkwater the observatory lens finally looks at stars.",
        "In Gearhaven the guard marches home and takes off its boots.",
        "",
        "And somewhere, a clock simply keeps time.",
        "",
        "",
        "TIN CAN CHRONICLES",
        "",
        "Thank you for playing!",
    ]

    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0
        flags = game.flags
        flags["game_clear"] = True
        try:
            save.save_game(game)
        except Exception:
            pass

    def update(self, dt, pressed, held):
        self.t += dt
        if self.t > 4 and ("a" in pressed or "b" in pressed) and \
                self.t > len(self.LINES) * 1.2:
            self.game.scene = TitleScene(self.game)

    def draw(self, surf):
        surf.fill((8, 10, 26))
        y0 = WINH - int(self.t * 34)
        for i, ln in enumerate(self.LINES):
            y = y0 + i * 36
            if -40 < y < WINH:
                big = ln == "TIN CAN CHRONICLES"
                assets.draw_text(surf, ln, WINW // 2, y, 40 if big else 22,
                                 PAL["amber"] if big else PAL["text"],
                                 bold=big, align="center")


class HelpScene(Scene):
    """F1 manual opened from the title menu."""

    def __init__(self, game):
        super().__init__(game)
        self.panel = HelpOverlay(game)

    def update(self, dt, pressed, held):
        if pressed:
            self.game.audio.sfx("cancel")
            self.game.scene = TitleScene(self.game)

    def draw(self, surf):
        surf.fill((10, 12, 26))
        self.panel.draw(surf)


class IntroScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.pages = list(data.INTRO)
        self.pi = 0
        self.t = 0.0

    def update(self, dt, pressed, held):
        self.t += dt
        if "a" in pressed:
            self.game.audio.sfx("confirm")
            self.pi += 1
            if self.pi >= len(self.pages):
                g = self.game
                x, y = data.TOWN_START
                g.start_world("town", x, y, "down")

    def draw(self, surf):
        surf.fill((8, 9, 18))
        if self.pi < len(self.pages):
            txt = self.pages[self.pi]
            r = pygame.Rect(90, 170, WINW - 180, 200)
            assets.draw_panel(surf, r)
            lines = assets.wrap_text(txt, 30, r.w - 60)
            y = r.y + 30
            for ln in lines:
                assets.draw_text(surf, ln, r.x + 30, y, 30)
                y += 40
            if self.game.frame % 50 < 30:
                assets.draw_text(surf, "- press Z -", WINW // 2, r.bottom + 24,
                                 24, PAL["text_dim"], align="center")


# ---------------------------------------------------------------------------
class ShopBox:
    def __init__(self, game, stock=None):
        self.game = game
        self.done = False
        self.stock = stock or data.SHOP_STOCKS.get(
            getattr(game.world_scene.world, "map_id", "shop"),
            data.SHOP_STOCKS["shop"])
        self.idx = 0
        self.note = None
        self.note_t = 0.0

    def update(self, dt, pressed):
        if self.note_t > 0:
            self.note_t -= dt
        stock = self.stock
        if "up" in pressed:
            self.idx = (self.idx - 1) % len(stock)
            self.game.audio.sfx("cursor")
        if "down" in pressed:
            self.idx = (self.idx + 1) % len(stock)
            self.game.audio.sfx("cursor")
        if "b" in pressed:
            self.game.audio.sfx("cancel")
            return "close"
        if "a" in pressed:
            iid = stock[self.idx]
            it = data.ITEMS[iid]
            p = self.game.party
            if p.gold >= it["price"]:
                p.gold -= it["price"]
                p.add_item(iid)
                if it["kind"] == "item":
                    self.game.audio.sfx("confirm")
                    self.flash(f"Bought {it['name']}!")
                else:
                    eq = p.autoequip(iid)
                    self.game.audio.sfx("confirm")
                    self.flash(eq or f"Bought {it['name']} (kept)!")

            else:
                self.game.audio.sfx("cancel")
                self.flash("Not enough gil!")

    def flash(self, txt):
        self.note = txt
        self.note_t = 1.4

    def draw(self, surf):
        p = self.game.party
        rect = pygame.Rect(150, 100, 420, 330)
        assets.draw_panel(surf, rect)
        assets.draw_text(surf, "* RUSTY NAIL GENERAL STORE *",
                         rect.x + 20, rect.y + 14, 26, PAL["amber"],
                         bold=True)
        assets.draw_text(surf, f"Gold: {p.gold}", rect.right - 150,
                         rect.y + 16, 24, PAL["amber"])
        y = rect.y + 56
        for i, iid in enumerate(self.stock):
            it = data.ITEMS[iid]
            col = PAL["text"]
            if i == self.idx:
                assets.draw_arrow(surf, rect.x + 14, y + 2)
                col = PAL["amber"]
            assets.draw_text(surf, it["name"], rect.x + 38, y, 24, col)
            assets.draw_text(surf, f"{it['price']} g", rect.right - 80, y, 24,
                             PAL["text_dim"])
            y += 33
        cur = data.ITEMS[self.stock[self.idx]]
        assets.draw_text(surf, cur.get("desc", ""), rect.x + 20,
                         rect.bottom - 34, 20, PAL["text_dim"])
        if self.note and self.note_t > 0:
            r2 = pygame.Rect(150, 442, 420, 40)
            assets.draw_panel(surf, r2)
            assets.draw_text(surf, self.note, 166, r2.y + 9, 24,
                             PAL["amber"])


# ---------------------------------------------------------------------------
class WorldScene(Scene):
    def __init__(self, game, map_id, x, y, face="down"):
        super().__init__(game)
        self.world = world_mod.World(game, game.party, game.sheets, map_id,
                                      x, y, face)
        self.state = "play"
        self.overlay = None            # dialogue / shop / menu
        self.pending_exit = None
        self.fade = None               # ('out'|'in', t)
        self.battle_fade_t = 0.0
        self.pending_battle = None
        self.transition_done_cb = None
        self.hint_t = 0.0
        if game.audio.ok:
            game.audio.play_music(self.world.music)

    # -- helpers -----------------------------------------------------------------
    def show_dialog(self, pages, on_finish=None, speakers=True):
        self.state = "dialog"
        self.overlay = dialogue.DialogueBox(self.game, pages,
                                            on_finish=on_finish,
                                            speakers=speakers)

    # -- one-shot story scenes (story.SCENES) ---------------------------------
    def _check_scenes(self):
        """Play the first pending scene for this map, if any."""
        w = self.world
        key = (w.map_id, len(self.game.flags),
               len(self.game.party.inventory))
        if key == getattr(self, "_scene_key", None):
            return False
        self._scene_key = key
        flags = self.game.flags
        for sc in getattr(data, "SCENES", {}).get(w.map_id, []):
            if sc["id"] in flags:
                continue
            if sc.get("req") is not None and self._match_dialog(
                    [dict(req=sc["req"], lines=[])]) is None:
                continue
            flags[sc["id"]] = True
            lines = list(sc.get("lines", []))
            for f in sc.get("set", []):
                flags[f] = True

            def talk(lines=lines):
                if lines:
                    self.show_dialog(lines)
            if sc.get("card"):
                num, title = sc["card"]
                self.state = "card"
                self.overlay = dialogue.ChapterCard(self.game, num, title,
                                                    on_finish=talk)
            else:
                talk()
            return True
        return False

    def begin_transition(self, to_map, tx, ty, face):
        self.pending_exit = (to_map, tx, ty, face)
        self.fade = ("out", 0.0)
        self.state = "transition"

    def use_exit(self, ex, x, y):
        if ex["to"] in ("locked", "none"):
            self.show_dialog(["*Locked*",
                              "It won't budge. Someone likes their privacy."])
            return
        req = ex.get("req")
        if req and not self.game.flags.get(req):
            self.show_dialog(["*The way is sealed.*",
                              "Something here is waiting for you to "
                              "prove yourself first."])
            return
        self.game.audio.sfx("confirm")
        self.begin_transition(ex["to"], ex["tx"], ex["ty"], ex["face"])

    def interact(self):
        w = self.world
        tgt = w.interact_target()
        if not tgt:
            ch = world_mod.tile_at(w.rows, *w.facing_tile())
            if ch == "b":
                self.show_dialog(["The barrel is empty. It mocks you."])
            return
        kind, obj = tgt
        if kind == "npc":
            self._npc_dialog(obj)
        elif kind == "monster":
            self.game.start_entity_battle(self, obj)
        elif kind == "chest":
            opened = self.game.flags["opened_chests"]
            if obj["id"] in opened:
                self.show_dialog(["The chest is empty."])
            else:
                opened[obj["id"]] = True
                self._give_chest(obj)
        elif kind == "sign":
            self.show_dialog(list(obj), speakers=False)
        elif kind == "crystal":
            p = self.game.party
            for m in p.members:
                m.hp, m.mp = m.maxhp, m.maxmp
            save.save_game(self.game)
            self.game.audio.sfx("save")
            self.show_dialog(["*An azure crystal hums softly...*",
                              "The party feels fully rested!",
                              "Progress saved."])
        elif kind == "ship":
            self._use_ship(obj)
        elif kind == "locked":
            self.show_dialog(["*Locked*", "It won't budge."])
        elif kind == "barrel":
            self.show_dialog(["Nothing but dust in here."])

    def _use_ship(self, ship):
        cfg = data.SHIPS2.get(self.world.map_id, {})
        alts = cfg.get("alts") or ([cfg["alt"]] if cfg.get("alt") else [])
        options = [("*The Umbra Wreck*", "ship", ship)]
        for alt in alts:
            if self.game.flags.get(alt.get("req", "none")):
                options.append((alt.get("label", "Set sail"), "ship", alt))
        self.state = "choice"
        ch = dialogue.Choice(
            self.game, (WINW // 3, WINH // 3, 320, 130), options,
            title="Set sail?")
        ch.on_pick = self._ship_pick
        self.overlay = ch

    def _ship_pick(self, sel):
        if sel is not None and sel[1] == "ship":
            payload = sel[2]
            lines = list(payload.get("lines", []))
            self.state = "dialog"
            self.overlay = dialogue.DialogueBox(
                self.game, lines,
                on_finish=lambda: self.begin_transition(
                    payload["to"], payload["tx"], payload["ty"],
                    payload.get("face", "down")))
        else:
            self.state = "play"

    def _npc_dialog(self, npc):
        if npc.shop:
            entries = npc.data.get("dialog", [])
            lines, flags_to_set, give = self._match_dialog(
                entries, flags_to_set=True)
            stock = npc.data.get("stock")

            def finish():
                self._apply_rewards(flags_to_set, give)
                self._open_shop(stock)
            self.show_dialog(lines, on_finish=finish)
            return
        if getattr(npc, "inn", 0):
            entries = npc.data.get("dialog", [])
            lines = self._match_dialog(entries)
            self.show_dialog(lines,
                             on_finish=lambda: self._open_inn_choice(npc))
            return
        self._run_dialog(npc)

    def _open_inn_choice(self, npc):
        self.state = "choice"
        ch = dialogue.Choice(
            self.game, (WINW // 3, WINH // 3 + 40, 320, 110),
            [("Rest", "rest", None), ("Leave", "none", None)],
            title="Rest here?")

        def pick(sel):
            if sel is None or sel[0] != "Rest":
                self.state = "play"
                return
            price = npc.inn
            p = self.game.party
            if p.gold < price:
                self.state = "dialog"
                self.overlay = dialogue.DialogueBox(
                    self.game, ["Not enough gil..."])
                return
            p.gold -= price
            for m in p.members:
                m.hp, m.mp = m.maxhp, m.maxmp
            save.save_game(self.game)
            self.game.audio.sfx("save")
            self.state = "dialog"
            self.overlay = dialogue.DialogueBox(
                self.game, ["*The bed is warm.*",
                            "HP and MP restored - progress saved!"])
        ch.on_pick = pick
        self.overlay = ch            # attach the choice UI

    def _run_dialog(self, npc):
        entries = npc.data.get("dialog", [])
        matched = self._match_dialog(entries, flags_to_set=True)
        if matched is None:
            self.show_dialog(["..."])
            return
        lines, flags_to_set, give = matched
        def finish():
            self._apply_rewards(flags_to_set, give)
            self.state = "play"
        self.show_dialog(lines, on_finish=finish)

    def _apply_rewards(self, flags_to_set, give):
        for f in flags_to_set or []:
            self.game.flags[f] = True
        if not give:
            return
        p = self.game.party
        p.gold += give.get("gold", 0)
        if give.get("exp"):
            for m in p.members:
                if m.hp > 0:
                    m.gain_exp(give["exp"])
        takes = give.get("take")
        for iid in (takes if isinstance(takes, list) else [takes]):
            if iid and p.has_item(iid):
                p.take_item(iid)
        if give.get("item"):
            p.add_item(give["item"])
            p.autoequip(give["item"])
        # NOTE: state set after dialog finishes

    def _match_dialog(self, entries, flags_to_set=False):
        flags = self.game.flags
        for e in entries:
            req = e.get("req")
            if isinstance(req, list):           # every condition must hold
                ok = all(self._match_dialog([dict(req=r, lines=[])])
                         is not None for r in req)
                req = None if ok else "__never__"
            ok = req is None
            if not ok and req is not None:
                if req.startswith("!"):
                    ok = req[1:] not in flags
                elif req.startswith("item:"):
                    ok = self.game.party.has_item(req[5:])
                elif req.startswith("kills:"):
                    try:
                        _, eid, cnt = req.split(":")
                        ok = flags.get("kills", {}).get(eid, 0) >= int(cnt)
                    except ValueError:
                        ok = False
                else:
                    ok = req in flags
            if ok:
                if flags_to_set:
                    return (list(e["lines"]), list(e.get("set", [])),
                            dict(e.get("give", {})))
                return list(e["lines"])
        return None

    def _open_shop(self, stock=None):
        self.state = "shop"
        self.overlay = ShopBox(self.game, stock=stock)

    def _give_chest(self, chest):
        p = self.game.party
        iid = chest["item"]
        qty = chest.get("qty", 1)
        it = data.ITEMS[iid]
        name = it["name"] + (f" x{qty}" if qty > 1 else "")
        msgs = [f"Found {name}!"]
        for _ in range(qty):
            p.add_item(iid)
        eq = p.autoequip(iid)
        if eq:
            msgs.append(eq)
        self.game.audio.sfx("chest")
        self.show_dialog(msgs)

    # -- update ---------------------------------------------------------------
    def update(self, dt, pressed, held):
        w = self.world
        if self.state == "play" and not w.walker.moving and \
                self._check_scenes():
            return
        if self.state == "play":
            self._update_play(dt, pressed, held)
            w.walker.update(dt, w)
            # chain straight into the next step while a direction is held,
            # so walking never drops a frame back to the idle pose
            if self.state == "play" and not w.walker.moving and \
                    w.walker.carry > 0 and w is self.world:
                self._try_walk(held)
                if not w.walker.moving:
                    w.walker.carry = 0.0
            for n in w.npcs:
                n.update(dt, w)
            for mo in w.monsters:
                mo.update(dt, w)
            # monster contact while standing still (they may wander into you)
            if w.walker.arrived_here is False and not w.walker.moving:
                for mo in w.monsters:
                    if abs(mo.x - w.walker.gx) + abs(mo.y - w.walker.gy) <= 1:
                        self.game.start_entity_battle(self, mo)
                        return
        elif self.state == "card":
            ov = self.overlay
            ov.update(dt, pressed)
            if ov.done and self.overlay is ov:
                self.overlay = None
                self.state = "play"
        elif self.state == "dialog":
            self.overlay.update(dt, pressed)
            if getattr(self.overlay, "done", False) and \
                    self.state == "dialog":
                self.overlay = None
                self.state = "play"
        elif self.state == "shop":
            res = self.overlay.update(dt, pressed)
            if res == "close":
                self.overlay = None
                self.state = "play"
        elif self.state == "menu":
            self.overlay.update(dt, pressed)
            if getattr(self.overlay, "done", False) and \
                    self.state == "menu":
                self.overlay = None
                self.state = "play"
        elif self.state == "choice":
            ov = self.overlay
            if ov is None:
                self.state = "play"
            else:
                ov.update(dt, pressed)
                if getattr(ov, "done", False):
                    # Choice already invoked on_pick itself; calling it
                    # again here charged inns twice / re-opened dialogs
                    if self.overlay is ov:
                        self.overlay = None
                    if self.state == "choice":
                        self.state = "play"
        elif self.state == "transition":
            _, t = self.fade
            t += dt
            if self.fade[0] == "out":
                if t >= 0.4:
                    to_map, tx, ty, face = self.pending_exit
                    self.world.load_map(to_map, tx, ty, face)
                    self.game.audio.play_music(self.world.music)
                    self.pending_exit = None
                    self.fade = ("in", 0.0)
                else:
                    self.fade = ("out", t)
            else:
                if t >= 0.4:
                    self.fade = None
                    self.state = "play"
                    self.world.walker.arrived_here = \
                        (self.world.walker.gx, self.world.walker.gy) in \
                        self.world.exits
                else:
                    self.fade = ("in", t)
        elif self.state == "battle_fade":
            self.battle_fade_t += dt
            if self.battle_fade_t >= 0.55:
                kind, payload = self.pending_battle
                self.pending_battle = None
                self.state = "battle_hold"
                if kind == "entity":
                    self.game.start_battle_scene(payload.group,
                                                 entity=payload,
                                                 boss=payload.boss)
                else:
                    self.game.start_battle_scene(payload)

    def _update_play(self, dt, pressed, held):
        w = self.world
        walker = w.walker
        if "menu" in pressed or "b" in pressed:
            self.state = "menu"
            self.overlay = menu_mod.MenuOverlay(self.game)
            self.game.audio.sfx("confirm")
            return
        if walker.moving:
            return
        if "a" in pressed:
            walker.moving = False
            self.interact()
            return
        self._try_walk(held)

    def _try_walk(self, held):
        w = self.world
        walker = w.walker
        dirs = []
        if "up" in held:
            dirs.append((0, -1))
        if "down" in held:
            dirs.append((0, 1))
        if "left" in held:
            dirs.append((-1, 0))
        if "right" in held:
            dirs.append((1, 0))
        if not dirs:
            return
        dx, dy = dirs[0]
        walker.face = {(-1, 0): "left", (1, 0): "right", (0, 1): "down",
                       (0, -1): "up"}[(dx, dy)]
        nx, ny = walker.gx + dx, walker.gy + dy
        if w.can_step(nx, ny):
            walker.begin_step(dx, dy)

    # -- draw -------------------------------------------------------------------
    def draw(self, surf):
        w = self.world
        low = pygame.Surface((GAMEW, GAMEH))
        ox = w.walker.px + TILE // 2 - GAMEW // 2
        oy = w.walker.py + TILE // 2 - GAMEH // 2
        if w.w * TILE >= GAMEW:
            ox = max(0, min(w.w * TILE - GAMEW, ox))
        else:
            ox = (w.w * TILE - GAMEW) // 2
        if w.h * TILE >= GAMEH:
            oy = max(0, min(w.h * TILE - GAMEH, oy))
        else:
            oy = (w.h * TILE - GAMEH) // 2
        w.draw(low, self.game.play_time, ox, oy)
        surf.blit(pygame.transform.scale(low, (WINW, WINH)), (0, 0))
        # overlays
        if self.overlay is not None and self.state in ("dialog", "shop",
                                                       "menu", "choice",
                                                       "card"):
            self.overlay.draw(surf)
        if self.fade:
            _, t = self.fade
            a = int(255 * min(1, t / 0.4))
            ov = pygame.Surface((WINW, WINH))
            ov.fill((0, 0, 0))
            ov.set_alpha(a)
            surf.blit(ov, (0, 0))
        if self.state in ("battle_fade", "battle_hold"):
            # SNES battle swirl: white flash, mosaic break-up, blinds close
            t = self.battle_fade_t
            if t < 0.12:
                ov = pygame.Surface((WINW, WINH), pygame.SRCALPHA)
                ov.fill((255, 255, 255, int(200 * (1 - t / 0.12))))
                surf.blit(ov, (0, 0))
            f = min(1.0, t / 0.55)
            assets.mosaic(surf, 1 + f * f * 28)
            assets.blinds(surf, max(0.0, (f - 0.35) / 0.65))
