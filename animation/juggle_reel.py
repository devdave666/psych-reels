"""'Still learning' - an older learner's brain grows while they learn to juggle.  A stylised glowing brain hangs above two
hands on a deep plum night.  The hands start with one ball tossed hand to hand (1.0 ... 4.0 s), add a second (5.0 s), fumble
it off-screen (thrown 6.5 s, missed at 7.3 s), pick it up with a third ball and start a shaky three-ball cascade (8.0 s).
Every good catch sends a spark up into the brain.  At the drop (t = 10 s) the cascade locks onto the beat, the hands steady,
and the brain's network of connections grows and lights up gold and mint; the payoff lands at 14.6 s.  1080x1920, 20 s.

Boyke, Driemeyer, Gaser, Buechel & May (2008, Journal of Neuroscience 28(28):7031-7035, 'Training-induced brain structure
changes in the elderly'): 44 healthy adults aged 50-67 (mean 59.1) had 3 months to learn three-ball cascade juggling, 25 age-
matched controls did not.  MRI at baseline, after 3 months and 3 months after practice stopped.  Trainees (main analysis: the
25 best jugglers vs 25 controls) showed transient grey-matter increases in visual-motion area hMT/V5, the left hippocampus and
the nucleus accumbens; they learned less proficiently than 20-year-olds in the earlier study (Draganski et al., 2004, Nature),
only 10 of 44 reached 60 s of juggling, and the gains faded after practice stopped (caveats go in the caption).
Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python juggle_reel.py out_silent.mp4      render
       python juggle_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
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
GRAV = 2000.0                                   # px / s^2 for the ball arcs
HAND_X = (390.0, 690.0)                         # left, right hand centres
HAND_Y = 1345.0
BRAIN = (540.0, 805.0, 300.0, 205.0)            # centre x, y, radius x, y
BALL_R = 33.0
BALL_COL = [(1.0, 0.47, 0.42), (0.36, 0.90, 0.76), (1.0, 0.80, 0.32)]
BALL_IN = [0.5, 4.4, 7.4]                       # when each ball first appears in a hand
BALL_HAND0 = [0, 1, 0]
T_FUMBLE_THROW, T_MISS = 6.5, 7.3
T_PICKUP = 7.5

# throw list: (time, ball, from hand, flight time, dropped)
THROWS = [(1.0, 0, 0, 0.8, False), (2.0, 0, 1, 0.8, False), (3.0, 0, 0, 0.8, False), (4.0, 0, 1, 0.8, False),
          (5.0, 0, 0, 0.8, False), (5.5, 1, 1, 0.8, False), (6.0, 0, 1, 0.8, False),
          (T_FUMBLE_THROW, 1, 0, 0.8, True), (7.0, 0, 0, 0.8, False)]
CASCADE_ORDER = [1, 0, 2]
for n in range(24):                              # three-ball cascade, one throw per beat from 8.0 s
    tt = 8.0 + 0.5 * n
    if tt > DUR + 1:
        break
    THROWS.append((tt, CASCADE_ORDER[n % 3], n % 2, 1.0, False))
THROWS.sort()
CATCH_T = [t0 + f for t0, b, h, f, dr in THROWS if not dr and t0 + f <= DUR]
rng = np.random.default_rng(66)
JIT = {i: (rng.uniform(-1, 1), rng.uniform(-1, 1)) for i in range(len(THROWS))}

# brain network: nodes inside the outline, edges between near neighbours, each with a reveal threshold
NODES = []
while len(NODES) < 46:
    u, v = rng.uniform(-1, 1), rng.uniform(-1, 1)
    if u * u + v * v < 0.78:
        NODES.append((BRAIN[0] + u * BRAIN[2] * 0.92, BRAIN[1] + v * BRAIN[3] * 0.9, rng.uniform(0, 6.28)))
EDGES = []
for i, (x1, y1, _) in enumerate(NODES):
    d = sorted(((math.hypot(x1 - x2, y1 - y2), j) for j, (x2, y2, _) in enumerate(NODES) if j != i))
    for dist, j in d[:3]:
        if i < j or (j, i) not in [(a, b) for a, b, _, _ in EDGES]:
            if (min(i, j), max(i, j)) not in [(a, b) for a, b, _, _ in EDGES]:
                EDGES.append((min(i, j), max(i, j), rng.uniform(0.02, 0.98), rng.uniform(-0.25, 0.25)))
STARS = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.8, 2.2), rng.uniform(0, 6.28)) for _ in range(70)]
SPARK_T = [ct for ct in CATCH_T]
SPARK_NODE = [int(rng.integers(0, len(NODES))) for _ in SPARK_T]


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def glow(c, x, y, r, col, a):
    if a <= 0.003:
        return
    gr = cairo.RadialGradient(x, y, 1, x, y, r)
    gr.add_color_stop_rgba(0, *col, a); gr.add_color_stop_rgba(1, *col, 0)
    c.set_source(gr); c.arc(x, y, r, 0, 2 * math.pi); c.fill()


def lock_k(t):
    """0 before the drop, 1 once the cascade is locked in"""
    return smooth((t - T_DROP) / 0.8) if t >= T_DROP else 0.0


def shake(t):
    """hand / throw wobble: clumsy at first, steadier with practice, gone after the drop"""
    return lerp(1.0, 0.45, clamp(t / 9.5)) * (1 - lock_k(t))


def growth(t):
    """how much of the brain network has grown, 0..1"""
    pre = 0.2 * sum(1 for ct in CATCH_T if ct <= t and ct < T_DROP) / max(1, sum(1 for ct in CATCH_T if ct < T_DROP))
    if t < T_DROP:
        return pre
    return lerp(0.2, 1.0, smooth((t - T_DROP) / 3.2))


def hand_pos(h, t):
    side = -1 if h == 0 else 1                                       # outer direction
    ph = 2 * math.pi * (t - (0.0 if h == 0 else 0.5))                # inner at the throw, outer half a beat later
    s = shake(t)
    x = HAND_X[h] - side * 34 * math.cos(ph) + s * 9 * math.sin(t * 13.0 + h * 2)
    y = HAND_Y + 16 * math.sin(ph) + s * 7 * math.sin(t * 11.0 + h)
    return x, y


def ball_pos(b, t):
    """(x, y, alpha, scale) of ball b at time t, or None when hidden"""
    if t < BALL_IN[b] - 0.25:
        return None
    mine = [(i, th) for i, th in enumerate(THROWS) if th[1] == b]
    last = None
    for i, th in mine:
        if th[0] <= t:
            last = (i, th)
    pop = smooth((t - (BALL_IN[b] - 0.25)) / 0.25)
    off = (26, -8) if (b == 2 and t < 9.0) else (0, 0)
    if last is None:
        hx, hy = hand_pos(BALL_HAND0[b], t)
        return hx + off[0], hy - 34 + off[1], pop, pop
    i, (t0, _, h, f, dropped) = last
    sx, sy = hand_pos(h, t0)
    sy -= 34
    if dropped:
        ex, ey = HAND_X[1] + 190, HAND_Y - 34
    else:
        ex, ey = hand_pos(1 - h, t0 + f)
        ey -= 34
        jx, jy = JIT[i]
        ex += 0.0
    u = (t - t0) / f
    if u <= 1:
        jx, jy = JIT[i]
        s = shake(t0)
        hgt = GRAV * f * f / 8 * (1 + 0.18 * s * jy)
        x = lerp(sx, ex, u) + 60 * s * jx * math.sin(math.pi * u)
        y = lerp(sy, ey, u) - 4 * hgt * u * (1 - u)
        return x, y, 1.0, 1.0
    if dropped:                                                      # keeps falling past the hand, off-screen
        k = t - (t0 + f)
        vx = (ex - sx) / f
        vy = (ey - sy) / f + 4 * GRAV * f * f / 8 / f
        x, y = ex + vx * k, ey + vy * k + 0.5 * GRAV * k * k
        if t < T_PICKUP - 0.25:
            return (x, y, clamp(1 - k / 0.6), 1.0) if y < H + 60 else None
        hx, hy = hand_pos(0, t)
        p = smooth((t - (T_PICKUP - 0.25)) / 0.25)
        return hx - 8, hy - 34, p, p
    hx, hy = hand_pos(1 - h, t)
    return hx + off[0], hy - 34 + off[1], 1.0, 1.0


def brain_path(c, scale=1.0):
    bx, by, rx, ry = BRAIN
    c.new_path()
    n = 180
    for k in range(n + 1):
        a = k / n * 2 * math.pi
        bump = 1 + 0.035 * math.sin(11 * a) + 0.02 * math.sin(5 * a + 1)
        flat = 1 - 0.12 * max(0.0, math.sin(a)) ** 2                  # flatter underside
        x = bx + rx * scale * bump * math.cos(a)
        y = by + ry * scale * bump * flat * math.sin(a)
        (c.move_to if k == 0 else c.line_to)(x, y)
    c.close_path()


def draw_brain(c, t, g, lk):
    bx, by, rx, ry = BRAIN
    beat = math.exp(-((t - T_DROP) % 0.5) * 7) if t >= T_DROP else 0.0
    glow(c, bx, by, 520, mix3((0.45, 0.30, 0.75), (1.0, 0.70, 0.40), lk), 0.16 + 0.22 * g + 0.08 * beat * lk)
    # cerebellum + stem
    c.set_source_rgba(*mix3((0.25, 0.20, 0.42), (0.42, 0.26, 0.40), lk), 0.95)
    c.save(); c.translate(bx + 175, by + 168); c.scale(1.0, 0.62); c.arc(0, 0, 88, 0, 2 * math.pi); c.restore(); c.fill()
    c.move_to(bx + 60, by + 150); c.curve_to(bx + 70, by + 230, bx + 95, by + 280, bx + 110, by + 300)
    c.line_to(bx + 150, by + 290); c.curve_to(bx + 128, by + 250, bx + 122, by + 200, bx + 130, by + 150)
    c.close_path(); c.fill()
    # cerebrum body
    brain_path(c)
    fill = cairo.LinearGradient(0, by - ry, 0, by + ry)
    fill.add_color_stop_rgb(0, *mix3((0.30, 0.24, 0.52), (0.55, 0.30, 0.50), lk))
    fill.add_color_stop_rgb(1, *mix3((0.17, 0.13, 0.32), (0.30, 0.15, 0.32), lk))
    c.set_source(fill); c.fill_preserve()
    c.set_line_width(6); c.set_source_rgba(*mix3((0.62, 0.55, 0.90), (1.0, 0.82, 0.55), lk), 0.75 + 0.25 * beat); c.stroke()
    # a few folds
    c.save(); brain_path(c, 0.98); c.clip()
    c.set_line_width(4); c.set_source_rgba(*mix3((0.45, 0.38, 0.72), (0.80, 0.55, 0.62), lk), 0.55)
    for k, (fx, fy, fl) in enumerate([(-0.55, -0.35, 0.7), (-0.1, -0.55, 0.8), (0.35, -0.3, 0.6), (-0.45, 0.25, 0.8),
                                      (0.15, 0.1, 0.9), (0.55, 0.35, 0.5)]):
        x0, y0 = bx + fx * rx, by + fy * ry
        c.move_to(x0, y0)
        c.curve_to(x0 + 40 * fl, y0 - 30, x0 + 80 * fl, y0 + 30, x0 + 130 * fl, y0 + 5 * (k % 2 * 2 - 1))
        c.stroke()
    # the network: edges grow from node a to node b when growth passes their threshold
    for a, b2, thr, bend in EDGES:
        p = clamp((g - thr * 0.95) / 0.12) if g > 0 else 0.0
        if p <= 0:
            continue
        x1, y1, _ = NODES[a]; x2, y2, _ = NODES[b2]
        mx, my = (x1 + x2) / 2 - (y2 - y1) * bend, (y1 + y2) / 2 + (x2 - x1) * bend
        col = mix3((0.55, 0.85, 1.0), (1.0, 0.85, 0.45) if thr > 0.5 else (0.45, 1.0, 0.82), lk)
        for lw, al in ((12, 0.12), (4, 0.85)):
            c.set_line_width(lw); c.set_source_rgba(*col, al * (0.7 + 0.3 * beat))
            c.move_to(x1, y1)
            # draw the partial quadratic up to p
            q0x, q0y = lerp(x1, mx, p), lerp(y1, my, p)
            q1x, q1y = lerp(mx, x2, p), lerp(my, y2, p)
            ex, ey = lerp(q0x, q1x, p), lerp(q0y, q1y, p)
            c.curve_to(x1 + (q0x - x1) * 2 / 3, y1 + (q0y - y1) * 2 / 3,
                       ex + (q0x - ex) * 2 / 3, ey + (q0y - ey) * 2 / 3, ex, ey)
            c.stroke()
    for k, (x, y, ph) in enumerate(NODES):
        lit = clamp(g * 1.4 - (k % 7) * 0.08) if g > 0 else 0.0
        tw = 0.6 + 0.4 * math.sin(t * 3 + ph)
        r = 5 + 4 * lit
        glow(c, x, y, 26 + 14 * lit, mix3((0.6, 0.8, 1.0), (1.0, 0.9, 0.6), lk), (0.10 + 0.45 * lit) * tw)
        c.set_source_rgba(*mix3((0.70, 0.72, 0.95), (1.0, 0.95, 0.80), lit * lk + 0.4 * lit), 0.35 + 0.65 * lit)
        c.arc(x, y, r, 0, 2 * math.pi); c.fill()
    c.restore()


def draw_hand(c, h, t, lk):
    x, y = hand_pos(h, t)
    side = -1 if h == 0 else 1
    skin = mix3((0.78, 0.62, 0.58), (0.95, 0.74, 0.60), lk)
    sleeve = mix3((0.26, 0.30, 0.52), (0.30, 0.52, 0.62), lk)
    # forearm from below the frame
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_source_rgb(*sleeve); c.set_line_width(74)
    c.move_to(x + side * 150, H + 60); c.line_to(x + side * 30, y + 70); c.stroke()
    c.set_source_rgb(*mix3(sleeve, (1, 1, 1), 0.15)); c.set_line_width(80)
    c.move_to(x + side * 52, y + 120); c.line_to(x + side * 38, y + 92); c.stroke()
    # cupped palm
    c.set_source_rgb(*skin)
    c.move_to(x - 58, y - 6)
    c.curve_to(x - 60, y + 40, x - 30, y + 70, x, y + 70)
    c.curve_to(x + 30, y + 70, x + 60, y + 40, x + 58, y - 6)
    c.curve_to(x + 30, y + 14, x - 30, y + 14, x - 58, y - 6)
    c.close_path(); c.fill()
    # thumb on the inner side
    c.set_line_width(26); c.move_to(x - side * 48, y + 22); c.line_to(x - side * 70, y - 4); c.stroke()
    c.set_source_rgba(0, 0, 0, 0.12); c.set_line_width(3)
    for k in (-24, 0, 24):
        c.move_to(x + k, y + 28); c.line_to(x + k * 1.1, y + 52); c.stroke()


def draw_ball(c, b, t, lk):
    p = ball_pos(b, t)
    if p is None:
        return
    x, y, a, s = p
    if a <= 0.01:
        return
    col = BALL_COL[b]
    glow(c, x, y, 70 * s, col, (0.18 + 0.35 * lk) * a)
    r = BALL_R * s
    gr = cairo.RadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r)
    gr.add_color_stop_rgba(0, *mix3(col, (1, 1, 1), 0.55), a)
    gr.add_color_stop_rgba(1, *mix3(col, (0, 0, 0), 0.25), a)
    c.set_source(gr); c.arc(x, y, r, 0, 2 * math.pi); c.fill()
    c.set_source_rgba(0, 0, 0, 0.18 * a); c.set_line_width(3)
    c.arc(x, y, r * 0.9, 0.2, 1.2); c.stroke()


def draw_trails(c, t, lk):
    if lk <= 0:
        return
    for b in range(3):
        for k in range(1, 9):
            p = ball_pos(b, t - k * 0.035)
            if p is None:
                continue
            x, y, a, s = p
            c.set_source_rgba(*BALL_COL[b], 0.20 * lk * a * (1 - k / 9))
            c.arc(x, y, BALL_R * s * (1 - k / 14), 0, 2 * math.pi); c.fill()


def draw_sparks(c, t, lk):
    for st, ni in zip(SPARK_T, SPARK_NODE):
        u = (t - st) / 0.55
        if 0 <= u <= 1:
            pre = st < T_DROP
            hx = HAND_X[0] if (round(st * 2) % 2 == 0) else HAND_X[1]
            nx, ny, _ = NODES[ni]
            k = smooth(u)
            x = lerp(hx, nx, k) + 40 * math.sin(math.pi * u) * (1 if ni % 2 else -1)
            y = lerp(HAND_Y - 60, ny, k)
            col = (0.7, 0.85, 1.0) if pre else (1.0, 0.9, 0.55)
            a = (0.55 if pre else 1.0) * math.sin(math.pi * u)
            glow(c, x, y, 40, col, 0.5 * a)
            c.set_source_rgba(1, 1, 1, 0.9 * a); c.arc(x, y, 4.5, 0, 2 * math.pi); c.fill()


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    lk = lock_k(t)
    g = growth(t)
    bg = cairo.LinearGradient(0, 0, 0, H)
    bg.add_color_stop_rgb(0, *mix3((0.05, 0.04, 0.12), (0.10, 0.05, 0.16), lk))
    bg.add_color_stop_rgb(0.45, *mix3((0.12, 0.08, 0.24), (0.26, 0.10, 0.30), lk))
    bg.add_color_stop_rgb(1, *mix3((0.06, 0.05, 0.14), (0.16, 0.07, 0.18), lk))
    c.set_source(bg); c.paint()
    for sx, sy, sr, sp in STARS:
        c.set_source_rgba(0.85, 0.85, 1.0, (0.25 + 0.25 * lk) * (0.5 + 0.5 * math.sin(t * 1.3 + sp)))
        c.arc(sx, (sy - 6 * t) % H, sr, 0, 2 * math.pi); c.fill()
    glow(c, 540, HAND_Y - 120, 420, mix3((0.35, 0.30, 0.70), (1.0, 0.55, 0.45), lk), 0.10 + 0.12 * lk)
    draw_brain(c, t, g, lk)
    draw_sparks(c, t, lk)
    draw_trails(c, t, lk)
    # balls behind the hands while held, hands, then balls in the air on top
    for h in (0, 1):
        draw_hand(c, h, t, lk)
    for b in range(3):
        draw_ball(c, b, t, lk)
    f2 = t - T_DROP
    if 0 <= f2 < 0.3:
        c.set_source_rgba(1, 0.92, 0.8, 0.45 * (1 - f2 / 0.3) ** 2); c.paint()
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
LILAC = (200, 185, 255)
MINT = (150, 240, 205)
GOLD = (255, 214, 120)
PEACH = (255, 205, 180)


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 3.9)
    ctext(d, (540, 340), "Think you're too old", font("Bold", 60), WHITE, h)
    ctext(d, (540, 428), "to learn something new?", font("Bold", 60), LILAC, h)
    b = win(t, 4.1, 9.8, 0.4, 0.3)
    ctext(d, (540, 340), "Adults aged 50 to 67", font("Bold", 60), WHITE, b)
    ctext(d, (540, 426), "learned to juggle.", font("Bold", 60), LILAC, b)
    a = win(t, 10.2, 14.4, 0.4, 0.4)
    ctext(d, (540, 300), "Brain scans after 3 months:", font("Bold", 48), WHITE, a)
    ctext(d, (540, 398), "more grey matter", font("Bold", 84), GOLD, a)
    a2 = win(t, 10.9, 14.4, 0.4, 0.4)
    ctext(d, (540, 490), "in motion and memory areas", font("Bold", 40), PEACH, a2)
    p = win(t, 14.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 340), "Your brain still adapts.", font("Bold", 66), WHITE, p)
    ctext(d, (540, 425), "Start the thing you want to learn.", font("Bold", 44), GOLD, p)
    q = win(t, 15.2, 20.1, 0.6, 0.1)
    ctext(d, (540, 498), "Boyke et al., 2008 · Journal of Neuroscience", font("Regular", 28), WHITE, q)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "juggle_silent.mp4"
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
