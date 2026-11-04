"""'The 20-minute nature pill' - time in nature and the stress hormone cortisol. A bare, drooping tree in a rainy city dusk
beside a red cortisol gauge; at the drop (t = 10 s) the rain stops, the sky turns green-gold, six leaf clusters burst open on
the beats (10.5 ... 13.0 s), a ring fills to 20 min and the gauge falls.  1080x1920, 20 s.

Hunter, Gillespie & Chen (2019, Frontiers in Psychology 10:722): 36 urban adults (of 44 recruited) took nature experiences
(>= 10 min, >= 3 times a week) for 8 weeks; salivary cortisol fell 21.3 %/hour beyond the 11.7 %/hour diurnal drop, and the
efficiency per minute was greatest at 20-30 minutes.  Small, self-selected, 92 % female sample (caveats go in the caption).
Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python nature_reel.py out_silent.mp4      render
       python nature_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
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
T_NUM = 10.2
T_FILL = 4.0                                    # seconds the ring takes to fill 0 -> 20 min
POPS = [10.5 + 0.5 * k for k in range(6)]       # six leaf clusters open on these beats (audio imports this)
BASE = (540, 1390)
GX, GY0, GY1 = 892, 560, 1100                   # cortisol gauge tube
RX, RY, RR = 540, 640, 128                      # timer ring
rng = np.random.default_rng(11)
RAIN = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.7, 1.3), rng.uniform(25, 60)) for _ in range(150)]
FIRE = [(rng.uniform(100, 980), rng.uniform(900, 1400), rng.uniform(1.5, 4.0), rng.uniform(0, 6.28)) for _ in range(60)]
CITY = []
_x = -20
while _x < W + 20:
    _w = int(rng.integers(60, 130)); _h = int(rng.integers(120, 340))
    CITY.append((_x, _w, _h, [bool(rng.random() < 0.35) for _ in range(12)]))
    _x += _w + int(rng.integers(0, 12))

RED = (0.96, 0.34, 0.30)
LEAF = (0.38, 0.86, 0.46)
GOLDC = (1.0, 0.84, 0.42)


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def tree(droop, sway):
    """Segments (x0, y0, x1, y1, width, depth) and tip points; deterministic."""
    segs, tips = [], []
    r = np.random.default_rng(3)

    def grow(x, y, a, ln, wd, d):
        a2 = a + droop * (0.16 * d) * (1 if math.sin(a) >= 0 else -1) + sway * 0.012 * d * math.sin(a * 3)
        x1 = x + ln * math.sin(a2); y1 = y - ln * math.cos(a2)
        segs.append((x, y, x1, y1, wd, d))
        if d >= 6:
            tips.append((x1, y1, a2))
            return
        for sgn in (-1, 1):
            grow(x1, y1, a2 + sgn * (0.42 + 0.14 * r.random()) + (r.random() - 0.5) * 0.15, ln * (0.74 + 0.05 * r.random()), wd * 0.68, d + 1)

    grow(BASE[0], BASE[1], 0.0, 150, 26, 0)
    return segs, tips


def pop_of(i, n):
    return min(5, int(6 * i / n))


def cort(t):                                     # cortisol gauge level 0..1
    if t < T_DROP:
        return 0.55 + 0.37 * smooth(t / 9.5)
    k = smooth((t - T_NUM) / T_FILL)
    return lerp(0.92, 0.28, k)


def minutes(t):
    return 20.0 * smooth((t - T_NUM) / T_FILL)


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    post = smooth((t - T_DROP) / 1.6) if t >= T_DROP else 0.0
    pre = smooth((t - 6.8) / 3.0) if t < T_DROP else 1.0           # clouds begin to part before the drop
    sky = cairo.LinearGradient(0, 0, 0, H)
    sky.add_color_stop_rgb(0, *mix3(mix3((0.08, 0.07, 0.14), (0.12, 0.12, 0.22), 0.4 * pre), (0.06, 0.20, 0.24), post))
    sky.add_color_stop_rgb(0.55, *mix3(mix3((0.15, 0.10, 0.20), (0.22, 0.17, 0.27), 0.4 * pre), (0.18, 0.46, 0.38), post))
    sky.add_color_stop_rgb(1, *mix3(mix3((0.24, 0.13, 0.17), (0.30, 0.20, 0.22), 0.4 * pre), (0.86, 0.74, 0.40), post))
    c.set_source(sky); c.paint()
    gl = cairo.RadialGradient(540, 1180, 20, 540, 1180, 820)
    gl.add_color_stop_rgba(0, 1.0, 0.86, 0.45, 0.60 * post); gl.add_color_stop_rgba(1, 1.0, 0.8, 0.4, 0)
    c.set_source(gl); c.paint()
    for (x, w, h, wins) in CITY:                                     # city silhouette
        col = mix3((0.07, 0.06, 0.11), (0.08, 0.20, 0.20), post)
        c.set_source_rgb(*col); c.rectangle(x, 1500 - h, w, h + 420); c.fill()
        for i, on in enumerate(wins):
            if on:
                wx = x + 12 + (i % 3) * 30; wy = 1500 - h + 24 + (i // 3) * 40
                if wy < 1480:
                    c.set_source_rgba(1.0, 0.82, 0.45, 0.55 - 0.3 * post); c.rectangle(wx, wy, 14, 20); c.fill()
    g = cairo.LinearGradient(0, 1380, 0, 1560)                       # ground
    g.add_color_stop_rgb(0, *mix3((0.10, 0.10, 0.14), (0.20, 0.50, 0.28), post))
    g.add_color_stop_rgb(1, *mix3((0.05, 0.05, 0.08), (0.08, 0.26, 0.16), post))
    c.set_source(g)
    c.move_to(0, 1420); c.curve_to(300, 1360, 780, 1360, W, 1420); c.line_to(W, H); c.line_to(0, H); c.close_path(); c.fill()
    ra = (1 - smooth((t - 9.6) / 0.5)) * (0.85 - 0.35 * pre)         # rain stops at the drop
    if ra > 0.01:
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        for rx, ry, sp, ln in RAIN:
            y = (ry + t * 900 * sp) % (H + 100) - 50
            x = rx - y * 0.12
            c.set_source_rgba(0.7, 0.78, 0.95, 0.45 * ra); c.set_line_width(2.4)
            c.move_to(x, y); c.line_to(x - ln * 0.12, y + ln); c.stroke()
    droop = max(0.0, 0.9 * (1 - smooth((t - 6.8) / 3.5))) if t < T_DROP + 1 else 0.0
    sway = math.sin(t * 1.7) * (0.3 + 0.7 * post)
    segs, tips = tree(droop, sway)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    bark = mix3((0.36, 0.30, 0.34), (0.40, 0.28, 0.18), post)
    for (x0, y0, x1, y1, wd, d) in segs:
        c.set_source_rgb(*bark); c.set_line_width(max(2.0, wd)); c.move_to(x0, y0); c.line_to(x1, y1); c.stroke()
    order = sorted(range(len(tips)), key=lambda i: tips[i][0])
    rank = {i: r for r, i in enumerate(order)}
    nt = len(tips)
    for i, (x, y, a) in enumerate(tips):
        k = pop_of(rank[i], nt)
        f = t - POPS[k]
        if f < 0:
            continue
        u = smooth(f / 0.5)
        sc = 1 + 0.4 * math.sin(clamp(f / 0.5) * math.pi) if f < 0.5 else 1.0
        for j in range(3):
            ox = 18 * math.cos(j * 2.1 + i); oy = 14 * math.sin(j * 2.1 + i * 1.3)
            col = mix3(LEAF, (0.62, 0.95, 0.40), (math.sin(i + j) + 1) / 4)
            r_ = 30 * u * sc
            lg = cairo.RadialGradient(x + ox, y + oy, 2, x + ox, y + oy, r_ * 1.9 + 1)
            lg.add_color_stop_rgba(0, *col, 0.30 * u); lg.add_color_stop_rgba(1, *col, 0)
            c.set_source(lg); c.arc(x + ox, y + oy, r_ * 1.9 + 1, 0, 2 * math.pi); c.fill()
            c.set_source_rgba(*col, 0.95 * u); c.save(); c.translate(x + ox, y + oy); c.rotate(a + j); c.scale(1.0, 0.62)
            c.arc(0, 0, r_, 0, 2 * math.pi); c.restore(); c.fill()
    for k, tp in enumerate(POPS):                                    # ring burst at the centre of each cluster
        f = t - tp
        if 0 <= f < 0.6:
            xs = [tips[i][0] for i in range(nt) if pop_of(rank[i], nt) == k]
            ys = [tips[i][1] for i in range(nt) if pop_of(rank[i], nt) == k]
            c.set_source_rgba(*GOLDC, 0.8 * (1 - f / 0.6)); c.set_line_width(6 * (1 - f / 0.6) + 1)
            c.arc(sum(xs) / len(xs), sum(ys) / len(ys), 25 + 150 * f / 0.6, 0, 2 * math.pi); c.stroke()
    for fx, fy, fr_, ph in FIRE:                                     # fireflies after the drop
        a = post * (0.35 + 0.35 * math.sin(t * 2.0 + ph))
        if a > 0.02:
            x = fx + 20 * math.sin(t * 0.8 + ph); y = fy - ((t * 18 + ph * 40) % 500) * 0.4
            c.set_source_rgba(1.0, 0.95, 0.65, a); c.arc(x, y, fr_, 0, 2 * math.pi); c.fill()
    lv = cort(t)                                                     # cortisol gauge
    c.set_source_rgba(0.05, 0.05, 0.08, 0.55)
    c.rectangle(GX - 20, GY0, 40, GY1 - GY0); c.fill()
    gcol = mix3(RED, (0.45, 0.9, 0.55), smooth((0.92 - lv) / 0.64)) if t >= T_DROP else RED
    top = GY1 - lv * (GY1 - GY0)
    c.set_source_rgb(*gcol); c.rectangle(GX - 20, top, 40, GY1 - top); c.fill()
    c.set_source_rgba(1, 1, 1, 0.7); c.set_line_width(3); c.rectangle(GX - 20, GY0, 40, GY1 - GY0); c.stroke()
    if 2.0 < t < T_DROP:
        pulse = 0.5 + 0.5 * math.sin(t * 6)
        gg = cairo.RadialGradient(GX, top, 4, GX, top, 70)
        gg.add_color_stop_rgba(0, *RED, 0.5 * pulse); gg.add_color_stop_rgba(1, *RED, 0)
        c.set_source(gg); c.arc(GX, top, 70, 0, 2 * math.pi); c.fill()
    if t >= T_DROP - 0.1:                                            # timer ring
        ra_ = smooth((t - T_DROP) / 0.4)
        m = minutes(t) / 20.0
        c.set_source_rgba(0.05, 0.1, 0.1, 0.45 * ra_); c.arc(RX, RY, RR, 0, 2 * math.pi); c.fill()
        c.set_source_rgba(1, 1, 1, 0.22 * ra_); c.set_line_width(14); c.arc(RX, RY, RR, 0, 2 * math.pi); c.stroke()
        if m > 0.002:
            c.set_line_cap(cairo.LINE_CAP_ROUND)
            for lw, al in ((30, 0.15), (14, 1.0)):
                c.set_source_rgba(*GOLDC, al * ra_); c.set_line_width(lw)
                c.arc(RX, RY, RR, -math.pi / 2, -math.pi / 2 + 2 * math.pi * m); c.stroke()
    f2 = t - T_DROP
    if 0 <= f2 < 0.3:
        c.set_source_rgba(0.95, 1.0, 0.9, 0.38 * (1 - f2 / 0.3) ** 2); c.paint()
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
        d.text((xy[0] + 2, xy[1] + 3), s, font=f, fill=(0, 0, 0, int(150 * a)), anchor="mm")
        d.text(xy, s, font=f, fill=(*fill, int(255 * a)), anchor="mm")


WHITE = (250, 246, 240)
MINTC = (170, 240, 190)
GOLD = (255, 215, 120)
ICE = (190, 205, 235)
PINK = (255, 170, 160)


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 3.5)
    ctext(d, (540, 380), "Feeling stressed?", font("Bold", 66), WHITE, h)
    ctext(d, (540, 466), "Your body feels it too.", font("Bold", 44), PINK, h)
    b = win(t, 3.8, 6.7, 0.4, 0.3)
    ctext(d, (540, 380), "The stress hormone", font("Bold", 46), ICE, b)
    ctext(d, (540, 456), "keeps climbing.", font("Bold", 62), WHITE, b)
    e = win(t, 6.9, 9.8, 0.4, 0.3)
    ctext(d, (540, 380), "Step outside.", font("Bold", 68), MINTC, e)
    ctext(d, (540, 456), "Find something green.", font("Bold", 46), WHITE, e)
    if t > 2.0:
        ctext(d, (GX, GY0 - 34), "cortisol", font("Regular", 26), WHITE, win(t, 2.0, 20.1, 0.5, 0.1))
    z = win(t, 10.2, 14.4, 0.3, 0.3)
    ctext(d, (540, 345), "Nature works fast.", font("Bold", 64), GOLD, z)
    ctext(d, (540, 410), "Stress drops fastest at", font("Bold", 38), WHITE, z)
    if t >= T_NUM:
        m = minutes(t)
        s = "20" if m >= 19.5 else str(int(round(m)))
        pop = 1 + 0.14 * math.sin(clamp((t - (T_NUM + T_FILL)) / 0.4) * math.pi) if t < T_NUM + T_FILL + 0.4 else 1
        a = win(t, T_NUM, 20.1, 0.2, 0.1)
        ctext(d, (RX, RY - 8), s, font("Bold", int(112 * pop)), GOLD, a)
        ctext(d, (RX, RY + 62), "min", font("Regular", 36), WHITE, a)
    p = win(t, 14.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 300), "Stressed? Go outside.", font("Bold", 54), WHITE, p)
    ctext(d, (540, 365), "20 minutes is the sweet spot.", font("Bold", 40), MINTC, p)
    q = win(t, 15.2, 20.1, 0.6, 0.1)
    ctext(d, (540, 1450), "Hunter, Gillespie & Chen · 2019", font("Regular", 27), WHITE, q)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "nature_silent.mp4"
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
