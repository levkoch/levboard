from datetime import date, timedelta
from pydantic import BaseModel
from concurrent import futures
from typing import Iterator, Optional
from itertools import count

from storage import SongUOW
from spreadsheet import Spreadsheet
from model import spotistats, Song, Album, Entry, NewEntry
from config import FIRST_DATE, TEST_SONG_FILE, LEVBOARD_SHEET


class Week(BaseModel):
    """
    A dataclass for a loaded week of songs.

    Attributes:
    * start_day (`date`): The date when
    """

    start_day: date
    end_day: date
    songs: list[spotistats.Position]

    def __lt__(self, other):
        try:
            return self.end_day < other.end_day
        except AttributeError:
            return NotImplemented


def load_week(start_day: date, end_day: date) -> Week:
    songs = spotistats.songs_week(start_day, end_day, adjusted=True)
    return Week(start_day=start_day, end_day=end_day, songs=songs)


def load_all_weeks(start_day: date) -> list[Week]:
    print('Loading all weeks')
    with futures.ThreadPoolExecutor() as executor:
        to_do: list[futures.Future] = []
        end_day = start_day + timedelta(days=7)

        while end_day <= date.today():
            future = executor.submit(
                load_week, start_day=start_day, end_day=end_day
            )
            to_do.append(future)
            print(f'Loading from {start_day!s} to {end_day!s}')

            start_day = end_day
            end_day = start_day + timedelta(days=7)

        weeks = [future.result() for future in futures.as_completed(to_do)]
        return sorted(weeks)


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
    if song.peak > 10 or song.peakweeks == 1:
        return str(song.peak)
    pweeks = str(song.peakweeks)
    for (k, v) in num_to_exp.items():
        pweeks = pweeks.replace(k, v)
    return str(song.peak) + pweeks


def create_song_chart(
    weeks: Iterator[Week],
) -> Iterator[tuple[dict, date, date]]:

    two_wa = next(weeks)
    one_wa = next(weeks)
    this_wk = next(weeks)

    while True:
        all_songs = (
            {pos.id for pos in two_wa.songs}
            | {pos.id for pos in one_wa.songs}
            | {pos.id for pos in this_wk.songs}
        )

        song_info: list[dict] = []

        for song_id in all_songs:
            two_wa_plays = next(
                (pos.plays for pos in two_wa.songs if pos.id == song_id), 0
            )
            one_wa_plays = next(
                (pos.plays for pos in one_wa.songs if pos.id == song_id), 0
            )
            this_wk_plays = next(
                (pos.plays for pos in this_wk.songs if pos.id == song_id), 0
            )

            song_info.append(
                {
                    'id': song_id,
                    'points': two_wa_plays
                    + 2 * one_wa_plays
                    + 4 * this_wk_plays,
                    'plays': this_wk_plays,
                }
            )

        for info in song_info:
            info['place'] = (
                len([i for i in song_info if i['points'] > info['points']]) + 1
            )

        song_info = [info for info in song_info if info['place'] <= 60]
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
    print(f'\nSong {tester.name} ({song_id}) not found.')
    print(f'Find the link here -> https://stats.fm/track/{song_id}')
    name = input('What should the song be called in the database? ').strip()

    if name == '':
        return tester

    if name.lower() == 'merge':
        merge: str = input('Id of the song to merge with: ')
        merge_into = uow.songs.get(merge)
        merge_into.add_alt(song_id)
        print(f'Sucessfully merged {tester.name} into {merge_into.name}')
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
            entry = NewEntry(
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
            f"{get_movement(end, start, song):>3} | {song.name:<45} | {', '.join(song.artists):<45} | {pos['place']:<2}"
            f" | {(prev.place if prev else '-'):<2} | {song.weeks:<2} | {pos['points']:<3} | {pos['plays']:<3} | {get_peak(song):<3}"
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

    new_rows.append([f'{start_date.isoformat()} to {actual_end.isoformat()}'])
    new_rows.append(
        ['MV', 'Title', 'Artists', 'TW', 'LW', 'OC', 'PTS', 'PLS', 'PK']
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
                song.name,
                ', '.join(song.artists),
                pos['place'],
                prev.place if prev else '-',
                song.weeks,
                pos['points'],
                pos['plays'],
                peak,
            ]
        )

    new_rows.append([''])
    new_rows.extend(rows)
    return new_rows


if __name__ == '__main__':
    # load_songs(file = TEST_SONG_FILE, verbose = True)

    uow = SongUOW(song_file=TEST_SONG_FILE)
    clear_entries(uow)

    week_counter = count(start=1)
    song_rows: list[list] = []
    weeks = load_all_weeks(FIRST_DATE)

    for positions, start_day, end_day in create_song_chart(iter(weeks)):
        insert_entries(uow, positions, start_day, end_day)
        show_chart(uow, positions, start_day, end_day, next(week_counter))
        song_rows = update_song_sheet(
            song_rows, uow, positions, start_day, end_day
        )

    start_song_rows = [
        ['MV', 'Title', 'Artists', 'TW', 'LW', 'OC', 'PTS', 'PLS', 'PK'],
        [''],
    ]

    song_rows = start_song_rows + song_rows

    sheet = Spreadsheet(LEVBOARD_SHEET)
    song_range = f'NEW_SONGS!A1:I{len(song_rows) + 1}'
    sheet.delete_range(song_range)
    sheet.update_range(song_range, song_rows)
