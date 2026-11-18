"""Most worries never happen - a storm sky of worry clouds that clears. 1080x1920, 20 s.

LaFreniere & Newman (2020, Behavior Therapy, "Exposing worry's deceit"): 29 people with generalized anxiety disorder
logged their worries at random prompts for 10 days, then about 20 days later rated whether each one had come true.
91.4% of the worry predictions did not come true; the most common per-person rate of untrue worries was 100%.
Here ten dark rain clouds hang over a hillside.  Nine of them break apart one by one (sm.T_CLEAR, 4.2 - 8.8 s), each
letting a shaft of light through, which is the "about 9 in 10" picture.  At the drop (10.0 s) the sun breaks out, the
sky turns to dawn, the last cloud goes pale and the big number lands.  Only the reported 91% is shown on screen.
Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python worry_reel.py out_silent.mp4      render
       python worry_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
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

CREAM = (246, 241, 230)
GOLD = (255, 204, 96)
T_FLASH = 0.25                                   # lightning on the hook
T_DROP = 10.0
# ten clouds: (x, y, scale).  Index 9 is the one that stays.
CLOUDS = [(250, 730, 1.0), (530, 700, 1.1), (810, 740, 0.95), (170, 910, 0.9), (410, 890, 1.05),
          (670, 905, 1.0), (910, 925, 0.85), (290, 1085, 0.95), (565, 1070, 1.1), (830, 1100, 0.9)]
ORDER = [4, 0, 7, 2, 5, 3, 8, 1, 6]              # which cloud clears at each T_CLEAR
T_CLEAR = [4.2, 4.9, 5.5, 6.1, 6.7, 7.3, 7.8, 8.3, 8.8]
CLEAR_AT = {ci: tc for ci, tc in zip(ORDER, T_CLEAR)}
DISS = 0.9                                       # seconds a cloud takes to break apart
PUFFS = [(-75, 22, 52), (-30, -14, 68), (32, -26, 62), (82, 14, 50), (2, 30, 62), (-110, 40, 36), (115, 40, 34)]
SUN = (540, 960)

rng = np.random.default_rng(41)
RAIN = [(rng.uniform(-90, 90), rng.uniform(0, 1), rng.uniform(0.7, 1.3)) for _ in range(14)]
PUFF_DIR = [(rng.uniform(-1, 1), rng.uniform(-1, 0.3)) for _ in PUFFS]
MOTES = [(rng.uniform(140, 940), rng.uniform(300, 1450), rng.uniform(2, 5), rng.uniform(0, 6.28)) for _ in range(60)]


def cleared(t):
    """Fraction of the nine clouds that have cleared (smooth)."""
    return sum(smooth((t - tc) / DISS) for tc in T_CLEAR) / 9.0


def cloud(c, x, y, s, dark, u, t, k):
    """Draw one cloud. dark 0..1 (storm grey -> pale), u 0..1 = how far it has broken apart."""
    if u >= 1:
        return
    a = (1 - u) ** 1.4
    bob = 6 * math.sin(t * 0.9 + k * 1.7)
    for j, (dx, dy, r) in enumerate(PUFFS):
        ex, ey = PUFF_DIR[j]
        px = x + (dx + ex * 150 * u) * s + 10 * math.sin(t * 0.5 + k)
        py = y + (dy + ey * 110 * u) * s + bob
        rr = r * s * (1 + 0.5 * u)
        g = cairo.RadialGradient(px - rr * 0.3, py - rr * 0.45, rr * 0.1, px, py, rr)
        top = (lerp(0.36, 0.97, dark), lerp(0.39, 0.93, dark), lerp(0.46, 0.92, dark))
        bot = (lerp(0.14, 0.88, dark), lerp(0.15, 0.74, dark), lerp(0.20, 0.72, dark))
        g.add_color_stop_rgba(0, *top, a)
        g.add_color_stop_rgba(1, *bot, a)
        c.set_source(g)
        c.arc(px, py, rr, 0, 2 * math.pi); c.fill()


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    cl = cleared(t)
    dawn = smooth((t - T_DROP) / 0.8)
    pre = 0.35 * cl * (1 - dawn)                       # sky lightens a little as clouds clear
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, lerp(0.05 + 0.04 * pre, 0.12, dawn), lerp(0.06 + 0.06 * pre, 0.22, dawn), lerp(0.10 + 0.10 * pre, 0.42, dawn))
    g.add_color_stop_rgb(0.55, lerp(0.10 + 0.10 * pre, 0.55, dawn), lerp(0.11 + 0.09 * pre, 0.42, dawn), lerp(0.16 + 0.08 * pre, 0.50, dawn))
    g.add_color_stop_rgb(1, lerp(0.13 + 0.25 * pre, 1.0, dawn), lerp(0.13 + 0.15 * pre, 0.70, dawn), lerp(0.18 + 0.05 * pre, 0.42, dawn))
    c.set_source(g); c.rectangle(0, 0, W, H); c.fill()

    # sun behind the clouds
    sb = 0.12 + 0.45 * cl + 0.6 * dawn
    rg = cairo.RadialGradient(*SUN, 30, *SUN, 420 + 380 * dawn)
    rg.add_color_stop_rgba(0, 1, 0.86, 0.5, min(1, 0.55 * sb))
    rg.add_color_stop_rgba(1, 1, 0.6, 0.3, 0)
    c.set_source(rg); c.paint()
    if dawn > 0:                                        # slowly turning rays
        c.save(); c.translate(*SUN); c.rotate(t * 0.08)
        for i in range(14):
            ang = i * 2 * math.pi / 14
            c.move_to(0, 0)
            c.arc(0, 0, 1300, ang - 0.06, ang + 0.06)
            c.close_path()
            c.set_source_rgba(1, 0.9, 0.6, 0.07 * dawn); c.fill()
        c.restore()
    c.set_source_rgba(1, 0.93, 0.7, min(1, 0.25 + 0.75 * dawn) * min(1, sb))
    c.arc(*SUN, 105 + 15 * dawn, 0, 2 * math.pi); c.fill()

    # light shafts where clouds broke
    for ci, tc in CLEAR_AT.items():
        d = t - tc
        if d > 0:
            x, y, s = CLOUDS[ci]
            a = 0.22 * clamp(d / 0.3) * (1 - 0.6 * dawn) * (0.75 + 0.25 * math.sin(t * 2 + ci))
            lg = cairo.LinearGradient(0, y - 120, 0, 1650)
            lg.add_color_stop_rgba(0, 1, 0.9, 0.6, a)
            lg.add_color_stop_rgba(1, 1, 0.8, 0.5, 0)
            c.set_source(lg)
            c.move_to(x - 40 * s, y - 60); c.line_to(x + 40 * s, y - 60)
            c.line_to(x + 140 * s, 1650); c.line_to(x - 140 * s, 1650); c.close_path(); c.fill()

    # rain under dark clouds
    c.set_line_width(3); c.set_line_cap(cairo.LINE_CAP_ROUND)
    for k, (x, y, s) in enumerate(CLOUDS):
        tc = CLEAR_AT.get(k, T_DROP)
        ra = (1 - clamp((t - tc) / 0.4)) * clamp(t / 0.6)
        if ra <= 0:
            continue
        for j, (dx, ph, sp) in enumerate(RAIN):
            u = (ph + t * 1.6 * sp + k * 0.13) % 1.0
            ry = y + 50 * s + u * 520
            rx = x + dx * s - u * 40
            c.set_source_rgba(0.6, 0.7, 0.85, 0.35 * ra * (1 - u))
            c.move_to(rx, ry); c.line_to(rx - 6, ry + 34); c.stroke()

    # clouds
    for k, (x, y, s) in enumerate(CLOUDS):
        if k in CLEAR_AT:
            u = clamp((t - CLEAR_AT[k]) / DISS)
            cloud(c, x, y, s, 0.0, u, t, k)
        else:                                           # the last worry: goes pale and small at the drop
            cloud(c, x, y, s * (1 - 0.35 * dawn), dawn, 0.0, t, k)

    # hills
    for hy, amp, col0, col1, ph in ((1560, 60, (0.08, 0.09, 0.12), (0.36, 0.30, 0.30), 0.0),
                                    (1660, 45, (0.05, 0.06, 0.08), (0.22, 0.18, 0.22), 2.0)):
        c.move_to(0, H)
        for i in range(0, 37):
            x = W * i / 36
            c.line_to(x, hy - amp * math.sin(x / 260 + ph) - 0.5 * amp * math.sin(x / 110 + ph * 2))
        c.line_to(W, H); c.close_path()
        c.set_source_rgb(*(lerp(a, b, dawn) for a, b in zip(col0, col1))); c.fill()

    # floating light motes after the drop
    if dawn > 0:
        for mx, my, r, ph in MOTES:
            yy = my - (t - T_DROP) * 30 * (0.5 + r / 5)
            c.set_source_rgba(1, 0.92, 0.7, 0.4 * dawn * (0.5 + 0.5 * math.sin(t * 2 + ph)))
            c.arc(mx + 10 * math.sin(t + ph), yy, r, 0, 2 * math.pi); c.fill()

    # lightning flash on the hook, burst at the drop
    d = t - T_FLASH
    if 0 <= d < 0.5:
        c.set_source_rgba(0.85, 0.9, 1, 0.5 * math.exp(-d / 0.08) + 0.25 * math.exp(-max(0, d - 0.15) / 0.06) * (d > 0.15))
        c.paint()
    d = t - T_DROP
    if 0 <= d < 0.45:
        c.set_source_rgba(1, 0.92, 0.7, 0.4 * (1 - d / 0.45) ** 2); c.paint()
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
    h = win(t, 0.25, 3.4, 0.25)
    ctext(d, (540, 350), "Most of your worries", font("Bold", 66), CREAM, h)
    ctext(d, (540, 465), "never happen.", font("Bold", 84), GOLD, h)
    a = win(t, 3.6, 6.6)
    ctext(d, (540, 360), "Worriers wrote down", font("Bold", 52), CREAM, a)
    ctext(d, (540, 445), "every worry for 10 days.", font("Bold", 52), CREAM, a)
    a = win(t, 6.8, 9.6)
    ctext(d, (540, 360), "Then they checked:", font("Bold", 52), CREAM, a)
    ctext(d, (540, 445), "did it come true?", font("Bold", 58), GOLD, a)
    a = win(t, T_DROP, 14.2, 0.2, 0.4)
    if a > 0:
        pop = 1 + 0.12 * math.exp(-(t - T_DROP) / 0.18)
        ctext(d, (540, 390), "91%", font("Bold", int(180 * pop)), GOLD, a)
        ctext(d, (540, 530), "never happened", font("Bold", 56), CREAM, a)
    p = win(t, 14.6, 20.1, 0.5, 0.1)
    ctext(d, (540, 350), "A worry is not", font("Bold", 60), CREAM, p)
    ctext(d, (540, 440), "a forecast.", font("Bold", 60), CREAM, p)
    ctext(d, (540, 550), "Go do the thing.", font("Bold", 68), GOLD, p)
    ci = win(t, 15.2, 20.1, 0.6, 0.1)
    if ci > 0.01:                                       # dark pill so the small citation reads on the bright sky
        d.rounded_rectangle((235, 1386, 845, 1474), radius=24, fill=(35, 22, 32, int(120 * ci)))
    ctext(d, (540, 1412), "LaFreniere & Newman, 2020 · 29 people", font("Regular", 27), (238, 228, 222), ci)
    ctext(d, (540, 1450), "with anxiety disorder, a small study", font("Regular", 27), (238, 228, 222), ci)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "worry_silent.mp4"
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
