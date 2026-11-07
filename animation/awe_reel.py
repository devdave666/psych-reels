"""'Awe expands time' - a cramped, ticking room (hand racing, walls closing) splits open onto an aurora over a mountain lake.
Rudd, Vohs & Aaker (2012, Psychological Science 23(10), 1130-1136): three experiments; people who felt awe (vs. other
emotions such as happiness) felt they had more time available, were less impatient, and were more willing to volunteer
their time. A 2019 attempt (Attention, Perception & Psychophysics) did not find consistent effects on implicit time
perception, so the reel shows no numbers and the caption says so. Text stays inside x 140-940, y 260-1480.
Usage: python awe_reel.py out_silent.mp4 | python awe_reel.py stills t1 t2 ..."""
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
CX, CY, CR = 540.0, 900.0, 235.0         # clock
rng = np.random.default_rng(23)
NST = 230
STARS = []
for i in range(NST):
    STARS.append((rng.uniform(0, W), rng.uniform(0, 1150), rng.uniform(0.8, 2.6), rng.uniform(0, 6.28)))
ORDER = list(rng.permutation(NST))
STAR_T = [0.0] * NST                     # reveal time per star (stars appear one after another = the sky expanding)
for rank, idx in enumerate(ORDER):
    STAR_T[idx] = T_DROP + 0.25 + 4.0 * (rank / NST) ** 0.8
FIRST_STARS = sorted(STAR_T)[:8]
TICKS = [(-0.25 + math.sqrt(0.0625 + 0.18 * k / 4)) / 0.09 for k in range(1, 28)]
SLOW_TICKS = [12.0, 14.0, 16.0, 18.0]


def rev(t):
    if t < T_DROP:
        return 0.25 * t + 0.045 * t * t
    return 7.0 + (t - T_DROP) / 12.0


def mtn(x, base, amp, seed):
    return base - amp * (0.55 + 0.30 * math.sin(x * 0.0062 + seed) + 0.22 * math.sin(x * 0.0171 + 2 * seed)
                         + 0.10 * math.sin(x * 0.043 + 3 * seed))


def person(c, x, y, s, col, lean=0.0, look=0.0):
    c.set_source_rgb(*col)
    c.save(); c.translate(x, y); c.scale(s, s)
    c.move_to(-14, 0); c.line_to(-11, -52 - 8 * lean); c.curve_to(-10, -64, 10, -64, 11, -52 - 8 * lean); c.line_to(14, 0); c.close_path(); c.fill()
    c.arc(3 * look, -78 - 8 * lean - 6 * abs(look), 15, 0, 2 * math.pi); c.fill()
    c.restore()


def clock_face(c, cx, cy, r, t, ring, handcol, alpha=1.0, glow=0.0):
    if glow > 0:
        gr = cairo.RadialGradient(cx, cy, r * 0.8, cx, cy, r * 1.6)
        gr.add_color_stop_rgba(0, *handcol, 0.35 * glow); gr.add_color_stop_rgba(1, *handcol, 0)
        c.set_source(gr); c.arc(cx, cy, r * 1.6, 0, 2 * math.pi); c.fill()
    c.set_line_width(10); c.set_source_rgba(*ring, alpha)
    c.arc(cx, cy, r, 0, 2 * math.pi); c.stroke()
    for k in range(12):
        a = k * math.pi / 6
        c.set_line_width(8 if k % 3 == 0 else 4)
        c.move_to(cx + math.sin(a) * r * 0.86, cy - math.cos(a) * r * 0.86)
        c.line_to(cx + math.sin(a) * r * 0.95, cy - math.cos(a) * r * 0.95); c.stroke()
    a = 2 * math.pi * rev(t)
    c.set_source_rgba(*handcol, alpha); c.set_line_width(9)
    c.move_to(cx - math.sin(a) * r * 0.18, cy + math.cos(a) * r * 0.18)
    c.line_to(cx + math.sin(a) * r * 0.82, cy - math.cos(a) * r * 0.82); c.stroke()
    h = 2 * math.pi * (rev(t) / 60.0 + 0.1)
    c.set_source_rgba(*ring, alpha); c.set_line_width(14)
    c.move_to(cx, cy); c.line_to(cx + math.sin(h) * r * 0.5, cy - math.cos(h) * r * 0.5); c.stroke()
    c.arc(cx, cy, 14, 0, 2 * math.pi); c.set_source_rgba(*handcol, alpha); c.fill()


def scene_a(t):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(s)
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, 0.11, 0.12, 0.16); g.add_color_stop_rgb(1, 0.17, 0.15, 0.17)
    c.set_source(g); c.paint()
    tense = clamp(t / T_DROP)
    gl = cairo.RadialGradient(CX, CY, 50, CX, CY, 800)
    gl.add_color_stop_rgba(0, 0.9, 0.35, 0.2, 0.10 + 0.14 * tense); gl.add_color_stop_rgba(1, 0, 0, 0, 0)
    c.set_source(gl); c.paint()
    clock_face(c, CX, CY, CR, t, (0.72, 0.72, 0.78), (1.0, 0.42, 0.28), 1.0, glow=0.4 + 0.6 * tense)
    ceil = 40 + 17 * t + 4 * math.sin(t * 9) * tense
    c.set_source_rgb(0.04, 0.04, 0.06); c.rectangle(0, 0, W, ceil); c.fill()
    c.rectangle(0, 1560 - 6 * t, W, H); c.fill()
    wl = 30 + 11 * t
    c.rectangle(0, 0, wl, H); c.fill(); c.rectangle(W - wl, 0, wl, H); c.fill()
    person(c, 540 + 2.5 * math.sin(t * 17) * tense, 1560 - 6 * t, 1.25, (0.03, 0.03, 0.05), lean=0.9)
    vg = cairo.RadialGradient(CX, 960, 350, CX, 960, 1200)
    vg.add_color_stop_rgba(0, 0, 0, 0, 0); vg.add_color_stop_rgba(1, 0, 0, 0, 0.55)
    c.set_source(vg); c.paint()
    return s


def aurora(c, t, a):
    for x in range(-10, W + 10, 10):
        bot = 640 + 110 * math.sin(x * 0.0058 + 0.5 + t * 0.35) + 55 * math.sin(x * 0.014 - t * 0.6)
        hgt = 420 + 170 * math.sin(x * 0.009 + 1.3 + t * 0.25)
        gr = cairo.LinearGradient(0, bot - hgt, 0, bot + 40)
        gr.add_color_stop_rgba(0, 0.25, 1.0, 0.65, 0)
        gr.add_color_stop_rgba(0.62, 0.25, 0.95, 0.62, 0.45 * a)
        gr.add_color_stop_rgba(0.92, 0.55, 0.95, 0.85, 0.80 * a)
        gr.add_color_stop_rgba(1.0, 0.65, 0.40, 1.0, 0)
        c.set_source(gr); c.rectangle(x, bot - hgt, 11, hgt + 40); c.fill()


def scene_b(c, t):
    open_k = smooth((t - T_DROP) / 1.5)
    sky = cairo.LinearGradient(0, 0, 0, 1420)
    sky.add_color_stop_rgb(0, 0.015, 0.03, 0.10); sky.add_color_stop_rgb(0.7, 0.03, 0.12, 0.20); sky.add_color_stop_rgb(1, 0.08, 0.24, 0.30)
    c.set_source(sky); c.rectangle(0, 0, W, 1420); c.fill()
    for (sx, sy, sr, sp), st in zip(STARS, STAR_T):
        k = clamp((t - st) / 0.5)
        if k > 0:
            c.set_source_rgba(0.95, 0.97, 1, k * (0.55 + 0.35 * math.sin(t * 1.7 + sp)))
            c.arc(sx, sy, sr * (1 + 0.8 * (1 - k)), 0, 2 * math.pi); c.fill()
    a = open_k * 0.9
    aurora(c, t, a)
    clock_face(c, CX, 840, 200, t, (0.75, 0.9, 0.95), (0.55, 1.0, 0.85), 0.28 * open_k)
    for base, amp, seed, col in ((1250, 260, 0.7, (0.05, 0.13, 0.20)), (1340, 190, 2.9, (0.02, 0.06, 0.11))):
        c.move_to(0, 1430)
        for x in range(0, W + 20, 20):
            c.line_to(x, mtn(x, base, amp, seed))
        c.line_to(W, 1430); c.close_path(); c.set_source_rgb(*col); c.fill()
    lake = cairo.LinearGradient(0, 1420, 0, H)
    lake.add_color_stop_rgb(0, 0.04, 0.14, 0.18); lake.add_color_stop_rgb(1, 0.01, 0.04, 0.08)
    c.set_source(lake); c.rectangle(0, 1420, W, H - 1420); c.fill()
    c.save(); c.rectangle(0, 1420, W, H - 1420); c.clip()
    c.translate(0, 2840); c.scale(1, -1); aurora(c, t + 0.4, a * 0.30); c.restore()
    c.set_source_rgb(0.015, 0.03, 0.05)
    c.move_to(0, 1432); c.curve_to(300, 1380, 760, 1380, W, 1432); c.line_to(W, 1450); c.line_to(0, 1450); c.close_path(); c.fill()
    person(c, 540, 1392, 1.25, (0.01, 0.02, 0.03), lean=0.0, look=-0.6)
    d = t - T_DROP
    if 0 <= d < 2.2:
        r = 1500 * smooth(d / 2.2)
        c.set_line_width(26 * (1 - d / 2.2) + 2); c.set_source_rgba(0.7, 1, 0.9, 0.55 * (1 - d / 2.2))
        c.arc(CX, 1000, r, 0, 2 * math.pi); c.stroke()


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    c.set_source_rgb(0.02, 0.03, 0.06); c.paint()
    if t >= T_DROP - 0.05:
        scene_b(c, t)
    sa = scene_a(t)
    k = smooth((t - T_DROP) / 0.8) if t >= T_DROP else 0.0
    if k < 1.0:
        ox = 560 * k
        if t >= T_DROP:
            gr = cairo.LinearGradient(CX - 120, 0, CX + 120, 0)
            gr.add_color_stop_rgba(0, 1, 1, 0.9, 0); gr.add_color_stop_rgba(0.5, 1, 1, 0.9, 0.9 * (1 - k)); gr.add_color_stop_rgba(1, 1, 1, 0.9, 0)
            c.set_source(gr); c.rectangle(CX - 120, 0, 240, H); c.fill()
        c.save(); c.rectangle(0, 0, W / 2 - ox, H); c.clip(); c.set_source_surface(sa, -ox, 0); c.paint(); c.restore()
        c.save(); c.rectangle(W / 2 + ox, 0, W / 2, H); c.clip(); c.set_source_surface(sa, ox, 0); c.paint(); c.restore()
    f2 = t - T_DROP
    if 0 <= f2 < 0.3:
        c.set_source_rgba(0.85, 1, 0.95, 0.35 * (1 - f2 / 0.3) ** 2); c.paint()
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
        d.text((xy[0] + 2, xy[1] + 3), s, font=f, fill=(0, 0, 0, int(170 * a)), anchor="mm")
        d.text(xy, s, font=f, fill=(*fill, int(255 * a)), anchor="mm")


WHITE = (250, 246, 240)
AMBER = (255, 190, 130)
MINT = (170, 255, 220)


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 3.9)
    ctext(d, (540, 370), "Never enough", font("Bold", 74), AMBER, h)
    ctext(d, (540, 462), "time?", font("Bold", 100), WHITE, h)
    b = win(t, 4.1, 9.8, 0.4, 0.3)
    ctext(d, (540, 340), "Tick. Tick. Tick.", font("Bold", 62), WHITE, b)
    e = win(t, 6.6, 9.8, 0.4, 0.3)
    ctext(d, (540, 430), "So you rush.", font("Regular", 46), AMBER, e)
    a = win(t, 10.3, 14.4, 0.4, 0.4)
    ctext(d, (540, 330), "Feel awe.", font("Bold", 100), MINT, a)
    a2 = win(t, 11.4, 14.4, 0.4, 0.4)
    ctext(d, (540, 430), "Time feels roomier.", font("Bold", 52), WHITE, a2)
    a3 = win(t, 12.4, 14.4, 0.4, 0.4)
    ctext(d, (540, 510), "More patient. More giving.", font("Regular", 38), WHITE, a3)
    p = win(t, 14.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 340), "Find something vast.", font("Bold", 62), WHITE, p)
    ctext(d, (540, 420), "Tonight, look up.", font("Bold", 52), MINT, p)
    q = win(t, 15.2, 20.1, 0.6, 0.1)
    ctext(d, (540, 1440), "Rudd, Vohs & Aaker, 2012 · Psychological Science", font("Regular", 26), WHITE, q)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "awe_silent.mp4"
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
