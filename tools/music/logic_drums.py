"""Perform the score using local Logic Pro drum kits. Only complete mixes are exported."""
from functools import lru_cache
import os
from pathlib import Path
import subprocess

import numpy as np
from scipy import signal


LIBRARY = Path(os.environ.get('PHASELINE_LOGIC_LIBRARY', '/Library/Application Support/Logic'))
DMD = LIBRARY / 'Ultrabeat Samples' / 'Drum Machine Designer'

# Kick, main snare, ghost snare, clap layer and rim articulation.
KITS = {
    'wave': ('Neon', 'Kick_1', 'Snare_1', 'Snare_2', 'Clap_2', 'Block'),
    'garage': ('Beat Machine', 'Kick_2', 'Snare_2', 'Snare_3', 'Clap', 'Rim'),
    'waltz': ('Crate Digger', 'Kick_2', 'Snare_2', 'Snare_3', 'Clap_2', 'Rim'),
    'breaks': ('Pile Driver', 'Kick_1', 'Snare_1', 'Snare_3', 'Clap_2', 'Tom_High'),
    'house': ('Big Room', 'Kick_2', 'Snare_2', 'Snare_3', 'Clap_1', 'Click'),
}
ROOM_SEND = {'snare': 0.22, 'rim': 0.16, 'crash': 0.13, 'hat_open': 0.045}
DRUM_GAIN = {'kick': .94, 'snare': .81, 'rim': .58, 'hat': .49,
             'hat_open': .48, 'crash': .50, 'rise': .68}


@lru_cache(maxsize=90)
def kit_hit(kit, articulation, rate):
    name = f"{articulation}_{kit.replace(' ', '')}_GB.aif"
    path = DMD / (kit + ' GB') / name
    if not path.is_file():
        raise FileNotFoundError(f'Install the Logic Pro {kit} drum kit to render the soundtrack: {path}')
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-ar', str(rate),
                                   '-ac', '2', '-f', 'f32le', 'pipe:1'])
    stereo = np.frombuffer(raw, dtype='<f4').reshape(-1, 2)
    levels = np.max(np.abs(stereo), axis=1)
    peak = float(levels.max())
    attack = np.flatnonzero(levels > peak * .009)
    start = max(0, int(attack[0]) - round(rate * .0008))
    return stereo[start:] * (.88 / peak)


def _layer(main, other, gain, delay):
    out = np.zeros((max(len(main), delay + len(other)), 2), dtype=np.float32)
    out[:len(main)] = main
    out[delay:delay + len(other)] += other * gain
    return out


@lru_cache(maxsize=320)
def drum_voice(style, kind, duration, velocity_step, variant, rate):
    kit, kick, snare, ghost, clap, rim = KITS[style]
    if kind == 'rise':
        # A pitched noise sweep ends on the downbeat of the next section.
        t = np.arange(round(duration * rate)) / rate
        motion = t / duration
        rng = np.random.default_rng(901 + variant)
        noise = rng.standard_normal((len(t), 2))
        out = np.zeros_like(noise)
        for center, cutoff in enumerate([320, 850, 2100, 5200, 10400]):
            filt = signal.butter(2, [cutoff * .48, cutoff * 1.48], fs=rate, btype='bandpass', output='sos')
            band = signal.sosfilt(filt, noise, axis=0)
            window = np.maximum(0, 1 - np.abs(motion * 4 - center))
            out += band * window[:, None]
        out *= (.39 * motion**1.8 * np.minimum(1, (duration - t) / .008))[:, None]
        return out.astype(np.float32)
    if kind == 'snare':
        soft = velocity_step < 6
        sound = kit_hit(kit, ghost if soft else snare, rate)
        if not soft and style != 'waltz':
            level = .48 if style == 'wave' else .28
            sound = _layer(sound, kit_hit(kit, clap, rate), level, round(.008 * rate))
    elif kind == 'hat':
        # Alternate articulations for downbeats and lighter offbeats.
        sound = kit_hit(kit, 'Hi-Hat_2' if variant % 3 == 0 else 'Hi-Hat_1', rate)
    else:
        name = {'kick': kick, 'rim': rim, 'hat_open': 'Hi-Hat_Open', 'crash': 'Crash'}[kind]
        sound = kit_hit(kit, name, rate)
    # Let the real kit supply its attack, room and decay. Shorten only tails that
    # would mask the following notes, leaving crash cymbals room to ring out.
    tail = {'kick': .53, 'snare': .43, 'rim': .23, 'hat': .12, 'hat_open': .32, 'crash': 1.75}[kind]
    count = min(len(sound), int(tail * rate))
    out = sound[:count].copy()
    release = min(count, round(rate * (.048 if kind != 'crash' else .15)))
    out[-release:] *= np.linspace(1, 0, release, dtype=np.float32)[:, None]
    return out
