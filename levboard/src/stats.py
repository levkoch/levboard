import functools
import itertools
from concurrent import futures
from datetime import datetime, timedelta
from typing import Iterator, Optional

from .model import spotistats, Song, SongCert
from .storage import Process


def get_song_play_history(song: Song) -> list[dict]:
    with futures.ThreadPoolExecutor() as executor:
        # make song main id into list to add to alternate ids
        mapped = executor.map(spotistats.song_play_history, (song.ids))

    return list(itertools.chain(*mapped))


def time_to_plays(song: Song, plays: int) -> timedelta:
    play_record = get_song_play_history(song)

    if len(play_record) < plays:
        raise ValueError('not enough plays for song')

    play_record.sort(key=lambda i: i['finished_playing'])
    first_play: datetime = play_record[0]['finished_playing']
    wanted_play: datetime = play_record[plays - 1]['finished_playing']

    time = wanted_play - first_play

    return (song, time)


def top_shortest_time_plays_milestones(process: Process, plays: int):
    contenders = (song for song in process.songs if song.plays >= plays)

    with futures.ThreadPoolExecutor() as executor:
        mapped = executor.map(
            functools.partial(time_to_plays, plays=plays), contenders
        )

    units = [i for i in mapped if i[1].days > 1]
    units.sort(key=lambda i: i[1])
    if len(units) > 16:
        units = [i for i in units if i[1] <= units[19][1]]
    print(f'Fastest songs to reach {plays} plays:')
    for (song, time) in units:
        place = len([unit for unit in units if unit[1].days < time.days]) + 1
        print(f'{place:<2} | {song:<60} | {time.days} days')
    print('')


def top_song_consecutive_weeks(process: Process, top: Optional[int]):
    units: list[tuple[Song, int]] = [
        (song, song.get_conweeks(top)) for song in process.songs
    ]
    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] >= units[19][1] and i[1] > 1]

    print(
        f"Songs with most consecutive weeks {f'in the top {top}' if top else 'on chart'}:"
    )
    for (song, weeks) in units:
        place = len([unit for unit in units if unit[1] > weeks]) + 1
        print(
            f"{place:>2} | {f'{song.name} by {song.str_artists}':<55} | {weeks:>2} wks"
        )


MILESTONES = [25, 50, 75, 100, 150, 200, 250, 300, 350, 400]

if __name__ == '__main__':
    process = Process({'username': 'lev'})
    with process:
        for milestone in MILESTONES[::-1]:
            top_shortest_time_plays_milestones(process, milestone)
