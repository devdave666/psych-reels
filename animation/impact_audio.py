"""Soundtrack for impact_reel: G major (music2, shift -7).
Build:  D   Bm  Em  A   G/A      (I vi ii V IV/V)  ->  drop:  D   Bm  Em  G/A   D   (I vi ii IV/V I)
A low 'declined' buzz for every red X, rising low-battery beeps (8.6, 9.1, 9.6 s), a whoosh as the cable snakes over,
a click + impact as the plug goes in on the drop, a rising charge chime for each cell (beats 10.5 ... 13.0 s), a bright
chord on the overflow (13.3 s) and sparkles on the payoff text.
Usage: python impact_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import impact_reel as fr
import music2
from synth import SR, dust, impact, thump, tinkle, tock, whoosh

music2.configure(
    shift=-7,
    prog=[["D"], ["Bm"], ["Em"], ["A"], ["G", "A"], ["D"], ["Bm"], ["Em"], ["G", "A"], ["D"]],
    melody={
        6: [(0, 74, 1), (1, 78, 1), (2, 81, 2)],
        7: [(0, 83, 1.5), (1.5, 81, 0.5), (2, 78, 2)],
        8: [(0, 79, 1), (1, 83, 1), (2, 86, 2)],
        9: [(0, 83, 1), (1, 79, 1), (2, 81, 1), (3, 85, 1)],
        10: [(0, 86, 0.5), (0.5, 85, 0.5), (1, 86, 3)],
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


def buzz(f, dur=0.22, gain=0.3):
    """two-tone 'declined' blip, a falling minor third"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    ff = np.where(t < dur / 2, f, f * 0.84)
    sq = np.tanh(3 * np.sin(2 * np.pi * np.cumsum(ff) / SR))
    env = np.minimum(1, t / 0.005) * np.exp(-t / 0.12)
    return gain * sq * env


hz = music2.hz
for i, rt in enumerate(fr.REJ_T):                                             # each "no"
    pan = -0.5 if fr.REJ_XY[i][0] < 540 else 0.5
    place(buzz(330 - 12 * i), rt, pan, 0.55)
    place(thump(0.25, 150, 60, 0.06), rt, pan, 0.35)
place(tock(520, 0.14), 0.3, 0, 0.8)                                           # hook
place(tock(430, 0.12), 4.1, 0, 0.7)                                           # "Call after call"
for k, bt in enumerate(fr.BEEP_T):                                            # low-battery beeps
    place(tinkle(880 + 60 * k, 0.12), bt, 0, 0.8)
place(tinkle(hz(81), 0.1), fr.T_STUDENT, 0.5, 0.9)                            # the student appears
place(whoosh(1.8, 180, 2200, 0.9, 0.3, 0.85), fr.T_CABLE, 0.2, 0.6)          # cable snakes over
place(tock(1500, 0.2), fr.T_DROP - 0.01, 0, 0.9)                              # plug click
place(impact(1.0, heavy=True), fr.T_DROP, 0, 0.55)                            # drop
place(dust(0.9, 0.25), fr.T_DROP, 0, 0.6)
place(tock(900, 0.12), 10.2, 0, 0.6)                                          # first text line
for j, ct in enumerate(fr.CELL_T):                                            # a cell charges on each beat
    place(whoosh(0.45, 500, 3000, 1.2, 0.2, 0.9), ct - 0.45, 0.25 * ((j % 2) * 2 - 1), 0.3)
    place(tinkle(hz(74 + (0, 2, 4, 7, 9, 12)[j]), 0.1), ct, -0.4 + 0.16 * j, 0.75)
    place(tinkle(hz(86 + (0, 2, 4, 7, 9, 12)[j]), 0.06), ct, 0.4 - 0.16 * j, 0.6)
for m in (86, 90, 93, 98):                                                    # overflow: +171%
    place(tinkle(hz(m), 0.11), fr.T_FULL, 0, 1.0)
place(whoosh(0.9, 800, 5000, 1.0, 0.25, 0.3), fr.T_FULL, 0, 0.45)
place(tinkle(hz(105), 0.12), 14.7, 0, 1.0)                                    # payoff text
place(tinkle(hz(110), 0.1), 14.85, 0, 1.0)

sfx = np.stack([L, R], 1)[: int(fr.DUR * SR)]
mus = music2.render_music()
mus = mus / (np.max(np.abs(mus)) + 1e-9)
mix = mus * 0.62 + sfx * 0.85
mix = np.tanh(1.25 * mix) / np.tanh(1.25)
mix *= 0.70 / np.max(np.abs(mix))
fade = int(0.01 * SR)
mix[:fade] *= np.linspace(0, 1, fade)[:, None]
out = sys.argv[1] if len(sys.argv) > 1 else "impact_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
