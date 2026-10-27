"""'The spotlight effect' - one embarrassed figure, a crowd that is not really looking. 1080x1920, 20 s.

Gilovich, Medvec & Savitsky (2000): people wearing an embarrassing T-shirt guessed about 46% of observers would notice it;
about 23% actually did.  Dread (3-10 s): a harsh spotlight, a pounding heartbeat, a slow push-in, the crowd's eyes on the figure.
Reality (10 s drop): the spotlight dies, most of the crowd turns away to a spotlight of their own, the figure stands tall.
Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python spotlight_reel.py out_silent.mp4      render
       python spotlight_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
"""
import math
import subprocess
import sys
from pathlib import Path

import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import stickrig as sr
from stickrig import clamp, lerp, smooth

W, H, FPS, DUR = 1080, 1920, 30, 20.0
SUB, SHUTTER = 4, 0.5
CREAM = (245, 240, 230)
RED = (255, 112, 100)
MINT = (130, 238, 208)
GOLD = (255, 205, 90)
FIG = (0.98, 0.95, 0.88)
GY = 0.66 * H                                   # ground line
CX = W / 2
PIVOT = (CX, GY - 170)
FONTS = Path(__file__).resolve().parent.parent / "fonts"
SAFE = (140, 260, 940, 1480)

T_ON, T_DROP = 3.0, 10.0

# heartbeat: lub-dub pairs, getting faster while the dread builds (shared with the audio script)
BEATS = []
_t = T_ON + 0.2
while _t < T_DROP - 0.1:
    BEATS.append(_t)
    _t += lerp(0.95, 0.5, smooth((_t - T_ON) / (T_DROP - T_ON)))


def pulse(t):
    p = 0.0
    for b in BEATS:
        if 0 <= t - b < 0.7:
            p += math.exp(-(t - b) / 0.11)
        if 0 <= t - b - 0.24 < 0.7:
            p += 0.6 * math.exp(-(t - b - 0.24) / 0.11)
    return min(1.4, p)


# ---------------------------------------------------------------- the crowd
rng = np.random.default_rng(11)
CROWD = []
for dy, sc, xs in ((-80, 0.36, (90, 200, 310, 420, 660, 770, 880, 990)),
                   (30, 0.43, (150, 260, 370, 470, 610, 710, 820, 930)),
                   (150, 0.50, (70, 185, 300, 415, 665, 780, 895, 1010))):
    for x in xs:
        CROWD.append(dict(x=x, dy=dy, sc=sc, ph=rng.uniform(0, 6.28)))
NC = len(CROWD)                                  # 24
order = rng.permutation(NC)
for i, k in enumerate(order):
    CROWD[k]["notice"] = i < 11                  # 11 of 24 = 46%: what the figure imagines
    CROWD[k]["stays"] = i < 6                    # 6 of 24 = 25%: roughly the 23% who really noticed
    CROWD[k]["turn"] = 10.25 + 1.45 * (i / (NC - 1))     # staggered, climbing
TURN_T = sorted(c["turn"] for c in CROWD if not c["stays"])

MOTES = [(rng.uniform(CX - 260, CX + 260), rng.uniform(300, GY), rng.uniform(1.0, 2.6), rng.uniform(0, 6.28)) for _ in range(46)]
CONF = [(rng.uniform(0, W), rng.uniform(0, 1), rng.uniform(260, 520), rng.uniform(8, 18), rng.integers(0, 4), rng.uniform(0, 6.28))
        for _ in range(70)]
CONF_COL = [GOLD, MINT, (255, 140, 170), CREAM]
HOP_T0 = 12.2


# ---------------------------------------------------------------- figure
DREAD = sr.P(0.34, (0.32, 0.65), (-0.18, 0.6), (0.55, 2.3), (0.3, 2.45))             # hunched, arms hugging the chest
RELIEF = sr.P(0.0, (0.1, 0.1), (-0.1, 0.1), (0.2, 0.2), (-0.2, 0.2))


def shrink(t):
    return smooth((t - T_ON) / 0.9) * (1 - smooth((t - T_DROP) / 0.5))


def fig_state(t):
    s = shrink(t)
    base = sr.lerp_pose(sr.idle_pose(t), DREAD, s)
    if t > T_DROP:
        base = sr.lerp_pose(base, sr.blend([(0.6, RELIEF), (0.4, sr.STANCE)]), smooth((t - T_DROP) / 0.5))
    air = 0.0
    if t > 10.9:
        cheer = smooth((t - 10.9) / 0.35)
        pose = sr.lerp_pose(base, sr.CHEER, cheer)
        if t > HOP_T0:
            p = ((t - HOP_T0) / 0.5) % 1.0
            h = math.sin(math.pi * p)
            pose = sr.lerp_pose(sr.CHEER, sr.HOP, h)
            air = 100 * h * smooth((t - HOP_T0) / 0.3)
        base = pose
    elif s > 0.01:
        base = dict(base, lean=base["lean"] + 0.015 * s * math.sin(t * 38))           # trembling
    return base, air


def star(c, x, y, r):
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        (c.move_to if i == 0 else c.line_to)(x + rr * math.cos(a), y + rr * math.sin(a))
    c.close_path()


def draw_main(c, t):
    pose, air = fig_state(t)
    sc = lerp(1.0, 0.9, shrink(t))
    c.save()
    c.translate(CX, GY); c.scale(sc, sc)
    j = sr.joints_from(pose, 0.0, air)
    sr.draw_shadow(c, 0.0, air)
    sr.draw_figure(c, j, FIG, 13)
    hx, hy = j["head"]
    c.set_source_rgb(0.1, 0.1, 0.16)                                                   # eyes
    d = 1 if t < T_DROP else 1
    for ex in (14, 3):
        c.arc(hx + d * ex, hy - 5 + (4 * shrink(t)), 4.2, 0, 2 * math.pi); c.fill()
    px = j["hip"][0] + 0.55 * (j["neck"][0] - j["hip"][0])
    py = j["hip"][1] + 0.55 * (j["neck"][1] - j["hip"][1])
    k = smooth((t - 10.4) / 0.4)                                                       # the 'embarrassing' blotch becomes a gold star
    if k > 0:
        c.set_source_rgb(*[lerp(a, b / 255, k) for a, b in zip((0.95, 0.25, 0.4), GOLD)])
        star(c, px, py, 26 + 4 * k)
    else:
        c.set_source_rgb(0.95, 0.25, 0.4)
        c.arc(px, py, 19, 0, 2 * math.pi)
    c.fill()
    if shrink(t) > 0.3:                                                                # sweat
        for q in range(3):
            ph = ((t * 1.7) + q / 3) % 1
            c.set_source_rgba(0.6, 0.85, 1.0, (1 - ph) * min(1, (shrink(t) - 0.3) * 2.5))
            c.arc(hx - 30 - 30 * ph, hy - 24 + 130 * ph * ph - 20 * ph, 7 * (1 - 0.4 * ph), 0, 2 * math.pi); c.fill()
    c.restore()


def draw_crowd_member(c, m, t):
    sc = m["sc"]
    pose = sr.idle_pose(t * 0.8 + m["ph"])
    side = 1 if m["x"] < CX else -1                    # +1: faces right (towards the figure)
    away = smooth((t - m["turn"]) / 0.3) if not m["stays"] else 0.0
    face = side * (1 - 2 * away)
    c.save()
    c.translate(m["x"], GY + m["dy"]); c.scale(sc * side, sc)                         # sc*side mirrors left-side members
    j = sr.joints_from(pose, 0.0, 0.0)
    col = mix3((0.43, 0.5, 0.72), (0.52, 0.72, 0.85), smooth((t - 10) / 0.8))
    sr.draw_figure(c, j, col, 15)
    hx, hy = j["head"]
    glow = m["notice"] and t >= T_ON
    looking = glow and (t < T_DROP or m["stays"])
    if looking:
        pu = 0.7 + 0.3 * pulse(t) if t < T_DROP else 0.8
        c.set_source_rgba(1.0, 0.75 * pu, 0.3, 0.95 if t >= T_ON + 0.2 else 0)
        r_eye = 6.4 + 2.2 * (pulse(t) if t < T_DROP else 0)
    else:
        c.set_source_rgb(0.08, 0.08, 0.14); r_eye = 4.6
    off = face * side                                   # eye direction in the mirrored frame
    if looking:                                         # halo so the staring eyes read at a glance
        hal = (0.5 + 0.5 * (pulse(t) if t < T_DROP else 0.5))
        c.set_source_rgba(1.0, 0.7, 0.25, 0.35 * hal)
        c.arc(hx + off * 9, hy - 4, 26, 0, 2 * math.pi); c.fill()
        c.set_source_rgba(1.0, 0.75 * pu, 0.3, 0.95); r_eye = 8 + 2.5 * (pulse(t) if t < T_DROP else 0)
    for ex in (15, 3):
        c.arc(hx + off * ex, hy - 4 - 4 * away, r_eye, 0, 2 * math.pi); c.fill()
    c.restore()


def draw_tiny_spot(c, m, t):
    k = smooth((t - m["turn"] - 0.15) / 0.5)
    if k <= 0 or m["stays"]:
        return
    sc = m["sc"]; x = m["x"]; yb = GY + m["dy"]
    top = yb - sc * 470
    g = cairo.LinearGradient(0, top, 0, yb)
    g.add_color_stop_rgba(0, 1, 0.95, 0.75, 0.0); g.add_color_stop_rgba(1, 1, 0.95, 0.75, 0.30 * k)
    c.set_source(g)
    c.move_to(x - 8 * sc, top); c.line_to(x + 8 * sc, top)
    c.line_to(x + 85 * sc, yb + 6); c.line_to(x - 85 * sc, yb + 6); c.close_path(); c.fill()
    c.save()
    c.translate(x, yb + 2); c.scale(1, 0.18)
    c.arc(0, 0, 80 * sc * k, 0, 2 * math.pi); c.restore()
    c.set_source_rgba(1, 0.95, 0.75, 0.35 * k); c.fill()


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def zoom(t):
    if t < T_DROP:
        return 1.0 + 0.2 * smooth((t - 2.6) / (T_DROP - 2.6))
    return lerp(1.2, 1.0, smooth((t - T_DROP) / 0.6))


# ---------------------------------------------------------------- scene
def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    R = smooth((t - T_DROP) / 0.7)                                                      # 0 dread -> 1 reality
    dread = shrink(t) if t < T_DROP else 0.0
    pl = pulse(t) if T_ON <= t < T_DROP else 0.0

    g = cairo.LinearGradient(0, 0, 0, GY)                                               # backdrop
    top = mix3(mix3((0.03, 0.03, 0.09), (0.02, 0.0, 0.04), dread), (0.10, 0.20, 0.42), R)
    hor = mix3(mix3((0.09, 0.07, 0.20), (0.05, 0.0, 0.08), dread), (0.22, 0.62, 0.70), R)
    g.add_color_stop_rgb(0, *top); g.add_color_stop_rgb(1, *hor)
    c.set_source(g); c.rectangle(0, 0, W, H); c.fill()
    c.set_source_rgb(*mix3(mix3((0.06, 0.05, 0.11), (0.03, 0.01, 0.05), dread), (0.07, 0.17, 0.24), R))   # stage floor
    c.rectangle(0, GY - 6, W, H - GY + 6); c.fill()
    for k in range(1, 8):                                                               # floor boards
        y = GY - 6 + (k ** 1.7) * 14
        c.set_source_rgba(1, 1, 1, 0.035 * (0.5 + R)); c.set_line_width(2)
        c.move_to(0, y); c.line_to(W, y); c.stroke()

    c.save()
    z = zoom(t)
    c.translate(*PIVOT); c.scale(z, z); c.translate(-PIVOT[0], -PIVOT[1])
    for m in CROWD:
        if m["dy"] < 0:
            draw_crowd_member(c, m, t)
    for m in CROWD:
        if m["dy"] == 30:
            draw_crowd_member(c, m, t)
    # the big spotlight (dread only)
    on = smooth((t - T_ON) / 0.25) * (1 - smooth((t - T_DROP) / 0.22))
    if on > 0:
        wob = 1 + 0.05 * pl
        wid = (300 + 140 * smooth((t - T_ON) / (T_DROP - T_ON))) * wob * (1 - 0.5 * smooth((t - T_DROP) / 0.22))
        gc = cairo.LinearGradient(0, -200, 0, GY)
        gc.add_color_stop_rgba(0, 1, 0.97, 0.85, 0.20 * on); gc.add_color_stop_rgba(1, 1, 0.97, 0.85, (0.50 + 0.12 * pl) * on)
        c.set_source(gc)
        c.move_to(CX - 55, -200); c.line_to(CX + 55, -200)
        c.line_to(CX + wid, GY + 8); c.line_to(CX - wid, GY + 8); c.close_path(); c.fill()
        c.save()
        c.translate(CX, GY + 4); c.scale(1, 0.14)
        c.arc(0, 0, wid * 1.02, 0, 2 * math.pi); c.restore()
        c.set_source_rgba(1, 0.97, 0.85, 0.55 * on); c.fill()
        for x, y, r, ph in MOTES:                                                        # dust in the beam
            yy = y + 18 * math.sin(t * 0.9 + ph)
            hw = 55 + (wid - 55) * (yy + 200) / (GY + 200)
            if abs(x - CX) < hw * 0.9:
                c.set_source_rgba(1, 1, 1, 0.5 * on); c.arc(x + 12 * math.sin(t * 0.6 + ph), yy, r, 0, 2 * math.pi); c.fill()
    for m in CROWD:
        draw_tiny_spot(c, m, t)
    draw_main(c, t)
    for m in CROWD:
        if m["dy"] == 150:
            draw_crowd_member(c, m, t)
    c.restore()

    if t >= T_DROP + 0.5:                                                               # confetti
        for x, ph0, sp, size, ci, ph in CONF:
            tt = t - (T_DROP + 0.5) + ph0 * 3
            y = -40 + (tt * sp) % (H + 80)
            c.save()
            c.translate(x + 40 * math.sin(tt * 1.4 + ph), y); c.rotate(tt * 3 + ph)
            col = CONF_COL[ci]
            c.set_source_rgba(*[v / 255 for v in col], 0.9 * smooth((t - T_DROP - 0.5) / 0.6))
            c.rectangle(-size / 2, -size / 4, size, size / 2); c.fill(); c.restore()

    if dread > 0:                                                                        # vignette + red edge
        vg = cairo.RadialGradient(CX, GY - 200, 380, CX, GY - 200, 1150)
        vg.add_color_stop_rgba(0, 0, 0, 0, 0); vg.add_color_stop_rgba(1, 0.12 * pl, 0, 0.02, 0.78 * dread)
        c.set_source(vg); c.paint()
    fl = t - T_DROP                                                                      # the drop
    if 0 <= fl < 0.4:
        c.set_source_rgba(1, 0.97, 0.88, 0.7 * (1 - fl / 0.4) ** 2); c.paint()
        c.set_source_rgba(1, 0.9, 0.6, 0.7 * (1 - fl / 0.4)); c.set_line_width(6)
        c.arc(CX, GY - 150, 60 + 950 * (1 - (1 - fl / 0.4) ** 3), 0, 2 * math.pi); c.stroke()

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


def ctext(d, xy, s, f, fill, a):
    if a > 0.01:
        d.text((xy[0] + 2, xy[1] + 3), s, font=f, fill=(0, 0, 0, int(160 * a)), anchor="mm")
        d.text(xy, s, font=f, fill=(*fill, int(255 * a)), anchor="mm")


def pct(t):
    if t < 10.3:
        return 46
    return round(lerp(46, 23, smooth((t - 10.3) / 1.3)))


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 2.8)
    ctext(d, (540, 420), "Ever feel like", font("Bold", 64), CREAM, h)
    ctext(d, (540, 505), "everyone's watching?", font("Bold", 64), CREAM, h)
    if t >= 3.2:
        a = clamp((t - 3.2) / 0.4)
        reality = t >= T_DROP
        k = smooth((t - 10.3) / 0.6)
        col = tuple(int(lerp(x, y, k)) for x, y in zip(RED, MINT))
        pop = math.exp(-(t - T_DROP) / 0.18) if reality else 0.0
        label = "R E A L I T Y" if reality else "Y O U   G U E S S"
        ctext(d, (540, 340), label, font("Bold", 38), GOLD, a)
        ctext(d, (540, 480), f"{pct(t)}%", font("Bold", int(240 + 40 * pop)), col, a)
    p = win(t, 12.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 700), "Nobody's watching as", font("Bold", 52), CREAM, p)
    ctext(d, (540, 770), "closely as you think.", font("Bold", 52), CREAM, p)
    ctext(d, (540, 850), "Gilovich, Medvec & Savitsky, 2000", font("Regular", 30), (200, 205, 215), win(t, 13.4, 20.1, 0.6, 0.1) * 0.85)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "spotlight_silent.mp4"
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
