"""Cinder Step, from the Habanera in Act I of Bizet's Carmen."""
from scores import Score, chord


# Two measures of Bizet's 2/4 fit inside one four-beat game bar. Keep the
# syllabic triplets, chromatic inflections and little turns of the vocal line.
DESCENT = (
    (0, 72, .26), (1 / 3, 72, .25), (2 / 3, 72, .28),
    (1, 71, .42), (1.5, 70, .44), (2, 69, .70), (2.75, 69, .19),
    (3, 68, .42), (3.5, 67, .44),
)
ANSWER = (
    (0, 65, .14), (1 / 6, 67, .13), (1 / 3, 65, .14),
    (.5, 64, .19), (.75, 65, .19), (1, 67, .43), (1.5, 65, .42),
    (2, 64, .60),
)
SECOND_LINE = DESCENT[:5] + (
    (2, 69, .61), (2.75, 69, .19), (3, 67, .42), (3.5, 65, .43),
)
CADENCE = (
    (0, 64, .14), (1 / 6, 65, .13), (1 / 3, 64, .14),
    (.5, 62, .19), (.75, 64, .19), (1, 65, .42), (1.5, 64, .42),
    (2, 62, .85),
)
PICKUP = ((3, 74, .42), (3.5, 73, .44))

# The change to the parallel major begins with four pairs of calls. On the
# last call the clarinet turns directly into the pickup of the refrain.
CALLS = (
    ((1, 66, .91), (2, 69, 1.44)),
    ((1, 74, .90), (2, 71, 1.42)),
    ((1, 64, .88), (2, 76, 1.45)),
    ((1, 69, .89), (2, 74, .45), (2.75, 69, .19), (3, 62, .44), (3.5, 64, .43)),
)
REFRAIN = (
    ((0, 66, .66), (.75, 69, .21), (1, 66, .44), (1.5, 64, .44),
     (2, 62, .68), (2.75, 64, .20), (3, 66, .40), (3.5, 67, .42)),
    ((0, 69, .20), (.25, 69, .19), (.5, 69, .21), (.75, 69, .21),
     (1, 71, .43), (1.5, 69, .44), (2, 67, .65),
     (2.75, 71, .19), (3, 64, .44), (3.5, 66, .43)),
    ((0, 67, .67), (.75, 71, .20), (1, 67, .43), (1.5, 66, .41),
     (2, 64, .67), (2.75, 66, .20), (3, 67, .40), (3.5, 69, .43)),
    ((0, 71, .21), (.25, 71, .19), (.5, 71, .21), (.75, 71, .21),
     (1, 73, .43), (1.5, 71, .43), (2, 69, 1.43)),
)
HARMONY = {
    # root in bass register, third above the octave, close keyboard voicing
    'dm': (38, 15, (53, 57, 64)), 'd': (38, 16, (54, 57, 64)),
    'gm': (43, 15, (53, 58, 62)), 'em': (40, 15, (55, 59, 62)),
    'a7': (33, 16, (55, 61, 64)), 'bb': (34, 16, (53, 57, 62)),
}


def _line(s, start, notes, kind='reed', strength=.82):
    for offset, pitch, length in notes:
        # Breath onsets, long accented syllables and lighter ornaments.
        accent = .72 if length < .24 else 1.0 if length >= .58 else .91
        s.note(start + offset, kind, pitch, length, strength * accent, -.07)


def _groove(s, bar, harmony, section):
    start = bar * 4
    root, third, keys = HARMONY[harmony]
    bare = section in ('intro', 'break')
    open_kit = section in ('refrain', 'final')
    s.downbeats.append(start)
    # Dotted eighth, sixteenth, two eighths. Let the recorded mute supply the
    # front of the bass notes and leave air between them for the kick drum.
    for half in (0, 2):
        for off, interval, length, weight in (
            (0, 0, .44, .77), (.75, 7, .19, .44),
            (1, third, .38, .56), (1.5, 7, .28, .46),
        ):
            if section == 'break' and half == 2 and off > 0:
                continue
            s.sound(start + half + off, 'bass', root + interval, length, weight)
    s.sound(start, 'kick', 0, .32, .49 if bare else .91)
    if bare:
        s.sound(start + 2, 'rim', 0, .15, .31, -.19)
        s.sound(start + 3.5, 'hat', 0, .10, .26, .35)
        if section == 'break':
            chord(s, start + .75, keys[1:], 1.76, .19, 'felt')
        return

    # A single heavy backbeat across two habanera cells, with short ghost
    # replies on the opposite side of the stereo field.
    backbeat = 'rim' if section == 'call' else 'snare'
    s.sound(start + 2, backbeat, 0, .22, .78, -.08)
    s.sound(start + (3.25 if bar % 2 else 1.75), 'kick', 0, .23, .64)
    if bar % 2:
        s.sound(start + 3.75, 'rim', 0, .12, .30, .25)
    for i, strength in enumerate((.45, .25, .36, .55, .36, .30, .42, .53)):
        s.sound(start + i / 2, 'hat_open' if open_kit and i == 7 else 'hat',
                0, .13, strength * (.88 if open_kit else .69), .24)
    if open_kit:
        s.sound(start + 1.75, 'hat', 0, .08, .31, -.34)
        s.sound(start + 2.75, 'kick', 0, .25, .58)
        s.sound(start, 'sub', root, .70, .31)
    for off, length, weight in ((.75, .20, .31), (1.5, .28, .22), (3, .40, .24)):
        chord(s, start + off, keys, length, weight, 'felt')
    if open_kit:
        chord(s, start + .04, keys[1:], 2.65, .21)


def make_score():
    source = 'https://s9.imslp.org/files/imglnks/usimg/8/8f/IMSLP851704-PMLP15769-Bizet%2C_Carmen%2C_Habanera.pdf'
    s = Score('cinder-step', 'Cinder Step', 'Georges Bizet', 'Habanera from Carmen',
              1875, source, 'Electro-tango', 96, 4, 34, '#ed785c', 'habanera', 2, 6)
    for bar in range(2):
        _groove(s, bar, 'dm', 'intro')
    _line(s, 4, PICKUP)

    for bar in range(2, 10):
        phrase = (bar - 2) % 4
        start = bar * 4
        _groove(s, bar, ('dm', 'a7', 'dm', 'dm')[phrase], 'verse')
        _line(s, start, (DESCENT, ANSWER, SECOND_LINE, CADENCE)[phrase])
        if phrase in (1, 3) and bar != 9:
            _line(s, start, PICKUP)
        if bar >= 6 and phrase % 2 == 0:
            s.sound(start, 'pad', 57, 1.85, .24, .30)
            s.sound(start + 2, 'pad', 53, 1.65, .24, .30)

    for i, call in enumerate(CALLS):
        bar = 10 + i
        _groove(s, bar, ('d', 'em', 'a7', 'd')[i], 'call')
        _line(s, bar * 4, call, strength=.88)
        # The electric keys answer in the pocket between the vocal phrases.
        s.sound(bar * 4 + .50, 'felt', (69, 71, 73, 74)[i], .36, .36, .30)

    for i in range(8):
        bar = 14 + i
        harmony = ('d', 'em', 'a7', 'd')[i % 4]
        _groove(s, bar, harmony, 'refrain')
        lead = 'reed' if i < 4 else 'pad'
        _line(s, bar * 4, REFRAIN[i % 4], lead, .85 if i < 4 else .93)
        if i >= 4:
            # String ensemble in unison across the melody; single clarinet
            # accents pick out the dance rhythm as the bow changes direction.
            for offset, pitch, length in REFRAIN[i % 4]:
                if offset in (0, 1, 2):
                    s.sound(bar * 4 + offset, 'reed', pitch + 12, min(.27, length), .35, .14)
    s.sound(14 * 4, 'crash', 0, 1.5, .42, .22)

    # Four bars of exposed electric piano recast fragments of the chromatic
    # melody in the lower octave. A roll leads back into the full beat.
    for i, notes in enumerate((
        ((0, 62, 1.48), (2, 61, 1.32)),
        ((0, 60, 1.48), (2, 59, .65), (3, 58, .66)),
        ((0, 57, 1.55), (2.75, 56, .21), (3, 55, .65)),
        ((0, 53, .65), (1, 52, 1.42), *PICKUP),
    )):
        bar = 22 + i
        _groove(s, bar, ('dm', 'bb', 'gm', 'a7')[i], 'break')
        _line(s, bar * 4, notes, 'felt', .74)
    for i, weight in enumerate((.19, .25, .34, .47)):
        s.sound(25 * 4 + 2 + i / 4, 'rim', 0, .10, weight, .16)

    for i, notes in enumerate((DESCENT, ANSWER + PICKUP, SECOND_LINE, CADENCE)):
        bar = 26 + i
        _groove(s, bar, ('dm', 'a7', 'gm', 'dm')[i], 'final')
        _line(s, bar * 4, notes, strength=.91)
    # Short tutti coda. The last bar drops the snare completely and leaves
    # space for the final all-hand D-minor cadence.
    for i, notes in enumerate((
        ((0, 74, .63), (.75, 73, .20), (1, 72, .43), (1.5, 69, .42), (2, 70, 1.38)),
        ((0, 67, .66), (.75, 70, .19), (1, 69, .43), (1.5, 67, .40), (2, 65, 1.38)),
        ((0, 64, .63), (.75, 67, .20), (1, 69, .45), (1.5, 70, .42), (2, 73, 1.38)),
        ((0, 76, .42), (.75, 73, .20), (1, 69, 1.44)),
    )):
        bar = 30 + i
        _groove(s, bar, ('bb', 'gm', 'a7', 'a7')[i], 'break' if i == 3 else 'final')
        _line(s, bar * 4, notes, strength=.85)
    last = s.bars * 4
    s.sound(last, 'kick', 0, .45, .83)
    s.sound(last, 'bass', 38, 1.65, .75)
    chord(s, last, (50, 57, 65, 69), 2.21, .34, 'felt')
    s.note(last, 'reed', 74, 1.86, .86, -.06)
    s.sound(last + .04, 'pad', 62, 2.51, .27, .30)
    return s
