"""Soundtrack for awe_reel: Ab major (music2, shift -6). Build on IV V vi I then ii/V; drop on I - IV - ii - IV/V - I.
Hand ticks lock to the racing clock hand (every quarter turn, accelerating), a long whoosh opens the doors on the drop,
an impact + shimmer on it, a tinkle on each of the first eight stars to appear, and slow soft ticks once time has slowed.
Usage: python awe_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import awe_reel as fr
import music2
from synth import SR, dust, impact, tinkle, tock, whoosh

music2.configure(
    shift=-6,
    prog=[["G"], ["A"], ["Bm"], ["D"], ["Em", "A"], ["D"], ["G"], ["Em"], ["G", "A"], ["D"]],
    melody={
        6: [(0, 78, 1), (1, 81, 1), (2, 86, 1.5), (3.5, 85, 0.5)],
        7: [(0, 83, 1), (1, 86, 1), (2, 88, 2)],
        8: [(0, 83, 1), (1, 86, 1), (2, 91, 1), (3, 88, 1)],
        9: [(0, 86, 1), (1, 83, 1), (2, 85, 1), (3, 88, 1)],
        10: [(0, 81, 0.5), (0.5, 86, 0.5), (1, 90, 3)],
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
place(tock(430, 0.12), 4.1, 0, 0.8)                                          # "Tick. Tick. Tick."
place(tock(330, 0.12), 6.6, 0, 0.7)                                          # "So you rush."
for k, tt in enumerate(fr.TICKS):                                            # clock hand, every quarter turn
    place(tock(900 + 12 * k, 0.12), tt, (-0.2 if k % 2 else 0.2), 0.55 + 0.01 * k)
place(whoosh(1.2, 250, 3200, 0.9, 0.3, 0.8), fr.T_DROP - 1.2, 0, 0.8)        # build into the drop
place(impact(1.0, heavy=True), fr.T_DROP, 0, 0.55)                           # doors fly open
place(dust(0.9, 0.25), fr.T_DROP, 0, 0.6)
place(whoosh(2.0, 600, 5000, 0.8, 0.3, 0.5), fr.T_DROP, 0, 0.45)             # expanding ring of light
SCALE = [78, 81, 83, 85, 88, 90, 93, 95]
for k, ts in enumerate(fr.FIRST_STARS):                                      # first stars blinking on
    place(tinkle(hz(SCALE[k] + 12), 0.12), ts, math.sin(k * 2.1) * 0.5, 0.8)
for tt in fr.SLOW_TICKS:                                                     # slow, soft clock now
    place(tock(380, 0.12), tt, 0, 0.6)
place(tinkle(hz(93), 0.12), 10.4, 0, 1.0)                                    # "Feel awe."
place(tinkle(hz(97), 0.1), 10.55, 0, 1.0)
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
out = sys.argv[1] if len(sys.argv) > 1 else "awe_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
