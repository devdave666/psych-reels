"""Soundtrack for bundle_reel: A-major build (music2, shift 7) I - IV - vi - V, drop on I - vi - IV - ii/V - I, effects locked to the picture.
Usage: python bundle_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import bundle_reel as fr
import music2
from synth import SR, impact, noise, svf, thump, tinkle, tock, whistle, whoosh

# key of A (shift 7, written in D-major terms)
music2.configure(
    shift=7,
    prog=[["D"], ["G"], ["Bm"], ["A"], ["G", "A"], ["D"], ["Bm"], ["G"], ["Em", "A"], ["D"]],
    melody={
        6: [(0, 81, 1), (1, 86, 1), (2, 90, 2)],                                        # A D F#
        7: [(0, 90, 1), (1, 88, 0.5), (1.5, 86, 0.5), (2, 83, 2)],                      # F# E D B
        8: [(0, 86, 1), (1, 83, 1), (2, 86, 1), (3, 88, 1)],                            # D B D E
        9: [(0, 88, 1), (1, 86, 1), (2, 85, 1), (3, 81, 1)],                            # E D C# A
        10: [(0, 85, 0.5), (0.5, 86, 0.5), (1, 90, 3)],                                 # C# D F#
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
place(whoosh(0.7, 400, 3000, 1.0, 0.25, 0.6), fr.T_ORB - 0.1, 0.5, 0.6)       # the treat appears
place(tinkle(hz(93), 0.12), fr.T_ORB + 0.1, 0.5, 1.0)
place(tinkle(hz(97), 0.1), fr.T_ORB + 0.25, 0.5, 1.0)
for k in range(int(fr.T_DASH - 5.0)):                                        # straining heartbeat of the barbell
    tb = 5.0 + k
    place(thump(0.3, 70, 42, 0.14, 0.03), tb, 0, 0.45)
    place(thump(0.25, 66, 42, 0.12, 0.03), tb + 0.22, 0, 0.3)
place(whoosh(fr.T_DROP - fr.T_DASH, 300, 3600, 1.1, 0.35, 0.9), fr.T_DASH, 0, 0.9)   # orb dashes in
place(thump(0.35, 80, 40, 0.15, 0.03), fr.T_DROP - 0.35, 0, 0.5)
place(impact(1.0, heavy=True), fr.T_DROP, 0, 0.55)                           # snap
place(whoosh(0.9, 250, 2600, 0.9, 0.3, 0.6), fr.T_DROP, 0, 0.7)              # lift off
for i, m in enumerate((88, 93, 97, 100)):
    place(tinkle(hz(m), 0.1), fr.T_DROP + 0.05 + 0.08 * i, -0.3 + 0.2 * i, 1.0)
for tb, m in zip(fr.BARS_T, (88, 93, 97)):                                   # bar steps
    place(thump(0.12, 120, 60, 0.05, 0.02), tb, 0, 0.5)
    place(tinkle(hz(m + 12), 0.1), tb, 0, 1.0)
place(tock(900, 0.12), fr.T_NUM, 0, 0.8)
rng = np.random.default_rng(9)
for tf in fr.T_FIRE:                                                         # sparkle bursts
    place(whistle(0.35, 700, 2400, 0.06), tf - 0.35, rng.uniform(-0.5, 0.5), 1.0)
    place(thump(0.5, 90, 40, 0.2, 0.05), tf, 0, 0.5)
    for q in range(14):
        c = svf(noise(int(0.04 * SR)), np.full(int(0.04 * SR), rng.uniform(2500, 6000)), 1.0)[0]
        place(c / (np.max(np.abs(c)) + 1e-9) * np.exp(-np.arange(len(c)) / SR / 0.01), tf + 0.05 + rng.uniform(0, 0.7), rng.uniform(-0.8, 0.8), 0.14)
for k in range(int((fr.DUR - 10.5) / 1.0)):                                  # a note pops up every second
    place(tinkle(hz((93, 97, 100, 105)[k % 4]), 0.07), fr.T_DROP + 0.5 + k, rng.uniform(-0.5, 0.5), 1.0)
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
out = sys.argv[1] if len(sys.argv) > 1 else "bundle_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
