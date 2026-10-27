"""'You've already started' - the endowed progress effect. One staircase, one figure. 1080x1920, 20 s.

Nunes & Dreze (2006): car-wash customers got a loyalty card. Same eight washes needed either way, but one card was blank
(8 spaces) and the other came with 2 free stamps already on it (10 spaces). 34% of the head-start cards were completed,
19% of the blank ones.  Here: the figure stares up an impossible staircase, then sees that the first two steps are already
lit, steps onto them and bounds to the top on the beat of the drop (hops land on 10.5, 11.0 ... 13.5 s).
Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python endowed_reel.py out_silent.mp4      render
       python endowed_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
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
NAVY = (34, 30, 82)
ORANGE = (226, 104, 18)
INK = (0.13, 0.12, 0.32)
GOLD = (1.0, 0.78, 0.28)
LAV = (0.80, 0.76, 0.93)
FONTS = Path(__file__).resolve().parent.parent / "fonts"
SAFE = (140, 260, 940, 1480)

SW, SH, NST = 96.0, 118.0, 10
GROUND_X = -110.0
T_DROP = 10.0
LAND = {1: 7.2, 2: 7.9, 3: 8.6}
LAND.update({s: 10.5 + 0.5 * (s - 4) for s in range(4, 11)})          # one step per beat of the drop
LIT = {1: 5.4, 2: 6.0, 3: LAND[3], **{s: LAND[s] for s in range(4, 11)}}
T_TOP = LAND[10]                                                       # 13.5
T_FIRE = [14.0, 14.45, 14.9, 15.5, 16.2, 17.0]
HOP_T0 = 14.5


def stand(k):
    return (GROUND_X, 0.0) if k == 0 else ((k - 0.5) * SW, -k * SH)


HOPS = [(0, 1, LAND[1] - 0.45, LAND[1]), (1, 2, LAND[2] - 0.45, LAND[2]), (2, 3, LAND[3] - 0.45, LAND[3])]
HOPS += [(s - 1, s, LAND[s] - 0.5, LAND[s]) for s in range(4, 11)]


def fig_pos(t):
    """World position of the feet, whether airborne and the hop progress u."""
    cur = stand(0)
    for a, b, t0, t1 in HOPS:
        if t < t0:
            break
        if t >= t1:
            cur = stand(b)
            continue
        u = (t - t0) / (t1 - t0)
        pa, pb = stand(a), stand(b)
        return (lerp(pa[0], pb[0], u), lerp(pa[1], pb[1], u) - 4 * 70 * u * (1 - u)), True, u
    return cur, False, 0.0


SLUMP = sr.P(0.2, (0.12, 0.1), (-0.1, 0.1), (0.1, 0.25), (0.0, 0.25))


def fig_pose(t, hopping, u):
    if t < 5.2:
        base = sr.lerp_pose(sr.idle_pose(t), SLUMP, smooth((t - 3.0) / 1.0))     # looking up at the climb, shoulders sinking
    else:
        base = sr.lerp_pose(SLUMP, sr.idle_pose(t), smooth((t - 5.2) / 0.6))
    if t > 8.6:
        base = sr.lerp_pose(base, sr.blend([(0.5, sr.STANCE), (0.5, sr.idle_pose(t))]), smooth((t - 8.6) / 0.5))
    if t > 10.0:
        base = sr.lerp_pose(base, sr.CHEER, smooth((t - 10.0) / 0.3))
    if hopping:
        return sr.lerp_pose(base, sr.HOP, math.sin(math.pi * u))
    return base


# ---------------------------------------------------------------- camera (critically damped spring on x, y, zoom)
WIDE = (480.0, -597.0, 0.62)
FINAL = (480.0, -846.0, 0.52)


def cam_target(t):
    (fx, fy), _, _ = fig_pos(t)
    if t < 3.5:
        return (300.0, -330.0, 0.78)
    if t < 5.2:
        k = smooth((t - 3.5) / 1.7)
        return tuple(lerp(a, b, k) for a, b in zip((300.0, -330.0, 0.78), WIDE))
    if t < 10.0:
        return WIDE
    if t < 13.6:
        return (fx + 130, fy - 230, 0.82)
    return FINAL


DT = 1 / 240
TS = np.arange(int((DUR + 0.5) / DT)) * DT
CAM = np.zeros((len(TS), 3))
_s = np.array(cam_target(0.0))
_v = np.zeros(3)
for _i, _t in enumerate(TS):
    _tg = np.array(cam_target(_t))
    _v += (3.2 ** 2 * (_tg - _s) - 2 * 3.2 * _v) * DT
    _s = _s + _v * DT
    CAM[_i] = _s


def camera(t):
    return tuple(float(np.interp(t, TS, CAM[:, i])) for i in range(3))


# ---------------------------------------------------------------- scene
rng = np.random.default_rng(7)
CLOUDS = [(rng.uniform(-300, 1500), rng.uniform(-1700, -80), rng.uniform(120, 260), rng.uniform(0.15, 0.4)) for _ in range(16)]
FIRE = []
for k, tf in enumerate(T_FIRE):
    cx0 = (760, 340, 600, 860, 250, 520)[k]
    cy0 = (660, 720, 640, 760, 640, 760)[k]
    col = ((1, 0.8, 0.3), (1, 0.45, 0.65), (1, 1, 1), (0.5, 0.9, 1), (1, 0.8, 0.3), (1, 0.45, 0.65))[k]
    parts = [(rng.uniform(0, 6.283), rng.uniform(120, 330)) for _ in range(34)]
    FIRE.append((tf, cx0, cy0, col, parts))


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def star(c, x, y, r):
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        (c.move_to if i == 0 else c.line_to)(x + rr * math.cos(a), y + rr * math.sin(a))
    c.close_path()


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    cx, cy, z = camera(t)
    glow = smooth((t - T_TOP) / 0.6)

    g = cairo.LinearGradient(0, 0, 0, H)                                                 # pastel sky
    g.add_color_stop_rgb(0, *mix3((0.50, 0.58, 0.93), (0.60, 0.66, 0.97), glow))
    g.add_color_stop_rgb(0.7, *mix3((0.98, 0.80, 0.80), (1.0, 0.86, 0.72), glow))
    g.add_color_stop_rgb(1, 0.99, 0.88, 0.78)
    c.set_source(g); c.rectangle(0, 0, W, H); c.fill()

    c.save()
    c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-cx, -cy)
    for x, y, r, al in CLOUDS:                                                           # clouds drift
        xx = x + 8 * t
        c.set_source_rgba(1, 1, 1, al)
        for dx, dy, rr in ((0, 0, r), (r * 0.7, r * 0.12, r * 0.75), (-r * 0.7, r * 0.15, r * 0.65)):
            c.save(); c.translate(xx + dx, y + dy); c.scale(1, 0.5); c.arc(0, 0, rr, 0, 2 * math.pi); c.restore(); c.fill()

    c.set_source_rgb(0.42, 0.40, 0.70)                                                   # hill / ground
    c.rectangle(-3000, 0, 7000, 4000); c.fill()
    c.set_source_rgba(1, 1, 1, 0.10); c.set_line_width(6)
    c.move_to(-3000, 3); c.line_to(4000, 3); c.stroke()

    for k in range(1, NST + 1):                                                          # steps
        lit = smooth((t - LIT[k]) / 0.3)
        x0, top = (k - 1) * SW, -k * SH
        face = mix3(LAV, GOLD, lit)
        c.set_source_rgb(*mix3(face, (0, 0, 0), 0.18))
        c.rectangle(x0, top, SW, -top); c.fill()                                         # block (front face, darker)
        c.set_source_rgb(*face)
        c.rectangle(x0, top, SW, 22); c.fill()                                           # lit tread
        if lit > 0:
            rg = cairo.RadialGradient(x0 + SW / 2, top, 5, x0 + SW / 2, top, 150)
            rg.add_color_stop_rgba(0, 1, 0.9, 0.5, 0.6 * lit * (1 - 0.4 * smooth((t - LIT[k] - 0.8) / 1.0)))
            rg.add_color_stop_rgba(1, 1, 0.9, 0.5, 0)
            c.set_source(rg); c.arc(x0 + SW / 2, top, 150, 0, 2 * math.pi); c.fill()
        d = t - LIT[k]
        if 0 <= d < 0.55:                                                                # landing ring
            c.set_source_rgba(1, 1, 1, 0.8 * (1 - d / 0.55)); c.set_line_width(5)
            c.save(); c.translate(x0 + SW / 2, top); c.scale(1, 0.3)
            c.arc(0, 0, 20 + 120 * d / 0.55, 0, 2 * math.pi); c.restore(); c.stroke()

    sx, sy = (NST - 0.5) * SW + 6, -NST * SH - 330                                        # the goal star
    bob = 6 * math.sin(t * 2.2)
    if glow > 0:
        rg = cairo.RadialGradient(sx, sy + bob, 10, sx, sy + bob, 190)
        rg.add_color_stop_rgba(0, 1, 0.9, 0.5, 0.8 * glow); rg.add_color_stop_rgba(1, 1, 0.9, 0.5, 0)
        c.set_source(rg); c.arc(sx, sy + bob, 190, 0, 2 * math.pi); c.fill()
    c.set_source_rgb(*mix3((0.66, 0.63, 0.82), GOLD, glow))
    star(c, sx, sy + bob, 62 + 16 * glow); c.fill()

    (fx, fy), hopping, u = fig_pos(t)                                                     # the figure
    pose = fig_pose(t, hopping, u)
    j = sr.joints_from(pose, 0.0, 0.0)
    c.save()
    c.translate(fx, fy)
    sh_a = 0.0 if hopping else 0.3
    c.save(); c.translate(0, 4); c.scale(1, 0.14); c.arc(0, 0, 60, 0, 2 * math.pi); c.restore()
    c.set_source_rgba(0, 0, 0, sh_a); c.fill()
    sr.draw_figure(c, j, INK, 13)
    hx, hy = j["head"]
    c.set_source_rgb(1, 1, 1)
    for ex in (14, 3):
        c.arc(hx + ex, hy - 5 - (6 if t < 5.2 else 0), 4.4, 0, 2 * math.pi); c.fill()
    c.restore()
    c.restore()

    for tf, fx0, fy0, col, parts in FIRE:                                                # fireworks (screen space)
        d = t - tf
        if 0 <= d < 1.4:
            for ang, spd in parts:
                r = spd * (1 - math.exp(-d * 3.0))
                px, py = fx0 + r * math.cos(ang), fy0 + r * math.sin(ang) + 110 * d * d
                al = (1 - d / 1.4) ** 1.4
                c.set_source_rgba(*col, al); c.arc(px, py, 6 * (1 - d / 1.8), 0, 2 * math.pi); c.fill()
            if d < 0.2:
                c.set_source_rgba(1, 1, 1, 0.5 * (1 - d / 0.2)); c.arc(fx0, fy0, 70 * d / 0.2, 0, 2 * math.pi); c.fill()
    fl = t - T_DROP
    if 0 <= fl < 0.35:
        c.set_source_rgba(1, 0.97, 0.88, 0.55 * (1 - fl / 0.35) ** 2); c.paint()
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
        d.text((xy[0] + 2, xy[1] + 3), s, font=f, fill=(255, 255, 255, int(120 * a)), anchor="mm")
        d.text(xy, s, font=f, fill=(*fill, int(255 * a)), anchor="mm")


def done(t):
    return sum(1 for k in range(1, NST + 1) if t >= LIT[k])


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 2.9)
    ctext(d, (540, 420), "Feel like you're", font("Bold", 64), NAVY, h)
    ctext(d, (540, 505), "starting from zero?", font("Bold", 64), NAVY, h)
    c_a = clamp((t - 3.2) / 0.4) * (1 - smooth((t - 13.9) / 0.4))
    if c_a > 0:
        n = done(t)
        last = max([LIT[k] for k in range(1, NST + 1) if t >= LIT[k]] or [0])
        pop = math.exp(-(t - last) / 0.16) if n else 0.0
        col = tuple(int(lerp(a, b, smooth(n / 2))) for a, b in zip(NAVY, ORANGE))
        ctext(d, (540, 340), "S T E P S   D O N E", font("Bold", 36), NAVY, c_a * 0.8)
        ctext(d, (540, 480), f"{n} / {NST}", font("Bold", int(210 + 36 * pop)), col, c_a)
    p = win(t, 14.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 360), "You've already started.", font("Bold", 54), NAVY, p)
    ctext(d, (540, 435), "Count what you've done.", font("Bold", 54), NAVY, p)
    ctext(d, (540, 525), "Nunes & Drèze, 2006: a card with 2 free", font("Regular", 28), (48, 44, 100), win(t, 15.2, 20.1, 0.6, 0.1))
    ctext(d, (540, 565), "stamps got finished 34% vs 19% of the time", font("Regular", 28), (48, 44, 100), win(t, 15.2, 20.1, 0.6, 0.1))
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
    out = sys.argv[1] if len(sys.argv) > 1 else "endowed_silent.mp4"
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
