"""Export the game's songs as WAV files to listen to outside the game.

    python scripts/music_preview.py [song ...]     (default: all songs)

Files go to docs/music/ (not committed). Uses the same renderer and disk
cache as the game.
"""
import os
import sys
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import audio  # noqa: E402


def main():
    names = sys.argv[1:] or audio.ORDER
    out = os.path.join(ROOT, "docs", "music")
    os.makedirs(out, exist_ok=True)
    for name in names:
        pcm = audio.render_song_pcm(name)
        path = os.path.join(out, f"{name}.wav")
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(audio.RATE)
            w.writeframes(pcm)
        print(f"{path}  ({len(pcm) / 2 / audio.RATE:.0f}s)")


if __name__ == "__main__":
    main()
