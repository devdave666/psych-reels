"""Soundtrack for savemore_reel: E major (music2, shift -10), an I-V-ii-IV build that lifts into the drop.
Build:  D  A  Em  G  Bm/A   (I V ii IV vi/V)  ->  drop:  D  Bm  Em  G/A  D   (I vi ii IV/V I)
In E major that sounds as E B F#m A C#m/B ... E.
Sound effects follow the picture: a tock on the hook, a soft fill swell as the tube fills (1.0 s), a falling 'bloop' plus a
splash and a rising chime on every raise drop (sm.T_RAISE, 4.0 / 5.5 / 7.0 / 8.5 s, each heard from FALL s before),
an impact and sparkle burst at the surge (10.0 s), and sparkles on the payoff (14.6 s).
Usage: python savemore_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import music2
import savemore_reel as sm
from synth import SR, impact, noise, norm, svf, thump, tinkle, tock, whoosh

music2.configure(
    shift=-10,
    prog=[["D"], ["A"], ["Em"], ["G"], ["Bm", "A"], ["D"], ["Bm"], ["Em"], ["G", "A"], ["D"]],
    melody={
        6: [(0, 74, 1), (1, 76, 0.5), (1.5, 78, 0.5), (2, 81, 2)],          # D5 E5 F#5 A5: the surge
        7: [(0, 83, 1), (1, 81, 1), (2, 78, 1), (3, 74, 1)],                # over Bm: B5 A5 F#5 D5
        8: [(0, 79, 1.5), (1.5, 78, 0.5), (2, 76, 1), (3, 79, 1)],          # over Em: G5 F#5 E5 G5
        9: [(0, 83, 1), (1, 81, 1), (2, 85, 1), (3, 88, 1)],                # G -> A: climbs to E6
        10: [(0, 88, 0.5), (0.5, 85, 0.5), (1, 86, 3)],                     # E6 C#6 D6, home
    })

total = int((sm.DUR + 0.5) * SR)
L = np.zeros(total); R = np.zeros(total)


def place(sig, s, pan=0.0, gain=1.0):
    a = (pan + 1) * math.pi / 4
    i = int(s * SR)
    m = min(len(sig), total - i)
    if m > 0:
        L[i:i + m] += sig[:m] * math.cos(a) * gain
        R[i:i + m] += sig[:m] * math.sin(a) * gain


def bloop(f0, f1, dur=0.5, gain=0.5):
    """A falling drop: a sine glide with a soft attack."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (t / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    env = np.minimum(1, t / 0.02) * np.exp(-t / (dur * 0.5))
    return gain * np.sin(ph) * env


def splash(gain=0.5):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    _, lo, _ = svf(noise(n), 3200 - 2400 * np.minimum(1, t / 0.4), 0.7)
    env = np.minimum(1, t / 0.004) * np.exp(-t / 0.09)
    return gain * norm(lo) * env


hz = music2.hz
place(tock(560, 0.16), 0.25, 0, 1.0)                                       # hook
place(whoosh(1.3, 200, 1200, 0.6, 0.3, 0.6), 0.95, 0, 0.45)                # tube fills to 3.5%
place(tock(760, 0.12), 2.0, 0.4, 1.0)                                      # 3.5% marker
for k, tr in enumerate(sm.T_RAISE):                                        # four raises
    t0 = tr - sm.FALL
    place(tock(620 + 60 * k, 0.12), t0, 0, 1.0)                            # counter ticks over
    place(bloop(hz(86 + 2 * k), hz(74 + 2 * k), 0.55, 0.35), t0, 0, 1.0)   # drop falls
    place(splash(0.5), tr, 0, 1.0)
    place(thump(0.14, 160, 70, 0.02, 0.02), tr, 0, 0.35)
    place(tinkle(hz((81, 83, 85, 86)[k] + 12), 0.10), tr + 0.08, -0.3 + 0.2 * k, 1.0)

place(whoosh(1.3, 250, 3600, 0.9, 0.3, 0.85), 8.75, 0, 0.9)                # pull into the drop
place(impact(1.0, heavy=True), sm.T_DROP, 0, 0.5)
place(splash(0.6), sm.T_DROP, 0, 1.0)
for k, m in enumerate((74, 78, 81, 86, 90)):                                # sparks: D chord shimmer
    place(tinkle(hz(m + 12), 0.10), sm.T_DROP + 0.05 + 0.07 * k, -0.5 + 0.25 * k, 1.0)
place(tinkle(hz(98), 0.12), 14.6, 0, 1.0)                                   # payoff text
place(tinkle(hz(102), 0.1), 14.75, 0.2, 1.0)
place(tinkle(hz(105), 0.08), 14.9, -0.2, 1.0)

sfx = np.stack([L, R], 1)[: int(sm.DUR * SR)]
mus = music2.render_music()
mus = mus / (np.max(np.abs(mus)) + 1e-9)
mix = mus * 0.62 + sfx * 0.85
mix = np.tanh(1.25 * mix) / np.tanh(1.25)
mix *= 0.70 / np.max(np.abs(mix))
fade = int(0.01 * SR)
mix[:fade] *= np.linspace(0, 1, fade)[:, None]
out = sys.argv[1] if len(sys.argv) > 1 else "savemore_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
