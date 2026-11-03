"""'Give your ideas legs' - walking and creative thinking. A scribble stuck in a tight loop breaks out into a flowing ribbon
and collects glowing ideas. 1080x1920, 20 s.

Oppezzo & Schwartz (2014, Journal of Experimental Psychology: Learning, Memory, and Cognition 40(4), 1142-1152), Stanford: four
experiments, 176 people (mostly college students).  Walking (on a treadmill or outdoors) vs sitting boosted divergent thinking
(alternate-uses idea generation); in one experiment walkers gave about twice as many creative responses (Stanford GSE and APA
summaries).  It did not help convergent (single-answer) thinking.  Small, mostly student lab study.
t < 10 s: the head circles in a tight cold scribble with six pale ideas; at the drop (t = 10 s) it breaks out onto a long
ribbon and six more ideas light up on the beats (10.5 ... 13.0 s) while the counter climbs 1.0x -> 2.0x.
Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python walking_reel.py out_silent.mp4      render
       python walking_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
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
CX, CY = 540, 1000                              # centre of the scribble / start of the ribbon
HEAD_SX = 640                                   # screen x of the head once the camera follows it
SPEED = 380.0
FLIGHT = 0.55
POPS = [10.5 + 0.5 * k for k in range(6)]       # the six new ideas light up on these beats (audio imports this)
A_TIMES = [4.0 + 0.6 * i for i in range(6)]     # the six pale ideas appear during the intro
SLOT_X = [270 + 108 * i for i in range(6)]
ROW_A, ROW_B = 1290, 1375
rng = np.random.default_rng(7)
DUST = [(rng.uniform(0, W), rng.uniform(0, 1500), rng.uniform(0.8, 2.6), rng.uniform(0, 6.28), rng.uniform(0.1, 0.5))
        for _ in range(80)]

ICEC = (0.62, 0.72, 0.84)
MINT = (0.62, 0.98, 0.70)
AMB = (1.0, 0.84, 0.40)


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def xh(t):                                       # world x of the head after the drop
    u = max(0.0, t - T_DROP)
    return CX + SPEED * (u + (math.exp(-4 * u) - 1) / 4)


def cam(t):
    return max(0.0, xh(t) - HEAD_SX)


def yr(x):                                       # ribbon height at world x (zero offset at x = CX)
    d = x - CX
    return CY + 120 * math.sin(d / 230.0) + 55 * math.sin(d / 95.0)


def scribble(s):                                 # the head's path inside the loop (and the blend into the ribbon start)
    p = s * (1 + 0.035 * s)
    x = CX + 165 * math.cos(5.3 * p) + 55 * math.cos(12.1 * p + 1)
    y = CY + 135 * math.sin(4.1 * p + 0.5) + 45 * math.sin(9.7 * p)
    k = smooth((s - 9.5) / 0.5)
    return lerp(x, CX, k), lerp(y, CY, k)


def head(t):                                     # world position of the head
    if t < T_DROP:
        return scribble(t)
    x = xh(t)
    return x, yr(x)


def warm(t):
    return 0.35 * smooth((t - 6.5) / 3.0) if t < T_DROP else 1.0


def seed_pos(k):
    x = xh(POPS[k])
    return x, yr(x)


def counter(t):
    done = sum(smooth((t - tp) / 0.3) for tp in POPS)
    return 1.0 + done / 6.0


def glow_orb(c, x, y, r, col, a, halo=3.2):
    gl = cairo.RadialGradient(x, y, r * 0.3, x, y, r * halo)
    gl.add_color_stop_rgba(0, *col, 0.55 * a); gl.add_color_stop_rgba(1, *col, 0)
    c.set_source(gl); c.arc(x, y, r * halo, 0, 2 * math.pi); c.fill()
    c.set_source_rgba(*mix3(col, (1, 1, 1), 0.55), a); c.arc(x, y, r, 0, 2 * math.pi); c.fill()
    c.set_source_rgba(*col, a); c.set_line_width(3); c.arc(x, y, r, 0, 2 * math.pi); c.stroke()


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    post = smooth((t - T_DROP) / 1.5) if t >= T_DROP else 0.0
    cm = cam(t)
    sky = cairo.LinearGradient(0, 0, 0, H)
    sky.add_color_stop_rgb(0, *mix3((0.02, 0.05, 0.09), (0.03, 0.10, 0.14), post))
    sky.add_color_stop_rgb(0.6, *mix3((0.04, 0.10, 0.14), (0.06, 0.24, 0.26), post))
    sky.add_color_stop_rgb(1, *mix3((0.06, 0.13, 0.17), (0.50, 0.42, 0.24), post))
    c.set_source(sky); c.paint()
    for sx, sy, sr, sp, par in DUST:
        x = (sx - cm * par) % W
        c.set_source_rgba(0.85, 0.98, 0.92, (0.22 + 0.2 * math.sin(t * 1.3 + sp)) * (0.7 + 0.5 * post))
        c.arc(x, sy, sr, 0, 2 * math.pi); c.fill()
    gl = cairo.RadialGradient(540, 1150, 30, 540, 1150, 800)
    gl.add_color_stop_rgba(0, 1.0, 0.80, 0.40, 0.42 * post); gl.add_color_stop_rgba(1, 1.0, 0.7, 0.3, 0)
    c.set_source(gl); c.paint()
    c.set_line_join(cairo.LINE_JOIN_ROUND); c.set_line_cap(cairo.LINE_CAP_ROUND)
    wm = warm(t)
    # the tangled scribble: the last 3.5 s of the head's path, fading with age
    te = min(t, T_DROP)
    col = mix3(ICEC, (0.95, 0.88, 0.62), wm)
    n = 150
    pts = [scribble_pt for scribble_pt in (scribble(te - 3.5 * (1 - i / n)) for i in range(n + 1))]
    for i in range(n):
        s = te - 3.5 * (1 - (i + 0.5) / n)
        a = clamp(1 - (t - s) / 3.5) ** 1.3
        if a <= 0.01 or s < 0:
            continue
        c.set_source_rgba(*col, 0.85 * a); c.set_line_width(5)
        c.move_to(pts[i][0] - cm, pts[i][1]); c.line_to(pts[i + 1][0] - cm, pts[i + 1][1]); c.stroke()
    # the ribbon the head draws after the drop
    hx, hy = head(t)
    if t >= T_DROP:
        rc = mix3(MINT, AMB, 0.0)
        x0 = CX
        xs = list(range(int(x0), int(hx) + 1, 6)) + [hx]
        for lw, al in ((26, 0.10), (13, 0.20), (6, 1.0)):
            gr = cairo.LinearGradient(max(0, x0 - cm), 0, hx - cm, 0)
            gr.add_color_stop_rgba(0, *rc, 0); gr.add_color_stop_rgba(0.12, *rc, 0.6 * al); gr.add_color_stop_rgba(1, *rc, al)
            c.set_source(gr); c.set_line_width(lw)
            c.move_to(xs[0] - cm, yr(xs[0]))
            for x in xs[1:]:
                c.line_to(x - cm, yr(x))
            c.stroke()
        for j in range(1, 26):                                   # sparks trailing from the head
            ts = t - 0.045 * j
            if ts < T_DROP:
                break
            px = xh(ts)
            py = yr(px) + 22 * math.sin(j * 1.7 + t * 9) * (j / 25)
            c.set_source_rgba(*MINT, 0.7 * (1 - j / 26)); c.arc(px - cm, py, 3.5 * (1 - j / 30) + 1, 0, 2 * math.pi); c.fill()
    hsx, hsy = hx - cm, hy
    hg = cairo.RadialGradient(hsx, hsy, 2, hsx, hsy, 62)
    hc = mix3(ICEC, MINT, post)
    hg.add_color_stop_rgba(0, 1, 1, 1, 0.95); hg.add_color_stop_rgba(0.25, *hc, 0.7); hg.add_color_stop_rgba(1, *hc, 0)
    c.set_source(hg); c.arc(hsx, hsy, 62, 0, 2 * math.pi); c.fill()
    # seeds waiting on the ribbon, ahead of the head
    for k in range(6):
        sxw, syw = seed_pos(k)
        if 9.7 <= t < POPS[k]:
            a = smooth((t - 9.7) / 0.5)
            sx = sxw - cm
            if sx < 1150:
                c.set_source_rgba(*MINT, 0.55 * a); c.set_line_width(3)
                c.arc(sx, syw, 18 + 2 * math.sin(t * 5 + k), 0, 2 * math.pi); c.stroke()
                c.set_source_rgba(*MINT, 0.2 * a); c.arc(sx, syw, 8, 0, 2 * math.pi); c.fill()
    # idea slots: row A (pale, appear while stuck), row B (amber, fly in from the head on the beats)
    for i, ta in enumerate(A_TIMES):
        if t >= ta:
            k = clamp((t - ta) / 0.35)
            sc = 1 + 0.35 * math.sin(k * math.pi) if k < 1 else 1
            glow_orb(c, SLOT_X[i], ROW_A, 19 * sc * smooth(k), mix3(ICEC, (0.95, 0.9, 0.7), 0.5 * post), 0.8 + 0.2 * post, halo=2.4)
    for k, tp in enumerate(POPS):
        f = t - tp
        if f < 0:
            continue
        sxw, syw = seed_pos(k)
        sx0, sy0 = sxw - cam(tp), syw
        if f < 0.6:                                              # pop ring where the head touched the seed
            r = 20 + 130 * f / 0.6
            c.set_source_rgba(*AMB, 0.8 * (1 - f / 0.6)); c.set_line_width(6 * (1 - f / 0.6) + 1); c.arc(sx0, sy0, r, 0, 2 * math.pi); c.stroke()
        if f < FLIGHT:
            u = smooth(f / FLIGHT)
            bx, by = SLOT_X[k], ROW_B
            x = lerp(sx0, bx, u); y = lerp(sy0, by, u) - 120 * math.sin(u * math.pi)
            glow_orb(c, x, y, 24, AMB, 1.0)
        else:
            pul = 1 + 0.08 * math.sin((t - tp) * 5)
            kk = clamp((f - FLIGHT) / 0.3)
            glow_orb(c, SLOT_X[k], ROW_B, 21 * pul * (1 + 0.3 * (1 - kk)), AMB, 1.0)
    f2 = t - T_DROP
    if 0 <= f2 < 0.3:
        c.set_source_rgba(0.9, 1.0, 0.9, 0.34 * (1 - f2 / 0.3) ** 2); c.paint()
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
ICE = (175, 205, 235)


def number_str(t):
    v = counter(t)
    return "2×" if v >= 1.995 else f"{v:.1f}×"


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 3.5)
    ctext(d, (540, 380), "Stuck on an idea?", font("Bold", 66), WHITE, h)
    ctext(d, (540, 466), "Brain going in circles?", font("Bold", 48), ICE, h)
    b = win(t, 3.8, 6.7, 0.4, 0.3)
    ctext(d, (540, 380), "Sitting still,", font("Bold", 46), ICE, b)
    ctext(d, (540, 456), "stuck on repeat.", font("Bold", 62), WHITE, b)
    e = win(t, 6.9, 9.8, 0.4, 0.3)
    ctext(d, (540, 380), "Stand up.", font("Bold", 68), MINTC, e)
    ctext(d, (540, 456), "Start walking.", font("Bold", 62), WHITE, e)
    z = win(t, 10.2, 14.4, 0.3, 0.3)
    ctext(d, (540, 345), "Walk it out.", font("Bold", 68), GOLD, z)
    ctext(d, (540, 415), "Ideas start to flow.", font("Bold", 42), WHITE, z)
    if t >= T_NUM:
        pop = 1 + 0.12 * math.sin(clamp((t - 13.0) / 0.4) * math.pi) if t < 13.4 else 1
        ctext(d, (540, 585), number_str(t), font("Bold", int(170 * pop)), GOLD, win(t, T_NUM, 20.1, 0.2, 0.1))
        ctext(d, (540, 690), "as many creative ideas", font("Regular", 34), WHITE, win(t, 11.0, 20.1, 0.4, 0.1))
        ctext(d, (540, 740), "walking vs sitting", font("Regular", 28), ICE, win(t, 11.4, 20.1, 0.4, 0.1))
    p = win(t, 14.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 300), "Stuck? Stand up.", font("Bold", 54), WHITE, p)
    ctext(d, (540, 365), "Take a walk.", font("Bold", 58), MINTC, p)
    q = win(t, 15.2, 20.1, 0.6, 0.1)
    ctext(d, (540, 1450), "Oppezzo & Schwartz, 2014 · Stanford", font("Regular", 27), WHITE, q)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "walking_silent.mp4"
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
