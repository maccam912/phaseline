"""First Light, a trance arrangement of the Allegro from Vivaldi's Spring."""
from scores import Score, chord, transition


# Eighth-note pickup, forte calls and the answering cadence from the 1725
# Violino principale part. Shorter gates leave room for each new bow stroke.
OPENING = ((0, 80, .37), (.5, 80, .34), (1, 80, .39), (1.5, 78, .21),
           (1.75, 76, .20), (2, 83, 1.36), (3.5, 83, .21), (3.75, 81, .21))
OPENING_CADENCE = ((0, 80, .43), (.5, 81, .21), (.75, 83, .21), (1, 81, .42),
                   (1.5, 80, .41), (2, 78, .41), (2.5, 75, .41), (3, 71, .44))
ANSWER = ((0, 83, .42), (.5, 81, .22), (.75, 80, .21), (1, 81, .41),
          (1.5, 83, .42), (2, 85, .39), (2.5, 83, .82), (3.5, 76, .39))
ANSWER_CADENCE = ((0, 85, .42), (.5, 83, .86), (1.5, 81, .41), (2, 80, .40),
                  (2.5, 78, .21), (2.75, 76, .21), (3, 78, .91))
REFRAIN = (OPENING, OPENING, OPENING_CADENCE, ((0, 76, 2.46), (3.5, 76, .38)),
           ANSWER, ANSWER, ANSWER_CADENCE, ((0, 76, 2.65),))

# The middle sections share a harmonic route. The bird calls break it into
# short exchanges while the brook moves in sixteenth notes beneath longer bows.
BIRDS = (
    ((0, 83, .31), (.5, 83, .35), (1, 85, .19), (1.25, 83, .19), (1.5, 85, .19),
     (1.75, 83, .20), (2, 80, 1.49)),
    ((.5, 81, .31), (1, 83, .31), (1.5, 85, .23), (2, 88, 1.42)),
    ((0, 87, .29), (.5, 87, .28), (1, 85, .24), (1.25, 87, .19),
     (1.5, 85, .18), (1.75, 83, .22), (2, 80, 1.32)),
    ((0, 78, .43), (.5, 80, .44), (1, 83, 1.48), (3.25, 81, .23), (3.5, 78, .40)),
)
BROOK = (
    ((0, 80, 1.72), (2, 76, .78), (3, 78, .71)),
    ((0, 81, 2.40), (2.75, 80, .48), (3.5, 76, .37)),
    ((0, 80, 1.40), (1.5, 78, .38), (2, 76, 1.62)),
    ((0, 75, 1.40), (1.5, 76, .40), (2, 78, 1.62)),
)

HARMONY = {
    'E': (40, (64, 68, 71)), 'A': (45, (64, 69, 73)),
    'B': (35, (63, 66, 71)), 'C#m': (37, (64, 68, 73)),
    'F#m': (42, (61, 66, 69)),
}
REFRAIN_CHORDS = ('E', 'E', 'B', 'E', 'E', 'A', 'B', 'E')
EPISODE_CHORDS = ('E', 'A', 'C#m', 'B', 'C#m', 'A', 'F#m', 'B')


def rhythm(s, bar, section):
    beat = bar * 4
    if section == 'intro':
        kicks, snares, hats = ((0, 2) if bar >= 2 else (0,)), (), (1.5, 3.5)
    elif section == 'birds':
        kicks, snares, hats = (0, 2.75), (2,), (.5, 1.5, 3.5)
    elif section == 'brook':
        kicks = (0, 1.75, 3) if bar % 2 else (0, 2.5)
        snares, hats = (1, 3), (.5, 1.5, 2.5, 3.5)
    else:
        kicks, snares, hats = (0, 1, 2, 3), (1, 3), (.5, 1.5, 2.5, 3.5)
    s.downbeats.append(beat)
    for offset in kicks:
        s.sound(beat + offset, 'kick', 0, .3, .75 if section in ('intro', 'birds') else .95)
    for offset in snares:
        s.sound(beat + offset, 'rim' if section == 'birds' else 'snare', 0, .22,
                .72 if offset == 1 else .83)
    for i, offset in enumerate(hats):
        open_hat = section == 'refrain' and i in (1, 3)
        s.sound(beat + offset, 'hat_open' if open_hat else 'hat', 0, .14,
                (.34, .44, .30, .54)[i], .24 if i % 2 else -.12)
    if section in ('refrain', 'brook') and bar % 2:
        s.sound(beat + 3.75, 'hat', 0, .10, .32, -.35)
    if bar in (3, 11, 27, 31):
        for offset, velocity in ((2.75, .26), (3.0, .43), (3.25, .52), (3.5, .70)):
            s.sound(beat + offset, 'snare', 0, .14, velocity, -.18 + .24 * (offset - 2.75))


def make_score():
    s = Score('first-light', 'First Light', 'Antonio Vivaldi',
              'Spring, I. Allegro, RV 269', 1725,
              'https://www.loc.gov/static/programs/national-recording-preservation-board/documents/The-Four-Seasons_Furuya.pdf#page=7',
              'Orchestral trance', 138, 4, 40, '#c3ea7c', 'spring', 4, 4)
    for bar in range(s.bars):
        beat = bar * 4
        if bar < 4:
            rhythm(s, bar, 'intro')
            root, voices = HARMONY[('E', 'A', 'F#m', 'B')[bar]]
            chord(s, beat, voices, 3.48, .18)
            s.sound(beat, 'sub', root, 1.38, .48)
            for offset, pitch in zip((0, .75, 2, 2.75), (voices[0], voices[2], voices[1], voices[2])):
                s.note(beat + offset, 'mallet', pitch, .38, .44, .22)
            if bar == 3:
                s.note(beat + 3.5, 'bow', 76, .42, .75, -.12)
            continue

        refrain = 4 <= bar < 12 or bar >= 32
        index = (bar - 4) % 8 if bar < 32 else bar - 32
        name = REFRAIN_CHORDS[index] if refrain else EPISODE_CHORDS[(bar - 12) % 8]
        root, voices = HARMONY[name]
        if refrain:
            rhythm(s, bar, 'refrain')
            for offset, pitch, length in REFRAIN[index]:
                accent = .96 if offset in (0, 2) else .77
                s.note(beat + offset, 'bow', pitch, length, accent, -.09)
                if bar >= 32 and (index >= 4 or length > 1):
                    s.sound(beat + offset, 'bird', pitch - 12, length * .90, .37, .23)
            # An answering inner voice comes through the gaps in each cadence.
            if index in (3, 7):
                for offset, pitch in zip((1.5, 2, 2.5, 3), (71, 73, 76, 80)):
                    s.sound(beat + offset, 'mallet', pitch, .39, .42, .28)
            for i, offset in enumerate((.5, 1.5, 2.5, 3.5)):
                s.sound(beat + offset, 'bass', root + (12 if i == 3 else 0), .34, .67)
            chord(s, beat, voices, 3.70, .18)
        elif bar < 20:
            rhythm(s, bar, 'birds')
            for offset, pitch, length in BIRDS[(bar - 12) % 4]:
                # A second player answers from the other side of the stage.
                lane_pan = -.34 if bar % 2 == 0 else .32
                s.note(beat + offset, 'bird', pitch, length, .78, lane_pan)
            chord(s, beat, voices[1:], 2.80, .27, 'bow')
            s.sound(beat, 'sub', root, 1.74, .57)
            for i, offset in enumerate((.75, 2.5, 3.25)):
                s.sound(beat + offset, 'mallet', voices[i], .46, .46, .27)
        elif bar < 28:
            rhythm(s, bar, 'brook')
            s.phrase(beat, BROOK[(bar - 20) % 4], 'bow', .78, pan=-.08)
            # The plucked ostinato passes through two inversions of each chord.
            moving = (voices[0], voices[1], voices[0], voices[2],
                      voices[1], voices[2], voices[1], voices[0] + 12)
            for i, pitch in enumerate(moving):
                s.sound(beat + i / 2, 'mallet', pitch, .28, .40 if i % 2 else .52, .26)
                if i in (2, 6):
                    s.sound(beat + i / 2 + .25, 'mallet', voices[1], .17, .30, -.31)
            s.sound(beat, 'bass', root, .72, .65)
            s.sound(beat + 2.5, 'bass', root + 7, .58, .53)
        else:
            rhythm(s, bar, 'build')
            root, voices = HARMONY[('C#m', 'A', 'F#m', 'B')[bar - 28]]
            s.sound(beat, 'sub', root, 2.9, .65)
            for i, pitch in enumerate((voices[0], voices[1], voices[2], voices[0] + 12)):
                s.note(beat + i, 'bow', pitch, .72, .61 + .06 * i, -.09)
                s.sound(beat + i + .5, 'mallet', pitch + 12, .21, .38, .26)
            if bar == 31:
                s.note(beat + 3.5, 'bow', 76, .42, .87, -.09)

    for bar in (4, 20, 32):
        transition(s, bar)
    end = s.bars * 4
    s.sound(end, 'kick', 0, .38, .97)
    s.sound(end, 'crash', 0, 2, .45, .24)
    s.sound(end, 'sub', 40, 2.12, .75)
    chord(s, end, (59, 64, 68), 2.68, .38, 'bow')
    s.note(end, 'bow', 76, 2.55, .88, -.09)
    s.sound(end, 'mallet', 83, 1.82, .44, .22)
    return s
