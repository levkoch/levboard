from copy import deepcopy
import functools
import itertools

from datetime import date, timedelta, datetime
from concurrent import futures
from operator import itemgetter
from typing import Optional, Iterator
from collections import Counter, defaultdict
from config import FIRST_DATE

from storage import SongUOW
from model import SongCert, Song, spotistats, Album


uow = SongUOW()
MAX_ADJUSTED = 25


def get_song_play_history(song: Song) -> list[spotistats.Listen]:
    with futures.ThreadPoolExecutor() as executor:
        # make song main id into list to add to alternate ids
        mapped = executor.map(
            spotistats.song_play_history, ([song.id] + song.alt_ids)
        )

    return list(itertools.chain(*mapped))


def time_to_units(song: Song, units_mark: int) -> tuple[Song, date, int]:
    """finds the time it took for a song to reach some unit amount"""

    if song.units < units_mark:
        raise ValueError('not enough units for song')

    play_record = get_song_play_history(song)
    date_counter = Counter(i.finished_playing.date() for i in play_record)

    play_record.sort(key=lambda i: i.finished_playing)
    first_play: datetime = play_record[0].finished_playing

    # int() returns 0 which is what we want the slots to start at
    daily_units: dict[date, int] = defaultdict(int)

    for day, plays in date_counter.items():
        if plays > MAX_ADJUSTED:
            # filter plays so they cap out at 25 per day
            plays = MAX_ADJUSTED
        daily_units[day] += plays * 2

    for entry in song.entries:
        daily_units[entry.end] += 61 - entry.place

    running_units = 0

    for day, units in sorted(list(daily_units.items()), key=itemgetter(0)):
        running_units += units
        if running_units >= units_mark:
            return (song, day, (day - first_play.date()).days)

    raise ValueError('shouldnt reach here')


def top_shortest_time_units_milestones(uow: SongUOW, unit_milestone: int):
    contenders = (song for song in uow.songs if song.units >= unit_milestone)

    with futures.ThreadPoolExecutor() as executor:
        units = list(
            executor.map(
                functools.partial(time_to_units, units_mark=unit_milestone),
                contenders,
            )
        )

    units.sort(key=itemgetter(1))
    if len(units) > 19:
        day_units = [i for i in units if i[1] <= units[19][1]]
    else:
        day_units = deepcopy(units)

    print(f'First songs to reach {unit_milestone} units:')
    for (song, day, time) in day_units:
        place = len([unit for unit in day_units if unit[1] < day]) + 1
        print(f'{place:<2} | {song:<60} | {day} ({time} days)')
    print('')

    units.sort(key=itemgetter(2))
    if len(units) > 19:
        time_units = [i for i in units if i[2] <= units[19][2]]
    else:
        time_units = deepcopy(units)

    print(f'Fastest songs to reach {unit_milestone} units:')
    for (song, day, time) in time_units:
        place = len([unit for unit in time_units if unit[2] < time]) + 1
        print(f'{place:<2} | {song:<60} | {time} days ({day})')
    print('')


def time_to_plays(song: Song, plays: int) -> tuple[Song, timedelta]:
    play_record = get_song_play_history(song)

    if len(play_record) < plays:
        raise ValueError('not enough plays for song')

    play_record.sort(key=lambda i: i.finished_playing)
    first_play: datetime = play_record[0].finished_playing
    wanted_play: datetime = play_record[plays - 1].finished_playing

    time = wanted_play - first_play

    # print(f'{song.name} took {time.days} days to reach {plays} plays')

    return (song, time)


def top_shortest_time_plays_milestones(uow: SongUOW, plays: int):
    contenders = (song for song in uow.songs if song.plays >= plays)

    with futures.ThreadPoolExecutor() as executor:
        mapped = executor.map(
            functools.partial(time_to_plays, plays=plays), contenders
        )

    units = [i for i in mapped if i[1].days > 1]
    units.sort(key=lambda i: i[1])
    if len(units) > 19:
        units = [i for i in units if i[1] <= units[19][1]]
    print(f'Fastest songs to reach {plays} plays:')
    for (song, time) in units:
        place = len([unit for unit in units if unit[1].days < time.days]) + 1
        print(f'{place:<2} | {song:<60} | {time.days} days')
    print('')


def top_albums_cert_count(uow: SongUOW, cert: SongCert):
    contenders = [(album, album.get_certs(cert)) for album in uow.albums]
    contenders.sort(key=lambda i: i[1], reverse=True)
    contenders = [
        i for i in contenders if i[1] >= contenders[19][1] and i[1]  # > 1
    ]
    print(f'Albums with most songs {cert:f} or higher:')
    for (album, songs) in contenders:
        place = len([unit for unit in contenders if unit[1] > songs]) + 1
        print(
            f"{place:>2} | {f'{album.title} by {album.str_artists}':<60} | {songs:>2} songs"
        )
    print('')


def top_albums_consecutive_weeks(uow: SongUOW, top: Optional[int]):
    units = [(album, album.get_conweeks(top)) for album in uow.albums]

    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] >= units[16][1] and i[1] > 1]
    print(
        f"Albums with most consecutive weeks {f'in the top {top}' if top else 'on chart'}:"
    )
    for (count, (album, weeks)) in enumerate(units):
        print(
            f"{count + 1:>2} | {f'{album.title} by {album.str_artists}':<55} | {weeks:>2} wks"
        )
    print('')


def top_albums_song_weeks(uow: SongUOW, top: Optional[int]):
    units = [(album, album.get_weeks(top)) for album in uow.albums]
    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] > units[16][1]]

    print(
        f"Albums with most song weeks {f'in the top {top}' if top else 'on chart'}:"
    )
    for album, weeks in units:
        place = len([i for i in units if i[1] > weeks]) + 1
        print(f'{place:>3} | {str(album):<50} | {weeks:<3} weeks')
    print('')


def top_album_hits(uow: SongUOW, top: Optional[int]):
    units = [(album, album.get_hits(top)) for album in uow.albums]
    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] > units[19][1]]

    print(
        f"Albums with most songs {f'peaking in the top {top}' if top else 'charted'}:"
    )
    for album, songs in units:
        place = len([i for i in units if i[1] > songs]) + 1
        print(f'{place:>3} | {str(album):<50} | {songs:<3} songs')
    print('')


def top_song_consecutive_weeks(uow, top):
    units: list[tuple[Song, int]] = [
        (song, song.get_conweeks(top)) for song in uow.songs
    ]
    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] >= units[19][1] and i[1] > 1]

    print(
        f"Songs with most consecutive weeks {f'in the top {top}' if top else 'on chart'}:"
    )
    for (song, weeks) in units:
        place = len([unit for unit in units if unit[1] > weeks]) + 1
        print(
            f"{place:>2} | {f'{song.name} by {song.str_artists}':<55} | {weeks:>2} wks"
        )


def top_album_song_weeks(uow: SongUOW, weeks: Optional[int]):
    units = [(album, album.get_charted(weeks)) for album in uow.albums]
    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] > units[20][1]]

    print(
        f"Albums with most songs {f'charting for {weeks} weeks or more' if weeks else 'charted'}:"
    )
    for album, songs in units:
        place = len([i for i in units if i[1] > songs]) + 1
        print(f'{place:>3} | {str(album):<50} | {songs:<2} songs')
    print('')


def top_albums_weeks(uow: SongUOW, top: Optional[int]):
    units = [(album, album.get_weeks(top)) for album in uow.albums]
    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] > units[19][1]]

    print(f"Albums with most song weeks {f'in the top {top}' if top else ''}:")
    for album, weeks in units:
        place = len([i for i in units if i[1] > weeks]) + 1
        print(f'{place:>3} | {str(album):<50} | {weeks:<2} weeks')
    print('')


def get_album_units(album: Album, start: date, end: date) -> tuple[Album, int]:
    return album, album.period_units(start, end)


def top_albums_month(uow: SongUOW, start: date, end: date):
    with futures.ThreadPoolExecutor() as executor:
        units: list[tuple] = list(
            executor.map(
                functools.partial(get_album_units, start=start, end=end),
                uow.albums,
            )
        )
    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] > units[19][1]]

    print(
        f'Bestselling albums between {start.isoformat()} and {end.isoformat()}.'
    )
    for album, data in units:
        place = len([i for i in units if i[1] > data]) + 1
        print(f'{place:>3} | {str(album):<50} | {data:<2} units')
    print('')


def display_all_songs(uow: SongUOW):
    all_songs = [song for song in uow.songs if song.units]
    all_songs.sort(key=lambda i: i.units, reverse=True)
    for (count, song) in enumerate(all_songs):
        print(
            f'{count + 1:>4} | {song.name:<45} | {song.str_artists:<45} | peak: {song.peak:<2} '
            f'{(("(" + str(song.peakweeks) + ")") if (song.peak < 11 and song.peakweeks > 1) else " "):<4} '
            f'| weeks: {song.weeks:<2} | plays: {song.plays:<3} | {song.cert}'
        )


MILESTONES = [25, 50, 75, 100, 150, 200, 250, 300, 350, 400]
CERT_UNITS = [100, 200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000]
ALBUM_TOP = [1, 3, 5, 10, 15, None]
SONG_TOP = [1, 3, 5, 10, 20, 30, None]
SONG_WEEKS = [30, 20, 15, 10, 5, None]
CERTS = [SongCert.from_units(i) for i in CERT_UNITS]

if __name__ == '__main__':
    uow = SongUOW()

    """
    for milestone in MILESTONES[::-1]:
        top_shortest_time_plays_milestones(uow, milestone)
    """

    
    for milestone in CERT_UNITS[::-1]:
        top_shortest_time_units_milestones(uow, milestone)
    

    """
    for cert in CERTS[::-1]:
        top_albums_cert_count(uow, cert)
    """
    """
    top_albums_month(uow, date.fromisoformat('2022-01-01'), date.fromisoformat('2023-01-01'))
    """

    """
    for top in ALBUM_TOP:
        top_albums_consecutive_weeks(uow, top)
        top_albums_weeks(uow, top)
    """

    '''
    for top in SONG_TOP:
        top_album_hits(uow, top)
    '''
    """
    for weeks in SONG_WEEKS:
        top_album_song_weeks(uow, weeks)
    """

    """
    start_day = date(FIRST_DATE.year, FIRST_DATE.month, 1)
    end_day = date(start_day.year, start_day.month + 1, 1)

    while start_day <= date.today():
        top_albums_month(uow, start_day, end_day)

        start_day: date = end_day
        next_month: int = end_day.month + 1
        next_year: int = end_day.year
        if next_month == 13:
            next_month = 1
            next_year += 1

        end_day = date(next_year, next_month, 1)
    """
    """
    display_all_songs(uow)
    """