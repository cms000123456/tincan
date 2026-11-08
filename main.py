#!/usr/bin/env python3
"""Tin Can Chronicles - a tiny Chrono-Trigger-style j-rpg.

Run:  python main.py           (windowed, needs pygame)
      python main.py --smoke   (headless self-test, N frames then exit)
"""
import sys

import game as game_mod


def main():
    smoke = "--smoke" in sys.argv
    frames = None
    if smoke:
        for a in sys.argv:
            if a.startswith("--frames="):
                frames = int(a.split("=", 1)[1])
        frames = frames or 300
    g = game_mod.Game(headless=smoke)
    g.run(frames=frames)


if __name__ == "__main__":
    main()
