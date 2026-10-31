"""Soundtrack for mental_contrasting_reel: Eb-major build (music2, shift 1), vi-I-IV-V -> ii-V, drop I - IV - V - vi - I.
Rope-snap plucks locked to the three cuts, a rising sparkle on the dream, a heavy thud when each bag is tied on.
Usage: python mental_contrasting_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import mental_contrasting_reel as fr
import music2
from synth import SR, impact, thump, tinkle, tock, whoosh

music2.configure(
    shift=1,
    prog=[["Bm"], ["D"], ["G"], ["A"], ["Em", "A"], ["D"], ["G"], ["A"], ["Bm", "A"], ["D"]],
    melody={
        6: [(0, 81, 1), (1, 85, 1), (2, 86, 2)],
        7: [(0, 83, 1.5), (1.5, 86, 0.5), (2, 88, 2)],
        8: [(0, 88, 1), (1, 85, 1), (2, 81, 1), (3, 85, 1)],
        9: [(0, 86, 1), (1, 90, 1), (2, 88, 1), (3, 85, 1)],
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
for k, n in enumerate([81, 85, 88, 93]):                                     # sparkle as the dream balloon glows
    place(tinkle(hz(n), 0.1), 3.9 + 0.18 * k, 0.3 * (k % 2 * 2 - 1), 0.9)
for i, tb in enumerate(fr.T_BAG):                                            # bags tied on
    place(thump(0.35, 80, 45, 0.15, 0.03), tb + 0.4, 0, 0.7)
place(tock(430, 0.12), 6.9, 0, 0.6)
place(thump(0.3, 70, 45, 0.15, 0.03), 8.7, 0, 0.5)                           # breath before the drop
place(whoosh(1.3, 250, 3200, 0.9, 0.3, 0.8), 8.75, 0, 0.9)
place(impact(1.0, heavy=True), fr.T_DROP, 0, 0.5)
for k, ts in enumerate(fr.SNAP):                                             # rope snaps + lift
    place(tock(900 + 150 * k, 0.1), ts, 0, 0.9)
    place(tinkle(hz(93 + 4 * k), 0.12), ts + 0.02, 0, 0.8)
    place(whoosh(1.2, 400, 2400, 0.8, 0.3, 0.6), ts + 0.05, 0, 0.5)
for k in range(15):                                                          # counter ticks 0 -> 60
    place(tock(700 + 40 * k, 0.1), fr.T_NUM + 0.1 * k, 0, 0.5)
place(tock(1100, 0.12), fr.T_NUM + 1.5, 0, 0.8)
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
out = sys.argv[1] if len(sys.argv) > 1 else "mental_contrasting_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
