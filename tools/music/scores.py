"""Phaseline arrangements. All times are measured in quarter-note beats."""
from dataclasses import dataclass, field


@dataclass
class Score:
    id: str
    title: str
    composer: str
    work: str
    year: int
    source: str
    genre: str
    bpm: int
    beats_per_bar: int
    bars: int
    color: str
    style: str
    tonic: int
    preview_bar: int
    events: list = field(default_factory=list)
    melody: list = field(default_factory=list)
    downbeats: list = field(default_factory=list)

    def sound(self, beat, instrument, pitch, length, volume, pan=0):
        self.events.append((beat, instrument, pitch, length, volume, pan))

    def note(self, beat, instrument, pitch, length, volume, pan=0):
        self.sound(beat, instrument, pitch, length, volume, pan)
        self.melody.append((beat, pitch, length))

    def phrase(self, start, motif, instrument, volume, transpose=0, pan=0, foreground=True):
        # Octave doubles and counterlines belong in the performance. A chart can
        # follow the principal voice independently through a change in orchestration.
        emit = self.note if foreground else self.sound
        for offset, pitch, length in motif:
            emit(start + offset, instrument, pitch + transpose, length, volume, pan)


def chord(score, beat, pitches, length, volume, voice='pad'):
    for i, pitch in enumerate(pitches):
        score.sound(beat, voice, pitch, length, volume, (-.47, .22, -.21, .47, .09)[i % 5])


def bass(score, beat, root, pattern, voice='bass', volume=.69):
    for off, transpose, length in pattern:
        score.sound(beat + off, voice, root + transpose, length, volume)


def fill(score, beat, beats_per_bar, volume):
    # Four ending shapes: drag, flam, skipping fill, and crescendo into a stop.
    shape = ((.24, .50, .35, .84), (.58, .20, .66, .89),
             (.24, .78, .41, .86), (.24, .39, .62, .97))[int(beat / beats_per_bar) // 8 % 4]
    for index, accent in enumerate(shape):
        pos = beat + beats_per_bar - 1 + index / 4
        score.sound(pos, 'snare', 0, .15, volume * accent, (index - 1.5) * .16)


def drums(s, bar, section='groove'):
    start, bp = bar * s.beats_per_bar, s.beats_per_bar
    if section == 'air':
        if bar % 2 == 0:
            s.sound(start, 'kick', 0, .30, .51 if bar < 4 else .67)
            s.downbeats.append(start)
        offsets = (1, 2) if bp == 3 else (1, 3)
        for index, off in enumerate(offsets):
            s.sound(start + off, 'rim', 0, .16, (.36, .22)[index], (-.18, .14)[index])
        return
    if s.style == 'garage':
        kicks = [0, 1.75, 2.5] if bar % 2 == 0 else [0, 1.5, 2.75]
        snares = [1, 3]
        hats = [0, .56, 1, 1.56, 2, 2.56, 3, 3.56]
        hat_accents = [.32, .64, .18, .81, .34, .51, .25, .72]
    elif s.style == 'breaks':
        kicks = [0, 2.5] if bar % 2 == 0 else [0, 1.75, 2.5]
        snares = [1, 3]
        hats = [i / 2 for i in range(8)]
        hat_accents = [.68, .24, .38, .60, .53, .23, .44, .77]
    elif s.style == 'waltz':
        kicks = [0, 2.52] if bar % 2 else [0]
        snares = [1]
        hats = [0, .53, 1, 1.53, 2, 2.53]
        hat_accents = [.34, .12, .26, .38, .24, .45]
    else:
        kicks, snares = [0, 1, 2, 3], [1, 3]
        hats = [i / 2 for i in range(8)]
        hat_accents = [.24, .55, .21, .42, .33, .67, .19, .48]
    s.downbeats.append(start)
    for off in kicks:
        weight = .99 if off == 0 else .89
        if s.style == 'waltz' and off != 0:
            weight = .43
        if s.style == 'breaks' and off == 1.75:
            weight = .63
        if (s.style == 'wave' and bar < 8) or bar % 8 == 7:
            weight *= .60 if off == 3 else .89
        s.sound(start + off, 'kick', 0, .35, weight)
    for off in snares:
        weight = .90 if off == 3 else .79
        if s.style == 'breaks' and bar >= 36:
            weight = .94
        if s.style == 'wave' and 16 <= bar < 20:
            weight = .90 if off == 3 else .32
        s.sound(start + off, 'rim' if s.style == 'waltz' else 'snare', 0, .21, weight)
    for i, off in enumerate(hats):
        is_open = i % 4 == 3 and section == 'lift'
        strength = .75 if section == 'lift' else .60
        if bar % 4 == 3 and i == len(hats) - 1:
            strength *= .40
        s.sound(start + off, 'hat_open' if is_open else 'hat', 0, .12,
                hat_accents[i] * strength, .20 if i % 2 == 0 else -.28)
    if section == 'lift' and bar % 2:
        for off, weight in [(bp - .75, .27), (bp - .25, .39)]:
            s.sound(start + off, 'hat', 0, .09, weight, -.44)
    if s.style in ('garage', 'breaks') and bar % 2 == 0:
        s.sound(start + 2.25, 'snare', 0, .1, .29, -.24)
    if bar % 8 == 7:
        fill(s, start, bp, .39 if s.style == 'waltz' else .81)
    # Grace notes against the two-step backbeat and staggered breakbeat pick-ups.
    if s.style in ('garage', 'breaks') and bar % 4 in (1, 2):
        swing = .32 if s.style == 'garage' else .25
        s.sound(start + 1 + swing, 'hat', 0, .09, .31, -.39)
        s.sound(start + 3 + swing, 'hat', 0, .09, .22, .32)


def transition(s, newbar):
    # A synthesized filtered-noise inhale resolves into the downbeat.
    beat = newbar * s.beats_per_bar
    s.sound(beat - 2, 'rise', 0, 2, .49, -.12)
    s.sound(beat, 'crash', 0, 2.8, .53, .24)


def finish(s, root, voicing):
    beat = s.bars * s.beats_per_bar
    s.sound(beat, 'kick', 0, .5, .9)
    s.sound(beat, 'sub', root, 2.2, .85)
    chord(s, beat, voicing, 2.7, .4)
    s.note(beat, 'bell', voicing[-1], 2.4, .82)
    s.sound(beat, 'crash', 0, 2.6, .52, -.26)
    return s


def bach():
    s = Score('midnight-current', 'Midnight Current', 'Johann Sebastian Bach',
              'Prelude in C major, BWV 846', 1722, 'https://www.bachvereniging.nl/en/bwv/bwv-846',
              'Synthwave', 116, 4, 36, '#69eedd', 'wave', 0, 8)
    # Bach's opening five-note shapes, with the characteristic 1-2-3-4-5-3-4-5 figure.
    shapes = [
        [48,52,55,60,64], [48,50,57,62,65], [47,50,55,62,65], [48,52,55,60,64],
        [48,52,57,64,69], [48,50,54,57,62], [47,50,55,62,67], [47,48,52,55,60],
        [45,48,52,57,60], [38,45,50,54,60], [43,47,50,55,59], [43,46,52,55,61],
        [41,45,50,57,62], [41,44,50,53,59], [40,43,48,55,60], [41,45,48,53,57]]
    shapes += shapes[:8] + [[45,48,52,57,60], [41,45,48,53,57], [43,47,50,55,59], [43,47,53,59,62]]
    shapes += shapes[:4] + [[45,48,52,57,60], [41,45,48,53,57], [43,47,50,55,62], [43,47,53,59,62]]
    assert len(shapes) == s.bars
    for bar, sh in enumerate(shapes):
        beat = bar * 4
        air = bar < 2 or 24 <= bar < 28
        lift = 8 <= bar < 24 or bar >= 28
        drums(s, bar, 'air' if air else 'lift' if lift else 'groove')
        # The breakdown exposes the moving inner voices. In the chorus the harmonic
        # bed moves higher, leaving space between the bass and the answering lead.
        bed = [sh[1]+12, sh[2]+12, sh[3]+12]
        if lift:
            chord(s, beat, bed, 3.65, .23)
        elif bar >= 2:
            chord(s, beat+.05, bed[1:], 3.45, .19)

        root = sh[0]-12
        if root < 29:
            root += 12
        if air:
            s.sound(beat, 'sub', root, 3.20 if bar>=24 else 1.88, .59)
        else:
            bass_phrase = [
                [(0,0,.62), (.75,12,.20), (1.5,0,.42), (2.5,7,.34), (3.5,12,.32)],
                [(0,0,.38), (.75,7,.38), (1.5,12,.22), (2,0,.72), (3.25,7,.22), (3.5,0,.32)],
                [(0,0,1.31), (1.5,12,.31), (2.5,7,.47), (3.5,12,.25)],
                [(0,0,.68), (.75,12,.23), (1.5,7,.36), (2,0,.72)]]
            if 16 <= bar < 20:
                bass(s, beat, root, [(0,0,1.45), (2,0,.93), (3.25,12,.48)], 'sub', .78)
            else:
                bass(s, beat, root, bass_phrase[bar % 4], 'bass', .76)
            if bar % 4 == 3 and bar + 1 < s.bars:
                target = shapes[bar+1][0] - 12
                if target < 29:
                    target += 12
                s.sound(beat+3.5, 'bass', target+2, .22, .60)
                s.sound(beat+3.75, 'bass', target+1, .18, .54)

        accents = (1, .57, .68, .77, .95, .55, .72, .81)
        if 24 <= bar < 28:
            arp_voice, strength = 'felt', .76
        elif bar < 2:
            arp_voice, strength = 'bell', .84
        else:
            arp_voice, strength = 'pluck', .55 if lift else .72
        for i, index in enumerate([0,1,2,3,4,2,3,4] * 2):
            pitch = sh[index] + 12
            strength2 = strength * accents[i % 8] * (1.02 if i >= 8 else .94)
            s.note(beat + i / 4, arp_voice, pitch, .27, strength2, -.22 + .09 * index)
        if 2 <= bar < 8:
            # Introduce the high, dotted three-note hook in the spaces between arpeggios.
            if bar % 2 == 0:
                s.note(beat+1.5, 'reed', sh[2]+12, .63, .61, .10)
                s.note(beat+2.5, 'reed', sh[3]+12, .72, .72, .10)
            else:
                s.note(beat, 'reed', sh[4]+12, 2.47, .79, .10)
        if lift:
            lead = 'reed' if bar < 16 or bar >= 28 else 'wire'
            s.note(beat, lead, sh[4]+12, 1.42 if bar % 2 == 0 else 2.68, .93, .05)
            if bar % 2 == 0:
                s.note(beat + 2, lead, sh[3]+12, 1.55, .85, .05)
                s.note(beat+1.5, lead, sh[3]+12, .22, .60, .08)
                s.note(beat+1.75, lead, sh[2]+12, .20, .66, .08)
            else:
                s.note(beat+2.75, lead, sh[2]+12, .39, .76, .07)
                s.note(beat+3.50, lead, sh[3]+12, .36, .79, .07)
            if bar >= 28 and bar % 2 == 0:
                s.sound(beat, 'brass', sh[4], 1.38, .44, -.20)
                s.sound(beat+2, 'brass', sh[3], 1.46, .39, -.20)
            if 20 <= bar < 24 or bar >= 32:
                chord(s, beat+.5, [sh[2]+12,sh[3]+12], .26, .34, 'wire')
                chord(s, beat+2.75, [sh[2]+12,sh[3]+12], .34, .32, 'wire')
        elif 24 <= bar < 28:
            s.note(beat, 'flute', sh[4]+12, 2.38, .69, -.09)
            s.note(beat+2.5, 'flute', sh[3]+12, .90, .64, -.09)
    for bar in (2, 8, 16, 28):
        transition(s, bar)
    return finish(s, 36, [48,55,64,67,72])


def beethoven():
    s = Score('glass-circuit', 'Glass Circuit', 'Ludwig van Beethoven', 'Für Elise, WoO 59',
              1810, 'https://katalog.beethoven.de/cgi-bin/biblio/hans_en.pl?reccheck=2163&t_show=x&wert=BH+116&wertreg=SIG&x=u', 'UK Garage',
              132, 4, 40, '#ca94ff', 'garage', 9, 8)
    # Für Elise's neighbouring-note pickup and contrasting C-major response in a two-step meter.
    melody = [
        [(0,76,.35),(.5,75,.35),(1,76,.38),(1.5,75,.35),(2,76,.36),(2.5,71,.34),(3,74,.38),(3.5,72,.36)],
        [(0,69,1.50),(2,60,.39),(2.5,64,.4),(3,69,.8)],
        [(0,71,1.4),(2,64,.37),(2.5,68,.4),(3,71,.86)],
        [(0,72,1.42),(2,64,.40),(2.5,76,.42),(3,75,.41),(3.5,76,.41)],
        [(0,75,.42),(.5,76,.44),(1,71,.40),(1.5,74,.4),(2,72,.42),(2.5,69,1.35)],
        [(0,60,.44),(.5,64,.44),(1,69,.9),(2,71,1.8)],
        [(0,64,.4),(.5,72,.39),(1,71,.92),(2,69,1.86)],
        [(0,69,2.08),(3,71,.43),(3.5,72,.44)]]
    answer = [
        [(0,74,.42),(.5,76,1.0),(2,67,.48),(2.5,77,.48),(3,76,.85)],
        [(0,74,1.66),(2,65,.46),(2.5,76,.43),(3,74,.87)],
        [(0,72,1.60),(2,64,.46),(2.5,74,.44),(3,72,.85)],
        [(0,71,1.60),(2,64,.44),(2.5,76,.45),(3,76,.41),(3.5,88,.40)]]
    harmony = [
        (45,[57,60,64]), (45,[55,60,64]), (40,[56,59,64]), (45,[57,60,64]),
        (45,[57,60,64]), (45,[57,60,64]), (40,[56,59,62]), (45,[55,60,64])]
    bridge_harmony = [(48,[55,60,64]),(43,[55,59,62]),(45,[57,60,64]),(40,[56,59,62])]
    for bar in range(s.bars):
        beat, idx = bar * 4, bar % 8
        bridge = 16 <= bar < 24
        air = bar < 2 or 20 <= bar < 24
        root, v = bridge_harmony[idx%4] if bridge else harmony[idx]
        motif = answer[idx%4] if bridge else melody[idx]
        drums(s, bar, 'air' if air else 'lift' if bar >= 8 else 'groove')
        s.phrase(beat, motif, 'glass', .96 if air else .86, pan=-.08)
        if bar >= 24:
            # The returned minor theme trades right and left-hand octaves.
            s.phrase(beat, motif, 'pluck', .46 if bar%4 in (1,3) else .27, -12, .24, foreground=False)
        if not air:
            chord(s, beat+.03, v[1:], 2.78, .16)
        if not 20 <= bar < 24:
            accents = (.62,.35,.82,.51) if bar%2 == 0 else (.48,.94,.37,.63)
            for i, off in enumerate((.55,1.55,2.55,3.55)):
                if air and i % 2 == 0:
                    continue
                chord(s, beat+off, v, .21 if i%2 else .16, .43*accents[i], 'organ')
        else:
            # The second half of the bridge leaves the piano hanging in space.
            for off in (1.55,3.55):
                chord(s, beat+off, v[1:], .46, .13, 'organ')
        if not air:
            groove = [
                [(0,0,.73), (1.5,12,.24), (2.5,0,.46), (3.32,7,.28)],
                [(0,0,1.15), (1.5,7,.23), (2.75,12,.48)],
                [(0,0,.57), (.75,7,.28), (1.75,12,.36), (2.5,0,.78)],
                [(0,0,.82), (1.5,7,.32), (2.5,0,.34), (3.32,12,.25), (3.75,7,.17)]]
            bass(s, beat, root-12, groove[idx%4], 'wobble', .82)
        if bar in (9,13,25,29,33,37):
            # A little echo of the chromatic pickup answers the held arrival on A.
            for off, note, velocity in [(.75,64,.44),(1.0,63,.39),(1.25,64,.50)]:
                s.sound(beat+off, 'pluck', note, .20, velocity, .34)
        if bridge:
            s.sound(beat, 'reed', root+12, 2.45, .39 if air else .51, -.23)
        elif 8 <= bar < 16 or bar >= 32:
            # The left-hand arpeggios from the bagatelle become a bass-register hook.
            for off, note in zip((.75,1.25,2.25), (v[0]-12, v[2]-12, v[1])):
                s.sound(beat+off, 'pluck', note, .32, .48, -.26)
    for bar in (2, 8, 16, 24, 32):
        transition(s, bar)
    return finish(s, 33, [45,52,60,64,69])


def satie():
    s = Score('velvet-orbit', 'Velvet Orbit', 'Erik Satie', 'Gymnopédie No. 1', 1888,
              'https://catalogue.bnf.fr/ark:/12148/cb13918639z', 'Downtempo', 90, 3, 36,
              '#ffada7', 'waltz', 2, 12)
    melody = [
        [(0,78,.91),(1,81,.89),(2,79,.9)], [(0,78,.92),(1,73,.9),(2,71,.88)],
        [(0,73,.92),(1,74,.92),(2,69,.91)], [(0,69,2.82)],
        [(0,66,.95),(1,69,.92),(2,67,.91)], [(0,66,.92),(1,61,.91),(2,59,.91)],
        [(0,61,.91),(1,62,.91),(2,57,.88)], [(0,57,2.76)]]
    for bar in range(s.bars):
        beat, idx = bar * 3, (bar - 4) % 8
        bridge = 20 <= bar < 28
        air = bar < 4 or 20 <= bar < 24
        if bridge:
            root,v = [(45,[52,55,60,71]),(40,[55,59,62,64]),
                      (43,[55,59,62,67]),(38,[54,57,62,66])][bar%4]
        else:
            root,v = (43,[54,59,62,66]) if bar % 2 == 0 else (38,[54,57,61,66])
        drums(s, bar, 'air' if air else 'lift' if bar >= 12 else 'groove')
        s.sound(beat, 'sub', root, 1.60 if not air else 2.25, .66)
        s.sound(beat, 'felt', root+12, 1.55, .48, -.17)
        chord(s, beat+1, v, 1.76, .39 if bridge else .43, 'felt')
        if bar >= 8:
            chord(s, beat+.02, v[1:], 2.75, .19 if bridge else .23)
        if bridge:
            # The two-note, lower-register response keeps the pulse under the new phrase.
            response = [[(0,59,1.72),(2,62,.88)],[(0,61,1.8),(2,57,.9)],
                        [(0,54,2.85)],[(0,55,1.65),(2,57,.90)]][bar%4]
            s.phrase(beat, response, 'wire', .40, pan=-.24, foreground=False)
            # Concert melody from the later minor-coloured strain of the Gymnopédie.
            strain = [[(0,69,.91),(1,71,.91),(2,72,.93)],
                      [(0,76,.92),(1,74,.92),(2,71,.94)],
                      [(0,74,.92),(1,72,.92),(2,71,.93)], [(0,74,2.78)]]
            for off,pitch,length in strain[bar%4]:
                s.note(beat+off, 'flute', pitch, length, .82, .04)
            if bar>=24:
                s.sound(beat+2.5, 'bell', v[-1]+12, .34, .33, .34)
        elif bar >= 4:
            motif = melody[idx]
            s.phrase(beat, motif, 'flute' if bar >= 12 else 'felt', .88, pan=.04)
            if idx in (3,7):
                # A distant three-note answer only enters after the melody lands.
                for off,note,velocity in [(1.5,v[-1]+12,.41),(2,v[-2]+12,.33),(2.5,v[-3]+12,.31)]:
                    s.note(beat+off, 'bell', note, .36, velocity, .36)
            if bar >= 28:
                s.phrase(beat, motif, 'bell', .30 if bar % 2 else .21, 0, -.26, foreground=False)
            if 12 <= bar < 20 or bar >= 28:
                for off,note in [(.5,root+19),(1.5,root+16)]:
                    s.sound(beat+off, 'wire', note, .23, .31, -.38)
        else:
            s.note(beat+1, 'bell', v[-1], 1.63, .57, .24)
        if not air:
            s.sound(beat+2.52, 'felt', v[bar%3]+12, .31, .33, .38)
            if bar%4 in (1,3) and not bridge:
                next_root = 43 if bar%2 else 38
                s.sound(beat+2.55, 'sub', next_root-2, .31, .43)
    for bar in (4,12,24,28):
        transition(s, bar)
    return finish(s, 38, [50,57,61,66,74])


def grieg():
    s = Score('breakpoint', 'Breakpoint', 'Edvard Grieg', 'In the Hall of the Mountain King', 1875,
              'https://www.bso.org/works/grieg-peer-gynt-bill-barclay-adaptation',
              'Drum & Bass', 156, 4, 44, '#ffbc66', 'breaks', 11, 12)
    motif = [
        [(0,47,.42),(.5,49,.4),(1,50,.4),(1.5,52,.4),(2,54,.83),(3,50,.45),(3.5,54,.42)],
        [(0,53,.83),(1,49,.48),(1.5,53,.42),(2,52,.85),(3,48,.44),(3.5,52,.43)],
        [(0,47,.41),(.5,49,.40),(1,50,.41),(1.5,52,.4),(2,54,.83),(3,50,.42),(3.5,54,.41)],
        [(0,59,.91),(1,57,.85),(2,54,1.77)]]
    # Grieg's original clipped eighths, the upward leap to B, and the contrasting
    # F-sharp-major episode. The lower string ostinato supplies the displaced accents.
    theme = [
        [(0,47,.34),(.5,49,.34),(1,50,.37),(1.5,52,.35),(2,54,.42),(2.5,50,.33),(3,54,.77)],
        [(0,53,.44),(.5,49,.34),(1,53,.77),(2,52,.43),(2.5,48,.34),(3,52,.78)],
        [(0,47,.35),(.5,49,.34),(1,50,.36),(1.5,52,.35),(2,54,.42),(2.5,50,.34),(3,54,.37),(3.5,59,.42)],
        [(0,57,.43),(.5,54,.36),(1,50,.35),(1.5,54,.34),(2,57,1.68)]]
    dominant_theme = [
        [(0,54,.34),(.5,56,.34),(1,58,.37),(1.5,59,.35),(2,61,.42),(2.5,58,.33),(3,61,.78)],
        [(0,62,.43),(.5,58,.35),(1,62,.76),(2,61,.41),(2.5,58,.34),(3,61,.78)],
        [(0,54,.34),(.5,56,.34),(1,58,.36),(1.5,59,.35),(2,61,.42),(2.5,58,.33),(3,61,.77)],
        [(0,62,.43),(.5,58,.36),(1,62,.76),(2,61,1.68)]]
    for bar in range(s.bars):
        beat, idx = bar*4, bar%4
        air = bar < 4 or 20 <= bar < 24
        dominant = 8 <= bar < 16 or 28 <= bar < 32
        lift = 12 <= bar < 20 or bar >= 28
        root = 42 if dominant else (38 if idx == 3 else 35)
        drums(s, bar, 'air' if air else 'lift' if lift else 'groove')
        # The syncopated lower voice uses a different octave and shorter strokes
        # than the tune. These accents also carry the playable hold notes.
        if dominant:
            scale = {47:42,48:43,49:46,50:49,52:54,53:55,54:58,57:61,59:66}
            line = [(off,scale[pitch],length) for off,pitch,length in motif[idx]]
        else:
            line = motif[idx]
        s.phrase(beat, line, 'wire', .52 if lift else .44, pan=-.23, foreground=False)
        register = 12 if bar < 12 or 20 <= bar < 28 else 24
        if dominant:
            register -= 12
        lead_voice = 'wire' if bar < 4 or 20<=bar<24 else 'reed'
        for off,pitch,length in (dominant_theme if dominant else theme)[idx]:
            accent = 1 if off in (0,2) else (.90 if off%1 == 0 else .79)
            s.note(beat+off, lead_voice, pitch+register, length, .94*accent, .07)
            if bar >= 36 and off in (0,1,2,3):
                s.sound(beat+off, 'brass', pitch+register-12, min(length,.63), .53*accent, -.08)
        if air:
            bass(s, beat, root, [(0,0,1.35),(2,7,.78)], 'sub', .67)
        elif dominant and idx%2:
            bass(s, beat, 38, [(0,0,.79),(1,8,.34),(2,4,.71),(3,11,.58)], 'bass', .82)
        else:
            grooves = [
                [(0,0,.72),(1,7,.35),(1.75,12,.29),(2.5,0,.58),(3.5,7,.33)],
                [(0,0,1.26),(1.75,7,.30),(2.5,0,.41),(3.25,12,.39)],
                [(0,0,.68),(.75,7,.29),(1.75,12,.38),(2.5,0,.86)],
                [(0,0,.77),(1,7,.40),(2,0,.62),(3.25,7,.36)]]
            bass(s, beat, root, grooves[idx], 'wobble' if lift else 'bass', .78)
        if air or bar >= 32:
            tones = [54,58,61] if dominant else [47,50,54]
            chord(s, beat, tones, 2.79 if air else 1.45, .21)
        if bar >= 24 and bar % 2:
            for tick, velocity in enumerate([.23,.30,.41,.52]):
                s.sound(beat+3+tick/4,'hat',0,.14,velocity,.26)
    for bar in (4,8,16,24,32,40):
        transition(s, bar)
    return finish(s, 35, [47,54,59,62,71])


def mozart():
    s = Score('afterimage', 'Afterimage', 'Wolfgang Amadeus Mozart', 'Alla turca, K. 331', 1783,
              'https://kv.mozarteum.at/work/alla-turca-4103', 'Electro House',
              128, 4, 40, '#9dafef', 'house', 9, 16)
    motif = [
        [(0,71,.20),(.25,69,.20),(.5,68,.20),(.75,69,.2),(1,72,.78),(2,74,.21),(2.25,72,.2),(2.5,71,.2),(2.75,72,.2),(3,76,.80)],
        [(0,77,.21),(.25,76,.21),(.5,75,.21),(.75,76,.2),(1,83,.22),(1.25,81,.22),(1.5,80,.2),(1.75,81,.2),(2,83,.21),(2.25,81,.22),(2.5,80,.2),(2.75,81,.2),(3,84,.85)],
        [(0,81,.44),(.5,84,.42),(1,83,.41),(1.5,81,.42),(2,80,.42),(2.5,81,.40),(3,83,.85)],
        [(0,81,.9),(1,76,.85),(2,72,.88),(3,69,.82)]]
    major = [
        [(0,69,.35),(.5,71,.36),(1,73,.74),(2,69,.34),(2.5,71,.36),(3,73,.76)],
        [(0,69,.38),(.5,71,.38),(1,73,.39),(1.5,69,.40),(2,74,.77),(3,73,.75)],
        [(0,71,.41),(.5,73,.4),(1,74,.83),(2,71,.39),(2.5,73,.38),(3,74,.76)],
        [(0,76,.81),(1,74,.77),(2,73,.42),(2.5,71,.42),(3,69,.80)]]
    march = [
        [(0,69,.36),(.5,71,.36),(1,73,.82),(2,69,.37),(2.5,71,.36),(3,73,.40),(3.5,71,.37)],
        [(0,69,.37),(.5,68,.37),(1,66,.42),(1.5,68,.37),(2,69,.42),(2.5,71,.37),(3,68,.42),(3.5,64,.39)],
        [(0,69,.38),(.5,71,.37),(1,73,.84),(2,69,.37),(2.5,71,.37),(3,73,.41),(3.5,71,.37)],
        [(0,69,.38),(.5,68,.37),(1,66,.39),(1.5,71,.37),(2,68,.42),(2.5,64,.38),(3,69,.88)]]
    for bar in range(s.bars):
        beat, idx = bar*4, bar%4
        bright = 12 <= bar < 24 or bar >= 32
        full_march = 16 <= bar < 24 or bar >= 32
        air = bar < 2 or 24 <= bar < 28
        root = [33,33,40,33][idx]
        v = [57,61 if bright else 60,64] if idx != 2 else [56,59,64]
        drums(s, bar, 'air' if air else 'lift' if bright else 'groove')
        if full_march:
            # The arcade response becomes a lower-string counterrhythm under Mozart's
            # octave march. Its articulated notes remain clear through the full refrain.
            harmonized = {69:45,71:52,73:57,74:61,76:64}
            lower = [(off,harmonized[pitch],length) for off,pitch,length in major[idx]]
            s.phrase(beat, lower, 'wire', .48, pan=-.21, foreground=False)
            for off,pitch,length in march[idx]:
                gain = .90 if off in (0,1,3) else .76
                s.note(beat+off, 'brass', pitch, length, gain, .02)
                if bar>=32:
                    s.sound(beat+off, 'chip', pitch+12, min(.40,length), .33, .27)
        else:
            s.phrase(beat, (major if bright else motif)[idx], 'brass' if bright else 'chip', .87, pan=-.06)
            if bright:
                s.phrase(beat, major[idx], 'chip', .30, 12, .21, foreground=False)
        if air:
            chord(s, beat+.03, v[1:], 2.45, .18)
        elif idx%2==0:
            chord(s, beat, v, 2.76, .16)
        for i,off in enumerate((.5,1.5,2.5,3.5)):
            response = (.35,.58,.42,.75) if idx%2==0 else (.62,.32,.72,.45)
            strength = .36 if bright else .30
            if air:
                strength = .14
            chord(s,beat+off,v,.28,strength*response[i],'organ')
        if not air:
            main = [(0,0,.42),(.5,12,.23),(1,0,.38),(1.5,7,.30),(2,0,.42),(2.5,12,.25),(3,0,.39),(3.5,7,.27)]
            reply = [(0,0,.68),(.75,7,.20),(1.5,12,.28),(2,0,.44),(2.75,7,.40),(3.50,12,.26)]
            bass(s,beat,root,main if idx%2==0 else reply,'bass',.78)
        if 24<=bar<28:
            # The minor theme comes back in a bare piano-and-counterbass interlude.
            for off,pitch,length in motif[idx]:
                s.sound(beat+off, 'felt', pitch-12, length, .41, -.28)
        if bright and bar%4==3:
            s.sound(beat+3.50, 'bell', 76, .22, .34, .39)
    for bar in (2,8,12,24,28,32):
        transition(s, bar)
    return finish(s, 33, [45,52,61,64,69])


def album():
    return [bach(), beethoven(), satie(), grieg(), mozart()]
