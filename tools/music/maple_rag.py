"""Maple After Hours. Two of Joplin's 2/4 measures fit one dance bar."""
from scores import Score, chord


# Top line from the 1899 John Stark edition, reduced to a single playable
# voice. Zero is a rest and -1 continues the preceding note by a sixteenth.
A = (
    (0, 68, 75, 68, 72, 75, -1, 67), (75, 67, 70, 75, -1, -1, -1, -1),
    (0, 68, 75, 68, 72, 75, -1, 67), (75, 67, 70, 75, -1, -1, 0, 75),
    (0, 68, 71, 76, 0, 75, 0, 75),   (0, 68, 71, 76, 0, 75, 0, 0),
    (0, 44, 47, 56, 0, 56, 59, 68),   (0, 68, 71, 80, 0, 68, 71, 80),
    (80, -1, 80, -1, 80, -1, 80, 80), (-1, 75, 77, 72, 75, 77, -1, 68),
    (-1, 70, 71, 68, 70, 72, -1, 68), (72, 68, 70, -1, 68, -1, 0, 80),
    (-1, -1, 80, -1, 80, -1, 80, 80), (-1, 75, 77, 72, 75, 77, -1, 68),
    (-1, 70, 71, 68, 70, 72, -1, 68), (72, 68, 70, -1, 68, -1, 0, 0),
)
B = (
    (0, 67, 75, 67, 70, 74, -1, 67),  (73, 67, 70, 72, -1, 63, 70, 63),
    (0, 60, 68, 60, 63, 65, -1, 60),  (68, 60, 63, 65, -1, 60, 65, -1),
    (0, 63, 67, 58, 61, 65, -1, 63),  (67, 58, 61, 65, -1, 61, 65, -1),
    (0, 60, 68, 60, 63, 65, -1, 60),  (68, 60, 63, 65, -1, 60, 65, -1),
    (0, 67, 75, 67, 70, 74, -1, 67),  (73, 67, 70, 72, -1, 63, 70, 63),
    (0, 60, 68, 60, 63, 65, -1, 60),  (68, -1, 68, -1, 67, -1, 66, -1),
    (0, 53, 57, 60, 65, 60, 57, 53),  (0, 53, 58, 61, 65, -1, 61, -1),
    (72, -1, 0, 72, 0, 70, -1, 63),   (0, 68, 72, 75, 80, -1, 0, 0),
)
TRIO = (
    (80, -1, -1, 80, -1, 75, 70, -1), (80, -1, -1, 80, -1, 75, 70, 75),
    (68, 73, 70, 73, 77, 68, 73, 77), (70, 73, 77, 68, -1, 77, 70, 77),
    (80, -1, -1, 80, -1, 75, 70, -1), (80, -1, -1, 80, -1, 75, 70, 75),
    (68, 73, 70, 73, 77, 68, 73, 77), (70, 73, 77, 68, -1, 77, 69, 77),
    (82, -1, -1, 82, -1, 77, 72, -1), (82, -1, -1, 82, -1, 77, 72, 77),
    (0, 63, 70, 63, 66, 72, -1, 63),  (70, 63, 66, 72, -1, 63, 70, -1),
    (73, -1, 73, -1, 72, -1, 70, -1), (65, 61, 63, 66, -1, 58, 65, -1),
    (65, 61, 63, 65, -1, 60, 63, 61), (-1, 61, 65, 68, 73, -1, 0, 0),
)

# Bass root and upper voicing for the piano's left hand / electric piano.
HARMONY = {
    'Ab': (32, (55, 60, 63)), 'Eb7': (39, (55, 58, 61)),
    'Fb': (40, (56, 59, 64)), 'Abm': (32, (51, 56, 59)),
    'Do': (38, (53, 56, 59)), 'Ab7': (32, (54, 60, 63)),
    'Db': (37, (53, 56, 61)), 'Bb7': (34, (53, 56, 62)),
    'Ebm': (39, (54, 58, 63)), 'F7': (41, (51, 57, 60)),
    'Bbm': (34, (53, 58, 61)), 'Gb': (30, (54, 58, 61)),
}
A_BASS = ('Ab', 'Eb7', 'Ab', 'Eb7', 'Fb', 'Fb', 'Abm', 'Abm',
          'Do', 'Ab', 'Fb', 'Ab', 'Do', 'Ab', 'Fb', 'Ab')
B_BASS = ('Eb7', 'Eb7', 'Ab', 'Ab', 'Eb7', 'Eb7', 'Ab', 'Ab',
          'Eb7', 'Eb7', 'Ab', 'Ab', 'F7', 'Bbm', 'Eb7', 'Ab')
TRIO_BASS = ('Ab7', 'Ab7', 'Db', 'Db', 'Ab7', 'Ab7', 'Db', 'Db',
             'Bb7', 'Bb7', 'Ebm', 'Ebm', 'Gb', 'Db', 'Ab7', 'Db')


def lead(s, start, measures, section):
    line = sum(measures, ())
    for step, pitch in enumerate(line):
        if pitch <= 0:
            continue
        bar, pos = divmod(step, 16)
        length = 1
        while step + length < len(line) and line[step + length] == -1:
            length += 1
        # The climb into the repeated high A-flats is deliberately exposed.
        voice = 'felt'
        if (section == 'B' and bar in (0, 2, 4, 6)) or (section == 'trio' and bar < 6):
            voice = 'reed'
        strength = (.84, .67, .75, .79)[step % 4]
        if section == 'trio' and voice == 'reed':
            strength *= .80
        if section == 'break':
            if bar < 2:
                pitch -= 12
            strength *= .74 + bar * .04
        # Light agogic swing on the sixteenths leaves Joplin's tied accents intact.
        beat = start + step * .25 + (.019 if step % 2 else 0)
        s.note(beat, voice, pitch, length * .25 - .046, strength, -.12 if voice == 'felt' else .16)
        if section == 'return' and pitch >= 68 and (pos in (2, 5, 8, 11) or length >= 3):
            s.sound(beat, 'reed', pitch - 12, length * .25 - .05, strength * .41, .23)


def rhythm_section(s, bar, harmonies, section):
    beat = bar * 4
    s.downbeats.append(beat)
    sparse = section in ('intro', 'break')
    finale = section == 'return'
    for half, harmony in enumerate(harmonies):
        root, voicing = HARMONY[harmony]
        pos = beat + 2 * half
        s.sound(pos, 'bass', root, .86 if sparse else .66, .80)
        if not sparse:
            # A fifth or octave answers the bass. Chord pushes enter between them.
            accent = root + (12 if (bar + half) % 4 == 2 else 7)
            s.sound(pos + 1, 'bass', accent, .40, .62)
            for off in (.54, 1.53):
                chord(s, pos + off, voicing, .19 if finale else .13,
                      .27 if finale else .22, 'organ')
        elif half == 1:
            chord(s, pos + .54, voicing[1:], .57, .25, 'organ')

    s.sound(beat, 'kick', 0, .24, .70 if sparse else .91)
    if sparse:
        s.sound(beat + 2, 'rim', 0, .17, .41, -.19)
        for off in (1.55, 3.55):
            s.sound(beat + off, 'hat', 0, .10, .26, .31)
        return
    s.sound(beat + 2, 'kick', 0, .23, .79)
    for backbeat in (1, 3):
        if finale:
            s.sound(beat + backbeat, 'kick', 0, .19, .57)
        s.sound(beat + backbeat, 'snare', 0, .18, .66 if backbeat == 1 else .76)
    for half in range(8):
        off = half * .5 + (.045 if half % 2 else 0)
        kind = 'hat_open' if half == 7 and bar % 2 == 1 else 'hat'
        s.sound(beat + off, kind, 0, .11, (.35, .29, .19, .46)[half % 4], .26)
    if bar % 4 == 1:
        for off, velocity in ((3.26, .28), (3.76, .41)):
            s.sound(beat + off, 'snare', 0, .1, velocity, -.15)
    elif bar % 4 == 3:
        s.sound(beat + 3.55, 'kick', 0, .16, .48)


def make_score():
    s = Score('maple-after-hours', 'Maple After Hours', 'Scott Joplin',
              'Maple Leaf Rag', 1899, 'https://levysheetmusic.mse.jhu.edu/collection/171/088',
              'Electro swing', 114, 4, 40, '#ffb457', 'rag', 8, 10)
    # A two-bar piano/bass exchange introduces the pickup into the first strain.
    for bar, harmony in enumerate(('Ab', 'Eb7')):
        rhythm_section(s, bar, (harmony, harmony), 'intro')
    s.phrase(0, ((0, 56, .8), (1.53, 60, .34), (2, 63, 1.42)), 'felt', .67)
    s.phrase(4, ((0, 67, 1.48), (2, 61, .42), (3, 58, .44), (3.55, 63, .33)), 'reed', .54)

    bar = 2
    for melody, harmonies, section in (
        (A, A_BASS, 'head'), (B, B_BASS, 'B'), (TRIO[:8], TRIO_BASS[:8], 'break'),
        (TRIO, TRIO_BASS, 'trio'), (A, A_BASS, 'return'),
    ):
        lead(s, bar * 4, melody, section)
        for half in range(0, len(harmonies), 2):
            rhythm_section(s, bar, harmonies[half:half + 2], section)
            bar += 1
        if section in ('break', 'trio'):
            s.sound(bar * 4 - 1.5, 'rise', 0, 1.5, .25)
            s.sound(bar * 4, 'crash', 0, 1.3, .36, -.26)

    # Two-bar stop-time tag. Isolated piano hits answer the bass before
    # the whole band sustains the final A-flat sixth.
    for off, name, pitch, length in ((0, 'Ab', 80, .7), (1.55, 'Ab', 75, .30),
                                     (2.5, 'Fb', 76, .83), (4, 'Eb7', 75, 1.45),
                                     (6, 'Eb7', 70, .31), (6.55, 'Eb7', 67, .32)):
        pos = bar * 4 + off
        root, voicing = HARMONY[name]
        s.note(pos, 'felt', pitch, length, .86, -.12)
        s.sound(pos, 'bass', root, length, .74)
        s.sound(pos, 'rim', 0, .14, .47)
        chord(s, pos, voicing, min(length, .34), .28, 'organ')
    beat = s.bars * 4
    s.note(beat, 'felt', 80, 2.7, .88, -.10)
    chord(s, beat, (56, 60, 63, 65), 2.48, .37, 'organ')
    s.sound(beat, 'reed', 72, 2.2, .50, .21)
    s.sound(beat, 'bass', 32, 2.0, .90)
    s.sound(beat, 'kick', 0, .40, .87)
    s.sound(beat, 'crash', 0, 2.1, .41, -.30)
    return s
