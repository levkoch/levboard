"""
levboard/main/main.py

The main (wow how original) script to run to collect the chart data
for the weeks. Make sure to run load.py first to collect the songs
and album declarations from the spreadsheet. Or add them one by one
here after getting prompted for it. :)
"""

import itertools
from concurrent import futures
from datetime import date, datetime, timedelta
from operator import itemgetter
from typing import Final, Iterable, Iterator, Optional, Union

from config import FIRST_DATE, LEVBOARD_SHEET
from model import (
    Album,
    AlbumEntry,
    Entry,
    Song,
    spotistats,
    SONG_CHART_LENGTH,
)
from model.spotistats import Week
from spreadsheet import Spreadsheet
from storage import SongUOW


def load_week(
    start_day: date,
    end_day: date,
    started: itertools.count,
    completed: itertools.count,
) -> Week:
    """
    Loads a singular week.

    Returns:
    *
    """
    print(
        f'-> [{next(started):03d}] collecting info for week ending {end_day.isoformat()}'
    )
    songs = spotistats.songs_week(start_day, end_day, adjusted=True)
    print(
        f'!! [{next(completed):03d}] finished collecting info for week ending {end_day.isoformat()}'
    )
    return Week(
        start_day=start_day,
        end_day=end_day,
        songs={pos.id: pos for pos in songs},
    )


def load_all_weeks(start_day: date) -> list[Week]:
    print('Loading all weeks')

    started_counter = itertools.count(start=1)
    completed_counter = itertools.count(start=1)

    with futures.ThreadPoolExecutor(thread_name_prefix='main') as executor:
        to_do: list[futures.Future[Week]] = []
        end_day = start_day + timedelta(days=7)

        while end_day <= date.today():
            future = executor.submit(
                load_week,
                start_day=start_day,
                end_day=end_day,
                started=started_counter,
                completed=completed_counter,
            )
            to_do.append(future)

            start_day = end_day
            end_day = start_day + timedelta(days=7)

    weeks: Iterator[Week] = iter(
        sorted(future.result() for future in futures.as_completed(to_do))
    )

    final = []
    for week in weeks:
        if len(week.songs) < SONG_CHART_LENGTH:
            # not enough songs streamed to be able
            # to create an actual chart (probably)
            while len(week.songs) < SONG_CHART_LENGTH:
                try:
                    week = week + next(weeks)
                except StopIteration:   # we ran out of weeks
                    break
        final.append(week)

    return final


def get_movement(
    current: date, last: date, charteable: Union[Song, Album]
) -> str:

    c_place = charteable.get_entry(current)
    p_place: Optional[Entry] = charteable.get_entry(last)

    weeks = charteable.weeks

    if c_place is None:   # shouldn't happen but always good to check
        raise ValueError('cant get the movement for a song not charting')

    if p_place is None:
        return 'NEW' if weeks == 1 else 'RE'

    movement = p_place.place - c_place.place
    if movement == 0:
        return '='
    if movement < 0:
        return '▼' + str(-1 * movement)
    return '▲' + str(movement)


def get_peak(listenable: Union[Song, Album]) -> str:
    """
    Transforms the peak of the listenable item into a nice
    string view with superscripts.
    """
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
    if listenable.peak > 10 or listenable.peakweeks == 1:
        return str(listenable.peak)
    pweeks = str(listenable.peakweeks)
    for (k, v) in num_to_exp.items():
        pweeks = pweeks.replace(k, v)
    return str(listenable.peak) + pweeks


def create_song_chart(
    uow: SongUOW,
    weeks: Iterator[Week],
) -> Iterator[tuple[list[dict], date, date]]:
    """
    Parses the weeks passed in into chart weeks.
    """

    two_wa = next(weeks)
    one_wa = next(weeks)
    this_wk = next(weeks)

    # every group of ids attached to a song, regarless of their parent variant
    id_groups: list[tuple[str]] = list(tuple(song.ids) for song in uow.songs)

    # every id we have stored somewhere in the system
    registered_ids: set[str] = set(itertools.chain.from_iterable(id_groups))

    while True:
        all_song_ids: set[str] = {
            pos.id
            for pos in set(two_wa.songs.values())
            | set(one_wa.songs.values())
            | set(this_wk.songs.values())
        }

        # all ids that got streamed but aren't registered
        rogue_ids: set[str] = all_song_ids - registered_ids

        # filtered positions to later process
        song_info: list[dict[str, Union[str, int]]] = []

        for song_id in rogue_ids:
            # process rogue ids first
            two_wa_plays = (
                0
                if song_id not in two_wa.songs
                else two_wa.songs[song_id].plays
            )
            one_wa_plays = (
                0
                if song_id not in one_wa.songs
                else one_wa.songs[song_id].plays
            )
            this_wk_plays = (
                0
                if song_id not in this_wk.songs
                else this_wk.songs[song_id].plays
            )

            song_info.append(
                {
                    'id': song_id,
                    'points': (
                        (two_wa_plays + one_wa_plays) * 2
                        + (10 * this_wk_plays)
                    ),
                    'plays': this_wk_plays,
                }
            )

        # if a song has the most streams out of all it's ids this week,
        # combine all of the other ids's points and plays with it's points
        # and plays as if they all went to that id.

        # this is a little bit unfortunate if one of the variants has multiple
        # ids attached to it. Ex.: if Black Mascara - Live. gains 4 streams while
        # Black Mascara. and Black Mascara (without period for some reason) both
        # gain 3 streams, the song will chart as Black Mascara - Live., even
        # though the studio version of the song got 6 plays.

        for id_group in id_groups:
            # skip everything that didn't get listened to at all
            if len(set(id_group) & all_song_ids) == 0:
                continue

            id_plays: Iterable[tuple[str, int]] = (
                (
                    song_id,
                    0
                    if song_id not in this_wk.songs
                    else this_wk.songs[song_id].plays,
                )
                for song_id in id_group
            )
            # the most streamed id out of the group.
            main_id = sorted(id_plays, key=itemgetter(1), reverse=True,)[
                0
            ][0]

            two_wa_plays = sum(
                two_wa.songs[song_id].plays
                for song_id in id_group
                if song_id in two_wa.songs
            )
            one_wa_plays = sum(
                one_wa.songs[song_id].plays
                for song_id in id_group
                if song_id in one_wa.songs
            )
            this_wk_plays = sum(
                this_wk.songs[song_id].plays
                for song_id in id_group
                if song_id in this_wk.songs
            )

            song_info.append(
                {
                    'id': main_id,
                    'points': (
                        (two_wa_plays + one_wa_plays) * 2
                        + (10 * this_wk_plays)
                    ),
                    'plays': this_wk_plays,
                }
            )

        # song infos that didn't chart are filtered later on because we
        # need the entire thing for albums
        song_info.sort(key=lambda i: i['points'], reverse=True)

        yield (song_info, this_wk.start_day, this_wk.end_day)

        # adjust week pointers
        two_wa = one_wa
        one_wa = this_wk

        try:
            this_wk = next(weeks)
        except StopIteration:
            return   # end process if no more weeks left


def ask_new_song(uow: SongUOW, song_id: str) -> Song:
    tester = Song(song_id)
    # defaults to official name if no name specified
    print(f'\nSong {tester.title} ({song_id}) not found.')
    print(f'Find the link here -> https://stats.fm/track/{song_id}')
    name = input('What should the song be called in the database? ').strip()

    if name == '':
        return tester
    if name == 'skip':
        return
    if name.lower() == 'merge':
        merge: str = input('Name of the song to merge with: ')
        merge_into = uow.songs.get_by_name(merge)
        if merge_into is None:
            raise ValueError(
                f'a song with the id {merge} does '
                'not exist in the local database'
            )

        merge_into.add_alt(song_id)
        print(f'Sucessfully merged {tester.title} into {merge_into.title}')
        return merge_into

    return Song(song_id, name)


def clear_entries(uow: SongUOW) -> None:
    print('Clearing previous entries.')
    with uow:
        for song_id in uow.songs.list():
            song: Song = uow.songs.get(song_id)
            song._entries.clear()
        for album_name in uow.albums.list():
            album: Album = uow.albums.get(album_name)
            album._entries.clear()
        uow.commit()


def insert_entries(
    uow: SongUOW,
    positions: list[dict],
    start_date: date,
    end_date: date,
    chart_cutoff: int,
) -> list[dict]:
    """
    filters out and inserts the eligible entries from the list of positions given.
    * uow (`SongUOW`): the UOW to stick the entries into.
    * positions (`list[dict[str, ...]]`): a SORTED list of dictionaries by "points"
      with the following schema:
        ```{
            "plays": 37,
            "points": 460,
            "id": "325382"
        }```
    * start_date (`datetime.date`): the starting date of the week
    * end_date (`datetime.date`): the ending date of the week
    * chart_cutoff (`int`): the number of chart positions avaliable
    """

    # POSITIONS ARE NOT FILTERED YET

    if not positions:
        return   # if positions is empty

    def process_song(song_id: str, plays: int, place: int, points: int):
        song: Optional[Song] = uow.songs.get(song_id)
        if not song:
            song = ask_new_song(uow, song_id)
            uow.songs.add(song)
        entry = Entry(
            end=end_date,
            start=start_date,
            plays=plays,
            place=place,
            points=points,
            variant=song_id,
        )
        song.add_entry(entry)

    first_pos = positions[0]
    process_song(first_pos['id'], first_pos['plays'], 1, first_pos['points'])

    prev_points = first_pos['points']
    prev_place = 1
    ties = 1
    filtered = [first_pos | {'place': prev_place}]

    for pos in positions[1:]:
        if pos['points'] == prev_points:
            ties += 1
            process_song(pos['id'], pos['plays'], prev_place, pos['points'])
            filtered.append(pos | {'place': prev_place})
        else:
            place = prev_place + ties
            if place > chart_cutoff:
                break
            process_song(pos['id'], pos['plays'], place, pos['points'])
            filtered.append(pos | {'place': place})
            prev_place = place
            prev_points = pos['points']
            ties = 1

    uow.commit()
    return filtered


def show_chart(
    uow: SongUOW,
    positions: list[dict],
    start: date,
    end: date,
    week_count: int,
):
    print(f'\n({week_count}) Week of {start.isoformat()} to {end.isoformat()}')

    print(
        f' MV | {"Title":<45} | {"Artists":<45} | TW | LW | OC | PTS | PLS | PK'
    )
    for pos in positions:
        with uow:
            song: Song = uow.songs.get(pos['id'])
        prev = song.get_entry(start)
        print(
            f'{get_movement(end, start, song):>3} | {song.active.title:<45} | '
            f"{', '.join(song.active.artists):<45} | {pos['place']:<2} | "
            f"{(prev.place if prev else '-'):<2} | {song.weeks:<2} | "
            f"{pos['points']:<3} | {pos['plays']:<3} | {get_peak(song):<3}"
        )
    print('')


def update_song_sheet(
    rows: list[list],
    uow: SongUOW,
    positions: list[dict],
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
            '',
        ],
        [
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
            '(ID)',
        ],
    ]

    for pos in positions:
        song: Song = uow.songs.get(pos['id'])
        prev: Optional[Entry] = song.get_entry(start_date)
        movement: str = get_movement(end_date, start_date, song)
        peak: str = get_peak(song)

        new_rows.append(
            [
                "'" + movement,
                "'" + song.active.title
                if song.title[0].isnumeric()
                else song.active.title,
                ', '.join(song.active.artists),
                pos['place'],
                prev.place if prev is not None else '-',
                song.weeks,
                pos['points'],
                pos['plays'],
                peak,
                week_count,
                song.sheet_id,
            ]
        )

    new_rows.extend([['']] + rows)
    return new_rows


def get_album_plays(uow: SongUOW, positions: list[dict]) -> dict[Album, int]:
    album_plays = {}

    for album in uow.albums:
        plays = 0
        for variant_id, song in album:
            plays += next(
                (
                    pos['plays']
                    for pos in positions
                    if pos['id'] in song.get_variant(variant_id).ids
                ),
                0,
            )

        album_plays[album] = plays

    return album_plays


def create_album_chart(
    uow: SongUOW,
    positions: list[dict],
    start_day: date,
    end_day: date,
    week_count: int,
    album_rows: list[list],
) -> list[list]:

    ALBUMS_CHART_LENGTH: Final[int] = 20

    album_plays: dict[Album, int] = get_album_plays(uow, positions)

    units: list[tuple[Album, int]] = [
        (album, u)
        for album in uow.albums
        if (u := album.get_points(end_day) + (2 * album_plays[album])) > 0
    ]

    units.sort(key=itemgetter(1), reverse=True)

    if len(units) > 20:
        units = [i for i in units if i[1] >= units[19][1]]

    actual_end = end_day - timedelta(days=1)
    new_rows = [
        [
            f'{start_day.isoformat()} to {actual_end.isoformat()}',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            week_count,
        ],
        [
            'MV',
            'Title',
            'Artists',
            'TW',
            'LW',
            'OC',
            'PK',
            'UTS',
            'PLS',
            'PTS',
            '(WK)',
        ],
    ]

    print(f' | A')

    def process_album(album: Album, album_units: int, place: int) -> list:
        nonlocal start_day, end_day, week_count
        entry = AlbumEntry(
            start=start_day, end=end_day, units=album_units, place=place
        )
        album.add_entry(entry)

        prev: Optional[AlbumEntry] = album.get_entry(start_day)
        movement: str = get_movement(end_day, start_day, album)
        peak: str = get_peak(album)
        plays: int = album_plays[album]
        points: int = album.get_points(end_day)

        return [
            "'" + movement,
            "'" + album.title if album.title[0].isnumeric() else album.title,
            album.str_artists,
            place,
            prev.place if prev else '-',
            album.weeks,
            peak,
            album_units,
            plays,
            points,
            week_count,
        ]

    f_album, f_units = units[0]
    new_rows.append(process_album(f_album, f_units, 1))

    prev_units = f_units
    prev_place = 1
    ties = 1

    for (album, album_units) in units[1:]:
        if album_units == prev_units:
            ties += 1
            new_rows.append(process_album(album, album_units, prev_place))
        else:
            place = prev_place + ties
            if place > ALBUMS_CHART_LENGTH:
                break
            new_rows.append(process_album(album, album_units, place))
            prev_place = place
            prev_units = album_units
            ties = 1

    return new_rows + [['']] + album_rows


def create_personal_charts():
    uow = SongUOW()

    clear_entries(uow)
    start_time = datetime.now()

    week_counter = itertools.count(start=1)
    song_rows: list[list] = []
    album_rows: list[list] = []
    weeks = load_all_weeks(FIRST_DATE)
    loading_time = datetime.now() - start_time

    for song_positions, start_day, end_day in create_song_chart(
        uow, iter(weeks)
    ):
        week_count = next(week_counter)
        filtered_songs = insert_entries(
            uow, song_positions, start_day, end_day, SONG_CHART_LENGTH
        )
        print(f'<> [{week_count:03d}] ({end_day.isoformat()}) S', end='')
        # show_chart(uow, song_positions, start_day, end_day, week_count)
        song_rows = update_song_sheet(
            song_rows, uow, filtered_songs, start_day, end_day, week_count
        )

        album_rows = create_album_chart(
            uow, song_positions, start_day, end_day, week_count, album_rows
        )

    uow.commit()

    crunching_time = (datetime.now() - start_time) - loading_time

    start_song_rows = [
        [
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
            '(ID)',
        ],
        [''],
    ]

    start_album_rows = [
        [
            'MV',
            'Title',
            'Artists',
            'TW',
            'LW',
            'OC',
            'PK',
            'UTS',
            'PLS',
            'PTS',
            '(WK)',
        ],
        [''],
    ]

    song_rows = start_song_rows + song_rows
    album_rows = start_album_rows + album_rows

    sheet = Spreadsheet(LEVBOARD_SHEET)

    print('')
    print(f'Sending {len(song_rows)} song rows to the spreadsheet.')

    song_range = f'BOT_SONGS!A1:K{len(song_rows) + 1}'
    sheet.delete_range(song_range)
    sheet.update_range(song_range, song_rows)

    print(f'Sending {len(album_rows)} album rows to the spreadsheet.')

    album_range = f'BOT_ALBUMS!A1:K{len(album_rows) + 1}'
    sheet.delete_range(album_range)
    sheet.update_range(album_range, album_rows)

    # use delete range first for the above two processes, because the way
    # that sheets works, it doens't overwrite when an empty cell is given
    # to overwrite with for some reason, so we clear it first and then
    # add the new data.

    finished = datetime.now()
    sending_time = (finished - start_time) - (loading_time + crunching_time)
    total_time = finished - start_time

    print('')
    print(
        f'Completed in     {total_time} '
        f'({total_time / week_count} per week)'
    )
    print(
        f'Loaded weeks in  {loading_time} '
        f'({loading_time / week_count} per week)'
    )
    print(
        f'Crunched data in {crunching_time} '
        f'({crunching_time / week_count} per week)'
    )
    print(f'Updated sheet in {sending_time}')


if __name__ == '__main__':
    create_personal_charts()
