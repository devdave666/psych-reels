"""Soundtrack for selfdistance_reel: Bb-major build (music2, shift -4), IV I ii V then drop on I - IV - ii - V/I.
Thunder locked to the lightning flashes, a pull-back sweep at the drop, chimes on the sunrise and the counter.
Usage: python selfdistance_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import selfdistance_reel as fr
import music2
from synth import SR, impact, rumble, thump, tinkle, tock, whoosh

music2.configure(
    shift=-4,
    prog=[["G"], ["D"], ["Em"], ["A"], ["Bm", "A"], ["D"], ["G"], ["Em"], ["G", "A"], ["D"]],
    melody={
        6: [(0, 78, 1), (1, 81, 1), (2, 85, 2)],
        7: [(0, 86, 1.5), (1.5, 83, 0.5), (2, 79, 1), (3, 83, 1)],
        8: [(0, 83, 1), (1, 86, 1), (2, 88, 2)],
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
for k, ft in enumerate(fr.FLASH):                                            # thunder with each lightning flash
    place(rumble(1.4, 0.5), ft + 0.05, 0, 0.7)
    place(thump(0.5, 90, 40, 0.2, 0.05), ft, 0, 0.6)
place(tock(430, 0.12), 3.8, 0, 0.7)                                          # "Don't ask"
place(tinkle(hz(88), 0.08), 6.9, 0, 0.9)                                     # "Ask"
place(tinkle(hz(93), 0.08), 7.05, 0, 0.9)
place(thump(0.3, 70, 45, 0.15, 0.03), 8.7, 0, 0.5)                           # breath before the drop
place(whoosh(1.3, 250, 3200, 0.9, 0.3, 0.8), 8.75, 0, 0.9)
place(impact(1.0, heavy=True), fr.T_DROP, 0, 0.5)
place(whoosh(3.6, 3000, 300, 0.8, 0.3, 0.7), fr.T_DROP + 0.1, 0, 0.7)        # camera pulling back
for k, tg in enumerate([10.6, 11.0, 11.4, 11.8, 12.2]):                      # sunrise chimes
    place(tinkle(hz(81 + 4 * (k % 3) + 12 * (k // 3)), 0.06), tg, np.sin(k * 2) * 0.5, 0.5)
n_ticks = 15
for k in range(n_ticks):                                                     # counter ticks 0 -> 585
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
out = sys.argv[1] if len(sys.argv) > 1 else "selfdistance_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
