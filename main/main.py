import requests
import time

from datetime import date, datetime, timedelta
from typing import Callable, Optional

from model import Album, AlbumEntry, AlbumCert, Song, Entry
from storage import SongUOW
from spreadsheet import Spreadsheet

# first week of awl time
FIRST_DATE = date.fromisoformat('2021-05-13')


def date_to_timestamp(day: date) -> int:
    return int(time.mktime(day.timetuple()) * 1000)


def load_week(start_day: date, end_day: date):
    r = requests.get(
        'https://api.stats.fm/api/v1/users/lev/top/tracks'
        f'?after={date_to_timestamp(start_day)}'
        f'&before={date_to_timestamp(end_day)}'
    )

    songs = [
        {'plays': i['streams'], 'id': str(i['track']['id'])}
        for i in r.json()['items']
        if i['streams'] > 1
    ]

    if len(songs) < 60:
        print(f'Only {len(songs)} songs got over 1 stream that week.')
        raise ValueError('not enough songs')

    cutoff: int = songs[59]['plays']
    print(f'Song cutoff this week is {cutoff} plays.')
    songs = [i for i in songs if i['plays'] >= cutoff]
    for i in songs:
        i['place'] = len([j for j in songs if j['plays'] > i['plays']]) + 1

    return songs


def ask_new_song(uow, song_id) -> Song:
    tester = Song(song_id)
    # defaults to official name if no name specified
    print(f'\nSong {tester.name} ({song_id}) not found.')
    print(f'Find the link here -> https://stats.fm/track/{song_id}')
    name: str = input('What should the song be called in the database? ')

    if name.strip() == '':
        return tester

    if name.lower().strip() == 'merge':
        merge: str = input('Id of the song to merge with: ')
        merge_into = uow.songs.get(merge)
        merge_into.add_alt(song_id)
        print(f'Sucessfully merged {tester.name} into {merge_into.name}')
        return merge_into

    return Song(song_id.strip(), name)


def get_positions(start_date: date, end_date: date) -> tuple[list[dict], date]:
    while True:
        print(
            f'\nChecking songs from {start_date.isoformat()} to {end_date.isoformat()}.'
        )
        try:
            positions = load_week(start_date, end_date)
        except ValueError:
            print('Not enough songs found in the time range.')
            end_date += timedelta(days=7)
        else:
            return positions, end_date


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
            )
            song.add_entry(entry)
        uow.commit()


def clear_entries(uow: SongUOW) -> None:
    print('Clearing previous entries.')
    with uow:
        for song_id in uow.songs.list():
            song: Song = uow.songs.get(song_id)
            song._entries = []
        for album_name in uow.albums.list():
            album: Album = uow.albums.get(album_name)
            album.entries = []
        uow.commit()


def get_movement(current: date, last: date, song: Song) -> str:
    c_place: Optional[Entry] = song.get_entry(current)
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
    uow: SongUOW,
    positions: list[dict],
    start: date,
    end: date,
    week_count: int,
):
    print(f'\n({week_count}) Week of {start.isoformat()} to {end.isoformat()}')
    print(f' MV | {"Title":<45} | {"Artists":<45} | TW | LW | OC | PLS | PK')
    for pos in positions:
        with uow:
            song: Song = uow.songs.get(pos['id'])
        prev = song.get_entry(start)
        print(
            f"{get_movement(end, start, song):>3} | {song.name:<45} | {', '.join(song.artists):<45} | {pos['place']:<2}"
            f" | {(prev.place if prev else '-'):<2} | {song.weeks:<2} | {pos['plays']:<3} | {get_peak(song):<3}"
        )
    print('')


def update_song_sheet(
    rows: list[list],
    uow: SongUOW,
    positions: list[dict],
    start_date: date,
    end_date: date,
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
        ]
    )
    new_rows.append(['MV', 'Title', 'Artists', 'TW', 'LW', 'OC', 'PLS', 'PK'])

    for pos in positions:
        with uow:
            song: Song = uow.songs.get(pos['id'])
        prev: Optional[Entry] = song.get_entry(start_date)
        movement: str = get_movement(end_date, start_date, song)
        peak: str = get_peak(song)

        new_rows.append(
            [
                "'" + movement,
                song.name,
                ', '.join(song.artists),
                pos['place'],
                prev.place if prev else '-',
                song.weeks,
                pos['plays'],
                peak,
            ]
        )

    new_rows.append(['', '', '', '', '', '', '', ''])
    new_rows.extend(rows)
    return new_rows


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


def get_album_week(
    start_date: date, end_date: date
) -> Callable[[Album, bool], int]:
    r = requests.get(
        'https://api.stats.fm/api/v1/users/lev/top/tracks'
        f'?after={date_to_timestamp(start_date)}'
        f'&before={date_to_timestamp(end_date)}'
    )
    plays = [
        {'plays': i['streams'], 'id': str(i['track']['id'])}
        for i in r.json()['items']
    ]

    def get_album_plays(album: Album, accurate: bool = False) -> int:
        album_plays = 0

        for song in album.songs:
            song_plays = next(
                (i['plays'] for i in plays if i['id'] == song.id), None
            )

            if song_plays is None:
                # period plays accounts for alternate ids
                if accurate:
                    album_plays += song.period_plays(start_date, end_date)
                # else add 0 becuase it didn't find anything

            else:
                album_plays += song_plays

                for alt_id in song.alt_ids:
                    song_plays = next(
                        (i['plays'] for i in plays if i['id'] == alt_id), 0
                    )
                    album_plays += song_plays

        return album_plays

    return get_album_plays


def make_album_chart(
    uow: SongUOW,
    start_date: date,
    end_date: date,
    week_count: int,
    rows: list[list],
) -> list[list]:
    units: list[tuple[Album, int]] = []
    album_plays = get_album_week(start_date, end_date)
    for album_name in uow.albums.list():
        album: Album = uow.albums.get(album_name)
        album_units = album.get_points(end_date) + (2 * album_plays(album))
        units.append([album, album_units])

    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] >= units[19][1] and i[1]]

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
            '',
            '',
        ],
        [
            'MV',
            'Title',
            'CRT',
            'Artists',
            'TW',
            'LW',
            'OC',
            'PK',
            'UTS',
            'PLS',
            'PTS',
        ],
    ]

    print(f'({week_count}) Albums chart for week of {end_date.isoformat()}.')
    print('')
    print(
        f' MV | {"Title":<45} | CRT | {"Artists":<45} | TW | LW | OC | PK  | UTS | PLS | PTS'
    )

    all_time_plays = get_album_week(FIRST_DATE, end_date)

    for (album, album_units) in units:
        position = len([i for i in units if i[1] > album_units]) + 1
        entry = AlbumEntry(
            start=start_date, end=end_date, units=album_units, place=position
        )
        album.add_entry(entry)

        album_cert = format(
            AlbumCert(all_time_plays(album) + album.points), 'S'
        )

        prev = album.get_entry(start_date)
        movement = get_movement(end_date, start_date, album)
        peak = get_peak(album)
        plays = album_plays(album)
        points = album.get_points(end_date)

        print(
            f'{movement:>3} | {album.title:<46} {album_cert:>4} | {album.str_artists:<45}'
            f" | {position:<2} | {(prev.place if prev else '-'):<2} | {album.weeks:<2}"
            f' | {peak:<3} | {album_units:<3} | {plays:<3} | {points:<3}'
        )

        new_rows.append(
            [
                "'" + movement,
                album.title,
                album_cert,
                album.str_artists,
                position,
                prev.place if prev else '-',
                album.weeks,
                peak,
                album_units,
                plays,
                points,
            ]
        )

    new_rows.append(['', '', '', '', '', '', '', '', '', '', ''])
    new_rows.extend(rows)
    return new_rows


if __name__ == '__main__':
    uow = SongUOW()

    """
    for top in (1, 3, 5, 10, 20, 40, None):
        display_longest_runs(uow, top)
        print('')
    """
    start_time = datetime.now()

    week_count = 0
    clear_entries(uow)

    start_date = FIRST_DATE
    song_rows: list[list] = []
    album_rows: list[list] = []

    while True:
        end_date = start_date + timedelta(days=7)
        if end_date > date.today():
            print('')
            print('All weeks found. Ending Process.')
            break  # from the big loop

        positions, end_date = get_positions(start_date, end_date)
        insert_entries(uow, positions, start_date, end_date)
        week_count += 1
        show_chart(uow, positions, start_date, end_date, week_count)
        album_rows = make_album_chart(
            uow, start_date, end_date, week_count, album_rows
        )

        song_rows = update_song_sheet(
            song_rows, uow, positions, start_date, end_date
        )
        start_date = end_date  # shift pointer

    start_song_rows = [
        ['MV', 'Title', 'Artists', 'TW', 'LW', 'OC', 'PLS', 'PK'],
    ]
    start_song_rows.extend(song_rows)
    song_rows = start_song_rows

    start_album_rows = [
        [
            'MV',
            'Title',
            'CRT',
            'Artists',
            'TW',
            'LW',
            'OC',
            'PK',
            'UTS',
            'PLS',
            'PTS',
        ],
    ]
    start_album_rows.extend(album_rows)
    album_rows = start_album_rows

    sheet = Spreadsheet('1_KNcoT92nfgQCRqLH7Iz4ZSxy9hxCd8ll0Hzn9hscqk')

    print('')
    print(f'Sending {len(song_rows)} song rows to the spreadsheet.')
    sheet.update_range(f'BOT_SONGS!A1:H{len(song_rows) + 1}', song_rows)

    print(f'Sending {len(album_rows)} album rows to the spreadsheet.')
    sheet.update_range(f'BOT_ALBUMS!A1:K{len(album_rows) + 1}', album_rows)

    print('')
    print(f'Process Completed in {datetime.now() - start_time}')
