"""'Same goal. Different system.' - split-screen psychology reel (1080x1920, 18 s).

Top lane (violet): waits until it feels right. Bottom lane (amber): decided the "when" in advance (an if-then plan).
Lesson: implementation intentions (Gollwitzer & Sheeran, 2006; 94 tests, d ~ 0.65 on goal attainment).

Usage: python higher_being_reel.py out_silent.mp4      render the video
       python higher_being_reel.py stills 1.0 5.0 ...   write still PNGs (no blur) for checking
"""
import math
import subprocess
import sys
from pathlib import Path

import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import stickrig as sr
from stickrig import clamp, smooth

W, H, FPS, DUR = 1080, 1920, 30, 18.0
SUB, SHUTTER = 4, 0.5
LW, LH = 1080, 760
LANE_Y = (230, 1010)                      # top lane = violet, bottom lane = amber
AMBER = (1.0, 0.69, 0.13)
VIOLET = (0.66, 0.52, 1.0)
CREAM = (245, 240, 230)
CHARCOAL = (26, 26, 26)
GOLD = (222, 178, 110)
GOAL = 1900.0
ZOOM0 = 1.2
FONTS = Path(__file__).resolve().parent.parent / "fonts"

# ---------------------------------------------------------------- story timeline (seconds)
T_BELL = 1.5                               # amber's trigger: the alarm rings
AMBER_GO = 1.8
AMBER_BUZZ = [4.7, 5.1, 5.5, 5.9, 6.3]     # phone buzzes as amber walks past it
AMBER_PHONE_X = 1050.0
VIO_PHONE_BUZZ = [3.4, 3.9, 4.4]
VIO_PHONE_X = 170.0
T_SIT0, T_SIT1 = 3.5, 5.6
T_SURGE = 5.5
T_SPRINT = 5.7
T_DRAIN = 6.4
OUTRO = 12.6

DT = 1 / 480
N = int((DUR + 0.5) / DT)
TS = np.arange(N) * DT


def bump(t, c, w):
    return math.exp(-((t - c) / w) ** 2)


def sim_amber():
    xs = np.zeros(N); vs = np.zeros(N)
    x = 0.0
    for i in range(N):
        t = TS[i]
        v = min(280 * smooth((t - AMBER_GO) / 0.7) * (1 - 0.3 * bump(t, 5.7, 0.5)), 3.2 * (GOAL - x))
        x += v * DT
        xs[i], vs[i] = x, v
    return xs, vs


def sim_violet():
    xs = np.zeros(N); vs = np.zeros(N)
    x = 0.0
    for i in range(N):
        t = TS[i]
        v = 430 * smooth((t - T_SPRINT) / 0.5) * (1 - smooth((t - T_DRAIN) / 2.0))
        x += v * DT
        xs[i], vs[i] = x, v
    return xs, vs


AX, AV = sim_amber()
VX, VV = sim_violet()
T_ARR = float(TS[np.argmax(GOAL - AX < 10)])


def ax_(t): return float(np.interp(t, TS, AX))
def av_(t): return float(np.interp(t, TS, AV))
def vx_(t): return float(np.interp(t, TS, VX))
def vv_(t): return float(np.interp(t, TS, VV))


def motivation(t):
    pre = 0.5 * smooth((t - 0.8) / 2.0) + (0.05 * math.sin(t * 7.0) if t > 1.5 else 0.0)
    drop = 1 - 0.85 * smooth((t - T_SIT0) / 0.4)
    surge = 0.95 * smooth((t - T_SURGE) / 0.5) * (1 - smooth((t - T_DRAIN) / 2.0))
    return clamp((pre * drop if t < T_SURGE else 0.1) + surge)


# ---------------------------------------------------------------- poses
def amber_air(t):
    u = (t - T_ARR - 0.1) / 0.6
    if 0 <= u < 2:
        f = u % 1
        return 110.0 * 4 * f * (1 - f)
    return 0.0


def amber_pose(t):
    x, v = ax_(t), av_(t)
    walk = clamp(v / 280) * (1 - smooth((t - T_ARR + 0.3) / 0.3))
    hop = clamp(amber_air(t) / 20) * smooth((t - T_ARR) / 0.1)
    cheer = smooth((t - (T_ARR + 1.4)) / 0.3)
    idle = max(0.0, 1 - walk - hop - cheer)
    return sr.blend([(walk, sr.walk_pose(x / 230, 0.55, 0.9, 0.5, 0.08)), (hop, sr.HOP), (cheer, sr.CHEER),
                     (idle, sr.idle_pose(t))])


def violet_pose(t):
    x, v = vx_(t), vv_(t)
    sit = smooth((t - T_SIT0) / 0.3) * (1 - smooth((t - T_SIT1) / 0.3))
    move = clamp(v / 430)
    fast = clamp((v - 200) / 200)
    ex = smooth((t - 7.4) / 0.6) * (1 - move)
    gait = sr.blend([(1 - fast + 1e-6, sr.walk_pose(x / 230, 0.55, 0.9, 0.5, 0.08)),
                     (fast, sr.walk_pose(x / 170, 0.9, 1.3, 0.9, 0.3))])
    idle = max(0.0, 1 - sit - move - ex)
    return sr.blend([(sit, sr.SIT), (move, gait), (ex, sr.HANDS_ON_KNEES), (idle, sr.idle_pose(t))])


def amber_joints(t): return sr.joints_from(amber_pose(t), ax_(t), amber_air(t))
def violet_joints(t): return sr.joints_from(violet_pose(t), vx_(t), 0.0)


# ---------------------------------------------------------------- cameras (critically damped spring follow)
def sim_cam(xs_fn, vs_fn, wx=3.0):
    xs = np.zeros(N)
    x = xs_fn(0.0) + 110 * vs_fn(0.0) / 300
    vel = 0.0
    for i in range(N):
        t = TS[i]
        tgt = xs_fn(t) + 130.0 * clamp(vs_fn(t) / 300)
        vel += (wx * wx * (tgt - x) - 2 * wx * vel) * DT
        x += vel * DT
        xs[i] = x
    return xs


CAM_X = {"a": sim_cam(ax_, av_), "v": sim_cam(vx_, vv_)}
ZOOM_KEYS = {"a": [(-1, ZOOM0), (0, ZOOM0), (T_ARR - 1.0, ZOOM0), (T_ARR + 0.6, 1.4), (T_ARR + 2.5, 1.35), (30, 1.35)],
             "v": [(-1, ZOOM0), (0, ZOOM0), (5.0, ZOOM0), (6.3, 1.12), (8.5, 1.28), (30, 1.3)]}


def camera(lane, t):
    z = sr.catmull(ZOOM_KEYS[lane], t)[0]
    return float(np.interp(t, TS, CAM_X[lane])), z


# ---------------------------------------------------------------- lane scene
rng = np.random.default_rng(7)
LAYERS = [(d, rng.uniform(0, 1, (n, 2)), r, a)
          for d, n, r, a in [(0.35, 45, 2.2, 0.16), (0.7, 35, 2.6, 0.22), (1.0, 22, 3.2, 0.28)]]
TW, TH = 2600.0, 1500.0


def rrect(c, x, y, w, h, r):
    c.new_sub_path()
    c.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    c.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    c.close_path()


def draw_phone(c, x, t, buzzes, appear=1.0):
    vib = sum(math.exp(-(t - b) / 0.12) * math.sin(2 * math.pi * 38 * (t - b)) for b in buzzes if 0 <= t - b < 0.6)
    glow = max([math.exp(-(t - b) / 0.22) for b in buzzes if t >= b] + [0.0])
    if appear <= 0:
        return
    c.save()
    c.translate(x + vib * 5, 0)
    c.rotate(-0.16)
    if glow > 0.02:
        rg = cairo.RadialGradient(0, -55, 5, 0, -55, 120)
        rg.add_color_stop_rgba(0, 0.55, 0.75, 1.0, 0.35 * glow)
        rg.add_color_stop_rgba(1, 0.55, 0.75, 1.0, 0.0)
        c.set_source(rg)
        c.arc(0, -55, 120, 0, 2 * math.pi)
        c.fill()
    rrect(c, -28, -104, 56, 104, 9)
    c.set_source_rgb(0.1, 0.11, 0.14)
    c.fill_preserve()
    c.set_source_rgba(0.62, 0.68, 0.8, 0.8)
    c.set_line_width(3)
    c.stroke()
    rrect(c, -22, -96, 44, 86, 5)
    c.set_source_rgba(0.55, 0.75, 1.0, 0.22 + 0.7 * glow)
    c.fill()
    c.restore()
    for b in buzzes:                           # notification ripples
        d = t - b
        if 0 <= d < 0.5:
            c.set_source_rgba(0.55, 0.75, 1.0, 0.5 * (1 - d / 0.5))
            c.set_line_width(3)
            c.arc(x, -60, 50 + 90 * d / 0.5, -2.5, -0.64)
            c.stroke()


def draw_goal(c, t):
    G = GOAL + 150.0                           # flag stands just past where amber stops
    c.set_source_rgba(1, 1, 1, 0.5)
    c.set_line_width(5)
    c.move_to(G, 0); c.line_to(G, -270); c.stroke()
    c.set_source_rgba(*AMBER, 0.55)
    c.set_line_width(4)
    c.move_to(G - 60, 0); c.line_to(G + 60, 0); c.stroke()
    hgt = 30 + 190 * smooth((t - T_ARR - 0.05) / 0.8)
    lit = smooth((t - T_ARR) / 0.4)
    c.set_source_rgba(*AMBER, 0.45 + 0.55 * lit)
    c.move_to(G + 3, -270 + 190 - hgt + 0)
    c.line_to(G + 3 + 105, -270 + 190 - hgt + 32)
    c.line_to(G + 3, -270 + 190 - hgt + 64)
    c.close_path()
    c.fill()
    dt = t - T_ARR
    if 0 <= dt <= 0.9:                         # arrival ring
        e = 1 - (1 - dt / 0.9) ** 3
        c.save()
        c.translate(G, 0); c.scale(1, 0.12)
        c.arc(0, 0, 40 + 420 * e, 0, 2 * math.pi)
        c.restore()
        c.set_source_rgba(*AMBER, 0.6 * (1 - dt / 0.9))
        c.set_line_width(4)
        c.stroke()
    if 0 <= dt <= 2.6:                         # confetti
        for k in range(20):
            ang = math.pi / 2 + (k / 19 - 0.5) * 1.5
            sp = 420 + (k % 5) * 70
            px = G + sp * math.cos(ang) * dt * 0.7
            py = min(0.0, -sp * math.sin(ang) * dt + 0.5 * 900 * dt * dt)
            c.set_source_rgba(*(AMBER if k % 2 else (0.96, 0.94, 0.9)), 1 - dt / 2.6)
            c.arc(px, py, 6, 0, 2 * math.pi)
            c.fill()


def render_lane(lane, t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, LW, LH)
    c = cairo.Context(surf)
    c.set_source_rgb(0.02, 0.02, 0.028)
    c.paint()
    cx, z = camera(lane, t)
    cy = -(0.30 * LH) / z                       # ground sits at 80% of lane height

    c.save()
    c.translate(LW / 2, LH / 2)
    for depth, pts, rad, alpha in LAYERS:
        c.set_source_rgba(1, 1, 1, alpha)
        for px, py in pts:
            u = ((px * TW - cx * depth + TW / 2) % TW) - TW / 2
            v = ((py * TH + TH / 2) % TH) - TH / 2
            s = z ** (0.6 + 0.4 * depth)
            c.arc(u * s, (v * 0.5 - 40) * s, rad * s, 0, 2 * math.pi)
            c.fill()
    c.restore()

    c.save()
    c.translate(LW / 2, LH / 2)
    c.scale(z, z)
    c.translate(-cx, -cy)
    g = cairo.LinearGradient(cx - 900, 0, cx + 900, 0)
    g.add_color_stop_rgba(0, 1, 1, 1, 0.0)
    g.add_color_stop_rgba(0.5, 1, 1, 1, 0.38)
    g.add_color_stop_rgba(1, 1, 1, 1, 0.0)
    c.set_source(g)
    c.set_line_width(3)
    c.move_to(cx - 900, 0); c.line_to(cx + 900, 0); c.stroke()
    first = math.floor((cx - 900) / 160) * 160
    for k in range(0, 13):
        gx = first + k * 160
        c.set_source_rgba(1, 1, 1, max(0.0, 1 - abs(gx - cx) / 900) * 0.3)
        c.move_to(gx, 8); c.line_to(gx, 20); c.stroke()
    c.set_source_rgba(1, 1, 1, 0.35)             # start line
    c.set_line_width(4)
    c.move_to(-70, 0); c.line_to(-70, -60); c.stroke()
    draw_goal(c, t)

    if lane == "a":
        draw_phone(c, AMBER_PHONE_X, t, AMBER_BUZZ)
        j, col, air = amber_joints(t), AMBER, amber_air(t)
    else:
        slide = smooth((t - 2.6) / 0.5)
        if slide > 0:
            draw_phone(c, VIO_PHONE_X + 520 * (1 - slide), t, VIO_PHONE_BUZZ)
        j, col, air = violet_joints(t), VIOLET, 0.0
    sr.draw_shadow(c, j["hip"][0], air)
    sr.draw_figure(c, j, col, 11)
    c.restore()
    buf = np.frombuffer(surf.get_data(), np.uint8).reshape(LH, LW, 4)
    return buf[:, :, 2::-1].astype(np.float32)


# ---------------------------------------------------------------- HUD / text (PIL, composited after motion blur)
def font(name, size):
    return ImageFont.truetype(str(FONTS / f"IBMPlexSerif-{name}.ttf"), size)


F = {k: font(n, s) for k, (n, s) in dict(cap=("Bold", 52), label=("Bold", 27), tag=("Regular", 31), tagb=("Bold", 29),
                                           small=("Regular", 22), big=("Bold", 84), bigi=("BoldItalic", 92),
                                           src=("Regular", 29), handle=("Regular", 30)).items()}


def win(t, t0, t1, fi=0.2, fo=0.25):
    return clamp((t - t0) / fi) * clamp((t1 - t) / fo)


def ctext(d, xy, s, f, fill, a):
    if a > 0.01:
        d.text(xy, s, font=f, fill=(*fill, int(255 * a)), anchor="mm")


def pill(d, x, y, head, body, t, t0, t1, outline):
    a = win(t, t0, t1)
    if a <= 0.01:
        return
    pad, gap = 20, 12
    hw = d.textlength(head, font=F["tagb"])
    bw = d.textlength(body, font=F["tag"])
    w = pad * 2 + hw + gap + bw
    y = y + 14 * (1 - smooth((t - t0) / 0.2))
    d.rounded_rectangle((x, y, x + w, y + 58), 14, fill=(*CREAM, int(235 * a)), outline=(*outline, int(255 * a)), width=3)
    d.text((x + pad, y + 29), head, font=F["tagb"], fill=(*GOLD[:2], 40, int(255 * a)) if False else (160, 112, 28, int(255 * a)), anchor="lm")
    d.text((x + pad + hw + gap, y + 29), body, font=F["tag"], fill=(*CHARCOAL, int(255 * a)), anchor="lm")


CAPTIONS = [(0.3, 3.0, "Same goal. Same start."), (3.0, 6.9, "Then a distraction shows up."),
            (6.9, 9.8, "Willpower spikes. Then it fades."), (9.8, 12.3, "A plan doesn't need a mood.")]


def hud(t, dim):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for t0, t1, s in CAPTIONS:
        ctext(d, (W / 2, 120), s, F["cap"], CREAM, win(t, t0, t1))
    lane_cols = {0: VIOLET, 1: AMBER}
    labels = {0: "WAITS UNTIL IT FEELS RIGHT", 1: "DECIDES THE WHEN IN ADVANCE"}
    for i in (0, 1):
        y0 = LANE_Y[i]
        col = tuple(int(255 * v) for v in lane_cols[i])
        d.line((0, y0, W, y0), fill=(*GOLD, 90), width=2)
        d.text((40, y0 + 34), labels[i], font=F["label"], fill=(*col, int(255 * dim)), anchor="lm")
        px = (vx_(t) if i == 0 else ax_(t)) / GOAL                 # progress track
        d.line((40, y0 + 78, W - 40, y0 + 78), fill=(255, 255, 255, int(70 * dim)), width=3)
        d.ellipse((40 + px * (W - 80) - 9, y0 + 69, 40 + px * (W - 80) + 9, y0 + 87), fill=(*col, int(255 * dim)))
        fx = W - 40
        d.polygon([(fx, y0 + 52), (fx + 22, y0 + 60), (fx, y0 + 68)], fill=(*GOLD, int(255 * dim)))
        d.line((fx, y0 + 52, fx, y0 + 80), fill=(*GOLD, int(255 * dim)), width=3)
    d.line((0, LANE_Y[1] + LH, W, LANE_Y[1] + LH), fill=(*GOLD, 90), width=2)

    vy, ay = LANE_Y[0], LANE_Y[1]
    m = motivation(t)                                                # motivation meter (violet lane)
    d.text((40, vy + 112), "MOTIVATION", font=F["small"], fill=(255, 255, 255, int(150 * dim)), anchor="lm")
    d.rounded_rectangle((40, vy + 132, 380, vy + 150), 8, fill=(255, 255, 255, int(40 * dim)))
    if m > 0.01:
        d.rounded_rectangle((40, vy + 132, 40 + 340 * m, vy + 150), 8, fill=(*[int(255 * v) for v in VIOLET], int(255 * dim)))
    pill(d, 40, vy + 190, "SOON", "I'll start when I feel ready.", t, 0.6, 3.3, (170, 133, 255))
    pill(d, 40, vy + 190, "NOW", "I'm motivated!", t, 5.5, 6.7, (170, 133, 255))
    pill(d, 40, vy + 190, "AND", "it's gone.", t, 8.6, 12.4, (170, 133, 255))

    pill(d, 40, ay + 120, "IF", "the alarm rings,", t, 0.6, 3.2, (255, 176, 33))
    pill(d, 40, ay + 188, "THEN", "shoes on. Go.", t, 1.1, 3.2, (255, 176, 33))
    pill(d, 40, ay + 120, "IF", "my phone buzzes,", t, 4.6, 7.6, (255, 176, 33))
    pill(d, 40, ay + 188, "THEN", "keep walking.", t, 5.1, 7.6, (255, 176, 33))

    a_bell = win(t, 0.8, 2.7)                                        # the trigger: a bell
    if a_bell > 0.01:
        bx, by = 940, ay + 170
        sw = math.sin((t - T_BELL) * 40) * 9 * bump(t, T_BELL + 0.2, 0.35) if t > T_BELL else 0.0
        gc = (*GOLD, int(255 * a_bell * dim))
        d.pieslice((bx - 36, by - 40, bx + 36, by + 32), 180, 360, fill=gc)
        d.rectangle((bx - 36, by - 4, bx + 36, by + 20), fill=gc)
        d.rounded_rectangle((bx - 46, by + 14, bx + 46, by + 26), 5, fill=gc)
        d.ellipse((bx - 6 + sw, by + 28, bx + 6 + sw, by + 40), fill=gc)
        d.ellipse((bx - 5, by - 52, bx + 5, by - 42), fill=gc)
        if T_BELL <= t < T_BELL + 0.6:
            u = (t - T_BELL) / 0.6
            for rr in (58, 80):
                ra = int(200 * (1 - u) * a_bell)
                d.arc((bx - rr * (0.5 + u * 0.6), by - rr * (0.5 + u * 0.6), bx + rr * (0.5 + u * 0.6), by + rr * (0.5 + u * 0.6)),
                      200, 340, fill=(*GOLD, ra), width=3)

    ca = win(t, OUTRO + 0.3, 14.6)                                   # outro cards
    ctext(d, (W / 2, H / 2 - 60), "Motivation is a mood.", F["big"], CREAM, ca)
    cb = win(t, 14.6, 18.0, 0.3, 0.3)
    if cb > 0.01:
        ctext(d, (W / 2, H / 2 - 190), "Decide the", F["big"], CREAM, cb)
        ctext(d, (W / 2, H / 2 - 80), "when", F["bigi"], GOLD, cb)
        ctext(d, (W / 2, H / 2 + 30), "in advance.", F["big"], CREAM, cb)
        ctext(d, (W / 2, H / 2 + 170), "If-then plans: a medium-to-large effect on goal attainment", F["src"], CREAM, cb * 0.75)
        ctext(d, (W / 2, H / 2 + 215), "94 tests  |  Gollwitzer & Sheeran, 2006", F["src"], GOLD, cb * 0.9)
    ctext(d, (W / 2, H - 80), "@the_higher_being", F["handle"], GOLD, 0.85)
    return ov


def compose(lane_v, lane_a, t):
    frame = np.empty((H, W, 3), np.float32)
    frame[:] = (3.5, 3.5, 5.0)
    dim = 1 - 0.8 * smooth((t - OUTRO) / 0.6)
    for i, lane in enumerate((lane_v, lane_a)):
        frame[LANE_Y[i]:LANE_Y[i] + LH] = lane * dim
    img = Image.fromarray(frame.clip(0, 255).astype(np.uint8)).convert("RGBA")
    img.alpha_composite(hud(t, dim))
    return img.convert("RGB")


def render_still(t):
    return compose(render_lane("v", t), render_lane("a", t), t)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "higher_being_silent.mp4"
    if out == "stills":
        for s in sys.argv[2:]:
            render_still(float(s)).save(f"still_{float(s):05.2f}.png")
        return
    n = int(DUR * FPS)
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-c:v", "libx264", "-crf", "15", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)
    for f in range(n):
        t0 = f / FPS
        accv = np.zeros((LH, LW, 3), np.float32); acca = np.zeros_like(accv)
        for s in range(SUB):
            ts = max(0.0, t0 + ((s + 0.5) / SUB - 0.5) * SHUTTER / FPS)
            accv += render_lane("v", ts); acca += render_lane("a", ts)
        ff.stdin.write(np.asarray(compose(accv / SUB, acca / SUB, t0)).tobytes())
        if f % 60 == 0:
            print("frame", f, "/", n, flush=True)
    ff.stdin.close(); ff.wait()
    print("done", out, n, "frames")


if __name__ == "__main__":
    print("amber arrives %.2fs; violet stops at x=%.0f (%.0f%% of the way)" % (T_ARR, VX[-1], 100 * VX[-1] / GOAL))
    main()
