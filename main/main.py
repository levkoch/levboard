import csv
import sys

from datetime import date, datetime, timedelta
from typing import Optional

from model import Song, Entry, spotistats, config
from storage import SongUOW

LAZY_NAME = True

def load_week(start_day: date, end_day: date):
    songs = spotistats.songs_week(start_day, end_day)

    if len(songs) < 60:
        print(f'Only {len(songs)} songs got over 1 stream that week.')
        raise ValueError('not enough songs')

    cutoff: int = songs[59]['plays']
    print(f'Song cutoff this week is {cutoff} plays.')
    songs = [i for i in songs if i['plays'] >= cutoff]
    for i in songs:
        i['place'] = len([j for j in songs if j['plays'] > i['plays']]) + 1

    return songs


def ask_new_song(uow: SongUOW, song_id: str) -> Song:
    """
    Song factory function to add songs into the database.
    """

    tester = Song(song_id)
    if LAZY_NAME: return tester
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
            if end_date > date.today():
                raise ValueError(
                    'Not enough songs found in this week.'
                ) from None
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
        for song in uow.songs:
            song._entries = []
        uow.commit()


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
                "'=" if movement == '=' else movement,
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


if __name__ == '__main__':
    if len(sys.argv) == 2:
        config.update_settings(username = sys.argv[1])

    username = config.get_username()
    print(f'Finding song data for {username}.')
    uow = SongUOW()
    start_time = datetime.now()
    week_count = 0
    start_date = config.get_start_date()
    song_rows: list[list] = []

    clear_entries(uow)

    while True:
        end_date = start_date + timedelta(days=7)

        try:
            positions, end_date = get_positions(start_date, end_date)
        # thrown when not enough to fill a week so week is extended past today
        except ValueError:
            print('')
            print('All weeks found. Ending Process.')
            break  # from the big loop

        insert_entries(uow, positions, start_date, end_date)
        week_count += 1
        show_chart(uow, positions, start_date, end_date, week_count)

        song_rows = update_song_sheet(
            song_rows, uow, positions, start_date, end_date
        )
        start_date = end_date  # shift pointer

    start_song_row = ['MV', 'Title', 'Artists', 'TW', 'LW', 'OC', 'PLS', 'PK'],
    
    with open('songs.csv', 'w', encoding='UTF-8', newline='') as f:
        songs_writer = csv.writer(f)
        songs_writer.writerow(start_song_row)
        songs_writer.writerows(song_rows)

    print('')
    print(f'Process Completed in {datetime.now() - start_time}')
