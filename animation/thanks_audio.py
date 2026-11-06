"""Soundtrack for thanks_reel: shift 8 (Bb major), D Em Bm A build, drop on D G D Em/A D.
Plane whoosh into the drop, window-light tinkles locked to the cascade, text ticks.
Usage: python thanks_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import thanks_reel as fr
import music2
from synth import SR, dust, impact, thump, tinkle, tock, whoosh

music2.configure(
    shift=8,
    prog=[["D"], ["Em"], ["Bm"], ["A"], ["G", "A"], ["D"], ["G"], ["D"], ["Em", "A"], ["D"]],
    melody={
        6: [(0, 78, 1), (1, 81, 1), (2, 86, 2)],
        7: [(0, 83, 1.5), (1.5, 86, 0.5), (2, 79, 2)],
        8: [(0, 86, 1), (1, 85, 1), (2, 81, 2)],
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
place(tock(430, 0.12), 4.1, 0, 0.8)                                          # "You think it'll be awkward"
place(tock(330, 0.12), 6.6, 0, 0.7)                                          # "So you don't send it"
place(whoosh(2.1, 250, 3000, 0.9, 0.3, 0.8), fr.T_LAUNCH, 0, 0.8)            # plane launches, lands on the drop
place(impact(1.0, heavy=True), fr.T_DROP, 0, 0.55)                           # window ignites
place(dust(0.8, 0.25), fr.T_DROP, 0, 0.7)
place(tinkle(hz(93), 0.12), fr.T_DROP + 0.05, 0, 1.0)
times = sorted(w[2] for w in fr.WINS if w[2] is not None)
sel = times[::max(1, len(times) // 16)][:16]
for k, tw in enumerate(sel):                                                 # neighbouring windows light up in a ripple
    place(tinkle(hz(86 + (0, 4, 7, 9, 12, 7, 4)[k % 7]), 0.06), tw, -0.6 + 0.19 * (k % 7), 0.5)
place(tock(900, 0.12), 10.2, 0, 0.7)                                         # "They feel happy"
place(tock(1100, 0.12), 11.4, 0, 0.7)
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
out = sys.argv[1] if len(sys.argv) > 1 else "thanks_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
