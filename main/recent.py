"""
levboard/main/recent.py

Displays recent events, such as new certifications & plays milestones,
along with all time plays changes.
"""

from collections import Counter
import csv
import functools
from concurrent import futures
from datetime import date, timedelta
import itertools
from operator import attrgetter, itemgetter, methodcaller
from typing import Iterator, Optional

from config import FIRST_DATE
from model import SongCert, Song
from model.spotistats import songs_week, Position
from stats import CERTS, PLAYS_MILESTONES, time_to_plays, time_to_units
from storage import Song, SongUOW

TODAY = date.today()
LAST_WK = TODAY - timedelta(days=7)


def get_new_songs(uow: SongUOW):
    """
    Scans all of the songs recently listened to, displaying all the ones missing in the system.
    """

    all_songs = uow.songs.list()
    upcoming_week = songs_week(after=LAST_WK, before=TODAY + timedelta(days=1))
    for pos in upcoming_week:
        if pos.id not in all_songs and pos.plays > 1:
            song = Song(pos.id)
            print(f'{song} ({pos.id}) not found ({pos.plays} plays)')


cached_listens: Optional[list[Position]] = None


def collect_listens():
    global cached_listens
    if cached_listens is not None:
        return cached_listens
    listens = songs_week(after=date(2000, 1, 1), before=TODAY + timedelta(days=1))
    cached_listens = listens
    return listens


def get_missing_songs(uow: SongUOW, threshold: int = 10):
    """
    Scans all of the songs listened to across all time,
    displaying all the ones missing in the system.
    """

    all_songs = uow.songs.list()
    all_listened = collect_listens()
    missing: list[list] = []
    for pos in all_listened:
        if pos.id not in all_songs and pos.plays > threshold:
            song = Song(pos.id)
            print(f'{song} ({pos.id}) not found ({pos.plays} plays)')
            missing.append(
                [
                    f'https://stats.fm/track/{pos.id}',
                    pos.id,
                    pos.plays,
                    str(song),
                ]
            )

    with open('missing.csv', 'w+') as fp:
        w = csv.writer(fp)
        w.writerows(missing)


def get_unused_ids(uow: SongUOW, threshold: int = 0):
    """
    Scans all of the songs listened to across all time, and then
    displays all of the ones that aren't actually being listened to.
    """

    all_listened = collect_listens()

    listened_ids = {pos.id for pos in all_listened if pos.plays > threshold}
    unlistened: list[list] = []
    for song in uow.songs:
        for id in song.ids:
            if id not in listened_ids:
                print(
                    f'{song} variant with id {id} not streamed. '
                    f'link: https://stats.fm/track/{id}'
                )

                unlistened.append(
                    [f'https://stats.fm/track/{id}', id, str(song)]
                )
    with open('unused.csv', 'w+') as fp:
        w = csv.writer(fp)
        w.writerows(unlistened)


def audit_unique_ids(uow: SongUOW):
    id_counter = Counter(
        itertools.chain.from_iterable(song.ids for song in uow.songs)
    )
    if id_counter.most_common(1)[0][1] == 1: 
        print('all ids are unique :)')
        return
    for (id, count) in id_counter.most_common():
        if count > 1:
            print(f'duplicate id found: {id}')


def get_new_certs(uow: SongUOW, cert: SongCert):
    contenders = (song for song in uow.songs if song.cert == cert)

    with futures.ThreadPoolExecutor() as executor:
        info = executor.map(
            functools.partial(time_to_units, units_mark=cert.to_units()),
            contenders,
        )

    for song, day, _ in info:
        if day >= LAST_WK:
            print(f'{day.isoformat()}: {cert:>4s} | {song}')


def get_all_new_certs(uow: SongUOW):
    print('New certifications:')
    for cert in CERTS:
        get_new_certs(uow, cert)


def get_new_plays(uow: SongUOW, plays: int):
    contenders = (
        song
        for song in uow.songs
        if song.plays >= plays and song.plays <= (plays + 25)
    )
    with futures.ThreadPoolExecutor() as executor:
        info = executor.map(
            functools.partial(time_to_plays, plays=plays),
            contenders,
        )

    for song, day, _ in info:
        if day >= LAST_WK:
            print(f'{day.isoformat()}: {plays:>3} | {song}')


def get_all_new_plays(uow: SongUOW):
    print('New plays milestones:')
    for plays in PLAYS_MILESTONES:
        get_new_plays(uow, plays)


def get_all_time_plays_changes(uow: SongUOW):
    contenders = sorted(uow.songs, key=attrgetter('plays'), reverse=True)[:150]
    # get top 150 just in case there's a lot of moving around,
    # but we will look at top 100

    with futures.ThreadPoolExecutor() as executor:
        # this part is threaded so that it takes less time, or else the rest
        # of the program will have to do those same requests sequentially
        # when it calls for song.period_plays
        executor.map(methodcaller('_populate_listens'), contenders)

    current_top = sorted(
        ((song, song.period_plays(FIRST_DATE, TODAY)) for song in contenders),
        key=itemgetter(1),
        reverse=True,
    )[:100]

    current_pos: Iterator[tuple[Song, int, int]] = (
        (
            song,
            plays,
            len([entry for entry in current_top if entry[1] > plays])
            + 1,  # position
        )
        for song, plays in current_top
    )

    last_top = sorted(
        (
            (song, song.period_plays(FIRST_DATE, LAST_WK))
            for song in contenders
        ),
        key=itemgetter(1),
        reverse=True,
    )

    last_pos: list[tuple[Song, int, int]] = [
        (
            song,
            plays,
            len([entry for entry in last_top if entry[1] > plays])
            + 1,  # position
        )
        for song, plays in last_top
    ]

    for song, plays, pos in current_pos:
        _, l_plays, l_pos = next(
            entry for entry in last_pos if entry[0] == song
        )

        movement = l_pos - pos
        if movement == 0:
            change = '='
        elif movement < 0:
            change = '▼' + str(-1 * movement)
        else:
            change = '▲' + str(movement)

        plays_change = plays - l_plays

        print(
            f'{pos:>3} {f"({change})":>5} | {song:<60} '
            f'| {plays} (+{plays_change})'
        )


def main():
    uow = SongUOW()
    audit_unique_ids(uow)
    get_new_songs(uow)
    # print('')
    # get_missing_songs(uow)
    print('')
    # get_unused_ids(uow)
    # print('')
    # get_all_new_certs(uow)
    # print('')
    # get_all_new_plays(uow)
    # print('')
    # get_all_time_plays_changes(uow)


if __name__ == '__main__':
    main()
