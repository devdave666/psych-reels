"""'Cap the scroll' - a phone glows in a cold blue room, its endless feed flicking up (0.5 ... 8.5 s, fast then slowing).
Three abstract app tiles on the screen each get a 10-minute timer ring that drains from 4.6 s to 9.4 s; the screen locks at
9.5 s.  At the drop (t = 10 s) the phone dims and sinks, the room turns to a warm dusk, and the feed cards lift off as
paper lanterns, one per beat (10.0 ... 13.0 s), drifting up into the sky.  Payoff text lands at 14.6 s.  1080x1920, 20 s.

Hunt, Marx, Lipson & Young (2018, Journal of Social and Clinical Psychology 37(10):751-768, 'No More FOMO: Limiting Social
Media Decreases Loneliness and Depression'): 143 University of Pennsylvania undergraduates, one week of baseline monitoring,
then randomly assigned to limit Facebook, Instagram and Snapchat to 10 minutes per platform per day, or use them as usual,
for three weeks (use checked with iPhone battery screenshots).  The limited group showed significant reductions in
loneliness and depression vs controls, most pronounced for those more depressed at baseline; both groups saw small drops in
anxiety and FOMO.  Caveats (caption): undergraduates, three platforms, three weeks, iPhone users only.  No app logos are drawn.
Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python scrollcap_reel.py out_silent.mp4      render
       python scrollcap_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
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
T_RING0, T_RING1 = 4.6, 9.4                      # timer rings drain
T_LOCK = 9.5                                     # screen locks
FLICKS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5]   # feed swipes: fast, then slowing
PINGS = [1.25, 2.75]                             # notification badge pops
FLICK_PX = 300.0
PHONE = (540.0, 1010.0, 400.0, 760.0)            # centre x, y, width, height
TILE_COL = [(1.0, 0.45, 0.45), (0.62, 0.48, 1.0), (1.0, 0.72, 0.30)]
LANTERN_T = [T_DROP + 0.5 * k for k in range(7)]  # one lantern per beat, 10.0 ... 13.0
rng = np.random.default_rng(1018)
CARD_COL = [tuple(rng.uniform(0.25, 0.55, 3)) for _ in range(40)]
LANTERNS = [(rng.uniform(-1, 1), rng.uniform(0.85, 1.15), rng.uniform(0, 6.28)) for _ in LANTERN_T]
# a few extra lanterns already far up the sky, drifting in from the payoff on
FAR = [(rng.uniform(170, 910), rng.uniform(760, 1300), rng.uniform(0.45, 0.75), rng.uniform(0, 6.28)) for _ in range(14)]
STARS = [(rng.uniform(0, W), rng.uniform(0, 1100), rng.uniform(0.8, 2.0), rng.uniform(0, 6.28)) for _ in range(60)]


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def glow(c, x, y, r, col, a):
    if a <= 0.003:
        return
    gr = cairo.RadialGradient(x, y, 1, x, y, r)
    gr.add_color_stop_rgba(0, *col, a); gr.add_color_stop_rgba(1, *col, 0)
    c.set_source(gr); c.arc(x, y, r, 0, 2 * math.pi); c.fill()


def rrect(c, x, y, w, h, r):
    c.new_sub_path()
    c.arc(x + w - r, y + r, r, -math.pi / 2, 0); c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi); c.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    c.close_path()


def warm_k(t):
    return smooth((t - T_DROP) / 1.6) if t >= T_DROP else 0.0


def feed_off(t):
    off = 0.0
    for tf in FLICKS:
        if t >= tf:
            off += FLICK_PX * (1 - (1 - clamp((t - tf) / 0.42)) ** 3)
    return off


def ring_left(t):
    return 1 - smooth((t - T_RING0) / (T_RING1 - T_RING0)) if t >= T_RING0 else 1.0


def phone_geom(t):
    """(cx, cy, scale, screen brightness)"""
    k = smooth((t - T_DROP) / 1.4) if t >= T_DROP else 0.0
    cx, cy, w, h = PHONE
    lockdim = 1 - 0.55 * smooth((t - T_LOCK) / 0.3) if t >= T_LOCK else 1.0
    return cx, lerp(cy, 1395, k), lerp(1.0, 0.42, k), lockdim * (1 - 0.9 * k)


def draw_feed(c, x0, y0, w, h, t, br):
    off = feed_off(t) + 6 * t
    card_h, gap = 230.0, 26.0
    step = card_h + gap
    first = int(off // step)
    for i in range(first, first + int(h // step) + 2):
        y = y0 + 150 + i * step - off
        if y > y0 + h or y + card_h < y0 + 130:
            continue
        col = CARD_COL[i % len(CARD_COL)]
        c.set_source_rgba(*mix3(col, (0.6, 0.75, 1.0), 0.35), 0.55 * br)
        rrect(c, x0 + 22, y, w - 44, card_h, 22); c.fill()
        c.set_source_rgba(0.85, 0.9, 1.0, 0.35 * br)
        c.arc(x0 + 62, y + 40, 18, 0, 2 * math.pi); c.fill()
        for k, ln in enumerate((0.55, 0.8, 0.4)):
            rrect(c, x0 + 40, y + 90 + k * 34, (w - 80) * ln, 16, 8); c.fill()


def draw_phone(c, t, wk):
    cx, cy, s, br = phone_geom(t)
    _, _, pw, ph = PHONE
    c.save(); c.translate(cx, cy); c.scale(s, s); c.translate(-pw / 2, -ph / 2)
    glow(c, pw / 2, ph / 2, 760, (0.35, 0.60, 1.0), 0.30 * br)
    c.set_source_rgb(*mix3((0.06, 0.07, 0.10), (0.12, 0.08, 0.08), wk))
    rrect(c, -16, -16, pw + 32, ph + 32, 64); c.fill()
    c.save(); rrect(c, 0, 0, pw, ph, 50); c.clip()
    sc = cairo.LinearGradient(0, 0, 0, ph)
    sc.add_color_stop_rgb(0, *(v * br for v in (0.16, 0.24, 0.42)))
    sc.add_color_stop_rgb(1, *(v * br for v in (0.08, 0.12, 0.26)))
    c.set_source(sc); c.paint()
    draw_feed(c, 0, 0, pw, ph, t, br)
    # top bar with the three app tiles and their 10-minute rings
    c.set_source_rgba(0.05, 0.08, 0.16, 0.92); c.rectangle(0, 0, pw, 132); c.fill()
    left = ring_left(t)
    rk = smooth((t - (T_RING0 - 0.4)) / 0.4) if t >= T_RING0 - 0.4 else 0.0
    for k in range(3):
        tx = pw / 2 + (k - 1) * 112
        ty = 70
        dead = 1 - left
        col = mix3(TILE_COL[k], (0.35, 0.37, 0.42), dead * 0.85)
        c.set_source_rgba(*col, br ** 0.5)
        rrect(c, tx - 34, ty - 34, 68, 68, 18); c.fill()
        c.set_source_rgba(1, 1, 1, 0.55 * br ** 0.5)
        c.arc(tx, ty, 12, 0, 2 * math.pi); c.fill()
        if rk > 0:
            c.set_line_width(7); c.set_source_rgba(1, 1, 1, 0.15 * rk); c.arc(tx, ty, 46, 0, 2 * math.pi); c.stroke()
            if left > 0.002:
                c.set_source_rgba(*mix3(TILE_COL[k], (1, 1, 1), 0.3), rk)
                c.arc(tx, ty, 46, -math.pi / 2, -math.pi / 2 + 2 * math.pi * left); c.stroke()
    c.restore()
    # notification badge pops
    for tp in PINGS:
        u = (t - tp) / 0.9
        if 0 <= u <= 1:
            sz = 1 + 0.35 * math.exp(-u * 10)
            a = clamp(u / 0.08) * clamp((1 - u) / 0.25)
            c.set_source_rgba(1, 0.28, 0.32, a)
            c.arc(pw - 10, 10, 26 * sz, 0, 2 * math.pi); c.fill()
    # lock: a padlock fades in on the dark screen
    if t >= T_LOCK:
        a = smooth((t - T_LOCK) / 0.25) * (1 - smooth((t - T_DROP - 0.6) / 0.6))
        c.set_source_rgba(1, 1, 1, 0.85 * a); c.set_line_width(14)
        c.arc(pw / 2, ph / 2 - 40, 46, math.pi, 2 * math.pi); c.stroke()
        rrect(c, pw / 2 - 72, ph / 2 - 40, 144, 116, 18); c.fill()
    c.restore()


def lantern_pos(k, t):
    t0 = LANTERN_T[k]
    if t < t0:
        return None
    u = t - t0
    sx, sp, ph = LANTERNS[k]
    _, _, s, _ = phone_geom(t0)
    x0 = 540 + sx * 70
    y0 = 1395 - 120
    x = x0 + sx * 230 * (1 - math.exp(-u / 1.8)) + 22 * math.sin(u * 1.6 + ph)
    y = y0 - sp * (120 * u + 50 * u * u / (1 + 0.25 * u))
    scale = clamp(u / 0.35) * lerp(1.0, 0.55, clamp(u / 9))
    return x, y, scale


def draw_lantern(c, x, y, s, t, ph, a=1.0):
    a *= clamp((y - 600) / 160)                      # fade out before reaching the text band
    if s <= 0.01 or a <= 0.01:
        return
    fl = 0.85 + 0.15 * math.sin(t * 9 + ph) * math.sin(t * 5.3 + ph * 2)
    glow(c, x, y, 150 * s, (1.0, 0.62, 0.30), 0.45 * fl * a)
    w, h = 74 * s, 96 * s
    c.save(); c.translate(x, y)
    gr = cairo.LinearGradient(0, -h / 2, 0, h / 2)
    gr.add_color_stop_rgba(0, 1.0, 0.86, 0.55, a)
    gr.add_color_stop_rgba(1, 1.0, 0.52, 0.25, a)
    c.set_source(gr)
    c.move_to(-w * 0.42, -h / 2); c.line_to(w * 0.42, -h / 2)
    c.curve_to(w * 0.62, -h * 0.1, w * 0.55, h * 0.35, w * 0.36, h / 2)
    c.line_to(-w * 0.36, h / 2)
    c.curve_to(-w * 0.55, h * 0.35, -w * 0.62, -h * 0.1, -w * 0.42, -h / 2)
    c.close_path(); c.fill()
    c.set_source_rgba(1.0, 0.97, 0.85, 0.9 * fl * a)
    c.arc(0, h * 0.32, 9 * s, 0, 2 * math.pi); c.fill()
    c.set_source_rgba(0.55, 0.25, 0.12, 0.35 * a); c.set_line_width(2.5 * s)
    for k in (-0.2, 0.2):
        c.move_to(w * k, -h / 2); c.line_to(w * k * 1.3, h / 2); c.stroke()
    c.restore()


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    wk = warm_k(t)
    bg = cairo.LinearGradient(0, 0, 0, H)
    bg.add_color_stop_rgb(0, *mix3((0.03, 0.05, 0.10), (0.10, 0.08, 0.24), wk))
    bg.add_color_stop_rgb(0.55, *mix3((0.05, 0.08, 0.15), (0.55, 0.24, 0.32), wk))
    bg.add_color_stop_rgb(0.85, *mix3((0.04, 0.06, 0.12), (0.95, 0.52, 0.30), wk))
    bg.add_color_stop_rgb(1, *mix3((0.03, 0.04, 0.08), (0.35, 0.16, 0.14), wk))
    c.set_source(bg); c.paint()
    for sx, sy, sr, sp in STARS:
        c.set_source_rgba(1, 0.95, 0.9, 0.55 * wk * (0.5 + 0.5 * math.sin(t * 1.4 + sp)))
        c.arc(sx, sy, sr, 0, 2 * math.pi); c.fill()
    # distant hills / horizon after the drop
    if wk > 0:
        c.set_source_rgba(0.16, 0.08, 0.14, wk)
        c.move_to(0, 1560)
        for x in range(0, W + 1, 20):
            c.line_to(x, 1520 + 40 * math.sin(x / 170) + 22 * math.sin(x / 61 + 1))
        c.line_to(W, H); c.line_to(0, H); c.close_path(); c.fill()
    fk = smooth((t - 14.0) / 2.0) if t >= 14.0 else 0.0
    for fx, fy, fs, fp in FAR:
        draw_lantern(c, fx + 10 * math.sin(t * 0.7 + fp), fy - 25 * (t - 14), fs * 0.6, t, fp, fk * 0.8)
    draw_phone(c, t, wk)
    for k in range(len(LANTERN_T)):
        p = lantern_pos(k, t)
        if p:
            draw_lantern(c, *p, t, LANTERNS[k][2])
    f2 = t - T_DROP
    if 0 <= f2 < 0.3:
        c.set_source_rgba(1, 0.85, 0.65, 0.40 * (1 - f2 / 0.3) ** 2); c.paint()
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
        d.text((xy[0] + 2, xy[1] + 3), s, font=f, fill=(0, 0, 0, int(200 * a)), anchor="mm")
        d.text(xy, s, font=f, fill=(*fill, int(255 * a)), anchor="mm")


WHITE = (250, 246, 240)
ICE = (170, 205, 255)
GOLD = (255, 214, 120)
PEACH = (255, 200, 170)


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.3, 4.0)
    ctext(d, (540, 340), "Scrolling all night", font("Bold", 64), WHITE, h)
    ctext(d, (540, 430), "and still feel lonely?", font("Bold", 64), ICE, h)
    b = win(t, 4.2, 9.8, 0.4, 0.3)
    ctext(d, (540, 320), "143 students got a limit:", font("Bold", 52), WHITE, b)
    ctext(d, (540, 420), "10 min per app, a day", font("Bold", 70), ICE, b)
    a = win(t, 10.2, 14.4, 0.4, 0.4)
    ctext(d, (540, 310), "3 weeks later:", font("Bold", 52), WHITE, a)
    ctext(d, (540, 408), "less lonely", font("Bold", 96), GOLD, a)
    a2 = win(t, 10.9, 14.4, 0.4, 0.4)
    ctext(d, (540, 500), "and less depressed", font("Bold", 46), PEACH, a2)
    p = win(t, 14.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 330), "Cap the scroll.", font("Bold", 76), WHITE, p)
    ctext(d, (540, 420), "Spend the time on real people.", font("Bold", 46), GOLD, p)
    q = win(t, 15.2, 20.1, 0.6, 0.1)
    ctext(d, (540, 492), "Hunt et al., 2018 · J. Social & Clinical Psychology", font("Regular", 27), WHITE, q)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "scrollcap_silent.mp4"
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
