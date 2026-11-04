"""Soundtrack for nature_reel: C# major build (music2, shift -1), I ii IV V then IV/V; drop on I - IV - vi - ii/V - I.
Rain hiss for the stormy intro that fades before the drop, a rising whoosh into the drop, an impact on it, then a tinkle
climbing a major scale on each of the six leaf bursts and ticks while the 20-minute ring fills.
Usage: python nature_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import nature_reel as fr
import music2
from synth import SR, dust, impact, tinkle, tock, whoosh

music2.configure(
    shift=-1,
    prog=[["D"], ["Em"], ["G"], ["A"], ["G", "A"], ["D"], ["G"], ["Bm"], ["Em", "A"], ["D"]],
    melody={
        6: [(0, 81, 1), (1, 86, 1), (2, 90, 1.5), (3.5, 88, 0.5)],
        7: [(0, 86, 1), (1, 88, 0.5), (1.5, 86, 0.5), (2, 90, 2)],
        8: [(0, 90, 1), (1, 86, 1), (2, 83, 1), (3, 86, 1)],
        9: [(0, 88, 1), (1, 85, 1), (2, 81, 1), (3, 85, 1)],
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
for k in range(9):                                                           # rain hiss swells, thinning toward the drop
    place(dust(1.3, 0.3), 0.2 + 1.1 * k, -0.3 if k % 2 else 0.3, 0.45 * (1 - 0.06 * k))
for k in range(6):                                                           # distant thunder-ish pulses on the climb
    place(whoosh(0.9, 200 + 30 * k, 600 + 60 * k, 1.2, 0.25, 0.5), 1.0 + 1.5 * k, 0, 0.25)
place(tock(430, 0.12), 3.8, 0, 0.7)                                          # "The stress hormone"
place(tinkle(hz(88), 0.08), 6.9, 0, 0.9)                                     # "Step outside."
place(tinkle(hz(93), 0.08), 7.05, 0, 0.9)
place(whoosh(1.2, 250, 3200, 0.9, 0.3, 0.8), 8.75, 0, 0.8)                   # build into the drop
place(impact(1.0, heavy=True), fr.T_DROP, 0, 0.5)
place(dust(0.7, 0.25), fr.T_DROP, 0, 0.7)
SCALE = [86, 88, 90, 91, 93, 95]
for k, tp in enumerate(fr.POPS):                                             # six leaf bursts on the beats
    place(whoosh(0.5, 500, 2600, 1.2, 0.25, 0.7), tp - 0.05, 0.0, 0.4)
    place(tinkle(hz(SCALE[k]), 0.12), tp, (k - 2.5) * 0.15, 1.0)
    place(tinkle(hz(SCALE[k] + 12), 0.05), tp + 0.06, (k - 2.5) * 0.15, 0.6)
for k in range(12):                                                          # ring ticks while it fills
    place(tock(700 + 40 * k, 0.1), fr.T_NUM + 0.3 + 0.3 * k, 0, 0.45)
place(tock(1100, 0.12), 14.2, 0, 0.8)                                        # ring full
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
out = sys.argv[1] if len(sys.argv) > 1 else "nature_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
