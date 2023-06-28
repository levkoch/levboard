"""
main/plays.py

A script to update the plays in the spreadsheet and the ones
stored in the local database.

Functions:
* `update_spreadsheet_plays()`: Update the song plays in the
    spreadsheet.
* `update_local_plays()`: Update the song plays stored in the
    local storage.
"""

import datetime
import itertools
from concurrent import futures
from operator import itemgetter
from typing import Callable

from config import LEVBOARD_SHEET, FIRST_DATE, MAX_ADJUSTED
from model import Song, spotistats
from spreadsheet import Spreadsheet
from storage import SongUOW


def _create_song(song_id: str, song_name: str) -> tuple[Song, int]:
    song_id = song_id.replace(',', ', ').replace('  ', ' ')
    if ', ' in song_id:
        song = Song(song_id.split(', ')[0], song_name)
        for alt in song_id.split(', ')[1:]:
            song.add_alt(alt)

    else:
        song = Song(song_id, song_name)

    return _update_song_plays(song)


def _update_song_plays(song: Song) -> tuple[Song, int]:
    song.update_plays(adjusted=True)
    return (song, song._plays)


def create_song_play_updater(
    uow: SongUOW,
) -> Callable[[str, str], tuple[Song, int]]:
    sheet = Spreadsheet(LEVBOARD_SHEET)
    songs_flagged_for_filtering = set()
    for row in sheet.get_range('BOT_SONGS!B:H').get('values'):
        if (not row) or (row[0] == 'Title'):
            continue
        if int(row[6]) >= MAX_ADJUSTED:
            songs_flagged_for_filtering.add(uow.songs.get_by_name(row[0]))

    print(f'{len(songs_flagged_for_filtering)} songs flagged for filtering')
    saved_plays = spotistats.songs_week(
        after=datetime.date(2000, 1, 1), before=datetime.date(3000, 1, 1)
    )
    # all time saved plays. this unfortunately only returns the top
    # 1 thousands songs of all time so some lesser played tracks will
    # have to be retrieved manually

    saved_plays_ids = [pos.id for pos in saved_plays]
    saved_plays_threshold = min(pos.plays for pos in saved_plays)

    print(f'Plays threshold is {saved_plays_threshold} plays.')

    def inner_update_song_plays(
        song_id: str, song_name: str
    ) -> tuple[Song, int]:
        song_id = song_id.replace(',', ', ').replace('  ', ' ')
        if ', ' in song_id:
            song = Song(song_id.split(', ')[0], song_name)
            for alt in song_id.split(', ')[1:]:
                song.add_alt(alt)
        else:
            song = Song(song_id, song_name)

        if song in songs_flagged_for_filtering:
            song.update_plays(adjusted=True)
            return (song, song._plays)

        plays = 0
        for track_id in song.ids:
            if track_id in saved_plays_ids:
                plays += next(
                    pos.plays for pos in saved_plays if pos.id == track_id
                )
            else:
                plays += spotistats.song_plays(
                    track_id, adjusted=(saved_plays_threshold > MAX_ADJUSTED)
                )
                # adjust plays if this id could have somehow been adjusted
                # and also not in the top 1 thousand songs of all time
                # otherwise if all other song ids have less streams than the
                # adjusted limit, save time by not having to adjust

        return (song, plays)

    return inner_update_song_plays


def update_spreadsheet_plays(verbose=False):
    """
    Updates the song plays for the songs in the spreadsheet.

    Arguments:
    * verbose (`bool`): Whether to produce console output or not.
        Defaults to `False`.
    """

    sheet = Spreadsheet(LEVBOARD_SHEET)

    # check if first element isn't blank so that it gets rid of empty rows.
    songs: list[list] = [
        i for i in sheet.get_range('Song Info!A2:D').get('values') if i[0]
    ]

    song_amt = len(songs)
    if verbose:
        print(f'{song_amt} items found.')

    final_songs: list[list] = []

    create_song = create_song_play_updater(uow)

    with futures.ThreadPoolExecutor() as executor:
        to_do: list[futures.Future] = []

        for sheet_song in songs:
            song_name, song_id, _, _ = sheet_song
            future = executor.submit(create_song, song_id, song_name)
            to_do.append(future)

        for count, future in enumerate(futures.as_completed(to_do), 1):
            song: Song
            plays: int
            song, plays = future.result()

            final_songs.append(
                [
                    "'" + song.name
                    if any(letter.isnumeric() for letter in song.name)
                    else song.name,
                    ', '.join(song.ids),
                    ', '.join(song.artists),
                    plays,
                ]
            )
            if verbose:
                print(
                    f'{count:>4} ({(count / song_amt * 100.0):.02f}%) '
                    f'updated {song} -> {plays} plays'
                )

    sheet.update_range(f'Song Info!A2:D{len(final_songs) + 1}', final_songs)

    if verbose:
        print(f'Updated {song_amt} spreadsheet song plays.')


def update_local_plays(uow: SongUOW, verbose: bool = False) -> None:
    """
    Updates the song plays for the songs in the local storage.

    Arguments:
    * uow (`SongUOW`): Where to read songs from.
    * verbose (`bool`): Whether to produce console output or not.
        Defaults to `False`.
    """

    song_amt = len(list(uow.songs))

    if verbose:
        print(f'{song_amt} items found.')

    with futures.ThreadPoolExecutor() as executor:
        with uow:
            to_do: list[futures.Future] = []
            for song in uow.songs:
                future = executor.submit(_update_song_plays, song)
                to_do.append(future)

            for count, future in enumerate(futures.as_completed(to_do), 1):
                song, plays = future.result()
                if verbose:
                    print(
                        f'{count:>4} ({(count / song_amt * 100.0):.02f}%) '
                        f'updated {song} -> {plays} plays'
                    )

            uow.commit()

    if verbose:
        print(f'Updated {song_amt} local song plays.')


def load_year_end_songs(uow: SongUOW, verbose: bool = False):
    """
    Updates the spreadsheet with the correct year-end songs.

    MUST be ran AFTER update_local_plays so that all songs in memory have all
    of their plays attached to them so that this takes 15 seconds to run and
    not 40 minutes as the program sequentially gets play data for 1,600+ songs.
    """

    sheet = Spreadsheet(LEVBOARD_SHEET)
    song_rows: list[list] = []

    current_year = datetime.date.today().year
    while current_year > FIRST_DATE.year - 1:
        if verbose:
            print(f'Collecting top songs of {current_year}')
        year_start = datetime.date(current_year, 1, 1)
        year_end = datetime.date(current_year + 1, 1, 1)
        year = (year_start, year_end)

        song_rows.extend(
            [
                [
                    f'{current_year} Year-End Songs',
                ],
                ['POS', 'Title', 'Artists', 'WKS', 'UTS', 'PLS', 'PK', 'PKW'],
            ]
        )

        eligible_songs = [
            (song, song.period_units(*year))
            for song in uow.songs
            if song.period_weeks(*year)
        ]

        eligible_songs.sort(key=itemgetter(1), reverse=True)
        eligible_songs = eligible_songs[:100]

        for song, units in eligible_songs:
            place = len([s for (s, u) in eligible_songs if u > units]) + 1
            peak = min(
                entry.place
                for entry in song.entries
                if entry.start >= year_start and entry.end <= year_end
            )
            peak_weeks = len(
                [
                    entry
                    for entry in song.entries
                    if entry.start >= year_start
                    and entry.end <= year_end
                    and entry.place == peak
                ]
            )
            info = [
                place,
                song.name,
                ', '.join(song.artists),
                song.period_weeks(*year),
                song.period_units(*year),
                song.period_plays(*year),
                peak,
                peak_weeks if peak_weeks > 1 else '—',
            ]
            song_rows.append(info)

        song_rows.append([''])
        current_year -= 1

    sheet.delete_range('Year-End!A:H')
    sheet.append_range('Year-End!A1:H', song_rows)


if __name__ == '__main__':
    uow = SongUOW()
    # update_local_plays(uow, verbose=True)

    print('')
    update_spreadsheet_plays(verbose=True)
    # load_year_end_songs(uow, verbose=True)
