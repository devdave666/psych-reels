"""'Small steps light the day' - the progress principle. A grid of 100 paper lanterns. 1080x1920, 20 s.

Amabile & Kramer (2011, The Progress Principle; ~12,000 daily diary entries from 238 professionals in 26 project teams,
7 companies): progress in meaningful work was involved in 76% of people's best days.  Self-reported, correlational diaries
of knowledge workers.  Here: 100 dark lanterns (best days); on the drop (t = 10 s) 76 of them light up one by one while
the counter climbs to 76%.  Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python progress_reel.py out_silent.mp4      render
       python progress_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
"""
import math
import subprocess
import sys
from pathlib import Path

import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from stickrig import clamp, lerp, smooth

W, H, FPS, DUR = 1080, 1920, 30, 20.0
SUB, SHUTTER = 4, 0.5
FONTS = Path(__file__).resolve().parent.parent / "fonts"
SAFE = (140, 260, 940, 1480)

T_DROP = 10.0
T_NUM = 10.0
rng = np.random.default_rng(11)
COLS, ROWS, SP, X0, Y0 = 10, 10, 76, 540 - 4.5 * 76, 725
POS = [(X0 + c * SP, Y0 + r * 66) for r in range(ROWS) for c in range(COLS)]
PHASE = rng.uniform(0, 6.283, 100)
LIT = sorted(rng.choice(100, 76, replace=False).tolist(), key=lambda i: (POS[i][1] // SP) * 4 + rng.uniform(0, 14))
# ignition times: accelerating wave over the drop
IGN = {i: 10.0 + 4.0 * (k / 75) ** 0.85 for k, i in enumerate(LIT)}
IGN_T = sorted(IGN.values())
STARS = [(rng.uniform(0, W), rng.uniform(0, 1500), rng.uniform(1, 3), rng.uniform(0, 6.28)) for _ in range(90)]


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def count(t):
    return sum(1 for x in IGN_T if t >= x)


def lantern(c, x, y, lit, pop, a):
    if lit > 0:
        gl = cairo.RadialGradient(x, y, 6, x, y, 95)
        gl.add_color_stop_rgba(0, 1, 0.75, 0.35, 0.55 * lit * a); gl.add_color_stop_rgba(1, 1, 0.6, 0.3, 0)
        c.set_source(gl); c.rectangle(x - 100, y - 100, 200, 200); c.fill()
    s = 1 + 0.35 * pop
    c.save(); c.translate(x, y); c.scale(s, s)
    body = mix3((0.20, 0.22, 0.40), (1.0, 0.72, 0.30), lit)
    c.set_source_rgba(*body, a)
    r = 12
    w, h = 22, 29
    c.new_sub_path(); c.arc(w - r, -h + r, r, -math.pi / 2, 0); c.arc(w - r + 4, h - r, r, 0, math.pi / 2)
    c.arc(-w + r - 4, h - r, r, math.pi / 2, math.pi); c.arc(-w + r, -h + r, r, math.pi, 1.5 * math.pi); c.close_path(); c.fill()
    c.set_source_rgba(*mix3((0.12, 0.13, 0.26), (0.55, 0.30, 0.12), lit), a)
    c.rectangle(-14, -h - 5, 28, 6); c.fill(); c.rectangle(-12, h - 1, 24, 5); c.fill()
    if lit > 0:
        c.set_source_rgba(1, 0.95, 0.75, 0.9 * lit * a); c.arc(0, 2, 8, 0, 2 * math.pi); c.fill()
    c.restore()


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    warm = smooth(count(t) / 76) if t >= T_DROP else 0.0
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *mix3((0.05, 0.05, 0.15), (0.14, 0.09, 0.26), warm))
    g.add_color_stop_rgb(0.6, *mix3((0.09, 0.08, 0.22), (0.38, 0.17, 0.35), warm))
    g.add_color_stop_rgb(1, *mix3((0.12, 0.09, 0.22), (0.62, 0.28, 0.36), warm))
    c.set_source(g); c.rectangle(0, 0, W, H); c.fill()
    for sx, sy, sr, sp in STARS:
        c.set_source_rgba(1, 1, 1, 0.25 + 0.2 * math.sin(t * 1.5 + sp)); c.arc(sx, sy, sr, 0, 2 * math.pi); c.fill()
    for i, (px, py) in enumerate(POS):
        r_ = i // COLS
        a = smooth((t - (0.6 + 0.28 * r_)) / 0.7)
        if a <= 0:
            continue
        y = py + 7 * math.sin(t * 1.2 + PHASE[i]) + 40 * (1 - a)
        x = px + 4 * math.sin(t * 0.9 + PHASE[i] * 2)
        lit = smooth((t - IGN[i]) / 0.3) if i in IGN else 0.0
        pop = math.exp(-(t - IGN[i]) / 0.14) if i in IGN and t >= IGN[i] else 0.0
        lantern(c, x, y, lit, pop, a)
    f2 = t - T_DROP
    if 0 <= f2 < 0.3:
        c.set_source_rgba(1, 0.9, 0.7, 0.35 * (1 - f2 / 0.3) ** 2); c.paint()
    buf = np.frombuffer(surf.get_data(), np.uint8).reshape(H, W, 4)
    return buf[:, :, 2::-1].astype(np.float32)


_FC = {}


def font(name, size):
    if (name, size) not in _FC:
        _FC[(name, size)] = ImageFont.truetype(str(FONTS / f"IBMPlexSerif-{name}.ttf"), size)
    return _FC[(name, size)]


def win(t, t0, t1, fi=0.35, fo=0.35):
    return clamp((t - t0) / fi) * clamp((t1 - t) / fo)


def ctext(d, xy, s, f, fill, a):
    if a > 0.01:
        d.text((xy[0] + 2, xy[1] + 3), s, font=f, fill=(0, 0, 0, int(130 * a)), anchor="mm")
        d.text(xy, s, font=f, fill=(*fill, int(255 * a)), anchor="mm")


WHITE = (250, 246, 240)
ROSE = (255, 170, 190)
GOLD = (255, 214, 120)


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 3.4)
    ctext(d, (540, 380), "Think of your best day.", font("Bold", 56), WHITE, h)
    ctext(d, (540, 460), "What made it great?", font("Bold", 62), ROSE, h)
    ctext(d, (540, 380), "A big win?", font("Bold", 56), (190, 205, 240), win(t, 5.4, 7.4, 0.5, 0.3))
    ctext(d, (540, 380), "Or a small step forward?", font("Bold", 52), GOLD, win(t, 7.6, 9.8, 0.5, 0.3))
    ctext(d, (540, 380), "Small steps forward.", font("Bold", 58), GOLD, win(t, 10.2, 14.4, 0.3, 0.3))
    if t >= T_NUM:
        pop = max([math.exp(-(t - x) / 0.1) for x in IGN_T if t >= x - 0.0] or [0.0])
        ctext(d, (540, 540), f"{count(t)}%", font("Bold", int(150 + 14 * pop)), GOLD, win(t, T_NUM, 20.1, 0.2, 0.1))
        ctext(d, (540, 636), "of best days involved progress", font("Regular", 30), WHITE, win(t, 11.0, 20.1, 0.4, 0.1))
    p = win(t, 14.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 330), "Progress makes the day.", font("Bold", 52), WHITE, p)
    ctext(d, (540, 400), "Take one small step.", font("Bold", 52), ROSE, p)
    q = win(t, 15.2, 20.1, 0.6, 0.1)
    ctext(d, (540, 1440), "Amabile & Kramer, 2011 · 238 diaries", font("Regular", 27), WHITE, q)
    return ov


def compose(frame, t, debug=False):
    img = Image.fromarray(frame.clip(0, 255).astype(np.uint8)).convert("RGBA")
    img.alpha_composite(hud(t))
    if debug:
        ImageDraw.Draw(img).rectangle(SAFE, outline=(255, 0, 0, 255), width=3)
    out = img.convert("RGB")
    if t < 0.4:
        out = Image.eval(out, lambda v: int(v * smooth(t / 0.4)))
    return out


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "progress_silent.mp4"
    if out == "stills":
        for s in sys.argv[2:]:
            compose(render(float(s)), float(s), debug=True).save(f"still_{float(s):05.2f}.png")
        return
    n = int(DUR * FPS)
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-c:v", "libx264", "-crf", "15", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)
    for f in range(n):
        t0 = f / FPS
        acc = np.zeros((H, W, 3), np.float32)
        for s in range(SUB):
            acc += render(max(0.0, t0 + ((s + 0.5) / SUB - 0.5) * SHUTTER / FPS))
        ff.stdin.write(compose(acc / SUB, t0).tobytes())
        if f % 60 == 0:
            print("frame", f, "/", n, flush=True)
    ff.stdin.close(); ff.wait()
    print("done", out, n, "frames")


if __name__ == "__main__":
    main()
