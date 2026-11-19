"""A wandering mind - a glowing 'mind' orb drifts away from a figure under a bare tree, then comes home. 1080x1920, 20 s.

Killingsworth & Gilbert (2010, Science 330:932, "A wandering mind is an unhappy mind"): an iPhone app pinged 2,250 adults
at random moments and asked how they felt, what they were doing and whether they were thinking about something else.
Minds wandered in 46.9% of the samples, and people were less happy when their minds were wandering than when they were
not, during every activity, including the least enjoyable ones.
Here a dusk-blue, colourless scene: a figure sits on a rock under a bare tree while a gold orb (their mind) floats out on
a thread and visits four 'elsewhere' bubbles - phone, clock, calendar, envelope (T_VISIT, 1.8 - 7.8 s).  From 8.6 s the
thread reels it back; at the drop (10.0 s) it lands in the figure's head, the scene floods with colour, the tree blossoms
and petals and fireflies drift.  Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python wander_reel.py out_silent.mp4      render
       python wander_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
"""
import math
import subprocess
import sys
from pathlib import Path

import cairo
import stickrig
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from stickrig import P, catmull, clamp, draw_figure, joints_from, lerp, lerp_pose, smooth

W, H, FPS, DUR = 1080, 1920, 30, 20.0
SUB, SHUTTER = 4, 0.5
FONTS = Path(__file__).resolve().parent.parent / "fonts"
SAFE = (140, 260, 940, 1480)

CREAM = (246, 241, 230)
GOLD = (255, 204, 96)
T_LEAVE = 1.0                                    # orb leaves the head
T_VISIT = [1.8, 3.8, 5.8, 7.8]                   # orb reaches each bubble
T_REEL = 8.6                                     # thread starts reeling it home
T_DROP = 10.0
GROUND = 1400
FIG_X = 400
TREE = (720, GROUND)
BUBBLES = [(250, 760, "phone"), (800, 690, "clock"), (230, 1040, "calendar"), (560, 820, "mail")]
SLUMP = P(0.42, (1.5, 1.5), (1.35, 1.4), (0.75, 0.2), (0.55, 0.2))            # seated, hunched, hands on knees
UPRIGHT = P(0.0, (1.5, 1.5), (1.35, 1.4), (0.9, 0.55), (0.7, 0.55))           # sitting tall
FIG_S = 1.45

rng = np.random.default_rng(7)
BLOSSOM = [(rng.uniform(-200, 200), rng.uniform(-170, 120), rng.uniform(16, 30), rng.uniform(0, 1.4)) for _ in range(46)]
BLOSSOM = [b for b in BLOSSOM if (b[0] / 210) ** 2 + ((b[1] + 25) / 160) ** 2 < 1]
PETALS = [(rng.uniform(250, 1000), rng.uniform(0, 1), rng.uniform(0.6, 1.3), rng.uniform(0, 6.28)) for _ in range(34)]
FLIES = [(rng.uniform(150, 930), rng.uniform(650, 1350), rng.uniform(0, 6.28), rng.uniform(0.5, 1.2)) for _ in range(26)]
STARS = [(rng.uniform(0, W), rng.uniform(0, 1100), rng.uniform(1, 2.6), rng.uniform(0, 6.28)) for _ in range(90)]
BRANCHES = [((0, -380), (-150, -560), 13), ((0, -380), (160, -600), 13), ((-150, -560), (-230, -640), 7),
            ((-150, -560), (-90, -690), 7), ((160, -600), (240, -660), 7), ((160, -600), (110, -730), 7),
            ((0, -380), (20, -700), 10), ((20, -700), (-40, -790), 6), ((20, -700), (90, -800), 6)]


def bloom(t):
    return smooth((t - T_DROP) / 0.9)


def head_pos(t):
    pose = lerp_pose(SLUMP, UPRIGHT, smooth((t - T_DROP + 0.4) / 0.8))
    j = joints_from(pose, 0, 0)
    return j, pose


def orb_pos(t, head):
    """Where the mind is: path out through the four bubbles, then reeled back to the head."""
    hx, hy = head
    keys = [(T_LEAVE, hx, hy - 10), (T_LEAVE + 0.4, hx + 40, hy - 160)]
    for tv, (bx, by, _) in zip(T_VISIT, BUBBLES):
        keys += [(tv, bx, by), (tv + 0.9, bx + 20 * math.sin(tv), by - 15)]
    if t < T_LEAVE:
        return hx, hy - 10
    if t < T_REEL:
        x, y = catmull(keys, t)
        return x + 8 * math.sin(t * 3.1), y + 8 * math.cos(t * 2.3)
    sx, sy = catmull(keys, T_REEL)
    u = smooth((t - T_REEL) / (T_DROP - T_REEL)) ** 1.6
    arc = math.sin(u * math.pi) * 90
    return lerp(sx, hx, u), lerp(sy, hy, u) - arc


def icon(c, kind, x, y, a, t):
    c.set_source_rgba(0.85, 0.88, 0.95, a)
    c.set_line_width(5)
    if kind == "phone":
        c.new_path()
        r, w, h = 10, 46, 80
        c.arc(x - w / 2 + r, y - h / 2 + r, r, math.pi, 1.5 * math.pi); c.arc(x + w / 2 - r, y - h / 2 + r, r, 1.5 * math.pi, 0)
        c.arc(x + w / 2 - r, y + h / 2 - r, r, 0, 0.5 * math.pi); c.arc(x - w / 2 + r, y + h / 2 - r, r, 0.5 * math.pi, math.pi)
        c.close_path(); c.stroke()
        for k in range(3):
            c.rectangle(x - 13, y - 22 + 14 * k, 26, 6); c.fill()
    elif kind == "clock":
        c.new_path(); c.arc(x, y, 36, 0, 2 * math.pi); c.stroke()
        for ang, ln in ((t * 2.0, 26), (t * 0.3, 18)):
            c.move_to(x, y); c.line_to(x + ln * math.sin(ang), y - ln * math.cos(ang)); c.stroke()
    elif kind == "calendar":
        c.new_path(); c.rectangle(x - 36, y - 30, 72, 64); c.stroke()
        c.rectangle(x - 36, y - 30, 72, 14); c.fill()
        for i in range(3):
            for k in range(2):
                c.rectangle(x - 26 + 20 * i, y - 6 + 18 * k, 10, 9); c.fill()
    else:
        c.new_path(); c.rectangle(x - 38, y - 26, 76, 52); c.stroke()
        c.move_to(x - 38, y - 26); c.line_to(x, y + 6); c.line_to(x + 38, y - 26); c.stroke()


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    bl = bloom(t)
    # sky: cold dusk blue -> warm rose twilight
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, lerp(0.07, 0.10, bl), lerp(0.09, 0.07, bl), lerp(0.15, 0.24, bl))
    g.add_color_stop_rgb(0.6, lerp(0.17, 0.55, bl), lerp(0.20, 0.30, bl), lerp(0.27, 0.45, bl))
    g.add_color_stop_rgb(1, lerp(0.24, 0.98, bl), lerp(0.27, 0.62, bl), lerp(0.32, 0.48, bl))
    c.set_source(g); c.rectangle(0, 0, W, H); c.fill()
    for sx, sy, r, ph in STARS:
        c.set_source_rgba(1, 1, 1, (0.25 + 0.25 * math.sin(t * 1.7 + ph)) * (1 - 0.6 * bl))
        c.arc(sx, sy, r, 0, 2 * math.pi); c.fill()
    # moon glow (warms up at the drop)
    mg = cairo.RadialGradient(860, 330, 10, 860, 330, 300 + 200 * bl)
    mg.add_color_stop_rgba(0, 1, lerp(0.95, 0.85, bl), lerp(0.9, 0.6, bl), 0.18 + 0.25 * bl)
    mg.add_color_stop_rgba(1, 1, 0.8, 0.6, 0)
    c.set_source(mg); c.paint()

    # hills
    for hy, amp, col0, col1, ph in ((1330, 50, (0.13, 0.15, 0.20), (0.42, 0.26, 0.36), 0.7),
                                    (GROUND, 22, (0.08, 0.10, 0.13), (0.20, 0.25, 0.18), 2.4)):
        c.move_to(0, H)
        for i in range(37):
            x = W * i / 36
            c.line_to(x, hy - amp * math.sin(x / 240 + ph) - 0.4 * amp * math.sin(x / 90 + ph))
        c.line_to(W, H); c.close_path()
        c.set_source_rgb(*(lerp(a, b, bl) for a, b in zip(col0, col1))); c.fill()

    # tree
    tx, ty = TREE
    trunk = tuple(lerp(a, b, bl) for a, b in zip((0.10, 0.11, 0.14), (0.28, 0.17, 0.16)))
    c.set_source_rgb(*trunk); c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.move_to(tx - 26, ty + 10); c.curve_to(tx - 14, ty - 150, tx - 18, ty - 260, tx - 6, ty - 380)
    c.line_to(tx + 6, ty - 380); c.curve_to(tx + 10, ty - 260, tx + 18, ty - 150, tx + 30, ty + 10); c.close_path(); c.fill()
    for (ax, ay), (bx, by), wd in BRANCHES:
        c.set_line_width(wd * 1.6)
        c.move_to(tx + ax, ty + ay); c.line_to(tx + bx, ty + by); c.stroke()
    cx, cy = tx + 5, ty - 650                                  # canopy centre
    for k, (dx, dy, r, delay) in enumerate(BLOSSOM):
        u = smooth((t - T_DROP - 0.1 - delay * 0.8) / 0.45)
        if u <= 0:
            continue
        pop = 1 + 0.25 * math.sin(math.pi * clamp(u * 1.0))
        col = (1.0, 0.62 + 0.18 * ((k * 37) % 5) / 4, 0.72 + 0.1 * ((k * 13) % 3) / 2)
        c.set_source_rgba(*col, 0.85 * u)
        c.arc(cx + dx, cy + dy + 3 * math.sin(t * 1.3 + k), r * u * pop, 0, 2 * math.pi); c.fill()

    # rock + figure
    rock = tuple(lerp(a, b, bl) for a, b in zip((0.16, 0.17, 0.21), (0.40, 0.33, 0.36)))
    c.set_source_rgb(*rock)
    c.save(); c.translate(FIG_X - 30, GROUND - 8); c.scale(1.0, 0.62)
    c.arc(0, 0, 120, math.pi, 2 * math.pi); c.restore(); c.fill()
    c.rectangle(FIG_X - 150, GROUND - 26, 240, 30); c.fill()
    j, _ = head_pos(t)
    # place figure: hip on the rock top, drawn 1.45x
    hip = (FIG_X - 40, GROUND - 80)
    sc = lambda q: (hip[0] + FIG_S * (q[0] - j["hip"][0]), hip[1] + FIG_S * (q[1] - j["hip"][1]))
    j = dict(hip=hip, neck=sc(j["neck"]), head=sc(j["head"]), limbs=[[sc(q) for q in l] for l in j["limbs"]])
    figc = tuple(lerp(a, b, bl) for a, b in zip((0.55, 0.58, 0.64), (0.99, 0.95, 0.88)))

    r0 = stickrig.HEAD_R; stickrig.HEAD_R = r0 * FIG_S
    draw_figure(c, j, figc, 13 * FIG_S)
    stickrig.HEAD_R = r0
    head = j["head"]

    # bubbles ("elsewhere")
    for k, (bx, by, kind) in enumerate(BUBBLES):
        tv = T_VISIT[k]
        a = smooth((t - tv + 0.6) / 0.5) * (1 - smooth((t - T_DROP + 0.2) / 0.35))
        if a <= 0:
            continue
        lit = math.exp(-max(0, t - tv) / 0.7) * (t >= tv)
        r = 78 + 6 * math.sin(t * 1.4 + k) + 14 * lit
        c.set_source_rgba(0.55, 0.62, 0.78, 0.16 * a + 0.12 * lit)
        c.arc(bx, by, r, 0, 2 * math.pi); c.fill()
        c.set_source_rgba(0.75, 0.82, 0.95, 0.45 * a)
        c.set_line_width(3); c.arc(bx, by, r, 0, 2 * math.pi); c.stroke()
        icon(c, kind, bx, by, 0.8 * a, t)
    # thread + orb
    ox, oy = orb_pos(t, head)
    if T_LEAVE < t < T_DROP + 0.05:
        c.set_source_rgba(1, 0.85, 0.5, 0.5)
        c.set_line_width(3); c.set_dash([10, 12], -t * 40)
        mx, my = (head[0] + ox) / 2, min(head[1], oy) - 80
        c.move_to(*head); c.curve_to(head[0], my, mx, my, ox, oy); c.stroke()
        c.set_dash([])
    if t < T_DROP:
        rr = 20 + 3 * math.sin(t * 5)
        og = cairo.RadialGradient(ox, oy, 2, ox, oy, rr * 4)
        og.add_color_stop_rgba(0, 1, 0.92, 0.6, 0.95)
        og.add_color_stop_rgba(0.25, 1, 0.8, 0.4, 0.5)
        og.add_color_stop_rgba(1, 1, 0.7, 0.3, 0)
        c.set_source(og); c.arc(ox, oy, rr * 4, 0, 2 * math.pi); c.fill()
        c.set_source_rgba(1, 0.96, 0.8, 1); c.arc(ox, oy, rr * 0.55, 0, 2 * math.pi); c.fill()
    else:                                                         # mind home: warm halo around the head
        hg = cairo.RadialGradient(*head, 10, *head, 170 + 20 * math.sin(t * 2))
        hg.add_color_stop_rgba(0, 1, 0.85, 0.5, 0.55)
        hg.add_color_stop_rgba(1, 1, 0.75, 0.4, 0)
        c.set_source(hg); c.arc(*head, 200, 0, 2 * math.pi); c.fill()
        d = t - T_DROP                                            # ring burst at the drop
        if d < 1.0:
            c.set_source_rgba(1, 0.9, 0.6, 0.7 * (1 - d))
            c.set_line_width(6 * (1 - d) + 1)
            c.arc(*head, 40 + 520 * smooth(d), 0, 2 * math.pi); c.stroke()

    # petals + fireflies after the drop
    if bl > 0:
        for k, (px, ph, sp, rot) in enumerate(PETALS):
            u = (ph + (t - T_DROP) * 0.16 * sp) % 1.0
            x = px - u * 380 + 30 * math.sin(t * 1.5 + rot)
            y = cy - 120 + u * 1000
            c.save(); c.translate(x, y); c.rotate(rot + t * sp); c.scale(1, 0.55)
            c.set_source_rgba(1, 0.72, 0.8, 0.8 * bl * clamp((t - T_DROP - 0.4) / 0.6))
            c.arc(0, 0, 11, 0, 2 * math.pi); c.restore(); c.fill()
        for fx, fy, ph, sp in FLIES:
            x = fx + 40 * math.sin(t * sp + ph)
            y = fy + 30 * math.cos(t * sp * 0.8 + ph * 1.3)
            a = bl * (0.4 + 0.6 * max(0, math.sin(t * 2.5 * sp + ph)))
            fg = cairo.RadialGradient(x, y, 1, x, y, 16)
            fg.add_color_stop_rgba(0, 1, 0.95, 0.6, a)
            fg.add_color_stop_rgba(1, 1, 0.9, 0.5, 0)
            c.set_source(fg); c.arc(x, y, 16, 0, 2 * math.pi); c.fill()
    d = t - T_DROP
    if 0 <= d < 0.45:
        c.set_source_rgba(1, 0.92, 0.75, 0.4 * (1 - d / 0.45) ** 2); c.paint()
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
        d.text((xy[0] + 2, xy[1] + 4), s, font=f, fill=(0, 0, 0, int(160 * a)), anchor=anchor)
        d.text(xy, s, font=f, fill=(*fill, int(255 * a)), anchor=anchor)


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.2, 3.4, 0.25)
    if h > 0:
        pop = 1 + 0.1 * math.exp(-max(0, t - 0.5) / 0.18) * (t > 0.5)
        ctext(d, (540, 330), "Your mind is elsewhere", font("Bold", 56), CREAM, h)
        ctext(d, (540, 455), "46.9%", font("Bold", int(140 * pop)), GOLD, clamp((t - 0.5) / 0.25) * h)
        ctext(d, (540, 570), "of the time", font("Bold", 54), CREAM, clamp((t - 0.5) / 0.25) * h)
    a = win(t, 3.6, 6.6)
    ctext(d, (540, 360), "2,250 people got", font("Bold", 56), CREAM, a)
    ctext(d, (540, 445), "pinged at random:", font("Bold", 56), CREAM, a)
    a = win(t, 6.8, 9.6)
    ctext(d, (540, 360), "Where is your mind?", font("Bold", 56), CREAM, a)
    ctext(d, (540, 445), "How do you feel?", font("Bold", 56), GOLD, a)
    a = win(t, T_DROP, 14.2, 0.2, 0.4)
    if a > 0:
        pop = 1 + 0.12 * math.exp(-(t - T_DROP) / 0.18)
        ctext(d, (540, 370), "Happier", font("Bold", int(130 * pop)), GOLD, a)
        ctext(d, (540, 490), "when the mind stayed here", font("Bold", 52), CREAM, a)
    p = win(t, 14.6, 20.1, 0.5, 0.1)
    ctext(d, (540, 370), "Wherever you are,", font("Bold", 62), CREAM, p)
    ctext(d, (540, 470), "be all there.", font("Bold", 74), GOLD, p)
    ci = win(t, 15.2, 20.1, 0.6, 0.1)
    if ci > 0.01:
        d.rounded_rectangle((225, 1386, 855, 1474), radius=24, fill=(35, 22, 32, int(120 * ci)))
    ctext(d, (540, 1412), "Killingsworth & Gilbert, Science 2010", font("Regular", 27), (238, 228, 222), ci)
    ctext(d, (540, 1450), "2,250 adults, self-reported via app", font("Regular", 27), (238, 228, 222), ci)
    return ov


def compose(frame, t, debug=False):
    img = Image.fromarray(frame.clip(0, 255).astype(np.uint8)).convert("RGBA")
    img.alpha_composite(hud(t))
    if debug:
        ImageDraw.Draw(img).rectangle(SAFE, outline=(255, 0, 0, 255), width=3)
    out = img.convert("RGB")
    if t < 0.2:
        out = Image.eval(out, lambda v: int(v * smooth(t / 0.2)))
    return out


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "wander_silent.mp4"
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
