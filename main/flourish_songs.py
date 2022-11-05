import csv
import functools
import itertools
from operator import attrgetter

from typing import Iterator, Union
from datetime import date, timedelta, datetime
from concurrent import futures

from model import Song
from config import FIRST_DATE, LEVBOARD_SHEET
from storage import SongUOW
from spreadsheet import Spreadsheet


def get_all_weeks() -> Iterator[date]:
    day = FIRST_DATE + timedelta(days=7)
    while day <= date.today():
        yield day
        day += timedelta(days=7)


def get_song_points(week: date, song: Song) -> tuple[date, int]:
    return week, song.period_points(FIRST_DATE, week)


started_counter = itertools.count(start=1)
completed_counter = itertools.count(start=1)


def get_song_sellings(
    song: Song, weeks: list[date]
) -> dict[str, Union[str, int]]:

    print(f'-> [{next(started_counter):03d}] collecting info for {song}')
    info = {
        'title': song.name,
        'artist': song.str_artists,
    }
    with futures.ThreadPoolExecutor(
        thread_name_prefix=song.name
    ) as executor:
        data = executor.map(
            functools.partial(get_song_points, song=song), weeks
        )

    for date, units in data:
        info[date.isoformat()] = units

    print(
        f'!! [{next(completed_counter):03d}] finished collecting info for {song}'
    )
    return info


def main():
    start_time = datetime.now()
    uow = SongUOW()
    weeks = list(get_all_weeks())
    str_weeks = list(i.isoformat() for i in weeks)
    songs = (song for song in sorted(uow.songs, key=attrgetter('points')) if song.points >= 200)

    with futures.ThreadPoolExecutor(thread_name_prefix='main') as executor:
        data = executor.map(
            functools.partial(get_song_sellings, weeks=weeks), songs
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
    main()
