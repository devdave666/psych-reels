"""'I don't' vs 'I can't' - empowered refusal. Two shelves of ten candles in a night wind. 1080x1920, 20 s.

Patrick & Hagtvedt (2012, Journal of Consumer Research), study 3: 30 working women with personal health goals were told to
refuse temptation with "I don't ..." , "I can't ..." or just "no" and to report every day for 10 days for as long as the
strategy kept working.  8 of 10 in the "don't" group kept going all 10 days, vs 1 of 10 for "can't" (3 of 10 control);
mean days 9.2 vs 2.9.  Here each candle is one participant: a wind gust blows on every "day" (one per beat, 4.0-8.5 s);
a candle goes out on the gust after its last day.  The individual persistence values are illustrative but match the
reported counts and means exactly (can't: 1x10 + 1,1,2,2,2,2,3,3,3 -> mean 2.9; don't: 8x10 + 5,7 -> mean 9.2).
At the drop (10.0 s) the eight "don't" flames flare up and the big number lands.
Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python dontcant_reel.py out_silent.mp4      render
       python dontcant_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
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

CREAM = (250, 240, 222)
AMBER = (255, 184, 72)
DIM = (150, 150, 190)
T_DROP = 10.0
DAYS = 10
T_DAY = [4.0 + 0.5 * d for d in range(DAYS)]          # gust / day tick d+1 at 4.0, 4.5 ... 8.5 s
CANT = [10, 1, 3, 2, 1, 2, 3, 2, 3, 2]                # days persisted per candle (sum 29 -> mean 2.9)
DONT = [10, 10, 5, 10, 10, 10, 7, 10, 10, 10]         # sum 92 -> mean 9.2
XS = [180 + 80 * i for i in range(10)]
ROW_Y = {"cant": 900.0, "dont": 1290.0}               # shelf top (candle base)


def out_time(p):
    """A candle that lasted p days goes out on the gust of day p+1; p == 10 never goes out."""
    return None if p >= DAYS else T_DAY[p] + 0.12


def gust(t):
    """Wind strength 0..1: a short swell on every day tick."""
    g = 0.0
    for td in T_DAY:
        d = t - td
        if -0.05 < d < 0.45:
            g = max(g, math.sin(math.pi * clamp((d + 0.05) / 0.5)) ** 2)
    return g


def day_now(t):
    return sum(1 for td in T_DAY if t >= td)


rng = np.random.default_rng(11)
STARS = [(rng.uniform(0, W), rng.uniform(0, H * 0.9), rng.uniform(1.0, 2.6), rng.uniform(0, 6.28)) for _ in range(140)]
PH = rng.uniform(0, 6.28, (2, 10, 3))


def candle(c, x, base, height, life, t, flare, phase, dim):
    """Wax, wick, flame (life 0..1), smoke after it dies."""
    wax_top = base - height
    wcol = (0.93 * (1 - 0.35 * dim), 0.89 * (1 - 0.35 * dim), 0.82 * (1 - 0.3 * dim))
    g = cairo.LinearGradient(x - 20, 0, x + 20, 0)
    g.add_color_stop_rgb(0, *(v * 0.78 for v in wcol))
    g.add_color_stop_rgb(0.45, *wcol)
    g.add_color_stop_rgb(1, *(v * 0.7 for v in wcol))
    c.set_source(g)
    c.rectangle(x - 19, wax_top, 38, height); c.fill()
    c.save(); c.translate(x, wax_top); c.scale(1, 0.28); c.arc(0, 0, 19, 0, 2 * math.pi); c.restore()
    c.set_source_rgb(*(min(1, v * 1.04) for v in wcol)); c.fill()
    c.set_source_rgba(0.12, 0.08, 0.06, 1); c.set_line_width(3)               # wick
    c.move_to(x, wax_top - 2); c.line_to(x + 1.5, wax_top - 14); c.stroke()
    if life > 0.01:
        wind = gust(t)
        fl = 1 + 0.06 * math.sin(t * 17 + phase[0]) + 0.05 * math.sin(t * 29 + phase[1]) + 0.03 * math.sin(t * 43 + phase[2])
        fh = (46 + 26 * flare) * fl * (0.55 + 0.45 * life) * (1 - 0.25 * wind)
        fw = (11 + 4 * flare) * (0.6 + 0.4 * life)
        lean = (8 + 34 * wind) * (1 if life > 0.99 else 1.6) + 3 * math.sin(t * 9 + phase[0])
        bx, by = x + 1.5, wax_top - 10
        tx, ty = bx + lean, by - fh
        halo = (110 + 80 * flare) * life
        rg = cairo.RadialGradient(bx, by - fh * 0.4, 4, bx, by - fh * 0.4, halo)
        rg.add_color_stop_rgba(0, 1, 0.72, 0.30, 0.42 * life * (1 + 0.6 * flare))
        rg.add_color_stop_rgba(1, 1, 0.55, 0.2, 0)
        c.set_source(rg); c.arc(bx, by - fh * 0.4, halo, 0, 2 * math.pi); c.fill()
        c.move_to(bx - fw, by - fh * 0.15)
        c.curve_to(bx - fw, by - fh * 0.55, tx - fw * 0.3, ty + fh * 0.35, tx, ty)
        c.curve_to(tx + fw * 0.3, ty + fh * 0.35, bx + fw, by - fh * 0.55, bx + fw, by - fh * 0.15)
        c.curve_to(bx + fw, by + fw * 0.6, bx - fw, by + fw * 0.6, bx - fw, by - fh * 0.15)
        c.close_path()
        fg = cairo.RadialGradient(bx + lean * 0.2, by - fh * 0.25, 1, bx + lean * 0.3, by - fh * 0.4, fh * 0.85)
        fg.add_color_stop_rgba(0, 1, 1, 0.92, life)
        fg.add_color_stop_rgba(0.35, 1, 0.86, 0.38, life)
        fg.add_color_stop_rgba(0.8, 1, 0.48, 0.12, 0.85 * life)
        fg.add_color_stop_rgba(1, 0.9, 0.3, 0.1, 0.0)
        c.set_source(fg); c.fill_preserve()
        c.set_source_rgba(0.35, 0.55, 1.0, 0.35 * life); c.set_line_width(2); c.stroke()


def smoke(c, x, top, d):
    if 0 <= d < 2.2:
        for k in range(14):
            u = k / 13
            yy = top - 14 - 260 * u * min(1, d / 1.2 + 0.2)
            xx = x + 18 * math.sin(u * 7 + d * 3) + 60 * u * u
            a = 0.30 * (1 - u) * (1 - d / 2.2)
            c.set_source_rgba(0.75, 0.75, 0.85, a)
            c.arc(xx, yy, 5 + 16 * u, 0, 2 * math.pi); c.fill()


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    warm = smooth((t - T_DROP) / 0.8)
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, 0.05, 0.05, 0.14)
    g.add_color_stop_rgb(0.55, lerp(0.10, 0.16, warm), lerp(0.08, 0.09, warm), lerp(0.22, 0.20, warm))
    g.add_color_stop_rgb(1, lerp(0.16, 0.30, warm), lerp(0.08, 0.13, warm), lerp(0.20, 0.14, warm))
    c.set_source(g); c.rectangle(0, 0, W, H); c.fill()
    for x, y, r, ph in STARS:
        c.set_source_rgba(1, 1, 1, 0.25 + 0.25 * math.sin(t * 1.7 + ph))
        c.arc(x, y, r, 0, 2 * math.pi); c.fill()

    wind = gust(t)                                                                # wind streaks
    for k in range(9):
        for td in T_DAY:
            d = t - td
            if -0.05 < d < 0.5:
                u = (d + 0.05) / 0.55
                y = 700 + 75 * k + 20 * math.sin(k * 2.1 + td)
                x0 = -400 + 1900 * u - 120 * (k % 3)
                c.set_source_rgba(0.75, 0.8, 1, 0.10 * math.sin(math.pi * u))
                c.set_line_width(3)
                c.move_to(x0, y); c.curve_to(x0 + 120, y - 18, x0 + 240, y + 12, x0 + 360, y - 6); c.stroke()

    melt = 18 * clamp((t - 4.0) / 5.0)
    for ri, (row, ps) in enumerate((("cant", CANT), ("dont", DONT))):
        base = ROW_Y[row]
        dim = smooth((t - T_DROP) / 0.6) if row == "cant" else 0.0
        c.set_source_rgb(0.20, 0.13, 0.10); c.rectangle(130, base, 820, 22); c.fill()     # shelf
        c.set_source_rgba(1, 0.8, 0.5, 0.18 + 0.2 * warm * (row == "dont")); c.rectangle(130, base, 820, 3); c.fill()
        c.set_source_rgba(0, 0, 0, 0.35); c.rectangle(140, base + 22, 800, 10); c.fill()
        for i, x in enumerate(XS):
            ot = out_time(ps[i])
            life = 1.0 if ot is None else 1 - smooth((t - ot) / 0.22)
            flare = 0.0
            if row == "dont" and ot is None:
                flare = smooth((t - T_DROP) / 0.25) * (0.75 + 0.25 * math.exp(-(t - T_DROP) / 0.6))
            hgt = 120 - melt * (0.6 + 0.4 * ((i * 7) % 5) / 4)
            if row == "cant" and ot is None:
                life *= 1 - 0.45 * dim
            candle(c, x, base, hgt, life, t, flare, PH[ri, i], dim if ot is not None else 0)
            if ot is not None:
                smoke(c, x + 1.5, base - hgt - 10, t - ot)
    fl = t - T_DROP
    if 0 <= fl < 0.4:
        c.set_source_rgba(1, 0.85, 0.6, 0.35 * (1 - fl / 0.4) ** 2); c.paint()
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


def ctext(d, xy, s, f, fill, a):
    if a > 0.01:
        d.text((xy[0] + 2, xy[1] + 4), s, font=f, fill=(0, 0, 0, int(150 * a)), anchor="mm")
        d.text(xy, s, font=f, fill=(*fill, int(255 * a)), anchor="mm")


def alive(ps, t):
    return sum(1 for p in ps if out_time(p) is None or t < out_time(p))


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.25, 3.3)
    ctext(d, (540, 360), "Stop telling yourself", font("Bold", 62), CREAM, h)
    ctext(d, (540, 480), "“I can’t.”", font("Bold", 120), AMBER, h)
    # row labels (stay up the whole time, the 'can't' one dims after the drop)
    la = clamp((t - 0.6) / 0.4)
    dim = smooth((t - T_DROP) / 0.6)
    lc = tuple(int(lerp(a, b, dim)) for a, b in zip(CREAM, DIM))
    ca = smooth((t - T_DROP - 0.4) / 0.4)
    for y, s, col, a in ((640, "“I can’t”", lc, la * (1 - 0.3 * dim)), (1030, "“I don’t”", CREAM, la)):
        ctext(d, (540 - 95 * ca, y), s, font("BoldItalic", 54), col, a)
    ctext(d, (700, 640), "1 of 10", font("Bold", 50), DIM, ca)
    ctext(d, (700, 1030), "8 of 10", font("Bold", 50), AMBER, ca)
    nd = day_now(t)
    da = clamp((t - 3.5) / 0.3) * (1 - smooth((t - 9.6) / 0.3))
    if da > 0 and nd > 0:
        pop = math.exp(-(t - T_DAY[nd - 1]) / 0.15)
        ctext(d, (540, 330), "D A Y", font("Bold", 36), CREAM, da * 0.85)
        ctext(d, (540, 450), f"{nd}", font("Bold", int(170 + 30 * pop)), CREAM, da)
    # drop: the result
    ra = win(t, T_DROP, 14.2, 0.2, 0.4)
    if ra > 0:
        pop = 1 + 0.12 * math.exp(-(t - T_DROP) / 0.18)
        ctext(d, (540, 400), "8 of 10", font("Bold", int(150 * pop)), AMBER, ra)
        ctext(d, (540, 515), "kept going all 10 days", font("Bold", 44), CREAM, ra)
    p = win(t, 14.6, 20.1, 0.5, 0.1)
    ctext(d, (540, 345), "Don’t say “I can’t.”", font("Bold", 56), CREAM, p)
    ctext(d, (540, 445), "Say “I don’t.”", font("Bold", 92), AMBER, p)
    ctext(d, (540, 535), "You’re choosing, not losing.", font("Bold", 42), CREAM, p)
    ci = win(t, 15.2, 20.1, 0.6, 0.1)
    ctext(d, (540, 1390), "Patrick & Hagtvedt, 2012 · small field study,", font("Regular", 27), (200, 196, 220), ci)
    ctext(d, (540, 1430), "30 women, 10 days", font("Regular", 27), (200, 196, 220), ci)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "dontcant_silent.mp4"
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
