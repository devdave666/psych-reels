"""'Close the book' - the testing effect (retrieval practice). A notebook page under a desk lamp. 1080x1920, 20 s.

Roediger & Karpicke (2006, Psychological Science 17(3), 249-255), Experiment 2: 180 Washington University undergraduates
learned a prose passage by studying it four times (SSSS), three times plus one recall test (SSST), or once plus three recall
tests (STTT); no feedback was given.  One week later the STTT group recalled 61% of the idea units vs 40% for SSSS, even
though SSSS read the passage about 14.2 times (they kept tally marks) vs 3.4.  On a 5-minute test rereading won (83% vs 71%),
and the rereaders felt more confident.  Lab study with prose passages.

Here: a highlighter sweeps the page again and again while tally marks pile up in the margin (14).  'One week later': seven day
dots tick by and six of the ten written lines dissolve into dust, leaving 40%.  Drop (t = 10 s): the page is wiped clean and a
gold pen writes six lines back from memory on the beats (10.5 ... 13.0 s), then 61% lands.  Text stays in x 140-940,
y 260-1480.
Usage: python testyourself_reel.py out_silent.mp4 | python testyourself_reel.py stills t1 t2 ..."""
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
PX0, PY0, PX1, PY1 = 240.0, 590.0, 840.0, 1190.0          # notebook page
NL = 10
LINE_Y = [745 + 42 * i for i in range(NL)]
LX0, LX1 = 290.0, 790.0
rng = np.random.default_rng(1108)
WORDS = []                                                 # per line: list of (x0, x1, phase)
for i in range(NL):
    x = LX0 + (rng.uniform(0, 30) if i % 4 == 0 else 0)
    end = LX1 - (rng.uniform(60, 220) if i in (3, 6, 9) else rng.uniform(0, 40))
    ws = []
    while x < end - 30:
        wl = rng.uniform(40, 110)
        ws.append((x, min(end, x + wl), rng.uniform(0, 6.28)))
        x += wl + rng.uniform(14, 22)
    WORDS.append(ws)
LINE_END = [ws[-1][1] for ws in WORDS]

# rereading: 14 highlighter passes, accelerating; a tally mark is added at the end of each pass
NPASS = 14
PASS_T = [0.5 + 5.6 * (k / NPASS) ** 0.78 for k in range(NPASS + 1)]
TALLY_T = PASS_T[1:]
# forgetting: seven day dots, then six lines dissolve; four survive (40%)
DAY_T = [6.6 + 0.24 * k for k in range(7)]
SURVIVE = (1, 4, 6, 9)
FORGET = [i for i in range(NL) if i not in SURVIVE]
FORGET_T = {ln: 6.75 + 0.3 * k for k, ln in enumerate(FORGET)}
FORGET_D = 0.85
T_40 = 8.5
# retrieval: six gold lines written from memory on the beats after the drop
WRITE_T = [10.5 + 0.5 * k for k in range(6)]
WRITE_D = 0.42
T_61 = 13.3
DUST = [(rng.uniform(80, 1000), rng.uniform(300, 1500), rng.uniform(1.2, 3.2), rng.uniform(0, 6.28), rng.uniform(8, 22))
        for _ in range(70)]


def word_path(c, x0, x1, y, ph, prog=1.0):
    """A wobbly handwritten 'word' from x0 to x0 + prog*(x1-x0)."""
    xe = x0 + (x1 - x0) * prog
    x = x0
    c.move_to(x, y + 6 * math.sin(ph))
    while x < xe:
        x = min(xe, x + 3)
        c.line_to(x, y + 6 * math.sin(x * 0.33 + ph) + 3 * math.sin(x * 0.91 + 2 * ph) - 2 * math.cos(x * 0.13 + ph))


def ink_line(c, i, col, alpha, width=3.2, prog=1.0, jitter=0.0):
    y = LINE_Y[i]
    xe = LX0 + (LINE_END[i] - LX0) * prog
    c.set_line_width(width); c.set_line_cap(cairo.LINE_CAP_ROUND); c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.set_source_rgba(*col, alpha)
    for x0, x1, ph in WORDS[i]:
        if x0 >= xe:
            break
        p = clamp((xe - x0) / (x1 - x0))
        c.save(); c.translate(0, -jitter * math.sin(x0 * 0.05)); word_path(c, x0, x1, y, ph, p); c.stroke(); c.restore()
    return xe


def page(c, t):
    # shadow + paper
    c.set_source_rgba(0, 0, 0, 0.45)
    c.rectangle(PX0 + 14, PY0 + 20, PX1 - PX0, PY1 - PY0); c.fill()
    g = cairo.LinearGradient(PX0, PY0, PX1, PY1)
    g.add_color_stop_rgb(0, 0.96, 0.93, 0.85); g.add_color_stop_rgb(1, 0.86, 0.82, 0.74)
    c.set_source(g); c.rectangle(PX0, PY0, PX1 - PX0, PY1 - PY0); c.fill()
    c.set_line_width(1.6)
    for y in LINE_Y:
        c.set_source_rgba(0.45, 0.6, 0.8, 0.35); c.move_to(PX0 + 10, y + 12); c.line_to(PX1 - 10, y + 12); c.stroke()
    c.set_source_rgba(0.85, 0.35, 0.35, 0.45); c.move_to(PX0 + 40, PY0); c.line_to(PX0 + 40, PY1); c.stroke()
    for k in range(9):                                     # binder holes
        c.set_source_rgba(0.07, 0.08, 0.14, 1); c.arc(PX0 + 18, PY0 + 50 + 63 * k, 7, 0, 2 * math.pi); c.fill()


def tally(c, t, alpha):
    c.set_line_cap(cairo.LINE_CAP_ROUND); c.set_line_width(4.5)
    for k, tt in enumerate(TALLY_T):
        p = clamp((t - tt) / 0.08)
        if p <= 0:
            continue
        g, j = divmod(k, 5)
        bx, by = 620 + g * 62, 640
        c.set_source_rgba(0.75, 0.18, 0.18, alpha)
        if j < 4:
            x = bx + j * 11
            c.move_to(x, by); c.line_to(x + 1, by + 52 * p); c.stroke()
        else:
            c.move_to(bx - 8, by + 44); c.line_to(bx - 8 + 58 * p, by + 44 - 36 * p); c.stroke()


def days(c, t, alpha):
    for k, tt in enumerate(DAY_T):
        p = clamp((t - tt) / 0.12)
        x, y = 305 + 34 * k, 665
        c.set_line_width(2.5); c.set_source_rgba(0.25, 0.27, 0.35, 0.8 * alpha)
        c.arc(x, y, 11, 0, 2 * math.pi); c.stroke()
        if p > 0:
            c.set_source_rgba(0.25, 0.27, 0.35, alpha * p); c.arc(x, y, 11 * (0.4 + 0.6 * p), 0, 2 * math.pi); c.fill()


def forget_dust(c, i, u):
    r = np.random.default_rng(500 + i)
    for _ in range(46):
        x = r.uniform(LX0, LINE_END[i]); d = r.uniform(0, 0.35)
        v = clamp((u - d) / (1 - d))
        if v <= 0 or v >= 1:
            continue
        y = LINE_Y[i] - 140 * v ** 0.8 * r.uniform(0.5, 1.2)
        x += 40 * v * r.uniform(-1, 1)
        c.set_source_rgba(0.25, 0.25, 0.3, 0.75 * (1 - v)); c.arc(x, y, r.uniform(1.5, 3.5) * (1 - 0.5 * v), 0, 2 * math.pi); c.fill()


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    post = t >= T_DROP
    bg = cairo.LinearGradient(0, 0, 0, H)
    bg.add_color_stop_rgb(0, 0.05, 0.06, 0.12); bg.add_color_stop_rgb(1, 0.03, 0.03, 0.07)
    c.set_source(bg); c.paint()
    warm = 0.55 + 0.45 * smooth((t - T_DROP) / 1.2) if post else 0.55 - 0.15 * clamp((t - 6.5) / 3)
    lamp = cairo.RadialGradient(470, 520, 60, 540, 900, 1050)
    lamp.add_color_stop_rgba(0, 1.0, 0.78, 0.42, 0.50 * warm); lamp.add_color_stop_rgba(0.55, 0.9, 0.55, 0.25, 0.16 * warm)
    lamp.add_color_stop_rgba(1, 0, 0, 0, 0)
    c.set_source(lamp); c.paint()

    # camera: slow push-in through the build, a bump on the drop, gentle drift after
    if not post:
        sc = 1.0 + 0.045 * smooth(t / T_DROP)
    else:
        d = t - T_DROP
        sc = 1.0 + 0.03 * math.exp(-d * 5) * math.cos(d * 18) + 0.012 * smooth(d / 10)
    c.save(); c.translate(540, 890); c.scale(sc, sc); c.translate(-540, -890)
    c.translate(540, 890); c.rotate(-0.025); c.translate(-540, -890)
    page(c, t)
    GRAPH = (0.18, 0.19, 0.25)
    if not post:
        fade_old = 1.0
        for i in range(NL):
            if i in FORGET_T:
                u = clamp((t - FORGET_T[i]) / FORGET_D)
                if u < 1:
                    ink_line(c, i, GRAPH, 1 - u, jitter=10 * u)
                if u > 0:
                    forget_dust(c, i, u)
            else:
                ink_line(c, i, GRAPH, 1.0 - 0.45 * clamp((t - 7.0) / 1.5))
        # highlighter passes over the lines
        for k in range(NPASS):
            a, b = PASS_T[k], PASS_T[k + 1]
            if a <= t < b:
                f = (t - a) / (b - a)
                li = min(NL - 1, int(f * NL)); fx = f * NL - li
                y = LINE_Y[li]
                c.set_source_rgba(1.0, 0.92, 0.25, 0.42)
                c.rectangle(LX0 - 6, y - 15, (LINE_END[li] - LX0 + 12) * fx, 30); c.fill()
        tally(c, t, fade_old)
        if t > 6.4:
            days(c, t, clamp((t - 6.4) / 0.3))
    else:
        d = t - T_DROP
        if d < 0.35:                                       # old ink wiped away by the flash
            for i in SURVIVE:
                ink_line(c, i, GRAPH, 0.55 * (1 - d / 0.35))
        GOLD = (0.80, 0.45, 0.02)
        for k, tw in enumerate(WRITE_T):
            p = clamp((t - tw) / WRITE_D)
            if p <= 0:
                continue
            pe = smooth(p)
            ink_line(c, k, (1.0, 0.72, 0.18), 0.35, width=13, prog=pe)
            xe = ink_line(c, k, GOLD, 1.0, width=4.4, prog=pe)
            if p < 1:
                y = LINE_Y[k]
                gl = cairo.RadialGradient(xe, y, 0, xe, y, 46)
                gl.add_color_stop_rgba(0, 1, 0.95, 0.7, 0.95); gl.add_color_stop_rgba(1, 1, 0.8, 0.3, 0)
                c.set_source(gl); c.arc(xe, y, 46, 0, 2 * math.pi); c.fill()
            ga = clamp((t - tw - WRITE_D) / 0.25) * clamp(1 - (t - tw - WRITE_D - 0.25) / 0.6)
            if ga > 0:                                     # glint when a line is finished
                c.set_source_rgba(1, 0.9, 0.5, 0.35 * ga)
                c.rectangle(LX0 - 10, LINE_Y[k] - 18, LINE_END[k] - LX0 + 20, 36); c.fill()
        if d < 1.4:
            r = 1300 * smooth(d / 1.4)
            c.set_line_width(22 * (1 - d / 1.4) + 2); c.set_source_rgba(1, 0.85, 0.45, 0.5 * (1 - d / 1.4))
            c.arc(540, 890, r, 0, 2 * math.pi); c.stroke()
    c.restore()

    if post:                                               # floating gold motes after the drop
        a = smooth((t - T_DROP) / 1.5)
        for x, y, r, ph, sp in DUST:
            yy = (y - sp * (t - T_DROP) * 3) % 1300 + 260
            c.set_source_rgba(1, 0.82, 0.4, a * (0.25 + 0.25 * math.sin(t * 2 + ph)))
            c.arc(x + 10 * math.sin(t * 0.7 + ph), yy, r, 0, 2 * math.pi); c.fill()
    vg = cairo.RadialGradient(540, 900, 380, 540, 900, 1250)
    vg.add_color_stop_rgba(0, 0, 0, 0, 0); vg.add_color_stop_rgba(1, 0, 0, 0, 0.6)
    c.set_source(vg); c.paint()
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
        d.text((xy[0] + 2, xy[1] + 3), s, font=f, fill=(0, 0, 0, int(170 * a)), anchor="mm")
        d.text(xy, s, font=f, fill=(*fill, int(255 * a)), anchor="mm")


WHITE = (250, 246, 240)
AMBER = (255, 200, 140)
GOLD = (255, 196, 70)
GREY = (175, 180, 195)


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.3, 3.9)
    ctext(d, (540, 345), "Still rereading", font("Bold", 68), AMBER, h)
    ctext(d, (540, 445), "your notes?", font("Bold", 96), WHITE, h)
    a = win(t, 4.1, 6.4, 0.3, 0.3)
    ctext(d, (540, 380), "Read it 14 times.", font("Bold", 68), WHITE, a)
    b = win(t, 6.6, 9.85, 0.35, 0.3)
    ctext(d, (540, 380), "One week later...", font("Bold", 68), AMBER, b)
    n = win(t, T_40, 9.85, 0.25, 0.3)
    s40 = 1.0 + 0.25 * (1 - smooth((t - T_40) / 0.3))
    ctext(d, (540, 1285), "40%", font("Bold", int(150 * s40)), GREY, n)
    ctext(d, (540, 1380), "remembered", font("Regular", 38), GREY, n)
    r1 = win(t, 10.25, 14.6, 0.35, 0.35)
    ctext(d, (540, 345), "Read it once.", font("Bold", 68), WHITE, r1)
    r2 = win(t, 10.85, 14.6, 0.35, 0.35)
    ctext(d, (540, 440), "Then test yourself.", font("Bold", 68), GOLD, r2)
    m = win(t, T_61, 20.1, 0.25, 0.1)
    s61 = 1.0 + 0.3 * (1 - smooth((t - T_61) / 0.35))
    ctext(d, (540, 1285), "61%", font("Bold", int(150 * s61)), GOLD, m)
    m2 = win(t, T_61 + 0.3, 20.1, 0.35, 0.1)
    ctext(d, (540, 1380), "a week later (rereading: 40%)", font("Regular", 36), WHITE, m2)
    p = win(t, 14.8, 20.1, 0.5, 0.1)
    ctext(d, (540, 345), "Close the book.", font("Bold", 72), WHITE, p)
    p2 = win(t, 15.3, 20.1, 0.5, 0.1)
    ctext(d, (540, 440), "Pull it from memory.", font("Bold", 60), GOLD, p2)
    q = win(t, 15.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 1448), "Roediger & Karpicke, 2006 · Psychological Science", font("Regular", 26), WHITE, q)
    return ov


def compose(frame, t, debug=False):
    img = Image.fromarray(frame.clip(0, 255).astype(np.uint8)).convert("RGBA")
    img.alpha_composite(hud(t))
    if debug:
        ImageDraw.Draw(img).rectangle(SAFE, outline=(255, 0, 0, 255), width=3)
    out = img.convert("RGB")
    if t < 0.3:
        out = Image.eval(out, lambda v: int(v * smooth(t / 0.3)))
    return out


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "testyourself_silent.mp4"
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
