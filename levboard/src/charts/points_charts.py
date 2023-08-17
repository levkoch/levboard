"""
levboard/src/charts/points_charts.py

The updates charts that use points and are much faster.
"""

import itertools

from concurrent import futures
from datetime import date, timedelta
from typing import Iterator

from ..storage import Process
from ..model import spotistats
from ..config import Config
from .chart_util import insert_entries, update_song_sheet


def load_week(
    config: Config,
    start_day: date,
    end_day: date,
    started: itertools.count,
    completed: itertools.count,
) -> spotistats.Week:
    print(
        f'-> [{next(started):03d}] collecting info for week ending {end_day.isoformat()}'
    )
    songs = spotistats.songs_week(
        config.username,
        start_day,
        end_day,
        adjusted=True,
        max_adjusted=config.max_adjusted,
    )
    print(
        f'!! [{next(completed):03d}] finished collecting info for week ending {end_day.isoformat()}'
    )
    return spotistats.Week(start_day=start_day, end_day=end_day, songs=songs)


def load_all_weeks(config: Config) -> list[spotistats.Week]:
    print('Loading all weeks')

    start_day = config.start_date
    started_counter = itertools.count(start=1)
    completed_counter = itertools.count(start=1)

    with futures.ThreadPoolExecutor(thread_name_prefix='main') as executor:
        to_do: list[futures.Future] = []
        end_day = start_day + timedelta(days=7)

        while end_day <= date.today():
            future = executor.submit(
                load_week,
                config=config,
                start_day=start_day,
                end_day=end_day,
                started=started_counter,
                completed=completed_counter,
            )
            to_do.append(future)

            start_day = end_day
            end_day = start_day + timedelta(days=7)

        weeks = [future.result() for future in futures.as_completed(to_do)]
        return sorted(weeks)


def create_song_chart(
    process: Process,
    weeks: Iterator[spotistats.Week],
) -> Iterator[tuple[list[spotistats.Position], date, date]]:

    config = process.config

    two_wa = next(weeks)
    one_wa = next(weeks)
    this_wk = next(weeks)

    registered_ids: set[str] = set(process.songs.list())

    while True:
        all_song_ids: set[str] = {
            pos.id
            for pos in set(two_wa.songs)
            | set(one_wa.songs)
            | set(this_wk.songs)
        }

        # all songs who are registered (and could be merged into another one)
        # are checked and turned into the base id
        filtered_ids: set[str] = {
            process.songs.get(song_id).main_id
            for song_id in (all_song_ids & registered_ids)
            # and then all songs that arent registered are added into the set normally
        } | (all_song_ids - registered_ids)

        song_info: list[spotistats.Position] = []

        for song_id in filtered_ids:
            if song_id in registered_ids:
                song_ids = {song_id} | process.songs.get(song_id).ids
            else:
                song_ids = {song_id}

            two_wa_plays = sum(
                pos.plays for pos in two_wa.songs if pos.id in song_ids
            )
            one_wa_plays = sum(
                pos.plays for pos in one_wa.songs if pos.id in song_ids
            )
            this_wk_plays = sum(
                pos.plays for pos in this_wk.songs if pos.id in song_ids
            )

            song_info.append(
                spotistats.Position(
                    id=song_id,
                    points=(
                        two_wa_plays * config.second_last_weight
                        + one_wa_plays * config.last_weight
                        + this_wk_plays * config.current_weight
                    ),
                    plays=this_wk_plays,
                    place=0,
                )
            )

        for info in song_info:
            info.place = (
                len([i for i in song_info if i.points > info.points]) + 1
            )

        # song infos that didn't chart are filtered later on because we
        # need the entire thing for albums
        song_info.sort(key=lambda i: i.points, reverse=True)

        yield (song_info, this_wk.start_day, this_wk.end_day)

        # adjust week pointers
        two_wa = one_wa
        one_wa = this_wk

        try:
            this_wk = next(weeks)
        except StopIteration:
            return   # end process if no more weeks left


def points_charts(process: Process):

    song_rows: list[list[str]] = []
    week_counter = itertools.count(start=1)
    weeks = load_all_weeks(process.config)

    for positions, start_day, end_day in create_song_chart(
        process, iter(weeks)
    ):
        week_count = next(week_counter)
        print(
            f'collecting data for week ending {end_day.isoformat()} ({week_count})'
        )
        song_positions = [
            pos
            for pos in positions
            if pos.place <= process.config.chart_length
        ]
        insert_entries(process, song_positions, start_day, end_day)
        song_rows = update_song_sheet(
            song_rows, process, song_positions, start_day, end_day, week_count
        )

    return song_rows
