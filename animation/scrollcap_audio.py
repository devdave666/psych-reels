"""Soundtrack for scrollcap_reel: F major in a low, warm register (music2, shift -9; bass roots raised an octave so they
stay audible on phones).  Build opens on the minor ii for a restless, late-night feel:
Build:  Em  Bm  G  A  Bm/A   (ii vi IV V vi/V)  ->  drop:  D  Em  G  G/A  D   (I ii IV IV/V I)
In F major that sounds as Gm Dm Bb C Dm/C ... F Gm Bb Bb/C F.
Sound effects follow the picture: a swipe on every feed flick (fr.FLICKS), notification pings (fr.PINGS), a soft clock tick
on every beat while the timer rings drain (4.6 ... 9.4 s), a lock click (9.5 s), an impact + air as the room turns warm
(10.0 s), a rising whoosh and chord-tone chime for each lantern launch (fr.LANTERN_T, 10.0 ... 13.0 s) and sparkles on the
payoff text (14.6 s).
Usage: python scrollcap_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import music2
import scrollcap_reel as fr
from synth import SR, dust, impact, thump, tinkle, tock, whoosh

for k in ("Em", "Bm", "G", "A", "D"):
    music2.ROOT[k] += 12                                                       # shift -9 would put the bass too low
music2.configure(
    shift=-9,
    prog=[["Em"], ["Bm"], ["G"], ["A"], ["Bm", "A"], ["D"], ["Em"], ["G"], ["G", "A"], ["D"]],
    melody={
        6: [(0, 74, 1), (1, 78, 1), (2, 81, 1.5), (3.5, 78, 0.5)],
        7: [(0, 79, 1), (1, 83, 1), (2, 88, 1.5), (3.5, 86, 0.5)],
        8: [(0, 86, 1), (1, 83, 1), (2, 79, 1), (3, 81, 1)],
        9: [(0, 83, 1), (1, 86, 1), (2, 85, 1), (3, 88, 1)],
        10: [(0, 90, 0.5), (0.5, 88, 0.5), (1, 86, 3)],
    })

total = int((fr.DUR + 0.5) * SR)
L = np.zeros(total); R = np.zeros(total)


def place(sig, s, pan=0.0, gain=1.0):
    a = (pan + 1) * math.pi / 4
    i = int(s * SR)
    m = min(len(sig), total - i)
    if m > 0 and i >= 0:
        L[i:i + m] += sig[:m] * math.cos(a) * gain
        R[i:i + m] += sig[:m] * math.sin(a) * gain


hz = music2.hz
place(tock(520, 0.14), 0.3, 0, 0.7)                                            # hook text
for j, tf in enumerate(fr.FLICKS):                                             # feed swipes
    pan = 0.2 if j % 2 else -0.2
    place(whoosh(0.32, 3200, 900, 1.3, 0.22, 0.3), tf - 0.04, pan, 0.55)
    place(tock(1500, 0.06), tf, pan, 0.5)
for tp in fr.PINGS:                                                            # notification badge
    place(tinkle(hz(86 + 12), 0.10), tp, 0.45, 0.8)
    place(tinkle(hz(81 + 12), 0.09), tp + 0.11, 0.45, 0.8)
place(tock(440, 0.12), 4.2, 0, 0.6)                                            # "143 students got a limit"
tick = fr.T_RING0
while tick <= fr.T_RING1 + 1e-6:                                               # clock ticks while the rings drain
    place(tock(1900 if round((tick - fr.T_RING0) * 2) % 2 == 0 else 1600, 0.07), tick, 0.15, 0.6)
    tick += 0.5
place(tock(1100, 0.16), fr.T_LOCK, 0, 0.8)                                     # screen lock click
place(thump(0.12, 220, 110, 0.025), fr.T_LOCK, 0, 0.5)
place(impact(1.0, heavy=True), fr.T_DROP, 0, 0.55)                             # room turns warm
place(dust(1.2, 0.3), fr.T_DROP, 0, 0.6)
place(tock(900, 0.12), 10.2, 0, 0.5)                                           # "3 weeks later" text
tones = (74, 78, 81, 86, 79, 83, 88)                                           # chord tones: D bar, then Em bar
for j, lt in enumerate(fr.LANTERN_T):                                          # lantern launches
    pan = max(-0.6, min(0.6, fr.LANTERNS[j][0] * 0.6))
    place(whoosh(0.6, 400, 2400, 1.0, 0.18, 0.35), lt - 0.05, pan, 0.4)
    place(tinkle(hz(tones[j]), 0.09), lt, pan, 0.8)
    place(tinkle(hz(tones[j] + 12), 0.04), lt + 0.04, pan, 0.6)
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
out = sys.argv[1] if len(sys.argv) > 1 else "scrollcap_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
