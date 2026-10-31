"""'Cut the sandbags' - mental contrasting (WOOP). A hot-air balloon dreams of the sky, then the sandbags (obstacles) are named,
then cut loose one by one at the drop. 1080x1920, 20 s.

Duckworth, Grant, Loew, Oettingen & Gollwitzer (2011, Educational Psychology 31(1), 17-26): 66 second-year high-school students
preparing for the PSAT did a 30-minute written mental contrasting + implementation intentions exercise (picture the wish, name the
obstacle, plan an if-then) or a placebo writing task; the exercise group completed more than 60% more practice questions.
Small sample; background: Oettingen & Mayer (2002) found purely positive fantasies predicted less effort.
Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python mental_contrasting_reel.py out_silent.mp4      render
       python mental_contrasting_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
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
SNAP = [10.0, 10.55, 11.1]                     # ropes cut, locked to the audio
T_BAG = [6.9, 7.15, 7.4]                       # bags tied on
BAGX = [-165, 0, 165]
LABELS = ["fear", "phone", "tired"]
rng = np.random.default_rng(41)
STARS = [(rng.uniform(0, 1080), rng.uniform(0, 1900), rng.uniform(1, 3.2), rng.uniform(0, 6.28)) for _ in range(120)]
CLOUDS = [(rng.uniform(-100, 1100), rng.uniform(0, 1), rng.uniform(120, 260)) for _ in range(7)]


def sink(t):
    return 75 * smooth((t - 6.9) / 1.3)


def released(t):
    return sum(smooth((t - s) / 0.8) for s in SNAP) / 3


def balloon_cy(t):
    return 1000 + sink(t) * (1 - released(t)) - 90 * released(t) + 10 * math.sin(t * 1.3)


def alt(t):
    return 1500 * smooth((t - T_DROP) / 6.5) if t > T_DROP else 0.0


def bag(i, t):
    """screen centre (x, y) of bag i, rope top, alpha, attached"""
    cy = balloon_cy(t)
    bx0 = 540 + 6 * math.sin(t * 1.1)
    top = (bx0 + BAGX[i] * 0.35, cy + 195)
    L = 150 * smooth((t - T_BAG[i]) / 0.5)
    sw = 14 * math.sin(t * 1.7 + i) if t < SNAP[i] else 0
    if t < SNAP[i]:
        return (top[0] + BAGX[i] * 0.45 + sw, top[1] + L + 28), top, 1.0, True
    dt = t - SNAP[i]
    y = top[1] + 150 + 28 + 900 * dt * dt
    return (top[0] + BAGX[i] * 0.45 + 40 * dt * (i - 1), y), top, clamp(1 - dt / 1.1), False


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    dawn = smooth((t - T_DROP - 0.5) / 5.0) if t >= T_DROP else 0.0
    A = alt(t)
    sky = cairo.LinearGradient(0, 0, 0, H)
    sky.add_color_stop_rgb(0, *mix3((0.05, 0.06, 0.18), (0.16, 0.30, 0.58), dawn))
    sky.add_color_stop_rgb(0.6, *mix3((0.18, 0.12, 0.32), (0.80, 0.52, 0.62), dawn))
    sky.add_color_stop_rgb(1, *mix3((0.40, 0.20, 0.40), (1.0, 0.72, 0.50), dawn))
    c.set_source(sky); c.paint()
    for sx, sy, sr, ph in STARS:                                  # stars drift down as we climb
        y = (sy + A * 0.25) % 1900
        a = (0.5 + 0.5 * math.sin(t * 2 + ph)) * (1 - dawn) * 0.9
        c.set_source_rgba(1, 0.97, 0.85, a); c.arc(sx, y, sr, 0, 6.3); c.fill()
    for cx0, cp, cr in CLOUDS:                                    # clouds only appear while climbing
        if A > 0:
            y = -250 + ((cp * 2400 + A * 1.2 - 200) % 2600)
            x = (cx0 + t * 8) % 1400 - 150
            c.set_source_rgba(1, 0.88, 0.85, 0.30 * smooth(A / 300))
            for k in range(3):
                c.arc(x + k * cr * 0.55, y + (k % 2) * 15, cr * 0.42, 0, 6.3); c.fill()
    gy = 1600 + A * 1.0                                           # hills at the bottom
    c.set_source_rgb(*mix3((0.06, 0.05, 0.12), (0.20, 0.14, 0.26), dawn))
    c.move_to(-10, H + 400)
    for x in range(-10, 1100, 30):
        c.line_to(x, gy + 40 * math.sin(x * 0.006) + 25 * math.sin(x * 0.017 + 1))
    c.line_to(1100, H + 400); c.close_path(); c.fill()
    # ghost balloon: the dream (3.8-6.9)
    g = clamp((t - 3.6) / 0.8) * clamp((7.2 - t) / 0.6)
    if g > 0:
        gx, gyy = 540 + 15 * math.sin(t), 620 - 25 * smooth((t - 3.8) / 3)
        gl = cairo.RadialGradient(gx, gyy, 10, gx, gyy, 230)
        gl.add_color_stop_rgba(0, 1, 0.88, 0.5, 0.55 * g); gl.add_color_stop_rgba(1, 1, 0.7, 0.4, 0)
        c.set_source(gl); c.arc(gx, gyy, 230, 0, 6.3); c.fill()
        c.set_source_rgba(1, 0.86, 0.45, 0.9 * g); c.arc(gx, gyy, 78, 0, 6.3); c.fill()
        c.move_to(gx - 20, gyy + 70); c.line_to(gx + 20, gyy + 70); c.line_to(gx + 12, gyy + 100); c.line_to(gx - 12, gyy + 100)
        c.close_path(); c.fill()
        for k in range(8):
            a = t * 1.4 + k * 0.8
            c.set_source_rgba(1, 0.95, 0.7, 0.8 * g * (0.5 + 0.5 * math.sin(t * 5 + k)))
            c.arc(gx + 135 * math.cos(a), gyy + 120 * math.sin(a), 3.5, 0, 6.3); c.fill()
    # real balloon
    cy = balloon_cy(t)
    bx = 540 + 6 * math.sin(t * 1.1)
    tilt = 0.03 * math.sin(t * 1.2)
    c.save(); c.translate(bx, cy); c.rotate(tilt)
    R = 150
    env = cairo.RadialGradient(-40, -50, 20, 0, 0, R * 1.2)
    env.add_color_stop_rgb(0, *mix3((0.98, 0.52, 0.45), (1.0, 0.70, 0.45), dawn))
    env.add_color_stop_rgb(1, *mix3((0.70, 0.22, 0.38), (0.88, 0.38, 0.40), dawn))
    c.set_source(env)
    c.move_to(0, R * 1.05)
    c.curve_to(-R * 1.45, R * 0.05, -R * 0.95, -R * 1.15, 0, -R * 1.15)
    c.curve_to(R * 0.95, -R * 1.15, R * 1.45, R * 0.05, 0, R * 1.05)
    c.fill()
    c.set_source_rgba(1, 0.92, 0.7, 0.55); c.set_line_width(14)       # centre stripe
    c.move_to(0, R * 1.05); c.curve_to(-R * 0.55, -R * 0.1, -R * 0.4, -R * 0.9, 0, -R * 1.15)
    c.curve_to(R * 0.4, -R * 0.9, R * 0.55, -R * 0.1, 0, R * 1.05); c.stroke()
    c.set_source_rgba(0.2, 0.1, 0.15, 0.7); c.set_line_width(3)
    for sx in (-45, 45):                                           # ropes to basket
        c.move_to(sx * 1.6, R * 0.8); c.line_to(sx * 0.5, 170); c.stroke()
    c.set_source_rgb(0.42, 0.26, 0.17)
    c.rectangle(-32, 170, 64, 42); c.fill()
    c.set_source_rgb(0.30, 0.18, 0.12); c.rectangle(-32, 170, 64, 8); c.fill()
    c.restore()
    for i in range(3):
        if t < T_BAG[i]:
            continue
        (px, py), top, al, att = bag(i, t)
        if att:
            c.set_source_rgba(0.9, 0.85, 0.75, 0.9); c.set_line_width(3)
            c.move_to(top[0], top[1]); c.line_to(px, py - 26); c.stroke()
        c.set_source_rgba(0.55, 0.42, 0.30, al)
        c.move_to(px - 34, py - 24); c.curve_to(px - 60, py + 10, px - 36, py + 38, px, py + 38)
        c.curve_to(px + 36, py + 38, px + 60, py + 10, px + 34, py - 24); c.close_path(); c.fill()
        c.set_source_rgba(0.38, 0.28, 0.20, al); c.rectangle(px - 28, py - 32, 56, 12); c.fill()
    for k, s in enumerate(SNAP):                                   # little snap sparks
        f = t - s
        if 0 <= f < 0.4:
            top = bag(k, s)[1]
            for j in range(8):
                a = j * 0.785
                c.set_source_rgba(1, 0.92, 0.6, 1 - f / 0.4)
                c.arc(top[0] + 140 * f * math.cos(a), top[1] + 150 + 140 * f * math.sin(a), 4, 0, 6.3); c.fill()
    f2 = t - T_DROP
    if 0 <= f2 < 0.3:
        c.set_source_rgba(1, 0.92, 0.72, 0.30 * (1 - f2 / 0.3) ** 2); c.paint()
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
ROSE = (255, 170, 160)
GOLD = (255, 220, 130)
ICE = (190, 205, 240)


def number(t):
    return int(round(60 * smooth((t - T_NUM) / 1.5)))


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 3.5)
    ctext(d, (540, 380), "Only picturing", font("Bold", 62), WHITE, h)
    ctext(d, (540, 462), "your success?", font("Bold", 66), ROSE, h)
    b = win(t, 3.8, 6.7, 0.4, 0.3)
    ctext(d, (540, 380), "1.  See the win", font("Bold", 58), GOLD, b)
    g = win(t, 6.9, 9.8, 0.4, 0.3)
    ctext(d, (540, 380), "2.  Name what", font("Bold", 56), ICE, g)
    ctext(d, (540, 452), "holds you back", font("Bold", 56), WHITE, g)
    for i in range(3):
        if T_BAG[i] + 0.5 < t < SNAP[i]:
            (px, py), _, _, _ = bag(i, t)
            ctext(d, (px, py + 4), LABELS[i], font("Bold", 24), WHITE, win(t, T_BAG[i] + 0.5, SNAP[i], 0.3, 0.05))
    z = win(t, 10.2, 14.4, 0.3, 0.3)
    ctext(d, (540, 345), "3.  Plan past it.", font("Bold", 62), GOLD, z)
    ctext(d, (540, 415), "If it hits, then I will...", font("Regular", 38), WHITE, z)
    if t >= T_NUM:
        ctext(d, (540, 585), f"+{number(t)}%", font("Bold", 150), GOLD, win(t, T_NUM, 20.1, 0.2, 0.1))
        ctext(d, (540, 668), "more practice done · 66 students", font("Regular", 30), WHITE, win(t, 11.0, 20.1, 0.4, 0.1))
    p = win(t, 14.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 300), "Dream it. Name it.", font("Bold", 54), WHITE, p)
    ctext(d, (540, 365), "Then rise.", font("Bold", 58), GOLD, p)
    q = win(t, 15.2, 20.1, 0.6, 0.1)
    ctext(d, (540, 1440), "Duckworth et al., 2011 · small study", font("Regular", 27), WHITE, q)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "mental_contrasting_silent.mp4"
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
