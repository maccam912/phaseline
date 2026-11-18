"""Render the local soundtrack and its score-synchronous note charts.

Rebuild with Python 3, NumPy, SciPy, FFmpeg, and the licensed instruments in CREDITS.md.
The game ships the finished audio and charts and has no build-time dependency.
"""
import argparse
from functools import lru_cache
import hashlib
import json
import math
import re
import tempfile
from pathlib import Path
import subprocess

import numpy as np
from scipy import signal

from scores import album
from charts import build_charts
from logic_drums import drum_voice, DRUM_GAIN, ROOM_SEND

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'music'
RATE = 44100
ORIGIN = .04
TAU = 2 * np.pi
DRUMS = {'kick', 'snare', 'rim', 'hat', 'hat_open', 'crash', 'rise'}
PITCHED = {
    'pluck': (.003, .13, .56), 'bell': (.004, .41, .60), 'felt': (.008, .28, .66),
    'glass': (.003, .23, .59), 'reed': (.022, .12, .65), 'flute': (.052, .19, .70),
    'brass': (.012, .11, .64), 'wire': (.005, .10, .61), 'chip': (.004, .08, .55),
    'pad': (.18, .48, .48), 'organ': (.004, .09, .67), 'bass': (.006, .09, .71),
    'sub': (.013, .21, .80), 'wobble': (.006, .11, .69),
}


def envelope(t, duration, attack, release):
    return np.minimum(1, t / attack) ** .72 * np.exp(-6.9 * np.maximum(0, t - duration) / release)


def saw(t, frequency, phase=0.0, motion=0.0):
    """Band-limited saw, with a polynomial correction around its discontinuity."""
    step = frequency / RATE
    p = (frequency * t + phase + motion) % 1
    y = 2 * p - 1
    rising = p < step
    u = p[rising] / step - 1
    y[rising] += u * u
    falling = p > 1 - step
    u = (p[falling] - 1) / step + 1
    y[falling] -= u * u
    return y


def moving_filter(stereo, cutoff):
    # Crossfade overlapping low-pass bands as the envelope opens and closes.
    # Each IIR has continuous state across the whole note.
    bank = (180, 470, 1250, 3300, 8700, 16000)
    position = np.interp(np.log(cutoff), np.log(bank), np.arange(len(bank)))
    filtered = np.zeros_like(stereo)
    for i, hz in enumerate(bank):
        weight = np.maximum(0, 1 - np.abs(position - i))
        if weight.max() > 0:
            sos = signal.butter(2, hz, fs=RATE, output='sos')
            filtered += signal.sosfilt(sos, stereo, axis=0) * weight[:, None]
    return filtered


@lru_cache(maxsize=160)
def synth_voice(kind, pitch, duration, velocity_step):
    """Original oscillator patches complement the acoustic and electric instruments."""
    amp = PITCHED[kind]
    attack, release, gain = amp
    frequency = 440 * 2 ** ((pitch - 69) / 12)
    t = np.arange(round((duration + release) * RATE)) / RATE
    phase = TAU * frequency * t
    velocity = .4 + .6 * velocity_step / 12
    bass = kind in ('bass', 'wobble', 'sub')
    if kind == 'sub':
        mono = .83 * np.sin(phase) + .19 * np.sin(2 * phase) * np.exp(-2.8 * t)
        stereo = np.column_stack((mono, mono))
    elif bass:
        pulse = .5 + .5 * np.cos(TAU * (2.0 if kind == 'wobble' else .45) * t)
        # The sub is mono. The upper harmonics give the line a voice on laptop speakers.
        dry = saw(t, frequency, .18)
        detune = .0032 if kind == 'wobble' else .0018
        spread = np.column_stack((saw(t, frequency * (1 - detune), .21),
                                  saw(t, frequency * (1 + detune), .24)))
        waves = .56 * dry[:, None] + .44 * spread
        cutoff = (460 + 2400 * np.exp(-6 * t) + (1150 if kind == 'wobble' else 360) * pulse) * velocity
        harmonics = moving_filter(waves, cutoff)
        stereo = .66 * harmonics + .45 * np.sin(phase)[:, None] + .19 * np.sin(2 * phase)[:, None]
        stereo = np.tanh(stereo * 1.5)
    elif kind in ('pad', 'reed', 'brass', 'chip', 'pluck', 'wire'):
        pad = kind == 'pad'
        lead = kind in ('reed', 'brass')
        depth = (.09 if lead else .05) * (1 - np.exp(-3.8 * t))
        vibrato = depth * np.sin(TAU * (4.65 if lead else .67) * t)
        center = saw(t, frequency, .2, vibrato)
        detune = .0043 if pad else .0024
        left = saw(t, frequency * (1 - detune), .47, vibrato)
        right = saw(t, frequency * (1 + detune), .75, vibrato)
        waves = .55 * center[:, None] + .45 * np.column_stack((left, right))
        if kind == 'chip':
            waves -= .55 * saw(t, frequency, .58, vibrato)[:, None]
        if pad:
            cutoff = 1250 + 2400 * (1 - np.exp(-1.4 * t))
        elif lead:
            cutoff = 1700 + 1600 * (1 - np.exp(-6 * t)) + 900 * np.exp(-5 * t)
        else:
            cutoff = 520 + 5500 * np.exp(-9.5 * t)
        stereo = moving_filter(waves, cutoff * velocity)
        stereo += .18 * np.sin(phase)[:, None]
        if kind in ('pluck', 'wire'):
            stereo *= (.25 + .75 * np.exp(-5 * t))[:, None]
    else:
        ratio = 2.001 if kind in ('bell', 'glass') else 1.0
        modulation = (2.1 if kind in ('bell', 'glass') else .65) * velocity * np.exp(-6 * t)
        mono = np.sin(phase + modulation * np.sin(ratio * phase)) + .18 * np.sin(2 * phase)
        stereo = np.column_stack((mono, mono))
        stereo *= (.45 + .55 * np.exp(-3 * t))[:, None]
    return (stereo * (envelope(t, duration, attack, release) * gain)[:, None]).astype(np.float32)


def seconds_for(s):
    return ORIGIN + (s.bars*s.beats_per_bar+3.3)*60/s.bpm + .8


def entry(s):
    fields = ('id','title','composer','work','year','source','genre','bpm','beats_per_bar','color')
    data = {field:getattr(s,field) for field in fields}
    data.update(beat_origin=ORIGIN, duration=round(seconds_for(s),4), audio=f'res://music/{s.id}.mp3', license='Original game soundtrack with licensed Apple Logic Pro sounds',
                arrangement_license='CC0-1.0', chart_license='CC0-1.0',
                preview=round(ORIGIN+s.preview_bar*s.beats_per_bar*60/s.bpm,4), charts=build_charts(s, ORIGIN))
    return data


def _plate(source, decay, rng):
    """A decorrelated stereo room using a generated impulse and early reflections."""
    t = np.arange(round(RATE * decay)) / RATE
    switches = ([(.016, .58), (.031, -.43), (.058, .31)],
                [(.020, .54), (.044, .38), (.069, -.31)])
    result = np.zeros_like(source)
    for side in range(2):
        noise = rng.normal(0, 1, len(t))
        sos = signal.butter(2, [330, 5800], btype='bandpass', fs=RATE, output='sos')
        tail = signal.sosfilt(sos, noise) * np.minimum(1, t / .027) * np.exp(-6.9 * t / decay)
        impulse = tail * (.85 / np.sqrt(np.sum(tail * tail)))
        for seconds, level in switches[side]:
            impulse[round(seconds * RATE)] += level
        feed = .78 * source[:, side] + .22 * source[:, 1 - side]
        result[:, side] = signal.oaconvolve(feed, impulse.astype(np.float32))[:len(feed)]
    return result


def _integrated_loudness(audio):
    info = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-f', 'f32le', '-ar', str(RATE),
                           '-ac', '2', '-i', 'pipe:0', '-af', 'ebur128=framelog=verbose',
                           '-f', 'null', '-'], input=audio.astype('<f4', copy=False).tobytes(),
                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
    values = re.findall(r'\bI:\s*(-?[\d.]+) LUFS', info.stderr.decode())
    return float(values[-1])


def _master(mix, target_lufs):
    mix = signal.sosfilt(signal.butter(2, 27, btype='highpass', fs=RATE, output='sos'),
                         mix, axis=0).astype(np.float32)
    # Leave transients intact up to the mastering ceiling. Use short look-ahead
    # and a gentler release to control isolated peaks without flattening the groove.
    mix *= 10 ** ((target_lufs - _integrated_loudness(mix)) / 20)
    block = 48
    padded = np.pad(np.max(np.abs(mix), axis=1), (0, -len(mix) % block))
    peaks = padded.reshape(-1, block).max(axis=1)
    ceiling = 10 ** (-1.6 / 20)
    goals = np.minimum(1, ceiling / np.maximum(peaks, 1e-8))
    ahead = np.pad(goals, (0, 5), mode='edge')
    goals = np.min(np.lib.stride_tricks.sliding_window_view(ahead, 6), axis=1)
    gain = np.empty_like(goals)
    level = 1.0
    recovery = 1 - np.exp(-block / (RATE * .074))
    for i, limit in enumerate(goals):
        level = min(limit, level + recovery * (1 - level))
        gain[i] = level
    env = np.interp(np.arange(len(mix)), np.arange(len(gain)) * block, gain)
    mix *= env[:, None]
    mix *= min(1, ceiling / max(1e-8, np.abs(mix).max()))
    mix[-round(RATE * .18):] *= np.linspace(1, 0, round(RATE * .18))[:, None]
    return mix


def render(s, target):
    from logic_instruments import sampled_voice

    beat_seconds = 60 / s.bpm
    frames = math.ceil(seconds_for(s) * RATE)
    buses = {key: np.zeros((frames, 2), np.float32)
             for key in ('drums', 'bass', 'melody', 'chords', 'room', 'echo')}
    rng = np.random.default_rng(4001 + int(hashlib.sha256(s.id.encode()).hexdigest()[:4], 16))
    duck = np.ones(frames, np.float32)
    release = {'wave': .115, 'house': .102, 'waltz': .082, 'breaks': .073, 'garage': .078}[s.style]
    recovery = np.exp(-np.arange(round(release * 4 * RATE)) / (RATE * release))
    for beat, kind, pitch, length, velocity, pan in s.events:
        start = round((ORIGIN + beat * beat_seconds) * RATE)
        # MIDI velocity also selects filters, articulations and drum layers.
        velocity_step = int(np.clip(round(velocity * 12), 1, 12))
        variant = int(rng.integers(0, 6))
        duration = round(length * beat_seconds, 5)
        if kind in DRUMS:
            audio = drum_voice(s.style, kind, duration, velocity_step, variant, RATE)
            bus, gain = 'drums', DRUM_GAIN[kind]
            room = ROOM_SEND.get(kind, .015)
            echo = 0.0
            if kind == 'kick':
                end = min(start + len(recovery), frames)
                depth = {'wave': .45, 'house': .56, 'waltz': .17, 'breaks': .33, 'garage': .4}[s.style]
                duck[start:end] = np.minimum(duck[start:end], 1 - velocity * depth * recovery[:end - start])
        else:
            audio = sampled_voice(s.style, kind, pitch, duration, velocity, variant, RATE)
            if audio is None:
                audio = synth_voice(kind, pitch, duration, velocity_step)
            elif kind == 'pluck' and s.style == 'wave':
                # A quiet stereo oscillator gives the piano ostinato its bright edge.
                analog = synth_voice(kind, pitch, duration, velocity_step)
                length_in_common = min(len(audio), len(analog))
                audio = audio.copy()
                audio[:length_in_common] += .24 * analog[:length_in_common]
            if kind in ('sub', 'bass', 'wobble'):
                bus, gain, room, echo = 'bass', .86, 0.0, 0.0
            elif kind in ('pad', 'organ'):
                bus, gain, room, echo = 'chords', (.62 if kind == 'pad' else .73), .18, .06
            else:
                bus, gain, room, echo = 'melody', .94, .205, .115
        if bus not in ('bass',) and kind != 'kick':
            pan += rng.uniform(-.032, .032)
        pan = np.clip(pan, -.92, .92)
        stereo_pan = np.sqrt([1 - pan, 1 + pan]).astype(np.float32)
        count = min(frames - start, len(audio))
        if count <= 0:
            continue
        clip = audio[:count] * (gain * velocity * stereo_pan)
        buses[bus][start:start + count] += clip
        buses['room'][start:start + count] += clip * room
        buses['echo'][start:start + count] += clip * echo
    # Keep the reverb out of the kick/sub range. The quieter waltz has a longer room.
    room = _plate(buses['room'], 1.42 if s.style == 'waltz' else .84, rng)
    echo = signal.sosfilt(signal.butter(2, [360, 4200], fs=RATE, btype='bandpass', output='sos'),
                          buses['echo'], axis=0).astype(np.float32)
    for fraction, level in [(0.75, .70), (1.50, .32), (2.25, .14)]:
        delay = round(RATE * beat_seconds * fraction)
        room[delay:] += echo[:-delay, ::-1] * level
    drums = buses['drums']
    drums = .86 * drums + .14 * np.tanh(1.8 * drums)
    synth = buses['chords'] * (.38 + .62 * duck[:, None]) + buses['bass'] * duck[:, None]
    mix = drums + synth + (buses['melody'] + room) * (.83 + .17 * duck[:, None])
    target_lufs = -15.0 if s.style == 'waltz' else -12.0
    mastered = _master(mix, target_lufs)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(RATE), '-ac', '2',
                    '-i', 'pipe:0', '-c:a', 'libmp3lame', '-b:a', '224k',
                    '-metadata', 'title=' + s.title, '-metadata', 'artist=Phaseline',
                    '-metadata', 'album=Classical Reworks', '-metadata', 'comment=Original game soundtrack. Contains licensed Apple Logic Pro sounds. See music/CREDITS.md.',
                    str(target)], input=mastered.astype('<f4', copy=False).tobytes(), check=True)
    print(f'{s.title}: {seconds_for(s):.2f}s, {_integrated_loudness(mastered):.1f} LUFS', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--charts-only', action='store_true')
    mode.add_argument('--track', help='render just the finished stereo mix for this track ID')
    parser.add_argument('--output', type=Path, default=OUT, help='output directory (default: music)')
    args = parser.parse_args()
    scores = album()
    if args.track and args.track not in [s.id for s in scores]:
        parser.error('unknown track')
    args.output.mkdir(parents=True, exist_ok=True)
    # Stage completed mixes so a missing local instrument cannot overwrite a good master.
    with tempfile.TemporaryDirectory(dir=args.output) as staging:
        stage = Path(staging)
        if not args.track:
            catalog = json.dumps([entry(s) for s in scores], ensure_ascii=False, indent=2)
            catalog = re.sub(r'\{\s+"t": ([\d.]+),\s+"l": (\d+),\s+"d": ([\d.]+)\s+\}',
                             r'{"t": \1, "l": \2, "d": \3}', catalog)
            (stage / 'library.json').write_text(catalog + '\n', encoding='utf-8')
        if not args.charts_only:
            for score in scores:
                if args.track is None or args.track == score.id:
                    render(score, stage / (score.id + '.mp3'))
        for path in stage.iterdir():
            path.replace(args.output / path.name)
