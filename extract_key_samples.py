"""Slice individual keystrokes out of a mechanical-keyboard recording into
sfx/keys/*.wav for render_typewriter_reel.py.

Usage:
    python3 extract_key_samples.py <recording.mp4|wav> [out_dir=sfx/keys]

Onsets are picked from the >1.5kHz envelope (the sharp click). Each sample
runs from just before the click until the next onset (max MAX_LEN), with a
short fade, so overlapping fast typing never leaks a neighbour's click into
a sample. The deepest-sounding samples are written as space-*.wav (used for
the space bar and line breaks); the rest are key-*.wav. Very quiet onsets
(key releases / ghost taps) are dropped.
"""
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

SR = 48000
PRE = 0.006          # seconds kept before the click peak
MAX_LEN = 0.14
MIN_LEN = 0.055      # shorter than this is too clipped to reuse
MIN_REL_PEAK = 0.35  # onset peak vs loudest onset
N_SPACE = 3


def load(path):
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-vn", "-ac", "1",
                        "-ar", str(SR), "-c:a", "pcm_s16le", wav], check=True)
        with wave.open(wav) as w:
            return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768


def find_onsets(x):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[f < 1500] = 0
    hp = np.fft.irfft(X, len(x))
    hop = SR // 1000
    e = np.sqrt(np.convolve(hp ** 2, np.ones(hop) / hop, "same"))[::hop]   # 1 ms envelope
    thr = e.max() * 0.12
    ons = [i for i in range(len(e)) if e[i] > thr and e[i] == e[max(0, i - 25): i + 26].max()]
    return ons, e


def write(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def main(src, out_dir):
    x = load(src)
    ons, e = find_onsets(x)
    loudest = max(e[i] for i in ons)
    samples = []
    for k, ms in enumerate(ons):
        if e[ms] < MIN_REL_PEAK * loudest:
            continue
        nxt = ons[k + 1] if k + 1 < len(ons) else None
        end_ms = ms + MAX_LEN * 1000
        if nxt is not None:
            end_ms = min(end_ms, nxt - 3)
        a = max(int((ms / 1000 - PRE) * SR), 0)
        b = min(int(end_ms / 1000 * SR), len(x))
        if (b - a) / SR < MIN_LEN:
            continue
        s = x[a:b].copy()
        fi, fo = int(0.001 * SR), int(0.012 * SR)
        s[:fi] *= np.linspace(0, 1, fi)
        s[-fo:] *= np.linspace(1, 0, fo)
        s *= 0.8 / np.abs(s).max()
        spec = np.abs(np.fft.rfft(s)) ** 2
        centroid = (spec * np.fft.rfftfreq(len(s), 1 / SR)).sum() / spec.sum()
        samples.append((centroid, s, ms))
    if len(samples) <= N_SPACE:
        raise SystemExit(f"only {len(samples)} usable keystrokes found - need more material")
    samples.sort(key=lambda t: t[0])
    os.makedirs(out_dir, exist_ok=True)
    for old in os.listdir(out_dir):
        if old.endswith(".wav"):
            os.remove(os.path.join(out_dir, old))
    for i, (c, s, ms) in enumerate(samples):
        name = f"space-{i + 1}.wav" if i < N_SPACE else f"key-{i - N_SPACE + 1:02d}.wav"
        write(os.path.join(out_dir, name), s)
        print(f"{name}: onset {ms}ms, {len(s) / SR * 1000:.0f}ms long, centroid {c:.0f}Hz")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "sfx/keys")
