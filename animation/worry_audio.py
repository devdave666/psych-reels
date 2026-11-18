"""Soundtrack for worry_reel: B major (music2, shift -3), a minor-leaning build that clears into the drop.
Build:  Bm  Em  G  F#m  Em/A   (vi ii IV iii ii/V)  ->  drop:  D  Em  Bm  G/A  D   (I ii vi IV/V I)
In B major that sounds as G#m C#m E D#m C#m/F# ... B.
Sound effects follow the picture: a thunder crack and rumble on the hook flash (wr.T_FLASH), a rain bed whose level follows
how many dark clouds are left, a soft 'poof' plus a rising chime each time a cloud breaks (wr.T_CLEAR, 4.2 - 8.8 s, the
chimes climb the scale), tocks on the two text changes (3.6, 6.8 s), an impact and shimmer when the sun breaks out
(10.0 s), and sparkles on the payoff (14.6 s).
Usage: python worry_audio.py [out.wav]"""
import math
import sys
import wave

import numpy as np

import music2
import worry_reel as wr
from synth import SR, impact, noise, norm, rumble, svf, tinkle, tock, whoosh

music2.CH["F#m"] = (61, 66, 69)
music2.ROOT["F#m"] = 42
music2.configure(
    shift=-3,
    prog=[["Bm"], ["Em"], ["G"], ["F#m"], ["Em", "A"], ["D"], ["Em"], ["Bm"], ["G", "A"], ["D"]],
    melody={
        6: [(0, 74, 1), (1, 78, 1), (2, 81, 1.5), (3.5, 83, 0.5)],         # D5 F#5 A5 B5: the sun breaks out
        7: [(0, 83, 1), (1, 79, 1), (2, 76, 1), (3, 79, 1)],                # over Em: B5 G5 E5 G5
        8: [(0, 78, 1.5), (1.5, 81, 0.5), (2, 83, 2)],                      # over Bm: F#5 A5 B5
        9: [(0, 79, 1), (1, 83, 1), (2, 81, 1), (3, 85, 1)],                # G -> A: climbs to C#6
        10: [(0, 86, 0.5), (0.5, 85, 0.5), (1, 86, 3)],                     # D6 C#6 D6, home
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


def crack(gain=0.6):
    """Thunder crack: a bright noise burst with a fast decay."""
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    _, _, hi = svf(noise(n), np.full(n, 900.0), 0.7)
    return gain * norm(hi) * np.minimum(1, t / 0.003) * (np.exp(-t / 0.05) + 0.4 * np.exp(-np.maximum(0, t - 0.15) / 0.07) * (t > 0.15))


hz = music2.hz
place(crack(0.7), wr.T_FLASH, 0, 1.0)                                      # hook: lightning
place(rumble(2.6, 0.7), wr.T_FLASH + 0.05, 0, 0.8)

# rain bed: level follows the dark clouds still in the sky (10 at the start, 1 left until the drop)
n = int(wr.DUR * SR)
tt = np.arange(n) / SR
dark = np.ones(n) * 10
for tc in wr.T_CLEAR:
    dark -= np.clip((tt - tc) / 0.4, 0, 1)
dark -= np.clip((tt - wr.T_DROP) / 0.4, 0, 1)
lvl = (dark / 10) * np.clip(tt / 0.6, 0, 1)
for ch, seed_pan in ((L, -1), (R, 1)):
    bp, _, _ = svf(noise(n), np.full(n, 4200.0), 0.6)
    ch[:n] += 0.10 * norm(bp) * lvl

place(tock(640, 0.12), 3.6, -0.3, 1.0)                                     # text changes
place(tock(700, 0.12), 6.8, 0.3, 1.0)
scale = [71, 74, 76, 78, 81, 83, 86, 88, 90]                               # chimes climb as clouds break
for k, (ci, tc) in enumerate(zip(wr.ORDER, wr.T_CLEAR)):
    pan = (wr.CLOUDS[ci][0] - 540) / 540 * 0.7
    place(whoosh(0.7, 900, 300, 0.9, 0.3, 0.25), tc, pan, 0.6)
    place(tinkle(hz(scale[k] + 12), 0.10), tc + 0.05, pan, 1.0)

place(whoosh(1.3, 250, 3600, 0.9, 0.3, 0.85), 8.75, 0, 0.9)                # pull into the drop
place(impact(1.0, heavy=True), wr.T_DROP, 0, 0.5)
for k, m in enumerate((74, 78, 81, 86, 90)):                                # sun shimmer: D chord
    place(tinkle(hz(m + 12), 0.10), wr.T_DROP + 0.05 + 0.07 * k, -0.5 + 0.25 * k, 1.0)
place(tinkle(hz(98), 0.12), 14.6, 0, 1.0)                                   # payoff text
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
out = sys.argv[1] if len(sys.argv) > 1 else "worry_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
