"""Save More Tomorrow - commit your future raises. A glowing glass reservoir that fills on every pay raise. 1080x1920, 20 s.

Thaler & Benartzi (2004, Journal of Political Economy): employees who said they could not afford to save more now were
offered a plan that raised their retirement saving automatically at each future pay raise.  78% of those offered joined,
80% of them stayed through the fourth raise, and their average saving rate rose from 3.5% to 13.6% over 40 months.
Here the reservoir starts at 3.5%; four glowing drops (one per raise, 4.0 / 5.5 / 7.0 / 8.5 s) fall in and each one lifts
the level a step.  No in-between percentages are shown (only the two reported endpoints).  At the drop (10.0 s) the
liquid surges to 13.6%, the tube lights up and the big number lands.
Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python savemore_reel.py out_silent.mp4      render
       python savemore_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
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

CREAM = (244, 240, 228)
GOLD = (255, 200, 90)
MINT = (140, 235, 205)
T_DROP = 10.0
T_RAISE = [4.0, 5.5, 7.0, 8.5]              # a drop lands in the tube at each of these times
FALL = 0.55                                  # seconds a drop falls before landing
TX0, TX1 = 400, 680                          # tube inner x
TB, TT = 1320, 640                           # tube bottom / top y
PMAX = 16.0                                  # % at the very top of the tube
# levels: 3.5% at the start, four equal visual steps toward ~12%, then the drop surge to 13.6%
STEPS = [3.5, 5.6, 7.7, 9.8, 11.9]


def ylev(p):
    return TB - (TB - TT) * p / PMAX


def level(t):
    p = STEPS[0] * smooth((t - 1.0) / 1.2)            # fills in during the hook
    for k, tr in enumerate(T_RAISE):
        p += (STEPS[k + 1] - STEPS[k]) * smooth((t - tr) / 0.45)
    p += (13.6 - STEPS[-1]) * smooth((t - T_DROP) / 0.35)
    # small slosh after each landing
    for tr in T_RAISE + [T_DROP]:
        d = t - tr
        if 0 < d < 1.5:
            p += 0.25 * math.sin(d * 14) * math.exp(-d * 3)
    return p


rng = np.random.default_rng(23)
STARS = [(rng.uniform(0, W), rng.uniform(0, H * 0.95), rng.uniform(0.8, 2.4), rng.uniform(0, 6.28)) for _ in range(150)]
BUB = [(rng.uniform(TX0 + 20, TX1 - 20), rng.uniform(0, 1), rng.uniform(3, 9), rng.uniform(0.08, 0.2)) for _ in range(40)]


def drop_xy(k, t):
    """Position of raise-drop k (None if not visible)."""
    tr = T_RAISE[k]
    u = (t - (tr - FALL)) / FALL
    if u < 0 or u > 1:
        return None
    y0 = 560.0
    y1 = ylev(STEPS[k])
    return 540.0, y0 + (y1 - y0) * u * u


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    glow = smooth((t - T_DROP) / 0.6)
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, 0.02, 0.06, 0.09)
    g.add_color_stop_rgb(0.6, lerp(0.03, 0.05, glow), lerp(0.12, 0.17, glow), lerp(0.15, 0.17, glow))
    g.add_color_stop_rgb(1, lerp(0.05, 0.16, glow), lerp(0.16, 0.16, glow), lerp(0.16, 0.10, glow))
    c.set_source(g); c.rectangle(0, 0, W, H); c.fill()
    for x, y, r, ph in STARS:
        c.set_source_rgba(0.8, 1, 0.95, 0.18 + 0.22 * math.sin(t * 1.5 + ph))
        c.arc(x, y, r, 0, 2 * math.pi); c.fill()

    p = level(t)
    yl = ylev(p)
    # ambient glow around the tube
    rg = cairo.RadialGradient(540, yl + 120, 20, 540, yl + 120, 520 + 160 * glow)
    rg.add_color_stop_rgba(0, 1, 0.75, 0.3, 0.16 + 0.22 * glow)
    rg.add_color_stop_rgba(1, 1, 0.6, 0.2, 0)
    c.set_source(rg); c.paint()

    # tick marks on the left of the tube (no numbers)
    for i in range(1, 16):
        y = ylev(i)
        c.set_source_rgba(0.7, 0.95, 0.9, 0.22 if i % 5 else 0.4)
        c.set_line_width(2)
        c.move_to(TX0 - 30, y); c.line_to(TX0 - 12 - (8 if i % 5 == 0 else 0), y); c.stroke()

    # liquid
    c.save()
    c.rectangle(TX0, TT, TX1 - TX0, TB - TT); c.clip()
    c.move_to(TX0, TB)
    for i in range(0, 29):
        x = TX0 + (TX1 - TX0) * i / 28
        wv = 5 * math.sin(x / 38 + t * 3.1) + 3 * math.sin(x / 17 - t * 4.7)
        for tr in T_RAISE + [T_DROP]:
            d = t - tr
            if 0 < d < 1.2:
                wv += 16 * math.exp(-d * 3.5) * math.cos((x - 540) / 30 - d * 18) * math.exp(-abs(x - 540) / 120)
        c.line_to(x, yl + wv)
    c.line_to(TX1, TB); c.close_path()
    lg = cairo.LinearGradient(0, yl, 0, TB)
    lg.add_color_stop_rgb(0, 1.0, lerp(0.80, 0.90, glow), lerp(0.40, 0.55, glow))
    lg.add_color_stop_rgb(0.25, 0.98, 0.62, 0.20)
    lg.add_color_stop_rgb(1, 0.70, 0.30, 0.10)
    c.set_source(lg); c.fill()
    for bx, ph, r, sp in BUB:                       # rising bubbles
        u = (ph + t * sp) % 1.0
        by = TB - (TB - yl) * u
        if by > yl + 10:
            c.set_source_rgba(1, 0.95, 0.75, 0.35 * (1 - u))
            c.arc(bx + 6 * math.sin(t * 2 + ph * 9), by, r, 0, 2 * math.pi); c.fill()
    c.restore()

    # glass tube
    c.set_line_width(8)
    c.set_source_rgba(0.75, 1, 0.95, 0.55 + 0.3 * glow)
    c.move_to(TX0 - 6, TT - 40); c.line_to(TX0 - 6, TB + 6)
    c.line_to(TX1 + 6, TB + 6); c.line_to(TX1 + 6, TT - 40); c.stroke()
    c.set_source_rgba(1, 1, 1, 0.18); c.rectangle(TX0 + 14, TT - 30, 14, TB - TT + 20); c.fill()   # glint
    c.set_source_rgba(0.08, 0.2, 0.22, 1); c.rectangle(TX0 - 40, TB + 10, TX1 - TX0 + 80, 26); c.fill()  # base
    c.set_source_rgba(0.6, 1, 0.9, 0.35); c.rectangle(TX0 - 40, TB + 10, TX1 - TX0 + 80, 3); c.fill()

    # 3.5% start line stays as a faint marker
    ya = ylev(3.5)
    ma = clamp((t - 2.0) / 0.4)
    c.set_source_rgba(0.7, 1, 0.9, 0.45 * ma); c.set_line_width(3); c.set_dash([10, 8])
    c.move_to(TX0 - 10, ya); c.line_to(TX1 + 40, ya); c.stroke(); c.set_dash([])

    # falling drops
    for k in range(4):
        xy = drop_xy(k, t)
        if xy:
            x, y = xy
            for r, a in ((40, 0.15), (22, 0.35)):
                c.set_source_rgba(1, 0.85, 0.4, a); c.arc(x, y, r, 0, 2 * math.pi); c.fill()
            c.set_source_rgba(1, 0.95, 0.7, 1)
            c.move_to(x, y - 28); c.curve_to(x + 16, y - 4, x + 16, y + 16, x, y + 16)
            c.curve_to(x - 16, y + 16, x - 16, y - 4, x, y - 28); c.fill()
        d = t - T_RAISE[k]
        if 0 <= d < 0.7:                                  # splash droplets
            for j in range(9):
                ang = math.pi * (0.15 + 0.7 * j / 8)
                v = 420
                sx = 540 - math.cos(ang) * v * d
                sy = ylev(STEPS[k]) - math.sin(ang) * v * d + 900 * d * d
                c.set_source_rgba(1, 0.85, 0.45, 0.8 * (1 - d / 0.7))
                c.arc(sx, sy, 6, 0, 2 * math.pi); c.fill()
    # drop: sparks shoot up out of the tube
    d = t - T_DROP
    if 0 <= d < 1.6:
        for j in range(26):
            ang = math.pi * (0.25 + 0.5 * ((j * 37) % 26) / 25)
            v = 500 + 300 * ((j * 13) % 7) / 6
            sx = 540 - math.cos(ang) * v * d
            sy = ylev(13.6) - math.sin(ang) * v * d + 500 * d * d
            c.set_source_rgba(1, 0.9, 0.55, 0.9 * (1 - d / 1.6))
            c.arc(sx, sy, 5, 0, 2 * math.pi); c.fill()
    if 0 <= d < 0.4:
        c.set_source_rgba(1, 0.9, 0.6, 0.35 * (1 - d / 0.4) ** 2); c.paint()
    buf = np.frombuffer(surf.get_data(), np.uint8).reshape(H, W, 4)
    return buf[:, :, 2::-1].astype(np.float32)


# ---------------------------------------------------------------- text (PIL, after motion blur)
_FC = {}


def font(name, size):
    if (name, size) not in _FC:
        _FC[(name, size)] = ImageFont.truetype(str(FONTS / f"IBMPlexSerif-{name}.ttf"), size)
    return _FC[(name, size)]


def win(t, t0, t1, fi=0.35, fo=0.35):
    return clamp((t - t0) / fi) * clamp((t1 - t) / fo)


def ctext(d, xy, s, f, fill, a, anchor="mm"):
    if a > 0.01:
        d.text((xy[0] + 2, xy[1] + 4), s, font=f, fill=(0, 0, 0, int(150 * a)), anchor=anchor)
        d.text(xy, s, font=f, fill=(*fill, int(255 * a)), anchor=anchor)


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.25, 3.4)
    ctext(d, (540, 350), "Can’t afford to save?", font("Bold", 64), CREAM, h)
    ctext(d, (540, 470), "Save your next raise.", font("Bold", 74), GOLD, h)
    ctext(d, (TX1 + 50, ylev(3.5)), "3.5%", font("Bold", 50), MINT, clamp((t - 2.0) / 0.4) * (1 - 0.4 * smooth((t - T_DROP) / 0.5)), "lm")
    # raise counter
    nr = sum(1 for tr in T_RAISE if t >= tr - FALL)
    ra = clamp((t - 3.45) / 0.25) * (1 - smooth((t - 9.4) / 0.3))
    if ra > 0 and nr > 0:
        pop = math.exp(-max(0, t - (T_RAISE[nr - 1] - FALL)) / 0.15)
        ctext(d, (540, 330), "P A Y   R A I S E", font("Bold", 36), CREAM, ra * 0.85)
        ctext(d, (540, 450), f"{nr}", font("Bold", int(160 + 30 * pop)), GOLD, ra)
    # drop: the result
    a = win(t, T_DROP, 14.2, 0.2, 0.4)
    if a > 0:
        pop = 1 + 0.12 * math.exp(-(t - T_DROP) / 0.18)
        ctext(d, (540, 395), "13.6%", font("Bold", int(160 * pop)), GOLD, a)
        ctext(d, (540, 515), "saved, up from 3.5%, in 40 months", font("Bold", 40), CREAM, a)
    p = win(t, 14.6, 20.1, 0.5, 0.1)
    ctext(d, (540, 340), "Future you says yes", font("Bold", 58), CREAM, p)
    ctext(d, (540, 440), "more easily.", font("Bold", 58), CREAM, p)
    ctext(d, (540, 545), "Commit the next raise today.", font("Bold", 52), GOLD, p)
    ci = win(t, 15.2, 20.1, 0.6, 0.1)
    ctext(d, (540, 1412), "Thaler & Benartzi, 2004 · one company,", font("Regular", 27), (200, 220, 215), ci)
    ctext(d, (540, 1450), "not a randomized trial", font("Regular", 27), (200, 220, 215), ci)
    return ov


def compose(frame, t, debug=False):
    img = Image.fromarray(frame.clip(0, 255).astype(np.uint8)).convert("RGBA")
    img.alpha_composite(hud(t))
    if debug:
        ImageDraw.Draw(img).rectangle(SAFE, outline=(255, 0, 0, 255), width=3)
    out = img.convert("RGB")
    if t < 0.3:
        out = Image.eval(out, lambda v: int(v * smooth(t / 0.3)))
    return out


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "savemore_silent.mp4"
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
