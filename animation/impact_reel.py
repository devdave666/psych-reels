"""'Plug into your why' - contact with the people your work helps. A drained battery, one "no" after another; at the drop
(t = 10 s) a cable from the student the work pays for plugs in and the battery recharges past full.  1080x1920, 20 s.

Grant, Campbell, Chen, Cottone, Lapedis & Lee (2007, Organizational Behavior and Human Decision Processes 103(1), 53-67),
Experiment 1: 39 paid callers at a university fundraising call centre.  17 spent about 5 minutes meeting a scholarship student
whose scholarship their calls helped fund; 12 only read a letter from him; 10 had no contact.  One month later the contact group
spent 142% more time on the phone and raised 171% more money per week than before (mean $185.94 -> $503.22, 2.71x);
the letter and no-contact groups did not change significantly.  Small sample, one organisation (caveats go in the caption).

t < 10 s: each rejection (a red X) knocks the battery down a notch, the student appears at 7 s and a cable snakes over (8.2 s);
drop (t = 10 s): the plug clicks in, six cells fill on the beats (10.5 ... 13.0 s) and the battery overflows to +171% (13.3 s).
Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python impact_reel.py out_silent.mp4      render
       python impact_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
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
T_STUDENT = 7.0                                  # the student fades in
T_CABLE = 8.2                                    # plug travels 8.2 -> 10.0
T_FULL = 13.3                                    # overflow / +171%
BX0, BX1, BY0, BY1 = 400.0, 680.0, 660.0, 1200.0  # battery body
PAD = 20.0
REJ_T = [0.9, 2.1, 3.3, 4.5, 5.7, 6.9, 8.0]      # one "no" each
REJ_XY = [(250, 760), (830, 900), (255, 1010), (825, 720), (250, 880), (830, 1060), (255, 700)]
LV0, LV_LOW = 0.86, 0.08
CELL_T = [T_DROP + 0.5 * (j + 1) for j in range(6)]           # a cell fills on each beat 10.5 ... 13.0
BEEP_T = [8.6, 9.1, 9.6]                                      # low-battery blinks
STU = (845.0, 1170.0)                                         # student's head
SOCKET = (540.0, 1238.0)
rng = np.random.default_rng(171)
DOTS = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1.0, 2.4), rng.uniform(0, 6.28)) for _ in range(90)]
SPARKS = [(rng.uniform(0, 6.28), rng.uniform(250, 700), rng.uniform(3, 7)) for _ in range(40)]


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def level(t):
    if t < T_DROP:
        lv = LV0
        for i, rt in enumerate(REJ_T):
            k = smooth((t - rt) / 0.25)
            lv -= k * (LV0 - LV_LOW) / len(REJ_T)
        return lv
    lv = LV_LOW
    for j, ct in enumerate(CELL_T):
        lv += smooth((t - ct + 0.18) / 0.3) * (1 - LV_LOW) / 6
    return lv


def fill_col(lv, post):
    if lv < 0.25:
        c = (0.92, 0.25, 0.22)
    elif lv < 0.5:
        c = (0.98, 0.66, 0.20)
    else:
        c = (0.35, 0.85, 0.45)
    return mix3(c, (1.0, 0.82, 0.30), post)


def cable_pts(t):
    """bezier from the student's hand to the plug tip; the plug slides along it until it reaches the socket"""
    p0 = (STU[0] - 40, STU[1] + 90)
    p3 = (SOCKET[0], SOCKET[1] + 40)
    c1 = (p0[0] - 30, 1400)
    c2 = (p3[0] + 10, 1420)
    return p0, c1, c2, p3


def bez(p0, p1, p2, p3, u):
    v = 1 - u
    return (v ** 3 * p0[0] + 3 * v * v * u * p1[0] + 3 * v * u * u * p2[0] + u ** 3 * p3[0],
            v ** 3 * p0[1] + 3 * v * v * u * p1[1] + 3 * v * u * u * p2[1] + u ** 3 * p3[1])


def glow(c, x, y, r, col, a):
    gr = cairo.RadialGradient(x, y, 1, x, y, r)
    gr.add_color_stop_rgba(0, *col, a); gr.add_color_stop_rgba(1, *col, 0)
    c.set_source(gr); c.arc(x, y, r, 0, 2 * math.pi); c.fill()


def rrect(c, x0, y0, x1, y1, r):
    c.new_sub_path()
    c.arc(x1 - r, y0 + r, r, -math.pi / 2, 0); c.arc(x1 - r, y1 - r, r, 0, math.pi / 2)
    c.arc(x0 + r, y1 - r, r, math.pi / 2, math.pi); c.arc(x0 + r, y0 + r, r, math.pi, 1.5 * math.pi)
    c.close_path()


def student(c, t, a, post):
    if a <= 0:
        return
    hx, hy = STU
    bob = 4 * math.sin(t * 2.2)
    hy += bob
    c.push_group()
    glow(c, hx, hy + 60, 230, (1.0, 0.8, 0.45), 0.25 + 0.25 * post)
    body = mix3((0.55, 0.60, 0.75), (0.98, 0.86, 0.62), post)
    c.set_source_rgb(*body)
    c.move_to(hx - 62, hy + 190); c.curve_to(hx - 60, hy + 80, hx - 40, hy + 52, hx, hy + 52)
    c.curve_to(hx + 40, hy + 52, hx + 60, hy + 80, hx + 62, hy + 190); c.close_path(); c.fill()
    c.arc(hx, hy, 40, 0, 2 * math.pi); c.fill()
    # mortarboard
    c.set_source_rgb(0.10, 0.11, 0.18)
    c.move_to(hx - 62, hy - 34); c.line_to(hx, hy - 58); c.line_to(hx + 62, hy - 34); c.line_to(hx, hy - 12); c.close_path()
    c.fill()
    c.rectangle(hx - 26, hy - 34, 52, 16); c.fill()
    c.set_line_width(3); c.set_source_rgb(1.0, 0.8, 0.3)
    c.move_to(hx + 4, hy - 34); c.line_to(hx + 46, hy - 26); c.line_to(hx + 46, hy + 2); c.stroke()
    # arm reaching toward the cable (waves during the payoff)
    wave = 0.35 * math.sin(t * 6) if t > 14.8 else 0.0
    c.set_line_width(16); c.set_line_cap(cairo.LINE_CAP_ROUND); c.set_source_rgb(*body)
    ax, ay = hx - 40, hy + 80
    if t > 14.8:
        c.move_to(hx + 40, hy + 80); c.line_to(hx + 80 + 30 * math.cos(-1.2 + wave), hy + 20 + 40 * math.sin(-1.2 + wave))
        c.stroke()
    c.move_to(ax, ay); c.line_to(ax - 10, ay + 10); c.stroke()
    # smile
    c.set_line_width(3.5); c.set_source_rgb(0.2, 0.15, 0.2)
    c.arc(hx, hy + 6, 16, 0.3, math.pi - 0.3); c.stroke()
    c.arc(hx - 13, hy - 6, 3.5, 0, 2 * math.pi); c.fill(); c.arc(hx + 13, hy - 6, 3.5, 0, 2 * math.pi); c.fill()
    c.pop_group_to_source(); c.paint_with_alpha(a)


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    post = smooth((t - T_DROP) / 1.5) if t >= T_DROP else 0.0
    bg = cairo.LinearGradient(0, 0, 0, H)
    bg.add_color_stop_rgb(0, *mix3((0.06, 0.07, 0.10), (0.03, 0.12, 0.16), post))
    bg.add_color_stop_rgb(0.55, *mix3((0.09, 0.10, 0.14), (0.05, 0.20, 0.22), post))
    bg.add_color_stop_rgb(1, *mix3((0.05, 0.05, 0.08), (0.04, 0.10, 0.12), post))
    c.set_source(bg); c.paint()
    for dx, dy, dr, dp in DOTS:
        c.set_source_rgba(*mix3((0.6, 0.65, 0.8), (1.0, 0.9, 0.55), post), 0.06 + 0.05 * math.sin(t * 1.1 + dp) + 0.18 * post)
        c.arc(dx, dy - 25 * post * ((t * 0.3 + dp) % 1), dr, 0, 2 * math.pi); c.fill()
    lv = level(t)
    low = clamp((t - BEEP_T[0] + 0.4) / 0.4) * (1 - post)
    blink = 0.0
    for bt in BEEP_T:
        u = t - bt
        if 0 <= u < 0.35:
            blink = max(blink, 1 - u / 0.35)
    cx = (BX0 + BX1) / 2
    # overflow aura
    over = smooth((t - T_FULL) / 0.6) if t >= T_FULL else 0.0
    if post > 0:
        glow(c, cx, (BY0 + BY1) / 2, 520 + 120 * over, (1.0, 0.8, 0.35), 0.18 * post + 0.25 * over)
    if over > 0:
        c.save(); c.translate(cx, (BY0 + BY1) / 2)
        for k in range(16):
            ang = k / 16 * 2 * math.pi + t * 0.25
            c.save(); c.rotate(ang)
            gr = cairo.LinearGradient(0, 0, 0, -700)
            gr.add_color_stop_rgba(0, 1, 0.85, 0.4, 0.0); gr.add_color_stop_rgba(0.45, 1, 0.85, 0.4, 0.10 * over)
            gr.add_color_stop_rgba(1, 1, 0.85, 0.4, 0)
            c.set_source(gr); c.move_to(-22, 0); c.line_to(0, -760); c.line_to(22, 0); c.close_path(); c.fill()
            c.restore()
        c.restore()
    # battery shell
    pulse = 1.0 + 0.04 * math.sin(clamp((t - T_FULL) / 0.5) * math.pi) if t >= T_FULL else 1.0
    c.save(); c.translate(cx, (BY0 + BY1) / 2); c.scale(pulse, pulse); c.translate(-cx, -(BY0 + BY1) / 2)
    shell = mix3((0.62, 0.66, 0.74), (1.0, 0.92, 0.70), post)
    shell = mix3(shell, (0.95, 0.3, 0.28), 0.8 * blink)
    rrect(c, cx - 60, BY0 - 44, cx + 60, BY0 + 6, 12); c.set_source_rgb(*shell); c.fill()
    rrect(c, BX0, BY0, BX1, BY1, 34); c.set_source_rgb(0.05, 0.06, 0.09); c.fill_preserve()
    c.set_line_width(14); c.set_source_rgb(*shell); c.stroke()
    # fill
    ih = (BY1 - BY0) - 2 * PAD
    fh = ih * clamp(lv, 0, 1)
    col = fill_col(lv, post)
    if fh > 1:
        top = BY1 - PAD - fh
        rrect(c, BX0 + PAD, top, BX1 - PAD, BY1 - PAD, 18)
        gr = cairo.LinearGradient(BX0, 0, BX1, 0)
        gr.add_color_stop_rgb(0, *[v * 0.75 for v in col]); gr.add_color_stop_rgb(0.4, *col)
        gr.add_color_stop_rgb(1, *[v * 0.8 for v in col])
        c.set_source(gr); c.fill()
        if post > 0:                                         # shimmer travelling up the fill
            sy = BY1 - PAD - ((t * 420) % (fh + 80))
            c.save(); rrect(c, BX0 + PAD, top, BX1 - PAD, BY1 - PAD, 18); c.clip()
            g2 = cairo.LinearGradient(0, sy - 60, 0, sy + 60)
            g2.add_color_stop_rgba(0, 1, 1, 1, 0); g2.add_color_stop_rgba(0.5, 1, 1, 0.9, 0.35 * post)
            g2.add_color_stop_rgba(1, 1, 1, 1, 0)
            c.set_source(g2); c.paint(); c.restore()
    # cell separators
    c.set_line_width(6); c.set_source_rgb(0.05, 0.06, 0.09)
    for j in range(1, 6):
        y = BY1 - PAD - ih * j / 6
        c.move_to(BX0 + PAD, y); c.line_to(BX1 - PAD, y); c.stroke()
    # cell flash on each beat
    for j, ct in enumerate(CELL_T):
        u = t - ct
        if 0 <= u < 0.45:
            y0 = BY1 - PAD - ih * (j + 1) / 6
            c.set_source_rgba(1, 1, 0.85, 0.7 * (1 - u / 0.45)); c.rectangle(BX0 + PAD, y0, BX1 - BX0 - 2 * PAD, ih / 6); c.fill()
    # bolt
    if post > 0:
        c.save(); c.translate(cx, (BY0 + BY1) / 2); s = 1.6 + 0.15 * math.sin(t * 5)
        c.scale(s, s)
        c.move_to(12, -70); c.line_to(-38, 8); c.line_to(-4, 8); c.line_to(-14, 70); c.line_to(38, -10); c.line_to(4, -10)
        c.close_path(); c.set_source_rgba(1, 1, 0.95, 0.9 * post); c.fill()
        c.restore()
    c.restore()
    # low-battery red wash
    if low > 0:
        c.set_source_rgba(0.8, 0.1, 0.1, 0.07 * low + 0.10 * blink); c.paint()
    # rejections
    for i, rt in enumerate(REJ_T):
        u = t - rt
        if 0 <= u < 1.4:
            x, y = REJ_XY[i]
            a = clamp(u / 0.12) * clamp((1.4 - u) / 0.5)
            s = 1.0 + 0.4 * math.exp(-u * 10)
            y -= 60 * u
            c.save(); c.translate(x, y); c.scale(s, s)
            glow(c, 0, 0, 110, (0.95, 0.2, 0.2), 0.35 * a)
            c.set_source_rgba(0.85, 0.18, 0.2, a); c.arc(0, 0, 44, 0, 2 * math.pi); c.fill()
            c.set_line_width(10); c.set_line_cap(cairo.LINE_CAP_ROUND); c.set_source_rgba(1, 0.95, 0.95, a)
            c.move_to(-17, -17); c.line_to(17, 17); c.move_to(17, -17); c.line_to(-17, 17); c.stroke()
            c.restore()
    # student
    sa = smooth((t - T_STUDENT) / 0.9) if t >= T_STUDENT else 0.0
    student(c, t, sa, post)
    # cable + plug
    if t >= T_CABLE:
        k = smooth((t - T_CABLE) / (T_DROP - T_CABLE))
        p0, c1, c2, p3 = cable_pts(t)
        n = max(2, int(80 * k))
        pts = [bez(p0, c1, c2, p3, k * i / (n - 1)) for i in range(n)]
        hot = post
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        for lw, al, colr in ((26, 0.25 * hot, (1, 0.8, 0.35)), (11, 1.0, mix3((0.35, 0.38, 0.46), (1.0, 0.82, 0.38), hot))):
            if al <= 0:
                continue
            c.new_path()
            for i, (x, y) in enumerate(pts):
                (c.move_to if i == 0 else c.line_to)(x, y)
            c.set_line_width(lw); c.set_source_rgba(*colr, al); c.stroke()
        if hot > 0:                                           # energy pulses travelling to the battery
            for q in range(5):
                u = ((t - T_DROP) * 0.9 + q / 5) % 1.0
                x, y = bez(p0, c1, c2, p3, u)
                glow(c, x, y, 34, (1, 0.95, 0.6), 0.9 * hot)
        tx, ty = pts[-1]
        tx2, ty2 = bez(p0, c1, c2, p3, max(0.0, k - 0.02))
        ang = math.atan2(ty - ty2, tx - tx2)
        c.save(); c.translate(tx, ty); c.rotate(ang)
        c.set_source_rgb(*mix3((0.75, 0.78, 0.85), (1.0, 0.92, 0.70), hot))
        rrect(c, -46, -22, 0, 22, 6); c.fill()
        c.rectangle(0, -14, 18, 7); c.fill(); c.rectangle(0, 7, 18, 7); c.fill()
        c.restore()
    # socket under the battery
    c.set_source_rgb(*mix3((0.30, 0.32, 0.40), (0.95, 0.85, 0.60), post))
    rrect(c, SOCKET[0] - 34, BY1 + 2, SOCKET[0] + 34, SOCKET[1] + 22, 8); c.fill()
    # sparks on the click
    f2 = t - T_DROP
    if 0 <= f2 < 1.2:
        for ang, sp, sz in SPARKS:
            d = sp * f2
            x = SOCKET[0] + d * math.cos(ang); y = SOCKET[1] + 20 + d * math.sin(ang) + 300 * f2 * f2
            c.set_source_rgba(1, 0.9, 0.5, clamp(1 - f2 / 1.2)); c.arc(x, y, sz * (1 - f2 / 1.4), 0, 2 * math.pi); c.fill()
    # overflow sparks rising from the top
    if over > 0:
        for i, (ang, sp, sz) in enumerate(SPARKS[:24]):
            u = ((t - T_FULL) * 0.6 + i / 24) % 1.0
            x = cx + 120 * math.sin(ang * 3 + u * 4)
            y = BY0 - 40 - 480 * u
            c.set_source_rgba(1, 0.9, 0.55, 0.8 * over * (1 - u)); c.arc(x, y, sz * 0.8, 0, 2 * math.pi); c.fill()
    if 0 <= f2 < 0.3:
        c.set_source_rgba(1, 0.92, 0.75, 0.4 * (1 - f2 / 0.3) ** 2); c.paint()
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
        d.text((xy[0] + 2, xy[1] + 3), s, font=f, fill=(0, 0, 0, int(160 * a)), anchor="mm")
        d.text((xy[0], xy[1] + 1), s, font=f, fill=(0, 0, 0, int(120 * a)), anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0, int(110 * a)))
        d.text(xy, s, font=f, fill=(*fill, int(255 * a)), anchor="mm")


WHITE = (250, 246, 240)
RED = (255, 120, 110)
GOLD = (255, 214, 110)
PALE = (255, 236, 200)


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.3, 3.9)
    ctext(d, (540, 380), "Running on", font("Bold", 74), WHITE, h)
    ctext(d, (540, 470), "empty?", font("Bold", 74), RED, h)
    b = win(t, 4.1, 9.8, 0.4, 0.3)
    ctext(d, (540, 360), "Call after call.", font("Bold", 60), WHITE, b)
    ctext(d, (540, 446), "No after no.", font("Bold", 60), RED, b)
    a = win(t, 10.2, 14.5, 0.4, 0.4)
    ctext(d, (540, 318), "5 min with the student they help:", font("Bold", 40), WHITE, a)
    a1 = win(t, T_FULL - 0.05, 14.5, 0.25, 0.4)
    ctext(d, (540, 432), "+171%", font("Bold", 136), GOLD, a1)
    a2 = win(t, T_FULL + 0.4, 14.5, 0.4, 0.4)
    ctext(d, (540, 548), "money raised a month later", font("Regular", 38), PALE, a2)
    p = win(t, 14.7, 20.1, 0.6, 0.1)
    ctext(d, (540, 360), "Meet who your", font("Bold", 64), WHITE, p)
    ctext(d, (540, 446), "work is for.", font("Bold", 64), GOLD, p)
    q = win(t, 15.3, 20.1, 0.6, 0.1)
    ctext(d, (540, 1452), "Grant et al., 2007 · 39 fundraising callers", font("Regular", 27), WHITE, q)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "impact_silent.mp4"
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
