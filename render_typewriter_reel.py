"""Typewriter reel: black screen -> the quote is typed out letter by letter
with real mechanical-keyboard key sounds, while the statue and the attribution/handle block
fade in slowly, reaching full brightness exactly when typing ends. Nothing
else is ever on screen. The final frame is the same card the static
pipeline renders (composite_card.py's layout), so the two stay consistent.

Usage:
    python3 render_typewriter_reel.py "<quote>" "<attribution>" "<source>" <row_id> [out.mp4]

Retention-driven timing: the first key lands ~0.05s after frame 0 (no dead
black time), pace is ~20 chars/sec with human-ish jitter, and the whole
typing run is clamped to MIN_TYPING..MAX_TYPING seconds so short quotes
don't flash by and long ones don't drag.
"""
import os
import random
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw

from composite_card import (
    draw_attribution_block,
    get_background,
    layout_quote_card,
    shifted_background,
)

FPS = 30
SR = 48000
FIRST_KEY_AT = 0.05
BASE_CHAR_INTERVAL = 0.048   # ~21 chars/sec
MIN_TYPING = 4.5
MAX_TYPING = 8.0
HOLD_AFTER = 2.5             # fully-lit card held after the last key


def build_timeline(lines, seed):
    """-> (events, typing_end). Each event is (time, line_idx, chars_in_line,
    kind) where kind is 'key', 'space' or 'return' (a deep stroke for the
    line break, played before the first key of a new line)"""
    rng = random.Random(seed)

    def pass_(scale):
        t = FIRST_KEY_AT
        ev = []
        for li, line in enumerate(lines):
            if li > 0:
                ev.append((t, li, 0, "return"))
                t += 0.16 * scale
            for ci, ch in enumerate(line):
                ev.append((t, li, ci + 1, "space" if ch == " " else "key"))
                step = BASE_CHAR_INTERVAL * scale * rng.uniform(0.7, 1.35)
                if ch in ",;:":
                    step += 0.10 * scale
                elif ch in ".?!":
                    step += 0.16 * scale
                t += step
        return ev, t

    ev, end = pass_(1.0)
    span = end - FIRST_KEY_AT
    target = min(max(span, MIN_TYPING), MAX_TYPING)
    if abs(target - span) > 1e-6:
        rng = random.Random(seed)
        ev, end = pass_(target / span)
    last_key = ev[-1][0]
    return ev, last_key


# ---------------------------------------------------------------- audio
# Real keystrokes sliced from a mechanical-keyboard recording (see
# extract_key_samples.py), not synthesis: sfx/keys/key-*.wav for letters,
# space-*.wav (the deepest strokes) for the space bar and line breaks.
# Each hit gets a small random gain/pitch nudge and never repeats the
# previous sample, so fast typing doesn't sound like a loop.

KEY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sfx", "keys")


def _load_bank():
    bank = {"key": [], "space": []}
    for name in sorted(os.listdir(KEY_DIR)):
        if not name.endswith(".wav"):
            continue
        with wave.open(os.path.join(KEY_DIR, name)) as w:
            assert w.getframerate() == SR and w.getnchannels() == 1
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
        bank["space" if name.startswith("space") else "key"].append(x)
    if not bank["key"] or not bank["space"]:
        raise SystemExit(f"no key samples in {KEY_DIR} - run extract_key_samples.py")
    return bank


def _repitch(x, ratio):
    idx = np.arange(0, len(x) - 1, ratio)
    return np.interp(idx, np.arange(len(x)), x)


def synth_audio(events, total_s, seed, path):
    rng = random.Random(seed + 1)
    bank = _load_bank()
    buf = np.zeros(int(SR * (total_s + 0.5)))
    last = {"key": -1, "space": -1}
    for t, _, _, kind in events:
        pool = "key" if kind == "key" else "space"      # line breaks use a deep stroke too
        choices = [i for i in range(len(bank[pool])) if i != last[pool]] or [0]
        last[pool] = rng.choice(choices)
        snd = _repitch(bank[pool][last[pool]], rng.uniform(0.96, 1.04))
        snd = snd * rng.uniform(0.82, 1.0) * (1.1 if kind == "return" else 1.0)
        i = int(t * SR)
        buf[i: i + len(snd)] += snd[: len(buf) - i]
    buf = buf[: int(SR * total_s)]
    buf = np.tanh(buf * 0.9)                              # soft limit where fast keys stack
    buf *= 0.8 / max(np.abs(buf).max(), 1e-6)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((buf * 32767).astype(np.int16).tobytes())


# ---------------------------------------------------------------- video

def smoothstep(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def render_reel(quote_text, attribution, source, row_id, out_path="typewriter_reel.mp4",
                work_wav="typewriter_audio.wav"):
    bg = shifted_background(get_background(attribution, row_id))
    w, h = bg.size
    bg_arr = np.asarray(bg, dtype=np.float32)
    lay = layout_quote_card(w, h, quote_text, row_id)
    lines = lay["lines"]

    # Attribution/source/handle drawn once on a transparent layer, then
    # faded in alongside the statue.
    attr_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_attribution_block(ImageDraw.Draw(attr_layer), w, h, lay, attribution, source)
    attr_alpha = np.asarray(attr_layer.getchannel("A"), dtype=np.float32) / 255.0

    events, typing_end = build_timeline(lines, seed=int(row_id) if str(row_id).isdigit() else 0)
    total_s = typing_end + HOLD_AFTER
    n_frames = int(round(total_s * FPS))

    synth_audio(events, total_s, seed=int(row_id) if str(row_id).isdigit() else 0, path=work_wav)

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-",
         "-i", work_wav,
         "-vf", "scale=1080:1890,pad=1080:1920:0:15:color=black,setsar=1",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), "-crf", "18", "-preset", "slow",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{total_s:.3f}", "-shortest",
         out_path],
        stdin=subprocess.PIPE,
    )

    # RGBA->RGB keeps the straight colour; coverage comes from attr_alpha
    attr_rgb = np.asarray(attr_layer.convert("RGB"), dtype=np.float32)
    fade_span = typing_end
    for f in range(n_frames):
        t = f / FPS
        a = smoothstep(t / fade_span)
        frame = bg_arr * a
        a_layer = attr_alpha * a
        frame = frame * (1 - a_layer[..., None]) + attr_rgb * a_layer[..., None]
        img = Image.fromarray(np.clip(frame + 0.5, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img)

        # typed quote - state = last event with time <= t
        done = [e for e in events if e[0] <= t]
        if done:
            _, li, nch, _ = done[-1]
            y = lay["y_start"]
            for idx, line in enumerate(lines):
                if idx < li:
                    d.text((lay["x_margin"], y), line, font=lay["quote_font"], fill=(255, 255, 255))
                elif idx == li and nch:
                    d.text((lay["x_margin"], y), line[:nch], font=lay["quote_font"], fill=(255, 255, 255))
                y += lay["line_height"]
        ff.stdin.write(img.tobytes())

    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit("ffmpeg failed")
    return total_s, typing_end, len(events)


if __name__ == "__main__":
    quote_text, attribution, source, row_id = sys.argv[1:5]
    out = sys.argv[5] if len(sys.argv) > 5 else "typewriter_reel.mp4"
    total, typing_end, n = render_reel(quote_text, attribution, source, row_id, out_path=out)
    print(f"{out}: {total:.1f}s total, typing ends at {typing_end:.2f}s, {n} key events")
