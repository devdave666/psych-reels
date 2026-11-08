"""Soundtrack for testyourself_reel: C mixolydian colour (music2, shift -2), with a new bVII chord (C in D-major terms).
Build (D-major names): Bm  C  G  Em  C/A   ->  drop: D  C  G  Em/A  D   (vi bVII IV ii bVII/V | I bVII IV ii/V I)
The bVII-IV-I 'anthem' cadence gives the drop its lift; the lead uses the flat seventh over the C bar.
SFX lock to the picture: a pencil tick on each of the 14 tally marks (accelerating, pitch rising), a soft tock on each of the
seven day dots, a dusty puff for each line that dissolves, a low thud when 40% lands, riser + impact + shimmer on the drop,
a pen scratch and a rising tinkle for each gold line written from memory, and a bright hit when 61% lands.
Usage: python testyourself_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import music2
import testyourself_reel as fr
from synth import SR, chalk, dust, impact, thump, tinkle, tock, whoosh

music2.CH["C"] = (60, 64, 67)
music2.ROOT["C"] = 36
music2.configure(
    shift=-2,
    prog=[["Bm"], ["C"], ["G"], ["Em"], ["C", "A"], ["D"], ["C"], ["G"], ["Em", "A"], ["D"]],
    melody={
        6: [(0, 78, 1), (1, 81, 1), (2, 86, 1.5), (3.5, 84, 0.5)],
        7: [(0, 84, 1), (1, 79, 1), (2, 88, 2)],
        8: [(0, 86, 1), (1, 83, 1), (2, 91, 1.5), (3.5, 88, 0.5)],
        9: [(0, 88, 1), (1, 83, 1), (2, 85, 1), (3, 88, 1)],
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
place(tinkle(hz(86), 0.12), 0.3, 0, 1.0)                                     # hook text
place(tinkle(hz(90), 0.1), 0.45, 0, 1.0)
for k, tt in enumerate(fr.TALLY_T):                                          # tally marks, one per reread
    place(tock(1100 + 25 * k, 0.13), tt, 0.25, 0.6 + 0.012 * k)
place(tock(600, 0.12), 4.1, 0, 0.7)                                          # "Read it 14 times."
for k, tt in enumerate(fr.DAY_T):                                            # seven days pass
    place(tock(420 - 15 * k, 0.12), tt, -0.4 + 0.13 * k, 0.75)
for ln, tt in fr.FORGET_T.items():                                           # lines dissolve
    place(dust(fr.FORGET_D, 0.35), tt, (fr.LINE_Y[ln] % 3 - 1) * 0.3, 0.9)
place(thump(0.6, 95, 40, 0.18, 0.04), fr.T_40, 0, 0.45)                      # 40% lands, dull
place(tock(260, 0.14), fr.T_40, 0, 0.8)
place(whoosh(1.3, 250, 3500, 0.9, 0.3, 0.85), fr.T_DROP - 1.3, 0, 0.75)       # into the drop
place(impact(1.0, heavy=True), fr.T_DROP, 0, 0.55)                           # page wiped clean
place(whoosh(1.6, 700, 5200, 0.8, 0.3, 0.4), fr.T_DROP, 0, 0.4)              # gold ring
SCALE = [78, 81, 83, 86, 88, 90]
for k, tw in enumerate(fr.WRITE_T):                                          # each line written from memory
    place(chalk(fr.WRITE_D, 0.22), tw, -0.3 + 0.12 * k, 0.9)
    place(tinkle(hz(SCALE[k] + 12), 0.12), tw + fr.WRITE_D, math.sin(k * 1.9) * 0.4, 0.9)
place(impact(0.55), fr.T_61, 0, 0.45)                                        # 61% lands
place(tinkle(hz(98), 0.13), fr.T_61, -0.2, 1.0)
place(tinkle(hz(102), 0.11), fr.T_61 + 0.12, 0.2, 1.0)
place(tinkle(hz(105), 0.12), 14.8, 0, 1.0)                                   # payoff text
place(tinkle(hz(110), 0.1), 14.95, 0, 1.0)

sfx = np.stack([L, R], 1)[: int(fr.DUR * SR)]
mus = music2.render_music()
mus = mus / (np.max(np.abs(mus)) + 1e-9)
mix = mus * 0.62 + sfx * 0.85
mix = np.tanh(1.25 * mix) / np.tanh(1.25)
mix *= 0.70 / np.max(np.abs(mix))
fade = int(0.01 * SR)
mix[:fade] *= np.linspace(0, 1, fade)[:, None]
out = sys.argv[1] if len(sys.argv) > 1 else "testyourself_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
