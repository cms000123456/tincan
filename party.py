"""Party & character model, stat derivation, exp/level-ups."""

import math
import random

import data


def stat_at(base, growth, level):
    return int(base + growth * (level - 1))


class Character:
    def __init__(self, cid):
        self.id = cid
        d = data.CHARS[cid]
        self.name = d["name"]
        self.level = 1
        self.exp = 0
        self.weapon = d["weapon"]
        self.charm = None
        self.update_stats(final=True)
        self.hp = self.maxhp
        self.mp = self.maxmp
        self.sheet = None          # filled by game (sprite surfaces)
        self.portrait = None
        self.flash = 0.0

    # -- stat derivation ------------------------------------------------------
    def update_stats(self, final=False):
        d = data.CHARS[self.id]
        b, g = d["base"], d["growth"]
        self.maxhp = stat_at(b["hp"], g["hp"], self.level)
        self.maxmp = stat_at(b["mp"], g["mp"], self.level)
        self.base_atk = stat_at(b["atk"], g["atk"], self.level)
        self.base_dfn = stat_at(b["dfn"], g["dfn"], self.level)
        self.base_mag = stat_at(b["mag"], g["mag"], self.level)
        self.base_mdf = stat_at(b["mdf"], g["mdf"], self.level)
        self.spd = stat_at(b["spd"], g["spd"], self.level)
        if final:
            self.hp, self.mp = self.maxhp, self.maxmp
        else:
            self.hp = min(self.hp, self.maxhp)
            self.mp = min(self.mp, self.maxmp)

    def equip_bonus(self, key):
        v = 0
        for it in (self.weapon, self.charm):
            if it and it in data.ITEMS:
                v += data.ITEMS[it].get(key, 0)
        return v

    def atk(self):
        return self.base_atk + self.equip_bonus("atk")

    def dfn(self):
        return self.base_dfn + self.equip_bonus("dfn")

    def mag(self):
        return self.base_mag + self.equip_bonus("mag")

    def mdf(self):
        return self.base_mdf + self.equip_bonus("mdf")

    def known_techs(self):
        return [t for t in data.CHARS[self.id]["techs"] if t["lvl"] <= self.level]

    def next_tech(self):
        for t in data.CHARS[self.id]["techs"]:
            if t["lvl"] > self.level:
                return t
        return None

    def weapon_name(self):
        return data.ITEMS[self.weapon]["name"] if self.weapon else "fists"

    def charm_name(self):
        return data.ITEMS[self.charm]["name"] if self.charm else "-"

    # -- exp / leveling --------------------------------------------------------
    def exp_needed(self):
        return int(18 * math.pow(self.level, 1.9))

    def gain_exp(self, amount):
        """Returns list of level-up message strings."""
        msgs = []
        if amount <= 0:
            return msgs
        self.exp += amount
        while self.exp >= self.exp_needed():
            self.exp -= self.exp_needed()
            old = self.level
            old_maxhp, old_maxmp = self.maxhp, self.maxmp
            self.level += 1
            self.update_stats()
            self.hp += self.maxhp - old_maxhp
            self.mp += self.maxmp - old_maxmp
            msgs.append(f"** {self.name} reached level {self.level}! **")
            newtech = [t for t in data.CHARS[self.id]["techs"]
                       if t["lvl"] == self.level]
            if newtech:
                msgs.append(f"** {self.name} learned {newtech[0]['name']}! **")
            del old
        return msgs


class Party:
    def __init__(self):
        self.members = [Character(c) for c in ("kai", "nara", "vela")]
        self.gold = 30
        self.inventory = {"potion": 2}

    # -- helpers ---------------------------------------------------------------
    def alive(self):
        return [m for m in self.members if m.hp > 0]

    def all_alive(self):
        return all(m.hp > 0 for m in self.members)

    def leader(self):
        return self.members[0]

    def add_item(self, item_id, qty=1):
        self.inventory[item_id] = self.inventory.get(item_id, 0) + qty

    def take_item(self, item_id, qty=1):
        self.inventory[item_id] = self.inventory.get(item_id, 0) - qty
        if self.inventory[item_id] <= 0:
            del self.inventory[item_id]

    def has_item(self, item_id):
        return self.inventory.get(item_id, 0) > 0

    def autoequip(self, item_id):
        """Equip weapon for its intended owner if better. Returns name or None."""
        it = data.ITEMS.get(item_id)
        if not it or it["kind"] != "weapon":
            return None
        for m in self.members:
            if m.id == it["for_"]:
                cur = data.ITEMS.get(m.weapon, {})
                curpower = cur.get("atk", 0) + cur.get("mag", 0) * 0.7
                newpower = it.get("atk", 0) + it.get("mag", 0) * 0.7
                if newpower > curpower:
                    m.weapon = item_id
                    return f"{m.name} now wields the {it['name']}!"
        return None

    def apply_item(self, item_id, target, battle=False):
        """Consume item on target member. Returns text message (or None)."""
        it = data.ITEMS.get(item_id)
        if not it or it["kind"] != "item":
            return None
        parts = []
        if it.get("heal"):
            healed = min(target.maxhp - target.hp, it["heal"])
            target.hp += healed
            if healed:
                parts.append(f"{healed} HP")
        if it.get("mana"):
            got = min(target.maxmp - target.mp, it["mana"])
            target.mp += got
            if got:
                parts.append(f"{got} MP")
        if not parts:
            return None
        self.take_item(item_id)
        return f"{target.name} recovered " + " and ".join(parts) + "!"
