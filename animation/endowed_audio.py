"""Soundtrack for endowed_reel: bright F-major build (music2, re-keyed) plus effects locked to the climb.
Usage: python endowed_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import endowed_reel as er
import music2
from synth import SR, impact, noise, svf, thump, tinkle, tock, whistle, whoosh

# bright, hopeful build (I V vi IV) instead of the uneasy minor opening; lead climbs one scale step per hop, then soars
music2.configure(
    shift=3,
    prog=[["D"], ["A"], ["Bm"], ["G"], ["Em", "A"], ["D"], ["A"], ["Bm"], ["G", "A"], ["D"]],
    melody={
        6: [(0, 69, 1), (1, 74, 1), (2, 76, 1), (3, 78, 1)],                  # A4, then D5 E5 F#5 on the first three landings
        7: [(0, 81, 1), (1, 83, 1), (2, 85, 1), (3, 86, 1)],                  # A5 B5 C#6 D6: the last landings
        8: [(0, 90, 2), (2, 88, 1), (3, 86, 1)],                              # F#6 held while the fireworks go off
        9: [(0, 86, 1), (1, 83, 1), (2, 85, 1), (3, 81, 1)],
        10: [(0, 78, 0.5), (0.5, 81, 0.5), (1, 86, 3)],
    })

total = int((er.DUR + 0.5) * SR)
L = np.zeros(total); R = np.zeros(total)


def place(sig, s, pan=0.0, gain=1.0):
    a = (pan + 1) * math.pi / 4
    i = int(s * SR)
    m = min(len(sig), total - i)
    if m > 0:
        L[i:i + m] += sig[:m] * math.cos(a) * gain
        R[i:i + m] += sig[:m] * math.sin(a) * gain


hz = music2.hz
place(tock(520, 0.14), 0.4, 0, 1.0)                                        # hook
place(tock(780, 0.14), 3.2, 0, 1.0)                                        # counter appears
# light breeze
n = int(er.DUR * SR)
bp, _, _ = svf(noise(n), 900 + 300 * np.sin(2 * np.pi * 0.23 * np.arange(n) / SR), 1.0)
place(bp / (np.max(np.abs(bp)) + 1e-9) * 0.05 * np.minimum(1, np.arange(n) / SR / 2), 0.0, 0, 1.0)

# the first two steps light up: warm chimes (D major in the new key)
place(tinkle(hz(81), 0.12), er.LIT[1], -0.2, 1.0)
place(tinkle(hz(86), 0.12), er.LIT[2], 0.2, 1.0)
place(whoosh(0.5, 400, 2600, 1.2, 0.2, 0.6), er.LIT[1] - 0.05, 0, 0.6)

# landings: soft thud + a chime on the scale degree (the lead handles 10.5-13.5, so these stay light)
for k, (a, b, t0, t1) in enumerate(er.HOPS):
    place(thump(0.12, 120, 60, 0.05, 0.02), t1, 0, 0.5)
    place(tock(500 + 60 * (b - 1), 0.1), t1, 0, 1.0)
    if t1 < 10:
        place(tinkle(hz(81 + 2 * b), 0.09), t1, 0.0, 1.0)
    else:
        place(tinkle(hz(93 + 2 * (b - 4)), 0.05), t1 + 0.01, 0.3 * math.sin(b), 1.0)
place(whoosh(1.4, 250, 3400, 0.9, 0.3, 0.8), 8.7, 0, 0.9)                  # pull into the drop
place(impact(1.0, heavy=True), er.T_DROP, 0, 0.5)

# fireworks: rising whistle, boom, crackle
rng = np.random.default_rng(9)
for tf in er.T_FIRE:
    place(whistle(0.35, 700, 2400, 0.06), tf - 0.35, rng.uniform(-0.5, 0.5), 1.0)
    place(thump(0.5, 90, 40, 0.2, 0.05), tf, 0, 0.55)
    for q in range(14):
        c = svf(noise(int(0.04 * SR)), np.full(int(0.04 * SR), rng.uniform(2500, 6000)), 1.0)[0]
        place(c / (np.max(np.abs(c)) + 1e-9) * np.exp(-np.arange(len(c)) / SR / 0.01), tf + 0.05 + rng.uniform(0, 0.7), rng.uniform(-0.8, 0.8), 0.14)
place(tinkle(hz(98), 0.12), 14.6, 0, 1.0)                                  # payoff text
place(tinkle(hz(105), 0.1), 14.75, 0, 1.0)
k = 0
while er.HOP_T0 + 0.5 * k < er.DUR:                                        # celebration hops on the beat
    place(thump(0.12, 110, 55, 0.05, 0.02), er.HOP_T0 + 0.5 * k, 0, 0.4)
    k += 1

sfx = np.stack([L, R], 1)[: int(er.DUR * SR)]
mus = music2.render_music()
mus = mus / (np.max(np.abs(mus)) + 1e-9)
mix = mus * 0.62 + sfx * 0.85
mix = np.tanh(1.25 * mix) / np.tanh(1.25)
mix *= 0.70 / np.max(np.abs(mix))
fade = int(0.01 * SR)
mix[:fade] *= np.linspace(0, 1, fade)[:, None]
out = sys.argv[1] if len(sys.argv) > 1 else "endowed_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
