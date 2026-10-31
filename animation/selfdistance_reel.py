"""'Zoom out' - self-distancing self-talk. A tiny boat inside a storm that is only huge because the camera is close.
1080x1920, 20 s.

Kross et al. (2014, Journal of Personality and Social Psychology 106(2), 304-324): seven studies, total N = 585.  People who
talked to themselves with their own name or non-first-person pronouns (instead of "I") under social stress (a speech, a first
impression) showed less distress and were rated by objective raters as performing better.
Here: t < 10 s close-up of a storm (anxious, first-person); at the drop (t = 10 s) the camera pulls back and the storm is a
small cloud over a calm golden sea.  Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python selfdistance_reel.py out_silent.mp4      render
       python selfdistance_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
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
T_ZOOM = 3.8                                   # length of the pull-back
FLASH = [2.0, 5.0, 7.6]                        # lightning, locked to thunder in the audio
Z0, Z1 = 3.6, 0.85
HOR = 960                                      # world y of the horizon
BX, BY = 540, 1010                             # boat (world)
rng = np.random.default_rng(23)
BLOBS = [(540 + rng.uniform(-190, 190), 795 + rng.uniform(-55, 50), rng.uniform(55, 100)) for _ in range(16)]
RAIN = [(rng.uniform(335, 745), rng.uniform(0, 1), rng.uniform(0.7, 1.3)) for _ in range(90)]
GLINT = [(rng.uniform(-260, 260), rng.uniform(0, 1), rng.uniform(0, 6.28)) for _ in range(34)]


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def zoom(t):
    if t < T_DROP:
        return Z0 + 0.25 * t / T_DROP
    x = clamp((t - T_DROP) / T_ZOOM)
    u = 1 - (1 - x) ** 3
    return math.exp(lerp(math.log(Z0 + 0.25), math.log(Z1), u))


def storm(t):                                  # 1 = raging, falls once the camera is back
    return 1 - 0.8 * smooth((t - T_DROP - 0.5) / 4.0) if t >= T_DROP else 1.0


def wave_y(x, t, base, amp, k, sp, ph):
    return base + amp * math.sin(x * k + t * sp + ph)


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    st = storm(t)
    dawn = smooth((t - T_DROP - 0.3) / 3.0) if t >= T_DROP else 0.0
    Z = zoom(t)
    shake = 3.0 * st * (t < T_DROP)
    c.translate(540 + shake * math.sin(t * 23), 1000 + shake * math.cos(t * 19))
    c.scale(Z, Z)
    c.translate(-BX, -BY)
    # sky
    sky = cairo.LinearGradient(0, -900, 0, HOR)
    sky.add_color_stop_rgb(0, *mix3((0.10, 0.13, 0.20), (0.10, 0.28, 0.45), dawn))
    sky.add_color_stop_rgb(1, *mix3((0.20, 0.24, 0.30), (1.0, 0.78, 0.50), dawn))
    c.set_source(sky); c.rectangle(-3000, -900, 7000, HOR + 900); c.fill()
    # sun and rays
    if dawn > 0:
        sy = HOR + 70 - 95 * smooth((t - T_DROP - 0.3) / 3.5)
        gl = cairo.RadialGradient(BX, sy, 10, BX, sy, 520)
        gl.add_color_stop_rgba(0, 1, 0.92, 0.65, 0.85 * dawn); gl.add_color_stop_rgba(1, 1, 0.7, 0.4, 0)
        c.set_source(gl); c.rectangle(BX - 540, sy - 540, 1080, 560); c.fill()
        c.save(); c.rectangle(-3000, -900, 7000, HOR + 900); c.clip()
        c.set_source_rgba(1, 0.96, 0.78, dawn); c.arc(BX, sy, 78, 0, 2 * math.pi); c.fill()
        for i in range(9):
            a = math.pi * (1.06 + 0.11 * i) + 0.04 * math.sin(t * 0.6 + i)
            c.set_source_rgba(1, 0.9, 0.6, 0.10 * dawn)
            c.move_to(BX, sy); c.line_to(BX + 1800 * math.cos(a - 0.025), sy + 1800 * math.sin(a - 0.025))
            c.line_to(BX + 1800 * math.cos(a + 0.025), sy + 1800 * math.sin(a + 0.025)); c.close_path(); c.fill()
        c.restore()
    # sea
    sea = cairo.LinearGradient(0, HOR, 0, HOR + 700)
    sea.add_color_stop_rgb(0, *mix3((0.10, 0.20, 0.27), (0.95, 0.70, 0.45), dawn * 0.9))
    sea.add_color_stop_rgb(1, *mix3((0.03, 0.09, 0.15), (0.05, 0.38, 0.45), dawn))
    c.set_source(sea); c.rectangle(-3000, HOR, 7000, 3000); c.fill()
    amp = 3 + 12 * st
    for li, (base, col_s, col_c) in enumerate([(HOR + 30, (0.08, 0.19, 0.25), (0.20, 0.55, 0.60)),
                                               (HOR + 70, (0.06, 0.16, 0.22), (0.12, 0.47, 0.53)),
                                               (HOR + 120, (0.04, 0.12, 0.18), (0.07, 0.40, 0.47))]):
        c.set_source_rgba(*mix3(col_s, col_c, dawn), 0.9)
        c.move_to(-3000, 3000)
        for x in range(-1500, 2600, 40):
            c.line_to(x, wave_y(x, t, base, amp * (1 + 0.4 * li), 0.021 + 0.004 * li, 1.9 + 0.5 * li, li * 1.7))
        c.line_to(2600, 3000); c.close_path(); c.fill()
    if dawn > 0:                               # sun glints
        for gx, gp, ph in GLINT:
            gy = HOR + 12 + 330 * gp ** 1.6
            w = 4 + 26 * gp
            c.set_source_rgba(1, 0.95, 0.75, 0.55 * dawn * (0.5 + 0.5 * math.sin(t * 3 + ph)))
            c.rectangle(BX + gx * (0.3 + gp) - w / 2, gy, w, 2.5 + 2 * gp); c.fill()
    # boat
    bob = 5 * st * math.sin(t * 2.6) + 1.5 * math.sin(t * 1.4)
    roll = (0.20 * st + 0.02) * math.sin(t * 2.1)
    c.save(); c.translate(BX, BY + bob); c.rotate(roll)
    c.set_source_rgb(*mix3((0.15, 0.10, 0.10), (0.45, 0.22, 0.14), dawn))
    c.move_to(-34, -4); c.line_to(34, -4); c.line_to(22, 14); c.line_to(-22, 14); c.close_path(); c.fill()
    c.set_source_rgb(*mix3((0.28, 0.30, 0.34), (1.0, 0.96, 0.86), dawn))
    c.move_to(-2, -8); c.line_to(-2, -56); c.line_to(26, -10); c.close_path(); c.fill()
    c.set_source_rgb(*mix3((0.20, 0.22, 0.26), (0.9, 0.80, 0.65), dawn))
    c.move_to(-6, -8); c.line_to(-6, -46); c.line_to(-26, -10); c.close_path(); c.fill()
    c.restore()
    # storm cloud + rain (drifts away and fades once we are out)
    away = smooth((t - 12.5) / 5.0) if t >= 12.5 else 0.0
    cx = -330 * away
    rain_a = (1 - smooth((t - T_DROP - 1.0) / 4.5)) if t >= T_DROP else 1.0
    if rain_a > 0.01:
        cur = cairo.LinearGradient(0, 800, 0, HOR + 25)
        cur.add_color_stop_rgba(0, 0.10, 0.13, 0.20, 0.78 * rain_a); cur.add_color_stop_rgba(1, 0.20, 0.26, 0.33, 0.45 * rain_a)
        c.push_group(); c.set_source(cur); c.rectangle(325 + cx, 800, 430, HOR + 25 - 800); c.fill(); c.pop_group_to_source()
        hm = cairo.LinearGradient(325 + cx, 0, 755 + cx, 0)
        for stp, al in ((0, 0), (0.2, 1), (0.8, 1), (1, 0)):
            hm.add_color_stop_rgba(stp, 0, 0, 0, al)
        c.mask(hm)
        c.set_source_rgba(0.75, 0.84, 0.92, 0.45 * rain_a); c.set_line_width(2.2)
        for rx, rp, rs in RAIN:
            y = 820 + ((rp + t * 1.1 * rs) % 1.0) * (HOR - 810)
            c.move_to(rx + cx, y); c.line_to(rx + cx - 6, y + 26); c.stroke()
    dark = mix3((0.13, 0.16, 0.23), (0.52, 0.56, 0.66), smooth((t - T_DROP - 1.0) / 6.0)) if t >= T_DROP else (0.13, 0.16, 0.23)
    for bx_, by_, br in BLOBS:
        c.set_source_rgba(*dark, 1.0); c.arc(bx_ + cx, by_, br, 0, 2 * math.pi); c.fill()
    for bx_, by_, br in BLOBS[::2]:
        c.set_source_rgba(*mix3(dark, (0.45, 0.50, 0.60), 0.6), 0.6); c.arc(bx_ + cx - 10, by_ - 22, br * 0.7, 0, 2 * math.pi); c.fill()
    c.identity_matrix()
    for ft in FLASH:                           # lightning
        f = t - ft
        if 0 <= f < 0.35:
            k = (1 - f / 0.35) ** 2 * (0.5 if f < 0.08 else 1.0)
            c.set_source_rgba(0.85, 0.92, 1.0, 0.38 * k); c.paint()
    f2 = t - T_DROP
    if 0 <= f2 < 0.3:
        c.set_source_rgba(1, 0.92, 0.72, 0.35 * (1 - f2 / 0.3) ** 2); c.paint()
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
ICE = (175, 205, 235)


def number(t):
    return int(round(585 * smooth((t - T_NUM) / 1.5)))


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 3.5)
    ctext(d, (540, 380), "Stressed before", font("Bold", 62), WHITE, h)
    ctext(d, (540, 462), "something big?", font("Bold", 66), ROSE, h)
    b = win(t, 3.8, 6.7, 0.4, 0.3)
    ctext(d, (540, 380), "Don't ask:", font("Bold", 46), ICE, b)
    ctext(d, (540, 456), "Why am I so nervous?", font("Bold", 50), WHITE, b)
    g = win(t, 6.9, 9.8, 0.4, 0.3)
    ctext(d, (540, 380), "Ask:", font("Bold", 46), ICE, g)
    ctext(d, (540, 456), "Why is Alex nervous?", font("Bold", 50), GOLD, g)
    z = win(t, 10.2, 14.4, 0.3, 0.3)
    ctext(d, (540, 345), "Zoom out.", font("Bold", 68), GOLD, z)
    ctext(d, (540, 415), "The storm gets smaller.", font("Bold", 44), WHITE, z)
    if t >= T_NUM:
        ctext(d, (540, 585), f"{number(t)}", font("Bold", 150), GOLD, win(t, T_NUM, 20.1, 0.2, 0.1))
        ctext(d, (540, 668), "people tested, 7 studies", font("Regular", 30), WHITE, win(t, 11.0, 20.1, 0.4, 0.1))
    p = win(t, 14.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 300), "Talk to yourself", font("Bold", 54), WHITE, p)
    ctext(d, (540, 365), "by name.", font("Bold", 58), ROSE, p)
    q = win(t, 15.2, 20.1, 0.6, 0.1)
    ctext(d, (540, 1440), "Kross et al., 2014 · calmer, better speeches", font("Regular", 27), WHITE, q)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "selfdistance_silent.mp4"
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
