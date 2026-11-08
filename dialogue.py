"""Dialogue box, choices, shop overlay."""

import pygame

import assets
from settings import PAL, SCALE, GAMEW, WINW, WINH


class DialogueBox:
    """Typewriter dialogue. Pages are strings; '*' marks amber emphasis."""

    def __init__(self, game, pages, on_finish=None):
        self.game = game
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

    def draw(self, surf):
        if self.done:
            return
        page = self.pages[self.page_i][:int(self.chars)]
        panel = pygame.Rect(34, 300, WINW - 68, 200)
        assets.draw_panel(surf, panel)
        segs = self._tokens(page)
        x, y = panel.x + 24, panel.y + 22
        maxw = panel.w - 48
        for txt, color in segs:
            lines = assets.wrap_text(txt, 28, maxw)
            for i, ln in enumerate(lines):
                assets.draw_text(surf, ln, x, y, 28, color,
                                 shadow=True)
                y += 34
                if y > panel.bottom - 40:
                    y = panel.bottom - 40
        # blink 'next' marker
        if self.game.frame % 50 < 25 and self.chars >= len(page):
            pts = [(WINW - 64, panel.bottom - 30),
                   (WINW - 48, panel.bottom - 22),
                   (WINW - 64, panel.bottom - 14)]
            pygame.draw.polygon(surf, PAL["amber"], pts)


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
