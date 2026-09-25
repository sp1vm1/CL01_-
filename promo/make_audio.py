"""Synthesizes the original soundtrack + hook SFX for the promo. No samples, no licensing.

128 BPM, A minor. Output: build/soundtrack.wav
"""
import os

import numpy as np
from scipy import signal
from scipy.io import wavfile

from timeline import (BEAT, SR, DURATION, t_of, A_OPEN, B_BUILD, STOP,
                      C_DROP, D_APP, E_PIVOT, F_END)

rng = np.random.default_rng(7)
N = int(DURATION * SR) + SR


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def place(buf, t, x, gain=1.0):
    i = int(t * SR)
    if i >= N:
        return
    x = x[: N - i]
    buf[i:i + len(x)] += gain * x


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def sos(kind, f, order=2):
    return signal.butter(order, f, btype=kind, fs=SR, output="sos")


# ---------- instruments ----------

def kick(big=False):
    d = 0.9 if big else 0.42
    n = int(d * SR)
    tt = np.arange(n) / SR
    f = 42 + 130 * np.exp(-tt / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * env_exp(n, 0.32 if big else 0.16)
    click = signal.sosfilt(sos("highpass", 2500), rng.standard_normal(n)) * env_exp(n, 0.003)
    return np.tanh(1.6 * x) + 0.25 * click


def boom():
    n = int(2.6 * SR)
    tt = np.arange(n) / SR
    f = 30 + 70 * np.exp(-tt / 0.08)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, 0.9)
    thud = signal.sosfilt(sos("lowpass", 900), rng.standard_normal(n)) * env_exp(n, 0.12)
    return np.tanh(1.8 * x) + 0.5 * thud


def clap():
    n = int(0.35 * SR)
    noise = signal.sosfilt(sos("bandpass", [900, 3200]), rng.standard_normal(n))
    e = np.zeros(n)
    for k, off in enumerate([0, 0.011, 0.022]):
        i = int(off * SR)
        e[i:] += env_exp(n - i, 0.006 if k < 2 else 0.11)
    return noise * e * 1.4


def hat(open_=False):
    n = int((0.28 if open_ else 0.06) * SR)
    x = signal.sosfilt(sos("highpass", 7000), rng.standard_normal(n))
    return x * env_exp(n, 0.07 if open_ else 0.012)


def pluck(note, dur=0.32, bright=1.0):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = midi(note)
    x = np.zeros(n)
    for h in range(1, 14):
        if f * h > 12000:
            break
        x += (1.0 / h) * np.sin(2 * np.pi * f * h * tt + 0.3 * h) * np.exp(-tt * (6 + 5.5 * h / bright))
    return x * (1 - np.exp(-tt / 0.002))


def pad(notes, dur, attack=0.6, release=0.8, cutoff=2400):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    x = np.zeros(n)
    for note in notes:
        for det in (-0.09, 0.0, 0.11):
            f = midi(note + det)
            for h in range(1, 9):
                x += ((-1) ** h / h) * np.sin(2 * np.pi * f * h * tt + rng.uniform(0, 6))
    x = signal.sosfilt(sos("lowpass", cutoff), x)
    e = np.minimum(1, tt / attack) * np.minimum(1, (dur - tt) / release).clip(0)
    return x * e / (len(notes) * 3)


def sub(note, dur):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    x = np.sin(2 * np.pi * midi(note) * tt)
    return np.tanh(1.3 * x) * np.minimum(1, tt / 0.005) * np.minimum(1, (dur - tt) / 0.02).clip(0)


def riser(dur):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    blk = 1024
    zi = None
    for i in range(0, n, blk):
        fc = 400 + 9000 * (i / n) ** 2
        s = sos("bandpass", [fc * 0.6, min(fc * 1.6, 20000)])
        if zi is None:
            zi = signal.sosfilt_zi(s) * 0
        seg, zi = signal.sosfilt(s, noise[i:i + blk], zi=zi)
        out[i:i + blk] = seg
    sweep = np.sin(2 * np.pi * np.cumsum(180 + 1400 * (tt / dur) ** 2.2) / SR) * 0.25
    return (out * 1.2 + sweep) * (tt / dur) ** 2.2


def key_click():
    n = int(0.05 * SR)
    x = signal.sosfilt(sos("bandpass", [1800, 6000]), rng.standard_normal(n)) * env_exp(n, 0.004)
    thump = np.sin(2 * np.pi * 180 * np.arange(n) / SR) * env_exp(n, 0.01)
    return x + 0.4 * thump


def error_tone(f, dur):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * f * 2 * tt) + 0.15 * np.sign(np.sin(2 * np.pi * f * tt))
    return x * env_exp(n, dur / 3) * np.minimum(1, tt / 0.003)


# ---------- arrangement ----------
B = BEAT
drums = [np.zeros(N), np.zeros(N)]
music = [np.zeros(N), np.zeros(N)]
fx = [np.zeros(N), np.zeros(N)]


def put(bus, t, x, gain=1.0, pan=0.0):
    place(bus[0], t, x, gain * np.sqrt(0.5 * (1 - pan)))
    place(bus[1], t, x, gain * np.sqrt(0.5 * (1 + pan)))


# Hook: late-night typing, then the "no results" error
for t in [0.05, 0.16, 0.24, 0.37, 0.45, 0.53, 0.66, 0.74]:
    put(fx, t, key_click(), 0.35, rng.uniform(-0.3, 0.3))
put(fx, 0.80, key_click(), 0.6)            # Enter
put(fx, 0.95, error_tone(392, 0.22), 0.35)
put(fx, 1.13, error_tone(311, 0.34), 0.35)
room_n = int(1.6 * SR)
put(fx, 0.0, signal.sosfilt(sos("lowpass", 220), rng.standard_normal(room_n)) * 0.05)

# A: black screen, a boom on each phrase (every 2 beats), dark drone underneath
for k in range(A_OPEN, B_BUILD, 2):
    put(drums, t_of(k), kick(big=True), 0.95)
put(music, t_of(A_OPEN), pad([45, 52, 57], (B_BUILD - A_OPEN) * B + 0.4, attack=1.2, cutoff=900), 0.55)
for k in range(A_OPEN + 4, B_BUILD):
    put(drums, t_of(k + 0.5), hat(), 0.18, 0.2)

# B: build — four on the floor, 16th hats, snare roll accelerating, riser; beat 27 is dead silent
prog_build = [57, 53, 60, 55]
for k in range(B_BUILD, STOP):
    put(drums, t_of(k), kick(), 0.9)
    for s in range(4):
        put(drums, t_of(k + s / 4), hat(), 0.14 + 0.05 * (s == 2), 0.25 * (-1) ** s)
    if k % 2 == 1:
        put(drums, t_of(k), clap(), 0.45)
    chord_root = prog_build[((k - B_BUILD) // 4) % 4]
    for s in (0, 0.75, 1.5, 2.25, 3.0) if (k - B_BUILD) % 4 == 0 else ():
        put(music, t_of(k + s), pluck(chord_root + 12, 0.25, 0.7), 0.22, 0.3)
roll = []
for k in range(STOP - 4, STOP):
    div = 4 if k < STOP - 2 else 8
    for s in range(div):
        roll.append(k + s / div)
for i, b in enumerate(roll):
    put(drums, t_of(b), clap(), 0.12 + 0.35 * i / len(roll))
put(fx, t_of(B_BUILD + 4), riser((STOP - B_BUILD - 4) * B), 0.5)
put(music, t_of(B_BUILD), pad([45, 52, 60, 64], (STOP - B_BUILD) * B, attack=2.5, release=0.02, cutoff=1600), 0.45)

# C + D: the drop. Am9 – Fmaj7 – Cmaj7 – Em7, pluck motif, sub, clap on 2 & 4, offbeat open hats
chords = [
    (45, [57, 60, 64, 67, 71]),
    (41, [57, 60, 64, 65, 69]),
    (48, [55, 59, 60, 64, 67]),
    (40, [55, 59, 62, 64, 67]),
]
motif = [0, 2, 4, 2, 3, 1, 4, 2, 0, 2, 4, 3, 2, 4, 1, 3]   # indices into the chord tones, 16ths
put(fx, t_of(C_DROP), boom(), 0.8)
for k in range(C_DROP, E_PIVOT):
    bar_pos = (k - C_DROP) % 16
    root, tones = chords[bar_pos // 4]
    put(drums, t_of(k), kick(), 1.0)
    if k % 2 == 1:
        put(drums, t_of(k), clap(), 0.6)
    put(drums, t_of(k + 0.5), hat(open_=True), 0.2, 0.15)
    for s in (0.25, 0.75):
        put(drums, t_of(k + s), hat(), 0.12, -0.2)
    # sub ducks under the kick: start it just after, on the off-8th
    put(music, t_of(k + 0.12), sub(root, B * 0.8), 0.42)
    for s in range(4):
        idx = motif[((k - C_DROP) * 4 + s) % 16]
        put(music, t_of(k + s / 4), pluck(tones[idx] + 12, 0.3, 1.2), 0.2, 0.35 * (-1) ** s)
    if bar_pos % 4 == 0:
        put(music, t_of(k), pad(tones, 4 * B, attack=0.02, release=0.3, cutoff=3200), 0.35)
    if k >= D_APP and bar_pos % 4 == 2:
        put(music, t_of(k), pluck(tones[-1] + 24, 0.5, 2.0), 0.12, 0.6)

# E: pivot — drums gone, filtered pad + distant pluck, small riser into the end hit
put(music, t_of(E_PIVOT), pad([45, 57, 60, 64, 71], (F_END - E_PIVOT) * B, attack=0.05, release=0.3, cutoff=700), 0.7)
for k in range(E_PIVOT, F_END):
    for s in (0, 0.5):
        idx = motif[((k - E_PIVOT) * 2 + int(s * 2)) % 16]
        put(music, t_of(k + s), pluck(chords[0][1][idx] + 12, 0.5, 0.35), 0.14, 0.3 * (-1) ** k)
put(fx, t_of(F_END - 2), riser(2 * B), 0.35)

# F: end hit — resolve to C major, long tail
put(fx, t_of(F_END), boom(), 0.9)
put(drums, t_of(F_END), kick(big=True), 0.8)
put(music, t_of(F_END), pad([48, 55, 60, 64, 67, 71], 7 * B, attack=0.01, release=2.5, cutoff=4000), 0.8)
for i, note in enumerate([72, 76, 79, 83]):
    put(music, t_of(F_END + i * 0.25), pluck(note, 1.2, 1.6), 0.16, 0.4 * (-1) ** i)


# ---------- mix ----------
def reverb(x, seconds=2.2, wet=0.25):
    n = int(seconds * SR)
    ir = rng.standard_normal(n) * env_exp(n, seconds / 6)
    ir = signal.sosfilt(sos("lowpass", 6000), ir)
    ir /= np.sqrt(np.sum(ir ** 2))
    return x + wet * signal.fftconvolve(x, ir)[: len(x)]


def sidechain(x):
    g = np.ones(N)
    for k in range(C_DROP, E_PIVOT):
        i = int(t_of(k) * SR)
        n = int(0.22 * SR)
        g[i:i + n] = np.minimum(g[i:i + n], 1 - 0.6 * np.exp(-np.arange(n) / (0.06 * SR)))
    return x * g


out = []
for ch in range(2):
    m = reverb(sidechain(music[ch]), 2.6, 0.35)
    d = drums[ch]
    f = reverb(fx[ch], 1.8, 0.3)
    mix = 0.9 * m + 1.0 * d + 0.9 * f
    mix = signal.sosfilt(sos("highpass", 28), mix)
    out.append(mix)
mix = np.stack(out, axis=1)
# Hard silence for the stop beat (tails included) — that's the point of it
i0, i1 = int(t_of(STOP) * SR), int(t_of(C_DROP) * SR)
fade = int(0.01 * SR)
mix[i0:i0 + fade] *= np.linspace(1, 0, fade)[:, None]
mix[i0 + fade:i1] = 0
mix = np.tanh(1.3 * mix / np.max(np.abs(mix)) * 1.4)
mix = mix / np.max(np.abs(mix)) * 0.89
mix = mix[: int(DURATION * SR)]

os.makedirs("build", exist_ok=True)
wavfile.write("build/soundtrack.wav", SR, (mix * 32767).astype(np.int16))
print("wrote build/soundtrack.wav", mix.shape[0] / SR, "s")
