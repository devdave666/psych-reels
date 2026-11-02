"""Soundtrack for reappraisal_reel: Ab-major build (music2, shift 6), I iii IV V then Bm/A; drop on I - V - IV - iii/V - I.
Heartbeat thumps on every beat of the intro, rocket whooshes and bursts locked to the fireworks, counter ticks to 81%.
Usage: python reappraisal_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import reappraisal_reel as fr
import music2
from synth import SR, dust, impact, thump, tinkle, tock, whoosh

music2.CH["F#m"] = (61, 66, 69)
music2.ROOT["F#m"] = 42
music2.configure(
    shift=6,
    prog=[["D"], ["F#m"], ["G"], ["A"], ["Bm", "A"], ["D"], ["A"], ["G"], ["F#m", "A"], ["D"]],
    melody={
        6: [(0, 86, 1.5), (1.5, 85, 0.5), (2, 81, 2)],
        7: [(0, 81, 1), (1, 85, 1), (2, 88, 2)],
        8: [(0, 86, 1), (1, 83, 1), (2, 79, 1), (3, 83, 1)],
        9: [(0, 85, 1), (1, 81, 1), (2, 85, 1), (3, 88, 1)],
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
for k in range(1, 18):                                                       # heartbeat lub-dub on each beat of the intro
    tb = 0.5 * k
    gain = 0.35 + 0.35 * min(1.0, tb / 9.0)
    place(thump(0.22, 95, 48, 0.12, 0.03), tb, 0, gain)
    place(thump(0.18, 80, 45, 0.10, 0.03), tb + 0.16, 0, gain * 0.6)
place(tock(430, 0.12), 3.8, 0, 0.7)                                          # "Calm down."
place(tinkle(hz(88), 0.08), 6.9, 0, 0.9)                                     # "I am excited."
place(tinkle(hz(93), 0.08), 7.05, 0, 0.9)
place(whoosh(1.0, 250, 3200, 0.9, 0.3, 0.8), 8.75, 0, 0.8)                   # build into the drop
for k, (lt, rx, by, sz) in enumerate(fr.ROCKETS):                            # rockets and bursts
    pan = (rx - 540) / 540 * 0.7
    place(whoosh(fr.RISE, 500, 3600, 1.2, 0.3, 0.7), lt, pan, 0.6)
    tb = lt + fr.RISE
    place(impact(0.7 * sz, heavy=(k == 0)), tb, pan, 0.45 if k else 0.5)
    place(dust(0.7, 0.25), tb, pan, 0.7)
    place(tinkle(hz(88 + 4 * (k % 3)), 0.07), tb + 0.05, pan, 0.8)
for k in range(15):                                                          # counter ticks 0 -> 81
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
out = sys.argv[1] if len(sys.argv) > 1 else "reappraisal_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
