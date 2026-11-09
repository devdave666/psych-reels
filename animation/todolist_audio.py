"""Soundtrack for todolist_reel: Eb major (music2, shift 1) with a new lydian colour chord, II (E major in D-major names).
Build:  G   E   Bm  A   G/A      (IV II vi V IV/V)  ->  drop:  D   E   G   Em/A   D   (I II IV ii/V I)
A tock for every new looping thought, a whoosh as the notepad slides up, an impact on the drop, a pencil scratch plus a
chime on each list line (beats 10.5 ... 13.0 s), soft chimes on the drifting z's.
Usage: python todolist_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import todolist_reel as fr
import music2
from synth import SR, chalk, dust, impact, tinkle, tock, whoosh

music2.CH["E"] = (59, 64, 68)
music2.ROOT["E"] = 40
music2.configure(
    shift=1,
    prog=[["G"], ["E"], ["Bm"], ["A"], ["G", "A"], ["D"], ["E"], ["G"], ["Em", "A"], ["D"]],
    melody={
        6: [(0, 78, 1), (1, 81, 1), (2, 86, 2)],
        7: [(0, 88, 1.5), (1.5, 83, 0.5), (2, 80, 2)],
        8: [(0, 86, 1), (1, 83, 1), (2, 79, 1), (3, 83, 1)],
        9: [(0, 83, 1), (1, 81, 1), (2, 85, 1), (3, 88, 1)],
        10: [(0, 85, 0.5), (0.5, 88, 0.5), (1, 86, 3)],
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
for i, th in enumerate(fr.THOUGHTS):                                          # each new thought pops in
    place(tock(380 + 45 * (i % 5), 0.12), th[0], (-0.6, 0.5, -0.2, 0.7, 0.1, -0.5)[i % 6], 0.55 + 0.03 * i)
place(tock(520, 0.14), 0.4, 0, 0.8)                                           # hook
place(tock(430, 0.12), 4.1, 0, 0.7)                                           # "Tomorrow's tasks keep looping"
place(whoosh(1.4, 200, 2400, 0.9, 0.3, 0.8), fr.T_PAD, 0, 0.6)                # notepad slides up
place(impact(1.0, heavy=True), fr.T_DROP, 0, 0.55)                            # drop
place(dust(0.8, 0.25), fr.T_DROP, 0, 0.6)
for j, tl in enumerate(fr.LINE_T):                                            # thoughts land, a line is written
    place(whoosh(0.5, 600, 2600, 1.2, 0.2, 0.85), tl - 0.5, 0.3 * ((j % 2) * 2 - 1), 0.35)
    place(chalk(0.4, 0.18), tl, -0.2 + 0.08 * j, 0.8)
    place(tinkle(hz(86 + (0, 2, 4, 7, 9, 12)[j]), 0.08), tl, -0.4 + 0.16 * j, 0.6)
place(tock(900, 0.12), 10.2, 0, 0.7)                                          # "9 min"
place(tock(1100, 0.12), 11.0, 0, 0.6)
for zt in fr.Z_T:                                                             # drifting z's
    place(tinkle(hz(98), 0.05), zt, 0.3, 0.6)
place(tinkle(hz(105), 0.12), 14.6, 0, 1.0)                                    # payoff text
place(tinkle(hz(110), 0.1), 14.75, 0, 1.0)

sfx = np.stack([L, R], 1)[: int(fr.DUR * SR)]
mus = music2.render_music()
mus = mus / (np.max(np.abs(mus)) + 1e-9)
mix = mus * 0.62 + sfx * 0.85
mix = np.tanh(1.25 * mix) / np.tanh(1.25)
mix *= 0.70 / np.max(np.abs(mix))
fade = int(0.01 * SR)
mix[:fade] *= np.linspace(0, 1, fade)[:, None]
out = sys.argv[1] if len(sys.argv) > 1 else "todolist_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
