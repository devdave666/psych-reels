"""'Pair it with a treat' - temptation bundling. A dull grey barbell sits in the dark; a glowing music orb (the treat) drifts
close, snaps into the bar on the drop (t = 10 s) and the pair lifts off glowing. 1080x1920, 20 s.

Milkman, Minson & Volpp (2014, Management Science), 226 people: those who could hear gripping audiobooks ONLY at the gym visited
51% more often (full treatment) / 29% more (intermediate) than controls early on; the effect faded later (after Thanksgiving).
Bars grow to +51% on the beats of the drop (12.0, 12.5, 13.0 s).  Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python bundle_reel.py out_silent.mp4      render
       python bundle_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
"""
import math
import subprocess
import sys
from pathlib import Path

import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DUR = 1080, 1920, 30, 20.0
SUB, SHUTTER = 4, 0.5
CREAM_I = (246, 238, 255)
GOLD_I = (255, 209, 89)
PINK_I = (255, 150, 200)
FONTS = Path(__file__).resolve().parent.parent / "fonts"
SAFE = (140, 260, 940, 1480)

T_ORB = 3.0
T_DASH = 9.3
T_DROP = 10.0
BARS_T = [12.0, 12.5, 13.0]
T_NUM = 12.0
T_FIRE = [14.0, 14.45, 14.9, 15.5, 16.2, 17.0]
FLOOR_Y = 1150
FLY_Y = 700
BASE_Y = 1180

rng = np.random.default_rng(23)
STARS = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1.5, 3.5), rng.uniform(0, 6.28)) for _ in range(70)]
FIRE = []
for k, tf in enumerate(T_FIRE):
    cx0 = (800, 280, 540, 860, 230, 600)[k]
    cy0 = (620, 600, 560, 760, 700, 800)[k]
    col = ((1, 0.82, 0.35), (1, 0.6, 0.8), (1, 1, 1), (0.6, 0.85, 1), (1, 0.6, 0.8), (1, 0.82, 0.35))[k]
    FIRE.append((tf, cx0, cy0, col, [(rng.uniform(0, 6.283), rng.uniform(120, 330)) for _ in range(34)]))


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, k):
    return a + (b - a) * k


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def bar_steps(t):
    return sum(smooth((t - tb) / 0.2) for tb in BARS_T) / 3


def lift(t):
    """0 on the floor, 1 floating; springs up with a small overshoot after the drop."""
    d = (t - T_DROP) / 0.9
    if d <= 0:
        return 0.0
    if d >= 1:
        return 1.0
    return smooth(d) + 0.08 * math.sin(math.pi * d) * (1 - d)


def bar_center(t):
    y = lerp(FLOOR_Y, FLY_Y, lift(t))
    if t > T_DROP + 0.9:
        y += 14 * math.sin((t - T_DROP) * 2.2)
    return 540, y


def tilt(t):
    if t < T_DROP:
        strain = smooth((t - 6.0) / 3.5)
        return 0.05 * (1 - strain * 0.4) + 0.012 * strain * math.sin(t * 38)
    return 0.05 * (1 - smooth((t - T_DROP) / 0.5)) + 0.03 * math.sin((t - T_DROP) * 1.7) * smooth((t - T_DROP - 0.5) / 1)


def orb_pos(t):
    bx, by = bar_center(t)
    px = 790 + 40 * math.sin(min(t, T_DASH) * 1.4)
    py = 560 + 40 * math.sin(min(t, T_DASH) * 1.9)
    if t >= T_DASH:
        u = smooth((t - T_DASH) / (T_DROP - T_DASH))
        return lerp(px, bx, u), lerp(py, by, u)
    return px, py


def note(c, x, y, s, col, a):
    c.save(); c.translate(x, y); c.scale(s, s)
    c.set_source_rgba(*col, a)
    c.save(); c.rotate(-0.4); c.scale(1.3, 1.0); c.arc(0, 0, 11, 0, 2 * math.pi); c.restore(); c.fill()
    c.set_line_width(5); c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.move_to(13, -4); c.line_to(13, -44); c.curve_to(14, -30, 32, -30, 28, -14); c.stroke()
    c.restore()


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    glow = smooth((t - T_DROP) / 1.2)
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *mix3((0.08, 0.07, 0.19), (0.20, 0.09, 0.36), glow))
    g.add_color_stop_rgb(1, *mix3((0.02, 0.03, 0.09), (0.36, 0.13, 0.36), glow))
    c.set_source(g); c.rectangle(0, 0, W, H); c.fill()
    for sx, sy, sz, ph in STARS:
        c.set_source_rgba(1, 1, 1, clamp(0.25 + 0.2 * math.sin(t * 1.5 + ph) + 0.3 * glow))
        c.arc(sx, sy, sz, 0, 2 * math.pi); c.fill()

    bx, by = bar_center(t)
    L = clamp(lift(t))
    ox, oy = orb_pos(t)
    orb_a = smooth((t - T_ORB) / 0.7)
    beat = math.exp(-((t * 2) % 1.0) / 0.18) if t >= T_ORB else 0.0

    # floor shadow, shrinks as the pair rises
    c.save(); c.translate(540, FLOOR_Y + 105); c.scale(1, 0.12)
    sh = cairo.RadialGradient(0, 0, 0, 0, 0, 340)
    sh.add_color_stop_rgba(0, 0, 0, 0, 0.55 * (1 - 0.7 * L)); sh.add_color_stop_rgba(1, 0, 0, 0, 0)
    c.set_source(sh); c.arc(0, 0, 340, 0, 2 * math.pi); c.fill(); c.restore()

    # thread from orb to bar (tension) before the drop
    if T_ORB + 1.5 <= t < T_DROP:
        k = smooth((t - T_ORB - 1.5) / 3.0)
        c.set_source_rgba(1, 0.75, 0.9, 0.35 * k * orb_a); c.set_line_width(4); c.set_dash([6, 14], -t * 40)
        c.move_to(ox, oy); c.line_to(bx + 200, by - 20); c.stroke(); c.set_dash([])

    # barbell
    gold = smooth((t - T_DROP) / 0.5)
    plate = mix3((0.42, 0.44, 0.50), (1.0, 0.78, 0.32), gold)
    plate2 = mix3((0.32, 0.34, 0.40), (0.95, 0.55, 0.45), gold)
    c.save(); c.translate(bx, by); c.rotate(tilt(t))
    if gold > 0:
        gl = cairo.RadialGradient(0, 0, 40, 0, 0, 420)
        gl.add_color_stop_rgba(0, 1, 0.8, 0.4, 0.38 * gold); gl.add_color_stop_rgba(1, 1, 0.8, 0.4, 0)
        c.set_source(gl); c.arc(0, 0, 420, 0, 2 * math.pi); c.fill()
    c.set_source_rgb(*mix3((0.62, 0.64, 0.70), (1, 0.92, 0.7), gold)); c.rectangle(-330, -9, 660, 18); c.fill()
    for sgn in (-1, 1):
        for x0, hh, col in ((190, 150, plate), (238, 110, plate2)):
            c.set_source_rgb(*col)
            r = 12; x = sgn * x0 - 19; y = -hh / 2
            c.new_sub_path()
            c.arc(x + 38 - r, y + r, r, -math.pi / 2, 0); c.arc(x + 38 - r, y + hh - r, r, 0, math.pi / 2)
            c.arc(x + r, y + hh - r, r, math.pi / 2, math.pi); c.arc(x + r, y + r, r, math.pi, 1.5 * math.pi); c.close_path(); c.fill()
        c.set_source_rgb(*mix3((0.55, 0.57, 0.63), (1, 0.95, 0.8), gold)); c.rectangle(sgn * 150 - 8, -22, 16, 44); c.fill()
    c.restore()

    # orb (the treat)
    if orb_a > 0:
        rad = 46 + 8 * beat + (14 * math.exp(-(t - T_DROP) / 0.25) if t >= T_DROP else 0)
        gl = cairo.RadialGradient(ox, oy, 4, ox, oy, rad * 3.2)
        gl.add_color_stop_rgba(0, 1, 0.75, 0.9, 0.55 * orb_a); gl.add_color_stop_rgba(1, 1, 0.5, 0.8, 0)
        c.set_source(gl); c.arc(ox, oy, rad * 3.2, 0, 2 * math.pi); c.fill()
        og = cairo.RadialGradient(ox - 12, oy - 14, 4, ox, oy, rad)
        og.add_color_stop_rgba(0, 1, 0.95, 0.85, orb_a); og.add_color_stop_rgba(1, 1, 0.45, 0.72, orb_a)
        c.set_source(og); c.arc(ox, oy, rad, 0, 2 * math.pi); c.fill()
        note(c, ox - 12, oy + 14, 1.15, (0.35, 0.1, 0.4), orb_a)

    # rising notes after the drop, one per beat
    if t >= T_DROP:
        for k in range(int((t - T_DROP) / 0.5) + 1):
            d = t - (T_DROP + 0.5 * k)
            if 0 <= d < 1.8:
                nx = ox + 70 * math.sin(k * 2.1) + 22 * math.sin(d * 3)
                ny = oy - 70 - 90 * d
                note(c, nx, ny, 0.9, (1, 0.85, 0.55) if k % 2 else (1, 0.65, 0.85), 0.9 * (1 - d / 1.8) ** 2)

    # bar chart
    bxs = (390, 690)
    if t >= 11.5:
        c.set_source_rgba(1, 1, 1, 0.5 * smooth((t - 11.5) / 0.4)); c.set_line_width(6)
        c.move_to(260, BASE_Y); c.line_to(820, BASE_Y); c.stroke()
        grow = smooth((t - 11.7) / 0.4)
        h0 = 200 * grow
        c.set_source_rgb(0.5, 0.52, 0.60); c.rectangle(bxs[0] - 70, BASE_Y - h0, 140, h0); c.fill()
        hb = (200 + 102 * bar_steps(t)) * grow
        c.set_source_rgb(*mix3((1, 0.6, 0.8), (1, 0.82, 0.35), smooth((t - 13.0) / 0.5))); c.rectangle(bxs[1] - 70, BASE_Y - hb, 140, hb); c.fill()
        for tb in BARS_T:
            d = t - tb
            if 0 <= d < 0.5:
                c.set_source_rgba(1, 1, 1, 0.7 * (1 - d / 0.5)); c.set_line_width(5)
                c.arc(bxs[1], BASE_Y - hb, 40 + 120 * d, 0, 2 * math.pi); c.stroke()

    for tf, fx0, fy0, col, parts in FIRE:
        d = t - tf
        if 0 <= d < 1.4:
            for ang, spd in parts:
                r = spd * (1 - math.exp(-d * 3.0))
                c.set_source_rgba(*col, (1 - d / 1.4) ** 1.4)
                c.arc(fx0 + r * math.cos(ang), fy0 + r * math.sin(ang) + 110 * d * d, 6 * (1 - d / 1.8), 0, 2 * math.pi); c.fill()
            if d < 0.2:
                c.set_source_rgba(1, 1, 1, 0.5 * (1 - d / 0.2)); c.arc(fx0, fy0, 70 * d / 0.2, 0, 2 * math.pi); c.fill()
    fl = t - T_DROP
    if 0 <= fl < 0.35:
        c.set_source_rgba(1, 0.95, 0.9, 0.5 * (1 - fl / 0.35) ** 2); c.paint()
        c.set_source_rgba(1, 1, 1, 0.8 * (1 - fl / 0.35)); c.set_line_width(10)
        c.arc(bx, by, 60 + 600 * fl, 0, 2 * math.pi); c.stroke()
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


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 2.9)
    ctext(d, (540, 400), "Dreading it?", font("Bold", 68), CREAM_I, h)
    ctext(d, (540, 485), "Bundle it.", font("Bold", 68), PINK_I, h)
    if t >= T_NUM:
        pops = [math.exp(-(t - tb) / 0.16) for tb in BARS_T if t >= tb]
        pop = max(pops) if pops else 0.0
        ctext(d, (540, 350), f"+{int(round(51 * bar_steps(t)))}%", font("Bold", int(150 + 28 * pop)), GOLD_I, win(t, T_NUM, 20.1, 0.2, 0.1))
        ctext(d, (540, 455), "more gym visits at first", font("Regular", 32), CREAM_I, win(t, 12.3, 20.1, 0.4, 0.1))
        ctext(d, (390, 1225), "gym alone", font("Regular", 28), CREAM_I, win(t, 12.0, 20.1, 0.4, 0.1))
        ctext(d, (690, 1225), "gym + treat", font("Regular", 28), CREAM_I, win(t, 12.0, 20.1, 0.4, 0.1))
    p = win(t, 14.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 1315), "Pair a should", font("Bold", 50), CREAM_I, p)
    ctext(d, (540, 1380), "with a want.", font("Bold", 50), PINK_I, p)
    q = win(t, 15.2, 20.1, 0.6, 0.1)
    ctext(d, (540, 1445), "Milkman, Minson & Volpp, 2014 · early weeks", font("Regular", 26), (225, 220, 235), q)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "bundle_silent.mp4"
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
