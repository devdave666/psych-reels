"""Soundtrack for wander_reel: G major (music2, shift 5), a 'canon' build (vi iii IV I) that only resolves at the drop.
Build:  Bm  F#m  G  D  Em/A   (vi iii IV I ii/V)  ->  drop:  D  A  Bm/F#m  G/A  D   (I V vi/iii IV/V I)
In G major that sounds as Em Bm C G Am/D ... G D Em/Bm C/D G.
Sound effects follow the picture: a soft lift and chime when the mind-orb leaves the head (wr.T_LEAVE), a bubble 'blip'
plus a chime each time it reaches an 'elsewhere' bubble (wr.T_VISIT, chimes wander up and down, never settling), tocks on
the two text changes (3.6, 6.8 s), a reel-in whoosh (wr.T_REEL -> drop), an impact and shimmer as it lands home (10.0 s),
a cascade of tinkles as the tree blossoms, and sparkles on the payoff (14.6 s).
Usage: python wander_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import music2
import wander_reel as wr
from synth import SR, boing, impact, tinkle, tock, whoosh

music2.CH["F#m"] = (61, 66, 69)
music2.ROOT["F#m"] = 42
music2.configure(
    shift=5,
    prog=[["Bm"], ["F#m"], ["G"], ["D"], ["Em", "A"], ["D"], ["A"], ["Bm", "F#m"], ["G", "A"], ["D"]],
    melody={
        6: [(0, 69, 1.5), (1.5, 66, 0.5), (2, 69, 1), (3, 71, 1)],          # A4 F#4 A4 B4 over D: home
        7: [(0, 73, 1), (1, 76, 1), (2, 73, 1), (3, 69, 1)],                # C#5 E5 C#5 A4 over A
        8: [(0, 74, 1), (1, 71, 1), (2, 73, 1.5), (3.5, 69, 0.5)],          # D5 B4 | C#5 A4 over Bm | F#m
        9: [(0, 71, 1), (1, 74, 1), (2, 76, 1), (3, 73, 1)],                # B4 D5 | E5 C#5 over G | A
        10: [(0, 73, 0.5), (0.5, 76, 0.5), (1, 74, 3)],                     # C#5 E5 -> D5, home
    })

total = int((wr.DUR + 0.5) * SR)
L = np.zeros(total); R = np.zeros(total)


def place(sig, s, pan=0.0, gain=1.0):
    a = (pan + 1) * math.pi / 4
    i = int(s * SR)
    m = min(len(sig), total - i)
    if m > 0:
        L[i:i + m] += sig[:m] * math.cos(a) * gain
        R[i:i + m] += sig[:m] * math.sin(a) * gain


hz = music2.hz
place(whoosh(0.8, 400, 1800, 1.2, 0.3, 0.6), wr.T_LEAVE - 0.1, 0, 0.6)        # mind lifts off
place(tinkle(hz(86), 0.12), wr.T_LEAVE, 0, 1.0)
place(tock(640, 0.12), 3.6, -0.3, 1.0)                                         # text changes
place(tock(700, 0.12), 6.8, 0.3, 1.0)
notes = [81, 88, 78, 85]                                                       # wandering, unresolved chimes
for k, (tv, (bx, by, _)) in enumerate(zip(wr.T_VISIT, wr.BUBBLES)):
    pan = (bx - 540) / 540 * 0.7
    place(boing(0.25, 520 + 60 * k, 0.12), tv, pan, 1.0)
    place(tinkle(hz(notes[k] + 12), 0.10), tv + 0.04, pan, 1.0)
    place(whoosh(0.6, 700, 300, 1.0, 0.3, 0.3), tv - 0.5, pan, 0.4)

place(whoosh(wr.T_DROP - wr.T_REEL, 250, 3600, 0.9, 0.3, 0.9), wr.T_REEL, 0, 0.9)   # reeled home
place(impact(1.0, heavy=True), wr.T_DROP, 0, 0.5)
for k, m in enumerate((74, 78, 81, 86, 90)):                                   # landing shimmer: D chord (G in key)
    place(tinkle(hz(m + 12), 0.10), wr.T_DROP + 0.05 + 0.07 * k, -0.5 + 0.25 * k, 1.0)
for k, m in enumerate((86, 90, 93, 98, 93, 90, 98, 102)):                       # blossoms popping
    place(tinkle(hz(m), 0.06), wr.T_DROP + 0.25 + 0.14 * k, 0.6 - 0.15 * k, 1.0)
place(tinkle(hz(98), 0.12), 14.6, 0, 1.0)                                      # payoff text
place(tinkle(hz(102), 0.1), 14.75, 0.2, 1.0)
place(tinkle(hz(105), 0.08), 14.9, -0.2, 1.0)

sfx = np.stack([L, R], 1)[: int(wr.DUR * SR)]
mus = music2.render_music()
mus = mus / (np.max(np.abs(mus)) + 1e-9)
mix = mus * 0.62 + sfx * 0.85
mix = np.tanh(1.25 * mix) / np.tanh(1.25)
mix *= 0.70 / np.max(np.abs(mix))
fade = int(0.01 * SR)
mix[:fade] *= np.linspace(0, 1, fade)[:, None]
out = sys.argv[1] if len(sys.argv) > 1 else "wander_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
