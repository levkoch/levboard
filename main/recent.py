"""
levboard/main/recent.py

Displays recent events, such as new certifications & plays milestones,
along with all time plays changes.
"""

import functools
from concurrent import futures
from datetime import date, timedelta
from operator import attrgetter, itemgetter, methodcaller
from typing import Iterator

from config import FIRST_DATE
from model import SongCert
from stats import CERTS, PLAYS_MILESTONES, time_to_plays, time_to_units
from storage import Song, SongUOW

TODAY = date.today()
LAST_WK = TODAY - timedelta(days=7)


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
        if song.plays >= plays and song.plays <= (plays + 50)
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
    get_all_new_certs(uow)
    print('')
    get_all_new_plays(uow)
    print('')
    get_all_time_plays_changes(uow)


if __name__ == '__main__':
    main()
