"""'Day 1 -> Day 66' - one figure, one night road, one sunrise. 1080x1920, 20 s.

The walk starts heavy (leaning into the wind, sweating, slow) and becomes effortless as the day counter climbs, following an
asymptotic automaticity curve like the one in Lally et al. (2010, UCL). Text is minimal and kept inside phone safe zones
(x 140-940, y 260-1480). No handle or UI-prone text at the edges.

Usage: python habit_reel.py out_silent.mp4      render
       python habit_reel.py stills 1 5 10.2 ...  still PNGs (no blur) with a safe-zone outline
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
AMBER = (1.0, 0.69, 0.13)
CREAM = (245, 240, 230)
GOLD = (222, 178, 110)
GY = 0.62 * H                                  # ground line on screen
FONTS = Path(__file__).resolve().parent.parent / "fonts"
SAFE = (140, 260, 940, 1480)                   # text must stay inside this box

T_DAY0, T_DAY66 = 3.0, 10.0
STEP = 115.0

DT = 1 / 480
N = int((DUR + 0.5) / DT)
TS = np.arange(N) * DT


def day(t):
    if t < T_DAY0:
        return 0.0
    return 1 + 65 * clamp((t - T_DAY0) / (T_DAY66 - T_DAY0)) ** 1.7


def auto(t):
    """Automaticity 0..1: asymptotic in the day count, then eases to full."""
    if t < T_DAY0:
        return 0.0
    a = 1 - math.exp(-(day(t) - 1) / 22)
    return a + (1 - a) * smooth((t - T_DAY66) / 5.0)


A_TAB = np.array([auto(t) for t in TS])
V_TAB = 100 + 400 * A_TAB
X_TAB = np.cumsum(V_TAB) * DT
RUN_TAB = np.array([smooth((a - 0.55) / 0.35) for a in A_TAB])
PH_TAB = np.cumsum(V_TAB / (230 - 60 * RUN_TAB)) * DT          # gait phase in cycles; stride shortens as it speeds up
STEP_X = np.arange(1, int(X_TAB[-1] / STEP))
STEP_T = np.interp(STEP_X * STEP, X_TAB, TS)


def fx(t): return float(np.interp(t, TS, X_TAB))
def fv(t): return float(np.interp(t, TS, V_TAB))
def fa(t): return float(np.interp(t, TS, A_TAB))
def fph(t): return float(np.interp(t, TS, PH_TAB))
def frun(t): return float(np.interp(t, TS, RUN_TAB))


def gait(ph, amp, knee, arm, lean):
    def leg(p):
        return amp * math.sin(2 * math.pi * p), 0.1 + knee * max(0.0, math.cos(2 * math.pi * p))

    def arms(p):
        return -arm * math.sin(2 * math.pi * p), 0.5 + 0.4 * smooth((arm - 0.5) / 0.3)

    return sr.P(lean, leg(ph), leg(ph + 0.5), arms(ph), arms(ph + 0.5))


def fig_pose(t):
    a = fa(t)
    return gait(fph(t), lerp(0.4, 0.9, a), lerp(0.6, 1.3, a), lerp(0.25, 0.9, a), lerp(0.42, 0.28, a))


def fig_joints(t):
    return sr.joints_from(fig_pose(t), fx(t), 0.0)


# ---------------------------------------------------------------- camera
CAM = np.zeros(N)
_x, _v = fx(0) + 90, 0.0
for _i in range(N):
    _tgt = X_TAB[_i] + 90
    _v += (2.6 ** 2 * (_tgt - _x) - 2 * 2.6 * _v) * DT
    _x += _v * DT
    CAM[_i] = _x
ZKEYS = [(-1, 1.5), (0, 1.5), (3, 1.5), (6.5, 1.25), (10, 1.0), (14, 0.9), (20, 0.82), (30, 0.82)]


def camera(t):
    return float(np.interp(t, TS, CAM)), sr.catmull(ZKEYS, t)[0]


# ---------------------------------------------------------------- scene
rng = np.random.default_rng(3)
STARS = [(rng.uniform(0, W), rng.uniform(40, GY * 0.82), rng.uniform(0.9, 2.3), rng.uniform(0.3, 0.9), rng.uniform(0, 6.28))
         for _ in range(95)]
WIND = [(rng.uniform(0, W + 500), rng.uniform(GY - 440, GY - 40), rng.uniform(110, 300), rng.uniform(900, 1500))
        for _ in range(22)]
MOUNT = [  # parallax, base, amps, wavelengths, phases, night colour, day colour
    (0.05, 330, (90, 50, 25), (520, 210, 95), (0.3, 1.7, 4.0), (0.05, 0.05, 0.11), (0.45, 0.27, 0.35)),
    (0.12, 230, (110, 60, 30), (380, 170, 80), (2.1, 0.4, 5.1), (0.035, 0.035, 0.08), (0.28, 0.14, 0.24)),
    (0.25, 130, (70, 40, 18), (300, 130, 60), (4.4, 2.2, 1.0), (0.025, 0.025, 0.05), (0.14, 0.07, 0.14)),
]


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def sun_rise(t): return smooth((t - 7.0) / 3.0)
def dawn(t): return smooth((t - 6.0) / 4.5) * 0.85 + 0.15 * smooth((t - 10.5) / 4.0)


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    S = dawn(t)
    a = fa(t)
    cx, z = camera(t)
    cy = -(0.12 * H) / z

    g = cairo.LinearGradient(0, 0, 0, GY)                        # sky
    top, hor = mix3((0.015, 0.02, 0.05), (0.12, 0.14, 0.32), S), mix3((0.05, 0.06, 0.14), (0.98, 0.60, 0.25), S)
    g.add_color_stop_rgb(0, *top); g.add_color_stop_rgb(1, *hor)
    c.set_source(g); c.rectangle(0, 0, W, H); c.fill()
    for x, y, r, al, ph in STARS:
        c.set_source_rgba(1, 1, 1, al * (1 - S) * (0.7 + 0.3 * math.sin(t * 2 + ph)))
        c.arc(x, y, r, 0, 2 * math.pi); c.fill()

    rise = sun_rise(t)                                             # sun
    sy = GY + 330 - 640 * rise
    if rise > 0:
        rg = cairo.RadialGradient(W / 2, sy, 20, W / 2, sy, 760)
        rg.add_color_stop_rgba(0, 1, 0.78, 0.4, 0.75 * rise); rg.add_color_stop_rgba(1, 1, 0.5, 0.2, 0)
        c.set_source(rg); c.arc(W / 2, sy, 760, 0, 2 * math.pi); c.fill()
        c.set_source_rgba(1, 0.9, 0.62, rise); c.arc(W / 2, sy, 125, 0, 2 * math.pi); c.fill()

    zl = z ** 0.5                                                  # mountains
    for f, base, amps, lams, phs, cn, cd in MOUNT:
        c.move_to(0, GY)
        for sx in range(0, W + 10, 9):
            xl = (sx - W / 2) / zl + cx * f
            h = base + sum(am * math.sin(xl / lm + ph) for am, lm, ph in zip(amps, lams, phs))
            c.line_to(sx, GY - h * zl)
        c.line_to(W, GY); c.close_path()
        c.set_source_rgb(*mix3(cn, cd, S)); c.fill()

    c.set_source_rgb(*mix3((0.02, 0.02, 0.03), (0.10, 0.06, 0.05), S))   # ground
    c.rectangle(0, GY, W, H - GY); c.fill()
    for wd, al in ((30, 0.05), (14, 0.12), (5, 0.35 + 0.5)):             # the path wears in as it becomes automatic
        c.set_source_rgba(*AMBER, al * a); c.set_line_width(wd * z * (0.6 + 0.6 * a))
        c.move_to(0, GY); c.line_to(W, GY); c.stroke()

    for f, ws, wl, wsp in WIND:                                    # headwind (fades as it gets automatic)
        al = 0.34 * (1 - a) ** 1.3
        if al < 0.01:
            continue
        x = (ws - wsp * t) % (W + 500) - 250
        c.set_source_rgba(1, 1, 1, al); c.set_line_width(3)
        c.move_to(x, f); c.line_to(x + wl, f); c.stroke()

    c.save()
    c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-cx, -cy)
    lo, hi = np.searchsorted(STEP_X * STEP, [cx - 700 / z, cx + 700 / z])
    for k in range(lo, hi):                                        # footprints + dust
        tk = STEP_T[k]
        if tk > t:
            break
        ak = fa(tk)
        c.save(); c.translate(STEP_X[k] * STEP, 5); c.scale(1, 0.2)
        c.arc(0, 0, 20, 0, 2 * math.pi); c.restore()
        c.set_source_rgba(*AMBER, 0.15 + 0.7 * ak); c.fill()
        d = t - tk
        if d < 0.7 and ak < 0.8:
            for q in range(3):
                c.set_source_rgba(0.8, 0.78, 0.74, 0.35 * (1 - ak) * (1 - d / 0.7))
                c.arc(STEP_X[k] * STEP - 18 - 30 * d * (q + 1), -8 - 55 * d - 9 * q, 6 + 12 * d, 0, 2 * math.pi); c.fill()

    j = fig_joints(t)
    sr.draw_shadow(c, j["hip"][0], 0.0)
    sr.draw_figure(c, j, AMBER, 12)
    eff = 1 - a
    if eff > 0.3:                                                  # sweat
        hx, hy = j["head"]
        for q in range(3):
            ph = ((t * 1.6) + q / 3) % 1
            c.set_source_rgba(0.6, 0.85, 1.0, (1 - ph) * min(1, (eff - 0.3) * 2.5))
            c.arc(hx - 26 - 34 * ph, hy - 20 + 120 * ph * ph - 20 * ph, 7 * (1 - 0.4 * ph), 0, 2 * math.pi); c.fill()
    c.restore()

    fl = t - 10.0                                                  # the drop
    if 0 <= fl < 0.35:
        c.set_source_rgba(1, 0.93, 0.75, 0.55 * (1 - fl / 0.35) ** 2); c.paint()
        c.set_source_rgba(1, 0.85, 0.5, 0.7 * (1 - fl / 0.35)); c.set_line_width(6)
        c.arc(W / 2, GY - 250, 60 + 900 * (1 - (1 - fl / 0.35) ** 3), 0, 2 * math.pi); c.stroke()

    buf = np.frombuffer(surf.get_data(), np.uint8).reshape(H, W, 4)
    return buf[:, :, 2::-1].astype(np.float32)


# ---------------------------------------------------------------- text (PIL, after motion blur)
_FC = {}


def font(name, size):
    key = (name, size)
    if key not in _FC:
        _FC[key] = ImageFont.truetype(str(FONTS / f"IBMPlexSerif-{name}.ttf"), size)
    return _FC[key]


def win(t, t0, t1, fi=0.35, fo=0.35):
    return clamp((t - t0) / fi) * clamp((t1 - t) / fo)


def ctext(d, xy, s, f, fill, a):
    if a > 0.01:
        d.text((xy[0] + 2, xy[1] + 3), s, font=f, fill=(0, 0, 0, int(150 * a)), anchor="mm")   # soft shadow for legibility
        d.text(xy, s, font=f, fill=(*fill, int(255 * a)), anchor="mm")


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 2.7)                                           # hook
    ctext(d, (540, 420), "How long does it take", font("Bold", 64), CREAM, h)
    ctext(d, (540, 505), "to build a habit?", font("Bold", 64), CREAM, h)
    if t >= T_DAY0:                                                # the counter
        n = int(min(66, day(t) + 1e-6))
        a = clamp((t - T_DAY0) / 0.4)
        pop = math.exp(-(t - 10.0) / 0.18) if t >= 10.0 else 0.0
        col = tuple(int(lerp(c1, c2, smooth((t - 9.6) / 0.6))) for c1, c2 in zip(CREAM, GOLD))
        ctext(d, (540, 340), "D A Y", font("Bold", 40), GOLD, a)
        ctext(d, (540, 480), str(n), font("Bold", int(250 + 50 * pop)), col, a)
    p = win(t, 12.2, 20.1, 0.6, 0.1)                               # payoff
    ctext(d, (540, 690), "One study: habits start to", font("Bold", 50), CREAM, p)
    ctext(d, (540, 760), "feel automatic around day 66.", font("Bold", 50), CREAM, p)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "habit_silent.mp4"
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
