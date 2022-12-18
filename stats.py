import functools
import itertools
from concurrent import futures
from datetime import datetime, timedelta
from typing import Iterator, Optional

from main.model import Song, SongCert, spotistats
from main.storage import SongUOW

uow = SongUOW()


def get_song_play_history(song: Song) -> Iterator[dict]:
    with futures.ThreadPoolExecutor() as executor:
        # make song main id into list to add to alternate ids
        mapped = executor.map(
            spotistats.song_play_history, ([song.id] + song.alt_ids)
        )

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


def top_shortest_time_plays_milestones(uow: SongUOW, plays: int):
    contenders = (song for song in uow.songs if song.plays >= plays)

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


def top_song_consecutive_weeks(uow: SongUOW, top: Optional[int]):
    units: list[tuple[Song, int]] = [
        (song, song.get_conweeks(top)) for song in uow.songs
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


def display_all_songs(uow: SongUOW):
    all_songs = [song for song in uow.songs if song.units]
    all_songs.sort(key=lambda i: i.units, reverse=True)
    for (count, song) in enumerate(all_songs):
        print(
            f'{count + 1:>4} | {song.name:<45} | {song.str_artists:<45} | peak: {song.peak:<2} '
            f'{(("(" + str(song.peakweeks) + ")") if (song.peak < 11 and song.peakweeks > 1) else " "):<4} '
            f'| weeks: {song.weeks:<2} | plays: {song.plays:<3} | {song.cert}'
        )


MILESTONES = [25, 50, 75, 100, 150, 200, 250, 300, 350, 400]

if __name__ == '__main__':
    uow = SongUOW()

    for milestone in MILESTONES[::-1]:
        top_shortest_time_plays_milestones(uow, milestone)

    display_all_songs(uow)
