import itertools
import functools
import operator

from datetime import date, timedelta, datetime
from concurrent import futures
from typing import Optional, Union, Iterator
from operator import itemgetter


from model import spotistats, Song, Entry, Album, AlbumEntry, SONG_CHART_LENGTH
from model.spotistats import Week
from plays import create_song_play_updater_from_weeks, update_spreadsheet_plays
from storage import SongUOW
from config import GROUPBOARD_SHEET, GROUP_DATE
from spreadsheet import Spreadsheet

MEMBERS: set[str] = {
    'lev',  # lev levsnasty
    'edmo',  # ed winagn
    'layomi',  # layomi _layomi_
    'joejoe',  # joe joeislevitating
    'thedoll',  # khia khiakardashian
    'akonsleeze',  # akon onickaspet
}


def load_week(
    start_day: date,
    end_day: date,
    started: itertools.count,
    completed: itertools.count,
) -> Week:
    print(
        f'-> [{next(started):03d}] collecting info for week ending {end_day.isoformat()}'
    )

    def getter(user):
        songs = spotistats.songs_week(
            start_day, end_day, user=user, adjusted=True
        )
        return Week(start_day=start_day, end_day=end_day, songs=songs)

    with futures.ThreadPoolExecutor(
        thread_name_prefix=f'{end_day.isoformat()}wk'
    ) as executor:
        weeks = list(executor.map(getter, MEMBERS))

    print(
        f'!! [{next(completed):03d}] finished collecting info for week ending {end_day.isoformat()}'
    )

    return functools.reduce(operator.add, weeks)


def load_all_weeks(start_day: date) -> list[Week]:
    print('Loading all weeks')

    started_counter = itertools.count(start=1)
    completed_counter = itertools.count(start=1)

    with futures.ThreadPoolExecutor(thread_name_prefix='main') as executor:
        to_do: list[futures.Future] = []
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

        weeks = [future.result() for future in futures.as_completed(to_do)]
        return sorted(weeks)


def get_movement(current: date, last: date, song: Song) -> str:
    c_place: Optional[Entry] = song.get_entry(current)
    if c_place is None:   # shouldn't happen but always good to check
        raise ValueError('cant get the movement for a song not charting')
    p_place: Optional[Entry] = song.get_entry(last)
    weeks = song.weeks

    if p_place is None:
        return 'NEW' if weeks == 1 else 'RE'

    movement = p_place.place - c_place.place
    if movement == 0:
        return '='
    if movement < 0:
        return '▼' + str(-1 * movement)
    return '▲' + str(movement)


def get_peak(listenable: Union[Song, Album]) -> str:
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

    two_wa = next(weeks)
    one_wa = next(weeks)
    this_wk = next(weeks)

    registered_ids: set[str] = set(uow.songs.list())

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
            uow.songs.get(song_id).main_id
            for song_id in (all_song_ids & registered_ids)
            # and then all songs that arent registered are added into the set normally
        } | (all_song_ids - registered_ids)

        song_info: list[dict] = []

        for song_id in filtered_ids:
            if song_id in registered_ids:
                song_ids = {song_id}.union(uow.songs.get(song_id).ids)
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
                {
                    'id': song_id,
                    'points': (
                        (two_wa_plays + one_wa_plays) * 2
                        + (10 * this_wk_plays)
                    ),
                    'plays': this_wk_plays,
                }
            )

        for info in song_info:
            info['place'] = (
                len([i for i in song_info if i['points'] > info['points']]) + 1
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
            album.entries.clear()
        uow.commit()


def insert_entries(uow: SongUOW, positions: list[dict], start_date, end_date):
    with uow:
        for position in positions:
            song: Optional[Song] = uow.songs.get(position['id'])
            if not song:
                song = ask_new_song(uow, position['id'])
                uow.songs.add(song)
            entry = Entry(
                end=end_date,
                start=start_date,
                plays=position['plays'],
                place=position['place'],
                points=position['points'],
            )
            song.add_entry(entry)
        uow.commit()


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
            f'{get_movement(end, start, song):>3} | {song.title:<45} | '
            f"{', '.join(song.artists):<45} | {pos['place']:<2} | "
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

    new_rows = []

    new_rows.append(
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
        ]
    )
    new_rows.append(
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
        ]
    )

    for pos in positions:
        with uow:
            song: Song = uow.songs.get(pos['id'])
        prev: Optional[Entry] = song.get_entry(start_date)
        movement: str = get_movement(end_date, start_date, song)
        peak: str = get_peak(song)

        new_rows.append(
            [
                "'" + movement,
                "'" + song.title if song.title[0].isnumeric() else song.title,
                ', '.join(song.artists),
                pos['place'],
                prev.place if prev is not None else '-',
                song.weeks,
                pos['points'],
                pos['plays'],
                peak,
                week_count,
            ]
        )

    new_rows.extend([['']] + rows)
    return new_rows


def get_album_plays(uow: SongUOW, positions: list[dict]) -> dict[Album, int]:
    album_plays = {}

    for album in uow.albums:
        plays = 0
        for song in album:
            plays += next(
                (
                    pos['plays']
                    for pos in positions
                    if pos['id'] == song.main_id
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

    album_plays: dict[Album, int] = get_album_plays(uow, positions)

    units: list[tuple[Album, int]] = [
        (album, album.get_points(end_day) + (2 * album_plays[album]))
        for album in uow.albums
    ]

    units.sort(key=itemgetter(1), reverse=True)

    if len(units) > 40:
        units = [i for i in units if i[1] >= units[39][1]]

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

    print(f'({week_count}) Albums chart for week of {end_day.isoformat()}.')
    print('')
    print(
        f' MV | {"Title":<45} | {"Artists":<45} | TW | LW | OC | PK  | UTS | PLS | PTS'
    )

    for (album, album_units) in units:
        position = len([i for i in units if i[1] > album_units]) + 1
        entry = AlbumEntry(
            start=start_day, end=end_day, units=album_units, place=position
        )
        album.add_entry(entry)

        prev = album.get_entry(start_day)
        movement = get_movement(end_day, start_day, album)
        peak = get_peak(album)
        plays = album_plays[album]
        points = album.get_points(end_day)

        print(
            f'{movement:>3} | {album.title:<45} | {album.str_artists:<45}'
            f" | {position:<2} | {(prev.place if prev else '-'):<2} | {album.weeks:<2}"
            f' | {peak:<3} | {album_units:<3} | {plays:<3} | {points:<3}'
        )

        new_rows.append(
            [
                "'" + movement,
                "'" + album.title
                if album.title[0].isnumeric()
                else album.title,
                album.str_artists,
                position,
                prev.place if prev else '-',
                album.weeks,
                peak,
                album_units,
                plays,
                points,
                week_count,
            ]
        )

    new_rows.extend([['']] + album_rows)
    return new_rows


def create_group_charts():
    uow = SongUOW(
        song_file='../data/groupsongs.json',
        album_file='../data/groupalbums.json',
    )
    clear_entries(uow)
    start_time = datetime.now()

    week_counter = itertools.count(start=1)
    song_rows: list[list] = []
    album_rows: list[list] = []
    weeks = load_all_weeks(GROUP_DATE)

    for positions, start_day, end_day in create_song_chart(uow, iter(weeks)):

        week_count = next(week_counter)
        song_positions = [
            pos for pos in positions if pos['place'] <= SONG_CHART_LENGTH
        ]
        insert_entries(uow, song_positions, start_day, end_day)
        show_chart(uow, song_positions, start_day, end_day, week_count)
        song_rows = update_song_sheet(
            song_rows, uow, song_positions, start_day, end_day, week_count
        )

        album_rows = create_album_chart(
            uow, positions, start_day, end_day, week_count, album_rows
        )

    uow.commit()

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

    sheet = Spreadsheet(GROUPBOARD_SHEET)

    print('')
    print(f'Sending {len(song_rows)} song rows to the spreadsheet.')

    song_range = f'BOT_SONGS!A1:J{len(song_rows) + 1}'
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

    print('')
    print(f'Process Completed in {datetime.now() - start_time}')
    return functools.reduce(operator.add, weeks)


if __name__ == '__main__':
    weeks = create_group_charts()
    update_spreadsheet_plays(
        create_song_play_updater_from_weeks(weeks),
        GROUPBOARD_SHEET,
        verbose=True,
    )