"""'A small kindness ripples out' - prosocial spending. A dark pond of lily pads. 1080x1920, 20 s.

Dunn, Aknin & Norton (2008, Science): 46 students were handed $5 or $20 to spend by the end of the day, on themselves or on
someone else.  Those who spent it on others were happier that evening; the amount ($5 vs $20) made no difference.  A 2022 close
replication (133 people, $10) found no effect on the original analysis, so the finding is promising rather than settled.
Here: a coin dropped "for yourself" makes one faint ripple that dies; the coin dropped "for someone else" at the drop
(t = 10 s) sends ripples across the pond and every lily pad blooms as the ripple reaches it.
Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python prosocial_reel.py out_silent.mp4      render
       python prosocial_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
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

T_SELF = 4.2          # coin for yourself lands
T_DROP = 10.0         # coin for someone else lands
CX, CY = 540, 1060    # where the coin lands
SPEED = 380.0         # ripple speed, px/s
COIN_HOVER = (540, 730)
RING_T = [T_DROP + 0.5 * k for k in range(5)]
rng = np.random.default_rng(23)

PADS = []
while len(PADS) < 44:
    x, y = rng.uniform(50, 1030), rng.uniform(760, 1860)
    d = math.hypot(x - CX, y - CY)
    if d < 190 or any(math.hypot(x - p[0], y - p[1]) < 120 for p in PADS):
        continue
    PADS.append((x, y, rng.uniform(34, 46), rng.uniform(0, 6.283), d))
BLOOM = [T_DROP + p[4] / SPEED for p in PADS]
BLOOM_T = sorted(BLOOM)
SPARKS = [(rng.uniform(0, W), rng.uniform(700, 1900), rng.uniform(1, 3), rng.uniform(0, 6.28)) for _ in range(70)]
STARS = [(rng.uniform(0, W), rng.uniform(0, 700), rng.uniform(1, 2.6), rng.uniform(0, 6.28)) for _ in range(60)]


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def ring(c, r, a, wd, col=(0.75, 0.95, 0.95)):
    if r <= 2 or a <= 0.01:
        return
    c.set_source_rgba(*col, a); c.set_line_width(wd); c.arc(CX, CY, r, 0, 2 * math.pi); c.stroke()
    c.set_source_rgba(*col, a * 0.35); c.set_line_width(wd * 3.2); c.arc(CX, CY, r - wd, 0, 2 * math.pi); c.stroke()


def coin(c, x, y, s, a, glow):
    if a <= 0.01 or s <= 0.02:
        return
    if glow > 0:
        gl = cairo.RadialGradient(x, y, 20 * s, x, y, 190 * s)
        gl.add_color_stop_rgba(0, 1, 0.85, 0.4, 0.55 * glow * a); gl.add_color_stop_rgba(1, 1, 0.8, 0.3, 0)
        c.set_source(gl); c.rectangle(x - 200 * s, y - 200 * s, 400 * s, 400 * s); c.fill()
    c.set_source_rgba(0.0, 0.0, 0.0, 0.25 * a); c.arc(x + 6 * s, y + 8 * s, 62 * s, 0, 2 * math.pi); c.fill()
    g = cairo.LinearGradient(x - 60 * s, y - 60 * s, x + 60 * s, y + 60 * s)
    g.add_color_stop_rgba(0, 1.0, 0.92, 0.55, a); g.add_color_stop_rgba(1, 0.86, 0.60, 0.15, a)
    c.set_source(g); c.arc(x, y, 62 * s, 0, 2 * math.pi); c.fill()
    c.set_source_rgba(0.62, 0.38, 0.06, a); c.set_line_width(5 * s); c.arc(x, y, 50 * s, 0, 2 * math.pi); c.stroke()


def pad(c, x, y, r, rot, a, wob):
    c.save(); c.translate(x, y); c.scale(1 + wob, 1 + wob); c.rotate(rot)
    c.set_source_rgba(0.0, 0.08, 0.08, 0.35 * a); c.arc(4, 6, r, 0, 2 * math.pi); c.fill()
    c.set_source_rgba(0.10, 0.40, 0.31, a)
    c.move_to(0, 0); c.arc(0, 0, r, 0.35, 2 * math.pi - 0.35); c.close_path(); c.fill()
    c.set_source_rgba(0.18, 0.55, 0.40, 0.8 * a); c.set_line_width(2)
    for k in range(3):
        ang = 0.9 + k * 1.6
        c.move_to(0, 0); c.line_to(r * 0.8 * math.cos(ang), r * 0.8 * math.sin(ang)); c.stroke()
    c.restore()


def flower(c, x, y, r, rot, k, pop):
    if k <= 0.01:
        return
    s = k * (1 + 0.35 * pop)
    gl = cairo.RadialGradient(x, y, 4, x, y, 70 * s)
    gl.add_color_stop_rgba(0, 1, 0.75, 0.55, 0.45 * min(1, k)); gl.add_color_stop_rgba(1, 1, 0.6, 0.5, 0)
    c.set_source(gl); c.rectangle(x - 75 * s, y - 75 * s, 150 * s, 150 * s); c.fill()
    c.save(); c.translate(x, y); c.rotate(rot)
    for layer, (n, ln, col) in enumerate(((8, 1.0, (1.0, 0.55, 0.62)), (6, 0.66, (1.0, 0.78, 0.80)))):
        for i in range(n):
            ang = 2 * math.pi * i / n + layer * 0.4
            c.save(); c.rotate(ang); c.translate(r * 0.42 * ln * s, 0); c.scale(r * 0.62 * ln * s, r * 0.24 * ln * s)
            c.set_source_rgba(*col, 0.95 * min(1, k)); c.arc(0, 0, 1, 0, 2 * math.pi); c.fill(); c.restore()
    c.set_source_rgba(1.0, 0.85, 0.35, min(1, k)); c.arc(0, 0, r * 0.2 * s, 0, 2 * math.pi); c.fill()
    c.restore()


def splash(c, ti, t, strength):
    d = t - ti
    if d < 0 or d > 0.7:
        return
    for i in range(18):
        ang = i * 0.349 + (i % 3) * 0.2
        v = 260 + 110 * (i % 4)
        px = CX + math.cos(ang) * v * d * 0.8
        py = CY + math.sin(ang) * v * d * 0.45 - (320 * d - 520 * d * d)
        c.set_source_rgba(0.85, 1, 1, strength * (1 - d / 0.7)); c.arc(px, py, 5 * (1 - d / 0.7) + 1.5, 0, 2 * math.pi); c.fill()


def coin_state(t):
    """(x, y, scale, alpha, glow) for the coin at time t, or None."""
    hx, hy = COIN_HOVER
    if 0.5 <= t < 3.5:                                    # first coin hovers
        return hx, hy + 9 * math.sin(t * 2.2), 1.15, smooth((t - 0.5) / 0.6), 0.15
    if 3.5 <= t < T_SELF:
        u = ((t - 3.5) / (T_SELF - 3.5)) ** 2
        return hx, lerp(hy, CY, u), lerp(1.15, 0.8, u), 1.0, 0.1
    if T_SELF <= t < T_SELF + 0.55:
        u = (t - T_SELF) / 0.55
        return CX, CY, 0.8 * (1 - 0.5 * u), 1 - u, 0.0
    if 6.8 <= t < 9.3:                                    # second coin: glowing, pulsing on the beat
        beat = math.exp(-((t * 2) % 1) / 0.18)
        return hx, hy + 9 * math.sin(t * 2.2), 1.15 + 0.06 * beat, smooth((t - 6.8) / 0.5), 0.5 + 0.5 * smooth((t - 6.8) / 2.5) + 0.3 * beat
    if 9.3 <= t < T_DROP:
        u = ((t - 9.3) / (T_DROP - 9.3)) ** 2
        return hx, lerp(hy, CY, u), lerp(1.2, 0.85, u), 1.0, 1.0
    if T_DROP <= t < T_DROP + 0.55:
        u = (t - T_DROP) / 0.55
        return CX, CY, 0.85 * (1 - 0.5 * u), 1 - u, 1 - u
    return None


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    warm = smooth((t - T_DROP) / 3.0) if t >= T_DROP else 0.0
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *mix3((0.02, 0.08, 0.13), (0.06, 0.12, 0.20), warm))
    g.add_color_stop_rgb(0.45, *mix3((0.03, 0.15, 0.20), (0.07, 0.26, 0.30), warm))
    g.add_color_stop_rgb(1, *mix3((0.04, 0.20, 0.25), (0.12, 0.34, 0.34), warm))
    c.set_source(g); c.rectangle(0, 0, W, H); c.fill()
    for sx, sy, sr, sp in STARS:
        c.set_source_rgba(1, 1, 1, 0.2 + 0.18 * math.sin(t * 1.5 + sp)); c.arc(sx, sy, sr, 0, 2 * math.pi); c.fill()
    # water shimmer
    for k in range(10):
        yy = 800 + k * 110 + 8 * math.sin(t * 0.8 + k)
        c.set_source_rgba(0.6, 0.9, 0.9, 0.05); c.set_line_width(3)
        c.move_to(60 + 40 * math.sin(t * 0.5 + k), yy); c.curve_to(300, yy - 14, 700, yy + 14, 1020 - 30 * math.cos(t * 0.4 + k), yy); c.stroke()
    # ripples
    d = t - T_SELF
    if d > 0:
        r = 190 * (1 - math.exp(-d / 0.55)); ring(c, r, 0.45 * max(0, 1 - d / 1.6), 4)
    for k, tr in enumerate(RING_T):
        d = t - tr
        if d > 0:
            r = SPEED * d
            ring(c, r, 0.6 * (1 - 0.14 * k) * max(0.0, 1 - r / 1250), 6 - 0.6 * k)
    # lily pads and flowers
    for i, (px, py, pr, rot, dist) in enumerate(PADS):
        a = smooth((t - (0.8 + (i % 11) * 0.12)) / 0.8)
        if a <= 0:
            continue
        wob = 0.0
        for tr in [T_SELF] + RING_T[:3]:
            e = t - tr - dist / (SPEED if tr != T_SELF else 220)
            if tr != T_SELF or dist < 260:
                if 0 < e < 0.6:
                    wob += (0.10 if tr != T_SELF else 0.04) * math.sin(e * 14) * math.exp(-e / 0.25)
        pad(c, px, py + 5 * math.sin(t * 1.1 + rot) + 30 * (1 - a), pr, rot, a, wob)
        e = t - BLOOM[i]
        if e > 0:
            flower(c, px, py + 5 * math.sin(t * 1.1 + rot) - 4, pr, rot, smooth(e / 0.5), math.exp(-e / 0.12))
    # sparkles rising after the drop
    if t > T_DROP:
        for sx, sy, sr, sp in SPARKS:
            u = (t - T_DROP + sp) % 5.0
            dist = math.hypot(sx - CX, sy - CY)
            if t - T_DROP < dist / SPEED:
                continue
            c.set_source_rgba(1, 0.9, 0.6, 0.55 * math.sin(u / 5.0 * math.pi) * smooth((t - T_DROP) / 1.5))
            c.arc(sx + 10 * math.sin(u + sp), sy - 70 * u, sr, 0, 2 * math.pi); c.fill()
    splash(c, T_SELF, t, 0.5)
    splash(c, T_DROP, t, 1.0)
    cs = coin_state(t)
    if cs:
        coin(c, *cs[:2], cs[2], cs[3], cs[4])
    f2 = t - T_DROP
    if 0 <= f2 < 0.3:
        c.set_source_rgba(1, 0.92, 0.75, 0.35 * (1 - f2 / 0.3) ** 2); c.paint()
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
ROSE = (255, 170, 190)
GOLD = (255, 214, 120)
MINT = (170, 235, 220)


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 3.4)
    ctext(d, (540, 380), "You have $5", font("Bold", 62), WHITE, h)
    ctext(d, (540, 460), "to spend today.", font("Bold", 58), GOLD, h)
    ctext(d, (540, 380), "On yourself...", font("Bold", 58), MINT, win(t, 4.4, 6.6, 0.4, 0.3))
    ctext(d, (540, 380), "or on someone else?", font("Bold", 56), ROSE, win(t, 7.4, 9.8, 0.5, 0.3))
    cs = coin_state(t)
    if cs and cs[3] > 0.05:                                           # the "$5" printed on the coin follows it
        ctext(d, (cs[0], cs[1] - 2), "$5", font("Bold", int(60 * cs[2])), (120, 70, 10), cs[3])
    if t >= T_DROP:
        pop = math.exp(-(t - T_DROP) / 0.2)
        a = win(t, T_DROP, 14.4, 0.2, 0.4)
        ctext(d, (540, 380), "Spent on others,", font("Bold", 52), WHITE, win(t, 10.2, 14.4, 0.3, 0.3))
        ctext(d, (540, 560), "$5 = $20", font("Bold", int(140 + 18 * pop)), GOLD, a)
        ctext(d, (540, 660), "the amount didn't matter", font("Regular", 32), WHITE, win(t, 11.0, 14.4, 0.4, 0.3))
    p = win(t, 14.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 330), "Spend $5 on someone else.", font("Bold", 50), WHITE, p)
    ctext(d, (540, 400), "Then notice your day.", font("Bold", 50), ROSE, p)
    q = win(t, 15.2, 20.1, 0.6, 0.1)
    if q > 0.01:
        d.rounded_rectangle((200, 1415, 880, 1465), 25, fill=(2, 20, 28, int(190 * q)))
    ctext(d, (540, 1440), "Dunn, Aknin & Norton, 2008 · 46 students", font("Regular", 27), WHITE, q)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "prosocial_silent.mp4"
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
