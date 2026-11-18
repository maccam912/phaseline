"""Check playability of the shipping JSON without any audio production dependencies."""
from collections import defaultdict
import json
from pathlib import Path

from charts import CAPACITY, FINGERS


def check_chart(notes, level, duration):
    assert notes and all(a['t'] <= b['t'] for a, b in zip(notes, notes[1:])), 'unordered notes'
    assert {n['l'] for n in notes} == set(range(10)), 'unused home-row lane'
    groups = defaultdict(list)
    for note in notes:
        assert 0 <= note['t'] and note['d'] >= 0 and note['t'] + note['d'] <= duration, 'note outside audio'
        groups[note['t']].append(note)
    release = [-1.0] * 8
    peak = 0
    for time, hits in groups.items():
        active = {i for i, end in enumerate(release) if end > time}
        for note in hits:
            finger = FINGERS[note['l']]
            assert finger not in active, 'overlapping notes need the same finger'
            assert time - release[finger] >= .049, 'finger has no time to lift'
            active.add(finger)
            release[finger] = time + max(note['d'], .040)
        peak = max(peak, len(active))
    assert peak == CAPACITY[level], f'peak of {peak} fingers for {level}'


if __name__ == '__main__':
    catalog = Path(__file__).resolve().parents[2] / 'music/library.json'
    for song in json.loads(catalog.read_text()):
        assert set(song['charts']) == set(CAPACITY)
        for level, notes in song['charts'].items():
            try:
                check_chart(notes, level, song['duration'])
            except AssertionError as exc:
                raise AssertionError(f"{song['title']} ({level}): {exc}") from exc
        print(f"{song['title']}: 4 charts, all ten lanes, finger limits verified")
