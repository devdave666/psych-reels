"""Soundtrack for selfcompassion_reel: E-major build (music2, shift 2), I vi IV V then drop on I - V - vi - IV/V - I.
Rain and thunder in the storm, effects locked to the picture. Usage: python selfcompassion_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import selfcompassion_reel as fr
import music2
from synth import SR, dust, impact, noise, svf, thump, tinkle, tock, whistle, whoosh, rumble

music2.configure(
    shift=2,
    prog=[["D"], ["Bm"], ["G"], ["A"], ["G", "A"], ["D"], ["A"], ["Bm"], ["G", "A"], ["D"]],
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
n = int(10.0 * SR)                                                           # rain bed, swelling until the drop
rn = svf(noise(n), np.full(n, 5500.0), 0.8)[0]
rn = rn / (np.max(np.abs(rn)) + 1e-9) * (np.linspace(0, 1, n) ** 1.5 * 0.35 + 0.05)
rn[:int(1.6 * SR)] *= np.linspace(0, 1, int(1.6 * SR))
rn[-int(0.4 * SR):] *= np.linspace(1, 0, int(0.4 * SR))
place(rn, 0.0, 0, 0.5)
for tl in fr.LIGHTNING:                                                      # lightning crack then thunder
    place(impact(0.7), tl, 0, 0.35)
    place(rumble(1.8, 0.4), tl + 0.15, 0, 0.5)
place(thump(0.3, 70, 45, 0.15, 0.03), 8.7, 0, 0.5)                           # breath before the cloud parts
place(whoosh(1.3, 250, 3200, 0.9, 0.3, 0.8), 8.75, 0, 0.9)
place(impact(1.0, heavy=True), fr.T_DROP, 0, 0.5)
place(whoosh(1.4, 3000, 500, 0.9, 0.3, 0.5), 10.0, 0, 0.6)                   # cloud sliding away
for q in range(8):                                                           # warm droplets
    place(tinkle(hz(93 + (q * 5) % 12), 0.05), 10.3 + q * 0.2, np.sin(q * 2.1) * 0.6, 0.7)
for tb, k in zip(fr.BARS_T, range(3)):                                       # growth steps: chimes up the scale
    place(thump(0.12, 120, 60, 0.05, 0.02), tb, 0, 0.5)
    place(tinkle(hz((93, 97, 100)[k]), 0.1), tb, 0, 1.0)
place(tock(900, 0.12), fr.T_NUM, 0, 0.8)
place(whoosh(0.8, 400, 2800, 0.9, 0.25, 0.5), fr.T_BLOOM - 0.5, 0, 0.7)       # bloom
place(tinkle(hz(105), 0.12), fr.T_BLOOM, 0, 1.0)
rng = np.random.default_rng(9)
for tf in fr.T_FIRE:                                                         # blossom bursts
    place(whistle(0.35, 700, 2400, 0.06), tf - 0.35, rng.uniform(-0.5, 0.5), 1.0)
    place(thump(0.5, 90, 40, 0.2, 0.05), tf, 0, 0.55)
    for q in range(14):
        c = svf(noise(int(0.04 * SR)), np.full(int(0.04 * SR), rng.uniform(2500, 6000)), 1.0)[0]
        place(c / (np.max(np.abs(c)) + 1e-9) * np.exp(-np.arange(len(c)) / SR / 0.01), tf + 0.05 + rng.uniform(0, 0.7), rng.uniform(-0.8, 0.8), 0.14)
place(tinkle(hz(98), 0.12), 14.6, 0, 1.0)                                    # payoff text
place(tinkle(hz(105), 0.1), 14.75, 0, 1.0)

sfx = np.stack([L, R], 1)[: int(fr.DUR * SR)]
mus = music2.render_music()
mus = mus / (np.max(np.abs(mus)) + 1e-9)
mix = mus * 0.62 + sfx * 0.85
mix = np.tanh(1.25 * mix) / np.tanh(1.25)
mix *= 0.70 / np.max(np.abs(mix))
fade = int(0.01 * SR)
mix[:fade] *= np.linspace(0, 1, fade)[:, None]
out = sys.argv[1] if len(sys.argv) > 1 else "selfcompassion_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
