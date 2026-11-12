"""Soundtrack for juggle_reel: F# major (music2, shift -8, a low, warm register), 'royal road' build.
Build:  G  A  F#m  Bm  Em/A   (IV V iii vi ii/V)  ->  drop:  D  G  F#m  Em/A  D   (I IV iii ii/V I)
In F# major that sounds as B  C#  A#m  D#m  G#m/C# ... F#.
Sound effects follow the picture: a soft tock on every throw and a leathery pat on every catch (fr.THROWS / fr.CATCH_T),
a whoosh + thud + low bounce for the fumble (thrown 6.5 s, missed 7.3 s), a pick-up tick (7.5 s), an impact as the cascade
locks in and the brain lights up (10.0 s), rising chord-tone chimes on the first locked-in catches (10.0 ... 13.0 s) and
sparkles on the payoff text (14.6 s).
Usage: python juggle_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import juggle_reel as fr
import music2
from synth import SR, boing, dust, impact, thump, tinkle, tock, whoosh

music2.CH["F#m"] = (61, 66, 69)
music2.ROOT["F#m"] = 42
music2.configure(
    shift=-8,
    prog=[["G"], ["A"], ["F#m"], ["Bm"], ["Em", "A"], ["D"], ["G"], ["F#m"], ["Em", "A"], ["D"]],
    melody={
        6: [(0, 74, 1), (1, 78, 1), (2, 81, 1), (3, 86, 1)],
        7: [(0, 83, 1.5), (1.5, 81, 0.5), (2, 79, 1), (3, 83, 1)],
        8: [(0, 85, 1), (1, 81, 1), (2, 78, 1.5), (3.5, 81, 0.5)],
        9: [(0, 79, 1), (1, 83, 1), (2, 85, 1), (3, 88, 1)],
        10: [(0, 90, 0.5), (0.5, 88, 0.5), (1, 86, 3)],
    })

total = int((fr.DUR + 0.5) * SR)
L = np.zeros(total); R = np.zeros(total)
rng = np.random.default_rng(9)


def place(sig, s, pan=0.0, gain=1.0):
    a = (pan + 1) * math.pi / 4
    i = int(s * SR)
    m = min(len(sig), total - i)
    if m > 0 and i >= 0:
        L[i:i + m] += sig[:m] * math.cos(a) * gain
        R[i:i + m] += sig[:m] * math.sin(a) * gain


hz = music2.hz
BALL_TOCK = (620, 700, 780)
place(tock(520, 0.14), 0.4, 0, 0.7)                                            # hook text
place(tock(440, 0.12), 4.1, 0, 0.6)                                            # "Adults aged 50 to 67"
for t0, b, h, f, dropped in fr.THROWS:                                         # throws
    if t0 < fr.DUR:
        pan = -0.35 if h == 0 else 0.35
        place(tock(BALL_TOCK[b], 0.10), t0, pan, 0.7)
        place(whoosh(0.25, 1400, 2600, 1.2, 0.08, 0.5), t0, pan, 0.35)
for ct in fr.CATCH_T:                                                          # catches: a soft leathery pat
    h = 1 if round((ct - 1.0) / 0.5) % 2 == 0 else 0
    pan = 0.35 if h else -0.35
    place(thump(0.12, 180, 90, 0.03), ct, pan, 0.55)
    place(tock(360, 0.09), ct, pan, 0.5)
place(whoosh(0.7, 2200, 500, 1.3, 0.22, 0.5), fr.T_MISS - 0.2, 0.5, 0.5)       # the fumble
place(thump(0.3, 140, 60, 0.08), fr.T_MISS + 0.35, 0.7, 0.8)
place(boing(0.45, 220.0, 0.25), fr.T_MISS + 0.38, 0.7, 0.7)
place(tock(900, 0.10), fr.T_PICKUP - 0.2, -0.35, 0.6)                          # pick it up + third ball
place(tinkle(hz(81), 0.08), fr.BALL_IN[2] - 0.2, -0.35, 0.6)
place(impact(1.0, heavy=True), fr.T_DROP, 0, 0.55)                             # cascade locks in, brain lights up
place(dust(1.2, 0.3), fr.T_DROP, 0, 0.6)
place(tock(900, 0.12), 10.2, 0, 0.6)                                           # first text line
tones = (74, 78, 81, 83, 86, 90, 93)                                           # rising chord tones on the locked-in catches
locked = [ct for ct in fr.CATCH_T if fr.T_DROP <= ct <= 13.01]
for j, ct in enumerate(locked[:len(tones)]):
    pan = 0.3 if j % 2 == 0 else -0.3
    place(tinkle(hz(tones[j]), 0.09), ct, pan, 0.8)
    place(tinkle(hz(tones[j] + 12), 0.04), ct + 0.04, pan, 0.6)
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
out = sys.argv[1] if len(sys.argv) > 1 else "juggle_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
