"""16-bit console style procedural music + SFX.

A tiny software synth in the spirit of the SNES sound chip: 32 kHz output,
soft sample-like instruments (flute/e-piano lead, string pad, plucked bass,
bell arpeggio, drum kit) with ADSR envelopes, delayed vibrato and the
console's signature feedback echo. Songs are the same 16-step melody/bass
patterns as before, arranged into a two-pass loop with harmony and drums.

Rendering is pure Python, so finished songs are cached to
~/.cache/tincan_chronicles/ and built on a background thread; the title
theme is built first. Everything silences itself without an audio device.
"""

import array
import hashlib
import math
import os
import random
import threading

import pygame

RATE = 32000
ENGINE_VERSION = "snes-1"
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
    # soft flute / ocarina-ish lead
    "lead": _table([(1, 1.0), (2, 0.28), (3, 0.12), (4, 0.05)]),
    # warm e-piano
    "epiano": _table([(1, 1.0), (2, 0.45), (3, 0.08), (5, 0.06)]),
    # band-limited saw for strings
    "string": _table([(h, 1.0 / h) for h in range(1, 9)]),
    # round fingered bass
    "bass": _table([(1, 1.0), (2, 0.5), (3, 0.18)]),
    # glassy bell (inharmonic-ish partials folded into the cycle)
    "bell": _table([(1, 1.0), (3, 0.42), (5, 0.2), (7, 0.1)]),
}

# instrument: wave, attack, decay, sustain level, release (seconds), vibrato
INSTR = {
    "lead":   ("lead",   0.012, 0.18, 0.62, 0.10, 0.0045),
    "epiano": ("epiano", 0.004, 0.45, 0.30, 0.12, 0.0),
    "string": ("string", 0.090, 0.30, 0.78, 0.22, 0.0025),
    "bass":   ("bass",   0.004, 0.22, 0.42, 0.06, 0.0),
    "bell":   ("bell",   0.002, 0.30, 0.10, 0.20, 0.0),
}

_note_cache = {}


def _note(instr, freq, dur):
    """Render one note (with release tail) -> array('f')."""
    key = (instr, round(freq, 2), round(dur, 4))
    if key in _note_cache:
        return _note_cache[key]
    wave, att, dec, sus, rel, vib = INSTR[instr]
    tab = WAVES[wave]
    n_on = max(1, int(dur * RATE))
    n = n_on + int(rel * RATE)
    out = array.array("f", bytes(4 * n))
    a_n, d_n = max(1, int(att * RATE)), max(1, int(dec * RATE))
    r_n = max(1, n - n_on)
    step = freq * TABLE / RATE
    vib_start = int(0.18 * RATE)
    ph = 0.0
    lp = 0.0
    k = 0.55 if wave == "string" else 0.85        # one-pole lowpass coef
    for i in range(n):
        if i < a_n:
            env = i / a_n
        elif i < a_n + d_n:
            env = 1.0 - (1.0 - sus) * (i - a_n) / d_n
        else:
            env = sus
        if i >= n_on:
            env *= 1.0 - (i - n_on) / r_n
        if vib and i > vib_start:
            # delayed vibrato, ~5.5 Hz
            ph += step * (1.0 + vib * math.sin(TWO_PI * 5.5 * i / RATE))
        else:
            ph += step
        v = tab[int(ph) % TABLE]
        lp += k * (v - lp)                          # soften like the S-DSP
        out[i] = lp * env
    _note_cache[key] = out
    return out


def _drum(kind):
    rng = random.Random(kind)
    if kind == "kick":
        n = int(0.16 * RATE)
        out = array.array("f", bytes(4 * n))
        ph = 0.0
        for i in range(n):
            t = i / RATE
            f = 50 + 110 * math.exp(-t * 38)
            ph += f / RATE
            out[i] = math.sin(TWO_PI * ph) * math.exp(-t * 18)
        return out
    if kind == "snare":
        n = int(0.14 * RATE)
        out = array.array("f", bytes(4 * n))
        lp = 0.0
        for i in range(n):
            t = i / RATE
            noise = rng.uniform(-1, 1)
            lp += 0.45 * (noise - lp)
            tone = math.sin(TWO_PI * 190 * t) * math.exp(-t * 40)
            out[i] = (lp * 0.8 + tone * 0.5) * math.exp(-t * 24)
        return out
    # hat
    n = int(0.045 * RATE)
    out = array.array("f", bytes(4 * n))
    prev = 0.0
    for i in range(n):
        noise = rng.uniform(-1, 1)
        hp = noise - prev                          # crude highpass
        prev = noise
        out[i] = hp * 0.5 * math.exp(-i / RATE * 90)
    return out


def _mix_into(buf, src, pos, gain):
    n = len(buf)
    for i, v in enumerate(src):
        j = pos + i
        if j >= n:
            j -= n                                 # wrap tails into the loop
        buf[j] += v * gain


def _echo(buf, delay_s=0.22, feedback=0.38, mix=0.32):
    """Feedback echo with a lowpass in the loop (the SNES 'reverb')."""
    n = len(buf)
    d = int(delay_s * RATE)
    line = array.array("f", bytes(4 * d))
    out = array.array("f", buf)
    lp = 0.0
    # run twice around the loop so the tail wraps seamlessly
    for _ in range(2):
        for i in range(n):
            j = i % d
            e = line[j]
            lp += 0.5 * (e - lp)
            line[j] = buf[i] + lp * feedback
            out[i] = buf[i] + lp * mix
    return out


def _to_pcm(buf, vol):
    peak = max(1e-6, max(abs(v) for v in buf))
    g = vol / peak * 32767
    a = array.array("h", (int(v * g) for v in buf))
    return a.tobytes()


# ---------------------------------------------------------------------------
# Song arrangement
# ---------------------------------------------------------------------------
STYLES = {
    # lead instrument, drum pattern, pad on?, arpeggio on 2nd pass?
    "town":   ("lead",   "light",   True, True),
    "over":   ("lead",   "march",   True, True),
    "cavern": ("epiano", None,      True, False),
    "battle": ("lead",   "drive",   True, True),
    "road":   ("lead",   "march",   True, True),
    "port":   ("epiano", "light",   True, True),
    "snow":   ("bell",   None,      True, True),
    "wreck":  ("epiano", None,      True, False),
    "vault":  ("bell",   "light",   True, False),
    "sky":    ("lead",   "drive",   True, True),
    "desert": ("lead",   "light",   True, True),
    "forest": ("epiano", "light",   True, True),
    "volcano": ("lead",  "drive",   True, False),
    "marsh":  ("epiano", None,      True, False),
    "city":   ("lead",   "march",   True, True),
    "orrery": ("bell",   "drive",   True, True),
}

# 16 eighth-note steps per bar: k=kick s=snare h=hat
DRUMS = {
    "light": "k-h-s-h-k-h-s-hh",
    "march": "k-hhs-h-kkhhs-hh",
    "drive": "khhhskhhkhhhskhs",
}


def _song(melody, bass, bpm, style):
    lead_i, drums, pad, arp = STYLES[style]
    step = 60.0 / bpm * 0.5                       # eighth notes
    bar = len(melody) * step
    total = int(bar * 2 * RATE)                   # two passes per loop
    buf = array.array("f", bytes(4 * total))
    kit = {k: _drum(k) for k in ("kick", "snare", "hat")} if drums else {}
    for p in range(2):
        base = p * bar
        # melody (an octave up on the second pass for bells, for lift)
        t = base
        for tok in melody:
            f = _freq(tok)
            if f:
                _mix_into(buf, _note(lead_i, f, step * 0.92),
                          int(t * RATE), 0.55)
            t += step
        # bass: quarter notes, plucked
        t = base
        for tok in bass:
            f = _freq(tok)
            if f:
                _mix_into(buf, _note("bass", f, step * 1.7),
                          int(t * RATE), 0.62)
            t += step * 2
        # pad: root/fifth/octave above each bass note, held
        if pad:
            t = base
            for tok in bass:
                f = _freq(tok)
                if f:
                    for mul, g in ((2, 0.13), (3, 0.10), (4, 0.08)):
                        _mix_into(buf, _note("string", f * mul, step * 2),
                                  int(t * RATE), g)
                t += step * 2
        # sparkle arpeggio on the repeat
        if arp and p == 1:
            t = base
            for tok in bass:
                f = _freq(tok)
                if f:
                    for k, mul in enumerate((4, 6, 8, 6)):
                        _mix_into(buf, _note("bell", f * mul, step * 0.45),
                                  int((t + k * step / 2) * RATE), 0.10)
                t += step * 2
        if drums:
            pat = DRUMS[drums]
            for k, ch in enumerate(pat * (len(melody) // len(pat) or 1)):
                if ch == "-":
                    continue
                name = {"k": "kick", "s": "snare", "h": "hat"}[ch]
                g = {"kick": 0.55, "snare": 0.32, "hat": 0.16}[name]
                _mix_into(buf, kit[name], int((base + k * step) * RATE), g)
    wet = {"cavern": 0.45, "wreck": 0.5, "vault": 0.45, "snow": 0.42}
    return _echo(buf, mix=wet.get(style, 0.30))


SONGS = {
    "town": (["E4", "G4", "A4", "-", "B4", "A4", "G4", "-",
              "E4", "G4", "A4", "B4", "C5", "B4", "A4", "G4"],
             ["C3", "-", "G2", "-", "A2", "-", "F2", "-",
              "C3", "-", "G2", "-", "F2", "-", "G2", "-"], 116),
    "over": (["C4", "E4", "G4", "E4", "F4", "-", "A4", "G4",
              "C4", "E4", "G4", "E4", "D4", "-", "G4", "F4"],
             ["C3", "-", "E3", "-", "F2", "-", "C3", "-",
              "G2", "-", "B2", "-", "C3", "-", "G2", "-"], 124),
    "cavern": (["-", "A3", "-", "C4", "-", "B3", "-", "-", "-",
                "A3", "-", "D4", "C4", "B3", "-", "-"],
               ["A2", "-", "A2", "-", "F2", "-", "F2", "-",
                "E2", "-", "E2", "-", "D2", "-", "D2", "-"], 92),
    "battle": (["A4", "-", "A4", "C5", "B4", "-", "E4", "-",
                "A4", "-", "A4", "D5", "C5", "B4", "A4", "G4"],
               ["A2", "A2", "E2", "E2", "F2", "F2", "E2", "E2",
                "A2", "A2", "E2", "E2", "D2", "D2", "E2", "E2"], 140),
    "road": (["G4", "A4", "B4", "A4", "G4", "-", "E4", "-",
              "C4", "D4", "E4", "G4", "A4", "-", "B4", "C5"],
             ["C3", "-", "G2", "-", "A2", "-", "F2", "-",
              "G2", "-", "C3", "-", "F2", "-", "G2", "-"], 128),
    "port": (["C4", "D4", "E4", "C4", "E4", "F4", "G4", "-",
              "A4", "G4", "E4", "C4", "D4", "-", "C4", "-"],
             ["C3", "-", "E3", "-", "G2", "-", "C3", "-",
              "F2", "-", "G2", "-", "C3", "-", "G2", "-"], 120),
    "snow": (["E5", "-", "C5", "D5", "E5", "-", "-", "-",
              "G5", "-", "E5", "D5", "C5", "-", "-", "-"],
             ["A2", "-", "F2", "-", "G2", "-", "G2", "-",
              "C3", "-", "G2", "-", "F2", "-", "F2", "-"], 100),
    "wreck": (["-", "D4", "-", "F4", "-", "E4", "-", "-", "-",
               "C4", "-", "D4", "-", "C4", "-", "-"],
              ["D2", "-", "D2", "-", "C2", "-", "C2", "-",
               "A1", "-", "A1", "-", "F2", "-", "F2", "-"], 86),
    "vault": (["A4", "-", "C5", "-", "E5", "-", "C5", "-",
               "D5", "-", "F5", "-", "E5", "-", "C5", "-"],
              ["A2", "-", "F2", "-", "C3", "-", "F2", "-",
               "D2", "-", "A2", "-", "E2", "-", "A2", "-"], 104),
    "sky": (["C5", "E5", "G5", "E5", "F5", "G5", "A5", "-",
             "G5", "E5", "G5", "A5", "C6", "-", "G5", "-"],
            ["C3", "-", "G3", "-", "F2", "-", "C3", "-",
             "G2", "-", "B2", "-", "C3", "-", "F2", "-"], 132),
}
SONGS.update({
    "desert": (["E4", "F4", "G#4", "-", "A4", "G#4", "F4", "E4",
                "-", "E4", "F4", "A4", "B4", "-", "A4", "G#4"],
               ["E2", "-", "E2", "-", "F2", "-", "E2", "-",
                "D2", "-", "E2", "-", "F2", "-", "E2", "-"], 108),
    "forest": (["G4", "B4", "D5", "B4", "C5", "-", "A4", "-",
                "G4", "A4", "B4", "D5", "E5", "-", "D5", "-"],
               ["G2", "-", "D3", "-", "C3", "-", "D3", "-",
                "E2", "-", "C3", "-", "D3", "-", "G2", "-"], 112),
    "volcano": (["D4", "-", "D4", "F4", "E4", "-", "C4", "-",
                 "D4", "-", "A4", "G4", "F4", "E4", "D4", "-"],
                ["D2", "D2", "A1", "A1", "A#1", "A#1", "A1", "A1",
                 "D2", "D2", "A1", "A1", "G1", "G1", "A1", "A1"], 132),
    "marsh": (["-", "B3", "-", "D4", "C#4", "-", "-", "A3",
               "-", "B3", "-", "F#4", "E4", "-", "-", "-"],
              ["B1", "-", "B1", "-", "G1", "-", "G1", "-",
               "A1", "-", "A1", "-", "F#1", "-", "F#1", "-"], 84),
    "city": (["C5", "E5", "G5", "E5", "D5", "F5", "A5", "F5",
              "E5", "G5", "C6", "G5", "F5", "D5", "B4", "G4"],
             ["C3", "-", "G2", "-", "F2", "-", "G2", "-",
              "A2", "-", "E2", "-", "F2", "-", "G2", "-"], 126),
    "orrery": (["A4", "C5", "E5", "A5", "G5", "E5", "C5", "D5",
                "E5", "-", "B4", "C5", "D5", "-", "E5", "-"],
               ["A2", "-", "F2", "-", "C3", "-", "G2", "-",
                "A2", "-", "F2", "-", "D2", "-", "E2", "-"], 118),
})
# build order: title first, then the places you reach soonest
ORDER = ["town", "over", "battle", "cavern", "road", "port", "snow",
         "wreck", "vault", "sky", "desert", "forest", "volcano", "marsh",
         "city", "orrery"]


def _cache_path(name):
    mel, bas, bpm = SONGS[name]
    h = hashlib.sha1(repr((ENGINE_VERSION, RATE, name, mel, bas, bpm,
                           STYLES[name])).encode()).hexdigest()[:12]
    return os.path.join(CACHE_DIR, f"{name}-{h}.pcm")


def render_song_pcm(name):
    """16-bit mono PCM bytes for a song, using the disk cache."""
    path = _cache_path(name)
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        pass
    mel, bas, bpm = SONGS[name]
    pcm = _to_pcm(_song(mel, bas, bpm, name), 0.42)
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
                              "string", 0.3),
        "chest": _sfx_seq([("G4", 0.06), ("C5", 0.06), ("E5", 0.06),
                           ("G5", 0.16)], "bell", 0.28),
        "save": _sfx_seq([("E5", 0.08), ("A5", 0.08), ("C#6", 0.08),
                          ("E6", 0.2)], "bell", 0.26),
        "run": _sfx_noise(0.25, 0.22, 0.15),
        "dead": _sfx_seq([("E4", 0.12), ("C4", 0.12), ("A3", 0.3)],
                         "string", 0.3),
        "step": array.array("h", [0] * 32).tobytes(),
    }


# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------
class Audio:
    def __init__(self):
        self.ok = False
        self.enabled = True
        self._music = {}
        self._sfx = {}
        self.current = None
        self._want = None
        self._lock = threading.Lock()
        try:
            pygame.mixer.init(RATE, -16, 1, 1024)
            self.ok = True
        except pygame.error:
            return
        try:
            self._sfx = {k: pygame.mixer.Sound(buffer=v)
                         for k, v in build_sfx_pcm().items()}
            # title theme now (cached after the first run), rest async
            self._add_song(ORDER[0])
            threading.Thread(target=self._build_rest, daemon=True).start()
        except Exception:
            self.ok = False

    def _add_song(self, name):
        snd = pygame.mixer.Sound(buffer=render_song_pcm(name))
        with self._lock:
            self._music[name] = snd
            start = self._want == name and self.current != name
        if start:
            self._start(name)

    def _build_rest(self):
        for name in ORDER[1:]:
            try:
                self._add_song(name)
            except Exception:
                pass

    def _start(self, name):
        if not (self.ok and self.enabled):
            return
        s = self._music.get(name)
        if s is None:
            return
        self.current = name
        pygame.mixer.stop()
        s.play(loops=-1)

    # -- api ------------------------------------------------------------------
    def play_music(self, name):
        if not self.ok or not self.enabled:
            return
        with self._lock:
            self._want = name
            if name == self.current:
                return
            ready = name in self._music
        if ready:
            self._start(name)
        else:
            # not built yet: silence now, starts when its render finishes
            pygame.mixer.stop()
            self.current = None

    def stop_music(self):
        if self.ok:
            self.current = None
            self._want = None
            pygame.mixer.stop()

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
                pygame.mixer.stop()
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
