"""'Thank-you letter' - a paper plane carries a thank-you to a dark window; it lights up, then the whole street glows.
Kumar & Epley (2018, Psychological Science 29(9), 1423-1435): people who wrote gratitude letters overestimated how
awkward recipients would feel and underestimated how positive/happy they would be. Sources conflict on experiment
count and give no ratings, so the reel shows no numbers. Text stays inside the phone safe zone (x 140-940, y 260-1480).
Usage: python thanks_reel.py out_silent.mp4 | python thanks_reel.py stills t1 t2 ..."""
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
T_LAUNCH = 7.9
PX0, PY0 = 250.0, 1190.0                 # plane waiting spot
TX, TY = 770.0, 875.0                    # target window centre
rng = np.random.default_rng(11)
STARS = [(rng.uniform(0, W), rng.uniform(0, 650), rng.uniform(0.8, 2.2), rng.uniform(0, 6.28)) for _ in range(45)]
BUILD = [(60, 760, 330, 1380), (430, 700, 930, 1380), (960, 900, 1120, 1380)]   # x0, top, x1, bottom
WINS = []                                # (x, y, lit_time or None)
for bi, (x0, top, x1, bot) in enumerate(BUILD):
    cols = max(1, int((x1 - x0 - 40) // 90))
    rows = int((bot - top - 60) // 85)
    for r in range(rows):
        for cc in range(cols):
            x = x0 + 70 + 90 * cc if bi == 1 else x0 + 55 + 90 * cc
            y = top + 90 + 85 * r
            if bi == 1 and cc == 3 and r == 1:
                continue
            d = math.hypot(x - TX, y - TY)
            on = rng.random() < 0.72
            WINS.append((x, y, T_DROP + 0.3 + d / 330 if on else None))


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def plane_pos(t):
    if t < T_LAUNCH:
        return PX0 + 12 * math.sin(t * 1.3), PY0 + 14 * math.sin(t * 2.1), -0.35 + 0.08 * math.sin(t * 2.1), 1.0
    k = clamp((t - T_LAUNCH) / (T_DROP - T_LAUNCH))
    e = smooth(k)
    x = (1 - e) ** 2 * PX0 + 2 * (1 - e) * e * 280 + e * e * TX
    y = (1 - e) ** 2 * PY0 + 2 * (1 - e) * e * 560 + e * e * TY
    dx = 2 * (1 - e) * (280 - PX0) + 2 * e * (TX - 280)
    dy = 2 * (1 - e) * (560 - PY0) + 2 * e * (TY - 560)
    return x, y, math.atan2(dy, dx), 1.0 - 0.55 * k


def glow_dot(c, x, y, r, col, a):
    gr = cairo.RadialGradient(x, y, 1, x, y, r)
    gr.add_color_stop_rgba(0, 1, 1, 0.92, a); gr.add_color_stop_rgba(0.25, *col, 0.7 * a); gr.add_color_stop_rgba(1, *col, 0)
    c.set_source(gr); c.arc(x, y, r, 0, 2 * math.pi); c.fill()


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    post = smooth((t - T_DROP) / 2.5) if t >= T_DROP else 0.0
    sky = cairo.LinearGradient(0, 0, 0, H)
    sky.add_color_stop_rgb(0, *mix3((0.05, 0.04, 0.14), (0.16, 0.10, 0.34), post))
    sky.add_color_stop_rgb(0.55, *mix3((0.09, 0.07, 0.22), (0.55, 0.22, 0.45), post))
    sky.add_color_stop_rgb(1, *mix3((0.13, 0.09, 0.27), (0.95, 0.52, 0.34), post))
    c.set_source(sky); c.paint()
    for sx, sy, sr, sp in STARS:
        c.set_source_rgba(0.95, 0.95, 1, (0.2 + 0.2 * math.sin(t * 1.5 + sp)) * (1 - 0.6 * post))
        c.arc(sx, sy, sr, 0, 2 * math.pi); c.fill()
    for (x0, top, x1, bot) in BUILD:
        c.set_source_rgb(*mix3((0.05, 0.04, 0.11), (0.17, 0.09, 0.20), post)); c.rectangle(x0, top, x1 - x0, bot - top); c.fill()
    c.set_source_rgb(*mix3((0.03, 0.025, 0.07), (0.10, 0.05, 0.12), post)); c.rectangle(0, 1380, W, H - 1380); c.fill()
    for (x, y, lt) in WINS:
        k = smooth((t - lt) / 0.5) if lt is not None else 0.0
        if k > 0:
            glow_dot(c, x, y, 70 * k + 20, (1, 0.7, 0.3), 0.35 * k)
            c.set_source_rgba(1, 0.82, 0.45, 0.35 + 0.65 * k)
        else:
            c.set_source_rgba(0.14, 0.12, 0.28, 1)
        c.rectangle(x - 24, y - 30, 48, 60); c.fill()
    k = smooth((t - T_DROP) / 0.4) if t >= T_DROP else 0.0                      # target window
    if k > 0:
        glow_dot(c, TX, TY, 420 * k * (1.0 - 0.3 * clamp((t - T_DROP) / 1.5)), (1, 0.72, 0.3), 0.9)
    c.set_source_rgb(*mix3((0.16, 0.14, 0.30), (1.0, 0.86, 0.50), k)); c.rectangle(TX - 30, TY - 38, 60, 76); c.fill()
    if k > 0.3:                                                                  # someone smiling at the window
        c.set_source_rgba(0.35, 0.18, 0.12, clamp((t - T_DROP - 0.3) / 0.5))
        c.arc(TX, TY - 6, 11, 0, 2 * math.pi); c.fill()
        c.arc(TX, TY + 34, 22, math.pi, 2 * math.pi); c.fill()
    if t < T_DROP + 0.05:                                                        # paper plane + trail
        if t >= T_LAUNCH:
            for j in range(10):
                q = plane_pos(max(T_LAUNCH, t - 0.045 * j))
                glow_dot(c, q[0], q[1], 22 - 1.6 * j, (1, 0.8, 0.5), 0.45 * (1 - j / 10))
        x, y, ang, sc = plane_pos(t)
        c.save(); c.translate(x, y); c.rotate(ang); c.scale(sc, sc)
        c.move_to(60, 0); c.line_to(-50, -34); c.line_to(-26, 0); c.close_path(); c.set_source_rgb(0.97, 0.95, 0.92); c.fill()
        c.move_to(60, 0); c.line_to(-50, 34); c.line_to(-26, 0); c.close_path(); c.set_source_rgb(0.76, 0.72, 0.80); c.fill()
        c.restore()
    f2 = t - T_DROP
    if 0 <= f2 < 0.3:
        c.set_source_rgba(1, 0.9, 0.7, 0.4 * (1 - f2 / 0.3) ** 2); c.paint()
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
LILAC = (205, 190, 245)


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 3.9)
    ctext(d, (540, 380), "Someone helped you.", font("Bold", 64), GOLD, h)
    ctext(d, (540, 466), "Did you tell them?", font("Bold", 56), WHITE, h)
    b = win(t, 4.1, 9.8, 0.4, 0.3)
    ctext(d, (540, 330), "You think it'll be", font("Bold", 52), WHITE, b)
    ctext(d, (540, 410), "awkward.", font("Bold", 84), LILAC, b)
    e = win(t, 6.6, 9.8, 0.4, 0.3)
    ctext(d, (540, 495), "So you don't send it.", font("Regular", 40), WHITE, e)
    a = win(t, 10.2, 14.4, 0.4, 0.4)
    ctext(d, (540, 330), "They feel", font("Bold", 56), WHITE, a)
    ctext(d, (540, 420), "happy.", font("Bold", 110), GOLD, a)
    a2 = win(t, 11.4, 14.4, 0.4, 0.4)
    ctext(d, (540, 520), "Warmer than you'd guess.", font("Regular", 42), LILAC, a2)
    p = win(t, 14.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 340), "Send the thank-you.", font("Bold", 60), WHITE, p)
    ctext(d, (540, 415), "Two minutes. Tonight.", font("Bold", 52), GOLD, p)
    q = win(t, 15.2, 20.1, 0.6, 0.1)
    ctext(d, (540, 1440), "Kumar & Epley, 2018 · letter-writing studies", font("Regular", 27), WHITE, q)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "thanks_silent.mp4"
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
