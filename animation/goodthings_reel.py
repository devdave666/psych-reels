"""'Three good things' - a jar that fills with light. Seligman, Steen, Park & Peterson (2005, American Psychologist 60(5),
410-421): 577 adults in an online randomized study; those assigned to write down three things that went well each night
(plus why) for one week were happier and less depressed at follow-ups through 6 months (411 completers analysed).
Later replication (Woodworth et al. 2017) found a placebo did as well, so the caption is hedged.
Text stays inside the phone safe zone (x 140-940, y 260-1480).
Usage: python goodthings_reel.py out_silent.mp4 | python goodthings_reel.py stills t1 t2 ..."""
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
FALL = 1.0
ORBS = [(4.4, 478, 1235), (6.4, 604, 1240), (8.4, 540, 1160)]   # (start time, rest x, rest y); lands at start + FALL
JX, JTOP, JBOT, JW = 540, 900, 1290, 190                       # jar centre x, body top/bottom, half width
rng = np.random.default_rng(7)
FLY = [(T_DROP + rng.uniform(0, 2.2), rng.uniform(4.5, 6.5), rng.uniform(-1, 1), rng.uniform(0, 6.28), rng.uniform(70, 150),
        rng.uniform(1.5, 4)) for _ in range(46)]
STARS = [(rng.uniform(0, W), rng.uniform(0, 800), rng.uniform(0.8, 2.2), rng.uniform(0, 6.28)) for _ in range(40)]


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def lit(t):
    return sum(smooth((t - (o[0] + FALL)) / 0.4) for o in ORBS)       # 0..3 orbs in jar


def orb_pos(i, t):
    t0, rx, ry = ORBS[i]
    k = (t - t0) / FALL
    if k < 0:
        return None
    if k >= 1:
        return rx, ry + 3 * math.sin(t * 2 + i)
    x = lerp(620 - 160 * i + (i - 1) * 50, JX, smooth(k)) if k < 0.85 else lerp(JX, rx, (k - 0.85) / 0.15)
    return x, lerp(480, ry, k * k)


def glow_dot(c, x, y, r, col, a):
    gr = cairo.RadialGradient(x, y, 1, x, y, r)
    gr.add_color_stop_rgba(0, 1, 1, 0.92, a); gr.add_color_stop_rgba(0.25, *col, 0.7 * a); gr.add_color_stop_rgba(1, *col, 0)
    c.set_source(gr); c.arc(x, y, r, 0, 2 * math.pi); c.fill()


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    post = smooth((t - T_DROP) / 1.5) if t >= T_DROP else 0.0
    n = lit(t)
    sky = cairo.LinearGradient(0, 0, 0, H)
    sky.add_color_stop_rgb(0, *mix3((0.02, 0.07, 0.11), (0.05, 0.16, 0.22), post))
    sky.add_color_stop_rgb(0.6, *mix3((0.04, 0.12, 0.17), (0.10, 0.30, 0.34), post))
    sky.add_color_stop_rgb(1, *mix3((0.06, 0.15, 0.19), (0.62, 0.38, 0.22), post))
    c.set_source(sky); c.paint()
    for sx, sy, sr, sp in STARS:
        c.set_source_rgba(0.9, 1, 0.95, 0.2 + 0.2 * math.sin(t * 1.5 + sp)); c.arc(sx, sy, sr, 0, 2 * math.pi); c.fill()
    c.set_source_rgb(*mix3((0.05, 0.09, 0.11), (0.30, 0.20, 0.14), post)); c.rectangle(0, JBOT, W, H - JBOT); c.fill()
    ga = 0.16 * n + 0.45 * post
    g = cairo.RadialGradient(JX, 1100, 30, JX, 1100, 640)
    g.add_color_stop_rgba(0, 1, 0.78, 0.38, ga); g.add_color_stop_rgba(1, 1, 0.6, 0.3, 0)
    c.set_source(g); c.paint()

    def jar_path():
        c.move_to(JX - 120, JTOP - 70); c.line_to(JX - 120, JTOP - 20)
        c.curve_to(JX - 120, JTOP + 10, JX - JW, JTOP + 10, JX - JW, JTOP + 70)
        c.line_to(JX - JW, JBOT - 30); c.curve_to(JX - JW, JBOT, JX - JW + 10, JBOT, JX - JW + 30, JBOT)
        c.line_to(JX + JW - 30, JBOT); c.curve_to(JX + JW - 10, JBOT, JX + JW, JBOT, JX + JW, JBOT - 30)
        c.line_to(JX + JW, JTOP + 70); c.curve_to(JX + JW, JTOP + 10, JX + 120, JTOP + 10, JX + 120, JTOP - 20)
        c.line_to(JX + 120, JTOP - 70)

    jar_path(); c.set_source_rgba(0.75, 0.95, 1.0, 0.07 + 0.10 * n / 3); c.fill()
    for i in range(3):
        p = orb_pos(i, t)
        if p:
            x, y = p
            if t < ORBS[i][0] + FALL:
                for j in range(7):
                    q = orb_pos(i, ORBS[i][0] + max(0.0, (t - ORBS[i][0]) / FALL - 0.025 * j) * FALL)
                    if q:
                        c.set_source_rgba(1, 0.85, 0.5, 0.4 * (1 - j / 7)); c.arc(q[0], q[1], 14 - j, 0, 2 * math.pi); c.fill()
            land = max(0.0, 1 - (t - ORBS[i][0] - FALL) / 0.5) if t >= ORBS[i][0] + FALL else 0
            glow_dot(c, x, y, 55 + 80 * land, (1, 0.75, 0.35), 0.95)
    jar_path(); c.set_source_rgba(0.85, 1, 1, 0.55); c.set_line_width(5); c.stroke()
    c.set_source_rgba(1, 1, 1, 0.22); c.set_line_width(7); c.move_to(JX - JW + 30, JTOP + 100); c.line_to(JX - JW + 30, JBOT - 90); c.stroke()
    if t < T_DROP + 0.8:                                   # lid pops off on the drop
        f = max(0.0, t - T_DROP)
        c.save(); c.translate(JX + 60 * f, JTOP - 88 - 90 * (1 - math.exp(-7 * f)) + 700 * f * f); c.rotate(-0.8 * clamp(f / 0.6))
        c.set_source_rgba(0.72, 0.58, 0.32, 1 - clamp(f / 0.8)); c.rectangle(-135, -20, 270, 40); c.fill(); c.restore()
    for (b, life, drift, ph, spd, size) in FLY:
        if t < b:
            continue
        u = ((t - b) % life) / life
        x = JX + drift * 90 + 160 * drift * u * 3 + 40 * math.sin(ph + t * 2)
        y = 1120 - u * (spd * 7) - 30 * math.sin(ph * 2 + t)
        al = math.sin(u * math.pi) ** 0.7 * (0.6 + 0.4 * math.sin(t * 6 + ph))
        glow_dot(c, x, y, 9 + size * 3.5, (1, 0.8, 0.4), al)
    f2 = t - T_DROP
    if 0 <= f2 < 0.3:
        c.set_source_rgba(1, 0.92, 0.72, 0.4 * (1 - f2 / 0.3) ** 2); c.paint()
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
GOLD = (255, 220, 130)
TEAL = (150, 225, 215)


def number(t):
    return max(1, int(round(6 * smooth((t - T_NUM) / 1.2))))


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 3.9)
    ctext(d, (540, 380), "Rough day?", font("Bold", 70), GOLD, h)
    ctext(d, (540, 466), "Try this tonight.", font("Bold", 56), WHITE, h)
    b = win(t, 4.1, 9.8, 0.4, 0.3)
    ctext(d, (540, 330), "Write 3 good things", font("Bold", 58), WHITE, b)
    ctext(d, (540, 400), "that went well today.", font("Bold", 46), TEAL, b)
    e = win(t, 7.0, 9.8, 0.4, 0.3)
    ctext(d, (540, 480), "And why they happened.", font("Regular", 40), GOLD, e)
    if t >= T_NUM:
        ctext(d, (540, 470), f"{number(t)} month{'s' if number(t) > 1 else ''}", font("Bold", 150), GOLD, win(t, T_NUM, 14.4, 0.2, 0.4))
        ctext(d, (540, 590), "later: still happier", font("Bold", 52), WHITE, win(t, 11.2, 14.4, 0.4, 0.4))
        ctext(d, (540, 655), "and less low", font("Regular", 40), TEAL, win(t, 11.6, 14.4, 0.4, 0.4))
    p = win(t, 14.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 340), "One week of this.", font("Bold", 56), WHITE, p)
    ctext(d, (540, 415), "Start tonight.", font("Bold", 62), GOLD, p)
    q = win(t, 15.2, 20.1, 0.6, 0.1)
    ctext(d, (540, 1440), "Seligman et al., 2005 · online study", font("Regular", 27), WHITE, q)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "goodthings_silent.mp4"
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
