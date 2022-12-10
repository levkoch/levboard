import csv
import functools
import itertools
from concurrent import futures
from datetime import date, datetime, timedelta
from operator import attrgetter
from typing import Iterator, Union

from config import FIRST_DATE, LEVBOARD_SHEET
from model import Album, Song
from spreadsheet import Spreadsheet
from storage import SongUOW


def get_all_weeks() -> Iterator[date]:
    day = FIRST_DATE + timedelta(days=7)
    while day <= date.today():
        yield day
        day += timedelta(days=7)


def get_album_units(week: date, album: Album) -> tuple[date, int]:
    return week, album.period_units(FIRST_DATE, week)


def get_album_sellings(
    album: Album,
    weeks: list[date],
    started: itertools.count,
    completed: itertools.count,
) -> dict[str, Union[str, int]]:

    print(f'[{next(started):02d}] ->  collecting info for {album}')
    info = {
        'title': album.title,
        'artist': album.str_artists,
    }
    with futures.ThreadPoolExecutor(
        thread_name_prefix=album.title
    ) as executor:
        data = executor.map(
            functools.partial(get_album_units, album=album), weeks
        )

    for date, units in data:
        info[date.isoformat()] = units

    print(f' !! [{next(completed):02d}] finished collecting info for {album}')
    return info


def flourish_albums():
    start_time = datetime.now()
    uow = SongUOW()
    weeks = list(get_all_weeks())
    str_weeks = list(i.isoformat() for i in weeks)
    albums = (album for album in uow.albums if album.units >= 1000)

    started_counter = itertools.count(start=1)
    completed_counter = itertools.count(start=1)

    with futures.ThreadPoolExecutor(thread_name_prefix='main') as executor:
        data = executor.map(
            functools.partial(
                get_album_sellings,
                weeks=weeks,
                started=started_counter,
                completed=completed_counter,
            ),
            albums,
        )

    sheet_rows = [['Title', 'Artist'] + str_weeks]
    for info in data:
        entry = [info['title'], info['artist']]
        for date in str_weeks:
            entry.append(info[date])
        sheet_rows.append(entry)

    with open('info.csv', 'a+', encoding='UTF-8') as f:
        csv.writer(f).writerows(sheet_rows)
        # write to csv in case google sheets is annoying

    sheet = Spreadsheet(LEVBOARD_SHEET)
    sheet.append_range(
        f'BOT_FLOURISH!A1:CZ{len(sheet_rows)+1}', values=sheet_rows
    )

    print('')
    print(f'Process Completed in {datetime.now() - start_time}')


def get_all_weeks() -> Iterator[date]:
    day = FIRST_DATE + timedelta(days=7)
    while day <= date.today():
        yield day
        day += timedelta(days=7)


def get_song_points(week: date, song: Song) -> tuple[date, int]:
    return week, song.period_points(FIRST_DATE, week)


def get_song_sellings(
    song: Song,
    weeks: list[date],
    started: itertools.count,
    completed: itertools.count,
) -> dict[str, Union[str, int]]:

    print(f'-> [{next(started):03d}] collecting info for {song}')
    info = {
        'title': song.name,
        'artist': song.str_artists,
    }
    with futures.ThreadPoolExecutor(thread_name_prefix=song.name) as executor:
        data = executor.map(
            functools.partial(get_song_points, song=song), weeks
        )

    for date, units in data:
        info[date.isoformat()] = units

    print(f'!! [{next(completed):03d}] finished collecting info for {song}')
    return info


def flourish_songs():
    start_time = datetime.now()
    uow = SongUOW()
    weeks = list(get_all_weeks())
    str_weeks = list(i.isoformat() for i in weeks)
    songs = (
        song
        for song in sorted(uow.songs, key=attrgetter('points'))
        if song.points >= 200
    )
    started_counter = itertools.count(start=1)
    completed_counter = itertools.count(start=1)

    with futures.ThreadPoolExecutor(thread_name_prefix='main') as executor:
        data = executor.map(
            functools.partial(
                get_song_sellings,
                weeks=weeks,
                started=started_counter,
                completed=completed_counter,
            ),
            songs,
        )

    sheet_rows = [['Title', 'Artist'] + str_weeks]
    for info in data:
        entry = [info['title'], info['artist']]
        for date in str_weeks:
            entry.append(info[date])
        sheet_rows.append(entry)

    with open('info.csv', 'a+', encoding='UTF-8') as f:
        csv.writer(f).writerows(sheet_rows)
        # write to csv in case google sheets is annoying

    sheet = Spreadsheet(LEVBOARD_SHEET)
    range = f'BOT_FLOURISH!A1:CZ{len(sheet_rows)+1}'
    sheet.delete_range(range)
    sheet.append_range(range, sheet_rows)

    print('')
    print(f'Process Completed in {datetime.now() - start_time}')


if __name__ == '__main__':
    flourish_albums()
    # flourish_songs()
