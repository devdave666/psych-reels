"""Music-theory synth for the 'Day 66' reel. No samples, numpy only.

Key of C major, 96 BPM, 8 bars (20 s). Progression I-vi-IV-V | I-V-IV-I:
bars 1-4 build (pad + sparse pluck, then bass, kick, riser, snare roll), bar 5 is the drop (t = 10 s), bars 5-8 are the
payoff with a lead melody that climbs to the tonic C6 and resolves in bar 8.
"""
import math

import numpy as np

from synth import SR, noise, norm, room, svf, thump

BPM = 96.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT                       # 2.5 s
NBARS = 8
DUR = NBARS * BAR                    # 20.0 s
N = int((DUR + 3.0) * SR)            # room for reverb tails

# chord tones as MIDI notes, bar by bar: C  Am  F  G | C  G  F  C
CHORDS = [(60, 64, 67), (60, 64, 69), (60, 65, 69), (59, 62, 67), (60, 64, 67), (59, 62, 67), (60, 65, 69), (60, 64, 67)]
ROOTS = [36, 33, 29, 31, 36, 31, 29, 36]
# lead melody for bars 5-8, as (beat in bar, MIDI note, length in beats). Climbs and lands on the tonic C6.
MELODY = {
    5: [(0, 76, 1.5), (1.5, 79, 0.5), (2, 81, 1), (3, 79, 1)],            # E5 G5 A5 G5  over C
    6: [(0, 74, 1.5), (1.5, 79, 0.5), (2, 83, 1), (3, 81, 1)],            # D5 G5 B5 A5  over G
    7: [(0, 81, 1.5), (1.5, 84, 0.5), (2, 81, 1), (3, 79, 1)],            # A5 C6 A5 G5  over F
    8: [(0, 76, 0.5), (0.5, 79, 0.5), (1, 84, 3.0)],                      # E5 G5 C6 (held) over C
}


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def bar_t(b):
    return (b - 1) * BAR


L = np.zeros(N); R = np.zeros(N)
WET_L = np.zeros(N); WET_R = np.zeros(N)         # reverb send
SC_L = np.zeros(N); SC_R = np.zeros(N)           # sidechained bus (pad, arp, bass)
KICKS = []


def add(bufL, bufR, sig, t0, pan=0.0, gain=1.0):
    i = int(t0 * SR)
    m = min(len(sig), N - i)
    if m <= 0:
        return
    a = (pan + 1) * math.pi / 4
    bufL[i:i + m] += sig[:m] * math.cos(a) * gain
    bufR[i:i + m] += sig[:m] * math.sin(a) * gain


def tvec(dur):
    return np.arange(int(dur * SR)) / SR


# ---------------------------------------------------------------- instruments
def pad_note(m, dur, fc, gain):
    """Three detuned band-limited saws with a static low-pass curve. Returns (left, right)."""
    t = tvec(dur + 0.7)
    f0 = hz(m)
    outs = []
    for cents, side in ((-9, 0), (0, 2), (9, 1)):
        f = f0 * 2 ** (cents / 1200)
        s = np.zeros(len(t))
        for k in range(1, int(min(26, fc * 3 / f)) + 1):
            s += np.sin(2 * np.pi * k * f * t) / k / (1 + (k * f / fc) ** 2)
        outs.append((s, side))
    env = np.minimum(1, t / 0.4) * np.minimum(1, np.maximum(0, (dur + 0.7 - t)) / 0.65)
    l = sum(s for s, side in outs if side in (0, 2)) * env * gain
    r = sum(s for s, side in outs if side in (1, 2)) * env * gain
    return l, r


def pluck(m, vel=1.0, dur=0.9):
    t = tvec(dur)
    f = hz(m)
    s = np.zeros(len(t))
    for k in range(1, 7):
        s += np.sin(2 * np.pi * k * f * t) / k ** 1.2 * np.exp(-t * (2.4 + 1.8 * k))
    return vel * 0.5 * s * np.minimum(1, t * 600)


def lead_note(m, dur):
    t = tvec(dur + 0.35)
    f = hz(m)
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, np.maximum(0, t - 0.25) / 0.3)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    s = sum(np.sin(k * ph) / k / (1 + (k * f / 3200) ** 2) for k in range(1, 11))
    s = s + 0.45 * np.sin(0.5 * ph)                                   # sub-octave for body
    env = np.minimum(1, t / 0.03) * np.minimum(1, np.maximum(0, (dur + 0.35 - t)) / 0.3)
    return 0.34 * s * env


def bass_note(m, dur):
    t = tvec(dur + 0.08)
    ph = 2 * np.pi * hz(m) * t
    s = np.tanh(1.9 * (np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph))) * 0.8
    env = np.minimum(1, t / 0.008) * (0.72 + 0.28 * np.exp(-t / 0.25)) * np.minimum(1, np.maximum(0, (dur + 0.08 - t)) / 0.08)
    return 0.8 * s * env


def make_drums():
    n = int(0.45 * SR); t = np.arange(n) / SR
    kick = thump(0.45, 135, 42, 0.16, 0.03)
    _, _, hp = svf(noise(n), np.full(n, 3500.0), 0.8)
    kick = np.tanh(1.5 * (kick + 0.2 * norm(hp) * np.exp(-t / 0.004)))
    n = int(0.3 * SR); t = np.arange(n) / SR
    bp, _, _ = svf(noise(n), np.full(n, 1900.0), 1.0)
    snare = 0.8 * norm(bp) * np.exp(-t / 0.085) + 0.5 * np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.05)
    clap = np.zeros(n)
    for k, d in enumerate((0, 0.011, 0.023)):
        i = int(d * SR)
        clap[i:] += norm(bp)[:n - i] * np.exp(-np.arange(n - i) / SR / 0.012) * 0.6
    clap += 0.7 * norm(bp) * np.exp(-np.maximum(0, t - 0.035) / 0.07) * (t > 0.035)
    n = int(0.12 * SR); t = np.arange(n) / SR
    _, _, hp = svf(noise(n), np.full(n, 7000.0), 0.7)
    hat = norm(hp) * np.exp(-t / 0.018)
    n = int(0.4 * SR); t = np.arange(n) / SR
    _, _, hp = svf(noise(n), np.full(n, 6500.0), 0.7)
    ohat = norm(hp) * np.exp(-t / 0.09)
    n = int(2.2 * SR); t = np.arange(n) / SR
    _, _, hp = svf(noise(n), np.full(n, 5200.0), 0.7)
    bp, _, _ = svf(noise(n), np.full(n, 9000.0), 0.8)
    crash = (0.7 * norm(hp) + 0.4 * norm(bp)) * np.exp(-t / 0.55)
    return kick, snare, clap, hat, ohat, crash


KICK, SNARE, CLAP, HAT, OHAT, CRASH = make_drums()


def riser(dur):
    n = int(dur * SR); u = np.linspace(0, 1, n)
    bp, _, _ = svf(noise(n), 350 * (9000 / 350) ** u, 1.6)
    tone = np.sin(2 * np.pi * np.cumsum(392 * 4 ** u) / SR) * (0.5 + 0.5 * np.sin(2 * np.pi * 9 * u * dur))
    return (0.9 * norm(bp) + 0.25 * tone) * u ** 2.2


# ---------------------------------------------------------------- arrangement
def arrange():
    for b in range(1, NBARS + 1):
        t0 = bar_t(b)
        ch = CHORDS[b - 1]
        # pad: darker and quieter in the build, bright and wide from the drop
        fc = {1: 650, 2: 800, 3: 1200, 4: 1500}.get(b, 3200)
        g = {1: 0.5, 2: 0.55, 3: 0.65, 4: 0.7}.get(b, 0.85)
        for m in ch:
            l, r = pad_note(m, BAR, fc, g * 0.16)
            add(SC_L, SC_R, l, t0, -1.0, 1.0)      # left channel content stays left, right stays right
            add(SC_L, SC_R, r, t0, 1.0, 1.0)
        # arp / plucks (chord tones one octave up)
        tones = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[0] + 24]
        if b <= 2:                                  # sparse: one pluck per beat
            for i, idx in enumerate((0, 2, 1, 2)):
                add(L, R, pluck(tones[idx], 0.5), t0 + i * BEAT, -0.25 + 0.2 * i, 0.5)
        elif b <= 7:                                # 8th-note arpeggio
            vel = 0.55 if b <= 4 else 0.75
            for i, idx in enumerate((0, 1, 2, 3, 2, 1, 2, 1)):
                add(SC_L, SC_R, pluck(tones[idx], vel), t0 + i * BEAT / 2, -0.4 + 0.1 * (i % 5), 0.55)
                add(WET_L, WET_R, pluck(tones[idx], vel * 0.5), t0 + i * BEAT / 2, 0.3, 0.3)
        else:                                       # bar 8: ring out
            for i, idx in enumerate((0, 1, 2, 3)):
                add(L, R, pluck(tones[idx], 0.4, 1.4), t0 + i * BEAT, 0.2 * i - 0.3, 0.45)
        # bass from bar 3
        if b >= 3:
            root = ROOTS[b - 1]
            if b == 8:
                add(SC_L, SC_R, bass_note(root, BAR), t0, 0, 0.6)
                add(SC_L, SC_R, bass_note(root, BAR), t0, 0, 0.6)
            else:
                for beat, ln in ((0, 1.5), (1.5, 0.5), (2, 1.0), (3.5, 0.5)):
                    add(SC_L, SC_R, bass_note(root, ln * BEAT * 0.92), t0 + beat * BEAT, 0, 0.5 if b < 5 else 0.62)
        # drums
        if b == 3:
            for beat in (0, 2):
                KICKS.append((t0 + beat * BEAT, 0.65))
        elif 4 <= b <= 7:
            for beat in range(4):
                KICKS.append((t0 + beat * BEAT, 0.8 if b == 4 else 1.0))
        elif b == 8:
            KICKS.append((t0, 1.0))
        if b == 4:
            for i in range(8):
                add(L, R, HAT, t0 + i * BEAT / 2, 0.3, 0.12 + 0.05 * (i % 2))
        if 5 <= b <= 7:
            for beat in (1, 3):
                add(L, R, CLAP, t0 + beat * BEAT, 0, 0.5)
                add(WET_L, WET_R, CLAP, t0 + beat * BEAT, 0, 0.35)
            for i in range(16):
                add(L, R, OHAT if (i % 4 == 2 and b >= 6) else HAT, t0 + i * BEAT / 4, 0.35, 0.10 + 0.06 * (i % 4 == 0))
        # lead melody
        for beat, m, ln in MELODY.get(b, []):
            sig = lead_note(m, ln * BEAT)
            add(L, R, sig, t0 + beat * BEAT, 0.0, 0.7)
            add(WET_L, WET_R, sig, t0 + beat * BEAT, 0.0, 0.7)
    # transitions
    add(L, R, riser(BAR), bar_t(4), 0, 0.33)
    add(WET_L, WET_R, riser(BAR), bar_t(4), 0, 0.2)
    for i in range(int(((bar_t(5) - 0.12) - (bar_t(4) + 2 * BEAT + BEAT * 0.75)) / (BEAT / 4))):   # snare roll into the drop
        tt = bar_t(4) + 3.5 * BEAT + i * BEAT / 4
        v = 0.15 + 0.85 * i / 7.0
        add(L, R, SNARE, tt, 0, min(1.0, v) * 0.5)
    add(L, R, CRASH, bar_t(5), 0, 0.55)
    add(WET_L, WET_R, CRASH, bar_t(5), 0, 0.3)
    add(L, R, CRASH, bar_t(8), 0, 0.3)
    add(L, R, thump(1.0, 70, 30, 0.35, 0.05), bar_t(5), 0, 0.7)       # sub boom on the drop


def sidechain():
    duck = np.ones(N)
    tau = np.arange(int(0.45 * SR)) / SR
    for tk, depth in KICKS:
        i = int(tk * SR)
        m = min(len(tau), N - i)
        duck[i:i + m] = np.minimum(duck[i:i + m], 1 - 0.55 * depth * np.exp(-tau[:m] / 0.14))
    return duck


def render_music():
    arrange()
    for tk, vel in KICKS:
        add(L, R, KICK, tk, 0, 0.9 * vel)
    duck = sidechain()
    mixL = L + SC_L * duck
    mixR = R + SC_R * duck
    wl = WET_L + 0.45 * SC_L + 0.3 * L
    wr = WET_R + 0.45 * SC_R + 0.3 * R
    mixL = mixL + 0.26 * room(wl, 3, 1.4, 0.42)
    mixR = mixR + 0.26 * room(wr, 4, 1.4, 0.42)
    out = np.stack([mixL, mixR], 1)[: int(DUR * SR)]
    out = np.tanh(1.15 * out / (np.max(np.abs(out)) + 1e-9) * 1.1)
    fade = int(0.9 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.3
    return out


if __name__ == "__main__":
    import sys
    import wave
    o = render_music()
    o = o / np.max(np.abs(o)) * 0.89
    with wave.open(sys.argv[1] if len(sys.argv) > 1 else "music.wav", "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((o * 32767).astype("<i2").tobytes())
    print("wrote", len(o) / SR, "s")
