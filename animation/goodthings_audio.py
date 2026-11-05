"""Soundtrack for goodthings_reel: key of Ab... shift -5 (music2), G Bm D A Em/A build, drop on D Bm G A Em/A D.
Orb whooshes + landing chimes, drop impact, firefly tinkles, counter ticks, all locked to the picture.
Usage: python goodthings_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import goodthings_reel as fr
import music2
from synth import SR, dust, impact, thump, tinkle, tock, whoosh

music2.configure(
    shift=-5,
    prog=[["G"], ["Bm"], ["D"], ["A"], ["Em", "A"], ["D"], ["Bm"], ["G"], ["Em", "A"], ["D"]],
    melody={
        6: [(0, 78, 1), (1, 81, 1), (2, 86, 2)],
        7: [(0, 83, 1.5), (1.5, 81, 0.5), (2, 78, 2)],
        8: [(0, 79, 1), (1, 83, 1), (2, 86, 2)],
        9: [(0, 88, 1), (1, 85, 1), (2, 81, 1), (3, 85, 1)],
        10: [(0, 81, 0.5), (0.5, 85, 0.5), (1, 86, 3)],
    })

total = int((fr.DUR + 0.5) * SR)
L = np.zeros(total); R = np.zeros(total)


def place(sig, s, pan=0.0, gain=1.0):
    a = (pan + 1) * math.pi / 4
    i = int(s * SR)
    m = min(len(sig), total - i)
    if m > 0:
        L[i:i + m] += sig[:m] * math.cos(a) * gain
        R[i:i + m] += sig[:m] * math.sin(a) * gain


hz = music2.hz
place(tock(520, 0.14), 0.4, 0, 1.0)                                          # hook
place(tock(430, 0.12), 4.1, 0, 0.8)                                          # "Write 3 good things"
place(tinkle(hz(88), 0.08), 7.0, 0, 0.8)                                     # "And why"
for i, (t0, rx, ry) in enumerate(fr.ORBS):                                   # each good thing drops into the jar
    place(whoosh(fr.FALL, 300, 2200, 1.0, 0.3, 0.6), t0, -0.2 + 0.2 * i, 0.55)
    tl = t0 + fr.FALL
    place(tinkle(hz(86 + 4 * i), 0.1), tl, 0, 1.0)
    place(tinkle(hz(98 + 4 * i), 0.07), tl + 0.08, 0.2, 0.8)
    place(thump(0.25, 110, 55, 0.12, 0.03), tl, 0, 0.5)
place(whoosh(1.2, 250, 3400, 0.9, 0.3, 0.8), 8.8, 0, 0.8)                    # build into the drop
place(impact(1.0, heavy=True), fr.T_DROP, 0, 0.55)                           # lid pops, light bursts
place(dust(0.8, 0.25), fr.T_DROP, 0, 0.7)
place(tock(380, 0.12), fr.T_DROP + 0.08, 0.3, 0.8)                           # lid clack
for k in range(14):                                                          # fireflies rising
    place(tinkle(hz(86 + (0, 4, 7, 9, 12, 7, 4)[k % 7]), 0.06), fr.T_DROP + 0.35 + 0.22 * k, -0.6 + 0.19 * (k % 7), 0.55)
for k in range(6):                                                           # months counter 1 -> 6
    place(tock(700 + 60 * k, 0.1), fr.T_NUM + 0.2 * k, 0, 0.55)
place(tock(1100, 0.12), fr.T_NUM + 1.3, 0, 0.8)
place(tinkle(hz(105), 0.12), 14.6, 0, 1.0)                                   # payoff text
place(tinkle(hz(109), 0.1), 14.75, 0, 1.0)

sfx = np.stack([L, R], 1)[: int(fr.DUR * SR)]
mus = music2.render_music()
mus = mus / (np.max(np.abs(mus)) + 1e-9)
mix = mus * 0.62 + sfx * 0.85
mix = np.tanh(1.25 * mix) / np.tanh(1.25)
mix *= 0.70 / np.max(np.abs(mix))
fade = int(0.01 * SR)
mix[:fade] *= np.linspace(0, 1, fade)[:, None]
out = sys.argv[1] if len(sys.argv) > 1 else "goodthings_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
