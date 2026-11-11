"""Soundtrack for stranger_reel: E major (music2, shift +2), with a borrowed flat-six chord for a heroic lift.
Build:  D  Bb  G  A  Em/A   (I bVI IV V ii/V)  ->  drop:  D  Bb  G  Em/A  D   (I bVI IV ii/V I)
In E major that sounds as E  C  A  B  F#m/B ... E.
A double rail clack each time a tunnel lamp passes (0.5, 1.5 ... 9.5 s), soft ticks on the hero's glances, a swish as the
phone is lowered (8.6 s), a bubble 'blip' for the first hello (9.2 s), breaking glass + impact on the drop (10.0 s), a
chord-tone chime for each speech bubble (10.5 ... 13.0 s) and sparkles on the payoff text (14.6 s).
Usage: python stranger_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import music2
import stranger_reel as fr
from synth import SR, dust, impact, thump, tinkle, tock, whoosh

music2.CH["Bb"] = (58, 62, 65)
music2.ROOT["Bb"] = 34
music2.configure(
    shift=2,
    prog=[["D"], ["Bb"], ["G"], ["A"], ["Em", "A"], ["D"], ["Bb"], ["G"], ["Em", "A"], ["D"]],
    melody={
        6: [(0, 74, 1), (1, 78, 1), (2, 81, 1.5), (3.5, 78, 0.5)],
        7: [(0, 77, 1), (1, 74, 1), (2, 82, 2)],
        8: [(0, 79, 1), (1, 83, 1), (2, 86, 1.5), (3.5, 83, 0.5)],
        9: [(0, 83, 1), (1, 79, 1), (2, 81, 1), (3, 85, 1)],
        10: [(0, 86, 0.5), (0.5, 85, 0.5), (1, 86, 3)],
    })

total = int((fr.DUR + 0.5) * SR)
L = np.zeros(total); R = np.zeros(total)
rng = np.random.default_rng(7)


def place(sig, s, pan=0.0, gain=1.0):
    a = (pan + 1) * math.pi / 4
    i = int(s * SR)
    m = min(len(sig), total - i)
    if m > 0:
        L[i:i + m] += sig[:m] * math.cos(a) * gain
        R[i:i + m] += sig[:m] * math.sin(a) * gain


hz = music2.hz
place(tock(520, 0.14), 0.4, 0, 0.7)                                            # hook text
place(tock(440, 0.12), 4.1, 0, 0.6)                                            # "Commuters guessed"
for k, ct in enumerate(fr.CLACK_T):                                            # rail joints under each passing lamp
    g = 0.55 + 0.03 * k
    place(thump(0.18, 110, 55, 0.05), ct - 0.06, -0.2, g * 0.6)
    place(tock(260, 0.16), ct - 0.06, -0.2, g)
    place(thump(0.18, 120, 60, 0.05), ct + 0.06, 0.2, g * 0.6)
    place(tock(300, 0.16), ct + 0.06, 0.2, g)
    place(whoosh(0.35, 2500, 600, 1.0, 0.12, 0.5), ct - 0.2, 0.6 - 1.2 * (k % 2) * 0, 0.4)   # lamp swish
for gt in fr.GLANCE_T:                                                         # hero sneaks a look
    place(tock(820, 0.08), gt, -0.15, 0.7)
place(whoosh(0.6, 1800, 400, 1.2, 0.25, 0.4), fr.T_LOWER, -0.15, 0.5)          # phone lowered
place(tinkle(hz(81), 0.1), fr.T_HI, -0.15, 0.9)                                # the first 'hi'
place(tinkle(hz(86), 0.07), fr.T_HI + 0.08, -0.15, 0.8)
place(impact(1.0, heavy=True), fr.T_DROP, 0, 0.55)                             # bubbles shatter
place(dust(1.2, 0.3), fr.T_DROP, 0, 0.7)
for k in range(22):                                                            # glass shards tinkling down
    tt = fr.T_DROP + rng.uniform(0.0, 0.9) ** 1.6
    place(tinkle(rng.uniform(2600, 6200), 0.05), tt, rng.uniform(-0.8, 0.8), 0.7)
place(tock(900, 0.12), 10.2, 0, 0.6)                                           # first text line
tones = (74, 78, 81, 83, 86, 90)                                               # the conversation: rising chord tones
for j, ct in enumerate(fr.CHAT_T):
    pan = 0.3 if j % 2 == 0 else -0.3                                          # stranger right, hero left
    place(tinkle(hz(tones[j]), 0.11), ct, pan, 0.85)
    place(tinkle(hz(tones[j] + 12), 0.05), ct + 0.05, pan, 0.6)
place(whoosh(0.9, 800, 5000, 1.0, 0.25, 0.3), 14.6 - 0.5, 0, 0.4)              # payoff text
place(tinkle(hz(98), 0.12), 14.6, 0, 1.0)
place(tinkle(hz(102), 0.1), 14.75, 0, 1.0)
place(tinkle(hz(105), 0.08), 14.9, 0, 0.9)

sfx = np.stack([L, R], 1)[: int(fr.DUR * SR)]
mus = music2.render_music()
mus = mus / (np.max(np.abs(mus)) + 1e-9)
mix = mus * 0.62 + sfx * 0.85
mix = np.tanh(1.25 * mix) / np.tanh(1.25)
mix *= 0.70 / np.max(np.abs(mix))
fade = int(0.01 * SR)
mix[:fade] *= np.linspace(0, 1, fade)[:, None]
out = sys.argv[1] if len(sys.argv) > 1 else "stranger_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
