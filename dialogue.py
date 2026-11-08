"""Dialogue box, choices, shop overlay."""

import re

import pygame

import assets
from settings import PAL, SCALE, GAMEW, WINW, WINH


class DialogueBox:
    """Typewriter dialogue. Pages are strings; '*' marks amber emphasis."""

    def __init__(self, game, pages, on_finish=None, speakers=True):
        self.game = game
        self.speakers = speakers
        self.pages = list(pages)
        self.page_i = 0
        self.chars = 0.0
        self.done = False
        self.on_finish = on_finish
        self.speed = 55.0   # chars per second

    def _tokens(self, page):
        """split into (text, color) segments by '*' pairs."""
        segs = []
        cur = ""
        colored = False
        for ch in page:
            if ch == "*":
                if cur:
                    segs.append((cur, PAL["amber"] if colored else PAL["text"]))
                cur = ""
                colored = not colored
            else:
                cur += ch
        if cur:
            segs.append((cur, PAL["amber"] if colored else PAL["text"]))
        return segs

    def update(self, dt, pressed):
        if self.done:
            return

        page = self.pages[self.page_i]
        total = len(page)
        if "a" in pressed:
            if self.chars < total:
                self.chars = total
                self.game.audio.sfx("cursor")
            else:
                self.page_i += 1
                self.chars = 0.0
                if self.page_i >= len(self.pages):
                    self.done = True
                    if self.on_finish:
                        cb, self.on_finish = self.on_finish, None
                        cb()
        else:
            self.chars = min(total, self.chars + self.speed * dt)

    # speaker prefix "Name: text" -> nameplate; party members get portraits
    _SPEAKER = re.compile(r"^([A-Z?][\w.' ?-]{0,26}):\s+(.*)$", re.S)

    def _split(self, page):
        m = self._SPEAKER.match(page) if self.speakers else None
        if not m:
            return None, page
        return m.group(1), m.group(2)

    def _portrait(self, name):
        if not name:
            return None
        party = getattr(self.game, "party", None)
        for mem in (party.members if party else []):
            if mem.name.lower() == name.lower():
                return getattr(mem, "portrait", None)
        return None

    def _layout(self, segs, size, maxw):
        """Word-wrap coloured segments together -> [[(text, color)...]]."""
        f = assets.get_font(size)
        lines, cur, cur_w = [], [], 0
        space = f.size(" ")[0]
        for txt, color in segs:
            for i, word in enumerate(txt.split(" ")):
                if word == "":
                    continue
                ww = f.size(word)[0]
                lead = space if cur else 0
                if cur and cur_w + lead + ww > maxw:
                    lines.append(cur)
                    cur, cur_w, lead = [], 0, 0
                cur.append((word, color, lead))
                cur_w += lead + ww
        if cur:
            lines.append(cur)
        return lines

    def draw(self, surf):
        if self.done:
            return
        full = self.pages[self.page_i]
        name, body = self._split(full)
        shown = int(self.chars) - (len(full) - len(body))
        body = body[:max(0, shown)]
        panel = pygame.Rect(34, 300, WINW - 68, 200)
        assets.draw_panel(surf, panel)
        x0 = panel.x + 24
        por = self._portrait(name)
        if por is not None:
            k = max(1, (panel.h - 44) // por.get_height())
            pw, ph = por.get_width() * k, por.get_height() * k
            img = por if k == 1 else pygame.transform.scale(por, (pw, ph))
            frame = pygame.Rect(panel.x + 16, panel.y + 18, pw + 8, ph + 8)
            pygame.draw.rect(surf, (12, 14, 40), frame)
            pygame.draw.rect(surf, (150, 160, 230), frame, 2)
            surf.blit(img, (frame.x + 4, frame.y + 4))
            x0 = frame.right + 18
        if name:
            f = assets.get_font(24, True)
            tw = f.size(name)[0]
            tab = pygame.Rect(panel.x + 14, panel.y - 30, tw + 34, 40)
            assets.draw_panel(surf, tab)
            assets.draw_text(surf, name, tab.x + 17, tab.y + 9, 24,
                             PAL["amber"], bold=True)
        maxw = panel.right - 24 - x0
        y = panel.y + 22
        f = assets.get_font(28)
        for line in self._layout(self._tokens(body), 28, maxw):
            x = x0
            for word, color, lead in line:
                x += lead
                assets.draw_text(surf, word, x, y, 28, color, shadow=True)
                x += f.size(word)[0]
            y += 34
            if y > panel.bottom - 40:
                break
        # blink 'next' marker
        if self.game.frame % 50 < 25 and self.chars >= len(full):
            pts = [(WINW - 64, panel.bottom - 30),
                   (WINW - 48, panel.bottom - 22),
                   (WINW - 64, panel.bottom - 14)]
            pygame.draw.polygon(surf, PAL["amber"], pts)


class ChapterCard:
    """'CHAPTER V - The Ticking Sands' banner that sweeps over the world."""

    DUR = 3.6

    def __init__(self, game, numeral, title, on_finish=None):
        self.game = game
        self.numeral = numeral
        self.title = title
        self.t = 0.0
        self.done = False
        self.on_finish = on_finish
        game.audio.sfx("confirm")

    def update(self, dt, pressed):
        if self.done:
            return
        self.t += dt
        if ("a" in pressed and self.t > 0.8) or self.t >= self.DUR:
            self.done = True
            if self.on_finish:
                cb, self.on_finish = self.on_finish, None
                cb()

    def draw(self, surf):
        t, D = self.t, self.DUR
        # envelope: band opens 0..0.4s, holds, closes in the last 0.5s
        k = min(1.0, t / 0.4, max(0.0, (D - t) / 0.5))
        k = k * k * (3 - 2 * k)
        dim = pygame.Surface((WINW, WINH), pygame.SRCALPHA)
        dim.fill((4, 6, 20, int(110 * k)))
        surf.blit(dim, (0, 0))
        bh = int(150 * k)
        if bh <= 2:
            return
        band = pygame.Surface((WINW, bh), pygame.SRCALPHA)
        for yy in range(bh):
            e = 1 - abs(yy - bh / 2) / (bh / 2)
            band.fill((10, 14, 48, int(235 * min(1.0, e * 2.2))),
                      (0, yy, WINW, 1))
        cy = WINH // 2 - 30
        surf.blit(band, (0, cy - bh // 2))
        if k < 0.9:
            return
        # gold rules sliding in from both sides
        slide = min(1.0, (t - 0.35) / 0.5)
        slide = 1 - (1 - max(0.0, slide)) ** 3
        rw = int(300 * slide)
        pygame.draw.rect(surf, PAL["amber"], (WINW // 2 - 20 - rw, cy - 4,
                                              rw, 3))
        pygame.draw.rect(surf, PAL["amber"], (WINW // 2 + 20, cy - 4, rw, 3))
        a = max(0.0, min(1.0, (t - 0.45) / 0.4))
        if a <= 0:
            return
        col = tuple(int(c * a) for c in PAL["amber"])
        assets.draw_text(surf, f"CHAPTER {self.numeral}", WINW // 2,
                         cy - 52, 26, col, bold=True, align="center")
        col2 = tuple(int(c * a) for c in (245, 245, 255))
        assets.draw_text(surf, self.title, WINW // 2, cy + 14, 42, col2,
                         bold=True, align="center")


class Choice:
    """Vertical list of options; returns callback or None."""

    def __init__(self, game, rect, options, title=None):
        self.game = game
        self.rect = pygame.Rect(rect)
        self.options = options        # list of (label, kind, payload)
        self.title = title
        self.idx = 0
        self.done = False

    def update(self, dt, pressed):
        n = len(self.options)
        if "up" in pressed:
            self.idx = (self.idx - 1) % n
            self.game.audio.sfx("cursor")
        if "down" in pressed:
            self.idx = (self.idx + 1) % n
            self.game.audio.sfx("cursor")
        if "a" in pressed:
            self.done = True
            self.game.audio.sfx("confirm")
            self.selected = self.options[self.idx]
            on_pick = getattr(self, "on_pick", None)
            if on_pick:
                on_pick(self.selected)
        if "b" in pressed:
            self.done = True
            self.selected = None
            self.game.audio.sfx("cancel")
            on_pick = getattr(self, "on_pick", None)
            if on_pick:
                on_pick(None)

    def draw(self, surf):
        assets.draw_panel(surf, self.rect)
        y = self.rect.y + 20
        if self.title:
            assets.draw_text(surf, self.title, self.rect.x + 20, y, 24,
                             PAL["amber"], bold=True)
            y += 34
        for i, (label, kind, payload) in enumerate(self.options):
            color = PAL["text"]
            if i == self.idx:
                assets.draw_arrow(surf, self.rect.x + 14, y + 6)
                color = PAL["amber"]
            assets.draw_text(surf, label, self.rect.x + 34, y, 26, color)
            y += 36
