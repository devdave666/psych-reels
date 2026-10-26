"""Small numpy sound-effect synth shared by the reels (no samples, no libraries)."""
import math

import numpy as np

SR = 48000
rng = np.random.default_rng(11)


def svf(x, fc, q):
    """Zero-delay-feedback state-variable filter, per-sample cutoff. Returns (bandpass, lowpass, highpass)."""
    g = np.tan(np.pi * np.clip(fc, 20, SR * 0.45) / SR)
    k = 1.0 / q
    n = len(x)
    bp = np.empty(n); lp = np.empty(n); hp = np.empty(n)
    ic1 = ic2 = 0.0
    a1 = 1.0 / (1.0 + g * (g + k)); a2 = g * a1; a3 = g * a2
    for i in range(n):
        v3 = x[i] - ic2
        v1 = a1[i] * ic1 + a2[i] * v3
        v2 = ic2 + a2[i] * ic1 + a3[i] * v3
        ic1 = 2 * v1 - ic1
        ic2 = 2 * v2 - ic2
        bp[i] = v1; lp[i] = v2; hp[i] = x[i] - k * v1 - v2
    return bp, lp, hp


def noise(n):
    return rng.standard_normal(n)


def norm(x):
    return x / (np.max(np.abs(x)) + 1e-9)


def whoosh(dur, f0, f1, q=1.4, gain=0.5, peak=0.7):
    n = int(dur * SR)
    u = np.linspace(0, 1, n)
    fc = f0 * (f1 / f0) ** u
    x = noise(n)
    bp, _, _ = svf(x, fc, q)
    _, lo, _ = svf(x, np.full(n, 500.0), 0.7)
    env = np.sin(np.pi * u ** (math.log(0.5) / math.log(peak))) ** 2
    return gain * (norm(bp) * env + 0.35 * norm(lo) * env ** 1.5) / 1.35


def thump(dur, f0, f1, decay, drop=0.03):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / drop)
    return np.tanh(1.6 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / decay))


def impact(power=1.0, heavy=False):
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    body = thump(0.5, 130 if heavy else 190, 34 if heavy else 48, 0.13 if heavy else 0.07, 0.035)
    _, lo, _ = svf(noise(n), np.full(n, 750.0 if heavy else 1100.0), 0.7)
    thud = norm(lo) * np.exp(-t / (0.07 if heavy else 0.045))
    bp, _, _ = svf(noise(n), np.full(n, 2600.0), 1.1)
    _, _, hp = svf(noise(n), np.full(n, 5000.0), 0.7)
    out = 0.85 * body + 0.7 * thud + 0.55 * norm(bp) * np.exp(-t / 0.012) + 0.35 * norm(hp) * np.exp(-t / 0.0018)
    return power * np.tanh(1.2 * out) / np.tanh(1.2)


def footstep(gain=0.35):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    _, lo, _ = svf(noise(n), np.full(n, 700.0), 0.7)
    return gain * (0.7 * thump(0.12, 120, 55, 0.03, 0.02) + 0.5 * norm(lo) * np.exp(-t / 0.02))


def dust(dur, gain=0.2):
    n = int(dur * SR)
    u = np.linspace(0, 1, n)
    _, lo, _ = svf(noise(n), np.full(n, 1800.0) * (1.2 - 0.6 * u), 0.7)
    return gain * norm(lo) * np.sin(np.pi * u ** 0.6) ** 2


def scuff(dur, gain=0.3):
    n = int(dur * SR)
    u = np.linspace(0, 1, n)
    bp, _, _ = svf(noise(n), np.full(n, 1300.0) * (1 - 0.4 * u), 0.9)
    return gain * norm(bp) * np.exp(-u * 3.0) * (0.6 + 0.4 * np.sin(2 * np.pi * 38 * u * dur))


def chalk(dur, gain=0.18):
    """Pencil/chalk scratch while a line is being drawn."""
    n = int(dur * SR)
    u = np.linspace(0, 1, n)
    bp, _, _ = svf(noise(n), np.full(n, 3800.0) * (1 + 0.15 * np.sin(2 * np.pi * 3 * u)), 0.9)
    am = 0.55 + 0.45 * np.abs(np.sin(2 * np.pi * 23 * u * dur * 0.5 + 6 * np.sin(2 * np.pi * 2.3 * u)))
    edge = np.minimum(1, np.minimum(u * 12, (1 - u) * 12))
    return gain * norm(bp) * am * edge


def tock(freq, gain=0.2):
    """Short woody tick; pitch passed in so a run of them can rise."""
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * np.cumsum(freq * (1 + 0.35 * np.exp(-t / 0.008))) / SR) * np.exp(-t / 0.022)
    _, _, hp = svf(noise(n), np.full(n, 4500.0), 0.7)
    return gain * (0.9 * tone + 0.3 * norm(hp) * np.exp(-t / 0.0012))


def room(sig, seed, size_s=0.35, decay=0.09):
    r = np.random.default_rng(seed)
    n = int(size_s * SR)
    ir = r.standard_normal(n) * np.exp(-np.arange(n) / SR / decay)
    ir[:int(0.004 * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2))
    size = 1 << (len(sig) + n).bit_length()
    return np.fft.irfft(np.fft.rfft(sig, size) * np.fft.rfft(ir, size), size)[:len(sig)]


# ---------------------------------------------------------------- cartoon extras
def _phase(f):
    return 2 * np.pi * np.cumsum(f) / SR


def boing(dur=0.4, f0=330.0, gain=0.25):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f0 * (1 + 0.55 * np.exp(-t / 0.14) * np.sin(2 * np.pi * 9 * t))
    return gain * np.sin(_phase(f)) * np.exp(-t / 0.16) * np.minimum(1, t * 400)


def squeak(dur, f0, f1, gain=0.25):
    n = int(dur * SR)
    u = np.linspace(0, 1, n)
    f = f0 * (f1 / f0) ** u * (1 + 0.03 * np.sin(2 * np.pi * 14 * u * dur))
    sig = np.sin(_phase(f)) + 0.35 * np.sin(2 * _phase(f))
    return gain * sig / 1.35 * np.sin(np.pi * np.clip(u, 0, 1) ** 0.8) ** 0.7


def whistle(dur, f0, f1, gain=0.25, trem=0.0):
    n = int(dur * SR)
    u = np.linspace(0, 1, n)
    f = f0 * (f1 / f0) ** u
    env = np.minimum(1, np.minimum(u * 20, (1 - u) * 6)) * (1 - trem + trem * (0.5 + 0.5 * np.sin(2 * np.pi * 11 * u * dur)))
    return gain * np.sin(_phase(f)) * env


def rumble(dur, gain=0.4):
    n = int(dur * SR)
    u = np.linspace(0, 1, n)
    _, lo, _ = svf(noise(n), np.full(n, 110.0), 0.9)
    sub = np.sin(_phase(np.full(n, 42.0) * (1 + 0.05 * np.sin(2 * np.pi * 5 * u * dur))))
    return gain * (norm(lo) * 0.8 + 0.5 * sub) * u ** 1.4 * np.minimum(1, (1 - u) * 20)


def roar(dur, gain=0.4):
    n = int(dur * SR)
    t = np.arange(n) / SR
    u = t / dur
    f0 = 72 * (1 + 0.06 * np.sin(2 * np.pi * 6 * t))
    ph = _phase(f0)
    sig = sum(np.sin(h * ph) / h for h in range(1, 9))
    bp, _, _ = svf(noise(n), np.full(n, 380.0), 1.5)
    am = 0.7 + 0.3 * np.sin(2 * np.pi * 15 * t)
    env = np.sin(np.pi * u) ** 0.6
    return gain * (norm(sig) * 0.7 + norm(bp) * 0.5) * am * env


def tinkle(f, gain=0.15):
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    return gain * (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.76 * t)) * np.exp(-t / 0.09)


def boom(gain=1.0):
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    _, lo, _ = svf(noise(n), np.full(n, 900.0), 0.7)
    body = thump(1.2, 85, 24, 0.45, 0.06)
    return gain * np.tanh(1.3 * (0.9 * body + 0.9 * norm(lo) * np.exp(-t / 0.22))) / np.tanh(1.3)
