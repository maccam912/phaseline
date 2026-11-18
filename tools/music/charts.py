"""Chart the recorded arrangement for ten home-row keys and eight fingers."""
from collections import defaultdict

# F/G share a left index finger, H/J share a right index finger.
FINGERS = (0, 1, 2, 3, 3, 4, 4, 5, 6, 7)
CAPACITY = {'easy': 1, 'normal': 2, 'hard': 2, 'expert': 8}
MIN_ONSET_GAP = {'easy': .32, 'normal': .167, 'hard': .104, 'expert': .084}
PULSE = {'kick', 'snare', 'rim'}
BASS = {'bass', 'sub', 'wobble'}


def _play_on(level, style, beat, offset, bar, kinds, melody):
    pulse = bool(kinds & PULSE)
    if level == 'easy':
        if style == 'waltz':
            return offset == 0 or (offset == 2 and bar % 2 == 1 and melody)
        return offset in (0, 2) and (pulse or melody or kinds & BASS)
    if level == 'normal':
        if offset % 1 == 0:
            return pulse or melody or kinds & (BASS | {'felt'})
        if style in ('garage', 'breaks') and 'kick' in kinds:
            return True
        return melody and offset % 1 == .5 and bar % 4 in (1, 3)
    if level == 'hard':
        return pulse or melody or (bar % 2 and kinds & {'hat_open', 'organ'})
    return pulse or melody or kinds & BASS or (kinds & {'hat', 'hat_open', 'organ'} and beat % .5 < .1)


def _chord_size(level, bar, offset, ending, kinds, pitch_count):
    if level == 'easy':
        return 1
    if ending:
        return CAPACITY[level]
    if level == 'normal':
        return 2 if offset == 0 and bar % 4 == 0 else 1
    if level == 'hard':
        return 2 if (offset == 0 and bar % 2 == 0) or ('snare' in kinds and bar % 4 >= 2) else 1
    if offset == 0:
        if bar % 8 == 0:
            return min(6, max(4, pitch_count + 1))
        return 3 if bar % 2 == 0 else 2
    if 'snare' in kinds or ('organ' in kinds and bar % 2 == 1):
        return 2
    return 1


def _lead_lane(level, bar, offset, pitch, scale, kinds):
    # Easy trades a steady bass pulse across the two hands. Fingering repeats
    # over a phrase before moving to the adjacent pair of keys.
    if level == 'easy':
        anchors = (2, 2, 3, 3, 1, 1, 4, 4, 0, 0)
        anchor = anchors[(bar if offset == 0 else bar + 2) % len(anchors)]
        return anchor if (offset == 0) == (bar % 8 < 4) else 9 - anchor
    if pitch is not None:
        if len(scale) > 1:
            position = 9 * scale.index(pitch) / (len(scale) - 1)
            # Resolve in-between notes toward opposite hands in answering phrases.
            return int(position + (.501 if bar // 4 % 2 else .499))
        return 3 if bar % 2 == 0 else 6
    if 'kick' in kinds or kinds & BASS:
        return (0, 2, 3, 1, 4, 2, 3, 0)[bar % 8]
    return (7, 9, 6, 8, 5, 7, 8, 9)[bar % 8]


def _build_one(score, level, events, melody, phrase_pitches, origin):
    beat_seconds = 60 / score.bpm
    last_beat = score.bars * score.beats_per_bar
    last_finger = [-100.0] * 8
    release_time = [-100.0] * 8
    last_lane = [-100.0] * 10
    last_onset = -100.0
    chart = []
    for beat in sorted(events):
        if beat < score.beats_per_bar or beat > last_beat:
            continue
        ending = beat == last_beat
        # Give the final Expert cadence a short pickup rest for the full-hand chord.
        if level == 'expert' and 0 < last_beat - beat < .70:
            continue
        bar, offset = divmod(beat, score.beats_per_bar)
        bar = int(bar)
        played = events[beat]
        kinds = {e[1] for e in played}
        pitch, length = melody.get(beat, (None, 0))
        if not ending and not _play_on(level, score.style, beat, offset, bar, kinds, pitch is not None):
            continue
        now = origin + beat * beat_seconds
        if now - last_onset < MIN_ONSET_GAP[level] and not ending:
            continue
        held = sum(end > now - .001 for end in release_time)
        capacity = CAPACITY[level] - held
        if capacity <= 0:
            continue
        pitches = {e[2] for e in played if e[2] > 0}
        wanted = min(capacity, _chord_size(level, bar, offset, ending, kinds, len(pitches)))
        target = _lead_lane(level, bar, offset, pitch, phrase_pitches[bar // 2], kinds)
        available = [lane for lane, finger in enumerate(FINGERS)
                     if now - release_time[finger] >= .050 and now - last_finger[finger] >= .155]
        picked = []
        for _ in range(wanted):
            if not available:
                break
            # Spread a chord across hands, then distribute its inner voices.
            if len(picked) == 1 and offset == 0:
                # Let the accompanying hand change chord voicings between phrases.
                other_hand = [x for x in available if (x < 5) != (picked[0] < 5)]
                if other_hand:
                    target = min(other_hand, key=lambda x: (last_lane[x], abs(x - (9 - picked[0]))))
            elif picked:
                target = max(available, key=lambda lane: min(abs(lane - used) for used in picked))
            lane = min(available, key=lambda x: (abs(x - target), last_lane[x]))
            picked.append(lane)
            finger = FINGERS[lane]
            available = [x for x in available if FINGERS[x] != finger]
        if not picked:
            continue
        last_onset = now
        hold_beats = 0
        if ending:
            hold_beats = 1.65
        elif pitch is not None and length >= 1.30:
            hold_beats = min(2.15, length - .16)
        elif offset == 0 and bar % 8 == 0 and score.style in ('wave', 'breaks', 'house'):
            hold_beats = 1.25
        if not ending:
            hold_beats = min(hold_beats, max(0, last_beat - beat - .72))
        for i, lane in enumerate(picked):
            duration = round(hold_beats * beat_seconds, 4) if i == 0 or ending else 0
            chart.append({'t': round(now, 4), 'l': lane, 'd': duration})
            last_lane[lane] = now
            last_finger[FINGERS[lane]] = now
            release_time[FINGERS[lane]] = now + max(.040, duration)
    return chart


def build_charts(score, origin):
    events = defaultdict(list)
    for event in score.events:
        events[round(event[0], 5)].append(event)
    # The lead may be doubled in an octave. Keep the longest voice on each attack.
    melody = {}
    for beat, pitch, length in score.melody:
        beat = round(beat, 5)
        if beat not in melody or length > melody[beat][1]:
            melody[beat] = (pitch, length)
    # Two-bar pitch ranks let ascending and descending hooks trace a repeatable
    # shape along the keys, even when the section transposes into a new register.
    phrase_pitches = defaultdict(set)
    for beat, (pitch, _) in melody.items():
        phrase_pitches[int(beat // score.beats_per_bar) // 2].add(pitch)
    scales = defaultdict(list, {i: sorted(v) for i, v in phrase_pitches.items()})
    return {level: _build_one(score, level, events, melody, scales, origin) for level in CAPACITY}
