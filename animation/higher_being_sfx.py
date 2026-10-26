"""Synthesized sound effects locked to higher_being_reel's timeline. Usage: python higher_being_sfx.py [out.wav]
No music: effects only. Violet lane sits slightly left in the stereo field, amber slightly right."""
import math
import sys
import wave

import numpy as np

import higher_being_reel as hb
from synth import (SR, boing, dust, footstep, impact, room, scuff, squeak, svf, noise, thump, tinkle, tock, whistle,
                   whoosh)

total = int((hb.DUR + 0.6) * SR)
L = np.zeros(total); R = np.zeros(total)
PAN = {"v": -0.28, "a": 0.28, "c": 0.0}


def place(sig, s, lane="c", gain=1.0):
    a = (PAN[lane] + 1) * math.pi / 4
    i = int(s * SR)
    m = min(len(sig), total - i)
    if m > 0:
        L[i:i + m] += sig[:m] * math.cos(a) * gain
        R[i:i + m] += sig[:m] * math.sin(a) * gain


def buzz(dur=0.3, gain=0.3):
    n = int(dur * SR)
    t = np.arange(n) / SR
    car = np.tanh(3 * np.sin(2 * np.pi * 150 * t)) + 0.4 * np.sin(2 * np.pi * 300 * t)
    am = 0.55 + 0.45 * np.sign(np.sin(2 * np.pi * 34 * t))
    return gain * car * am * np.minimum(1, t * 300) * np.minimum(1, (dur - t) * 40) / 1.4


def steps(x_fn, t0, t1, stride, lane, gain):
    prev = None
    for s in np.arange(t0, t1, 0.004):
        k = math.floor(x_fn(s) / stride)
        if prev is not None and k != prev:
            place(footstep(gain), s, lane)
        prev = k


# --- violet: waits
place(tock(440, 0.18), 0.6, "v")
place(whoosh(0.4, 500, 1600, 1.0, 0.18, 0.6), 2.6, "v")                 # phone slides in
place(thump(0.1, 150, 60, 0.04) * 0.4, 3.1, "v")
for b in hb.VIO_PHONE_BUZZ:
    place(buzz(0.32, 0.3), b, "v")
place(thump(0.14, 120, 55, 0.05) * 0.45, 3.65, "v")                     # sits down
place(squeak(0.5, 300, 200, 0.12), 3.6, "v")
place(whistle(0.6, 300, 1500, 0.16), hb.T_SURGE, "v")                   # motivation surge
place(tock(660, 0.18), 5.5, "v")
place(whoosh(0.45, 400, 1800, 1.0, 0.32, 0.5), hb.T_SPRINT, "v")
steps(hb.vx_, 5.7, 8.6, 85.0, "v", 0.33)
place(whistle(2.0, 900, 180, 0.1), hb.T_DRAIN, "v")                     # motivation drains away
place(tock(300, 0.16), 8.6, "v")
place(squeak(0.9, 380, 150, 0.2), 8.5, "v")                             # sad wah
place(thump(0.12, 120, 55, 0.04) * 0.35, 8.9, "v")

# --- amber: the plan
place(tock(660, 0.18), 0.6, "a")
place(tock(880, 0.18), 1.1, "a")
for k, f in enumerate((2093, 2637, 2093, 2637)):                        # the trigger: an alarm bell
    place(tinkle(f, 0.17), hb.T_BELL + k * 0.1, "a")
place(whoosh(0.35, 400, 1400, 1.0, 0.22, 0.6), 1.75, "a")
steps(hb.ax_, 1.9, hb.T_ARR - 0.2, 115.0, "a", 0.3)
for b in hb.AMBER_BUZZ:
    place(buzz(0.28, 0.17), b, "a")
place(tock(660, 0.18), 4.6, "a")
place(tock(880, 0.18), 5.1, "a")

T = hb.T_ARR                                                            # arrival + celebration
place(whoosh(0.6, 500, 2200, 1.0, 0.3, 0.8), T - 0.1, "a")
for k, f in enumerate((1047, 1319, 1568, 2093)):
    place(tinkle(f, 0.2), T + k * 0.09, "a")
place(boing(0.4, 420, 0.22), T + 0.1, "a")
for k in range(2):
    place(thump(0.1, 160, 60, 0.04) * 0.45, T + 0.7 + k * 0.6, "a")
    place(dust(0.25, 0.08), T + 0.7 + k * 0.6, "a")
for _ in range(14):
    place(tinkle(float(np.random.default_rng(int(_)).uniform(1200, 2600)), 0.07), T + 0.2 + _ * 0.13, "a")

# --- outro
place(tock(520, 0.2), hb.OUTRO + 0.3, "c")
place(whoosh(0.5, 300, 900, 0.8, 0.2, 0.5), hb.OUTRO, "c")
place(tock(780, 0.2), 14.6, "c")
place(thump(0.4, 90, 40, 0.18) * 0.45, 14.6, "c")

wet = 0.1
L2 = L + wet * room(L, 1); R2 = R + wet * room(R, 2)
mix = np.stack([L2, R2], 1)
mix = np.tanh(1.1 * mix) / np.tanh(1.1)
mix = mix[: int(hb.DUR * SR)]
mix *= 0.89 / np.max(np.abs(mix))
fade = int(0.01 * SR)
mix[:fade] *= np.linspace(0, 1, fade)[:, None]; mix[-fade:] *= np.linspace(1, 0, fade)[:, None]

out = sys.argv[1] if len(sys.argv) > 1 else "higher_being_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", out, "%.2fs" % (len(mix) / SR), "peak %.2f" % np.max(np.abs(mix)))
