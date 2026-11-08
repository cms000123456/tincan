"""16-bit console style procedural music + SFX.

A tiny software synth in the spirit of the SNES sound chip: 32 kHz output,
sample-like instruments (flute, oboe, brass, strings, choir, e-piano, harp,
marimba, bells, bass, drums) with envelopes, delayed vibrato and the
console's feedback echo.

Music is *composed*, not looped: each song in SPECS has a key, mode,
tempo, instruments and chord progressions for three sections. compose()
writes motif-based melodies (phrases that answer each other and cadence)
and arranges them through a form - verse, contrast, repeats with new
instruments / harmony / counter-melody, a breakdown, drum fills - so a
song runs 1-2 minutes before it loops.

Rendering is pure Python, so songs are cached in
~/.cache/tincan_chronicles/audio/ and built on a background thread
(whatever is playing next is built first). Silent without an audio device.
"""

import array
import hashlib
import math
import os
import random
import threading
from collections import OrderedDict
from operator import add

import pygame

RATE = 32000
ENGINE_VERSION = "snes-2"
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache",
                         "tincan_chronicles", "audio")
TWO_PI = 2 * math.pi

_NOTES = {}


def _freq(name):
    """note name like 'C4' / 'F#3' -> Hz (0 for rests)."""
    if name in _NOTES:
        return _NOTES[name]
    semis = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    if not name or name[0] not in semis:
        return 0.0
    s = semis[name[0]] + (1 if len(name) > 2 and name[1] == "#" else 0)
    f = 440.0 * 2 ** ((int(name[-1]) - 4) + s / 12.0)
    _NOTES[name] = f
    return f


# ---------------------------------------------------------------------------
# Instruments: one-cycle wavetables + envelopes
# ---------------------------------------------------------------------------
TABLE = 512


def _table(harmonics):
    """Additive wavetable from [(harmonic, amplitude)], normalised."""
    t = [sum(a * math.sin(TWO_PI * h * i / TABLE) for h, a in harmonics)
         for i in range(TABLE)]
    m = max(abs(v) for v in t) or 1.0
    return [v / m for v in t]


WAVES = {
    "lead": _table([(1, 1.0), (2, 0.28), (3, 0.12), (4, 0.05)]),
    "flute": _table([(1, 1.0), (2, 0.16), (3, 0.05)]),
    "oboe": _table([(1, 1.0), (2, 0.55), (3, 0.45), (4, 0.25), (5, 0.16),
                    (6, 0.08)]),
    "brass": _table([(h, 1.0 / h ** 1.1) for h in range(1, 11)]),
    "epiano": _table([(1, 1.0), (2, 0.45), (3, 0.08), (5, 0.06)]),
    "string": _table([(h, 1.0 / h) for h in range(1, 9)]),
    "choir": _table([(1, 1.0), (2, 0.35), (3, 0.22), (4, 0.08), (5, 0.05)]),
    "bass": _table([(1, 1.0), (2, 0.5), (3, 0.18)]),
    "bell": _table([(1, 1.0), (3, 0.42), (5, 0.2), (7, 0.1)]),
    "harp": _table([(1, 1.0), (2, 0.32), (3, 0.14), (4, 0.05)]),
    "marimba": _table([(1, 1.0), (4, 0.22), (10, 0.05)]),
    "square": _table([(1, 1.0), (3, 0.3), (5, 0.14), (7, 0.06)]),
}

# name: wave, attack, decay, sustain, release, vibrato, lowpass k, pluck?
# pluck instruments decay exponentially toward `sustain` (time const decay)
INSTR = {
    "lead":    ("lead",    0.012, 0.18, 0.62, 0.10, 0.0040, 0.85, False),
    "flute":   ("flute",   0.045, 0.20, 0.78, 0.12, 0.0045, 0.80, False),
    "oboe":    ("oboe",    0.030, 0.20, 0.70, 0.10, 0.0030, 0.55, False),
    "brass":   ("brass",   0.040, 0.16, 0.72, 0.09, 0.0030, 0.50, False),
    "strings": ("string",  0.120, 0.30, 0.80, 0.30, 0.0025, 0.50, False),
    "choir":   ("choir",   0.200, 0.30, 0.85, 0.40, 0.0035, 0.45, False),
    "epiano":  ("epiano",  0.004, 0.70, 0.05, 0.14, 0.0,    0.85, True),
    "harp":    ("harp",    0.002, 0.55, 0.0,  0.20, 0.0,    0.80, True),
    "marimba": ("marimba", 0.002, 0.22, 0.0,  0.08, 0.0,    0.80, True),
    "bell":    ("bell",    0.002, 0.80, 0.0,  0.30, 0.0,    0.85, True),
    "bass":    ("bass",    0.004, 0.40, 0.35, 0.06, 0.0,    0.70, True),
    "square":  ("square",  0.006, 0.20, 0.55, 0.06, 0.0035, 0.55, False),
}

_note_cache = {}


def _midi_freq(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def _note(instr, freq, dur, gain=1.0):
    """Render one note (with release tail), pre-scaled -> array('f')."""
    key = (instr, round(freq, 2), round(dur, 3), round(gain, 3))
    hit = _note_cache.get(key)
    if hit is not None:
        return hit
    wave, att, dec, sus, rel, vib, k, pluck = INSTR[instr]
    tab = WAVES[wave]
    n_on = max(1, int(dur * RATE))
    r_n = max(1, int(rel * RATE))
    n = n_on + r_n
    out = array.array("f", bytes(4 * n))
    a_n, d_n = max(1, int(att * RATE)), max(1, int(dec * RATE))
    step = freq * TABLE / RATE
    vib_start = int(0.22 * RATE)
    dk = math.exp(-1.0 / d_n)
    ph = lp = 0.0
    env_d = 1.0
    off_env = None
    for i in range(n):
        if i < a_n:
            env = i / a_n
        elif pluck:
            env_d *= dk
            env = sus + (1.0 - sus) * env_d
        elif i < a_n + d_n:
            env = 1.0 - (1.0 - sus) * (i - a_n) / d_n
        else:
            env = sus
        if i >= n_on:
            if off_env is None:
                off_env = env
            env = off_env * (1.0 - (i - n_on) / r_n)
        if vib and i > vib_start:
            ph += step * (1.0 + vib * math.sin(TWO_PI * 5.2 * i / RATE))
        else:
            ph += step
        lp += k * (tab[int(ph) % TABLE] - lp)
        out[i] = lp * env * gain
    _note_cache[key] = out
    return out


def _drum(kind):
    rng = random.Random(kind)
    if kind == "kick":
        n = int(0.18 * RATE)
        out = array.array("f", bytes(4 * n))
        ph = 0.0
        for i in range(n):
            t = i / RATE
            ph += (48 + 105 * math.exp(-t * 36)) / RATE
            out[i] = math.sin(TWO_PI * ph) * math.exp(-t * 16)
        return out
    if kind in ("tom", "tom_lo"):
        n = int(0.22 * RATE)
        f0 = 170 if kind == "tom" else 115
        out = array.array("f", bytes(4 * n))
        ph = 0.0
        for i in range(n):
            t = i / RATE
            ph += (f0 * (0.7 + 0.3 * math.exp(-t * 20))) / RATE
            out[i] = math.sin(TWO_PI * ph) * math.exp(-t * 13)
        return out
    if kind == "snare":
        n = int(0.15 * RATE)
        out = array.array("f", bytes(4 * n))
        lp = 0.0
        for i in range(n):
            t = i / RATE
            lp += 0.45 * (rng.uniform(-1, 1) - lp)
            tone = math.sin(TWO_PI * 185 * t) * math.exp(-t * 38)
            out[i] = (lp * 0.8 + tone * 0.5) * math.exp(-t * 22)
        return out
    if kind == "crash":
        n = int(1.1 * RATE)
        out = array.array("f", bytes(4 * n))
        prev = lp = 0.0
        for i in range(n):
            t = i / RATE
            v = rng.uniform(-1, 1)
            hp = v - prev
            prev = v
            lp += 0.6 * (hp - lp)
            out[i] = lp * 0.6 * math.exp(-t * 3.2)
        return out
    if kind == "shaker":
        n = int(0.07 * RATE)
        out = array.array("f", bytes(4 * n))
        prev = 0.0
        for i in range(n):
            t = i / RATE
            v = rng.uniform(-1, 1)
            out[i] = (v - prev) * 0.35 * math.sin(math.pi * t / 0.07)
            prev = v
        return out
    n = int(0.045 * RATE)                          # closed hat
    out = array.array("f", bytes(4 * n))
    prev = 0.0
    for i in range(n):
        v = rng.uniform(-1, 1)
        out[i] = (v - prev) * 0.5 * math.exp(-i / RATE * 90)
        prev = v
    return out


def _mix_into(buf, src, pos, gain=1.0):
    """buf[pos:] += src (tails wrap round to the loop start)."""
    n, m = len(buf), len(src)
    pos %= n
    if gain != 1.0:
        src = array.array("f", [v * gain for v in src])
    end = min(n, pos + m)
    k = end - pos
    buf[pos:end] = array.array("f", map(add, buf[pos:end], src[:k]))
    if k < m:                                       # wrap the tail
        rest = src[k:]
        r = min(len(rest), n)
        buf[0:r] = array.array("f", map(add, buf[0:r], rest[:r]))


def _echo(buf, delay_s=0.24, feedback=0.36, mix=0.30):
    """Feedback echo with a soft lowpass (the SNES 'reverb'), circular so
    the loop point stays seamless. Block-wise for speed."""
    n = len(buf)
    d = int(delay_s * RATE)
    if d >= n:
        return buf
    wet = array.array("f", bytes(4 * n))

    def seg(a, ln, arr):                           # circular slice
        a %= n
        if a + ln <= n:
            return arr[a:a + ln]
        return arr[a:] + arr[:ln - (n - a)]
    for _ in range(3):                             # settle the wrap-around
        for s in range(0, n, d):
            ln = min(d, n - s)
            prev_in = seg(s - d, ln, buf)
            prev_wet = seg(s - d, ln, wet)
            wet[s:s + ln] = array.array(
                "f", map(lambda a, b: a + feedback * b, prev_in, prev_wet))
    sh = wet[-1:] + wet[:-1]
    sh2 = wet[-2:] + wet[:-2]
    return array.array("f", map(lambda x, a, b, c: x + mix * (a + b + c) / 3,
                                buf, wet, sh, sh2))


def _to_pcm(buf, vol):
    peak = max(1e-6, max(abs(v) for v in buf))
    g = vol / peak * 32767
    return array.array("h", (int(v * g) for v in buf)).tobytes()


# ---------------------------------------------------------------------------
# Composer
# ---------------------------------------------------------------------------
SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10],
    "harmonic": [0, 2, 3, 5, 7, 8, 11], "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixo": [0, 2, 4, 5, 7, 9, 10], "lydian": [0, 2, 4, 6, 7, 9, 11],
    "phrygdom": [0, 1, 4, 5, 7, 8, 10],
}
KEYS = {"C": 60, "C#": 61, "Db": 61, "D": 62, "Eb": 63, "E": 64, "F": 65,
        "F#": 66, "G": 67, "Ab": 68, "A": 57, "Bb": 58, "B": 59}

RHYTHMS = {   # one bar = 8 eighth-note units
    "slow": [[4, 4], [2, 2, 4], [6, 2], [4, 2, 2], [3, 1, 4], [2, 6]],
    "flow": [[2, 2, 2, 2], [2, 1, 1, 2, 2], [3, 1, 2, 2], [2, 2, 1, 1, 2],
             [1, 1, 2, 2, 2], [2, 2, 4], [3, 1, 4]],
    "drive": [[1, 1, 2, 1, 1, 2], [2, 1, 1, 2, 1, 1], [1, 1, 1, 1, 2, 2],
              [3, 3, 2], [2, 2, 2, 2], [1, 1, 2, 2, 2], [2, 1, 1, 1, 1, 2]],
    "lilt": [[3, 1, 3, 1], [3, 1, 2, 2], [2, 1, 1, 3, 1], [3, 1, 4]],
}
CADENCE = {
    "slow": [[8], [4, 4], [6, 2]],
    "flow": [[2, 2, 4], [4, 4], [3, 1, 4], [2, 6]],
    "drive": [[2, 2, 4], [1, 1, 2, 4], [3, 3, 2]],
    "lilt": [[3, 1, 4], [4, 4], [6, 2]],
}

BASS = {   # (unit, length, chord member) per bar; A = approach next root
    "rootfifth": [(0, 2, "R"), (2, 2, "5"), (4, 2, "R"), (6, 2, "5")],
    "halves": [(0, 4, "R"), (4, 4, "5")],
    "pedal": [(0, 8, "R")],
    "walk": [(0, 2, "R"), (2, 2, "3"), (4, 2, "5"), (6, 2, "A")],
    "pulse": [(0, 3, "R"), (3, 1, "R"), (4, 3, "5"), (7, 1, "A")],
    "root8": [(i, 1, "R") for i in range(6)] + [(6, 1, "8"), (7, 1, "5")],
    "gallop": [(0, 1, "R"), (1, 1, "R"), (2, 2, "R"), (4, 1, "5"),
               (5, 1, "5"), (6, 2, "8")],
    "oompah": [(0, 2, "R"), (4, 2, "5")],
}
ARPS = {   # indices into a 4-note voicing (R, 3, 5, R')
    "broken": [0, 2, 1, 2, 0, 2, 1, 2],
    "up": [0, 1, 2, 3, 2, 1, 0, 1],
    "rolling": [0, 1, 2, 3, 1, 2, 3, 2],
    "slow": [0, None, 2, None, 3, None, 2, None],
    "stab": "stab",          # off-beat chord stabs (oom-PAH)
}
DRUMS = {  # 8 units per bar: k kick s snare h hat t tom T low tom x shaker
    "light": ["k-h-s-h-", "k-h-s-hh"],
    "march": ["k-hsk-hs", "k-hsk-sh"],
    "drive": ["khhskhhs", "khhskkhs"],
    "rock": ["k-hsk-hs", "khhskhhs"],
    "shuffle": ["k-hsk-hs", "k-hsxkhs"],
    "tribal": ["k-t-kkt-", "k-tkk-tT"],
    "half": ["k---s---", "k---s-h-"],
    "shaker": ["x-x-xxx-", "x-xxx-x-"],
}
FILLS = {
    "light": "k-s-ssss", "march": "k-sssstt", "drive": "ssssttTT",
    "rock": "k-ssttTT", "shuffle": "k-ss-sss", "tribal": "ttTTttTT",
    "half": "k---ssss", "shaker": "x-xxxxxx",
}
DGAIN = {"k": ("kick", 0.50), "s": ("snare", 0.26), "h": ("hat", 0.07),
         "t": ("tom", 0.30), "T": ("tom_lo", 0.32), "x": ("shaker", 0.12)}

# arrangement passes; each pass replays one section's tune differently
FORMS = {
    "song": [("A", {}), ("A", dict(lead="lead2", harm=True)),
             ("B", dict(counter=True)), ("A", dict(orn=True, counter=True)),
             ("C", dict(drums="half", arp=False, vel=0.85)),
             ("B", dict(lead="lead2", harm=True, vel=1.08))],
    "calm": [("A", {}), ("B", {}), ("A", dict(lead="lead2", counter=True)),
             ("C", dict(melody=False, counter=True, vel=0.85)),
             ("B", dict(harm=True)), ("A", dict(orn=True, oct=1, vel=0.9))],
    "battle": [("A", {}), ("B", {}), ("A", dict(harm=True, lead="lead2")),
               ("C", dict(drums="half", vel=0.9)),
               ("B", dict(oct=1, harm=True, vel=1.05))],
    "anthem": [("A", dict(drums=False, arp=False)), ("A", dict(counter=True)),
               ("B", dict(harm=True)), ("C", dict(lead="lead2")),
               ("B", dict(harm=True, oct=1, vel=1.1))],
    "town": [("A", {}), ("B", {}), ("A", dict(lead="lead2", harm=True)),
             ("C", dict(drums=False, counter=True, vel=0.85)),
             ("A", dict(orn=True, counter=True)), ("B", dict(lead="lead2"))],
}


class Spec(dict):
    pass


def S(**kw):
    return Spec(kw)


# Degrees: 0=I 1=ii 2=iii 3=IV 4=V 5=vi 6=vii (in the song's mode).
SPECS = {
    "title": S(key="D", mode="major", bpm=88, feel="slow", form="anthem",
               lead="strings", lead2="brass", arp="harp", arp_pat="rolling",
               pad="choir", bass="halves", drums="half",
               A=[0, 4, 5, 2, 3, 0, 1, 4], B=[3, 4, 2, 5, 1, 4, 3, 4],
               C=[5, 3, 0, 4, 5, 3, 1, 4]),
    "town": S(key="F", mode="major", bpm=104, feel="flow", form="town",
              lead="flute", lead2="oboe", arp="harp", arp_pat="broken",
              pad="strings", bass="rootfifth", drums="light",
              A=[0, 3, 4, 0, 5, 3, 1, 4], B=[3, 4, 2, 5, 3, 0, 1, 4],
              C=[5, 2, 3, 0, 1, 4, 0, 4]),
    "over": S(key="D", mode="major", bpm=118, feel="flow", form="song",
              lead="brass", lead2="strings", arp="epiano", arp_pat="up",
              pad="strings", bass="walk", drums="march",
              A=[0, 4, 5, 3, 0, 4, 3, 4], B=[5, 2, 3, 0, 1, 4, 0, 4],
              C=[3, 3, 0, 0, 1, 1, 4, 4]),
    "battle": S(key="A", mode="harmonic", bpm=150, feel="drive",
                form="battle", lead="brass", lead2="square", arp="epiano",
                arp_pat="rolling", pad="strings", bass="gallop",
                drums="drive", vol=0.46,
                A=[0, 0, 5, 4, 0, 0, 3, 4], B=[3, 4, 2, 5, 3, 4, 0, 4],
                C=[5, 5, 3, 3, 1, 1, 4, 4]),
    "battle2": S(key="E", mode="dorian", bpm=144, feel="drive",
                 form="battle", lead="square", lead2="brass", arp="marimba",
                 arp_pat="up", pad="strings", bass="root8", drums="rock",
                 vol=0.46,
                 A=[0, 6, 3, 0, 0, 6, 3, 4], B=[3, 3, 0, 0, 5, 6, 4, 4],
                 C=[0, 3, 0, 3, 5, 6, 4, 4]),
    "boss": S(key="C", mode="harmonic", bpm=156, feel="drive",
              form="battle", lead="brass", lead2="strings", arp="bell",
              arp_pat="rolling", pad="choir", bass="root8", drums="drive",
              vol=0.48,
              A=[0, 1, 4, 0, 5, 1, 4, 4], B=[5, 3, 1, 4, 5, 3, 6, 4],
              C=[0, 0, 5, 5, 3, 3, 4, 4]),
    "cavern": S(key="D", mode="dorian", bpm=80, feel="slow", form="calm",
                lead="epiano", lead2="flute", arp="harp", arp_pat="slow",
                pad="strings", bass="pedal", drums=None, wet=0.45,
                A=[0, 0, 3, 3, 0, 0, 6, 6], B=[5, 3, 0, 4, 5, 3, 6, 4],
                C=[3, 6, 0, 0, 3, 6, 4, 4]),
    "road": S(key="G", mode="mixo", bpm=124, feel="flow", form="song",
              lead="lead", lead2="brass", arp="epiano", arp_pat="broken",
              pad="strings", bass="pulse", drums="rock",
              A=[0, 6, 3, 0, 0, 6, 3, 4], B=[3, 0, 6, 3, 1, 4, 6, 4],
              C=[5, 3, 6, 0, 5, 3, 4, 4]),
    "port": S(key="Bb", mode="major", bpm=112, feel="lilt", form="town",
              swing=0.32, lead="oboe", lead2="flute", arp="epiano",
              arp_pat="stab", pad="strings", bass="oompah", drums="shuffle",
              A=[0, 0, 3, 4, 0, 5, 1, 4], B=[3, 3, 0, 5, 1, 4, 0, 4],
              C=[5, 5, 3, 3, 1, 1, 4, 4]),
    "snow": S(key="E", mode="minor", bpm=86, feel="slow", form="calm",
              lead="bell", lead2="flute", arp="harp", arp_pat="up",
              pad="choir", bass="halves", drums=None, wet=0.45,
              A=[0, 5, 2, 6, 0, 5, 3, 4], B=[5, 6, 2, 5, 3, 6, 4, 4],
              C=[3, 0, 3, 0, 5, 6, 4, 4]),
    "wreck": S(key="C", mode="minor", bpm=74, feel="slow", form="calm",
               lead="oboe", lead2="epiano", arp="harp", arp_pat="slow",
               pad="strings", bass="pedal", drums=None, wet=0.5,
               A=[0, 0, 5, 5, 3, 3, 4, 4], B=[5, 6, 0, 0, 3, 4, 0, 4],
               C=[0, 1, 0, 1, 5, 5, 4, 4]),
    "vault": S(key="B", mode="minor", bpm=96, feel="flow", form="calm",
               lead="bell", lead2="strings", arp="epiano", arp_pat="rolling",
               pad="choir", bass="halves", drums="half", wet=0.45,
               A=[0, 5, 3, 4, 0, 5, 6, 4], B=[2, 5, 3, 0, 2, 5, 1, 4],
               C=[5, 5, 6, 6, 0, 0, 4, 4]),
    "sky": S(key="Eb", mode="lydian", bpm=128, feel="flow", form="song",
             lead="brass", lead2="flute", arp="bell", arp_pat="up",
             pad="choir", bass="pulse", drums="drive",
             A=[0, 1, 0, 1, 5, 1, 3, 4], B=[3, 4, 5, 2, 3, 4, 0, 4],
             C=[5, 1, 5, 1, 3, 3, 4, 4]),
    "desert": S(key="E", mode="phrygdom", bpm=100, feel="flow", form="song",
                lead="marimba", lead2="oboe", arp="harp", arp_pat="broken",
                pad="strings", bass="pulse", drums="tribal",
                A=[0, 1, 0, 6, 0, 1, 5, 0], B=[3, 2, 1, 0, 3, 2, 1, 0],
                C=[5, 6, 0, 0, 5, 6, 1, 0]),
    "forest": S(key="G", mode="lydian", bpm=100, feel="flow", form="song",
                lead="flute", lead2="harp", arp="harp", arp_pat="rolling",
                pad="strings", bass="halves", drums="shaker",
                A=[0, 1, 5, 4, 0, 1, 3, 4], B=[3, 2, 5, 1, 3, 2, 1, 4],
                C=[5, 5, 1, 1, 3, 3, 4, 4]),
    "volcano": S(key="D", mode="harmonic", bpm=136, feel="drive",
                 form="battle", lead="brass", lead2="oboe", arp="marimba",
                 arp_pat="up", pad="strings", bass="root8", drums="rock",
                 A=[0, 5, 3, 4, 0, 5, 1, 4], B=[5, 3, 0, 4, 5, 3, 1, 4],
                 C=[0, 0, 5, 5, 3, 3, 4, 4]),
    "marsh": S(key="F#", mode="minor", bpm=78, feel="slow", form="calm",
               lead="epiano", lead2="oboe", arp="harp", arp_pat="slow",
               pad="choir", bass="pedal", drums=None, wet=0.5,
               A=[0, 5, 0, 5, 3, 6, 4, 4], B=[5, 3, 0, 6, 5, 3, 4, 4],
               C=[3, 3, 0, 0, 1, 1, 4, 4]),
    "city": S(key="C", mode="major", bpm=122, feel="flow", form="song",
              lead="square", lead2="brass", arp="epiano", arp_pat="stab",
              pad="strings", bass="walk", drums="rock",
              A=[0, 5, 1, 4, 0, 5, 1, 4], B=[3, 4, 2, 5, 3, 4, 0, 4],
              C=[1, 4, 0, 5, 1, 4, 0, 4]),
    "orrery": S(key="A", mode="minor", bpm=108, feel="flow", form="song",
                lead="bell", lead2="strings", arp="harp", arp_pat="rolling",
                pad="choir", bass="halves", drums="half",
                A=[0, 5, 2, 6, 0, 5, 3, 4], B=[5, 6, 0, 3, 5, 6, 4, 4],
                C=[3, 4, 2, 5, 3, 4, 6, 6]),
    "ruins": S(key="G", mode="dorian", bpm=92, feel="flow", form="calm",
               lead="oboe", lead2="epiano", arp="marimba", arp_pat="slow",
               pad="strings", bass="walk", drums="half", wet=0.42,
               A=[0, 3, 0, 3, 6, 3, 4, 4], B=[5, 6, 0, 3, 5, 6, 4, 4],
               C=[0, 0, 6, 6, 5, 5, 4, 4]),
    "lair": S(key="B", mode="harmonic", bpm=112, feel="drive", form="battle",
              lead="strings", lead2="brass", arp="bell", arp_pat="up",
              pad="choir", bass="pulse", drums="half", wet=0.4,
              A=[0, 0, 5, 5, 3, 3, 4, 4], B=[5, 1, 4, 0, 5, 1, 4, 4],
              C=[0, 5, 0, 5, 1, 1, 4, 4]),
    "ending": S(key="F", mode="major", bpm=84, feel="slow", form="anthem",
                lead="flute", lead2="strings", arp="harp", arp_pat="rolling",
                pad="choir", bass="halves", drums="half",
                A=[0, 2, 3, 0, 5, 3, 1, 4], B=[3, 4, 2, 5, 1, 4, 0, 0],
                C=[5, 3, 0, 4, 5, 3, 1, 4]),
    # Act II towns: each region gets its own home tune
    "desert_town": S(key="A", mode="phrygdom", bpm=96, feel="lilt",
                     form="town", swing=0.25, lead="oboe", lead2="marimba",
                     arp="harp", arp_pat="broken", pad="strings",
                     bass="oompah", drums="shaker",
                     A=[0, 6, 5, 0, 0, 6, 1, 0], B=[3, 3, 0, 0, 5, 6, 1, 0],
                     C=[5, 6, 0, 0, 5, 6, 1, 0]),
    "forest_town": S(key="D", mode="major", bpm=96, feel="lilt",
                     form="town", swing=0.28, lead="flute", lead2="harp",
                     arp="harp", arp_pat="up", pad="strings",
                     bass="rootfifth", drums="light",
                     A=[0, 3, 0, 4, 0, 3, 4, 0], B=[5, 3, 0, 4, 5, 3, 1, 4],
                     C=[3, 4, 2, 5, 3, 4, 0, 4]),
    "volcano_town": S(key="G", mode="mixo", bpm=108, feel="flow",
                      form="town", lead="brass", lead2="oboe", arp="epiano",
                      arp_pat="stab", pad="strings", bass="oompah",
                      drums="march",
                      A=[0, 6, 3, 0, 0, 6, 4, 0], B=[3, 0, 3, 0, 1, 6, 4, 4],
                      C=[5, 3, 6, 0, 5, 3, 4, 4]),
    "marsh_town": S(key="D", mode="dorian", bpm=88, feel="lilt",
                    form="town", swing=0.3, lead="epiano", lead2="flute",
                    arp="harp", arp_pat="broken", pad="choir",
                    bass="walk", drums="shaker", wet=0.4,
                    A=[0, 3, 0, 3, 6, 3, 4, 0], B=[2, 5, 6, 0, 2, 5, 4, 4],
                    C=[3, 3, 0, 0, 6, 6, 4, 4]),
    "city_town": S(key="Eb", mode="major", bpm=116, feel="flow",
                   form="town", lead="lead", lead2="square", arp="epiano",
                   arp_pat="stab", pad="strings", bass="walk",
                   drums="shuffle", swing=0.2,
                   A=[0, 5, 1, 4, 2, 5, 1, 4], B=[3, 2, 1, 4, 3, 2, 1, 4],
                   C=[3, 4, 2, 5, 1, 4, 0, 4]),
}
SONGS = SPECS            # name list used by the cache / build order


def _deg_midi(root, scale, d):
    return root + 12 * (d // 7) + scale[d % 7]


def _chord_degs(c):
    return [c % 7, (c + 2) % 7, (c + 4) % 7]


def _nearest(cur, cands_mod7, lo, hi, rng, bias=0):
    """Nearest scale degree (absolute) to cur whose class is in cands."""
    best = None
    for d in range(lo, hi + 1):
        if d % 7 in cands_mod7:
            score = abs(d - (cur + bias)) + rng.random() * 0.6
            if best is None or score < best[0]:
                best = (score, d)
    return best[1] if best else cur


def _melody(rng, prog, feel, lo, hi, sparse=False):
    """8-bar period -> per bar a list of (start_unit, units, degree|None).

    Shape: phrase 1 (bars 1-4) rises to a small peak and settles on a half
    cadence; phrase 2 restates the opening, climbs to the climax in bar 7
    and comes home to the tonic. Bar 3 sequences the motif onto its chord,
    bar 5 repeats it exactly, bar 7 sequences it upward."""
    pool, cads = RHYTHMS[feel], CADENCE[feel]
    r_a, r_b = rng.choice(pool), rng.choice(pool)
    cad1, cad2 = rng.choice(cads), rng.choice(cads)
    span = hi - lo
    base = lo + span // 3                         # where phrases start
    arch = [0, 1, 2, 0.5, 0, 2, 3.5, 1]           # contour per bar (degrees)
    lift = max(1.0, span / 5.0)

    def target(b, frac):
        a0 = arch[b]
        a1 = arch[b + 1] if b < 7 else 0
        return base + (a0 + (a1 - a0) * frac) * lift

    def clamp(d):
        return max(lo, min(hi, d))

    bars, motif = [], None
    cur = _nearest(base, _chord_degs(prog[0]), lo, hi, rng)
    hist = []
    for b, chord in enumerate(prog):
        tones = _chord_degs(chord)
        if b in (2, 4, 6) and motif:
            if b == 4:
                shift = 0                           # consequent: exact
            else:
                want = target(b, 0) + (1 if b == 6 else 0)
                first = _nearest(round(want), tones, lo, hi, rng)
                shift = first - motif[0][2]
                ds = [d for (_, _, d) in motif if d is not None]
                shift = min(shift, hi - max(ds))        # fit, don't squash
                shift = max(shift, lo - min(ds))
            notes = [(u, ln, None if d is None else clamp(d + shift))
                     for (u, ln, d) in motif]
            bars.append(notes)
            sounding = [n[2] for n in notes if n[2] is not None]
            cur = sounding[-1]
            hist = sounding[-2:]
            continue
        rhythm = {3: cad1, 7: cad2}.get(b, r_a if b % 2 == 0 else r_b)
        notes, u = [], 0
        for i, ln in enumerate(rhythm):
            final = i == len(rhythm) - 1
            strong = u % 4 == 0
            tgt = target(b, u / 8.0)
            if final and b == 7:
                d = _nearest(cur, [0], lo, hi, rng)          # home
            elif final and b == 3:
                d = _nearest(round(tgt), [tones[0], tones[1]], lo, hi, rng)
            elif strong:
                d = _nearest(round((cur + tgt) / 2), tones, lo, hi, rng)
            else:
                direction = 1 if tgt > cur + 0.5 else -1 if \
                    tgt < cur - 0.5 else rng.choice((1, -1))
                d = clamp(cur + direction * rng.choice((1, 1, 1, 2)))
            if len(hist) >= 2 and hist[-1] == hist[-2] == d:
                d = clamp(d + (1 if d < hi else -1))  # no triple repeats
            if not strong and not final and rng.random() < (
                    0.2 if sparse else 0.06):
                notes.append((u, ln, None))
            else:
                notes.append((u, ln, d))
                cur = d
                hist = (hist + [d])[-2:]
            u += ln
        if b == 0:
            motif = notes
        bars.append(notes)
    return bars


def _lead_range(root, scale, lo_midi, hi_midi):
    """Degrees whose pitches fall inside [lo_midi, hi_midi]."""
    ds = [d for d in range(-21, 29)
          if lo_midi <= _deg_midi(root, scale, d) <= hi_midi]
    return ds[0], ds[-1]


def _ornament(rng, bar):
    """Split some long notes into note + neighbour for a livelier repeat."""
    out = []
    for (u, ln, d) in bar:
        if d is not None and ln >= 4 and rng.random() < 0.6:
            out += [(u, ln - 1, d), (u + ln - 1, 1, d + rng.choice((1, -1)))]
        elif d is not None and ln == 2 and rng.random() < 0.25:
            out += [(u, 1, d), (u + 1, 1, d + 1)]
        else:
            out.append((u, ln, d))
    return out


def compose(name):
    spec = SPECS[name]
    rng = random.Random("tincan-" + name)
    root = KEYS[spec["key"]]
    scale = SCALES[spec["mode"]]
    unit = 60.0 / spec["bpm"] / 2                  # eighth note (s)
    bar_s = unit * 8
    swing = spec.get("swing", 0.0)
    feel = spec["feel"]
    form = FORMS[spec["form"]]
    # lead range in absolute degrees (~ root+0 .. root+12 semitones up)
    # melodies live around G4..E5 (B sections a little higher)
    rng_by = {"A": (62, 79), "B": (65, 83), "C": (60, 77)}
    tunes = {}
    for sec in ("A", "B", "C"):
        lo, hi = _lead_range(root, scale, *rng_by[sec])
        tunes[sec] = _melody(random.Random(f"{name}-{sec}"), spec[sec], feel,
                             lo, hi, sparse=spec["form"] == "calm")
    n_bars = 8 * len(form)
    total = int(bar_s * n_bars * RATE)
    buf = array.array("f", bytes(4 * total))
    kit = {}

    def drum(k):
        if k not in kit:
            kit[k] = _drum(k)
        return kit[k]

    def t_of(bar, u):
        base = bar * bar_s + (u // 2) * 2 * unit
        return base + (unit * (1 + swing) if u % 2 else 0.0)

    def put(instr, midi, bar, u, ln, gain, legato=0.92):
        dur = (t_of(bar, u + ln) - t_of(bar, u)) * legato
        _mix_into(buf, _note(instr, _midi_freq(midi), max(0.04, dur), gain),
                  int(t_of(bar, u) * RATE))

    for p, (sec, var) in enumerate(form):
        prog = spec[sec]
        tune = tunes[sec]
        vel = var.get("vel", 1.0)
        lead = spec[var.get("lead", "lead")]
        octv = 12 * var.get("oct", 0)
        if lead in ("bell", "marimba", "harp") and not var.get("oct"):
            octv += 12                              # tinkly ones sit higher
        drums = var.get("drums", spec.get("drums"))
        if drums is True:
            drums = spec.get("drums")
        orn_rng = random.Random(f"{name}-{p}")
        for b in range(8):
            bar = p * 8 + b
            chord = prog[b]
            nxt = prog[(b + 1) % 8]
            cd = _chord_degs(chord)
            # --- melody (+ harmony a diatonic third below)
            if var.get("melody", True):
                notes = tune[b]
                if var.get("orn"):
                    notes = _ornament(orn_rng, notes)
                for (u, ln, d) in notes:
                    if d is None:
                        continue
                    m = _deg_midi(root, scale, d) + octv
                    put(lead, m, bar, u, ln, 0.34 * vel,
                        0.78 if feel == "drive" else 0.92)
                    if var.get("harm"):
                        hm = _deg_midi(root, scale, d - 2) + octv
                        put(spec["lead2"] if lead != spec["lead2"]
                            else "strings", hm, bar, u, ln, 0.15 * vel)
            # --- counter-melody: long chord tones in the middle register
            if var.get("counter"):
                for half in (0, 4):
                    m = _deg_midi(root, scale, cd[1 if half == 0 else 2])
                    put("strings", m, bar, half, 4, 0.12 * vel, 0.98)
            # --- pad: sustained triad, soft
            if var.get("pad", True) and spec.get("pad"):
                for k, dd in enumerate(cd):
                    m = _deg_midi(root, scale, dd) - 12
                    put(spec["pad"], m, bar, 0, 8, 0.055 * vel, 1.0)
            # --- arpeggio / stabs
            if var.get("arp", True) and spec.get("arp"):
                pat = ARPS[spec.get("arp_pat", "broken")]
                low = 12 if spec["arp"] in ("epiano", "strings") else 0
                voicing = [_deg_midi(root, scale, dd) - low for dd in cd]
                voicing.append(voicing[0] + 12)
                if pat == "stab":
                    for u in (2, 6):
                        for m in voicing[:3]:
                            put(spec["arp"], m, bar, u, 1, 0.07 * vel, 0.7)
                else:
                    for u, idx in enumerate(pat):
                        if idx is None:
                            continue
                        put(spec["arp"], voicing[idx], bar, u, 1,
                            0.085 * vel, 0.9)
            # --- bass
            bpat = BASS[var.get("bass", spec["bass"])]
            r = _deg_midi(root, scale, chord) - 24
            while r < 36:
                r += 12
            for (u, ln, who) in bpat:
                if who == "R":
                    m = r
                elif who == "5":
                    m = r + 7
                elif who == "3":
                    m = r + (_deg_midi(root, scale, chord + 2) -
                             _deg_midi(root, scale, chord))
                elif who == "8":
                    m = r + 12
                else:                                # approach next root
                    nr = _deg_midi(root, scale, nxt) - 24
                    while nr < 36:
                        nr += 12
                    m = nr - 1 if nr > r else nr + 2
                put("bass", m, bar, u, ln, 0.40 * vel, 0.9)
            # --- drums (fill on each section's last bar, crash on its first)
            if drums:
                if b == 0 and p > 0:
                    _mix_into(buf, drum("crash"), int(t_of(bar, 0) * RATE),
                              0.16 * vel)
                pats = DRUMS[drums]
                line = FILLS[drums] if b == 7 else pats[b % 2]
                for u, ch in enumerate(line):
                    if ch == "-":
                        continue
                    kind, g = DGAIN[ch]
                    if b == 7 and ch in "stT":
                        g *= 0.7 + 0.06 * u          # fill crescendo
                    _mix_into(buf, drum(kind), int(t_of(bar, u) * RATE),
                              g * vel)
    return _echo(buf, mix=spec.get("wet", 0.28))


ORDER = ["title", "town", "over", "battle", "battle2", "cavern", "boss",
         "road", "port", "snow", "wreck", "vault", "sky", "desert",
         "desert_town", "ruins", "lair", "forest", "forest_town", "volcano",
         "volcano_town", "marsh", "marsh_town", "city", "city_town",
         "orrery", "ending"]


def _cache_path(name):
    h = hashlib.sha1(repr((ENGINE_VERSION, RATE, name,
                           sorted(SPECS[name].items()))).encode()
                     ).hexdigest()[:12]
    return os.path.join(CACHE_DIR, f"{name}-{h}.pcm")


def render_song_pcm(name):
    """16-bit mono PCM bytes for a song, using the disk cache."""
    path = _cache_path(name)
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        pass
    pcm = _to_pcm(compose(name), SPECS[name].get("vol", 0.42))
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(pcm)
        os.replace(tmp, path)
    except OSError:
        pass
    return pcm


# ---------------------------------------------------------------------------
# SFX
# ---------------------------------------------------------------------------
def _sfx_seq(notes, instr="bell", vol=0.3, echo=True):
    total = sum(d for _, d in notes) + 0.25
    buf = array.array("f", bytes(4 * int(total * RATE)))
    t = 0.0
    for n, d in notes:
        f = _freq(n)
        if f:
            src = _note(instr, f, d)
            pos = int(t * RATE)
            for i, v in enumerate(src):
                if pos + i < len(buf):
                    buf[pos + i] += v
        t += d
    if echo:
        d = int(0.09 * RATE)
        for i in range(d, len(buf)):
            buf[i] += buf[i - d] * 0.3
    return _to_pcm(buf, vol)


def _sfx_noise(dur, vol, lp_k=0.3, pitch_drop=None):
    rng = random.Random(dur)
    n = int(dur * RATE)
    buf = array.array("f", bytes(4 * n))
    lp, ph = 0.0, 0.0
    for i in range(n):
        t = i / RATE
        lp += lp_k * (rng.uniform(-1, 1) - lp)
        v = lp
        if pitch_drop:
            f0, f1 = pitch_drop
            ph += (f1 + (f0 - f1) * math.exp(-t * 25)) / RATE
            v = v * 0.6 + math.sin(TWO_PI * ph) * 0.7
        buf[i] = v * math.exp(-t * (4.0 / dur))
    return _to_pcm(buf, vol)


def build_sfx_pcm():
    return {
        "cursor": _sfx_seq([("E6", 0.035)], "bell", 0.16, echo=False),
        "confirm": _sfx_seq([("B5", 0.04), ("E6", 0.07)], "bell", 0.22),
        "cancel": _sfx_seq([("E5", 0.04), ("B4", 0.06)], "epiano", 0.2),
        "hit": _sfx_noise(0.09, 0.32, 0.5, (520, 140)),
        "hit_big": _sfx_noise(0.22, 0.42, 0.25, (240, 60)),
        "heal": _sfx_seq([("C5", 0.06), ("E5", 0.06), ("G5", 0.06),
                          ("C6", 0.12)], "bell", 0.24),
        "tech": _sfx_seq([("E5", 0.04), ("G5", 0.04), ("B5", 0.04),
                          ("E6", 0.1)], "lead", 0.26),
        "levelup": _sfx_seq([("C5", 0.08), ("E5", 0.08), ("G5", 0.08),
                             ("C6", 0.24)], "lead", 0.3),
        "encounter": _sfx_seq([("A4", 0.05), ("C5", 0.05), ("E5", 0.05),
                               ("A5", 0.05), ("C6", 0.05), ("E6", 0.14)],
                              "strings", 0.3),
        "chest": _sfx_seq([("G4", 0.06), ("C5", 0.06), ("E5", 0.06),
                           ("G5", 0.16)], "bell", 0.28),
        "save": _sfx_seq([("E5", 0.08), ("A5", 0.08), ("C#6", 0.08),
                          ("E6", 0.2)], "bell", 0.26),
        "run": _sfx_noise(0.25, 0.22, 0.15),
        "dead": _sfx_seq([("E4", 0.12), ("C4", 0.12), ("A3", 0.3)],
                         "strings", 0.3),
        "fanfare": _sfx_seq([("G4", 0.09), ("C5", 0.09), ("E5", 0.09),
                             ("G5", 0.18), ("E5", 0.09), ("G5", 0.09),
                             ("C6", 0.5)], "brass", 0.32),
        "step": array.array("h", [0] * 32).tobytes(),
    }


# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------
class Audio:
    """Music on two reserved channels (crossfades), SFX on the rest.

    Songs render on a background thread into the disk cache - whatever the
    game wants right now is rendered next - and only the last few are kept
    in memory."""

    KEEP = 3                     # songs held in memory

    def __init__(self):
        self.ok = False
        self.enabled = True
        self._music = OrderedDict()
        self._ready = set()
        self._sfx = {}
        self.current = None
        self._want = None
        self._lock = threading.Lock()
        try:
            pygame.mixer.init(RATE, -16, 1, 1024)
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(2)
            self._chans = [pygame.mixer.Channel(0), pygame.mixer.Channel(1)]
            self._ci = 0
            self.ok = True
        except pygame.error:
            return
        try:
            self._sfx = {k: pygame.mixer.Sound(buffer=v)
                         for k, v in build_sfx_pcm().items()}
        except Exception:
            self.ok = False
            return
        for name in ORDER:                       # already cached on disk?
            if os.path.exists(_cache_path(name)):
                self._ready.add(name)
        threading.Thread(target=self._build_all, daemon=True).start()

    def _build_all(self):
        pending = [n for n in ORDER if n not in self._ready]
        while pending:
            with self._lock:
                want = self._want
            name = want if want in pending else pending[0]
            pending.remove(name)
            try:
                render_song_pcm(name)
            except Exception:
                continue
            with self._lock:
                self._ready.add(name)
                start = self._want == name and self.current != name
            if start:
                self._start(name)

    def _sound(self, name):
        snd = self._music.get(name)
        if snd is None:
            snd = pygame.mixer.Sound(buffer=render_song_pcm(name))
            self._music[name] = snd
            while len(self._music) > self.KEEP:
                self._music.popitem(last=False)
        self._music.move_to_end(name)
        return snd

    def _start(self, name):
        if not (self.ok and self.enabled):
            return
        with self._lock:
            if name not in self._ready:
                return
        try:
            snd = self._sound(name)
        except Exception:
            return
        quick = name in ("battle", "battle2", "boss")
        old = self._chans[self._ci]
        old.fadeout(200 if quick else 700)
        self._ci ^= 1
        ch = self._chans[self._ci]
        ch.set_volume(0.85)
        ch.play(snd, loops=-1, fade_ms=120 if quick else 900)
        self.current = name

    # -- api ------------------------------------------------------------------
    def play_music(self, name):
        if not self.ok or not self.enabled:
            return
        if name not in SPECS:
            name = "town"
        with self._lock:
            self._want = name
            if name == self.current:
                return
            ready = name in self._ready
        if ready:
            self._start(name)
        else:
            # not rendered yet: fade out now, starts when its render is done
            for ch in self._chans:
                ch.fadeout(500)
            self.current = None

    def stop_music(self):
        if self.ok:
            self.current = None
            self._want = None
            for ch in self._chans:
                ch.fadeout(250)

    def sfx(self, name):
        if not self.ok or not self.enabled:
            return
        s = self._sfx.get(name)
        if s:
            s.play()

    def toggle(self):
        self.enabled = not self.enabled
        if not self.enabled:
            if self.ok:
                for ch in self._chans:
                    ch.stop()
            self.current = None
        elif self._want:
            self._start(self._want)
        return self.enabled


AUDIO = None


def get_audio():
    global AUDIO
    if AUDIO is None:
        AUDIO = Audio()
    return AUDIO
