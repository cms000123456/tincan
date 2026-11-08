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
        self.slot = 0
        self.scroll = 0

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
            n = len(self.game.party.members)
            if "b" in pressed:
                self.mode = "root"
                self.game.audio.sfx("cancel")
            if "left" in pressed or "right" in pressed:
                d = 1 if "right" in pressed else -1
                self.member_idx = (self.member_idx + d) % n
                self.game.audio.sfx("cursor")
            if "up" in pressed or "down" in pressed:
                self.slot = 1 - self.slot
                self.game.audio.sfx("cursor")
            if "a" in pressed:
                self.mode = "equip_list"
                cands = self._equip_candidates()
                m = self.game.party.members[self.member_idx]
                cur = m.weapon if self.slot == 0 else m.charm
                ids = [c[0] for c in cands]
                self.item_idx = ids.index(cur) if cur else 0
                self.scroll = 0
                self.game.audio.sfx("confirm")
        elif self.mode == "equip_list":
            cands = self._equip_candidates()
            n = len(cands)
            if "b" in pressed:
                self.mode = "equip"
                self.game.audio.sfx("cancel")
            if "up" in pressed:
                self.item_idx = (self.item_idx - 1) % n
                self.game.audio.sfx("cursor")
            if "down" in pressed:
                self.item_idx = (self.item_idx + 1) % n
                self.game.audio.sfx("cursor")
            if "a" in pressed:
                iid = cands[self.item_idx % n][0]
                m2 = self.game.party.members[self.member_idx]
                slot = "weapon" if self.slot == 0 else "charm"
                if iid is None:
                    setattr(m2, slot, None)
                    self.flash("Unequipped.")
                else:
                    setattr(m2, slot, iid)
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
        # party glance (right column) - hidden under the big equip panel
        glance = self.mode not in ("equip", "equip_list")
        if glance:
            assets.draw_panel(surf, (330, 60, 260, 320))
        for i, m in enumerate(p.members if glance else []):
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
        if self.note and self.note_t > 0:
            if self.mode in ("equip", "equip_list"):
                rect = pygame.Rect(30, 392, 290, 44)     # clear of the list
                size = 20
            else:
                rect = pygame.Rect(340, 380, 420, 44)
                size = 24
            assets.draw_panel(surf, rect)
            assets.draw_text(surf, self.note, rect.x + 14, rect.y + 11,
                             size, PAL["amber"])

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
        """Owned gear that fits the selected member's slot, best first,
        then a 'remove' entry. A charm worn by someone else only counts
        if you own a spare."""
        p = self.game.party
        m = p.members[self.member_idx]
        kind = "weapon" if self.slot == 0 else "charm"
        out = []
        for iid, it in data.ITEMS.items():
            if it["kind"] != kind:
                continue
            if kind == "weapon" and it.get("for_") != m.id:
                continue
            mine = (m.weapon if kind == "weapon" else m.charm) == iid
            owned = p.inventory.get(iid, 0)
            if kind == "charm":
                owned -= sum(1 for o in p.members
                             if o is not m and o.charm == iid)
            if mine or owned > 0:
                out.append((iid, it))
        out.sort(key=lambda t: -(t[1].get("atk", 0) + t[1].get("mag", 0) +
                                 t[1].get("dfn", 0) + t[1].get("mdf", 0)))
        out.append((None, dict(name="- remove -", desc="Take it off.")))
        return out

    STATS = (("ATK", "atk"), ("DEF", "dfn"), ("MAG", "mag"), ("MDF", "mdf"))

    def _equip_panel(self, surf):
        """One panel inside the screen: member, slots, stats (with a
        preview of the highlighted item) and the scrolling gear list."""
        p = self.game.party
        m = p.members[self.member_idx]
        rect = pygame.Rect(330, 40, WINW - 360, WINH - 80)
        assets.draw_panel(surf, rect)
        x0 = rect.x + 22
        listing = self.mode == "equip_list"
        # header: < Kai >
        assets.draw_text(surf, "EQUIP", x0, rect.y + 14, 26, PAL["amber"],
                         bold=True)
        img = m.sheet.get(("down", "idle"))
        hx = rect.right - 210
        if img:
            surf.blit(img, (hx, rect.y + 6))
        assets.draw_text(surf, m.name, hx + 40, rect.y + 14, 26,
                         PAL["text"], bold=True)
        if not listing:
            assets.draw_text(surf, "<", hx - 26, rect.y + 14, 26,
                             PAL["amber"])
            assets.draw_text(surf, ">", rect.right - 30, rect.y + 14, 26,
                             PAL["amber"])
        # slots
        y = rect.y + 62
        for i, (label, iid) in enumerate((("Weapon", m.weapon),
                                          ("Charm", m.charm))):
            sel = self.slot == i
            col = PAL["amber"] if sel else PAL["text_dim"]
            if sel and not listing:
                assets.draw_arrow(surf, x0 - 6, y + 2)
            assets.draw_text(surf, label, x0 + 18, y, 24, col, bold=True)
            nm = data.ITEMS[iid]["name"] if iid else "- none -"
            assets.draw_text(surf, nm, x0 + 140, y, 24,
                             PAL["text"] if iid else PAL["text_dim"])
            y += 36
        # stats, with preview of the highlighted candidate
        cands = self._equip_candidates() if listing else []
        pick = cands[self.item_idx % len(cands)] if cands else None
        slot_attr = "weapon" if self.slot == 0 else "charm"
        y += 6
        for k, (lab, key) in enumerate(self.STATS):
            sx = x0 + k * ((rect.w - 44) // 4)
            now = getattr(m, key)()
            assets.draw_text(surf, lab, sx, y, 20, PAL["text_dim"])
            assets.draw_text(surf, str(now), sx + 52, y, 20)
            if pick is not None:
                old = getattr(m, slot_attr)
                setattr(m, slot_attr, pick[0])
                new = getattr(m, key)()
                setattr(m, slot_attr, old)
                if new != now:
                    col = PAL["green"] if new > now else PAL["red"]
                    assets.draw_text(surf, f"{'+' if new > now else ''}"
                                     f"{new - now}", sx + 52, y + 24, 18,
                                     col)
        y += 58
        pygame.draw.line(surf, (110, 120, 190), (x0, y), (rect.right - 22, y),
                         2)
        y += 12
        if not listing:
            assets.draw_text(surf, "Left/Right: party member   "
                             "Up/Down: slot   Z: change", x0, y, 18,
                             PAL["text_dim"])
            return
        # scrolling list
        rows = max(3, (rect.bottom - 60 - y) // 32)
        idx = self.item_idx % len(cands)
        if idx < self.scroll:
            self.scroll = idx
        elif idx >= self.scroll + rows:
            self.scroll = idx - rows + 1
        top = y
        for i in range(self.scroll, min(len(cands), self.scroll + rows)):
            iid, it = cands[i]
            yy = top + (i - self.scroll) * 32
            sel = i == idx
            if sel:
                assets.draw_arrow(surf, x0 - 6, yy + 2)
            worn = iid is not None and getattr(m, slot_attr) == iid
            name = it["name"] + ("  (E)" if worn else "")
            assets.draw_text(surf, name, x0 + 18, yy, 22,
                             PAL["amber"] if sel else PAL["text"])
            bon = "  ".join(f"{lab}+{it.get(key, 0)}" for lab, key in
                            self.STATS if it.get(key, 0))
            assets.draw_text(surf, bon, rect.right - 24, yy + 2, 18,
                             PAL["cyan"], align="right")
        if self.scroll > 0:
            assets.draw_text(surf, "^", rect.centerx, top - 16, 18,
                             PAL["amber"])
        if self.scroll + rows < len(cands):
            assets.draw_text(surf, "v", rect.centerx, rect.bottom - 58, 18,
                             PAL["amber"])
        desc = pick[1].get("desc", "") if pick else ""
        assets.draw_text(surf, desc, x0, rect.bottom - 36, 18,
                         PAL["text_dim"])

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
