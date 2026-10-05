"""Typewriter reel: black screen -> the quote is typed out letter by letter
with typewriter sounds, while the statue and the attribution/handle block
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
    kind) where kind is 'key', 'space' or 'return' (carriage return sound
    before the first key of a new line)."""
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
# Everything is filtered noise plus low "body" resonances - no pitched
# high sine tones (those read as beeps, not machinery). A short synthetic
# room tail and a gentle low-pass keep it warm rather than harsh.

def _env(n, decay):
    return np.exp(-np.arange(n) / (SR * decay))


def _bandpass(x, lo, hi):
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    gain = np.clip((freqs - lo) / (lo * 0.4 + 1), 0, 1) * np.clip((hi - freqs) / (hi * 0.4 + 1), 0, 1)
    y = np.fft.irfft(spec * gain, len(x))
    return y / (y.std() + 1e-9)          # unit level so component gains are comparable


def _noise(rng, n):
    return np.random.default_rng(rng.randrange(1 << 30)).standard_normal(n)


def _place(buf, snd, at):
    i = int(at * SR)
    if i < 0 or i >= len(buf):
        return
    buf[i: i + len(snd)] += snd[: len(buf) - i]


def _key_sound(rng, kind):
    n = int(SR * 0.16)
    t = np.arange(n) / SR
    heavy = kind == "space"
    out = np.zeros(n)
    # quiet high-band mechanical tick riding on the strike
    tick = _bandpass(_noise(rng, n), 2500, 6000) * _env(n, 0.0015) * 0.35
    # type-bar strike on the platen: mid-band noise, very short
    strike = _bandpass(_noise(rng, n), 700, 3800) * _env(n, 0.005) * (0.6 if heavy else 2.2)
    # wooden/metal body "thock"
    body = _bandpass(_noise(rng, n), 120, 520) * _env(n, 0.035 if heavy else 0.022) * (1.2 if heavy else 0.55)
    f0 = rng.uniform(75, 95) if heavy else rng.uniform(110, 170)
    thump = np.sin(2 * np.pi * f0 * t) * _env(n, 0.03 if heavy else 0.018) * (0.5 if heavy else 0.25)
    out += tick + strike + body + thump
    return out * rng.uniform(0.75, 1.0)


def _return_sound(rng):
    """Carriage return: rolling ratchet (noise gated at ~85Hz), then a slam."""
    n = int(SR * 0.26)
    t = np.arange(n) / SR
    gate = (np.sin(2 * np.pi * 85 * t) > 0.2).astype(float)
    zip_ = _bandpass(_noise(rng, n), 900, 3200) * gate * np.linspace(1, 0.5, n) * 0.28
    out = np.zeros(int(SR * 0.5))
    out[:n] += zip_
    slam = _key_sound(rng, "space") * 1.2
    _place(out, slam, 0.22)
    return out


def _bell():
    """Soft warm bell - low partials, longer decay, quiet."""
    n = int(SR * 1.4)
    t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * 1760 * t) * 0.6
         + np.sin(2 * np.pi * 2655 * t) * 0.25
         + np.sin(2 * np.pi * 3520 * t) * 0.1) * _env(n, 0.35)
    s[:int(SR * 0.003)] *= np.linspace(0, 1, int(SR * 0.003))
    return s * 0.14


def _room(buf, seed):
    """Short diffuse room tail, ~12% wet."""
    rng = np.random.default_rng(seed)
    n = int(SR * 0.09)
    ir = rng.standard_normal(n) * _env(n, 0.025)
    ir[0] = 0
    wet = np.convolve(buf, ir, mode="full")[: len(buf)]
    return buf + wet * (0.12 * np.abs(buf).max() / max(np.abs(wet).max(), 1e-9))


def synth_audio(events, total_s, bell_at, seed, path):
    rng = random.Random(seed + 1)
    buf = np.zeros(int(SR * (total_s + 0.5)))
    for t, _, _, kind in events:
        snd = _return_sound(rng) if kind == "return" else _key_sound(rng, kind)
        _place(buf, snd, t)
    _place(buf, _bell(), bell_at)
    buf = _room(buf, seed)
    buf = _bandpass(buf, 60, 9000)                      # tame harsh highs and rumble
    buf = buf[: int(SR * total_s)]
    buf = np.tanh(buf * 0.9)
    buf *= 0.6 / max(np.abs(buf).max(), 1e-6)           # peak ~ -3 dB
    pcm = (buf * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


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

    synth_audio(events, total_s, bell_at=typing_end + 0.12, seed=int(row_id) if str(row_id).isdigit() else 0,
                path=work_wav)

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
