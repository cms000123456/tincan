"""In-world pause menu: Items / Status / Quest / Save / Close."""

import pygame

import assets
import data
from settings import PAL, WINW, WINH


class MenuOverlay:
    def __init__(self, game):
        self.game = game
        self.mode = "root"      # root | items | pick | status | quest
        self.idx = 0
        self.item_idx = 0
        self.member_idx = 0
        self.selected_item = None
        self.done = False
        self.note = None
        self.note_t = 0.0

    def flash(self, text):
        self.note = text
        self.note_t = 1.6

    def update(self, dt, pressed):
        if self.note_t > 0:
            self.note_t -= dt
        if self.mode == "root":
            opts = 6
            if "up" in pressed:
                self.idx = (self.idx - 1) % opts
                self.game.audio.sfx("cursor")
            if "down" in pressed:
                self.idx = (self.idx + 1) % opts
                self.game.audio.sfx("cursor")
            if "b" in pressed:
                self.done = True
                self.game.audio.sfx("cancel")
            if "a" in pressed:
                self.game.audio.sfx("confirm")
                if self.idx == 0:
                    self.mode = "items"
                    self.item_idx = 0
                elif self.idx == 1:
                    self.mode = "status"
                    self.member_idx = 0
                elif self.idx == 2:
                    self.mode = "quest"
                elif self.idx == 3:
                    self.mode = "equip"
                    self.member_idx = 0
                elif self.idx == 4:
                    import save
                    save.save_game(self.game)
                    self.flash("Game saved!")
                    self.game.audio.sfx("save")
                else:
                    self.done = True
        elif self.mode == "items":
            items = [(k, data.ITEMS[k]) for k in sorted(
                self.game.party.inventory)]
            n = max(1, len(items))
            if "up" in pressed and items:
                self.item_idx = (self.item_idx - 1) % n
                self.game.audio.sfx("cursor")
            if "down" in pressed and items:
                self.item_idx = (self.item_idx + 1) % n
                self.game.audio.sfx("cursor")
            if "b" in pressed:
                self.mode = "root"
                self.game.audio.sfx("cancel")
            if "a" in pressed and items:
                k, idef = items[self.item_idx % len(items)]
                self.selected_item = k
                self.mode = "pick"
                self.member_idx = 0
                self.game.audio.sfx("confirm")
        elif self.mode == "pick":
            n = len(self.game.party.members)
            if "up" in pressed:
                self.member_idx = (self.member_idx - 1) % n
                self.game.audio.sfx("cursor")
            if "down" in pressed:
                self.member_idx = (self.member_idx + 1) % n
                self.game.audio.sfx("cursor")
            if "b" in pressed:
                self.mode = "items"
                self.game.audio.sfx("cancel")
            if "a" in pressed:
                m = self.game.party.members[self.member_idx]
                k = self.selected_item
                it = data.ITEMS[k]
                if it.get("heal") and m.hp >= m.maxhp or \
                        it.get("mana") and m.mp >= m.maxmp:
                    self.flash("No effect...")
                elif m.hp <= 0:
                    self.flash(f"{m.name} is out cold...")
                else:
                    txt = self.game.party.apply_item(k, m)
                    self.game.audio.sfx("heal")
                    self.flash(txt or "...")
                self.mode = "items"
        elif self.mode == "equip":
            if "b" in pressed:
                self.mode = "root"
                self.game.audio.sfx("cancel")
            if "left" in pressed or "up" in pressed:
                self.slot = 1 - getattr(self, "slot", 0)
                self.game.audio.sfx("cursor")
            if "right" in pressed or "down" in pressed:
                self.slot = 1 - getattr(self, "slot", 0)
                self.game.audio.sfx("cursor")
            if "a" in pressed:
                self.mode = "equip_list"
                self.item_idx = 0
                self.game.audio.sfx("confirm")
        elif self.mode == "equip_list":
            cands = self._equip_candidates()
            if "b" in pressed:
                self.mode = "equip"
                self.game.audio.sfx("cancel")
            if cands:
                n = len(cands)
                if "up" in pressed:
                    self.item_idx = (self.item_idx - 1) % n
                    self.game.audio.sfx("cursor")
                if "down" in pressed:
                    self.item_idx = (self.item_idx + 1) % n
                    self.game.audio.sfx("cursor")
            if "a" in pressed and cands:
                iid = cands[self.item_idx % len(cands)][0]
                m2 = self.game.party.members[self.member_idx]
                if iid == "(none)":
                    slot = "weapon" if self.slot == 0 else "charm"
                    setattr(m2, slot, None)
                    self.flash("Unequipped.")
                else:
                    setattr(m2, "weapon" if self.slot == 0 else "charm",
                            iid)
                    self.flash(f"Equipped: {data.ITEMS[iid]['name']}!")
                self.game.audio.sfx("confirm")
                self.mode = "equip"
        elif self.mode in ("status", "quest"):
            if "b" in pressed or "a" in pressed:
                if self.mode == "status" and "a" in pressed:
                    self.member_idx = (self.member_idx + 1) % 3
                    self.game.audio.sfx("cursor")
                else:
                    self.mode = "root"
                    self.game.audio.sfx("cancel")

    def draw(self, surf):
        p = self.game.party
        assets.draw_panel(surf, (30, 60, 280, 320))
        y = 80
        for i, label in enumerate(["Items", "Status", "Quest", "Equip",
                                   "Save", "Close"]):
            if self.mode == "root" and i == self.idx:
                assets.draw_arrow(surf, 48, y - 9)
                assets.draw_text(surf, label, 66, y - 12, 28, PAL["amber"],
                                 bold=True)
            else:
                assets.draw_text(surf, label, 66, y - 12, 28,
                                 PAL["text"] if self.mode == "root"
                                 else PAL["text_dim"])
            y += 46
        assets.draw_text(surf, f"Gold: {p.gold}", 48, 350, 26, PAL["amber"])
        # party glance (right column)
        assets.draw_panel(surf, (330, 60, 260, 320))
        for i, m in enumerate(p.members):
            yy = 150 + i * 80
            img = m.sheet.get(("down", "idle"))
            if img:
                surf.blit(img, (348, yy - 20))
            col = PAL["text"] if m.hp > 0 else PAL["red"]
            if self.mode in ("status",) and i == self.member_idx:
                col = PAL["amber"]
                assets.draw_arrow(surf, 336, yy - 10)
            assets.draw_text(surf, m.name, 376, yy - 16, 24, col, bold=True)
            assets.draw_text(surf, f"HP {m.hp:4d}/{m.maxhp:4d}", 376, yy + 8,
                             18)
            assets.draw_text(surf, f"MP {m.mp:3d}/{m.maxmp:3d}", 376, yy + 30,
                             18, PAL["cyan"])

        if self.mode == "items":
            self._list_panel(surf, "ITEMS",
                             [(data.ITEMS[k]["name"],
                               f"x{p.inventory.get(k, 0)}",
                               data.ITEMS[k].get("desc", ""))
                              for k in sorted(p.inventory)])
            if self.mode == "pick":
                self._pick_panel(surf)
        elif self.mode == "status":
            self._status_panel(surf)
        elif self.mode == "quest":
            self._quest_panel(surf)
        elif self.mode == "equip":
            self._equip_panel(surf)
        elif self.mode == "equip_list":
            self._equip_panel(surf)
            self._equip_list_panel(surf)
        if self.note and self.note_t > 0:
            rect = pygame.Rect(340, 380, 420, 44)
            assets.draw_panel(surf, rect)
            assets.draw_text(surf, self.note, 356, rect.y + 10, 24,
                             PAL["amber"])

    def _list_panel(self, surf, title, entries):
        rect = pygame.Rect(WINW // 2 - 90, 60, 300,
                           100 + 34 * max(1, len(entries)))
        assets.draw_panel(surf, rect)
        assets.draw_text(surf, title, rect.x + 18, rect.y + 12, 24,
                         PAL["amber"], bold=True)
        if not entries:
            assets.draw_text(surf, "(nothing)", rect.x + 24, rect.y + 56, 22,
                             PAL["text_dim"])
            return
        for i, (name, right, _desc) in enumerate(entries):
            y = rect.y + 50 + i * 34
            sel = self.mode == "items" and i == self.item_idx
            if sel:
                assets.draw_arrow(surf, rect.x + 12, y - 4)
            assets.draw_text(surf, name, rect.x + 34, y - 6, 22,
                             PAL["amber"] if sel else PAL["text"])
            assets.draw_text(surf, right, rect.right - 20, y - 6, 22,
                             PAL["text_dim"], align="right")
        if self.mode == "items":
            k = sorted(self.game.party.inventory)[
                self.item_idx % len(entries)]
            it = data.ITEMS[k]
            assets.draw_text(surf, it.get("desc", ""), rect.x + 20,
                             rect.bottom - 36, 20, PAL["text_dim"])

    def _pick_panel(self, surf):
        rect = pygame.Rect(WINW // 2 - 90, 60, 300, 100)
        assets.draw_panel(surf, rect)
        assets.draw_text(surf, "USE ON:", rect.x + 18, rect.y + 12, 24,
                         PAL["amber"], bold=True)
        for i, m in enumerate(self.game.party.members):
            y = rect.y + 50 + i * 30
            assets.draw_text(surf, m.name, rect.x + 40, y, 22,
                             PAL["amber"] if i == self.member_idx
                             else PAL["text"])

    def _status_panel(self, surf):
        m = self.game.party.members[self.member_idx]
        rect = pygame.Rect(WINW // 2 - 200, 110, 560, 340)
        assets.draw_panel(surf, rect)
        assets.draw_text(surf, m.name, rect.x + 20, rect.y + 12, 26,
                         PAL["amber"], bold=True)
        img = m.portrait
        if img:
            surf.blit(img, (rect.x + 20, rect.y + 44))
        cols = [
            ("LV", str(m.level)),
            ("HP", f"{m.hp}/{m.maxhp}"),
            ("MP", f"{m.mp}/{m.maxmp}"),
            ("ATK", str(m.atk())),
            ("DEF", str(m.dfn())),
            ("MAG", str(m.mag())),
            ("MDF", str(m.mdf())),
            ("SPD", str(m.spd)),
        ]
        yy = rect.y + 20
        for i, (k, v) in enumerate(cols):
            if i % 2 == 0:
                yy += 24
            x = rect.x + 140 + (i % 2) * 200
            assets.draw_text(surf, k, x, yy, 20, PAL["text_dim"])
            assets.draw_text(surf, v, x + 60, yy, 20)
        for k, v in (("Weapon", m.weapon_name()), ("Charm", m.charm_name())):
            yy += 24
            assets.draw_text(surf, k, rect.x + 140, yy, 20, PAL["text_dim"])
            assets.draw_text(surf, v, rect.x + 240, yy, 20)
        techs = m.known_techs()
        ty = yy + 34
        assets.draw_text(surf, "Techs:", rect.x + 20, ty, 20,
                         PAL["text_dim"])
        ty += 24
        for i, t in enumerate(techs):
            assets.draw_text(surf, f"{t['name']} ({t['mp']}MP)",
                             rect.x + 34 + (i % 2) * 260,
                             ty + (i // 2) * 22, 20)
        nt = m.next_tech()
        if nt:
            assets.draw_text(surf, f"Next: {nt['name']} at LV {nt['lvl']}",
                             rect.x + 20, rect.bottom - 30, 18,
                             PAL["text_dim"])

    def _equip_candidates(self):
        m = self.game.party.members[self.member_idx]
        out = []
        if self.slot == 0:
            for iid, it in data.ITEMS.items():
                if it["kind"] == "weapon" and it.get("for_") == m.id:
                    out.append((iid, it))
        else:
            for iid, it in data.ITEMS.items():
                if it["kind"] == "charm":
                    out.append((iid, it))
        out.sort(key=lambda t: -(t[1].get("atk", 0) + t[1].get("mag", 0) +
                                 t[1].get("dfn", 0) + t[1].get("mdf", 0)))
        return out

    def _equip_panel(self, surf):
        m = self.game.party.members[self.member_idx]
        rect = pygame.Rect(WINW // 2 - 40, 80, 420, 300)
        assets.draw_panel(surf, rect)
        assets.draw_text(surf, f"EQUIP - {m.name}", rect.x + 20,
                         rect.y + 12, 26, PAL["amber"], bold=True)
        slots = [("Weapon", m.weapon), ("Charm", m.charm)]
        for i, (label, iid) in enumerate(slots):
            sel = getattr(self, "slot", 0) == i
            col = PAL["amber"] if sel else PAL["text"]
            if sel:
                assets.draw_arrow(surf, rect.x + 16, rect.y + 64 + i * 60 - 2)
            assets.draw_text(surf, label, rect.x + 38, rect.y + 60 + i * 60,
                             24, col, bold=True)
            nm = data.ITEMS[iid]["name"] if iid else "- none -"
            assets.draw_text(surf, nm, rect.x + 38, rect.y + 88 + i * 60, 22)
        cur = m.known_techs()
        assets.draw_text(surf,
                         f"ATK {m.atk()}  DEF {m.dfn()}  MAG {m.mag()}  "
                         f"MDF {m.mdf()}", rect.x + 20, rect.bottom - 34, 20,
                         PAL["text_dim"])

    def _equip_list_panel(self, surf):
        cands = self._equip_candidates()
        rect = pygame.Rect(WINW // 2 + 380, 120, 380, 120 + 32 * len(cands))
        assets.draw_panel(surf, rect)
        assets.draw_text(surf, "choose:", rect.x + 18, rect.y + 12, 22,
                         PAL["amber"], bold=True)
        if not cands:
            assets.draw_text(surf, "(nothing fits)", rect.x + 20,
                             rect.y + 44, 20, PAL["text_dim"])
            return
        for i, (iid, it) in enumerate(cands):
            y = rect.y + 40 + i * 30
            sel = self.item_idx % len(cands) == i
            if sel:
                assets.draw_arrow(surf, rect.x + 12, y - 4)
            bonuses = "+".join(f"{k.upper()}+{v}" for k, v in
                               (("atk", it.get("atk", 0)), ("mag", it.get("mag", 0)),
                                ("dfn", it.get("dfn", 0)),
                                ("mdf", it.get("mdf", 0))) if v)
            assets.draw_text(surf, f"{it['name']}  {bonuses}", rect.x + 34,
                             y - 5, 20, PAL["amber"] if sel else PAL["text"])
        cands.append(("(none)", dict(name="remove")))
        i0 = self.item_idx % len(cands)
        sel_it = cands[i0][1]
        assets.draw_text(surf, sel_it.get("desc", ""), rect.x + 18,
                         rect.bottom - 32, 20, PAL["text_dim"])

    def _quest_panel(self, surf):
        import data
        rect = pygame.Rect(WINW // 2 - 160, 30, 610, 470)
        assets.draw_panel(surf, rect)
        assets.draw_text(surf, "QUESTS", rect.x + 20, rect.y + 12, 26,
                         PAL["amber"], bold=True)
        flags = self.game.flags
        y = rect.y + 48
        # active quests in full, finished ones as a single line after them
        order = [q for q in data.QUESTS if q["flag"] not in flags] + \
            [q for q in data.QUESTS if q["flag"] in flags]
        for n, q in enumerate(order):
            done = q["flag"] in flags
            body = [] if done else assets.wrap_text(q["active"], 20,
                                                    rect.w - 60)
            need = 22 + 20 * len(body)
            if y + need > rect.bottom - 16:
                left = len(order) - n
                assets.draw_text(surf, f"...and {left} more", rect.x + 24,
                                 y, 20, PAL["text_dim"])
                break
            title = q["title"] + ("  (done)" if done else "")
            assets.draw_text(surf, title, rect.x + 24, y, 22,
                             PAL["text_dim"] if done else PAL["amber"],
                             bold=not done)
            y += 22
            for ln in body:
                assets.draw_text(surf, ln, rect.x + 40, y, 20)
                y += 20
            y += 4 if done else 8
