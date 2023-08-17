"""
The original charts code (not using points and with flexible week bounds.)
"""

from datetime import date, timedelta
from operator import attrgetter

from ..storage import Process
from ..config import Config
from ..model import Song, spotistats

from .chart_util import (
    get_movement,
    get_peak,
    insert_entries,
    update_song_sheet,
)


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


def original_charts(process: Process) -> dict:
    song_rows: list[list[str]] = []
    week_count = 0
    start_date = process.config.start_date

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
        song_rows = update_song_sheet(
            song_rows, process, positions, start_date, end_date, week_count
        )
        start_date = end_date  # shift pointer

    return song_rows
