"""Soundtrack for freshstart_reel: G-major build (music2, re-keyed) with ii-IV-I-V, effects locked to the chalkboard.
Usage: python freshstart_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import freshstart_reel as fr
import music2
from synth import SR, chalk, dust, impact, noise, svf, thump, tinkle, tock, whistle, whoosh

# key of G (shift 5, written in D-major terms): ii IV I V build, then I IV V vi-V and home on I
music2.configure(
    shift=5,
    prog=[["Em"], ["G"], ["D"], ["A"], ["Em", "A"], ["D"], ["G"], ["A"], ["Bm", "A"], ["D"]],
    melody={
        6: [(0, 81, 1), (1, 86, 1), (2, 85, 0.5), (2.5, 86, 0.5), (3, 90, 1)],           # A D C# D F#
        7: [(0, 91, 1.5), (1.5, 90, 0.5), (2, 86, 2)],                                  # G F# D
        8: [(0, 88, 1), (1, 85, 1), (2, 88, 1), (3, 85, 1)],                            # E C# E C#
        9: [(0, 90, 1), (1, 86, 1), (2, 85, 1), (3, 88, 1)],
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
# each scribble: a chalk squeak over its 0.45 s drawing time
for ts, dur, lines in fr.SCRIB:
    place(chalk(dur, 0.2), ts, 0, 1.0)
    place(tock(300, 0.08), ts + dur, 0, 0.6)
place(thump(0.3, 70, 45, 0.15, 0.03), 8.7, 0, 0.5)                           # breath before the wipe
place(whoosh(1.3, 250, 3200, 0.9, 0.3, 0.8), 8.75, 0, 0.9)
place(impact(1.0, heavy=True), fr.T_DROP, 0, 0.5)
for a, b in fr.WIPE:                                                         # three eraser passes
    place(dust(b - a, 0.35), a, 0, 1.0)
    place(whoosh(b - a, 1800, 700, 1.0, 0.25, 0.4), a, 0, 0.6)
for tb, k in zip(fr.BARS_T, range(3)):                                       # bar steps: chimes up the scale
    place(thump(0.12, 120, 60, 0.05, 0.02), tb, 0, 0.5)
    place(tinkle(hz((93, 97, 100)[k]), 0.1), tb, 0, 1.0)
place(tock(900, 0.12), fr.T_NUM, 0, 0.8)
place(chalk(0.4, 0.2), 11.5, 0, 0.8)
rng = np.random.default_rng(9)
for tf in fr.T_FIRE:                                                         # chalk fireworks
    place(whistle(0.35, 700, 2400, 0.06), tf - 0.35, rng.uniform(-0.5, 0.5), 1.0)
    place(thump(0.5, 90, 40, 0.2, 0.05), tf, 0, 0.55)
    for q in range(14):
        c = svf(noise(int(0.04 * SR)), np.full(int(0.04 * SR), rng.uniform(2500, 6000)), 1.0)[0]
        place(c / (np.max(np.abs(c)) + 1e-9) * np.exp(-np.arange(len(c)) / SR / 0.01), tf + 0.05 + rng.uniform(0, 0.7), rng.uniform(-0.8, 0.8), 0.14)
place(tinkle(hz(98), 0.12), 14.6, 0, 1.0)                                    # payoff text
place(tinkle(hz(105), 0.1), 14.75, 0, 1.0)
k = 0
while fr.HOP_T0 + 0.5 * k < fr.DUR:                                          # celebration hops on the beat
    place(thump(0.12, 110, 55, 0.05, 0.02), fr.HOP_T0 + 0.5 * k, 0, 0.4)
    k += 1

sfx = np.stack([L, R], 1)[: int(fr.DUR * SR)]
mus = music2.render_music()
mus = mus / (np.max(np.abs(mus)) + 1e-9)
mix = mus * 0.62 + sfx * 0.85
mix = np.tanh(1.25 * mix) / np.tanh(1.25)
mix *= 0.70 / np.max(np.abs(mix))
fade = int(0.01 * SR)
mix[:fade] *= np.linspace(0, 1, fade)[:, None]
out = sys.argv[1] if len(sys.argv) > 1 else "freshstart_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
