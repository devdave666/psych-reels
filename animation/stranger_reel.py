"""'Say hello' - talking to a stranger on the train.  A cold-blue commuter carriage rattles through a dark tunnel; four
passengers sit side by side, each sealed in a frosted glass bubble, faces lit by their phones.  The hero keeps glancing at
the stranger beside them, lowers the phone (8.6 s) and a little speech bubble forms (9.2 s).  At the drop (t = 10 s) both
glass bubbles shatter, the train bursts out of the tunnel into a sunrise, and the two trade speech bubbles on every beat
(10.5 ... 13.0 s) while the carriage warms to amber.  1080x1920, 20 s.

Epley & Schroeder (2014, Journal of Experimental Psychology: General, 'Mistakenly seeking solitude'):
  Exp 1a - 97 Chicago-area (Homewood Metra) train commuters randomly told to talk to a stranger, sit in solitude, or commute
           as usual; the connection group reported a significantly more positive commute than the solitude group.
           Conversations averaged 14.2 min.
  Exp 1b - commuters who only imagined it predicted the opposite (connection the least positive).
  Exp 3a - 64 commuters predicted fewer than 47% of fellow commuters would be willing to talk; in reality everyone who
           returned a survey reported talking with the person they tried to connect with, and not one reported being
           rebuffed (7 in Exp 1a could not try because nobody sat next to them).
  Self-reported mood, mailed-back surveys, one city (caveats go in the caption).
Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python stranger_reel.py out_silent.mp4      render
       python stranger_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
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
T_LOWER = 8.6                                  # hero lowers the phone 8.6 -> 9.2
T_HI = 9.2                                     # first little speech bubble
GLANCE_T = [2.2, 5.0, 7.2]                     # hero sneaks a look (0.9 s each)
CLACK_T = [0.5 + k for k in range(10)]         # a tunnel lamp passes the centre each second (rail clack)
CHAT_T = [T_DROP + 0.5 * (j + 1) for j in range(6)]   # speech bubbles traded on the beats 10.5 ... 13.0
PX = [190, 420, 660, 890]                      # passengers' x
HERO, STR = 1, 2
HEAD_Y, SEAT_Y, FLOOR_Y = 1010, 1262, 1520
WIN_Y0, WIN_Y1 = 650, 940
WINS = [(50, 330), (400, 680), (750, 1030)]
ZOOM = 1.15
LAMP_V = 1500.0                                # px / s
rng = np.random.default_rng(41)
SHARDS = []                                    # (person, start x, start y, vx, vy, spin, size, phase)
for p in (HERO, STR):
    for k in range(30):
        a = k / 30 * 2 * math.pi + rng.uniform(-0.08, 0.08)
        sx, sy = PX[p] + 108 * math.cos(a), 1150 + 235 * math.sin(a)
        sp = rng.uniform(380, 760)
        SHARDS.append((p, sx, sy, math.cos(a) * sp + (p - 1.5) * 160, math.sin(a) * sp * 0.7 - 260,
                       rng.uniform(-9, 9), rng.uniform(14, 30), rng.uniform(0, 6.28)))
DUST = [(rng.uniform(0, W), rng.uniform(600, 1500), rng.uniform(1.2, 3.2), rng.uniform(0, 6.28)) for _ in range(46)]
SKY = [(rng.uniform(0, 1), rng.uniform(40, 170), rng.uniform(30, 70)) for _ in range(26)]     # skyline blocks


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def glow(c, x, y, r, col, a):
    gr = cairo.RadialGradient(x, y, 1, x, y, r)
    gr.add_color_stop_rgba(0, *col, a); gr.add_color_stop_rgba(1, *col, 0)
    c.set_source(gr); c.arc(x, y, r, 0, 2 * math.pi); c.fill()


def rrect(c, x0, y0, x1, y1, r):
    c.new_sub_path()
    c.arc(x1 - r, y0 + r, r, -math.pi / 2, 0); c.arc(x1 - r, y1 - r, r, 0, math.pi / 2)
    c.arc(x0 + r, y1 - r, r, math.pi / 2, math.pi); c.arc(x0 + r, y0 + r, r, math.pi, 1.5 * math.pi)
    c.close_path()


def warm_k(t):
    return smooth((t - T_DROP) / 2.5) if t >= T_DROP else 0.0


def glance(t):
    """0..1 how far the hero's head is turned toward the stranger"""
    g = 0.0
    for gt in GLANCE_T:
        g = max(g, smooth((t - gt) / 0.25) * smooth((gt + 0.9 - t) / 0.25) * 0.8)
    if t >= T_LOWER:
        g = max(g, smooth((t - T_LOWER) / 0.5))
    return g


def windows(c, t, sway):
    out = smooth((t - T_DROP) / 0.6) if t >= T_DROP else 0.0
    for x0, x1 in WINS:
        c.save()
        rrect(c, x0, WIN_Y0 + sway, x1, WIN_Y1 + sway, 34); c.clip()
        # tunnel
        c.set_source_rgb(0.02, 0.03, 0.05); c.paint()
        if out < 1:
            for k in range(-1, 24):
                lx = 540 + (0.5 + k - t) * LAMP_V                         # lamp k passes x = 540 at t = 0.5 + k
                if -200 < lx < W + 200:
                    for yy in (WIN_Y0 + 60, WIN_Y1 - 50):
                        gr = cairo.LinearGradient(lx - 160, 0, lx + 30, 0)
                        gr.add_color_stop_rgba(0, 0.6, 0.8, 1.0, 0)
                        gr.add_color_stop_rgba(1, 0.75, 0.9, 1.0, 0.85 * (1 - out))
                        c.set_source(gr); c.rectangle(lx - 160, yy + sway - 4, 190, 8); c.fill()
                    glow(c, lx, WIN_Y0 + 60 + sway, 70, (0.5, 0.7, 1.0), 0.3 * (1 - out))
        if out > 0:
            sky = cairo.LinearGradient(0, WIN_Y0, 0, WIN_Y1)
            sky.add_color_stop_rgba(0, 0.98, 0.62, 0.42, out)
            sky.add_color_stop_rgba(0.55, 1.0, 0.82, 0.55, out)
            sky.add_color_stop_rgba(1, 1.0, 0.93, 0.74, out)
            c.set_source(sky); c.paint()
            glow(c, 620, WIN_Y1 - 40 + sway, 260, (1.0, 0.95, 0.7), 0.9 * out)
            c.set_source_rgba(1.0, 0.97, 0.85, out); c.arc(620, WIN_Y1 - 40 + sway, 62, 0, 2 * math.pi); c.fill()
            for u, h, w in SKY:                                            # skyline scrolling by
                bx = ((u * 1600 - (t - T_DROP) * 260) % 1600) - 260
                c.set_source_rgba(0.45, 0.25, 0.32, 0.85 * out)
                c.rectangle(bx, WIN_Y1 + sway - h * 0.8, w, h); c.fill()
        c.restore()
        # frame
        rrect(c, x0, WIN_Y0 + sway, x1, WIN_Y1 + sway, 34)
        c.set_line_width(10); c.set_source_rgb(*mix3((0.34, 0.40, 0.50), (0.62, 0.48, 0.38), warm_k(t))); c.stroke()
    return out


def person(c, i, t, sway, wk):
    x = PX[i] + 2.5 * math.sin(t * 2.1 + i)
    hero, strg = i == HERO, i == STR
    coat = {HERO: (0.92, 0.55, 0.26), STR: (0.22, 0.62, 0.66)}.get(i, (0.30, 0.34, 0.44))
    coat = mix3(mix3(coat, (0.25, 0.32, 0.45), 0.35), coat, wk) if (hero or strg) else mix3(coat, (0.42, 0.36, 0.38), wk)
    skin = mix3((0.62, 0.64, 0.74), (0.93, 0.74, 0.60), wk if (hero or strg) else 0.4 * wk)
    if hero:
        turn = glance(t)
    elif strg:
        turn = -smooth((t - T_DROP) / 0.5) if t >= T_DROP else 0.0
    else:
        turn = 0.0
    # legs
    c.set_source_rgb(*mix3((0.10, 0.12, 0.18), (0.20, 0.14, 0.16), wk))
    for dx in (-34, 22):
        c.rectangle(x + dx, SEAT_Y + sway, 30, FLOOR_Y - SEAT_Y - 30); c.fill()
        rrect(c, x + dx - 6, FLOOR_Y - 34 + sway, x + dx + 44, FLOOR_Y - 8 + sway, 10); c.fill()
    # torso
    c.move_to(x - 78, SEAT_Y + 20 + sway)
    c.curve_to(x - 84, 1130 + sway, x - 70, 1080 + sway, x, 1074 + sway)
    c.curve_to(x + 70, 1080 + sway, x + 84, 1130 + sway, x + 78, SEAT_Y + 20 + sway)
    c.close_path(); c.set_source_rgb(*coat); c.fill()
    # phone: held at chest, hero lowers it, stranger drops it at the drop
    down = 0.0
    if hero and t >= T_LOWER:
        down = smooth((t - T_LOWER) / 0.6)
    if strg and t >= T_DROP:
        down = smooth((t - T_DROP) / 0.5)
    py = lerp(1150, 1228, down) + sway
    lit = 1 - down
    hx, hy = x + 26 * turn, HEAD_Y + 10 * lit + sway
    if lit > 0:
        glow(c, hx, hy + 20, 120, (0.45, 0.7, 1.0), 0.25 * lit)
    c.set_source_rgb(*coat); c.set_line_width(26); c.set_line_cap(cairo.LINE_CAP_ROUND)
    for s in (-1, 1):                                                       # arms toward the phone
        c.move_to(x + s * 66, 1110 + sway); c.line_to(x + s * 22, py + 12); c.stroke()
    c.set_source_rgb(0.08, 0.09, 0.12); rrect(c, x - 22, py - 30, x + 22, py + 30, 7); c.fill()
    c.set_source_rgba(0.55, 0.8, 1.0, 0.9 * lit + 0.15); rrect(c, x - 17, py - 25, x + 17, py + 24, 5); c.fill()
    # head
    c.set_source_rgb(*skin); c.arc(hx, hy, 56, 0, 2 * math.pi); c.fill()
    hair = {HERO: (0.30, 0.17, 0.10), STR: (0.14, 0.12, 0.14)}.get(i, (0.16, 0.17, 0.22))
    c.set_source_rgb(*hair)
    c.arc(hx, hy - 6, 58, math.pi * 1.0, math.pi * 2.0); c.fill()
    if strg:
        c.arc(hx + 46, hy + 8, 22, 0, 2 * math.pi); c.fill()                  # bun / ponytail
    look_down = 0.65 * lit
    ex = 24 * turn
    ey = 8 + 14 * look_down
    for s in (-1, 1):
        cx_, cy_ = hx + s * 20 + ex * 0.6, hy + ey
        if (t % 4.3 + i * 0.7) % 4.3 < 0.12:
            c.set_line_width(4); c.set_source_rgb(0.1, 0.1, 0.14); c.move_to(cx_ - 7, cy_); c.line_to(cx_ + 7, cy_); c.stroke()
        else:
            c.set_source_rgb(0.1, 0.1, 0.14); c.arc(cx_ + ex * 0.25, cy_, 6.5, 0, 2 * math.pi); c.fill()
    smile = wk if (hero or strg) else 0.0
    c.set_line_width(4.5); c.set_source_rgb(0.25, 0.12, 0.12)
    mx, my = hx + ex * 0.6, hy + 32 + 6 * look_down
    if smile > 0.05:
        c.arc(mx, my - 8, 15, 0.25 * math.pi, 0.75 * math.pi); c.stroke()
    else:
        c.move_to(mx - 11, my); c.line_to(mx + 11, my); c.stroke()


def bubble_glass(c, i, t, sway, a):
    """frosted glass bubble sealing each passenger in"""
    if a <= 0.01:
        return
    x, y = PX[i], 1150 + sway
    c.save(); c.translate(x, y); c.scale(1, 235 / 108)
    c.arc(0, 0, 108, 0, 2 * math.pi); c.restore()
    c.set_source_rgba(0.6, 0.78, 1.0, 0.10 * a); c.fill_preserve()
    c.set_line_width(5); c.set_source_rgba(0.7, 0.86, 1.0, 0.55 * a); c.stroke()
    c.save(); c.translate(x, y); c.scale(1, 235 / 108)
    c.arc(0, 0, 92, math.pi * 1.1, math.pi * 1.45); c.restore()
    c.set_line_width(7); c.set_source_rgba(1, 1, 1, 0.35 * a); c.stroke()


def speech(c, x, y, s, col, a, kind, tail):
    if a <= 0.01 or s <= 0.01:
        return
    c.save(); c.translate(x, y); c.scale(s, s)
    rrect(c, -78, -46, 78, 46, 30)
    c.move_to(tail * 20, 40); c.line_to(tail * 46, 76); c.line_to(tail * 50, 40); c.close_path()
    c.set_source_rgba(*col, a); c.fill()
    ink = (0.20, 0.16, 0.22)
    if kind == 0:                                                           # three dots
        for k in (-1, 0, 1):
            c.set_source_rgba(*ink, a); c.arc(k * 30, 0, 9, 0, 2 * math.pi); c.fill()
    elif kind == 1:                                                         # star
        c.new_path()
        for k in range(10):
            r = 28 if k % 2 == 0 else 12
            u = -math.pi / 2 + k * math.pi / 5
            (c.move_to if k == 0 else c.line_to)(r * math.cos(u), r * math.sin(u))
        c.close_path(); c.set_source_rgba(0.95, 0.62, 0.20, a); c.fill()
    elif kind == 2:                                                         # heart
        c.new_path(); c.move_to(0, 24)
        c.curve_to(-40, -4, -22, -34, 0, -12); c.curve_to(22, -34, 40, -4, 0, 24)
        c.set_source_rgba(0.92, 0.36, 0.40, a); c.fill()
    else:                                                                   # laugh: 'ha' squiggle
        c.set_line_width(6); c.set_source_rgba(*ink, a)
        c.move_to(-46, 4)
        for k in range(1, 9):
            c.line_to(-46 + k * 11.5, 4 + (-14 if k % 2 else 10))
        c.stroke()
    c.restore()


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    wk = warm_k(t)
    rattle = 1 - smooth((t - T_DROP) / 1.5) if t >= T_DROP else 1.0
    sway = 3.0 * math.sin(t * 2 * math.pi * 1.0) * rattle + 4 * math.exp(-((t % 1.0) - 0.5) ** 2 / 0.002) * rattle
    wall = cairo.LinearGradient(0, 0, 0, H)
    wall.add_color_stop_rgb(0, *mix3((0.05, 0.07, 0.11), (0.20, 0.10, 0.10), wk))
    wall.add_color_stop_rgb(0.33, *mix3((0.10, 0.14, 0.20), (0.40, 0.22, 0.17), wk))
    wall.add_color_stop_rgb(0.6, *mix3((0.13, 0.17, 0.24), (0.47, 0.29, 0.21), wk))
    wall.add_color_stop_rgb(1, *mix3((0.04, 0.05, 0.08), (0.16, 0.09, 0.08), wk))
    c.set_source(wall); c.paint()
    c.save(); c.translate(540, 900); c.scale(ZOOM, ZOOM); c.translate(-540, -900)    # bring the carriage closer
    out = windows(c, t, sway)
    # grab rail and straps
    c.set_source_rgb(*mix3((0.55, 0.60, 0.68), (0.85, 0.68, 0.50), wk)); c.rectangle(0, 600 + sway, W, 10); c.fill()
    for k, sx in enumerate((120, 300, 480, 660, 840, 1010)):
        ang = 0.08 * math.sin(t * 2.6 + k) * rattle + 0.03 * math.sin(t * 1.1 + k)
        c.save(); c.translate(sx, 610 + sway); c.rotate(ang)
        c.set_source_rgb(*mix3((0.40, 0.45, 0.52), (0.70, 0.55, 0.42), wk))
        c.rectangle(-4, 0, 8, 26); c.fill()
        c.set_line_width(6); c.arc(0, 40, 15, 0, 2 * math.pi); c.stroke()
        c.restore()
    # light from the windows after the tunnel
    if out > 0:
        for x0, x1 in WINS:
            c.move_to(x0 + 20, WIN_Y1 + sway); c.line_to(x1 - 20, WIN_Y1 + sway)
            c.line_to(x1 + 140, FLOOR_Y); c.line_to(x0 + 120, FLOOR_Y); c.close_path()
            gr = cairo.LinearGradient(0, WIN_Y1, 0, FLOOR_Y)
            gr.add_color_stop_rgba(0, 1.0, 0.85, 0.55, 0.20 * out); gr.add_color_stop_rgba(1, 1.0, 0.85, 0.55, 0)
            c.set_source(gr); c.fill()
    # seat back + cushion
    c.set_source_rgb(*mix3((0.16, 0.22, 0.34), (0.55, 0.26, 0.22), wk)); rrect(c, 20, 990 + sway, W - 20, SEAT_Y + sway, 26); c.fill()
    for k in range(5):
        c.set_source_rgba(0, 0, 0, 0.15); c.rectangle(20 + k * 260 + 130, 1000 + sway, 4, SEAT_Y - 1010); c.fill()
    # floor
    c.set_source_rgb(*mix3((0.05, 0.06, 0.09), (0.15, 0.09, 0.08), wk)); c.rectangle(0, FLOOR_Y - 20, W, H); c.fill()
    for i in range(4):
        person(c, i, t, sway, wk)
    c.set_source_rgb(*mix3((0.20, 0.27, 0.40), (0.66, 0.33, 0.26), wk)); rrect(c, 10, SEAT_Y - 8 + sway, W - 10, SEAT_Y + 46 + sway, 18); c.fill()
    # glass bubbles (hero + stranger shatter at the drop)
    for i in range(4):
        if i in (HERO, STR):
            a = 1.0 if t < T_DROP else 0.0
            if T_HI <= t < T_DROP and i == HERO:                           # strains as the hero reaches out
                a = 1.0 - 0.25 * math.sin((t - T_HI) * 30) ** 2
        else:
            a = 1.0 - 0.5 * wk
        bubble_glass(c, i, t, sway, a)
    if t >= T_DROP:
        u = t - T_DROP
        if u < 1.8:
            for p, sx, sy, vx, vy, spn, sz, ph in SHARDS:
                x, y = sx + vx * u, sy + vy * u + 900 * u * u + sway
                a = clamp(1 - u / 1.8)
                c.save(); c.translate(x, y); c.rotate(ph + spn * u)
                c.move_to(-sz, -sz * 0.4); c.line_to(sz * 0.8, -sz * 0.6); c.line_to(sz * 0.2, sz)
                c.close_path(); c.set_source_rgba(0.8, 0.92, 1.0, 0.75 * a); c.fill()
                c.restore()
        glow(c, (PX[HERO] + PX[STR]) / 2, 1060, 360, (1.0, 0.78, 0.45), 0.35 * wk)
    # warm dust motes in the sunbeams
    if out > 0:
        for dx, dy, dr, dp in DUST:
            c.set_source_rgba(1, 0.9, 0.7, 0.35 * out * (0.5 + 0.5 * math.sin(t * 1.5 + dp)))
            c.arc(dx + 14 * math.sin(t * 0.6 + dp), dy - 10 * t % 40, dr, 0, 2 * math.pi); c.fill()
    # speech bubbles
    hx = PX[HERO] + 26 * glance(t)
    if T_HI <= t < T_DROP + 0.1:
        k = smooth((t - T_HI) / 0.35)
        speech(c, hx + 60, 880 + sway, 0.75 * k, (0.92, 0.95, 1.0), 0.95, 0, -1)
    for j, ct in enumerate(CHAT_T):
        u = t - ct
        if 0 <= u < 1.1:
            left = j % 2 == 1                                                # stranger answers first
            sx = PX[HERO] + 40 if not left else PX[STR] - 40
            sx = (PX[STR] - 10) if j % 2 == 0 else (PX[HERO] + 10)
            pop = smooth(u / 0.18) * (1 + 0.12 * math.exp(-u * 10))
            a = clamp((1.1 - u) / 0.35)
            col = (1.0, 0.94, 0.82) if j % 2 else (0.86, 0.97, 0.96)
            speech(c, sx + (1 if j % 2 == 0 else -1) * 30 * u, 875 - 70 * u + sway, 0.85 * pop, col, a, (j % 3) + 1 if j else 0,
                   -1 if j % 2 == 0 else 1)
    c.restore()
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
        d.text((xy[0] + 2, xy[1] + 3), s, font=f, fill=(0, 0, 0, int(200 * a)), anchor="mm")
        d.text(xy, s, font=f, fill=(*fill, int(255 * a)), anchor="mm")


WHITE = (250, 246, 240)
ICE = (175, 210, 255)
GOLD = (255, 214, 120)
PEACH = (255, 210, 180)


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 3.9)
    ctext(d, (540, 360), "Too awkward to", font("Bold", 66), WHITE, h)
    ctext(d, (540, 446), "talk to a stranger?", font("Bold", 66), ICE, h)
    b = win(t, 4.1, 9.8, 0.4, 0.3)
    ctext(d, (540, 350), "Commuters guessed", font("Bold", 56), WHITE, b)
    ctext(d, (540, 430), "under half would chat.", font("Bold", 56), ICE, b)
    a = win(t, 10.2, 14.4, 0.4, 0.4)
    ctext(d, (540, 300), "Everyone they tried did.", font("Bold", 50), WHITE, a)
    ctext(d, (540, 410), "0 rebuffed", font("Bold", 120), GOLD, a)
    a2 = win(t, 11.0, 14.4, 0.4, 0.4)
    ctext(d, (540, 508), "and a happier commute", font("Bold", 42), PEACH, a2)
    p = win(t, 14.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 340), "Say hello first.", font("Bold", 68), WHITE, p)
    ctext(d, (540, 425), "It goes better than you think.", font("Bold", 46), GOLD, p)
    q = win(t, 15.2, 20.1, 0.6, 0.1)
    ctext(d, (540, 1452), "Epley & Schroeder, 2014 · Chicago train commuters", font("Regular", 27), WHITE, q)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "stranger_silent.mp4"
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
