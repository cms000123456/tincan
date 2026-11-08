"""Battle scene: active-time battle (Wait mode), techs, items, boss AI."""

import math
import random

import pygame

import assets
import data
from settings import PAL, WINW, WINH, SCALE, ELEMENT_COLOR

PARTY_SLOTS = [(150, 300), (290, 355), (430, 295)]
ENEMY_SLOTS = [(900, 250), (750, 360), (900, 430)]


class Actor:
    """Battle combatant wrapper."""

    def __init__(self, kind=None, ref=None):
        self.kind = kind          # 'party' or 'enemy'
        self.ref = ref            # Character or enemy definition dict
        self.bar = random.uniform(0.0, 0.25)
        self.dead = False
        self.name = ref["name"] if kind == "enemy" else ref.name
        self.spd = ref["spd"] if kind == "enemy" else ref.spd
        self.fx_off = (0, 0)
        self.flash = 0.0
        self.shake = 0.0

    def atk(self):
        return self.ref.atk() if self.kind == "party" else self._atk

    def dfn(self):
        return self.ref.dfn() if self.kind == "party" else self._dfn

    def mag(self):
        return self.ref.mag() if self.kind == "party" else self._mag

    def mdf(self):
        return self.ref.mdf() if self.kind == "party" else self._mdf


class EnemyActor(Actor):
    def __init__(self, ref):
        super().__init__("enemy", ref)
        self.hp = ref["hp"]
        self.maxhp = ref["hp"]
        self.mp = 99
        self._atk = ref["atk"]
        self._dfn = ref["dfn"]
        self._mag = ref["mag"]
        self._mdf = ref["mdf"]
        self.sprite = ref["sprite"]
        self.scale = ref.get("scale", 4)
        self.skills = ref.get("skills") or {}
        self.weak = ref.get("weak")
        self.resist = ref.get("resist")


class PartyActor(Actor):
    """HP reads/writes route to the live Character."""

    def __init__(self, ref):
        super().__init__("party", ref)

    @property
    def hp(self):
        return self.ref.hp

    @hp.setter
    def hp(self, v):
        self.ref.hp = max(0, v)

    @property
    def maxhp(self):
        return self.ref.maxhp

    # party actors delegate stat calls to the Character


class Timeline:
    """Simple keyframe action for one attacker."""

    def __init__(self, attacker, targets, fn_apply, kind):
        self.att = attacker
        self.targets = targets
        self.fn = fn_apply
        self.t = 0.0
        self.kind = kind        # 'phys' | 'mag' | 'heal' | 'enemy' | 'item'
        self.hit_done = False
        self.duration = 0.75

    def update(self, dt, scene):
        self.t += dt
        sign = 1 if self.kind == "phys" else -1
        if self.kind in ("phys", "enemy"):
            if self.t < self.duration * 0.4:
                f = self.t / (self.duration * 0.4)
                self.att.fx_off = (int(24 * f) * sign, -int(6 * f))
            elif self.t < self.duration:
                f = (self.t - self.duration * 0.4) / (self.duration * 0.6)
                self.att.fx_off = (int(24 * (1 - f)) * sign,
                                   -int(6 * (1 - f)))
            # apply at 40%
            if not self.hit_done and self.t >= self.duration * 0.4:
                self.hit_done = True
                self.fn(scene)
        elif self.kind == "mag":
            if not self.hit_done and self.t >= self.duration * 0.45:
                self.hit_done = True
                self.fn(scene)
        else:
            if not self.hit_done and self.t >= self.duration * 0.4:
                self.hit_done = True
                self.fn(scene)
        if self.t >= self.duration:
            self.att.fx_off = (0, 0)
            return True
        return False


class BattleScene:
    def __init__(self, game, group, entity=None, boss_ok=False):
        self.game = game
        self.party = game.party
        self.group = group
        self.entity = entity
        self.is_boss = boss_ok
        self.audio = game.audio
        self.actors_e = [EnemyActor(data.ENEMIES[eid]) for eid in group]
        self.actors_p = [PartyActor(m) for m in self.party.members]
        self.phase = "intro"
        self.t = 0.0
        self.timeline = None
        self.menu = None            # command menu (list of strings)
        self.menu_idx = 0
        self.submenu = None         # ('tech'|'item', entries, idx)
        self.targeting = None       # ('enemy'|'ally', payload)
        self.target_idx = 0
        self.active = None          # actor currently commanding
        self.msg = None
        self.msg_t = 0.0
        self.floaters = []
        self.slashes = []
        self.particles = []
        self.shake = 0.0
        self.flashcol = None
        self.flash_a = 0.0
        self.victory_msgs = None
        self.victory_idx = 0
        self.gameover = False
        self.result = None
        self.music = "battle"
        self.audio.play_music("battle")
        self.audio.sfx("encounter")
        self.bg = self._make_bg()
        intro = None
        if self.is_boss:
            for eid in self.group:
                if eid in data.BOSS_INTROS:
                    intro = data.BOSS_INTROS[eid]
                    break
        self.intro_boss_text = intro
        if self.intro_boss_text:
            self.show_msg(self.intro_boss_text[0], 1.2)

    # -- visuals ---------------------------------------------------------------
    def _area_key(self):
        """Map id, or the encounter region on maps that have several."""
        ws = getattr(self.game, "world_scene", None)
        if ws is None:
            return None
        w = ws.world
        enc = data.MAPS.get(w.map_id, {}).get("encounters")
        if isinstance(enc, list):
            gx, gy = w.walker.gx, w.walker.gy
            for region in enc:
                x0, y0, x1, y1 = region["rect"]
                if x0 <= gx <= x1 and y0 <= gy <= y1:
                    return region["name"]
        return w.map_id

    def _make_bg(self):
        """Generated scene for this area if there is one, else gears."""
        import sprites
        key = self._area_key()
        bg = data.MAPS.get(key, {}).get("battle_bg") if key else None
        img = sprites.battle_backdrop(bg or key, (WINW, WINH))
        if img is not None:
            return img
        s = pygame.Surface((WINW, WINH))
        for y in range(WINH):
            k = y / WINH
            r = int(18 + 26 * k)
            gg = int(22 + 30 * k)
            b = int(46 + 40 * k)
            pygame.draw.rect(s, (r, gg, b), (0, y, WINW, 1))
        for i in range(5):
            x = 130 + i * 190
            y = 130 + (i % 2) * 40
            assets.draw_gear(s, x, y, 26 + (i % 3) * 12, (38, 42, 62), 8)
        pygame.draw.ellipse(s, (44, 58, 86), (-120, 430, WINW + 240, 300))
        pygame.draw.ellipse(s, (52, 70, 100), (-60, 460, WINW + 120, 240))
        return s

    def _slot(self, actors, i):
        return (ENEMY_SLOTS if actors else PARTY_SLOTS)[min(i, 2)]

    def pos_of(self, actor):
        if actor.kind == "party":
            i = self.actors_p.index(actor)
            bx, by = PARTY_SLOTS[min(i, 2)]
            bob = int(2 * math.sin(self.t * 2 + i))
            return bx + actor.fx_off[0], by + actor.fx_off[1] + bob
        i = self.actors_e.index(actor)
        bx, by = ENEMY_SLOTS[min(i, 2)]
        # keep wide (boss) sprites fully on screen
        hi = self.game.assets.get("enemies_battle", {}).get(actor.sprite)
        if hi is not None:
            half = hi.get_width() * 3 // 2 + 12
            bx = min(bx, WINW - half)
        bob = int(3 * math.sin(self.t * 2.4 + i * 2.1))
        return bx + actor.fx_off[0], by + actor.fx_off[1] + bob

    # -- damage math -----------------------------------------------------------
    def variance(self):
        return random.uniform(0.86, 1.14)

    def calc_phys(self, att, tar, power, elem="none"):
        atk = att.atk()
        dfn = tar.dfn() * 0.9
        dmg = int((atk * 2 * power - dfn) * self.variance())
        crit = random.random() < 0.05
        if crit:
            dmg = int(dmg * 1.7)
        if att.kind == "party" and tar.kind == "enemy":
            if elem and getattr(tar, "weak", None) == elem:
                dmg = int(dmg * 1.6)
            if elem and getattr(tar, "resist", None) == elem:
                dmg = max(1, int(dmg * 0.55))
        return max(1, dmg), crit

    def calc_mag(self, att, tar, power, elem="none"):
        mag = att.mag()
        mdf = tar.mdf() * 0.8
        dmg = int((mag * 2.5 * power - mdf) * self.variance())
        if att.kind == "party" and tar.kind == "enemy":
            if elem and getattr(tar, "weak", None) == elem:
                dmg = int(dmg * 1.6)
            if elem and getattr(tar, "resist", None) == elem:
                dmg = max(1, int(dmg * 0.55))
        return max(1, dmg)

    def calc_heal(self, att, power):
        return int(power + att.mag() * 2.2)

    # -- helpers ----------------------------------------------------------------
    def show_msg(self, text, dur=1.1):
        self.msg = text
        self.msg_t = dur

    def pop_float(self, actor, text, color):
        x, y = self.pos_of(actor)
        self.floaters.append([text, color, x + 10, y - 10, 0.0])

    def burst(self, actor, color, n=14, big=False):
        x, y = self.pos_of(actor)
        for i in range(n if not big else n * 2):
            a = random.uniform(0, 6.28)
            sp = random.uniform(40, 160) * (1.6 if big else 1.0)
            self.particles.append([x, y, math.cos(a) * sp, math.sin(a) * sp,
                                   color, random.uniform(0.3, 0.7)])

    def flash_screen(self, color, alpha=110):
        self.flashcol = color
        self.flash_a = alpha

    def alive_enemies(self):
        return [a for a in self.actors_e if not a.dead]

    def alive_party(self):
        return [a for a in self.actors_p if not a.dead]

    # -- actions ----------------------------------------------------------------
    def do_attack(self, user, target):
        dmg, crit = self.calc_phys(user, target, 1.0, "none")
        self._apply_damage(user, target, dmg, crit, PAL["text"])

    def do_tech(self, user, tech, target):
        if tech["kind"] == "heal":
            amt = self.calc_heal(user, tech["power"])
            if tech["target"] == "allies":
                targets = self.alive_party()
            elif tech["target"] == "ally" and target is not None:
                targets = [target]
            else:
                targets = [user]
            def fn(scene):
                for tg in targets:
                    self._apply_heal(user, tg, amt)
            self.audio.sfx("heal")
        elif tech["kind"] == "phys":
            targets = self._targets_of(tech["target"], user)
            def fn(scene):
                for tg in targets:
                    d, c = self.calc_phys(user, tg, tech["power"],
                                          tech["elem"])
                    self._apply_damage(user, tg, d, c, PAL["amber"])
        else:
            targets = self._targets_of(tech["target"], user)
            def fn(scene):
                for tg in targets:
                    d = self.calc_mag(user, tg, tech["power"], tech["elem"])
                    self._apply_damage(user, tg, d, False, ELEMENT_COLOR.get(
                        tech["elem"], PAL["text"]))
        user.ref.mp -= tech["mp"]
        self.audio.sfx("tech")
        col = ELEMENT_COLOR.get(tech.get("elem"), (255, 255, 255))
        self.flash_screen(col, 80)
        self.show_msg(f"{user.name} uses {tech['name']}!", 0.8)
        return Timeline(user, targets, fn, "mag")

    def _targets_of(self, target_kind, user, is_ally=False):
        if target_kind == "enemies":
            return self.alive_enemies()
        if target_kind == "allies":
            return self.alive_party()
        return [user] if is_ally else self.alive_enemies()[:1]

    def do_combo(self, user, combo):
        partner = combo["partner"]
        partner.bar = 0.0
        user.ref.mp -= combo["mp"]
        self.audio.sfx("tech")
        col = ELEMENT_COLOR.get(combo.get("elem"), (255, 255, 255))
        self.flash_screen(col, 90)
        kind = combo["kind"]

        if kind == "guard":
            amt = int(90 + user.ref.mag() * 2.0)
            def fn(scene):
                for t in self.alive_party():
                    self._apply_heal(user, t, amt)
            msg = f"{user.name} & {partner.ref.name} cast {combo['name']}!"
        else:
            def fn(scene):
                for e in self.alive_enemies():
                    if kind == "waltz":
                        base = (user.atk() * 2.2 + partner.mag() * 1.8)
                        d = int((base - e.dfn() * 0.9) * self.variance())
                    else:   # tempest
                        base = (user.mag() * 2.4 + partner.mag() * 1.6)
                        d = int((base - e.mdf() * 0.8) * self.variance())
                    if combo.get("elem"):
                        if getattr(e, "weak", None) == combo["elem"]:
                            d = int(d * 1.6)
                        if getattr(e, "resist", None) == combo["elem"]:
                            d = max(1, int(d * 0.55))
                    self._apply_damage(user, e, max(1, d), False,
                                       ELEMENT_COLOR.get(combo["elem"],
                                                         PAL["amber"]))
            msg = f"{user.name} & {partner.ref.name} unleash " \
                  f"{combo['name']}!"
        self.show_msg(msg, 1.0)
        self.burst(user, col, 18, big=True)
        return Timeline(user, [], fn, "mag")

    def slash(self, target, color):
        x, y = self.pos_of(target)
        self.slashes.append([x, y + 18, 0.0, color])

    def _apply_damage(self, user, target, dmg, crit, color):
        if user is not None:
            self.slash(target, (255, 255, 255) if user.kind == "party"
                       else (255, 110, 90))
        target.hp -= dmg
        target.flash = 0.25
        self.pop_float(target, str(dmg), color)
        self.burst(target, color)
        target.shake = 0.3
        self.shake = 0.25
        self.audio.sfx("hit_big" if dmg > 40 else "hit")
        if crit:
            self.pop_float(target, "CRIT!", PAL["red"])
        if target.hp <= 0:
            target.hp = 0
            target.dead = True
            if target.kind == "party":
                self.audio.sfx("dead")
            self.burst(target, (120, 120, 140), 20, big=True)
        if target.kind == "party":
            target.ref.flash = 0.3

    def _apply_heal(self, user, target, amt):
        gain = min(target.maxhp - target.hp, amt) \
            if target.kind == "party" else 0
        if target.kind == "enemy":
            gain = 0
        if target.kind == "party":
            target.hp = min(target.maxhp, target.hp + gain)
            self.pop_float(target, str(gain), PAL["green"])
            self.burst(target, (140, 255, 160), 10)
            self.audio.sfx("heal")

    def do_item(self, user, item_id, target):
        it = data.ITEMS[item_id]
        def fn(scene):
            before = target.ref.hp
            self.game.party.apply_item(item_id, target.ref)
            if it.get("heal"):
                gain = target.ref.hp - before
                self._heal_visual(target, gain)
            elif it.get("mana"):
                self.pop_float(target, "MP!", PAL["cyan"])
            self.audio.sfx("heal")
        return Timeline(user, [target], fn, "item")

    def _heal_visual(self, actor, gain):
        self.pop_float(actor, str(gain), PAL["green"])
        self.burst(actor, (140, 255, 160), 10)

    def enemy_act(self, actor):
        """Pick and begin an enemy action."""
        user = actor
        # choose skill or attack
        skills = actor.skills
        choice = None
        if skills:
            entries = [("Attack", None, 0.6)]
            for name, sk in skills.items():
                entries.append((name, sk, sk.get("weight", 0.2)))
            total = sum(w for _, _, w in entries)
            r = random.uniform(0, total)
            acc = 0
            for name, sk, w in entries:
                acc += w
                if r <= acc:
                    choice = (name, sk)
                    break
            choice = choice or ("Attack", None)
        else:
            choice = ("Attack", None)
        name, sk = choice
        if sk is None:
            tgt = random.choice(self.alive_party())
            def fn(scene):
                self._enemy_damage(user, tgt, phys=True, power=1.0,
                                   elem="none", label=None)
            self.audio.sfx("hit")
            self.show_msg(f"{user.name} attacks!", 0.7)
            return Timeline(user, [tgt], fn, "enemy")
        kind = sk.get("kind", "phys")
        if sk.get("target") in ("all", "enemies"):
            tgts = self.alive_party()
        else:
            tgts = [random.choice(self.alive_party())]
        def fn(scene):
            for tg in tgts:
                self._enemy_damage(user, tg, phys=(kind == "phys"),
                                   power=sk.get("power", 1.0),
                                   elem=sk.get("elem", "none"), label=name)
        self.audio.sfx("tech" if kind == "mag" else "hit")
        col = ELEMENT_COLOR.get(sk.get("elem"), (255, 255, 255))
        if kind == "mag":
            self.flash_screen(col, 70)
        self.show_msg(f"{user.name} uses {name}!", 0.8)
        return Timeline(user, tgts, fn, "enemy")

    def _enemy_damage(self, user, target, phys, power, elem, label):
        # mirror of _apply_damage but reading enemy stats
        self.slash(target, (255, 110, 90))
        if phys:
            atk = user.atk()
            dfn = target.ref.dfn() * 0.9
            dmg = int((atk * 2 * power - dfn) * self.variance())
        else:
            mag = user.mag()
            mdf = target.ref.mdf() * 0.8
            dmg = int((mag * 2.5 * power - mdf) * self.variance())
        dmg = max(1, dmg)
        target.hp -= dmg
        target.flash = 0.3
        target.shake = 0.3
        self.shake = 0.3
        self.pop_float(target, str(dmg), (255, 120, 100))
        self.burst(target, (255, 120, 100))
        self.audio.sfx("hit_big")
        if target.hp <= 0:
            target.hp = 0
            target.dead = True
            self.audio.sfx("dead")
            self.burst(target, (120, 120, 140), 20, big=True)

    # -- command UI --------------------------------------------------------------
    def open_command(self, actor):
        self.active = actor
        self.menu = ["Attack", "Tech", "Item", "Run"]
        self.menu_idx = 0

    # -- update ------------------------------------------------------------------
    def update(self, dt, pressed, held=None):
        self.t += dt
        for a in self.actors_p + self.actors_e:
            a.flash = max(0.0, a.flash - dt)
            a.shake = max(0.0, a.shake - dt)
            if a.kind == "party":
                a.ref.flash = max(0.0, a.ref.flash - dt)
        if self.flash_a > 0:
            self.flash_a = max(0.0, self.flash_a - dt * 220)
        if self.msg_t > 0:
            self.msg_t -= dt
        for f in self.floaters[:]:
            f[4] += dt
            f[2] += dt * 6
            if f[4] > 0.9:
                self.floaters.remove(f)
        for sl in self.slashes[:]:
            sl[2] += dt
            if sl[2] > 0.22:
                self.slashes.remove(sl)
        for p in self.particles[:]:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 220 * dt
            p[5] -= dt
            if p[5] <= 0:
                self.particles.remove(p)
        self.shake = max(0.0, self.shake - dt)

        if self.phase == "intro":
            self.t_reset = getattr(self, "t_reset", 0.0) + dt
            if self.t_reset > (1.5 if self.is_boss else 0.8):
                self.phase = "idle"
            return
        if self.phase == "gameover":
            if "a" in pressed:
                self.result = "gameover"
                self.game.end_battle(self)
            return
        if self.phase == "victory":
            self._victory_update(dt, pressed)
            return

        # timeline action running
        if self.timeline:
            if self.timeline.update(dt, self):
                bar = self.timeline.att.bar
                self.timeline = None
                if self._check_end():
                    return
                self.phase = "idle"
            return

        # running bars (Wait mode: pause while commanding)
        commanding = self.menu is not None or self.submenu is not None \
            or self.targeting is not None
        if self.phase == "idle" and not commanding:
            for a in self.actors_p + self.actors_e:
                if not a.dead:
                    a.bar = min(1.0, a.bar + dt * (a.spd / 60.0) * 0.9)
            ready = [a for a in self.actors_p if not a.dead and a.bar >= 1.0]
            if ready:
                self.open_command(max(ready, key=lambda a: a.bar))
                self.audio.sfx("cursor")
                return
            eready = [a for a in self.actors_e if not a.dead and a.bar >= 0.9]
            if eready:
                actor = max(eready, key=lambda a: a.bar)
                actor.bar = 0.0
                self.timeline = self.enemy_act(actor)
                if not self._check_end():
                    self.phase = "acting"
            return
        if self.phase == "idle" and commanding:
            self._command_update(pressed)
            return
        if self.phase == "acting" and not commanding:
            self.phase = "idle"

    def _check_end(self):
        if not self.alive_enemies():
            self._start_victory()
            return True
        if not self.alive_party():
            self.phase = "gameover"
            self.show_msg("The party has fallen...", 5.0)
            return True
        return False

    # -- command input -----------------------------------------------------------
    def _tech_entries(self, actor):
        import data as _d
        me_id = actor.ref.id
        out = list(actor.ref.known_techs())
        for c in _d.COMBOS:
            other = c["b"] if c["a"] == me_id else                 (c["a"] if c["b"] == me_id else None)
            if not other:
                continue
            partner = next((a for a in self.alive_party()
                            if a.ref.id == other
                            and a is not actor), None)
            if partner and partner.bar >= 0.9:
                tag = dict(c)
                tag["partner"] = partner
                tag["combo"] = True
                out.append(tag)
        return out

    def _close_command(self):
        self.menu = None
        self.submenu = None
        self.targeting = None

    def _command_update(self, pressed):
        if self.submenu:
            self._submenu_update(pressed)
            return
        if self.targeting:
            self._targeting_update(pressed)
            return
        n = len(self.menu)
        if "up" in pressed:
            self.menu_idx = (self.menu_idx - 1) % n
            self.audio.sfx("cursor")
        if "down" in pressed:
            self.menu_idx = (self.menu_idx + 1) % n
            self.audio.sfx("cursor")
        if "b" in pressed:
            self._close_command()
            self.audio.sfx("cancel")
            return
        if "a" in pressed:
            cmd = self.menu[self.menu_idx]
            actor = self.active
            if cmd == "Attack":
                self.targeting = ("attack", None)
                self.target_idx = 0
                self.menu = None
                self.audio.sfx("confirm")
            elif cmd == "Tech":
                techs = self._tech_entries(actor)
                if not techs:
                    self.show_msg("No techs ready yet!", 0.8)
                    return
                self.submenu = ("tech", techs, 0)
                self.menu = None
                self.audio.sfx("confirm")
            elif cmd == "Item":
                inv = [(k, data.ITEMS[k]) for k in
                       sorted(self.game.party.inventory)
                       if data.ITEMS[k]["kind"] == "item"]
                if not inv:
                    self.show_msg("No usable items!", 0.8)
                    return
                self.submenu = ("item", inv, 0)
                self.menu = None
                self.audio.sfx("confirm")
            elif cmd == "Run":
                if self.is_boss:
                    self.show_msg("Can't escape the GEARLORD!", 1.0)
                    self.active.bar = 0.6
                    self._close_command()
                    return
                if random.random() < 0.6:
                    self.audio.sfx("run")
                    self.result = "ran"
                    self.game.end_battle(self)
                else:
                    self.show_msg("Can't escape!", 0.9)
                    self.active.bar = 0.5
                    self._close_command()
            else:
                self._close_command()

    def _submenu_update(self, pressed):
        kind, entries, idx = self.submenu
        n = len(entries)
        if kind == "tech":
            usable = [self.active.ref.mp >= t["mp"] for t in entries]
        else:
            usable = [True] * n
        moved = False
        if "up" in pressed:
            for _ in range(n):
                idx = (idx - 1) % n
                if usable[idx]:
                    moved = True
                    break
            self.audio.sfx("cursor")
        if "down" in pressed:
            for _ in range(n):
                idx = (idx + 1) % n
                if usable[idx]:
                    moved = True
                    break
            self.audio.sfx("cursor")
        self.submenu = (kind, entries, idx)
        if "b" in pressed:
            self.submenu = None
            self.menu = ["Attack", "Tech", "Item", "Run"]
            self.audio.sfx("cancel")
            return
        if "a" in pressed:
            i = self.submenu[2]
            if kind == "tech":
                tech = entries[i]
                if self.active.ref.mp < tech["mp"]:
                    self.audio.sfx("cancel")
                    return
                self.submenu = None
                if tech.get("combo"):
                    self.timeline = self.do_combo(self.active, tech)
                    self.active.bar = 0.0
                    self.active = None
                    self.phase = "acting"
                    return
                tgt = tech["target"]
                if tgt == "enemy":
                    self.targeting = ("tech", tech)
                    self.target_idx = 0
                    self.audio.sfx("confirm")
                    return
                if tgt == "ally":
                    self.targeting = ("tech_ally", tech)
                    self.target_idx = 0
                    self.audio.sfx("confirm")
                    return
                # instant tech (all targets)
                self.timeline = self.do_tech(self.active, tech, None)
                self.active.bar = 0.0
                self.active = None
                self.phase = "acting"
            else:
                item_id = entries[i][0]
                self.submenu = None
                it = data.ITEMS[item_id]
                if it.get("aoe"):
                    def fn(scene, item_id=item_id):
                        for e in list(self.alive_enemies()):
                            d = int(it["aoe"] * self.variance())
                            self._apply_damage(None, e, d, False,
                                               (255, 150, 60))
                    self.timeline = Timeline(user, [], fn, "mag")
                    self.game.party.take_item(item_id)
                    self.active.bar = 0.0
                    self.active = None
                    self.phase = "acting"
                    self.show_msg(f"{user.name} throws a {it['name']}!",
                                  0.9)
                    return
                self.targeting = ("item", item_id)
                self.target_idx = 0
                self.audio.sfx("confirm")

    def _targeting_update(self, pressed):
        kind, payload = self.targeting
        if kind in ("attack", "tech"):
            alives = self.alive_enemies()
            if not alives:
                return
            if "left" in pressed or "up" in pressed:
                self.target_idx = (self.target_idx - 1) % len(alives)
                self.audio.sfx("cursor")
            if "right" in pressed or "down" in pressed:
                self.target_idx = (self.target_idx + 1) % len(alives)
                self.audio.sfx("cursor")
            if "b" in pressed:
                self.targeting = None
                self.menu = ["Attack", "Tech", "Item", "Run"]
                self.audio.sfx("cancel")
                return
            if "a" in pressed:
                tgt = alives[self.target_idx % len(alives)]
                self.targeting = None
                if kind == "attack":
                    user = self.active
                    self.timeline = Timeline(
                        user, [tgt],
                        lambda scene: self._apply_damage(
                            user, tgt,
                            *self.calc_phys(user, tgt, 1.0, "none"),
                            PAL["text"]),
                        "phys")
                    self.audio.sfx("hit")
                else:
                    self.timeline = self.do_tech(self.active, payload, tgt)
                self.active.bar = 0.0
                self.active = None
                self.phase = "acting"
        else:  # ally-targeted (item / ally tech)
            alives = self.alive_party()
            if "up" in pressed or "left" in pressed:
                self.target_idx = (self.target_idx - 1) % len(alives)
                self.audio.sfx("cursor")
            if "down" in pressed or "right" in pressed:
                self.target_idx = (self.target_idx + 1) % len(alives)
                self.audio.sfx("cursor")
            if "b" in pressed:
                self.targeting = None
                self.menu = ["Attack", "Tech", "Item", "Run"]
                self.audio.sfx("cancel")
                return
            if "a" in pressed:
                tgt = alives[self.target_idx % len(alives)]
                if kind == "tech_ally":
                    self.timeline = self.do_tech(self.active, payload, tgt)
                else:
                    self.timeline = self.do_item(self.active, payload, tgt)
                self.targeting = None
                self.active.bar = 0.0
                self.active = None
                self.phase = "acting"

    # -- victory ------------------------------------------------------------------
    def _start_victory(self):
        self.phase = "victory"
        self._close_command()
        self.audio.stop_music()
        self.audio.sfx("save")
        exp = sum(a.ref["exp"] for a in self.actors_e)
        gold = sum(a.ref["gold"] for a in self.actors_e)
        msgs = ["** VICTORY! **"]
        msgs.append(f"The party gains {exp} EXP and {gold} gil!")
        self.game.party.gold += gold
        kills = self.game.flags.setdefault("kills", {})
        for eid in self.group:
            kills[eid] = kills.get(eid, 0) + 1
        drops = []
        for a in self.actors_e:
            d = a.ref.get("drop")
            if d and random.random() < d[1]:
                drops.append(d[0])
        for it in drops:
            self.game.party.add_item(it)
            msgs.append(f"Found a {data.ITEMS[it]['name']}!")
        for m in self.party.members:
            if m.hp > 0:
                msgs.extend(m.gain_exp(exp))
        msgs.append("Press Z to continue.")
        self.victory_msgs = msgs
        self.victory_idx = 0
        self.victory_t = 0.0

    def victory_result(self):
        self.result = "won"
        self.game.end_battle(self)

    def _victory_update(self, dt, pressed):
        self.victory_t += dt
        # reveal lines as they finish
        if "a" in pressed and self.victory_t > 0.4:
            self.victory_idx += 1
            self.victory_t = 0.0
            self.audio.sfx("cursor")
            if self.victory_idx >= len(self.victory_msgs):
                self.victory_result()

    # -- drawing --------------------------------------------------------------------
    def draw(self, surf):
        sh = self.shake
        ox = random.randint(-6, 6) if sh > 0 else 0
        oy = random.randint(-4, 4) if sh > 0 else 0
        bg = self.bg
        surf.blit(bg, (ox, oy))
        # shadow ellipses
        for a in self.actors_p + self.actors_e:
            if a.dead:
                continue
            x, y = self.pos_of(a)
            if a.kind == "party":
                pygame.draw.ellipse(surf, (8, 10, 22),
                                    (x - 18, y + 40, 56, 18))
            else:
                pygame.draw.ellipse(surf, (8, 10, 22),
                                    (x - 26, y + 38, 52, 18))
        # enemies
        for a in self.actors_e:
            x, y = self.pos_of(a)
            if a.shake > 0 and random.random() < 0.6:
                x += random.randint(-3, 3)
            hi = self.game.assets.get("enemies_battle", {}).get(a.sprite)
            img = hi or self.game.assets["enemies"].get(a.sprite) or \
                self.game.assets["enemies"]["slime"]
            k = 3 if hi is not None else a.scale   # match the party's pixels
            w0, h0 = img.get_width(), img.get_height()
            squish = 1.0 + 0.045 * math.sin(self.t * 3.2 +
                                            self.actors_e.index(a) * 2.0)
            img = pygame.transform.scale(
                img, (int(w0 * squish * k), h0 * k))
            if a.dead:
                img = img.copy()
                img.set_alpha(80)
            surf.blit(img, (x - img.get_width() // 2, y - img.get_height() + 46))
            if a.flash > 0:
                pygame.draw.circle(surf, (255, 255, 255),
                                   (x, y + 20),
                                   max(6, img.get_width() // 3), 2)
            if not a.dead:
                # hp pips
                self._hp_sliver(surf, x, y + 50, a.hp / a.maxhp,
                                (200, 60, 60))
        # party
        for a, m in zip(self.actors_p, self.party.members):
            x, y = self.position_party(a)
            if a.dead:
                img = m.sheet.get(("right", "idle"))
                if img:
                    img = pygame.transform.scale(
                        img, (img.get_width() * 3, img.get_height() * 3))
                    img.set_alpha(60)
                    surf.blit(img, (x + 25 - img.get_width() // 2,
                                    y + 50 - img.get_height()))
                continue
            frame = "a" if (self.timeline and self.timeline.att is a) \
                else "idle"
            img = m.sheet[("right", frame)]
            img = pygame.transform.scale(
                img, (img.get_width() * 3, img.get_height() * 3))
            if m.flash > 0 or a.shake > 0 and random.random() < 0.6:
                x += random.randint(-3, 3)
            surf.blit(img, (x + 25 - img.get_width() // 2,
                            y + 50 - img.get_height()))
        self._slash_draw(surf)
        self._floaters_particles(surf)
        self._hud(surf)
        if self.msg and self.msg_t > 0:
            r = pygame.Rect(220, 150, WINW - 440, 118)
            if self.phase == "gameover":
                r = pygame.Rect(140, 200, WINW - 280, 140)
            assets.draw_panel(surf, r)
            y = r.y + 18
            for ln in assets.wrap_text(self.msg, 26, r.w - 40):
                assets.draw_text(surf, ln, r.x + 20, y, 26,
                                 PAL["red"] if self.phase == "gameover"
                                 else PAL["text"])
                y += 32
        if self.flash_a > 0 and self.flashcol:
            ov = pygame.Surface((WINW, WINH), pygame.SRCALPHA)
            ov.fill((*self.flashcol, int(self.flash_a)))
            surf.blit(ov, (0, 0))
        if self.phase == "victory":
            self._victory_panel(surf)

    def position_party(self, actor):
        x, y = self.pos_of(actor)
        return x - 8, y

    def _hp_sliver(self, surf, x, y, frac, col):
        w = int(44 * frac)
        pygame.draw.rect(surf, (10, 10, 20), (x - 22, y, 44, 5))
        if w > 0:
            pygame.draw.rect(surf, col, (x - 22, y, w, 5))

    def _slash_draw(self, surf):
        for (x, y, t, col) in self.slashes:
            pr = t / 0.22
            r = 22 + int(38 * pr)
            a0 = -2.4 + 1.9 * pr
            a1 = a0 + 1.0
            rect = pygame.Rect(x - r, y - r, r * 2, r * 2)
            pygame.draw.arc(surf, (255, 255, 255), rect, a0, a1, 4)
            pygame.draw.arc(surf, col, rect.inflate(-6, -6), a0 + 0.06,
                            a1 - 0.02, 2)

    def _floaters_particles(self, surf):
        for txt, col, x, y, t in self.floaters:
            a = max(0, int(255 * (1 - t / 0.9)))
            img = assets.get_font(26, True).render(txt, True, col)
            img.set_alpha(a)
            surf.blit(img, (int(x) - 10, int(y) - int(t * 46)))
        for p in self.particles:
            r = max(1, int(3 * p[5] / 0.7))
            surf.fill(p[4], (int(p[0]), int(p[1]), r, r))

    def _hud(self, surf):
        # party status panel
        panel = pygame.Rect(18, 396, 560, 116)
        assets.draw_panel(surf, panel)
        for i, (a, m) in enumerate(zip(self.actors_p, self.party.members)):
            rr = panel.y + 12 + i * 36
            assets.draw_text(surf, m.name, panel.x + 16, rr, 22,
                             PAL["amber"] if a.dead else PAL["text"],
                             bold=True)
            if a.dead:
                assets.draw_text(surf, "KO", panel.x + 96, rr, 22, PAL["red"],
                                 bold=True)
                continue
            assets.draw_text(surf, f"{m.hp:4d}/{m.maxhp:4d}",
                             panel.x + 96, rr, 20)
            assets.draw_text(surf, f"{m.mp:3d}", panel.x + 236, rr, 20,
                             PAL["cyan"])
            assets.draw_text(surf, "MP", panel.x + 214, rr + 1, 16,
                             PAL["text_dim"])
            barw = 150
            assets.draw_bar(surf, (panel.x + 300, rr + 4, barw, 14),
                            a.bar, PAL["amber"] if a.bar < 1 else
                            PAL["green"])
            if self.active is a and self.menu:
                continue
        # command menu
        if self.menu and self.active:
            self._menu_panel(surf, self.menu, self.menu_idx, panel.right + 18,
                             panel.y - 52)
        if self.submenu:
            kind, entries, idx = self.submenu
            labels = []
            for it in entries:
                if kind == "tech":
                    t = it
                    c = PAL["text"] if self.active.ref.mp >= t["mp"] \
                        else (150, 150, 160)
                    labels.append((f"{t['name']}  {t['mp']}MP", c))
                else:
                    iid, idef = it
                    count = self.game.party.inventory.get(iid, 0)
                    labels.append((f"{idef['name']} x{count}",
                                   PAL["text"]))
            rect = pygame.Rect(panel.right + 18, panel.y - 52, 260,
                               44 + 32 * len(labels))
            assets.draw_panel(surf, rect)
            if kind == "tech":
                assets.draw_text(surf, "TECH", rect.x + 20, rect.y + 12, 20,
                                 PAL["amber"], bold=True)
            else:
                assets.draw_text(surf, "ITEMS", rect.x + 20, rect.y + 12, 20,
                                 PAL["amber"], bold=True)
            for i, (lab, col) in enumerate(labels):
                y = rect.y + 44 + i * 32
                if i == idx:
                    assets.draw_arrow(surf, rect.x + 12, y + 5)
                assets.draw_text(surf, lab, rect.x + 34, y, 20, col)
        if self.targeting:
            kind, payload = self.targeting
            if kind in ("attack", "tech"):
                alives = self.alive_enemies()
                if alives:
                    self.target_idx %= len(alives)
                    a = alives[self.target_idx]
                    x, y = self.pos_of(a)
                    pts = [(x, y - 84), (x - 12, y - 104),
                           (x + 12, y - 104)]
                    pygame.draw.polygon(surf, PAL["amber"], pts)
                    name = payload["name"] if payload else "Attack"
                    assets.draw_text(surf, a.name + "  <-", x, y - 78, 24,
                                     PAL["amber"], align="center",
                                     bold=True)
            else:
                alives = self.alive_party()
                if alives:
                    self.target_idx %= len(alives)
                    a = alives[self.target_idx]
                    x, y = self.pos_of(a)
                    assets.draw_text(surf, "-> " + a.name, x - 10, y - 20, 24,
                                     PAL["green"], bold=True)

    def _menu_panel(self, surf, options, idx, x, y):
        rect = pygame.Rect(x, y, 190, 40 + 34 * len(options))
        assets.draw_panel(surf, rect)
        name = self.active.name if self.active else ""
        assets.draw_text(surf, name, rect.x + 20, rect.y + 10, 20,
                         PAL["amber"], bold=True)
        for i, o in enumerate(options):
            yy = rect.y + 40 + i * 34
            if i == idx:
                assets.draw_arrow(surf, rect.x + 16, yy + 6)
            assets.draw_text(surf, o, rect.x + 38, yy, 24)

    def _victory_panel(self, surf):
        lines = self.victory_msgs[:self.victory_idx + 1]
        rect = pygame.Rect(170, 120, WINW - 340, 120 + 30 * len(lines))
        assets.draw_panel(surf, rect)
        y = rect.y + 20
        for ln in lines:
            col = PAL["amber"] if "**" in ln or "VICTORY" in ln else PAL["text"]
            ln = ln.replace("**", "")
            assets.draw_text(surf, ln, rect.x + 30, y, 26, col, bold=True)
            y += 32
