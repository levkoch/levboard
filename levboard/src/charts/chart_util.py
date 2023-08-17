from datetime import date, timedelta
import functools
from typing import Optional
from concurrent import futures

from ..storage import Process
from ..model import Entry, Song, spotistats

SONG_ROW_HEADERS: list[str] = [
    'MV',
    'Title',
    'Artists',
    'TW',
    'LW',
    'OC',
    'PTS',
    'PLS',
    'PK',
    '(WK)',
]


def insert_entry(song_id: str, entry: Entry, process: Process) -> None:
    song: Optional[Song] = process.songs.get(song_id)
    if song is None:
        song = process.songs.create(song_id)
    song.add_entry(entry)


def insert_entries(
    process: Process,
    positions: list[spotistats.Position],
    start_date,
    end_date,
):
    entries = (
        Entry(
            end=end_date,
            start=start_date,
            plays=position.plays,
            place=position.place,
            points=position.points,
        )
        for position in positions
    )
    with futures.ThreadPoolExecutor() as executor:
        # force the iterator to execute
        list(
            executor.map(
                functools.partial(insert_entry, process=process),
                (position.id for position in positions),
                entries,
            )
        )


def get_movement(current: date, last: date, song: Song) -> str:
    # current place will always return an entry or else the program
    # shouldn't be asking for the movement
    c_place: Entry = song.get_entry(current)
    p_place: Optional[Entry] = song.get_entry(last)
    weeks = song.weeks

    if p_place is None:
        if weeks == 1:
            return 'NEW'
        else:
            return 'RE'

    movement = p_place.place - c_place.place
    if movement == 0:
        return '='
    if movement < 0:
        return '▼' + str(-1 * movement)
    return '▲' + str(movement)


def get_peak(song: Song) -> str:
    num_to_exp: dict = {
        '0': '⁰',
        '1': '¹',
        '2': '²',
        '3': '³',
        '4': '⁴',
        '5': '⁵',
        '6': '⁶',
        '7': '⁷',
        '8': '⁸',
        '9': '⁹',
    }
    if song.peak > 10:
        return str(song.peak)
    if song.peakweeks == 1:
        return str(song.peak)
    pweeks = str(song.peakweeks)
    for (k, v) in num_to_exp.items():
        pweeks = pweeks.replace(k, v)
    return str(song.peak) + pweeks


def update_song_sheet(
    rows: list[list],
    process: Process,
    positions: list[spotistats.Position],
    start_date: date,
    end_date: date,
    week_count: int,
) -> list[list]:
    
    actual_end = end_date - timedelta(days=1)
    new_rows = [
        [
            f'{start_date.isoformat()} to {actual_end.isoformat()}',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            week_count,
        ], SONG_ROW_HEADERS
    ]

    for pos in positions:
        song: Song = process.songs.get(pos.id)
        prev: Optional[Entry] = song.get_entry(start_date)
        movement: str = get_movement(end_date, start_date, song)
        peak: str = get_peak(song)

        new_rows.append(
            [
                movement,
                song.name,
                ', '.join(song.artists),
                pos.place,
                prev.place if prev is not None else '-',
                song.weeks,
                pos.points,
                pos.plays,
                peak,
                week_count,
            ]
        )

    return new_rows + [['']] + rows
