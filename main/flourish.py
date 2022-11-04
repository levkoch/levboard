import csv
import functools
import itertools

from typing import Iterator, Union
from datetime import date, timedelta, datetime
from concurrent import futures

from model import Album
from config import FIRST_DATE, LEVBOARD_SHEET
from storage import SongUOW
from spreadsheet import Spreadsheet


def get_all_weeks() -> Iterator[date]:
    day = FIRST_DATE + timedelta(days=14)
    while day <= date.today():
        yield day
        day += timedelta(days=14)


def get_album_units(week: date, album: Album) -> tuple[date, int]:
    return week, album.period_units(FIRST_DATE, week)


started_counter = itertools.count(start=1)
completed_counter = itertools.count(start=1)


def get_album_sellings(
    album: Album, weeks: list[date]
) -> dict[str, Union[str, int]]:

    print(f'-> [{next(started_counter):2d}] collecting info for {album}')
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

    print(
        f'!! [{next(completed_counter):2d}] finished collecting info for {album}'
    )
    return info


def main():
    start_time = datetime.now()
    uow = SongUOW()
    weeks = list(get_all_weeks())
    str_weeks = list(i.isoformat() for i in weeks)
    albums = (album for album in uow.albums if album.units >= 2000)

    with futures.ThreadPoolExecutor(thread_name_prefix='main') as executor:
        data = executor.map(
            functools.partial(get_album_sellings, weeks=weeks), albums
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
    sheet.append_range(f'BOT_FLOURISH!A1:CZ{len(sheet_rows)+1}', values = sheet_rows)

    print('')
    print(f'Process Completed in {datetime.now() - start_time}')


if __name__ == '__main__':
    main()
