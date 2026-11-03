"""Soundtrack for walking_reel: B-major build (music2, shift -3), vi IV ii V then IV/V; drop on I - vi - IV - ii/V - I.
Soft swirl whooshes for the scribble, a tinkle per pale idea, a rising whoosh into the drop, an impact on it, then a tinkle
climbing a major scale on each of the six idea pops and ticks while the counter climbs 1.0x -> 2.0x.
Usage: python walking_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import walking_reel as fr
import music2
from synth import SR, dust, impact, thump, tinkle, tock, whoosh

music2.configure(
    shift=-3,
    prog=[["Bm"], ["G"], ["Em"], ["A"], ["G", "A"], ["D"], ["Bm"], ["G"], ["Em", "A"], ["D"]],
    melody={
        6: [(0, 86, 1), (1, 85, 0.5), (1.5, 86, 0.5), (2, 90, 2)],
        7: [(0, 90, 1.5), (1.5, 88, 0.5), (2, 86, 1), (3, 83, 1)],
        8: [(0, 83, 1), (1, 86, 1), (2, 91, 2)],
        9: [(0, 88, 1), (1, 83, 1), (2, 85, 1), (3, 88, 1)],
        10: [(0, 81, 0.5), (0.5, 86, 0.5), (1, 90, 1), (2, 86, 2)],
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
for k in range(8):                                                           # swirl of the scribble, quickening
    ts = 0.8 + 1.2 * k
    place(whoosh(0.9, 300 + 40 * k, 900 + 80 * k, 1.2, 0.25, 0.5), ts, -0.4 if k % 2 else 0.4, 0.35 + 0.04 * k)
for i, ta in enumerate(fr.A_TIMES):                                          # pale ideas appear
    place(tinkle(hz(81 + 2 * i), 0.07), ta, (i - 2.5) * 0.15, 0.8)
place(tock(430, 0.12), 3.8, 0, 0.7)                                          # "Sitting still"
place(tinkle(hz(88), 0.08), 6.9, 0, 0.9)                                     # "Stand up."
place(tinkle(hz(93), 0.08), 7.05, 0, 0.9)
place(whoosh(1.2, 250, 3200, 0.9, 0.3, 0.8), 8.75, 0, 0.8)                   # build into the drop
place(impact(1.0, heavy=True), fr.T_DROP, 0, 0.5)
place(dust(0.7, 0.25), fr.T_DROP, 0, 0.7)
SCALE = [86, 88, 90, 91, 93, 95]
for k, tp in enumerate(fr.POPS):                                             # six ideas light up on the beats
    place(whoosh(fr.FLIGHT, 400, 2400, 1.2, 0.25, 0.7), tp, 0.0, 0.45)
    place(tinkle(hz(SCALE[k]), 0.12), tp, (k - 2.5) * 0.15, 1.0)
    place(tinkle(hz(SCALE[k] + 12), 0.05), tp + 0.06, (k - 2.5) * 0.15, 0.6)
    place(tock(700 + 60 * k, 0.1), fr.T_NUM + 0.3 + 0.5 * k, 0, 0.5)         # counter tick (on the display change)
place(tock(1100, 0.12), 13.1, 0, 0.8)                                        # lands on 2x
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
out = sys.argv[1] if len(sys.argv) > 1 else "walking_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
