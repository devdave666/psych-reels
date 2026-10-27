"""'Be kind first' - self-compassion after failure. A seedling under a storm cloud. 1080x1920, 20 s.

Breines & Chen (2012, Personality and Social Psychology Bulletin, Experiment 3): 86 undergraduates took a hard antonyms
test (mean 4/10), then got instructions to study for a second test.  Those who saw a self-compassionate line ("you're not
alone ... try not to be too hard on yourself") studied 306.5 s on average versus 203.2 s with no message (+51%, p < .05);
versus a self-esteem line (229.9 s) the difference was only marginal (p = .085).  Second-test scores did not differ
significantly.  Here: the storm and a wilting sprout build up, the cloud parts on the drop (t = 10 s), the sprout stands
and grows 51% taller on the beats of the drop (12.0, 12.5, 13.0 s) and blooms.
Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python selfcompassion_reel.py out_silent.mp4      render
       python selfcompassion_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
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
BARS_T = [12.0, 12.5, 13.0]
T_NUM = 12.0
T_BLOOM = 13.6
T_FIRE = [14.0, 14.45, 14.9, 15.5, 16.2, 17.0]
LIGHTNING = [4.6, 7.2, 9.0]
BASE = (540, 1150)                         # where the stem leaves the pot
H0 = 230.0
GROW = 0.51
rng = np.random.default_rng(5)

RAIN = [(rng.uniform(-100, W + 100), rng.uniform(0, 1500), rng.uniform(0.7, 1.3)) for _ in range(150)]
FIRE = []
for k, tf in enumerate(T_FIRE):
    cx0 = (780, 320, 600, 860, 260, 520)[k]
    cy0 = (860, 800, 700, 1000, 960, 560)[k]
    col = ((1, 0.82, 0.35), (1.0, 0.65, 0.75), (1, 1, 1), (0.6, 0.95, 0.8), (1, 0.65, 0.75), (1, 0.82, 0.35))[k]
    FIRE.append((tf, cx0, cy0, col, [(rng.uniform(0, 6.283), rng.uniform(120, 330)) for _ in range(34)]))


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def wilt(t):
    w = smooth((t - 2.0) / 7.0)
    if t >= T_DROP:
        w *= 1 - smooth((t - T_DROP) / 1.0)
    return w


def grow(t):
    return sum(smooth((t - tb) / 0.2) for tb in BARS_T) / 3


def bez(p, u):
    a = (1 - u) ** 3, 3 * u * (1 - u) ** 2, 3 * u * u * (1 - u), u ** 3
    x = sum(w * q[0] for w, q in zip(a, p)); y = sum(w * q[1] for w, q in zip(a, p))
    d = (3 * (1 - u) ** 2, 6 * u * (1 - u), 3 * u * u)
    dx = sum(w * (p[i + 1][0] - p[i][0]) for i, w in enumerate(d)); dy = sum(w * (p[i + 1][1] - p[i][1]) for i, w in enumerate(d))
    return x, y, math.atan2(dy, dx)


def stem(t):
    w = wilt(t)
    h = H0 * (1 + GROW * grow(t)) * (1 - 0.18 * w)
    sway = 6 * math.sin(t * 1.7) * (1 - w)
    tip = (BASE[0] + 175 * w + sway, BASE[1] - h * (1 - 0.55 * w))
    return [BASE, (BASE[0], BASE[1] - h * 0.55), (BASE[0] + 20 * w + sway * 0.5, BASE[1] - h * (0.95 - 0.5 * w)), tip], w, h


def leaf(c, x, y, ang, ln, wd, col):
    c.save(); c.translate(x, y); c.rotate(ang)
    c.move_to(0, 0); c.curve_to(ln * 0.3, -wd, ln * 0.75, -wd * 0.8, ln, 0)
    c.curve_to(ln * 0.75, wd * 0.8, ln * 0.3, wd, 0, 0)
    c.set_source_rgb(*col); c.fill(); c.restore()


def flower(c, x, y, r, open_, col, core):
    if open_ <= 0:
        return
    for i in range(8):
        a = i * math.pi / 4 + 0.2
        c.save(); c.translate(x, y); c.rotate(a)
        c.set_source_rgb(*col); c.scale(1, 0.55)
        c.arc(r * 0.62 * open_, 0, r * 0.52 * open_, 0, 2 * math.pi); c.fill(); c.restore()
    c.set_source_rgb(*core); c.arc(x, y, r * 0.32 * open_, 0, 2 * math.pi); c.fill()


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    dawn = smooth((t - T_DROP) / 1.4)
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *mix3((0.06, 0.07, 0.16), (0.27, 0.19, 0.44), dawn))
    g.add_color_stop_rgb(0.6, *mix3((0.10, 0.12, 0.24), (0.80, 0.42, 0.52), dawn))
    g.add_color_stop_rgb(1, *mix3((0.08, 0.09, 0.16), (0.98, 0.66, 0.48), dawn))
    c.set_source(g); c.rectangle(0, 0, W, H); c.fill()

    if dawn > 0:                                                                          # sun rising behind the plant
        sy = lerp(1500, 840, dawn)
        sg = cairo.RadialGradient(540, sy, 40, 540, sy, 620)
        sg.add_color_stop_rgba(0, 1, 0.93, 0.65, 0.95 * dawn); sg.add_color_stop_rgba(0.25, 1, 0.78, 0.55, 0.5 * dawn)
        sg.add_color_stop_rgba(1, 1, 0.7, 0.5, 0)
        c.set_source(sg); c.rectangle(0, 0, W, H); c.fill()
        c.set_source_rgba(1, 0.96, 0.8, dawn); c.arc(540, sy, 150, 0, 2 * math.pi); c.fill()

    ground = mix3((0.12, 0.14, 0.2), (0.42, 0.26, 0.3), dawn)                              # ground
    c.set_source_rgb(*ground); c.rectangle(0, 1330, W, H - 1330); c.fill()

    # storm cloud
    leave = smooth((t - T_DROP) / 1.3)
    cl = smooth((t - 1.2) / 1.5)
    if cl > 0 and leave < 1:
        shade = mix3((0.17, 0.18, 0.28), (0.45, 0.35, 0.5), leave)
        blobs = [(-250, 30, 170), (-110, -40, 200), (60, -20, 220), (200, 30, 190), (330, 40, 150), (0, 70, 220), (-170, 80, 160), (190, 90, 160)]
        for i, (bx, by, br) in enumerate(blobs):
            off = (-1 if bx < 0 else 1) * 760 * leave
            c.set_source_rgba(*shade, cl * (1 - 0.6 * leave))
            c.arc(540 + bx + off + 8 * math.sin(t * 0.8 + i), 640 + by - 60 * (1 - cl), br * (0.5 + 0.5 * cl), 0, 2 * math.pi); c.fill()

    # rain
    rain_a = clamp((t - 1.6) / 2.0) * (1 - smooth((t - T_DROP) / 0.8)) * (0.5 + 0.5 * smooth((t - 3) / 6))
    if rain_a > 0.01:
        c.set_source_rgba(0.62, 0.72, 0.95, 0.55 * rain_a); c.set_line_width(4); c.set_line_cap(cairo.LINE_CAP_ROUND)
        for x, y0, sp in RAIN:
            yy = (y0 + t * 1300 * sp) % 1500 + 520
            if yy > 1330:
                continue
            xx = x - (yy - 520) * 0.12
            c.move_to(xx, yy); c.line_to(xx - 10, yy + 40 * sp); c.stroke()
    if 10.2 <= t < 11.8:                                                                    # gentle warm droplets
        a = math.sin(math.pi * (t - 10.2) / 1.6)
        for i, (x, y0, sp) in enumerate(RAIN[:40]):
            yy = 560 + ((y0 * 0.7 + (t - 10.2) * 420 * sp) % 760)
            c.set_source_rgba(1, 0.92, 0.7, 0.5 * a); c.arc(x * 0.7 + 160, yy, 5, 0, 2 * math.pi); c.fill()

    # the plant
    pts, w, h = stem(t)
    shade_g = mix3((0.34, 0.50, 0.40), (0.38, 0.78, 0.45), 1 - w)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_source_rgb(*shade_g); c.set_line_width(20)
    c.move_to(*pts[0]); c.curve_to(*pts[1], *pts[2], *pts[3]); c.stroke()
    for u, side, ln in ((0.30, -1, 130), (0.42, 1, 140), (0.58, -1, 115), (0.70, 1, 120), (0.82, -1, 90)):
        x, y, a = bez(pts, u)
        down = math.pi / 2 - side * 0.55 - (2 * math.pi if side < 0 else 0)
        ang = lerp(-math.pi / 2 + side * 0.95, down, w)
        leaf(c, x, y, ang, ln * (1 + 0.5 * grow(t)) * (1 - 0.15 * w), 34, shade_g)
    tx, ty, ta = bez(pts, 1.0)
    bud = smooth((t - 11.6) / 1.2)
    bl = smooth((t - T_BLOOM) / 0.9)
    if bl > 0:
        flower(c, tx, ty - 12, 62 + 14 * bl, bl, (1.0, 0.62, 0.74), (1.0, 0.85, 0.35))
    elif t < T_BLOOM and w < 0.5:
        c.set_source_rgb(0.95, 0.62, 0.72); c.arc(tx, ty - 6, 12 + 10 * bud, 0, 2 * math.pi); c.fill()
    elif w >= 0.5:
        c.set_source_rgb(0.5, 0.45, 0.45); c.arc(tx, ty + 6, 10, 0, 2 * math.pi); c.fill()
    # dashed line at the old height
    if t >= 11.9:
        a = smooth((t - 11.9) / 0.5)
        c.set_source_rgba(1, 1, 1, 0.5 * a); c.set_line_width(4); c.set_dash([16, 14])
        c.move_to(380, BASE[1] - H0); c.line_to(700, BASE[1] - H0); c.stroke(); c.set_dash([])
    # pot
    c.set_source_rgb(*mix3((0.40, 0.25, 0.22), (0.80, 0.45, 0.35), dawn))
    c.move_to(430, 1150); c.line_to(650, 1150); c.line_to(620, 1320); c.line_to(460, 1320); c.close_path(); c.fill()
    c.set_source_rgb(*mix3((0.46, 0.29, 0.25), (0.90, 0.52, 0.40), dawn)); c.rectangle(416, 1130, 248, 34); c.fill()

    for tf, fx0, fy0, col, parts in FIRE:                                                    # blossom bursts
        d = t - tf
        if 0 <= d < 1.4:
            for ang, spd in parts:
                r = spd * (1 - math.exp(-d * 3.0))
                c.set_source_rgba(*col, (1 - d / 1.4) ** 1.4)
                c.arc(fx0 + r * math.cos(ang), fy0 + r * math.sin(ang) + 110 * d * d, 6 * (1 - d / 1.8), 0, 2 * math.pi); c.fill()
            if d < 0.2:
                c.set_source_rgba(1, 1, 1, 0.5 * (1 - d / 0.2)); c.arc(fx0, fy0, 70 * d / 0.2, 0, 2 * math.pi); c.fill()

    fl = 0.0                                                                                 # lightning flashes
    for tl in LIGHTNING:
        d = t - tl
        if 0 <= d < 0.35:
            fl = max(fl, (1 - d / 0.35) ** 2 * (1 if d < 0.15 else 0.6))
    if fl > 0:
        c.set_source_rgba(0.85, 0.9, 1, 0.45 * fl); c.paint()
    f2 = t - T_DROP
    if 0 <= f2 < 0.3:
        c.set_source_rgba(1, 0.95, 0.8, 0.45 * (1 - f2 / 0.3) ** 2); c.paint()
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
        d.text((xy[0] + 2, xy[1] + 3), s, font=f, fill=(0, 0, 0, int(130 * a)), anchor="mm")
        d.text(xy, s, font=f, fill=(*fill, int(255 * a)), anchor="mm")


WHITE = (250, 246, 240)
ROSE = (255, 170, 190)
GOLD = (255, 214, 120)


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 3.4)
    ctext(d, (540, 380), "You bombed the test.", font("Bold", 58), WHITE, h)
    ctext(d, (540, 460), "Now what?", font("Bold", 64), ROSE, h)
    ctext(d, (540, 380), "Beating yourself up?", font("Bold", 52), (190, 205, 240), win(t, 5.4, 9.6, 0.5, 0.3))
    k = win(t, 10.2, 11.9, 0.3, 0.3)
    ctext(d, (540, 380), "One kind sentence.", font("Bold", 58), GOLD, k)
    if t >= T_NUM:
        pops = [math.exp(-(t - tb) / 0.16) for tb in BARS_T if t >= tb]
        pop = max(pops) if pops else 0.0
        ctext(d, (540, 560), f"+{int(round(51 * grow(t)))}%", font("Bold", int(150 + 28 * pop)), GOLD, win(t, T_NUM, 20.1, 0.2, 0.1))
        ctext(d, (540, 668), "more study time than no message", font("Regular", 30), WHITE, win(t, 12.3, 20.1, 0.4, 0.1))
    p = win(t, 14.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 330), "Be kind first.", font("Bold", 52), WHITE, p)
    ctext(d, (540, 400), "Then try again.", font("Bold", 52), ROSE, p)
    q = win(t, 15.2, 20.1, 0.6, 0.1)
    ctext(d, (540, 1410), "Breines & Chen, 2012 · 86 students", font("Regular", 27), WHITE, q)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "selfcompassion_silent.mp4"
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
