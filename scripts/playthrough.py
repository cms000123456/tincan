"""Full-story playthrough bot: plays all four chapters through the real game
loop (Game.step) using only key presses, then reports play time.

    python scripts/playthrough.py [--seed N] [--minimal] [--quiet]

--minimal skips up-front grinding (the bot only grinds after losing to a
boss), approximating a player who rushes the story.

The bot plans routes across maps (exits, doors, the ship), talks to NPCs,
opens key chests, shops for weapons and tonics, rests at crystals/inns,
grinds random encounters when under-levelled, fights with a simple tactic
(heal when low, techs on bosses/groups, otherwise attack the weakest) and
reloads its last save after a game over. Human-ish pauses are inserted for
reading dialogue and picking commands so the timing approximates a real
first playthrough. Headless (SDL dummy drivers).
"""
import collections
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import data  # noqa: E402
import game as game_mod  # noqa: E402
import save  # noqa: E402
import world as world_mod  # noqa: E402

DT = 1 / 60.0
FPS = 60

# human-ish pacing (frames)
READ_BASE, READ_PER_CHAR = 30, 0.9     # after a dialogue page is shown
THINK = 40                              # before acting on a battle command
KEY_GAP = 7                             # between menu key presses
VICTORY_GAP = 40                        # per victory-screen line


def fmt(frames):
    s = int(frames / FPS)
    return f"{s // 3600}h{(s % 3600) // 60:02d}m{s % 60:02d}s"


# ---------------------------------------------------------------------------
# Static map graph for route planning
# ---------------------------------------------------------------------------
def rows_of(mid):
    return getattr(data, mid.upper())


def static_ok(mid, x, y):
    rows = rows_of(mid)
    if not (0 <= y < len(rows) and 0 <= x < len(rows[0])):
        return False
    if rows[y][x] in world_mod.SOLIDS:
        return False
    m = data.MAPS[mid]
    if any((c["x"], c["y"]) == (x, y) for c in m["chests"]):
        return False
    if (x, y) in [tuple(c) for c in m.get("crystals", [])]:
        return False
    signs = m["signs"]
    if isinstance(signs, dict) and (x, y) in signs:
        return False
    for n in m["npcs"]:
        if n.get("wander", 0) == 0 and (n["x"], n["y"]) == (x, y):
            return False
    return True


DIRS = {(0, 1): "down", (0, -1): "up", (1, 0): "right", (-1, 0): "left"}


def plan_route(flags, start, goal_fn):
    """BFS over (map, x, y) with exits and the ship as edges.
    goal_fn(map, x, y) -> True at the goal. Returns list of states."""
    q = collections.deque([start])
    prev = {start: None}
    arrived = {start}       # standing on an exit you arrived by: walk off
    exits_by = {mid: {(e["x"], e["y"]): e for e in m["exits"]}
                for mid, m in data.MAPS.items()}
    while q:
        st = q.popleft()
        mid, x, y = st
        if goal_fn(mid, x, y):
            path = []
            while st is not None:
                path.append(st)
                st = prev[st]
            return path[::-1]
        nbrs = []
        ex = exits_by[mid].get((x, y))
        if ex and st not in arrived and ex["to"] in data.MAPS and \
                (not ex.get("req") or flags.get(ex["req"])):
            n = (ex["to"], ex["tx"], ex["ty"])
            if n not in prev:
                arrived.add(n)
            nbrs.append(n)
        else:
            for dx, dy in DIRS:
                nx, ny = x + dx, y + dy
                if static_ok(mid, nx, ny):
                    nbrs.append((mid, nx, ny))
            # the ship (interact from a neighbouring tile)
            sh = data.SHIPS.get(mid)
            if sh and abs(sh["x"] - x) + abs(sh["y"] - y) == 1:
                dests = [sh] + [a for a in data.SHIPS2.get(mid, {}).get(
                    "alts", []) if flags.get(a.get("req"))]
                for dst in dests:
                    n = (dst["to"], dst["tx"], dst["ty"])
                    if n not in prev:
                        arrived.add(n)
                    nbrs.append(n)
        for n in nbrs:
            if n not in prev:
                prev[n] = st
                q.append(n)
    return None


# ---------------------------------------------------------------------------
class Bot:
    def __init__(self, g, quiet=False):
        self.g = g
        self.quiet = quiet
        self.frames = 0
        self.wait = 0
        self.route = None
        self.route_key = None
        self.local_path = []
        self.battles = 0
        self.gameovers = 0
        self.min_level = {}          # goal key -> required level after a loss
        self.log_lines = []
        self.seen_battle = None
        self.plan = None
        self.stuck = 0
        self.last_pos = None

    def log(self, msg):
        line = f"[{fmt(self.frames)}] {msg}"
        self.log_lines.append(line)
        if not self.quiet:
            print(line, flush=True)

    # -- low-level ---------------------------------------------------------
    def step(self, pressed=frozenset(), held=frozenset()):
        self.g.step(DT, set(pressed), set(held))
        self.frames += 1

    @property
    def flags(self):
        return self.g.flags

    @property
    def ws(self):
        return self.g.world_scene

    def party_level(self):
        return min(m.level for m in self.g.party.members)

    def hp_frac(self):
        p = self.g.party.members
        return sum(m.hp for m in p) / sum(m.maxhp for m in p)

    # -- one frame of play -------------------------------------------------
    def frame(self, goal):
        """Advance one frame towards goal. Returns True if goal reached."""
        g = self.g
        sc = g.scene
        name = type(sc).__name__
        if self.wait > 0:
            self.wait -= 1
            self.step()
            return False
        if name == "TitleScene":
            self._title(sc)
            return False
        if name == "IntroScene":
            self.step({"a"})
            self.wait = READ_BASE
            return False
        if name == "BattleScene":
            self._battle(sc)
            return False
        if name == "EndingScene":
            self.step()
            return False
        if name != "WorldScene":
            self.step()
            return False
        ws = sc
        if ws.state == "dialog":
            self._dialog(ws.overlay)
            return False
        if ws.state == "choice":
            self._choice(ws.overlay, goal)
            return False
        if ws.state == "shop":
            self._shop(ws.overlay)
            return False
        if ws.state == "menu":
            self.step({"b"})
            return False
        if ws.state != "play":
            self.step()
            return False
        if goal.done(self):
            return True
        goal.act(self)
        return False

    # -- UI handlers -------------------------------------------------------
    def _title(self, sc):
        opts = sc.options()
        want = "Continue" if (self.gameovers and "Continue" in opts) \
            else "New Game"
        if opts[sc.opt_idx] != want:
            self.step({"down"})
            self.wait = KEY_GAP
        else:
            self.step({"a"})
            self.wait = 20

    def _dialog(self, box):
        if box is None:
            self.step()
            return
        page = box.pages[box.page_i] if box.page_i < len(box.pages) else ""
        if box.chars < len(page):
            self.step()                  # let it type out, like a reader
            return
        key = (id(box), box.page_i)
        if getattr(self, "_read", None) != key:
            self._read = key             # first sight: take time to read
            self.wait = int(READ_BASE + READ_PER_CHAR * len(page))
            self.step()
            return
        self.step({"a"})

    def _choice(self, ch, goal):
        want = getattr(goal, "choice", None)
        if any(o[1] == "ship" for o in ch.options):
            want = getattr(self, "goal_choice", None)
        idx = 0
        if want is not None:
            for i, o in enumerate(ch.options):
                if want in o[0]:
                    idx = i
        if ch.idx != idx:
            self.step({"down"})
            self.wait = KEY_GAP
        else:
            self.step({"a"})
            self.wait = 12

    def _shop(self, box):
        plan = getattr(self, "shop_plan", None)
        if not plan:
            self.step({"b"})
            self.wait = 12
            return
        iid = plan[0]
        idx = box.stock.index(iid)
        if box.idx != idx:
            self.step({"down"})
            self.wait = KEY_GAP
            return
        it = data.ITEMS[iid]
        if self.g.party.gold >= it["price"]:
            self.step({"a"})
            self.log(f"  bought {it['name']} ({self.g.party.gold} gil left)")
        plan.pop(0)
        self.wait = 14

    # -- battle ------------------------------------------------------------
    def _battle(self, sc):
        if sc is not self.seen_battle:
            self.seen_battle = sc
            self.battles += 1
            self.plan = None
            names = ", ".join(a.name for a in sc.actors_e)
            if sc.is_boss:
                self.log(f"BOSS BATTLE: {names} (party Lv "
                         f"{[m.level for m in self.g.party.members]})")
        if sc.phase == "victory":
            self.step({"a"})
            self.wait = VICTORY_GAP
            return
        if sc.phase == "gameover":
            self.gameovers += 1
            self.log(f"GAME OVER vs {', '.join(a.name for a in sc.actors_e)}"
                     " - reloading last save")
            self.on_gameover(sc)
            self.step({"a"})
            self.wait = 60
            return
        if sc.active is None or (sc.menu is None and sc.submenu is None and
                                 sc.targeting is None):
            self.step()
            return
        if self.plan is None or self.plan["actor"] is not sc.active:
            self.plan = self._decide(sc)
            self.wait = THINK
            self.step()
            return
        self._execute(sc)

    def _decide(self, sc):
        me = sc.active
        party = sc.alive_party()
        foes = sc.alive_enemies()
        weakest_foe = min(foes, key=lambda a: a.hp)
        low = [a for a in party if a.hp < a.maxhp * 0.45]
        dead_or_low = len(low)
        inv = self.g.party.inventory
        techs = sc._tech_entries(me)
        mp = me.ref.mp

        def tech(pred):
            ok = [t for t in techs if not t.get("combo") and mp >= t["mp"]
                  and pred(t)]
            return max(ok, key=lambda t: (t["mp"], t.get("power", 0))) \
                if ok else None
        # 1. heal
        if dead_or_low:
            if dead_or_low >= 2:
                t = tech(lambda t: t["kind"] == "heal" and t["target"] ==
                         "allies")
                if t:
                    return dict(actor=me, cmd="Tech", tech=t["name"])
            t = tech(lambda t: t["kind"] == "heal" and t["target"] == "ally")
            tgt = min(low, key=lambda a: a.hp / a.maxhp)
            if t:
                return dict(actor=me, cmd="Tech", tech=t["name"], ally=tgt)
            for iid in ("megapotion", "elixir", "hipotion", "potion"):
                if inv.get(iid) and tgt.hp < tgt.maxhp * 0.35:
                    return dict(actor=me, cmd="Item", item=iid, ally=tgt)
        # 2. techs on bosses / groups (keep healer MP in reserve)
        reserve = 6 if me.ref.id == "nara" else 0
        if sc.is_boss or len(foes) >= 2 or weakest_foe.hp > 120:
            if len(foes) >= 2:
                t = tech(lambda t: t["kind"] in ("mag", "phys") and
                         t["target"] == "enemies" and mp - t["mp"] >= reserve)
                if t:
                    return dict(actor=me, cmd="Tech", tech=t["name"])
            t = tech(lambda t: t["kind"] in ("mag", "phys") and
                     t["target"] == "enemy" and mp - t["mp"] >= reserve)
            if t and (sc.is_boss or weakest_foe.hp > 60):
                return dict(actor=me, cmd="Tech", tech=t["name"],
                            foe=weakest_foe)
        return dict(actor=me, cmd="Attack", foe=weakest_foe)

    def _press(self, key):
        self.step({key})
        self.wait = KEY_GAP

    def _execute(self, sc):
        p = self.plan
        if sc.menu is not None:
            want = sc.menu.index(p["cmd"])
            if sc.menu_idx != want:
                self._press("down")
            else:
                self._press("a")
            return
        if sc.submenu is not None:
            kind, entries, idx = sc.submenu
            key = p.get("tech") if kind == "tech" else p.get("item")
            names = [e["name"] if kind == "tech" else e[0] for e in entries]
            if key not in names:
                self._press("b")
                self.plan = dict(actor=p["actor"], cmd="Attack",
                                 foe=None)
                return
            want = names.index(key)
            self._press("down" if idx != want else "a")
            return
        if sc.targeting is not None:
            kind, _ = sc.targeting
            if kind in ("attack", "tech"):
                pool, tgt = sc.alive_enemies(), p.get("foe")
            else:
                pool, tgt = sc.alive_party(), p.get("ally")
            if not pool:
                self._press("b")
                return
            cur = pool[sc.target_idx % len(pool)]
            if tgt in pool and cur is not tgt:
                self._press("down")
            else:
                self._press("a")

    def on_gameover(self, sc):
        pass                          # hooked by the runner

    # -- world movement ------------------------------------------------------
    def pos(self):
        w = self.ws.world
        return (w.map_id, w.walker.gx, w.walker.gy)

    def walk_towards(self, goal_fn, key, interact_at=None):
        """Move one step along a planned route. interact_at=(x, y) on the
        final map means: stand next to it, face it, press A."""
        w = self.ws.world
        walker = w.walker
        if walker.moving:
            self.step()
            return
        here = self.pos()
        if self.route is None or self.route_key != key or here not in \
                self.route:
            self.route = plan_route(self.flags, here, goal_fn)
            self.route_key = key
            if self.route is None:
                raise RuntimeError(f"no route for {key} from {here}")
        i = self.route.index(here)
        if i == len(self.route) - 1:
            if interact_at:
                tx, ty = interact_at
                d = DIRS.get((tx - here[1], ty - here[2]))
                if d and walker.face != d:
                    self.step(held={d})      # turn in place (blocked)
                    self.step()
                    return
                self.step({"a"})
                self.wait = 6
            else:
                self.step()
            return
        nxt = self.route[i + 1]
        if nxt[0] != here[0]:
            # map change from here: either the ship or a step onto an exit
            sh = data.SHIPS.get(here[0])
            alts = data.SHIPS2.get(here[0], {}).get("alts", [])
            if sh and (nxt[0] == sh["to"] or
                       any(a["to"] == nxt[0] for a in alts)):
                self.goal_choice = "Wreck" if nxt[0] == sh["to"] else next(
                    a["label"] for a in alts if a["to"] == nxt[0])
                d = DIRS[(sh["x"] - here[1], sh["y"] - here[2])]
                if walker.face != d:
                    self.step(held={d})
                    self.step()
                else:
                    self.step({"a"})
                    self.wait = 6
                return
            self.step()
            return
        d = DIRS[(nxt[1] - here[1], nxt[2] - here[2])]
        if not w.step_ok(nxt[1], nxt[2]):
            # dynamic blocker (NPC / monster): wait a moment, then re-plan
            self.stuck += 1
            if self.stuck > 40:
                self.route = None
                self.stuck = 0
                # sidestep randomly to break deadlocks
                d = random.choice(list(DIRS.values()))
            else:
                self.step()
                return
        self.step(held={d})


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------
class Goal:
    choice = None

    def __init__(self, label):
        self.label = label

    def done(self, bot):
        return False

    def act(self, bot):
        bot.step()


class TalkTo(Goal):
    def __init__(self, label, mid, npc_id, until):
        super().__init__(label)
        self.mid, self.npc_id, self.until = mid, npc_id, until

    def done(self, bot):
        return self.until(bot)

    def _npc(self, bot):
        w = bot.ws.world
        if w.map_id != self.mid:
            return None
        return next((n for n in w.npcs if n.id == self.npc_id), None)

    def act(self, bot):
        n = self._npc(bot)
        if n is None:
            d = next(d for d in data.MAPS[self.mid]["npcs"]
                     if d["id"] == self.npc_id)
            tx, ty = d["x"], d["y"]
        else:
            tx, ty = n.x, n.y
        rows = rows_of(self.mid)

        def near(mid, x, y):
            if mid != self.mid:
                return False
            if abs(x - tx) + abs(y - ty) == 1:
                return True
            # talk across a counter
            for dx, dy in DIRS:
                if (x + dx, y + dy) != (tx, ty) and \
                        world_mod.tile_at(rows, x + dx, y + dy) == "c" and \
                        (x + 2 * dx, y + 2 * dy) == (tx, ty):
                    return True
            return False
        here = bot.pos()
        target = (tx, ty)
        if here[0] == self.mid:
            for dx, dy in DIRS:
                if world_mod.tile_at(rows, here[1] + dx, here[2] + dy) == "c" \
                        and (here[1] + 2 * dx, here[2] + 2 * dy) == (tx, ty):
                    target = (here[1] + dx, here[2] + dy)
        bot.walk_towards(near, ("talk", self.npc_id, tx, ty),
                         interact_at=target)


class Interact(Goal):
    """Face a fixed tile (chest / crystal) and press A."""

    def __init__(self, label, mid, xy, until):
        super().__init__(label)
        self.mid, self.xy, self.until = mid, tuple(xy), until

    def done(self, bot):
        return self.until(bot)

    def act(self, bot):
        tx, ty = self.xy
        bot.walk_towards(
            lambda m, x, y: m == self.mid and abs(x - tx) + abs(y - ty) == 1,
            ("int", self.mid, tx, ty), interact_at=self.xy)


class Kill(Goal):
    def __init__(self, label, mid, ent_id):
        super().__init__(label)
        self.mid, self.ent_id = mid, ent_id

    def done(self, bot):
        return self.ent_id in bot.flags.get("slain", {})

    def act(self, bot):
        w = bot.ws.world
        mo = None
        if w.map_id == self.mid:
            mo = next((m for m in w.monsters if m.id == self.ent_id), None)
        if mo is None:
            d = next(d for d in data.ENTITIES[self.mid]
                     if d["id"] == self.ent_id)
            tx, ty = d["pos"]
        else:
            tx, ty = mo.x, mo.y
        bot.walk_towards(
            lambda m, x, y: m == self.mid and abs(x - tx) + abs(y - ty) <= 1,
            ("kill", self.ent_id, tx, ty), interact_at=(tx, ty))


class GoTo(Goal):
    def __init__(self, label, mid, xy=None):
        super().__init__(label)
        self.mid, self.xy = mid, xy

    def done(self, bot):
        here = bot.pos()
        return here[0] == self.mid and (self.xy is None or
                                        tuple(here[1:]) == tuple(self.xy))

    def act(self, bot):
        bot.walk_towards(
            lambda m, x, y: m == self.mid and
            (self.xy is None or (x, y) == tuple(self.xy)),
            ("goto", self.mid, self.xy))


class Grind(Goal):
    """Pace up and down tall grass on `mid` until the party reaches `level`."""

    def __init__(self, label, mid, level_fn):
        super().__init__(label)
        self.mid, self.level_fn = mid, level_fn
        self.spot = None
        self.flip = False

    def done(self, bot):
        return bot.party_level() >= self.level_fn(bot) and self.rest is None

    rest = None

    def act(self, bot):
        if self.rest is None and (bot.hp_frac() < 0.45 or any(
                m.hp == 0 for m in bot.g.party.members)):
            self.rest = Rest("  (rest while grinding)")
            bot.log("  party is worn out - heading back to rest")
        if self.rest is not None:
            if self.rest.done(bot):
                self.rest = None
                self.spot = None
            else:
                self.rest.act(bot)
                return
        rows = rows_of(self.mid)
        if self.spot is None:
            here = bot.pos()
            cand = [(x, y) for y, r in enumerate(rows) for x, c in
                    enumerate(r) if c == "," and
                    world_mod.tile_at(rows, x + 1, y) == ","]
            # nearest reachable grass pair from where we entered
            path = plan_route(bot.flags, here,
                              lambda m, x, y: m == self.mid and (x, y) in
                              set(cand))
            self.spot = path[-1][1:] if path else cand[0]
        x0, y0 = self.spot
        tgt = (x0 + (1 if self.flip else 0), y0)
        here = bot.pos()
        if here == (self.mid, *tgt):
            self.flip = not self.flip
            tgt = (x0 + (1 if self.flip else 0), y0)
        bot.walk_towards(lambda m, x, y: m == self.mid and (x, y) == tgt,
                         ("grind", tgt))


class Explore(Goal):
    """Open every chest on a map, nearest first (like a thorough player)."""

    def __init__(self, label, mid):
        super().__init__(label)
        self.mid = mid
        self.cur = None

    def _left(self, bot):
        opened = bot.flags["opened_chests"]
        return [c for c in data.MAPS[self.mid]["chests"]
                if c["id"] not in opened]

    def done(self, bot):
        return not self._left(bot)

    def act(self, bot):
        left = self._left(bot)
        if self.cur is None or self.cur["id"] not in [c["id"] for c in left]:
            here = bot.pos()
            self.cur = min(left, key=lambda c: abs(c["x"] - here[1]) +
                           abs(c["y"] - here[2]))
            self.sub = Interact("", self.mid, (self.cur["x"], self.cur["y"]),
                                lambda b: False)
        self.sub.act(bot)


class Hunt(Grind):
    """Fight in a field until `eid` has been defeated `n` times."""

    def __init__(self, label, mid, eid, n):
        super().__init__(label, mid, lambda b: 0)
        self.eid, self.n = eid, n

    def done(self, bot):
        return bot.flags.get("kills", {}).get(self.eid, 0) >= self.n and \
            self.rest is None


class Rest(Goal):
    """Full heal at the nearest crystal (or inn) - also saves the game."""
    choice = "Rest"

    def __init__(self, label, prefer=None):
        super().__init__(label)
        self.prefer = prefer
        self.target = None
        self.t0 = None

    def done(self, bot):
        if self.t0 is None:              # must save from *this* visit on
            self.t0 = time.time() - 0.01
        full = all(m.hp == m.maxhp and m.mp == m.maxmp
                   for m in bot.g.party.members)
        try:
            saved = os.path.getmtime(save.SAVE_PATH) >= self.t0
        except OSError:
            saved = False
        return full and saved

    def act(self, bot):
        here = bot.pos()
        if self.target is None:
            spots = set()
            for mid, m in data.MAPS.items():
                for c in m.get("crystals", []):
                    spots.add((mid, tuple(c)))
            best = plan_route(bot.flags, here, lambda m, x, y: any(
                m == sm and abs(x - sx) + abs(y - sy) == 1
                for sm, (sx, sy) in spots))
            end = best[-1]
            self.target = next((sm, s) for sm, s in spots
                               if sm == end[0] and
                               abs(end[1] - s[0]) + abs(end[2] - s[1]) == 1)
        mid, (sx, sy) = self.target
        bot.walk_towards(
            lambda m, x, y: m == mid and abs(x - sx) + abs(y - sy) == 1,
            ("rest", mid, sx, sy), interact_at=(sx, sy))


class Shop(Goal):
    def __init__(self, label, mid, npc_id, wish):
        super().__init__(label)
        self.talk = TalkTo(label, mid, npc_id, lambda b: False)
        self.wish = wish
        self.started = False
        self.finished = False

    def done(self, bot):
        if self.started and bot.ws.state == "play" and \
                not getattr(bot, "shop_plan", None):
            self.finished = True
        return self.finished

    def act(self, bot):
        if not self.started:
            bot.shop_plan = self.wish(bot)
            if not bot.shop_plan:
                self.finished = True
                return
            self.started = True
        self.talk.act(bot)


def weapon_wish(stock_key, tonics=("potion", 6), reserve=0):
    """Buy each member's best affordable upgrade, then tonics."""
    def wish(bot):
        p = bot.g.party
        gold = p.gold - reserve
        buys = []
        stock = data.SHOP_STOCKS[stock_key]
        for m in p.members:
            cur = data.ITEMS.get(m.weapon, {})
            score = (cur.get("atk") or 0) + (cur.get("mag") or 0)
            best = None
            for iid in stock:
                it = data.ITEMS[iid]
                if it["kind"] != "weapon" or it.get("for_") != m.id:
                    continue
                s = (it.get("atk") or 0) + (it.get("mag") or 0)
                if s > score and it["price"] <= gold:
                    best, score = iid, s
            if best:
                buys.append(best)
                gold -= data.ITEMS[best]["price"]
        iid, n = tonics
        have = p.inventory.get(iid, 0)
        price = data.ITEMS[iid]["price"]
        for _ in range(max(0, n - have)):
            if gold >= price:
                buys.append(iid)
                gold -= price
        # buy in stock order so the cursor only ever moves down
        buys.sort(key=lambda i: stock.index(i))
        return buys
    return wish


# ---------------------------------------------------------------------------
GRIND_TARGETS = {"ch1": 4, "ch2": 9, "ch3": 14, "ch4": 18}


def story(side=False):
    f = lambda k: (lambda b: k in b.flags)  # noqa: E731
    T = GRIND_TARGETS
    G = []
    # Chapter 1 -----------------------------------------------------------
    G += [("Chapter 1", None)]
    G += [(None, TalkTo("Talk to Elder Bram", "elder_home", "elder",
                        f("met_elder"))),
          (None, Shop("Shop: Rusty Nail", "shop", "shopkeep",
                      weapon_wish("shop", ("potion", 6)))),
          (None, Grind("Grind on Cinder Road", "overworld",
                       lambda b: b.min_level.get("ch1", T["ch1"]))),
          (None, Rest("Rest at the cavern crystal")),
          (None, Kill("Defeat GEARLORD VX", "cavern", "boss")),
          (None, TalkTo("Report to Elder Bram", "elder_home", "elder",
                        f("reward_given")))]
    # Chapter 2 -----------------------------------------------------------
    G += [("Chapter 2", None)]
    G += [(None, Shop("Shop: Rusty Nail (upgrades)", "shop", "shopkeep",
                      weapon_wish("shop", ("potion", 8)))),
          (None, TalkTo("Meet Captain Row", "ember_port", "captain",
                        f("met_row"))),
          (None, Shop("Shop: Anchor & Anvil", "ember_arms", "arms_ember",
                      weapon_wish("ember_arms", ("hipotion", 4)))),
          (None, Grind("Grind on the coast road", "east_road",
                       lambda b: b.min_level.get("ch2", T["ch2"]))),
          (None, Rest("Rest before the wreck")),
          (None, GoTo("Sail to the Umbra Wreck", "umbra_wreck")),
          (None, Interact("Find Marla's lantern", "umbra_wreck", (25, 2),
                          lambda b: "w_lantern" in
                          b.flags["opened_chests"])),
          (None, Rest("Rest in the wreck")),
          (None, Kill("Defeat CAPTAIN RUSTHOOK", "umbra_wreck", "wboss")),
          (None, TalkTo("Return the lantern to Marla", "ember_port",
                        "marla", f("q_lantern")))]
    # Chapter 3 -----------------------------------------------------------
    G += [("Chapter 3", None)]
    G += [(None, Shop("Shop: Anchor & Anvil (upgrades)", "ember_arms",
                      "arms_ember", weapon_wish("ember_arms",
                                                ("hipotion", 6)))),
          (None, TalkTo("Meet Warden Lumi", "frostline", "elder_frost",
                        f("met_lumi"))),
          (None, Shop("Shop: Glacier Goods", "frost_shop", "arms_frost",
                      weapon_wish("frost_shop", ("hipotion", 6)))),
          (None, Grind("Grind in the snowfields", "east_road",
                       lambda b: b.min_level.get("ch3", T["ch3"]))),
          (None, Rest("Rest before the vault")),
          (None, GoTo("Enter the Glacial Vault", "glacial_vault")),
          (None, Rest("Rest in the vault")),
          (None, Kill("Defeat RIME COLOSSUS", "glacial_vault", "gboss"))]
    # Chapter 4 -----------------------------------------------------------
    G += [("Chapter 4", None)]
    G += [(None, Shop("Shop: Glacier Goods (upgrades)", "frost_shop",
                      "arms_frost", weapon_wish("frost_shop",
                                                ("hipotion", 8)))),
          (None, Grind("Grind in the snowfields", "east_road",
                       lambda b: b.min_level.get("ch4", T["ch4"]))),
          (None, Rest("Rest before the bastion")),
          (None, GoTo("Through the Aether Gate", "sky_bastion")),
          (None, Rest("Rest in the bastion")),
          (None, Kill("Defeat ARCHON PRIME", "sky_bastion", "aboss"))]
    G += act2()
    return G


def act2():
    import chapters
    f = lambda k: (lambda b: k in b.flags)  # noqa: E731
    G = []
    for c in chapters.CH:
        key, n = c["key"], c["n"]
        G += [(f"Chapter {n}", None)]
        G += [(None, TalkTo(f"Meet {c['leader'][0]} in {c['town']}",
                            f"{key}_town", f"{key}_leader", f(f"met_{key}"))),
              (None, Shop(f"Shop: {c['town']}", f"{key}_shop",
                          f"{key}_shop_k", weapon_wish(f"{key}_shop",
                                                       ("megapotion", 6)))),
              (None, Grind(f"Grind in the {c['region']}", f"{key}_field",
                           lambda b, k=f"ch{n}", L=c["level"]:
                           b.min_level.get(k, GRIND_TARGETS.get(
                               k, L - 3)))),
              (None, Kill("Hunt the elite pack", f"{key}_field",
                          f"{key}_elite")),
              (None, Rest(f"Rest before the {c['dungeon']}"))]
        for fl in range(1, chapters.FLOORS + 1):
            mid = f"{key}_d{fl}"
            G += [(None, GoTo(f"{c['dungeon']} {fl}F", mid)),
                  (None, Explore(f"Search {fl}F for treasure", mid))]
            if fl == 2:
                G += [(None, Rest("Rest at the crystal"))]
        G += [(None, Rest("Rest before the boss")),
              (None, Kill(f"Defeat {chapters.NAMES[c['boss']]}",
                          f"{key}_d{chapters.FLOORS}", f"{key}_boss")),
              (None, Hunt(f"Bounty: {chapters.NAMES[c['enemies'][0]]}",
                          f"{key}_field", c["enemies"][0], 8)),
              (None, TalkTo("Claim the bounty", f"{key}_town",
                            f"{key}_hunter", f(f"q_{key}_bounty"))),
              (None, TalkTo("Report the elite pack", f"{key}_town",
                            f"{key}_scout", f(f"q_{key}_elite"))),
              (None, TalkTo("Return the heirloom", f"{key}_town",
                            f"{key}_elder", f(f"q_{key}_relic"))),
              (None, TalkTo("Star Fragments to the smith", f"{key}_town",
                            f"{key}_smith", f(f"q_{key}_smith")))]
    G += [("Chapter 10", None)]
    G += [(None, Grind("Grind before the Orrery", "gear_field",
                       lambda b: b.min_level.get("ch10", GRIND_TARGETS.get(
                           "ch10", 29)))),
          (None, Rest("Rest before the Orrery"))]
    for fl in range(1, chapters.ORRERY_FLOORS + 1):
        mid = f"orrery_{fl}"
        G += [(None, GoTo(f"Astral Orrery {fl}F", mid)),
              (None, Explore(f"Search {fl}F", mid))]
        if fl == 3:
            G += [(None, Rest("Rest before the Guardian")),
                  (None, Kill("Defeat the ORRERY GUARDIAN", mid,
                              "orrery_guardian"))]
    G += [(None, Rest("Rest before the Clockmaker")),
          (None, Kill("Defeat THE CLOCKMAKER",
                      f"orrery_{chapters.ORRERY_FLOORS}", "clockmaker"))]
    return G


def _chest_xy(mid, cid):
    return next((c["x"], c["y"]) for c in data.MAPS[mid]["chests"]
                if c["id"] == cid)


def main():
    args = sys.argv[1:]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 7
    quiet = "--quiet" in args
    if "--minimal" in args:
        # no up-front grinding: only grind after a boss wins
        for n in range(1, 11):
            GRIND_TARGETS[f"ch{n}"] = 1
    random.seed(seed)
    if os.path.exists(save.SAVE_PATH):
        os.remove(save.SAVE_PATH)
    g = game_mod.Game(headless=True)
    bot = Bot(g, quiet=quiet)
    plan = story()
    chapter, chapter_start, splits = None, 0, []
    cur_key = {f"Chapter {n}": f"ch{n}" for n in range(1, 11)}
    t0 = time.time()
    i = 0

    def gameover_hook(sc):
        # reload the last save and redo the chapter's grind with a higher
        # target; completed goals finish instantly (they check flags)
        nonlocal i, plan
        k = cur_key[chapter]
        bot.min_level[k] = max(bot.min_level.get(k, 0),
                               bot.party_level() + 2)
        bot.log(f"  -> will grind to Lv {bot.min_level[k]} before retrying")
        j = max(n for n in range(i + 1) if isinstance(plan[n][1], Grind))
        plan = story()
        i = j
    bot.on_gameover = gameover_hook

    # title + intro
    while type(g.scene).__name__ != "WorldScene":
        bot.frame(Goal("boot"))
    MAX_FRAMES = 60 * 60 * 60 * 12         # 12 hours of game time
    goal_start = bot.frames
    while i < len(plan) and bot.frames < MAX_FRAMES and \
            "game_clear" not in g.flags:
        head, goal = plan[i]
        if head:
            if chapter:
                splits.append((chapter, bot.frames - chapter_start))
                bot.log(f"=== {chapter} complete in "
                        f"{fmt(bot.frames - chapter_start)} ===")
            chapter, chapter_start = head, bot.frames
            bot.log(f"=== {chapter} ===")
            i += 1
            continue
        if not getattr(goal, "_announced", False):
            goal._announced = True
            bot.log(f"-> {goal.label}")
        if isinstance(goal, (Rest,)):
            bot.goal_choice = "Rest"
        if bot.frames - goal_start > 45 * 60 * FPS:
            bot.log(f"STUCK (watchdog): '{goal.label}' ran 45 game-minutes"
                    " - skipping it")
            i += 1
            goal_start = bot.frames
            continue
        try:
            if bot.frame(goal):
                i += 1
                goal_start = bot.frames
        except RuntimeError as e:
            bot.log(f"STUCK: {e}")
            break
    splits.append((chapter, bot.frames - chapter_start))
    ok = "game_clear" in g.flags
    print()
    print("=" * 56)
    print("PLAYTHROUGH", "COMPLETE" if ok else "INCOMPLETE")
    for ch, fr in splits:
        print(f"  {ch:10s} {fmt(fr)}")
    print(f"  {'TOTAL':10s} {fmt(bot.frames)}  (in-game clock "
          f"{fmt(int(g.play_time * FPS))})")
    print(f"  battles {bot.battles}, game overs {bot.gameovers}, "
          f"final levels {[m.level for m in g.party.members]}, "
          f"gold {g.party.gold}")
    print(f"  simulated in {time.time() - t0:.0f}s wall time")
    flags = sorted(k for k in g.flags if k.startswith(("shard", "q_", "met",
                                                         "reward")))
    print(f"  flags: {flags}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
