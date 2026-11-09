"""'Write it down' - a bedtime to-do list. A sleeper lies awake while tangled thought-scribbles circle the head faster and
faster; at the drop (t = 10 s) a notepad catches them, two by two, as six list lines written on the beats (10.5 ... 13.0 s),
then the room cools to moonlit blue and the sleeper drifts off.  1080x1920, 20 s.

Scullin, Krueger, Ballard, Pruett & Bliwise (2018, Journal of Experimental Psychology: General; PMC5758411): 57 healthy
young adults (18-30) wrote for 5 minutes at bedtime before overnight polysomnography in a sleep lab.  Writing a to-do list for
the next few days (n = 28) vs a list of tasks already completed (n = 29): sleep onset 15.82 vs 25.09 min (t(55) = 2.32,
p = .02, d = 0.63), and more specific to-do lists went with faster sleep.  One night, no no-writing control, people without
sleep problems (caveats go in the caption).  Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python todolist_reel.py out_silent.mp4      render
       python todolist_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
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
T_PAD = 8.6                                   # notepad slides up 8.6 -> 9.8
T_STOW = 14.5                                 # notepad moves to the nightstand 14.5 -> 15.7
CX, CY = 540.0, 900.0                         # swarm centre
HEAD = (330.0, 1262.0)
PAD_C, PAD_W, PAD_H = (540.0, 880.0), 400.0, 500.0
NTH = 12
rng = np.random.default_rng(23)
THOUGHTS = []                                 # appear time, orbit angle, rx, ry, size, shape phase, jitter phase
for i in range(NTH):
    THOUGHTS.append((0.4 + 0.68 * i, rng.uniform(0, 6.28), rng.uniform(150, 300), rng.uniform(150, 260),
                     rng.uniform(30, 46), rng.uniform(0, 6.28), rng.uniform(0, 6.28)))
LINE_T = [T_DROP + 0.5 * (j + 1) for j in range(6)]          # a line is written on each beat 10.5 ... 13.0
LINE_L = [rng.uniform(170, 250) for _ in range(6)]
STARS = [(rng.uniform(0, W), rng.uniform(0, 1150), rng.uniform(0.8, 2.3), rng.uniform(0, 6.28)) for _ in range(60)]
Z_T = [13.6 + 1.3 * k for k in range(5)]


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def spin(t):
    return 0.55 * t + 0.045 * t * t                          # the loop speeds up as the night drags on


def swarm_pos(i, t):
    ta, a0, rx, ry, sz, ph, jp = THOUGHTS[i]
    p = a0 + spin(t) * (1 if i % 2 else -1) * (0.8 + 0.04 * i)
    jit = 4 + 1.2 * min(t, 10)
    x = CX + rx * math.cos(p) + jit * math.sin(t * 17 + jp)
    y = CY + ry * 0.75 * math.sin(p) + jit * math.cos(t * 13 + jp)
    return x, y


def pad_frame(t):
    """notepad centre, scale and alpha"""
    if t < T_PAD:
        return None
    k = smooth((t - T_PAD) / 1.2)
    x, y = PAD_C[0], lerp(1750, PAD_C[1], k)
    s = 1.0
    if t > T_STOW:
        q = smooth((t - T_STOW) / 1.2)
        x, y, s = lerp(x, 150, q), lerp(y, 1262, q), lerp(1.0, 0.32, q)
    return x, y, s


def line_xy(j):
    x0 = PAD_C[0] - PAD_W / 2
    y0 = PAD_C[1] - PAD_H / 2
    return x0 + 95, y0 + 120 + 62 * j


def scribble(c, x, y, sz, ph, col, a, lw=4.0):
    c.save(); c.translate(x, y)
    c.new_path()
    for k in range(90):
        u = k / 89 * 2 * math.pi
        px = sz * (0.7 * math.sin(3 * u + ph) + 0.35 * math.sin(5 * u))
        py = sz * (0.6 * math.cos(2 * u) + 0.35 * math.sin(7 * u + ph))
        (c.move_to if k == 0 else c.line_to)(px, py)
    c.set_line_width(lw * 3.2); c.set_source_rgba(*col, 0.18 * a); c.stroke_preserve()
    c.set_line_width(lw); c.set_source_rgba(*col, a); c.stroke()
    c.restore()


def glow(c, x, y, r, col, a):
    gr = cairo.RadialGradient(x, y, 1, x, y, r)
    gr.add_color_stop_rgba(0, *col, a); gr.add_color_stop_rgba(1, *col, 0)
    c.set_source(gr); c.arc(x, y, r, 0, 2 * math.pi); c.fill()


def ink_line(c, x0, y, L, k, a):
    c.new_path()
    n = max(2, int(40 * k))
    for i in range(n):
        u = i / 39
        (c.move_to if i == 0 else c.line_to)(x0 + L * u, y + 5 * math.sin(u * 23) + 3 * math.sin(u * 61))
    c.set_line_width(5); c.set_source_rgba(0.16, 0.18, 0.36, a); c.stroke()


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    post = smooth((t - T_DROP) / 2.5) if t >= T_DROP else 0.0
    tense = clamp(t / 10.0) * (1 - post)
    sky = cairo.LinearGradient(0, 0, 0, H)
    sky.add_color_stop_rgb(0, *mix3((0.08, 0.04, 0.12), (0.02, 0.04, 0.13), post))
    sky.add_color_stop_rgb(0.6, *mix3((0.15, 0.05, 0.13), (0.04, 0.09, 0.22), post))
    sky.add_color_stop_rgb(1, *mix3((0.20, 0.06, 0.10), (0.05, 0.12, 0.24), post))
    c.set_source(sky); c.paint()
    if tense > 0:                                              # hot, pulsing glow around the restless head
        pulse = 0.5 + 0.5 * math.sin(t * (4 + 0.5 * t))
        glow(c, CX, CY + 80, 620, (0.9, 0.25, 0.25), (0.10 + 0.08 * pulse) * tense)
    for sx, sy, sr, sp in STARS:
        c.set_source_rgba(0.9, 0.93, 1, (0.08 + 0.1 * math.sin(t * 1.3 + sp)) + 0.45 * post * (0.6 + 0.4 * math.sin(t * 1.7 + sp)))
        c.arc(sx, sy, sr, 0, 2 * math.pi); c.fill()
    if post > 0:                                               # moon
        glow(c, 830, 640, 240, (0.6, 0.75, 1.0), 0.35 * post)
        c.push_group()
        c.set_source_rgb(0.95, 0.96, 1.0); c.arc(830, 640, 58, 0, 2 * math.pi); c.fill()
        c.set_operator(cairo.OPERATOR_CLEAR); c.arc(856, 626, 52, 0, 2 * math.pi); c.fill()
        c.pop_group_to_source(); c.paint_with_alpha(post)
    # nightstand, bed, pillow, sleeper
    c.set_source_rgb(*mix3((0.09, 0.04, 0.07), (0.03, 0.06, 0.14), post)); c.rectangle(0, 1400, W, H - 1400); c.fill()
    c.set_source_rgb(*mix3((0.16, 0.07, 0.10), (0.07, 0.11, 0.22), post)); c.rectangle(40, 1300, 220, 180); c.fill()
    c.set_source_rgb(*mix3((0.26, 0.12, 0.16), (0.12, 0.18, 0.32), post)); c.rectangle(30, 1290, 240, 18); c.fill()
    c.set_source_rgb(*mix3((0.20, 0.09, 0.13), (0.09, 0.14, 0.28), post)); c.rectangle(270, 1380, 830, 90); c.fill()
    c.save(); c.translate(330, 1310); c.scale(1.9, 0.55)
    c.arc(0, 0, 60, 0, 2 * math.pi); c.restore()
    c.set_source_rgb(*mix3((0.62, 0.52, 0.58), (0.55, 0.62, 0.78), post)); c.fill()
    breath = 6 * math.sin(t * (2.4 if t < T_DROP else 1.1))
    c.move_to(380, 1400); c.line_to(380, 1290)
    c.curve_to(470, 1230 - breath, 640, 1215 - breath, 760, 1240 - breath)
    c.curve_to(880, 1260, 980, 1270, 1100, 1300); c.line_to(1100, 1400); c.close_path()
    c.set_source_rgb(*mix3((0.45, 0.18, 0.24), (0.20, 0.32, 0.55), post)); c.fill()
    hx, hy = HEAD
    restless = 6 * math.sin(t * 5.1) * tense
    hx += restless
    c.set_source_rgb(*mix3((0.80, 0.60, 0.52), (0.62, 0.62, 0.72), post)); c.arc(hx, hy, 52, 0, 2 * math.pi); c.fill()
    c.set_source_rgb(*mix3((0.25, 0.12, 0.12), (0.13, 0.12, 0.22), post))
    c.arc(hx + 6, hy - 18, 50, math.pi * 1.05, math.pi * 1.95); c.fill()          # hair
    closed = t >= 11.8
    ex, ey = hx + 30, hy + 4
    if not closed:
        blink = (t % 3.7) < 0.12
        if blink:
            c.set_line_width(4); c.set_source_rgb(0.15, 0.08, 0.1); c.move_to(ex - 9, ey); c.line_to(ex + 9, ey); c.stroke()
        else:
            c.set_source_rgb(1, 1, 1); c.arc(ex, ey, 9, 0, 2 * math.pi); c.fill()
            c.set_source_rgb(0.12, 0.06, 0.08); c.arc(ex + 3 * math.sin(t * 3), ey - 2, 4.5, 0, 2 * math.pi); c.fill()
    else:
        c.set_line_width(4); c.set_source_rgb(0.15, 0.12, 0.22); c.arc(ex, ey - 2, 9, 0.2, math.pi - 0.2); c.stroke()
    # notepad
    pf = pad_frame(t)
    if pf:
        px, py, s = pf
        c.save(); c.translate(px, py); c.rotate(-0.03); c.scale(s, s); c.translate(-PAD_C[0], -PAD_C[1])
        x0, y0 = PAD_C[0] - PAD_W / 2, PAD_C[1] - PAD_H / 2
        if t >= T_DROP:
            glow(c, PAD_C[0], PAD_C[1], 420, (1.0, 0.85, 0.55), 0.28 * (1 - 0.6 * post))
        c.set_source_rgba(0, 0, 0, 0.35); c.rectangle(x0 + 10, y0 + 14, PAD_W, PAD_H); c.fill()
        c.set_source_rgb(0.97, 0.94, 0.85); c.rectangle(x0, y0, PAD_W, PAD_H); c.fill()
        c.set_source_rgb(0.86, 0.35, 0.32); c.rectangle(x0, y0, PAD_W, 52); c.fill()
        for j in range(6):
            lx, ly = line_xy(j)
            c.set_source_rgba(0.55, 0.66, 0.85, 0.5); c.set_line_width(2)
            c.move_to(x0 + 30, ly + 22); c.line_to(x0 + PAD_W - 30, ly + 22); c.stroke()
            k = clamp((t - LINE_T[j]) / 0.4)
            if k > 0:
                c.set_line_width(3.5); c.set_source_rgba(0.16, 0.18, 0.36, k)
                c.rectangle(x0 + 42, ly - 14, 26, 26); c.stroke()
                ink_line(c, lx, ly, LINE_L[j], smooth(k), 1.0)
        c.restore()
    # thoughts
    for i in range(NTH):
        ta, a0, rx, ry, sz, ph, jp = THOUGHTS[i]
        if t < ta:
            continue
        pop = smooth((t - ta) / 0.25)
        j = i // 2
        ts, tl = LINE_T[j] - 0.5, LINE_T[j]
        col = (1.0, 0.45, 0.35)
        if t < ts:
            x, y = swarm_pos(i, t)
            scribble(c, x, y, sz * pop * (1 + 0.06 * math.sin(t * 9 + jp)), ph + t * 1.5, col, 0.95)
        elif t < tl:
            k = smooth((t - ts) / 0.5)
            x0_, y0_ = swarm_pos(i, ts)
            lx, ly = line_xy(j)
            tx, ty = lx + LINE_L[j] * (0.25 + 0.5 * (i % 2)), ly
            x, y = lerp(x0_, tx, k), lerp(y0_, ty, k) - 80 * math.sin(math.pi * k)
            scribble(c, x, y, sz * (1 - 0.8 * k), ph + t * 1.5, mix3(col, (1, 0.85, 0.5), k), 1.0)
            glow(c, x, y, 50, (1, 0.8, 0.5), 0.4 * k)
        elif t < tl + 0.3:
            lx, ly = line_xy(j)
            glow(c, lx + LINE_L[j] * (0.25 + 0.5 * (i % 2)), ly, 70, (1, 0.85, 0.55), 0.5 * (1 - (t - tl) / 0.3))
    # z's drifting up from the sleeper
    for zt in Z_T:
        u = t - zt
        if 0 <= u < 2.6:
            a = clamp(u / 0.4) * clamp((2.6 - u) / 0.8)
            zx, zy, zs = HEAD[0] + 60 + 70 * u, HEAD[1] - 80 - 120 * u, 18 + 10 * u
            c.set_line_width(5); c.set_source_rgba(0.75, 0.85, 1.0, 0.8 * a)
            c.move_to(zx - zs, zy - zs); c.line_to(zx + zs, zy - zs); c.line_to(zx - zs, zy + zs); c.line_to(zx + zs, zy + zs)
            c.stroke()
    f2 = t - T_DROP
    if 0 <= f2 < 0.3:
        c.set_source_rgba(1, 0.92, 0.75, 0.35 * (1 - f2 / 0.3) ** 2); c.paint()
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
CORAL = (255, 140, 120)
GOLD = (255, 220, 130)
ICE = (190, 215, 255)


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 3.9)
    ctext(d, (540, 380), "Can't switch off", font("Bold", 66), WHITE, h)
    ctext(d, (540, 466), "at night?", font("Bold", 66), CORAL, h)
    b = win(t, 4.1, 9.8, 0.4, 0.3)
    ctext(d, (540, 360), "Tomorrow's tasks", font("Bold", 58), WHITE, b)
    ctext(d, (540, 444), "keep looping.", font("Bold", 58), CORAL, b)
    a = win(t, 10.2, 14.4, 0.4, 0.4)
    ctext(d, (540, 330), "Write them down:", font("Bold", 50), WHITE, a)
    ctext(d, (540, 445), "9 min", font("Bold", 130), GOLD, a)
    a2 = win(t, 11.0, 14.4, 0.4, 0.4)
    ctext(d, (540, 555), "faster asleep (16 vs 25)", font("Regular", 40), ICE, a2)
    p = win(t, 14.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 360), "Tonight, list tomorrow.", font("Bold", 60), WHITE, p)
    ctext(d, (540, 440), "5 minutes. Be specific.", font("Bold", 50), GOLD, p)
    q = win(t, 15.2, 20.1, 0.6, 0.1)
    ctext(d, (540, 1452), "Scullin et al., 2018 · 57 adults, sleep lab", font("Regular", 27), WHITE, q)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "todolist_silent.mp4"
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
