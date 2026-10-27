"""Soundtrack for spotlight_reel: the layered track (music2.py) plus effects locked to the picture.
Usage: python spotlight_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import music2
import spotlight_reel as sp
from synth import SR, impact, noise, svf, thump, tinkle, tock, whoosh

total = int((sp.DUR + 0.5) * SR)
L = np.zeros(total); R = np.zeros(total)


def place(sig, s, pan=0.0, gain=1.0):
    a = (pan + 1) * math.pi / 4
    i = int(s * SR)
    m = min(len(sig), total - i)
    if m > 0:
        L[i:i + m] += sig[:m] * math.cos(a) * gain
        R[i:i + m] += sig[:m] * math.sin(a) * gain


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


# --- crowd murmur: syllable-modulated band noise; tense and loud while everyone 'stares', light chatter afterwards
n = int(sp.DUR * SR)
u = np.arange(n) / SR
bp, _, _ = svf(noise(n), 700 + 350 * np.sin(2 * np.pi * 0.31 * u), 1.1)
syl = 0.55 + 0.45 * np.sin(2 * np.pi * 3.7 * u + 2 * np.sin(2 * np.pi * 0.43 * u))
amb = 0.05 + 0.10 * np.interp(u, [0, 3, 6, 9.9, 10.0, 11, 20], [0, 0.2, 0.7, 1.0, 0.35, 0.25, 0.2])
murmur = bp / (np.max(np.abs(bp)) + 1e-9) * syl * amb
place(murmur, 0.0, 0.0, 1.0)

# --- spotlight clunks on, hums while the dread builds, powers down at the drop
place(thump(0.25, 160, 50, 0.07, 0.03), sp.T_ON, 0, 0.9)
place(tock(900, 0.12), sp.T_ON + 0.02, 0, 1.0)
place(tock(520, 0.14), 0.4, 0, 1.0)                                    # hook appears
place(tock(780, 0.14), 3.2, 0, 1.0)                                    # counter appears
hn = int((sp.T_DROP - sp.T_ON) * SR)
uh = np.arange(hn) / SR
hum = (np.sin(2 * np.pi * 110 * uh) + 0.5 * np.sin(2 * np.pi * 220 * uh) + 0.25 * np.sin(2 * np.pi * 330 * uh)) * 0.05
hum *= np.minimum(1, uh / 0.4) * (0.5 + 0.5 * uh / uh[-1])
place(hum, sp.T_ON, 0, 1.0)

# --- heartbeat, locked to the visual pulse, quickening
for k, b in enumerate(sp.BEATS):
    g = 0.6 + 0.5 * k / max(1, len(sp.BEATS) - 1)
    place(thump(0.2, 85, 38, 0.07, 0.04), b, 0, 0.9 * g)
    place(thump(0.17, 75, 36, 0.06, 0.04), b + 0.24, 0, 0.55 * g)

# --- the drop: power-down sweep, boom, party-popper
place(whoosh(0.45, 3200, 200, 0.9, 0.3, 0.2), sp.T_DROP - 0.4, 0, 1.0)
place(impact(1.0, heavy=True), sp.T_DROP, 0, 0.5)
pn = int(0.4 * SR)
tp = np.arange(pn) / SR
pop = svf(noise(pn), np.full(pn, 3200.0), 0.9)[0]
place(pop / (np.max(np.abs(pop)) + 1e-9) * np.exp(-tp / 0.08), sp.T_DROP + 0.5, 0, 0.5)
for i in range(7):                                                      # confetti sparkle run
    place(tinkle(hz(86 + 2 * i) , 0.08), sp.T_DROP + 0.5 + 0.045 * i, -0.4 + 0.13 * i, 1.0)

# --- each crowd member turns away to a spotlight of their own: a climbing D-major pentatonic tinkle
PENT = (0, 2, 4, 7, 9)
for i, tt in enumerate(sp.TURN_T):
    m = 74 + PENT[i % 5] + 12 * (i // 5)
    place(tinkle(hz(min(m, 100)), 0.07), tt, -0.7 + 1.4 * ((i * 7) % 10) / 9, 1.0)

# --- the number counts down, 46 -> 23
for k in range(12):
    place(tock(420 + 45 * k, 0.1), 10.3 + 1.3 * k / 11, 0, 1.0)

# --- audience applause swelling, then hops landing on the beat
rng = np.random.default_rng(5)
for tt in np.sort(rng.uniform(11.4, 20.0, 150) ** 1.0):
    dens = min(1.0, (tt - 11.4) / 2.5)
    if rng.random() < dens:
        c = svf(noise(int(0.05 * SR)), np.full(int(0.05 * SR), rng.uniform(1800, 3800)), 1.0)[0]
        place(c / (np.max(np.abs(c)) + 1e-9) * np.exp(-np.arange(len(c)) / SR / 0.012), float(tt), rng.uniform(-0.8, 0.8), 0.22)
place(tinkle(1175, 0.12), 12.6, 0, 1.0)                                # payoff text
place(tinkle(1760, 0.1), 12.75, 0, 1.0)
k = 0
while sp.HOP_T0 + 0.5 * k < sp.DUR - 0.1:
    place(thump(0.12, 110, 55, 0.05, 0.02) * 0.6, sp.HOP_T0 + 0.5 * k + 0.5, 0, 0.45)
    k += 1

sfx = np.stack([L, R], 1)[: int(sp.DUR * SR)]
mus = music2.render_music()
mus = mus / (np.max(np.abs(mus)) + 1e-9)
mix = mus * 0.62 + sfx * 0.85
mix = np.tanh(1.25 * mix) / np.tanh(1.25)
mix *= 0.70 / np.max(np.abs(mix))
fade = int(0.01 * SR)
mix[:fade] *= np.linspace(0, 1, fade)[:, None]

out = sys.argv[1] if len(sys.argv) > 1 else "spotlight_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
