"""Objective audio check for a reel soundtrack (nobody can listen before it is live).
Usage: python check_audio.py file.wav [bar_seconds=2.0]
Prints the strongest pitch classes, RMS and peak per bar (compare with the intended chords), then overall LUFS / true peak
via ffmpeg. Targets: about -14 LUFS, peak below -2 dBFS, intro bars not below about -26 dB RMS."""
import subprocess
import sys
import wave

import numpy as np

path = sys.argv[1]
BAR = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
w = wave.open(path)
sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, 2).mean(1) / 32768
names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
for b in range(int(len(x) / sr / BAR)):
    s = x[int(b * BAR * sr):int((b + 1) * BAR * sr)]
    f = np.abs(np.fft.rfft(s * np.hanning(len(s))))
    fr = np.fft.rfftfreq(len(s), 1 / sr)
    m = (fr > 80) & (fr < 2000)
    pc = (np.round(12 * np.log2(fr[m] / 440) + 69).astype(int)) % 12
    ch = np.zeros(12)
    np.add.at(ch, pc, f[m] ** 2)
    top = np.argsort(ch)[::-1][:4]
    print(b + 1, [names[i] for i in top], "rms %.1f dB" % (20 * np.log10(np.sqrt((s ** 2).mean()) + 1e-9)), "peak %.2f" % np.abs(s).max())
r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
print("\n".join(l for l in r.stderr.splitlines() if "I:" in l or "Peak:" in l)[-200:])
