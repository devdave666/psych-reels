"""'Same pulse, new label' - reappraising anxiety as excitement. A racing heartbeat line that stays just as fast, but is
relabelled and then launches fireworks. 1080x1920, 20 s.

Brooks (2014, Journal of Experimental Psychology: General 143(3), 1144-1158), Harvard Business School.  Karaoke study:
people sang "Don't Stop Believin'" in front of a stranger and were scored on singing accuracy (0-100%).  Saying out loud
"I am excited" before singing: M = 80.52%; saying nothing: M = 69.27%; saying "I am anxious": M = 52.98%.
Self-reported anxiety and heart rate did not change, only the label (arousal congruency).  Short lab task.
t < 10 s: shaky, cold-blue ECG; at the drop (t = 10 s) the same pulse turns gold and launches fireworks.
Text stays inside the phone safe zone (x 140-940, y 260-1480).

Usage: python reappraisal_reel.py out_silent.mp4      render
       python reappraisal_reel.py stills 1 5 10.5 ...  still PNGs (no blur) with a safe-zone outline
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
T_NUM = 10.2
PERIOD = 0.5                                   # one heartbeat per beat of the music (120 bpm)
BASE_Y = 1290                                  # ECG baseline
HEAD_X = 880
SPEED = 420.0                                  # px per second the trace scrolls
AMP = 330.0
RISE = 0.5
# (launch time, x, burst y, size); the first bursts exactly on the drop. The audio imports this list.
ROCKETS = [(9.5, 540, 800, 1.35), (10.0, 300, 900, 0.9), (10.5, 790, 840, 1.0), (11.5, 420, 960, 0.9),
           (12.0, 700, 760, 1.0), (12.5, 250, 1010, 0.8), (13.5, 560, 880, 1.1), (14.5, 820, 1000, 0.8)]
rng = np.random.default_rng(31)
STARS = [(rng.uniform(0, W), rng.uniform(0, 1100), rng.uniform(0.8, 2.4), rng.uniform(0, 6.28)) for _ in range(70)]
PART = []
for _ in ROCKETS:
    n = 34
    ang = np.linspace(0, 2 * math.pi, n, endpoint=False) + rng.uniform(0, 1)
    spd = rng.uniform(120, 250, n)
    col = [(1.0, 0.85, 0.45), (1.0, 0.55, 0.60), (1.0, 0.95, 0.80)][rng.integers(0, 3)]
    PART.append((ang, spd, col))


def mix3(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def g(u, m, s):
    return math.exp(-((u - m) / s) ** 2)


def ecg(u):                                    # one PQRST complex, u in [0, 1)
    return (0.12 * g(u, 0.15, 0.04) - 0.14 * g(u, 0.27, 0.012) + 1.0 * g(u, 0.30, 0.014)
            - 0.28 * g(u, 0.335, 0.013) + 0.26 * g(u, 0.58, 0.05))


def warm(t):                                   # 0 cold blue .. 1 gold
    if t >= T_DROP:
        return 1.0
    return 0.45 * smooth((t - 7.0) / 2.6)


def trace_y(x, t, tremor):
    s = t - (HEAD_X - x) / SPEED
    u = (s / PERIOD) % 1.0
    return BASE_Y - AMP * ecg(u) + tremor * (math.sin(x * 0.9 + t * 31) * 5 + math.sin(x * 2.3 - t * 47) * 3)


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    wm = warm(t)
    post = smooth((t - T_DROP) / 1.5) if t >= T_DROP else 0.0
    # sky
    sky = cairo.LinearGradient(0, 0, 0, H)
    sky.add_color_stop_rgb(0, *mix3((0.04, 0.04, 0.10), (0.10, 0.05, 0.24), post))
    sky.add_color_stop_rgb(0.6, *mix3((0.08, 0.06, 0.17), (0.34, 0.09, 0.36), post))
    sky.add_color_stop_rgb(1, *mix3((0.11, 0.08, 0.20), (0.85, 0.38, 0.30), post))
    c.set_source(sky); c.paint()
    for sx, sy, sr, sp in STARS:
        c.set_source_rgba(1, 0.95, 0.9, (0.25 + 0.25 * math.sin(t * 1.7 + sp)) * (1 - 0.5 * post))
        c.arc(sx, sy, sr, 0, 2 * math.pi); c.fill()
    glow = cairo.RadialGradient(540, BASE_Y + 40, 20, 540, BASE_Y + 40, 700)
    glow.add_color_stop_rgba(0, 1.0, 0.65, 0.35, 0.55 * post); glow.add_color_stop_rgba(1, 1.0, 0.5, 0.3, 0)
    c.set_source(glow); c.paint()
    # ECG trace: a gradient fades the history to the left
    tremor = 1.0 if t < T_DROP else max(0.0, 1 - (t - T_DROP) / 0.6)
    col = mix3((0.55, 0.72, 0.98), (1.0, 0.82, 0.42), wm)
    if 7.0 <= t < T_DROP:
        col = mix3(col, (1.0, 0.60, 0.70), 0.5)
    c.set_line_join(cairo.LINE_JOIN_ROUND); c.set_line_cap(cairo.LINE_CAP_ROUND)
    for lw, al in ((22, 0.10), (12, 0.18), (5.5, 1.0)):
        gr = cairo.LinearGradient(40, 0, HEAD_X, 0)
        gr.add_color_stop_rgba(0, *col, 0); gr.add_color_stop_rgba(0.55, *col, 0.55 * al); gr.add_color_stop_rgba(1, *col, al)
        c.set_source(gr); c.set_line_width(lw)
        c.move_to(40, trace_y(40, t, tremor))
        for x in range(42, HEAD_X + 1, 2):
            c.line_to(x, trace_y(x, t, tremor))
        c.stroke()
    hy = trace_y(HEAD_X, t, tremor)
    hg = cairo.RadialGradient(HEAD_X, hy, 2, HEAD_X, hy, 60)
    hg.add_color_stop_rgba(0, 1, 1, 1, 0.95); hg.add_color_stop_rgba(0.25, *col, 0.7); hg.add_color_stop_rgba(1, *col, 0)
    c.set_source(hg); c.arc(HEAD_X, hy, 60, 0, 2 * math.pi); c.fill()
    # fireworks
    for i, (lt, rx, by, sz) in enumerate(ROCKETS):
        f = t - lt
        if 0 <= f < RISE:
            k = f / RISE
            y = lerp(BASE_Y, by, 1 - (1 - k) ** 2)
            for j in range(8):
                kk = max(0.0, k - 0.02 * j)
                yy = lerp(BASE_Y, by, 1 - (1 - kk) ** 2)
                c.set_source_rgba(1, 0.9, 0.6, 0.5 * (1 - j / 8)); c.arc(rx + 3 * math.sin(j + t * 20), yy, 5 - 0.4 * j, 0, 2 * math.pi); c.fill()
            c.set_source_rgba(1, 0.97, 0.85, 1); c.arc(rx, y, 6, 0, 2 * math.pi); c.fill()
        tau = f - RISE
        if 0 <= tau < 2.0:
            ang, spd, pc = PART[i]
            life = 1 - tau / 2.0
            fl = cairo.RadialGradient(rx, by, 5, rx, by, 330 * sz)
            fl.add_color_stop_rgba(0, *pc, 0.55 * max(0, 1 - tau / 0.35) ** 2); fl.add_color_stop_rgba(1, *pc, 0)
            c.set_source(fl); c.arc(rx, by, 330 * sz, 0, 2 * math.pi); c.fill()
            for a, sp in zip(ang, spd):
                kd = 2.6
                d = sp * sz * (1 - math.exp(-kd * tau)) / kd * 3.3
                d0 = sp * sz * (1 - math.exp(-kd * max(0, tau - 0.07))) / kd * 3.3
                px, py = rx + d * math.cos(a), by + d * math.sin(a) + 90 * tau * tau
                qx, qy = rx + d0 * math.cos(a), by + d0 * math.sin(a) + 90 * max(0, tau - 0.07) ** 2
                c.set_source_rgba(*pc, life ** 1.3 * (0.6 + 0.4 * math.sin(tau * 40 + a * 7)))
                c.set_line_width(8 * life + 2); c.move_to(qx, qy); c.line_to(px, py); c.stroke(); c.arc(px, py, 5 * life + 1.5, 0, 2 * math.pi); c.fill()
    f2 = t - T_DROP
    if 0 <= f2 < 0.3:
        c.set_source_rgba(1, 0.92, 0.72, 0.38 * (1 - f2 / 0.3) ** 2); c.paint()
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
ROSE = (255, 170, 160)
GOLD = (255, 220, 130)
ICE = (175, 205, 235)


def number(t):
    return int(round(81 * smooth((t - T_NUM) / 1.5)))


def hud(t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    h = win(t, 0.4, 3.5)
    ctext(d, (540, 380), "Heart racing?", font("Bold", 68), ROSE, h)
    ctext(d, (540, 466), "Hands shaking?", font("Bold", 62), WHITE, h)
    b = win(t, 3.8, 6.7, 0.4, 0.3)
    ctext(d, (540, 380), "Don't tell yourself:", font("Bold", 46), ICE, b)
    ctext(d, (540, 456), "“Calm down.”", font("Bold", 62), WHITE, b)
    e = win(t, 6.9, 9.8, 0.4, 0.3)
    ctext(d, (540, 380), "Tell yourself:", font("Bold", 46), ICE, e)
    ctext(d, (540, 456), "“I am excited.”", font("Bold", 62), GOLD, e)
    z = win(t, 10.2, 14.4, 0.3, 0.3)
    ctext(d, (540, 345), "Same pulse.", font("Bold", 68), GOLD, z)
    ctext(d, (540, 415), "New meaning.", font("Bold", 46), WHITE, z)
    if t >= T_NUM:
        ctext(d, (540, 585), f"{number(t)}%", font("Bold", 170), GOLD, win(t, T_NUM, 20.1, 0.2, 0.1))
        ctext(d, (540, 690), "karaoke accuracy", font("Regular", 34), WHITE, win(t, 11.0, 20.1, 0.4, 0.1))
        ctext(d, (540, 740), "vs 53% after saying “I am anxious”", font("Regular", 28), ICE, win(t, 11.4, 20.1, 0.4, 0.1))
    p = win(t, 14.6, 20.1, 0.6, 0.1)
    ctext(d, (540, 300), "Don't calm down.", font("Bold", 54), WHITE, p)
    ctext(d, (540, 365), "Get excited.", font("Bold", 58), ROSE, p)
    q = win(t, 15.2, 20.1, 0.6, 0.1)
    ctext(d, (540, 1440), "Brooks, 2014 · Harvard Business School", font("Regular", 27), WHITE, q)
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
    out = sys.argv[1] if len(sys.argv) > 1 else "reappraisal_silent.mp4"
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
