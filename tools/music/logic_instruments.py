"""Read installed Logic instrument recordings for the finished stereo soundtrack.

Set PHASELINE_LOGIC_LIBRARY to relocate the Logic support folder. The matching
GarageBand support folder is normally its sibling. Source recordings and
individual notes are only read into memory. Score velocity controls articulation
and the mixer's channel fader controls the final volume.
"""
import os
import re
import struct
import warnings
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

LOGIC = Path(os.environ.get("PHASELINE_LOGIC_LIBRARY", "/Library/Application Support/Logic"))
GARAGEBAND = Path(os.environ.get("PHASELINE_GARAGEBAND_LIBRARY", LOGIC.parent / "GarageBand"))
ORCHESTRA = GARAGEBAND / "Instrument Library/Sampler/Sampler Files"
ALCHEMY = LOGIC / "Alchemy Samples"
PIANO_CAF = LOGIC / "EXS Factory Samples/01 Acoustic Pianos/Steinway Piano_consolidated.caf"
PIANO_EXS = LOGIC / "Sampler Instruments/01 Acoustic Pianos/Steinway Grand Piano 2.exs"

# These libraries use different octave conventions. The Mark II/organ names
# place C3 at MIDI 60. Their WAV root tags can contain sample indices instead
# (e.g. Mark II C3 says 16). Wind/string file names use C4 at MIDI 60.
BANKS = {
    "ep": (ALCHEMY / "Keys/Electric Pianos/EPiano Mrk II", 2),
    "organ": (ALCHEMY / "Organs/60s Transistor Organ", 2),
    "strings": (ORCHESTRA / "String Ensemble", 1),
    "flute": (ORCHESTRA / "Flute Solo/Flute_LV_na_sus_mf", 1),
    "flute_short": (ORCHESTRA / "Flute Solo/Flute_stac_mp1", 1),
    "clarinet": (ORCHESTRA / "Clarinet Solo/Clarinet-L_pA_sus_mf", 1),
    "clarinet_short": (ORCHESTRA / "Clarinet Solo/Clarinet_stac_f1", 1),
    "horn": (ORCHESTRA / "French Horns/French Horns_nA_sus_mf", 1),
    "horn_short": (ORCHESTRA / "French Horns/French Horns_stac_mf1", 1),
    "trumpet": (ORCHESTRA / "Trumpets/Trumpets_nA_sus_mf", 1),
    "trumpet_short": (ORCHESTRA / "Trumpets/Trumpets_stac_mf1", 1),
}
NOTE = re.compile(r"([A-G])(#?)(-?\d+)(?: M)?$")
SEMITONE = dict(zip("CDEFGAB", (0, 2, 4, 5, 7, 9, 11)))


@dataclass(frozen=True)
class Zone:
    path: Path
    root: float
    start: int = 0
    end: int = 0
    low_velocity: int = 0
    high_velocity: int = 127


@lru_cache(maxsize=1)
def _steinway_zones():
    # This is the single consolidated D-274 bank supplied with Logic. The EXS
    # zones reference frame ranges in its stereo CAF. Use the played notes and
    # four hammer dynamics. Pedal-down recordings belong to separate groups.
    raw = PIANO_EXS.read_bytes()
    groups = []
    regions = []
    pos = 0
    while pos + 84 <= len(raw):
        size = struct.unpack_from("<I", raw, pos + 4)[0]
        if raw[pos + 16:pos + 20] != b"TBOS":
            break
        kind = raw[pos + 3] & 0x0f
        data = raw[pos + 84:pos + 84 + size]
        if kind == 1:
            root = data[1]
            start, end = struct.unpack_from("<II", data, 12)
            group = struct.unpack_from("<I", data, 88)[0]
            regions.append((root, start, end, group))
        elif kind == 2:
            name = raw[pos + 20:pos + 84].split(b"\0")[0]
            groups.append((name, data[5], data[6]))
        pos += 84 + size
    zones = []
    for root, start, end, group in regions:
        name, lo, hi = groups[group]
        if b"pedal" not in name.lower():
            zones.append(Zone(PIANO_CAF, root, start, end, lo, hi))
    if not zones:
        raise ValueError(f"No Steinway note zones in {PIANO_EXS}")
    return zones


@lru_cache(maxsize=1)
def _piano_audio():
    with PIANO_CAF.open("rb") as audio:
        if audio.read(8)[:4] != b"caff":
            raise ValueError(f"Expected a CAF recording at {PIANO_CAF}")
        while header := audio.read(12):
            tag, length = struct.unpack(">4sq", header)
            if tag == b"desc":
                rate, codec, flags, _, _, channels, bits = struct.unpack(">d4s5I", audio.read(length))
                if (codec, flags, channels, bits) != (b"lpcm", 0, 2, 16):
                    raise ValueError(f"Unexpected Steinway recording format in {PIANO_CAF}")
            elif tag == b"data":
                # CAF edit count precedes the big-endian PCM.
                pcm = np.memmap(PIANO_CAF, dtype=">i2", mode="r", offset=audio.tell() + 4)
                return int(rate), pcm.reshape(-1, 2)
            else:
                audio.seek(length, 1)
    raise ValueError(f"No audio in {PIANO_CAF}")


@lru_cache(maxsize=None)
def _zones(bank):
    if bank == "piano":
        return _steinway_zones()
    directory, octave = BANKS[bank]
    zones = []
    for path in sorted(directory.glob("*.wav")):
        note = NOTE.search(path.stem)
        if note:
            letter, sharp, register = note.groups()
            pitch = (int(register) + octave) * 12 + SEMITONE[letter] + bool(sharp)
            zones.append(Zone(path, pitch))
    if not zones:
        raise FileNotFoundError(f"Install the Logic instrument samples in {directory}")
    return zones


@lru_cache(maxsize=180)
def _source(zone):
    if zone.end:
        rate, recording = _piano_audio()
        samples = recording[zone.start:zone.end]
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", wavfile.WavFileWarning)
            rate, samples = wavfile.read(zone.path)
    scale = float(2 ** (samples.dtype.itemsize * 8 - 1)) if samples.dtype.kind == "i" else 1.0
    samples = samples.astype(np.float32) / scale
    if samples.ndim == 1:
        samples = np.repeat(samples[:, None], 2, axis=1)
    # Preserve the room image and the breath, bow or hammer transient. The
    # pre-roll in some orchestral recordings exceeds an entire sixteenth note.
    amplitude = np.abs(samples).max(axis=1)
    peak = amplitude.max()
    onset = np.flatnonzero(amplitude > peak * 0.023)
    if not onset.size:
        raise ValueError(f"Silent Logic source in {zone.path}")
    start = max(0, onset[0] - round(rate * 0.0025))
    return rate, np.ascontiguousarray(samples[start:] * (0.78 / peak))


@lru_cache(maxsize=170)
def _transposed(zone, pitch, rate):
    source_rate, original = _source(zone)
    ratio = rate / source_rate * 2 ** ((zone.root - pitch) / 12)
    if abs(ratio - 1.0) < 0.00001:
        return original
    ratio = Fraction(ratio).limit_denominator(256)
    return resample_poly(original, ratio.numerator, ratio.denominator, axis=0)


def _note(bank, pitch, duration, velocity, variant, rate, release):
    zones = _zones(bank)
    if bank == "piano":
        # Select a real hammer strike, varying its brightness slightly between
        # repeated notes without changing the score or chart timing.
        dynamic = np.clip(round(velocity * 127) + (variant % 3 - 1) * 3, 1, 127)
        zones = [z for z in zones if z.low_velocity <= dynamic <= z.high_velocity]
    candidates = sorted(zones, key=lambda z: abs(z.root - pitch))
    index = 0
    # An alternate adjacent recording gives repeated notes a second attack.
    # Only do this when both recordings are naturally close to the requested key.
    if len(candidates) > 1 and variant % 5 == 3 and abs(candidates[1].root - pitch) <= 2:
        index = 1
    source = _transposed(candidates[index], pitch, rate)
    count = min(len(source), max(1, round((duration + release) * rate)))
    times = np.arange(count, dtype=np.float32) / rate
    attack = np.minimum(1, times / 0.0018)
    tail = np.exp(-4.7 * np.maximum(0, times - duration) / release)
    # A real staccato may already have decayed before the requested key-off.
    end = np.minimum(1, (count - 1 - np.arange(count)) / max(1, rate * 0.006))
    return source[:count] * (attack * tail * end).astype(np.float32)[:, None]


def _blend(primary, secondary, amount):
    mixed = np.zeros((max(len(primary), len(secondary)), 2), dtype=np.float32)
    mixed[:len(primary)] += primary * (1.0 - amount)
    mixed[:len(secondary)] += secondary * amount
    return mixed


def sampled_voice(style, kind, pitch, duration, velocity, variant, rate):
    """Return a stereo note in memory, or None for the oscillator parts."""
    def play(bank, release=0.15, dynamic=velocity):
        return _note(bank, pitch, duration, dynamic, variant, rate, release)

    if style == "wave" and kind in ("pluck", "bell"):
        return play("piano", 0.28 if kind == "bell" else 0.15,
                    dynamic=velocity * (0.57 if kind == "bell" else 0.91))
    if style == "garage" and kind == "glass":
        return play("piano", 0.22)
    if style == "garage" and kind == "pluck":
        return play("ep", 0.21)
    if style == "waltz" and kind == "felt":
        # The original Rhodes-like instrument runs out of sampled keys at F#4.
        # A touch of close-miked high piano supplies upper-register definition.
        ep = play("ep", 0.41)
        if pitch >= 69:
            return _blend(ep, play("piano", 0.31, dynamic=velocity * 0.57), 0.30)
        return ep
    if style == "waltz" and kind == "flute":
        return play("flute", 0.17)
    if style in ("breaks", "waltz") and kind == "pad":
        return play("strings", 0.23)
    if style == "breaks" and kind == "wire":
        # Short ensemble-horn attacks articulate the lower marching figure.
        # The string section supplies the sustained bow behind each accent.
        horn = play("horn_short" if duration < 0.35 else "horn", 0.12)
        return _blend(horn, play("strings", 0.11), 0.27)
    if style == "breaks" and kind == "reed":
        return play("clarinet_short" if duration < 0.29 else "clarinet", 0.13)
    if style == "house" and kind == "chip":
        return play("flute_short" if duration < 0.28 else "flute", 0.08)
    if style == "house" and kind == "brass":
        return play("trumpet_short" if duration < 0.31 else "trumpet", 0.115)
    if style in ("garage", "house") and kind == "organ":
        return play("organ", 0.065)
    return None
