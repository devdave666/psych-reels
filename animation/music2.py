"""Layered, motivational track for the 'spotlight' reel. numpy only, no samples.

Key of D major, 120 BPM, 10 bars of 2 s (20 s).
Harmony:  Bm  G  | D  A | Em A  ||  D  A | Bm  G A | D
          vi  IV   I  V   ii V     I  V   vi  IV V    I
The build opens on the relative minor (vi) so it feels uneasy, climbs through I-V to a ii-V half cadence that begs
for resolution, and the drop (bar 6, t = 10 s) lands on the tonic D with a soaring lead.  Layers: pad, strings, vowel-formant
choir, electric piano, bell, pluck arp, bass, kick/snare/clap/hats/shaker/tambourine, supersaw lead with dotted-8th echo,
riser, reversed crash and a snare roll.
"""
import math

import numpy as np

import music as m1                                   # drum samples, bass, riser (shared with the first track)
from synth import SR, noise, norm, room, svf, thump

BPM = 120.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT                                       # 2.0 s
NBARS = 10
DUR = NBARS * BAR                                    # 20.0 s
N = int((DUR + 3.0) * SR)

CH = {"Bm": (59, 62, 66), "G": (59, 62, 67), "D": (62, 66, 69), "A": (61, 64, 69), "Em": (59, 64, 67)}
ROOT = {"Bm": 35, "G": 31, "D": 38, "A": 33, "Em": 40}
PROG = [["Bm"], ["G"], ["D"], ["A"], ["Em", "A"], ["D"], ["A"], ["Bm"], ["G", "A"], ["D"]]
# lead, bars 6-10: (beat, MIDI, beats).  F#5 A5 D6 ... climbs to E6, answers down, then lands on D6.
MELODY = {
    6: [(0, 78, 1), (1, 81, 1), (2, 86, 1.5), (3.5, 85, 0.5)],
    7: [(0, 83, 1), (1, 85, 1), (2, 88, 2)],
    8: [(0, 86, 1.5), (1.5, 83, 0.5), (2, 78, 1), (3, 83, 1)],
    9: [(0, 86, 1), (1, 83, 1), (2, 85, 1), (3, 81, 1)],
    10: [(0, 78, 0.5), (0.5, 81, 0.5), (1, 86, 3)],
}
PADFC = {1: 600, 2: 750, 3: 950, 4: 1300, 5: 1800, 6: 3600, 7: 3600, 8: 3600, 9: 3800, 10: 3200}
PADG = {1: 0.5, 2: 0.55, 3: 0.6, 4: 0.65, 5: 0.7, 6: 0.85, 7: 0.85, 8: 0.85, 9: 0.9, 10: 0.9}


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def bar_t(b):
    return (b - 1) * BAR


def tvec(d):
    return np.arange(int(d * SR)) / SR


def bus():
    return [np.zeros(N), np.zeros(N)]


DRY, MUS, WET = bus(), bus(), bus()                  # dry (drums, lead), sidechained music, reverb send
KICKS = []


def add(b, sig, t0, pan=0.0, gain=1.0):
    i = int(t0 * SR)
    m = min(len(sig), N - i)
    if m <= 0:
        return
    a = (pan + 1) * math.pi / 4
    b[0][i:i + m] += sig[:m] * math.cos(a) * gain
    b[1][i:i + m] += sig[:m] * math.sin(a) * gain


def add_st(b, l, r, t0, gain=1.0):
    i = int(t0 * SR)
    m = min(len(l), N - i)
    if m > 0:
        b[0][i:i + m] += l[:m] * gain
        b[1][i:i + m] += r[:m] * gain


# ---------------------------------------------------------------- instruments
def saw_stack(m, dur, cents, fc, vib=0.0, att=0.3, rel=0.6, kmax=36, rolloff=1.0):
    """Detuned band-limited saws spread across the stereo field. Returns (left, right)."""
    t = tvec(dur + rel)
    f0 = hz(m)
    env = np.minimum(1, t / att) * np.minimum(1, np.maximum(0, dur + rel - t) / rel)
    vf = 1 + vib * np.sin(2 * np.pi * 5.3 * t) * np.minimum(1, np.maximum(0, t - 0.3) / 0.5) if vib else None
    l = np.zeros(len(t)); r = np.zeros(len(t))
    for vi, c in enumerate(cents):
        f = f0 * 2 ** (c / 1200)
        ph = 2 * np.pi * np.cumsum(f * vf) / SR if vib else 2 * np.pi * f * t
        s = np.zeros(len(t))
        for k in range(1, int(min(kmax, fc * 3 / f)) + 1):
            s += np.sin(k * ph + vi * 1.7) / k ** rolloff / (1 + (k * f / fc) ** 2)
        pan = vi / max(1, len(cents) - 1)
        l += s * math.cos(pan * math.pi / 2); r += s * math.sin(pan * math.pi / 2)
    return l * env, r * env


def choir_note(m, dur, vowel="a"):
    """Sung 'ah'/'oo': a vibrato saw shaped by vowel formants, three voices."""
    formants = {"a": ((800, 90, 1.0), (1150, 100, 0.55), (2900, 180, 0.22)),
                "o": ((450, 60, 1.0), (800, 80, 0.4), (2830, 180, 0.08))}[vowel]
    t = tvec(dur + 0.8)
    f0 = hz(m)
    env = np.minimum(1, t / 0.4) * np.minimum(1, np.maximum(0, dur + 0.8 - t) / 0.7)
    l = np.zeros(len(t)); r = np.zeros(len(t))
    for vi, (c, rate) in enumerate(((-14, 5.0), (0, 5.4), (13, 5.8))):
        f = f0 * 2 ** (c / 1200)
        vf = 1 + 0.006 * np.sin(2 * np.pi * rate * t + vi) * np.minimum(1, np.maximum(0, t - 0.25) / 0.5)
        ph = 2 * np.pi * np.cumsum(f * vf) / SR
        s = np.zeros(len(t))
        for k in range(1, int(min(34, 4200 / f)) + 1):
            fk = k * f
            w = sum(g * math.exp(-0.5 * ((fk - fc) / bw) ** 2) for fc, bw, g in formants) + 0.03
            s += w * np.sin(k * ph + vi * 2.1) / k ** 0.55
        pan = vi / 2
        l += s * math.cos(pan * math.pi / 2); r += s * math.sin(pan * math.pi / 2)
    breath = norm(svf(noise(len(t)), np.full(len(t), 2400.0), 1.2)[0]) * 0.05
    return (l + breath) * env, (r + breath) * env


def ep(m, vel=0.8, dur=1.3):
    """FM electric piano with a short tine."""
    t = tvec(dur)
    f = hz(m)
    ph = 2 * np.pi * f * t
    idx = (0.9 + 1.6 * vel) * np.exp(-t * 5.0)
    s = np.sin(ph + idx * np.sin(ph)) * np.exp(-t * 2.3) + 0.12 * np.sin(14 * ph) * np.exp(-t * 28)
    return vel * 0.45 * s * np.minimum(1, t * 900)


def bell(m, vel=0.7, dur=1.8):
    t = tvec(dur)
    f = hz(m)
    s = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d)
            for a, r, d in ((1, 1, 2.2), (0.5, 2.76, 3.4), (0.28, 5.4, 5.0), (0.12, 8.9, 8.0)))
    return vel * 0.4 * s * np.minimum(1, t * 1500)


def lead_note(m, dur):
    l, r = saw_stack(m, dur, (-11, 0, 11), 4300, vib=0.0055, att=0.02, rel=0.3, kmax=26)
    ol, orr = saw_stack(m - 12, dur, (-5, 5), 1500, vib=0.0055, att=0.03, rel=0.3, kmax=14)
    return 0.1 * (l + 0.45 * ol), 0.1 * (r + 0.45 * orr)


def make_extras():
    n = int(0.09 * SR); t = np.arange(n) / SR
    _, _, hp = svf(noise(n), np.full(n, 6000.0), 0.8)
    shaker = norm(hp) * np.exp(-t / 0.022) * np.minimum(1, t * 400)
    n = int(0.3 * SR); t = np.arange(n) / SR
    _, _, hp = svf(noise(n), np.full(n, 8500.0), 1.2)
    tamb = norm(hp) * (np.exp(-t / 0.06) + 0.6 * np.exp(-np.maximum(0, t - 0.018) / 0.08) * (t > 0.018))
    return shaker, tamb


SHAKER, TAMB = make_extras()


# ---------------------------------------------------------------- arrangement
def arrange():
    for b in range(1, NBARS + 1):
        t0 = bar_t(b)
        segs = PROG[b - 1]
        for si, name in enumerate(segs):
            ln = 4 / len(segs)
            ts = t0 + si * ln * BEAT
            dur = ln * BEAT
            tones = CH[name]
            for m in tones:                                                        # pad
                l, r = saw_stack(m, dur, (-9, 0, 9), PADFC[b], att=0.35, rel=0.5, kmax=26)
                add_st(MUS, l, r, ts, PADG[b] * 0.13)
            if b >= 3:                                                             # strings, swelling toward the drop
                g = {3: 0.5, 4: 0.7, 5: 1.0}.get(b, 1.1)
                for m in tones:
                    l, r = saw_stack(m + 12, dur, (-13, -4, 5, 14), 2400 + 700 * (b >= 6), vib=0.0045, att=0.55, rel=0.5, kmax=30)
                    add_st(MUS, l, r, ts, g * 0.09)
                l, r = saw_stack(tones[0] - 12 + 12, dur, (-7, 7), 1100, vib=0.004, att=0.5, rel=0.5, kmax=16)
                add_st(MUS, l, r, ts, g * 0.1)                                      # cello line
            if b >= 5 or (b >= 3):                                                 # choir: 'oo' in the build, 'ah' in the drop
                vow = "o" if b < 6 else "a"
                g = {3: 0.25, 4: 0.35, 5: 0.5}.get(b, 0.8)
                for m in tones[1:] if b < 6 else tones:
                    l, r = choir_note(m + 12, dur, vow)
                    add_st(MUS, l, r, ts, g * 0.05)
                    add_st(WET, l, r, ts, g * 0.05)
        ch0 = CH[segs[0]]
        # electric piano
        if b <= 2:
            for i in range(4):
                add(DRY, ep(ch0[i % 3] + 12, 0.55), t0 + i * BEAT, -0.3 + 0.2 * i, 0.5)
        elif b <= 5:
            for i in range(8):
                nm = segs[min(len(segs) - 1, i // 4)]
                ts_ = CH[nm]
                add(DRY, ep(ts_[(0, 1, 2, 1)[i % 4] if i % 8 < 4 else (2, 1, 0, 1)[i % 4]] + 12, 0.6 + 0.04 * b), t0 + i * BEAT / 2, -0.2 + 0.1 * (i % 5), 0.5)
        elif b <= 9:
            for i in range(8):
                nm = segs[min(len(segs) - 1, i // 4)]
                add(DRY, ep(CH[nm][(0, 2, 1, 2)[i % 4]] + 12, 0.55), t0 + i * BEAT / 2, 0.3 - 0.1 * (i % 4), 0.38)
        else:
            for i, mm in enumerate(ch0):
                add(DRY, ep(mm + 12, 0.6, 2.4), t0 + i * 0.04, 0.1 * i - 0.1, 0.5)
        # high pluck arp (drop only)
        if 6 <= b <= 9:
            for i in range(16):
                nm = segs[min(len(segs) - 1, i // 8)]
                tn = CH[nm]
                m = tn[(0, 1, 2, 1, 2, 1, 0, 1)[i % 8]] + 24
                add(MUS, m1.pluck(m, 0.5, 0.6), t0 + i * BEAT / 4, -0.55 + 0.11 * (i % 10), 0.4)
                add(WET, m1.pluck(m, 0.35, 0.6), t0 + i * BEAT / 4, 0.4, 0.3)
        # bass
        for si, name in enumerate(segs):
            ln = 4 / len(segs)
            ts = t0 + si * ln * BEAT
            r_ = ROOT[name]
            if 3 <= b <= 5:
                add(MUS, m1.bass_note(r_, ln * BEAT * 0.95), ts, 0, 0.5)
            elif b >= 6:
                if b == 10:
                    add(MUS, m1.bass_note(r_, BAR), ts, 0, 0.6)
                else:
                    pat = [(0, 0.75, r_), (1, 0.5, r_), (1.5, 0.5, r_ + 12), (2, 0.75, r_), (3, 0.5, r_), (3.5, 0.5, r_ + 7)]
                    for beat, bl, mm in pat:
                        if beat < ln:
                            add(MUS, m1.bass_note(mm, bl * BEAT * 0.9), ts + beat * BEAT, 0, 0.62)
        # drums
        if b == 3:
            for beat in (0, 2):
                KICKS.append((t0 + beat * BEAT, 0.65))
        elif b == 4:
            for beat in range(4):
                KICKS.append((t0 + beat * BEAT, 0.8))
        elif b == 5:
            for beat in (0, 1):
                KICKS.append((t0 + beat * BEAT, 0.9))
        elif 6 <= b <= 9:
            for beat in range(4):
                KICKS.append((t0 + beat * BEAT, 1.0))
        elif b == 10:
            KICKS.append((t0, 1.0))
        if b in (4, 5):
            for i in range(8):
                add(DRY, m1.HAT, t0 + i * BEAT / 2, 0.3, 0.1 + 0.05 * (i % 2) + 0.03 * (b == 5))
        if 6 <= b <= 9:
            for beat in (1, 3):
                add(DRY, m1.CLAP, t0 + beat * BEAT, 0, 0.5)
                add(DRY, m1.SNARE, t0 + beat * BEAT, 0, 0.28)
                add(WET, m1.CLAP, t0 + beat * BEAT, 0, 0.35)
                add(DRY, TAMB, t0 + beat * BEAT, 0.25, 0.28)
            for i in range(16):
                add(DRY, m1.HAT, t0 + i * BEAT / 4, 0.35, 0.07 + 0.05 * (i % 4 == 0))
                add(DRY, SHAKER, t0 + i * BEAT / 4 + BEAT / 8 * 0, -0.3, 0.1 if i % 2 else 0.05)
            for beat in (0.5, 1.5, 2.5, 3.5):
                add(DRY, m1.OHAT, t0 + beat * BEAT, 0.3, 0.16)
        # lead + echo + bell
        for beat, m, ln in MELODY.get(b, []):
            l, r = lead_note(m, ln * BEAT)
            tt = t0 + beat * BEAT
            add_st(DRY, l, r, tt, 0.85)
            for k, g in ((1, 0.32), (2, 0.16), (3, 0.08)):                         # dotted-eighth echo
                add_st(WET, l, r, tt + 0.375 * k, 0.9 * g * 2)
            add_st(WET, l, r, tt, 0.6)
        if 6 <= b <= 10:
            tn = CH[segs[0]]
            add(DRY, bell(tn[2] + 24, 0.8), t0, 0.2, 0.5)
            add(WET, bell(tn[2] + 24, 0.8), t0, 0.2, 0.4)
            if b in (8, 9):
                for i, beat in enumerate((1.5, 2.5, 3.5)):
                    add(DRY, bell(tn[(1, 2, 0)[i]] + 24, 0.5), t0 + beat * BEAT, -0.3 + 0.3 * i, 0.3)
    # transitions
    rs = m1.riser(2 * BAR)
    add(DRY, rs, bar_t(4), 0, 0.3)
    add(WET, rs, bar_t(4), 0, 0.2)
    rc = m1.CRASH[::-1]
    add(DRY, rc, bar_t(6) - len(rc) / SR, 0, 0.45)
    t_roll = bar_t(5) + 2 * BEAT
    hits = [t_roll + i * 0.125 for i in range(4)] + [t_roll + 0.5 + j * 0.0625 for j in range(8)]
    for i, tt in enumerate(hits):
        add(DRY, m1.SNARE, tt, 0, 0.18 + 0.5 * i / len(hits))
    add(DRY, m1.CRASH, bar_t(6), 0, 0.6)
    add(WET, m1.CRASH, bar_t(6), 0, 0.3)
    add(DRY, m1.CRASH, bar_t(10), 0, 0.28)
    add(DRY, thump(1.2, 70, 30, 0.4, 0.05), bar_t(6), 0, 0.75)                      # sub boom on the drop


def sidechain():
    duck = np.ones(N)
    tau = np.arange(int(0.4 * SR)) / SR
    for tk, depth in KICKS:
        i = int(tk * SR)
        m = min(len(tau), N - i)
        duck[i:i + m] = np.minimum(duck[i:i + m], 1 - 0.5 * depth * np.exp(-tau[:m] / 0.12))
    return duck


def render_music():
    arrange()
    for tk, vel in KICKS:
        add(DRY, m1.KICK, tk, 0, 0.9 * vel)
    duck = sidechain()
    l = DRY[0] + MUS[0] * duck
    r = DRY[1] + MUS[1] * duck
    wl = WET[0] + 0.4 * MUS[0] + 0.22 * DRY[0]
    wr = WET[1] + 0.4 * MUS[1] + 0.22 * DRY[1]
    l = l + 0.3 * room(wl, 3, 1.5, 0.42)
    r = r + 0.3 * room(wr, 4, 1.5, 0.42)
    out = np.stack([l, r], 1)[: int(DUR * SR)]
    out = np.tanh(1.2 * out / (np.max(np.abs(out)) + 1e-9) * 1.1)
    fade = int(0.9 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.3
    return out


if __name__ == "__main__":
    import sys
    import wave
    o = render_music()
    o = o / np.max(np.abs(o)) * 0.89
    with wave.open(sys.argv[1] if len(sys.argv) > 1 else "music2.wav", "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((o * 32767).astype("<i2").tobytes())
    print("wrote", len(o) / SR, "s")
