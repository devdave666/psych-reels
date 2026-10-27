"""'Wipe the slate' - the fresh start effect. A chalkboard of a messy week, one figure. 1080x1920, 20 s.

Dai, Milkman & Riis (2014, Management Science): at a large university gym, the probability that a student visited on a given
day rose 47.1% at the start of a semester and 33.4% at the start of a week, relative to baseline (archival data, 'temporal
landmarks').  Here: scribbled failures pile up on the board while the figure sinks, an eraser wipes it clean on the drop
(t = 10 s), then a chalk bar chart grows to +47% on the beats of the drop (12.0, 12.5, 13.0 s).
Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python freshstart_reel.py out_silent.mp4      render
       python freshstart_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
"""
import math
import subprocess
import sys
from pathlib import Path

import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import stickrig as sr
from stickrig import clamp, lerp, smooth

W, H, FPS, DUR = 1080, 1920, 30, 20.0
SUB, SHUTTER = 4, 0.5
CHALK = (0.95, 0.94, 0.88)
CHALK_I = (243, 240, 226)
RED = (0.93, 0.52, 0.50)
MINT = (0.55, 0.95, 0.78)
GOLD = (1.0, 0.82, 0.35)
FONTS = Path(__file__).resolve().parent.parent / "fonts"
SAFE = (140, 260, 940, 1480)

BOARD = (160, 300, 920, 1000)            # x0, y0, x1, y1 of the slate
T_DROP = 10.0
WIPE = [(10.0, 10.45), (10.45, 10.9), (10.9, 11.35)]        # three passes (bands)
BANDS = [(540, 690), (690, 840), (840, 990)]
BARS_T = [12.0, 12.5, 13.0]
T_NUM = 12.0
T_FIRE = [14.0, 14.45, 14.9, 15.5, 16.2, 17.0]
HOP_T0 = 14.5
BASE_Y = 930
FEET = (540, 1462)

rng = np.random.default_rng(11)


def make_scribbles():
    items = []                                           # (t_start, duration, polylines)
    spots = [(250, 590), (520, 590), (790, 600), (250, 740), (520, 750), (790, 740), (300, 900), (560, 910), (800, 900)]
    for i, (sx, sy) in enumerate(spots):
        ts = 2.9 + i * 0.72
        kind = i % 3
        lines = []
        if kind == 0:                                    # crossed-out tally
            for k in range(4):
                lines.append([(sx + 22 * k, sy - 40), (sx + 22 * k + rng.uniform(-3, 3), sy + 40)])
            lines.append([(sx - 20, sy + 25), (sx + 90, sy - 25)])
        elif kind == 1:                                  # angry zigzag
            pts = [(sx - 70, sy)]
            for k in range(1, 9):
                pts.append((sx - 70 + k * 18, sy + (-38 if k % 2 else 38) + rng.uniform(-6, 6)))
            lines.append(pts)
        else:                                            # big X
            lines.append([(sx - 45, sy - 45), (sx + 45, sy + 45)])
            lines.append([(sx + 45, sy - 45), (sx - 45, sy + 45)])
        items.append((ts, 0.45, lines))
    return items


SCRIB = make_scribbles()
FIRE = []
for k, tf in enumerate(T_FIRE):
    cx0 = (760, 340, 600, 860, 250, 520)[k]
    cy0 = (660, 560, 520, 700, 520, 780)[k]
    col = ((1, 0.82, 0.35), (0.55, 0.95, 0.78), (1, 1, 1), (1, 0.6, 0.7), (0.55, 0.95, 0.78), (1, 0.82, 0.35))[k]
    FIRE.append((tf, cx0, cy0, col, [(rng.uniform(0, 6.283), rng.uniform(120, 330)) for _ in range(34)]))

SLUMP = sr.P(0.3, (0.14, 0.1), (-0.1, 0.1), (0.1, 0.25), (0.0, 0.25))


def fig_pose(t):
    base = sr.lerp_pose(sr.idle_pose(t), SLUMP, smooth((t - 2.0) / 3.5))
    if t > 8.6:
        base = sr.lerp_pose(base, sr.idle_pose(t), smooth((t - 8.6) / 0.9))     # inhale before the wipe
    if t > T_DROP:
        base = sr.lerp_pose(base, sr.CHEER, smooth((t - T_DROP) / 0.35))
    air = 0.0
    if t >= HOP_T0:
        ph = ((t - HOP_T0) / 0.5) % 1.0
        air = 4 * 24 * ph * (1 - ph)
        base = sr.lerp_pose(base, sr.HOP, math.sin(math.pi * ph))
    return base, air


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def star(c, x, y, r):
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        (c.move_to if i == 0 else c.line_to)(x + rr * math.cos(a), y + rr * math.sin(a))
    c.close_path()


def chalk_line(c, pts, frac, col, width=9, alpha=1.0):
    """Stroke the first `frac` of a polyline."""
    if frac <= 0:
        return
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    want = sum(seg) * min(1, frac)
    c.set_source_rgba(*col, alpha); c.set_line_width(width)
    c.set_line_cap(cairo.LINE_CAP_ROUND); c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.move_to(*pts[0])
    for i, s in enumerate(seg):
        if want >= s:
            c.line_to(*pts[i + 1]); want -= s
        else:
            f = want / s
            c.line_to(lerp(pts[i][0], pts[i + 1][0], f), lerp(pts[i][1], pts[i + 1][1], f))
            break
    c.stroke()


def eraser_pos(t):
    for k, (a, b) in enumerate(WIPE):
        if a <= t <= b:
            u = smooth((t - a) / (b - a))
            x = lerp(BOARD[0] - 40, BOARD[2] + 40, u) if k % 2 == 0 else lerp(BOARD[2] + 40, BOARD[0] - 40, u)
            return x, (BANDS[k][0] + BANDS[k][1]) / 2, k
    return None


def bar_steps(t):
    return sum(smooth((t - tb) / 0.2) for tb in BARS_T) / 3


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    glow = smooth((t - 10.4) / 1.2)
    g = cairo.LinearGradient(0, 0, 0, H)                                                 # classroom wall
    g.add_color_stop_rgb(0, *mix3((0.13, 0.27, 0.27), (0.17, 0.36, 0.34), glow))
    g.add_color_stop_rgb(1, *mix3((0.07, 0.15, 0.17), (0.10, 0.22, 0.24), glow))
    c.set_source(g); c.rectangle(0, 0, W, H); c.fill()

    x0, y0, x1, y1 = BOARD
    c.set_source_rgb(0.45, 0.30, 0.18); c.rectangle(x0 - 22, y0 - 22, x1 - x0 + 44, y1 - y0 + 44); c.fill()     # frame
    bg = cairo.LinearGradient(0, y0, 0, y1)
    bg.add_color_stop_rgb(0, 0.12, 0.25, 0.22); bg.add_color_stop_rgb(1, 0.09, 0.19, 0.17)
    c.set_source(bg); c.rectangle(x0, y0, x1 - x0, y1 - y0); c.fill()
    c.set_source_rgba(1, 1, 1, 0.06)
    for k in range(3):                                                                   # faint old smudges
        c.save(); c.translate(300 + 230 * k, 420 + 140 * (k % 2)); c.scale(1, 0.4); c.arc(0, 0, 150, 0, 2 * math.pi); c.restore(); c.fill()
    c.set_source_rgb(0.40, 0.27, 0.16); c.rectangle(x0 - 22, y1 + 22, x1 - x0 + 44, 14); c.fill()     # chalk ledge

    c.save()                                                                             # scribbles, clipped by the wipe
    c.rectangle(x0, y0, x1 - x0, y1 - y0); c.clip()
    for bi, (by0, by1) in enumerate(BANDS):
        a, b = WIPE[bi]
        if t >= b:
            continue
        c.save()
        if t >= a:
            ex = eraser_pos(t)[0]
            if bi % 2 == 0:
                c.rectangle(ex + 40, by0, 2000, by1 - by0)
            else:
                c.rectangle(0, by0, ex - 40, by1 - by0)
        else:
            c.rectangle(0, by0, W, by1 - by0)
        c.clip()
        for ts, dur, lines in SCRIB:
            cy = sum(p[1] for ln in lines for p in ln) / sum(len(ln) for ln in lines)
            if not (by0 <= cy < by1) or t < ts:
                continue
            for ln in lines:
                chalk_line(c, ln, (t - ts) / dur, RED, 9, 0.95)
        c.restore()
    c.restore()

    er = eraser_pos(t)                                                                   # the eraser + chalk dust
    if er:
        ex, ey, k = er
        c.save(); c.translate(ex, ey)
        c.set_source_rgb(0.25, 0.22, 0.20); c.rectangle(-40, -62, 80, 124); c.fill()
        c.set_source_rgb(0.80, 0.70, 0.45); c.rectangle(-40, -62, 80, 26); c.fill()
        c.restore()
        for q in range(26):
            d = (q * 0.037 + t * 3) % 1.0
            dx = (-1 if k % 2 == 0 else 1) * (30 + 150 * d)
            c.set_source_rgba(1, 1, 0.95, 0.35 * (1 - d))
            c.arc(ex + dx, ey + math.sin(q * 7.3) * 55 - 30 * d, 5 + 9 * d, 0, 2 * math.pi); c.fill()

    bx = (390, 640)                                                                      # chalk bar chart
    if t >= 11.5:
        chalk_line(c, [(260, BASE_Y), (800, BASE_Y)], smooth((t - 11.5) / 0.4), CHALK, 7, 0.9)
        grow = smooth((t - 11.7) / 0.4)
        h0 = 140 * grow
        c.set_source_rgba(*CHALK, 0.55); c.rectangle(bx[0] - 60, BASE_Y - h0, 120, h0); c.fill()
        hb = (140 + 66 * bar_steps(t)) * grow
        c.set_source_rgb(*mix3(MINT, GOLD, smooth((t - 13.0) / 0.5))); c.rectangle(bx[1] - 60, BASE_Y - hb, 120, hb); c.fill()
        for tb in BARS_T:
            d = t - tb
            if 0 <= d < 0.5:
                c.set_source_rgba(1, 1, 1, 0.7 * (1 - d / 0.5)); c.set_line_width(5)
                c.arc(bx[1], BASE_Y - hb, 40 + 120 * d, 0, 2 * math.pi); c.stroke()

    pose, air = fig_pose(t)                                                              # the figure, on the floor
    j = sr.joints_from(pose, 0.0, air)
    c.save(); c.translate(*FEET); c.scale(1.15, 1.15)
    sr.draw_shadow(c, 0, air)
    sr.draw_figure(c, j, (1.0, 0.93, 0.75), 13)
    hx, hy = j["head"]
    c.set_source_rgb(0.1, 0.2, 0.2)
    for ex in (14, 3):
        c.arc(hx + ex, hy - 5 + (3 if t < 8.6 else 0), 4.4, 0, 2 * math.pi); c.fill()
    c.restore()

    for tf, fx0, fy0, col, parts in FIRE:                                                # fireworks (screen space)
        d = t - tf
        if 0 <= d < 1.4:
            for ang, spd in parts:
                r = spd * (1 - math.exp(-d * 3.0))
                c.set_source_rgba(*col, (1 - d / 1.4) ** 1.4)
                c.arc(fx0 + r * math.cos(ang), fy0 + r * math.sin(ang) + 110 * d * d, 6 * (1 - d / 1.8), 0, 2 * math.pi); c.fill()
            if d < 0.2:
                c.set_source_rgba(1, 1, 1, 0.5 * (1 - d / 0.2)); c.arc(fx0, fy0, 70 * d / 0.2, 0, 2 * math.pi); c.fill()
    fl = t - T_DROP
    if 0 <= fl < 0.3:
        c.set_source_rgba(1, 1, 0.92, 0.4 * (1 - fl / 0.3) ** 2); c.paint()
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
        d.text((xy[0] + 2, xy[1] + 3), s, font=f, fill=(0, 0, 0, int(110 * a)), anchor="mm")
        d.text(xy, s, font=f, fill=(*fill, int(255 * a)), anchor="mm")


MINT_I = (140, 242, 198)


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 2.9)
    ctext(d, (540, 400), "Blew your week?", font("Bold", 64), CHALK_I, h)
    ctext(d, (540, 480), "Wipe the slate.", font("Bold", 64), MINT_I, h)
    if t >= T_NUM:
        pops = [math.exp(-(t - tb) / 0.16) for tb in BARS_T if t >= tb]
        pop = max(pops) if pops else 0.0
        ctext(d, (540, 590), f"+{int(round(47 * bar_steps(t)))}%", font("Bold", int(160 + 30 * pop)), (255, 209, 89), win(t, T_NUM, 20.1, 0.2, 0.1))
        ctext(d, (540, 700), "more gym visits at a fresh start", font("Regular", 30), CHALK_I, win(t, 12.3, 20.1, 0.4, 0.1))
        ctext(d, (390, 962), "normal day", font("Regular", 28), CHALK_I, win(t, 12.0, 20.1, 0.4, 0.1))
        ctext(d, (640, 962), "semester start", font("Regular", 28), CHALK_I, win(t, 12.0, 20.1, 0.4, 0.1))
    p = win(t, 14.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 370), "New week. New month.", font("Bold", 50), CHALK_I, p)
    ctext(d, (540, 435), "Start again there.", font("Bold", 50), MINT_I, p)
    q = win(t, 15.2, 20.1, 0.6, 0.1)
    ctext(d, (540, 1066), "Dai, Milkman & Riis, 2014 · university gym data", font("Regular", 27), (225, 232, 225), q)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "freshstart_silent.mp4"
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
