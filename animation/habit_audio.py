"""Soundtrack for habit_reel: synthesized music (music.py) + sound effects locked to the figure's walk.
Usage: python habit_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import habit_reel as hr
import music
from synth import SR, dust, footstep, impact, scuff, svf, noise, thump, tinkle, tock, whistle, whoosh

total = int((hr.DUR + 0.5) * SR)
L = np.zeros(total); R = np.zeros(total)


def place(sig, s, pan=0.0, gain=1.0):
    a = (pan + 1) * math.pi / 4
    i = int(s * SR)
    m = min(len(sig), total - i)
    if m > 0:
        L[i:i + m] += sig[:m] * math.cos(a) * gain
        R[i:i + m] += sig[:m] * math.sin(a) * gain


# --- footsteps: heavy thuds with scuff early, light quick pats once it is automatic
for tk in hr.STEP_T:
    if tk > hr.DUR:
        break
    a = hr.fa(tk)
    place(thump(0.14, 100, 45, 0.05, 0.02) * 0.55 + scuff(0.14, 0.3), tk, 0.0, (1 - a) ** 1.2 * 0.9)
    place(footstep(0.3), tk, 0.0, 0.25 + 0.5 * a)
    if a < 0.6:
        place(dust(0.25, 0.12), tk + 0.02, 0.0, 1 - a)

# --- headwind: filtered noise that gusts and fades as the habit becomes automatic
n = int(11 * SR)
u = np.arange(n) / SR
fc = 500 + 250 * np.sin(2 * np.pi * 0.4 * u)
bp, _, _ = svf(noise(n), fc, 1.2)
wind = bp / (np.max(np.abs(bp)) + 1e-9) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * u + 1)) ** 1.5
wind *= np.array([(1 - hr.fa(t)) ** 1.3 for t in np.arange(0, 11, 1 / SR * 100).repeat(100)[:n]]) * 0.16
place(wind, 0.0, -0.1, 1.0)

# --- day counter: a soft C-major pentatonic tick per day, climbing
PENT = (0, 2, 4, 7, 9)
last = 0
for t in np.arange(hr.T_DAY0, hr.T_DAY66 + 0.001, 0.002):
    d = int(min(66, hr.day(t) + 1e-6))
    if d != last:
        last = d
        idx = d - 1
        m = 72 + 12 * (idx // 10) + PENT[idx % 5] if idx < 30 else 84 + PENT[idx % 5]
        place(tinkle(music.hz(min(m, 100)), 0.06 if d < 60 else 0.09), t, 0.2 * math.sin(d), 1.0)

place(tock(520, 0.14), 0.4, 0, 1.0)                                    # hook appears
place(tock(780, 0.14), hr.T_DAY0, 0, 1.0)                              # counter appears
place(whoosh(1.6, 300, 3600, 0.9, 0.38, 0.8), 8.7, 0, 1.0)             # pull-out into the drop
place(impact(1.0, heavy=True), 10.0, 0, 0.55)
place(tinkle(1568, 0.12), 12.2, 0, 1.0)                                # payoff text
place(tinkle(2093, 0.1), 12.35, 0, 1.0)
for k, (tt, f0, f1) in enumerate(((11.3, 2400, 3600), (11.45, 2800, 3800), (14.2, 2200, 3300), (14.33, 2600, 3500),
                                  (16.8, 2500, 3700), (16.95, 3000, 4000))):   # birdsong after sunrise
    place(whistle(0.11, f0, f1, 0.05), tt, -0.5 + 0.35 * (k % 3), 1.0)

sfx = np.stack([L, R], 1)[: int(hr.DUR * SR)]
mus = music.render_music()
mus = mus / (np.max(np.abs(mus)) + 1e-9)
mix = mus * 0.62 + sfx * 0.85
mix = np.tanh(1.25 * mix) / np.tanh(1.25)
mix *= 0.70 / np.max(np.abs(mix))
fade = int(0.01 * SR)
mix[:fade] *= np.linspace(0, 1, fade)[:, None]

out = sys.argv[1] if len(sys.argv) > 1 else "habit_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
