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

from collections import defaultdict
import datetime

from concurrent import futures
from operator import itemgetter
from typing import Any, Callable, Union

from config import LEVBOARD_SHEET, FIRST_DATE, MAX_ADJUSTED
from model.spotistats import Week
from model import Song, spotistats
from spreadsheet import Spreadsheet
from storage import SongUOW, SongRepository, AlbumRepository


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


PLAY_UPDATER = Callable[..., tuple[Song, int]]


def create_song_play_updater(uow: SongUOW, sheet_id: str) -> PLAY_UPDATER:
    sheet = Spreadsheet(sheet_id)
    songs_flagged_for_filtering: set[Song] = set()
    for row in sheet.get_range('BOT_SONGS!B:H').get('values'):
        if (not row) or (row[0] == 'Title'):
            continue
        if int(row[6]) >= MAX_ADJUSTED:
            songs_flagged_for_filtering.add(uow.songs.get_by_name(row[0]))

    # this now collects all song data, and makes multiple calls if need be
    saved_plays = spotistats.songs_week(
        after=datetime.date(2000, 1, 1), before=datetime.date(3000, 1, 1)
    )

    saved_plays_ids: set[str] = {pos.id for pos in saved_plays}
    saved_plays_mapping: dict[str, int] = {
        pos.id: pos.plays for pos in saved_plays
    }
    saved_plays_threshold: int = min(pos.plays for pos in saved_plays)
    print(
        f'{len(songs_flagged_for_filtering)} songs flagged for filtering'
        + f' | Plays threshold is {saved_plays_threshold} plays.'
    )

    def inner_update_song_plays(
        song_id: str, song_name: str
    ) -> tuple[Song, int]:
        song_id = song_id.replace(',', ', ').replace('  ', ' ')
        if ', ' in song_id:   # has multiple ids
            first_id = song_id.split(', ')[0]
            all_ids = set(song_id.split(', '))
            cached_song = uow.songs.get(first_id)

            if cached_song is None or cached_song.ids != all_ids:
                song = Song(song_id.split(', ')[0], song_name)
                for alt in song_id.split(', ')[1:]:
                    song.add_alt(alt)
                print(f'unable to find {song} in cache.')
            else:
                song = cached_song
        else:
            cached_song = uow.songs.get(song_id)
            if cached_song is None:
                song = Song(song_id, song_name)
                print(f'unable to find {song} in cache.')
            else:
                song = cached_song

        if song in songs_flagged_for_filtering:
            print(f'{song} flagged for filtering')
            song.update_plays(adjusted=True)
            return (song, song._plays)

        plays = 0
        for track_id in song.ids:
            if track_id in saved_plays_ids:
                plays += saved_plays_mapping[track_id]
            else:
                print(f'### {song} {track_id}: loading information')
                plays += spotistats.song_plays(
                    track_id, adjusted=(saved_plays_threshold > MAX_ADJUSTED)
                )
                # adjust plays if this id could have somehow been adjusted
        return (song, plays)

    return inner_update_song_plays


def create_song_play_updater_from_weeks(
    week: Week, uow: SongUOW
) -> PLAY_UPDATER:
    """
    Creates a song play updater function based on data collected from all
    the weeks created by the main script comped together.
    """

    play_mapping = defaultdict(int)
    play_mapping.update({pos.id: pos.plays for pos in week.songs})

    print(f'{len(play_mapping)} songs loaded with streams.')

    def inner_update_song_plays(
        song_id: str, song_name: str
    ) -> tuple[Song, int]:
        song_id = song_id.replace(',', ', ').replace('  ', ' ')
        if ', ' in song_id:   # has multiple ids
            first_id = song_id.split(', ')[0]
            all_ids = set(song_id.split(', '))
            cached_song = uow.songs.get(first_id)

            if cached_song is None or cached_song.ids != all_ids:
                song = Song(song_id.split(', ')[0], song_name)
                for alt in song_id.split(', ')[1:]:
                    song.add_alt(alt)
                print(f'unable to find {song} in cache.')
            else:
                song = cached_song
        else:
            cached_song = uow.songs.get(song_id)
            if cached_song is None:
                song = Song(song_id, song_name)
                print(f'unable to find {song} in cache.')
            else:
                song = cached_song

        plays = sum(play_mapping.get(track_id) for track_id in song.ids)
        return (song, plays)

    return inner_update_song_plays


def update_spreadsheet_plays(
    play_updater: PLAY_UPDATER,
    sheet_id: str,
    verbose=False,
):
    """
    Updates the song plays for the songs in the spreadsheet.

    Arguments:
    * verbose (`bool`): Whether to produce console output or not.
        Defaults to `False`.
    """

    sheet = Spreadsheet(sheet_id)

    # check if first element isn't blank so that it gets rid of empty rows.
    songs: list[list] = [
        i for i in sheet.get_range('Song Info!A2:D').get('values') if i[0]
    ]

    song_amt = len(songs)
    if verbose:
        print(f'{song_amt} items found.')

    final_songs: list[list] = []

    with futures.ThreadPoolExecutor() as executor:
        to_do: list[futures.Future] = []

        for sheet_song in songs:
            song_name, song_id, _, _ = sheet_song
            future = executor.submit(play_updater, song_id, song_name)
            to_do.append(future)

        for count, future in enumerate(futures.as_completed(to_do), 1):
            song: Song
            plays: int
            song, plays = future.result()

            final_songs.append(
                [
                    "'" + song.title
                    if any(letter.isnumeric() for letter in song.title)
                    else song.title,
                    ', '.join(song.ids),
                    ', '.join(song.artists),
                    plays,
                ]
            )
            if verbose:
                print(
                    f'{count:>4} ({(count / song_amt * 100.0):.02f}%) '
                    f'| {spotistats.total_requests:>3} req | '
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


def year_end_collection_creater(sheet_id: str, range_name: str, quantity: int):
    sheet = Spreadsheet(sheet_id)

    def inner(
        collection: Union[SongRepository, AlbumRepository], verbose=False
    ):
        nonlocal sheet, range_name, quantity
        item_rows: list[list] = []
        kind = type(collection.get(collection.list()[0])).__name__

        current_year = datetime.date.today().year
        while current_year > FIRST_DATE.year - 1:
            if verbose:
                print(f'Collecting top {kind}s of {current_year}')
            year_start = datetime.date(current_year, 1, 1)
            year_end = datetime.date(current_year + 1, 1, 1)
            year = (year_start, year_end)

            item_rows.extend(
                [
                    [
                        f'{current_year} Year-End {kind}s',
                    ],
                    [
                        'POS',
                        'Title',
                        'Artists',
                        'WKS',
                        'UTS',
                        'PLS',
                        'PK',
                        'PKW',
                    ],
                ]
            )

            eligible_items = [
                (item, item.period_units(*year))
                for item in collection
                if item.period_weeks(*year)
            ]

            eligible_items.sort(key=itemgetter(1), reverse=True)
            eligible_items = eligible_items[:quantity]

            for item, units in eligible_items:
                place = len([s for (s, u) in eligible_items if u > units]) + 1
                peak = min(
                    entry.place
                    for entry in item.entries
                    if entry.start >= year_start and entry.end <= year_end
                )
                peak_weeks = len(
                    [
                        entry
                        for entry in item.entries
                        if entry.start >= year_start
                        and entry.end <= year_end
                        and entry.place == peak
                    ]
                )
                info = [
                    place,
                    "'" + item.title if item.title[0].isnumeric() else item.title,
                    ', '.join(item.artists),
                    item.period_weeks(*year),
                    item.period_units(*year),
                    item.period_plays(*year),
                    peak,
                    peak_weeks if peak_weeks > 1 else '—',
                    current_year
                    # for filtering reasons but will be hidden in sheet
                ]
                item_rows.append(info)

            item_rows.append([''])
            current_year -= 1

        sheet.delete_range(range_name)
        sheet.append_range(range_name, item_rows)

    return inner


load_year_end_songs = year_end_collection_creater(
    LEVBOARD_SHEET, 'Year-End!A1:I', 100
)
load_year_end_albums = year_end_collection_creater(
    LEVBOARD_SHEET, "'Year-End Albums'!A1:I", 40
)

def month_end_collection_creater(sheet_id: str, range_name: str, quantity: int):
    sheet = Spreadsheet(sheet_id)

    def inner(
        collection: Union[SongRepository, AlbumRepository], verbose=False
    ):
        nonlocal sheet, range_name, quantity
        item_rows: list[list] = []
        kind = type(collection.get(collection.list()[0])).__name__

        current_year = datetime.date.today().year
        current_month = datetime.date.today().month

        while ((current_year > FIRST_DATE.year) 
            or (current_month > FIRST_DATE.month - 1)):
            if verbose:
                print(
                    f'Collecting top {kind}s of {current_month}/{current_year}')
            
            year_start = datetime.date(current_year, current_month, 1)
            next_month = (1 if current_month == 12 else current_month + 1)
            next_year = (
                current_year + 1 if current_month == 12 else current_year)
            year_end = datetime.date(next_year, next_month, 1)
            year = (year_start, year_end)

            item_rows.extend(
                [
                    [
                        f'{current_month}/{current_year} Month-End {kind}s',
                    ],
                    [
                        'POS',
                        'Title',
                        'Artists',
                        'WKS',
                        'UTS',
                        'PLS',
                        'PK',
                        'PKW',
                    ],
                ]
            )

            eligible_items = [
                (item, item.period_units(*year))
                for item in collection
                if item.period_weeks(*year)
            ]

            eligible_items.sort(key=itemgetter(1), reverse=True)
            eligible_items = eligible_items[:quantity]

            for item, units in eligible_items:
                place = len([s for (s, u) in eligible_items if u > units]) + 1
                peak = min(
                    entry.place
                    for entry in item.entries
                    if entry.start >= year_start and entry.end <= year_end
                )
                peak_weeks = len(
                    [
                        entry
                        for entry in item.entries
                        if entry.start >= year_start
                        and entry.end <= year_end
                        and entry.place == peak
                    ]
                )
                info = [
                    place,
                    "'" + item.title if item.title[0].isnumeric() else item.title,
                    ', '.join(item.artists),
                    item.period_weeks(*year),
                    item.period_units(*year),
                    item.period_plays(*year),
                    peak,
                    peak_weeks if peak_weeks > 1 else '—',
                    f'{current_month}/{current_year}'
                    # for filtering reasons but will be hidden in sheet
                ]
                item_rows.append(info)

            item_rows.append([''])

            prev_month = (12 if current_month == 1 else current_month - 1)
            prev_year = (current_year - 1 
                if current_month == 1 else current_year)
            current_month = prev_month
            current_year = prev_year

        sheet.delete_range(range_name)
        sheet.append_range(range_name, item_rows)

    return inner


load_month_end_songs = month_end_collection_creater(
    LEVBOARD_SHEET, 'Month-End!A1:I', 40
)
load_month_end_albums = month_end_collection_creater(
    LEVBOARD_SHEET, "'Month-End Albums'!A1:I", 20
)


if __name__ == '__main__':
    uow = SongUOW()
    
    update_local_plays(uow, verbose=True)
    load_year_end_songs(uow.songs, verbose=True)
    load_year_end_albums(uow.albums, verbose=True)
    load_month_end_songs(uow.songs, verbose=True)
    load_month_end_albums(uow.albums, verbose=True)

    """
    update_spreadsheet_plays(
        create_song_play_updater(uow, LEVBOARD_SHEET),
        LEVBOARD_SHEET,
        verbose=True,
    )"""
