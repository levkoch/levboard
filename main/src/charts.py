"""
main/src/charts.py
"""

import itertools

from concurrent import futures
from datetime import date, datetime, timedelta
from operator import attrgetter
from typing import Optional

from .storage import Process
from .config import Config
from .model import Entry, Song, spotistats


def load_week(config: Config, start_day: date, end_day: date):
    positions = spotistats.songs_week(config.username, start_day, end_day)
    positions = list(
        filter(lambda pos: pos.plays >= config.min_plays, positions)
    )

    if len(positions) < 60:
        print(f'Only {len(positions)} songs got over 1 stream that week.')
        raise ValueError('not enough songs')

    cutoff: int = positions[59].plays
    print(f'Song cutoff this week is {cutoff} plays.')
    positions = [pos for pos in positions if pos.plays >= cutoff]
    for pos in positions:
        pos.place = len([p for p in positions if p.plays > pos.plays]) + 1
    return sorted(positions, key=attrgetter('plays'), reverse=True)


def get_positions(
    config: Config, start_date: date, end_date: date
) -> tuple[list[dict], date]:
    while True:
        print(
            f'\nCollecting songs from {start_date.isoformat()} to {end_date.isoformat()}.'
        )
        try:
            positions = load_week(config, start_date, end_date)
        except ValueError:
            print('Not enough songs found in the time range.')
            end_date += timedelta(days=7)
            if end_date > date.today():
                raise ValueError(
                    'Not enough songs found in this week.'
                ) from None
        else:
            return positions, end_date


def insert_entry(song_id: str, process: Process, entry: Entry) -> None:
    song: Optional[Song] = process.songs.get(song_id)
    if not song:
        song = process.songs.create(song_id)
    song.add_entry(entry)


def insert_entries(
    process: Process,
    positions: list[spotistats.Position],
    start_date,
    end_date,
):
    print(f'inserting {len(positions)} entries')
    entries = (
        Entry(
            end=end_date,
            start=start_date,
            plays=position.plays,
            place=position.place,
            points=position.plays * process.config.current_weight,
        )
        for position in positions
    )
    with futures.ThreadPoolExecutor() as executor:
        # force the iterator to execute
        list(
            executor.map(
                insert_entry,
                (position.id for position in positions),
                itertools.repeat(process),
                entries,
            )
        )


def clear_entries(uow: Process) -> None:
    print('Clearing previous entries.')
    for song in uow.songs:
        song._entries = []


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


def show_chart(
    process: Process,
    positions: list[spotistats.Position],
    start: date,
    end: date,
    week_count: int,
):
    print(f'\n({week_count}) Week of {start.isoformat()} to {end.isoformat()}')
    print(f' MV | {"Title":<45} | {"Artists":<45} | TW | LW | OC | PLS | PK')
    for pos in positions:
        song: Song = process.songs.get(pos.id)
        prev = song.get_entry(start)
        print(
            f"{get_movement(end, start, song):>3} | {song.name:<45} | {', '.join(song.artists):<45} | {pos.place:<2}"
            f" | {(prev.place if prev else '-'):<2} | {song.weeks:<2} | {pos.plays:<3} | {get_peak(song):<3}"
        )
    print('')


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


def create_song_chart(process: Process) -> dict:
    username = process.config.username
    print(f'Finding song data for {username}.')
    start_time = datetime.now()
    week_count = 0
    start_date = process.config.start_date

    clear_entries(process)

    while True:
        end_date = start_date + timedelta(days=7)

        try:
            positions, end_date = get_positions(
                process.config, start_date, end_date
            )
        # thrown when not enough to fill a week so week is extended past today
        except ValueError:
            print('')
            print('All weeks found. Ending Process.')
            break  # from the big loop

        insert_entries(process, positions, start_date, end_date)
        week_count += 1
        show_chart(process, positions, start_date, end_date, week_count)
        start_date = end_date  # shift pointer

    print('')
    print(f'Process Completed in {datetime.now() - start_time}')

    return process.songs.to_dict()
