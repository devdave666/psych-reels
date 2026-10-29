"""Soundtrack for progress_reel: C-major build (music2, shift -2), vi V IV I then drop on I - V - IV - ii/V - I.
Lantern chimes on every ignition, effects locked to the picture. Usage: python progress_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import progress_reel as fr
import music2
from synth import SR, impact, thump, tinkle, tock, whoosh

music2.configure(
    shift=-2,
    prog=[["Bm"], ["A"], ["G"], ["D"], ["Em", "A"], ["D"], ["A"], ["G"], ["Em", "A"], ["D"]],
    melody={
        6: [(0, 78, 1), (1, 81, 1), (2, 86, 2)],
        7: [(0, 85, 1.5), (1.5, 81, 0.5), (2, 88, 2)],
        8: [(0, 86, 1), (1, 83, 1), (2, 78, 1), (3, 81, 1)],
        9: [(0, 86, 1), (1, 83, 1), (2, 85, 1), (3, 81, 1)],
        10: [(0, 78, 0.5), (0.5, 81, 0.5), (1, 86, 3)],
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
for r in range(10):                                                          # lanterns drifting in, row by row
    place(tinkle(hz(81 + (r * 2) % 12), 0.06), 0.6 + 0.28 * r, np.sin(r) * 0.5, 0.35)
place(thump(0.3, 70, 45, 0.15, 0.03), 8.7, 0, 0.5)                           # breath before the drop
place(whoosh(1.3, 250, 3200, 0.9, 0.3, 0.8), 8.75, 0, 0.9)
place(impact(1.0, heavy=True), fr.T_DROP, 0, 0.5)
scale = [81, 83, 85, 88, 90, 93, 95, 97]                                     # D-major pentatonic-ish chimes
for k, tg in enumerate(fr.IGN_T):                                            # one soft chime per lantern lighting up
    place(tinkle(hz(scale[(k * 3) % len(scale)] + 12 * (k // 40)), 0.05), tg, np.sin(k * 1.7) * 0.7, 0.45)
    if k % 4 == 0:
        place(thump(0.1, 110, 55, 0.04, 0.02), tg, 0, 0.35)
place(tock(900, 0.12), fr.T_NUM, 0, 0.8)
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
out = sys.argv[1] if len(sys.argv) > 1 else "progress_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
