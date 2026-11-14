"""Soundtrack for dontcant_reel: C# major (music2, shift -1), a ii-vi-V-IV build that only resolves at the drop.
Build:  Em  Bm  A  G  Em/A   (ii vi V IV ii/V)  ->  drop:  D  F#m  Bm  G/A  D   (I iii vi IV/V I)
In C# major that sounds as D#m A#m G# F# D#m/G# ... C#.
Sound effects follow the picture: a tock on the hook and the row labels, a wind gust plus a rising day tick on every day
(dc.T_DAY, 4.0 ... 8.5 s), a soft 'fft' puff and a tiny hiss on every candle that goes out (dc.out_time), an impact as the
eight flames flare (10.0 s), warm chord-tone chimes on the counts (10.4 s) and sparkles on the payoff (14.6 s).
Usage: python dontcant_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import dontcant_reel as dc
import music2
from synth import SR, impact, noise, norm, svf, thump, tinkle, tock, whoosh

music2.CH["F#m"] = (61, 66, 69)
music2.ROOT["F#m"] = 42
music2.configure(
    shift=-1,
    prog=[["Em"], ["Bm"], ["A"], ["G"], ["Em", "A"], ["D"], ["F#m"], ["Bm"], ["G", "A"], ["D"]],
    melody={
        6: [(0, 74, 1), (1, 78, 1), (2, 81, 1.5), (3.5, 83, 0.5)],          # D5 F#5 A5 B5: the flames rise
        7: [(0, 85, 1.5), (1.5, 81, 0.5), (2, 78, 1), (3, 81, 1)],          # over F#m: C#6 A5 F#5 A5
        8: [(0, 86, 1), (1, 85, 1), (2, 83, 1.5), (3.5, 81, 0.5)],          # over Bm: D6 C#6 B5 A5
        9: [(0, 83, 1), (1, 86, 1), (2, 85, 1), (3, 88, 1)],                # G -> A: climbs to E6
        10: [(0, 90, 0.5), (0.5, 88, 0.5), (1, 86, 3)],                     # F#6 E6 D6, home
    })

total = int((dc.DUR + 0.5) * SR)
L = np.zeros(total); R = np.zeros(total)
rng = np.random.default_rng(5)


def place(sig, s, pan=0.0, gain=1.0):
    a = (pan + 1) * math.pi / 4
    i = int(s * SR)
    m = min(len(sig), total - i)
    if m > 0:
        L[i:i + m] += sig[:m] * math.cos(a) * gain
        R[i:i + m] += sig[:m] * math.sin(a) * gain


def puff(gain=0.5):
    """A breathy 'fft': low-passed noise with a quick swell and a short tail."""
    n = int(0.32 * SR)
    t = np.arange(n) / SR
    _, lo, _ = svf(noise(n), 1400 - 900 * np.minimum(1, t / 0.25), 0.8)
    env = np.minimum(1, t / 0.015) * np.exp(-t / 0.08)
    return gain * norm(lo) * env


hz = music2.hz
place(tock(560, 0.16), 0.25, 0, 1.0)                                       # hook
place(tock(700, 0.12), 0.6, 0, 1.0)                                        # row labels
n = int(dc.DUR * SR)                                                       # soft candle crackle bed
cr = np.zeros(n)
for _ in range(160):
    i = int(rng.uniform(0, n - 600))
    cr[i:i + 400] += rng.uniform(0.2, 1.0) * np.exp(-np.arange(400) / 40) * rng.standard_normal(400)
_, _, cr = svf(cr, np.full(n, 3000.0), 0.7)
place(norm(cr) * 0.05, 0.0, 0, 1.0)

for d, td in enumerate(dc.T_DAY):                                          # days: gust + rising tick
    place(whoosh(0.55, 300, 1800, 1.1, 0.35, 0.45), td - 0.05, -0.6 + 0.12 * d, 0.8)
    place(tock(480 + 40 * d, 0.13), td, 0, 1.0)
for row, ps in (("cant", dc.CANT), ("dont", dc.DONT)):                     # candles going out
    for i, p in enumerate(ps):
        ot = dc.out_time(p)
        if ot is not None:
            pan = (dc.XS[i] - 540) / 540 * 0.7
            place(puff(0.45), ot - 0.03, pan, 1.0)
            place(thump(0.08, 180, 90, 0.02, 0.01), ot, pan, 0.12)

place(whoosh(1.3, 250, 3600, 0.9, 0.3, 0.85), 8.75, 0, 0.9)                # pull into the drop
place(impact(1.0, heavy=True), dc.T_DROP, 0, 0.5)
for k, m in enumerate((74, 78, 81, 86)):                                    # flames flare: D chord shimmer
    place(tinkle(hz(m + 12), 0.10), dc.T_DROP + 0.05 + 0.06 * k, -0.4 + 0.27 * k, 1.0)
place(tock(620, 0.12), 10.4, -0.2, 1.0)                                     # counts slide in
place(tinkle(hz(93), 0.10), 10.45, 0.2, 1.0)
place(tinkle(hz(98), 0.12), 14.6, 0, 1.0)                                   # payoff text
place(tinkle(hz(102), 0.1), 14.75, 0.2, 1.0)
place(tinkle(hz(105), 0.08), 14.9, -0.2, 1.0)

sfx = np.stack([L, R], 1)[: int(dc.DUR * SR)]
mus = music2.render_music()
mus = mus / (np.max(np.abs(mus)) + 1e-9)
mix = mus * 0.62 + sfx * 0.85
mix = np.tanh(1.25 * mix) / np.tanh(1.25)
mix *= 0.70 / np.max(np.abs(mix))
fade = int(0.01 * SR)
mix[:fade] *= np.linspace(0, 1, fade)[:, None]
out = sys.argv[1] if len(sys.argv) > 1 else "dontcant_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
