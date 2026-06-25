"""
main/stats.py

a collection of various statistics generators for data already collected.
"""

import functools
import itertools

from collections import Counter, defaultdict
from concurrent import futures
from datetime import date, datetime, timedelta
from operator import attrgetter, itemgetter
from typing import Final, Iterable, Optional, TypeAlias, Union

from config import FIRST_DATE
from plays import update_local_plays
from model import Album, Song, SongCert, spotistats
from model.spotistats import MAX_ADJUSTED
from storage import AlbumRepository, SongRepository, SongUOW

Charteable: TypeAlias = Union[Song, Album]

uow = SongUOW()


def is_chart_date(date: date) -> bool:
    return date.weekday() == 3


def charted_between(
    song_or_album: Union[Song, Album], start: date, end: date
) -> bool:
    current = start

    def chart_dates(end: date):
        nonlocal current
        while True:
            if is_chart_date(current):
                yield current
            if current > end:
                return
            current += timedelta(days=1)

    dates = set(chart_dates(end))

    return len(dates & set(entry.end for entry in song_or_album.entries)) > 0


def get_song_play_history(song: Song) -> list[spotistats.Listen]:
    with futures.ThreadPoolExecutor() as executor:
        # make song main id into list to add to alternate ids
        mapped = executor.map(spotistats.song_play_history, song.ids)

    return list(itertools.chain(*mapped))


def get_album_play_history(album: Album) -> dict[str, list[spotistats.Listen]]:
    """collects play history for every song in the album"""

    def inner(main_id, ids) -> tuple[str, Iterable[spotistats.Listen]]:
        return (
            main_id,
            itertools.chain.from_iterable(
                spotistats.song_play_history(i) for i in ids
            ),
        )

    with futures.ThreadPoolExecutor() as executor:
        mapped = executor.map(
            inner,
            (id for (id, song) in album.songs),
            (song.get_variant(id).ids for (id, song) in album.songs),
        )

    return {id: list(listens) for (id, listens) in mapped}


def time_to_units(song: Song, units_mark: int) -> tuple[Song, date, int]:
    """finds the time it took for a song to reach some unit amount"""

    if song.units < units_mark:
        raise ValueError('not enough units for song')

    play_record = get_song_play_history(song)
    date_counter = Counter(i.finished_playing.date() for i in play_record)

    play_record.sort(key=lambda i: i.finished_playing)
    first_play: date = play_record[9].finished_playing.date()

    # int() returns 0 which is what we want the slots to start at
    daily_units: dict[date, int] = defaultdict(int)

    for day, plays in date_counter.items():
        # song histories are now always filtered
        daily_units[day] += plays * 2

    for entry in song.entries:
        daily_units[entry.end] += 61 - entry.place

    running_units = 0

    for day, units in sorted(list(daily_units.items()), key=itemgetter(0)):
        running_units += units
        if running_units >= units_mark:
            return (song, day, (day - first_play).days)

    raise ValueError(f'{song} hasnt reached {units_mark} units yet')


def time_to_units_album(
    album: Album, units_mark: int
) -> tuple[Album, date, int]:
    if album.units < units_mark:
        raise ValueError(f'{album} hasnt reached {units_mark} units yet')

    first_play: date = date.today()
    # int() returns 0 which is what we want the slots to start at
    daily_units: dict[date, int] = defaultdict(int)

    all_listens = get_album_play_history(album)

    for (id, song) in album.songs:
        play_record = all_listens[id]
        date_counter = Counter(i.finished_playing.date() for i in play_record)

        play_record.sort(key=lambda i: i.finished_playing)
        first_play = min(first_play, play_record[0].finished_playing.date())

        for day, plays in date_counter.items():
            if plays > MAX_ADJUSTED:
                # filter plays so they cap out at 25 per day
                plays = MAX_ADJUSTED
            daily_units[day] += plays * 2

        for entry in song.entries:
            if entry.variant in song.get_variant(id).ids:
                daily_units[entry.end] += 61 - entry.place

    running_units = 0

    for day, units in sorted(list(daily_units.items()), key=itemgetter(0)):
        running_units += units
        if running_units >= units_mark:
            return (album, day, (day - first_play).days)

    return (album, date.today(), -1)

def top_shortest_time_units_milestones(
    uow: SongUOW, unit_milestone: int, cutoff: int = 20
):
    with futures.ThreadPoolExecutor() as executor:
        executor.map(
            lambda i: i._populate_listens(),
            (song for song in uow.songs if song.weeks and not song.plays),
        )

    contenders = (song for song in uow.songs if song.units >= unit_milestone)

    with futures.ThreadPoolExecutor() as executor:
        units = list(
            executor.map(
                functools.partial(time_to_units, units_mark=unit_milestone),
                contenders,
            )
        )
    """
    units.sort(key=itemgetter(1))
    if len(units) > cutoff:
        day_units = [i for i in units if i[1] <= units[(cutoff-1)][1]]
    else:
        day_units = deepcopy(units)

    print(f'First songs to reach {unit_milestone} units:')
    for (song, day, time) in day_units:
        place = len([unit for unit in day_units if unit[1] < day]) + 1
        print(f'{place:<2} | {song:<60} | {day} ({time} days)')
    print('')
    """

    units.sort(key=itemgetter(2))
    if len(units) > cutoff:
        time_units = [i for i in units if i[2] <= units[(cutoff - 1)][2]]
    else:
        time_units = units

    print(f'Fastest songs to reach {unit_milestone} units:')
    for (song, day, time) in time_units:
        place = len([unit for unit in time_units if unit[2] < time]) + 1
        print(f'{place:<2} | {song:<60} | {time} days ({day})')
    print('')


def top_shortest_time_units_milestones_infographic(
    uow: SongUOW, unit_milestone: int, extras=False
):
    contenders = (
        song
        for song in uow.songs
        if song.units >= unit_milestone
    )

    with futures.ThreadPoolExecutor() as executor:
        units = list(
            executor.map(
                functools.partial(time_to_units, units_mark=unit_milestone),
                contenders,
            )
        )

    units.sort(key=itemgetter(1))
    BEGINNING: date = date(2021, 5, 1)

    print(f'First songs to reach {unit_milestone} units:')
    for (song, day, time) in units:
        place = len([unit for unit in units if unit[1] < day]) + 1
        start_day: date = day - timedelta(days=time)

        print(
            f'{place:<3} | {song:<60} | day {(start_day - BEGINNING).days:>4}'
            f' -> {(day - BEGINNING).days:<4} ({time:<4} days / '
            f'{start_day.isoformat()} -> {day.isoformat()})'
        )

        if extras:
            period_plays = song.period_plays(start_day, day)
            period_weeks = song.period_weeks(start_day, day)
            print(
                f'{66*" "}| {period_plays:<4} plays | {period_weeks:<2} weeks'
            )

    units.sort(key=itemgetter(2))

    print(f'\nFastest songs to reach {unit_milestone} units:')
    for (song, day, time) in units:
        place = len([unit for unit in units if unit[2] < time]) + 1
        start_day: date = day - timedelta(days=time)

        print(
            f'{place:<3} | {song:<60} | day {(start_day - BEGINNING).days:>4}'
            f' -> {(day - BEGINNING).days:<4} ({time:<4} days / '
            f'{start_day.isoformat()} -> {day.isoformat()})'
        )

        if extras:
            period_plays = song.period_plays(start_day, day)
            period_weeks = song.period_weeks(start_day, day)
            print(
                f'{66*" "}| {period_plays:<4} plays | {period_weeks:<2} weeks'
            )

def top_upcoming_projected_milestone(
    uow: SongUOW, unit_milestone: int, cutoff: int, show: int = 20
):
    TODAY = date.today()
    THREEMOS = date.today() - timedelta(days=7*12)
    YEARAGO = date.today() - timedelta(days=365)

    contenders = [
        song 
        for song in uow.songs
        if song.units < unit_milestone
    ]

    results = []

    for song in contenders:
        # assuming each song gets a steady stream of units,
        # days to reach milestone = units remaining / units per day
        start = song.nth_stream(5)

        if start > THREEMOS:
            combined = song.period_units(THREEMOS, TODAY) / (7*12)
        else: 
            all_time = song.units / (TODAY - start).days
            three_months = song.period_units(THREEMOS, TODAY) / (7*12)
            last_year = song.period_units(YEARAGO, TODAY) / 365
            combined = three_months * 0.5 + last_year * 0.25 + all_time * 0.25

        projection = int((unit_milestone - song.units) / combined)
        run = (TODAY - start).days + projection
        results.append((song, unit_milestone - song.units, projection, run))
        
    results.sort(key=itemgetter(2))
    print(f'next songs projected to reach {unit_milestone} units')
    for song, remaining, projection, run in results[:show]:
        print(f"{projection:<4} | {TODAY + timedelta(days=projection)} ({run:<4})| {remaining:<4} left | {song}")


def top_shortest_time_album_units_milestones_infographic(
    uow: SongUOW, unit_milestone: int, extras=False
):

    with futures.ThreadPoolExecutor() as executor:
        units = executor.map(
            functools.partial(time_to_units_album, units_mark=unit_milestone),
            uow.albums,
        )

    units: list[tuple] = [
        (album, day, days) for (album, day, days) in units if days != -1
    ]
    print(f'found {len(units)} contenders for fastest to {unit_milestone}\n')

    units.sort(key=itemgetter(1))
    BEGINNING: date = date(2021, 5, 1)

    print(f'First albums to reach {unit_milestone} units:')
    for (album, day, time) in units:
        place = len([unit for unit in units if unit[1] < day]) + 1
        start_day: date = day - timedelta(days=time)

        print(
            f'{place:<2} | {str(album):<60} | day {(start_day - BEGINNING).days:>4}'
            f' -> {(day - BEGINNING).days:<4} ({time:<4} days / '
            f'{start_day.isoformat()} -> {day.isoformat()})'
        )

        if extras:
            period_plays = album.period_plays(start_day, day)
            period_weeks = album.period_weeks(start_day, day)
            print(
                f'{66*" "}| {period_plays:<4} plays | {period_weeks:<2} weeks'
            )

    units.sort(key=itemgetter(2))

    print(f'\nFastest albums to reach {unit_milestone} units:')
    for (album, day, time) in units:
        place = len([unit for unit in units if unit[2] < time]) + 1
        start_day: date = day - timedelta(days=time)

        print(
            f'{place:<2} | {str(album):<60} | day {(start_day - BEGINNING).days:>4}'
            f' -> {(day - BEGINNING).days:<4} ({time:<4} days / '
            f'{start_day.isoformat()} -> {day.isoformat()})'
        )

        if extras:
            period_plays = album.period_plays(start_day, day)
            period_weeks = album.period_weeks(start_day, day)
            print(
                f'{66*" "}| {period_plays:<4} plays | {period_weeks:<2} weeks'
            )


def time_to_plays(song: Song, plays: int) -> tuple[Song, date, int]:
    play_record = get_song_play_history(song)

    if len(play_record) < plays:
        raise ValueError('not enough plays for song')

    play_record.sort(key=lambda i: i.finished_playing)
    first_play: datetime = play_record[0].finished_playing
    wanted_play: datetime = play_record[plays - 1].finished_playing

    time = wanted_play - first_play

    return (song, wanted_play.date(), time.days)


def top_shortest_time_plays_milestones(
    uow: SongUOW, plays: int, cutoff: int = 20
):
    contenders = (song for song in uow.songs if song.plays >= plays)

    with futures.ThreadPoolExecutor() as executor:
        mapped = executor.map(
            functools.partial(time_to_plays, plays=plays), contenders
        )
    units = list(mapped)
    units.sort(key=itemgetter(2))
    if len(units) > cutoff:
        units = [i for i in units if i[2] <= units[(cutoff - 1)][2]]
    if units:
        print(f'Fastest songs to reach {plays} plays:')
    for (song, _, time) in units:
        place = len([unit for unit in units if unit[2] < time]) + 1
        print(f'{place:<2} | {song:<60} | {time} days')
    if units:
        print('')


def top_albums_cert_count(uow: SongUOW, cert: SongCert):
    contenders = [(album, album.song_cert_count(cert)) for album in uow.albums]
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


def top_albums_play_count(uow: SongUOW, plays: int):
    contenders = [
        (album, len([i for i in album if i._plays >= plays]))
        for album in uow.albums
    ]
    contenders.sort(key=lambda i: i[1], reverse=True)
    contenders = [
        i for i in contenders if i[1] >= contenders[19][1] and i[1]  # > 1
    ]
    print(f'Albums with most songs with {plays} plays or higher:')
    for (album, songs) in contenders:
        place = len([unit for unit in contenders if unit[1] > songs]) + 1
        print(
            f"{place:>2} | {f'{album.title} by {album.str_artists}':<60} | {songs}/{len(album)} songs"
        )
    print('')


def top_albums_consecutive_weeks(uow: SongUOW, top: Optional[int]):
    units = [(album, album.get_con_weeks(top)) for album in uow.albums]

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
    units = [(album, album.get_song_weeks(top)) for album in uow.albums]
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


def weeks_top(
    c: Charteable,
    *,
    top: Optional[int] = None,
    before: Optional[date] = None,
    variant: Optional[str] = None,
) -> int:
    """
    the number of weeks the charteable spent in the top `top` before &
    including the week ending `before`, both arguments are optional
    and including just one works as well. Defaults to the number
    of weeks the album has spent charting.
    """

    if variant:
        try:
            eligible = [e for e in c.entries if e.variant == variant]
        except AttributeError:
            raise ValueError(
                "cannot specify an 'variant' parameter when filtering through album entries."
            )

    else:
        eligible = c.entries

    if top and before:   # filter by both
        return sum(
            1
            for entry in eligible
            if entry.place <= top and entry.end <= before
        )
    if top:   # filter only by top
        return sum(1 for entry in eligible if entry.place <= top)
    if before:   # filter only by weeks before
        return sum(1 for entry in eligible if entry.end <= before)
    return len(eligible)   # dont filter whatsoever


def conweeks(
    c: Charteable, breaks: bool = False, top: Optional[int] = None
) -> int:
    """
    The greatest number of consecutive weeks the song has spent in the top
    `top` of the chart. Will return 0 if the song has never charted or
    never charted in that region. Allows for songs to leave for 1 week if
    `breaks` is true. CCC_CCCCC_C will return 5 if `breaks` is false but 11
    if it's true.
    """

    entries = c.entries  # returns a copy, so we can pop
    if top:
        entries = [i for i in entries if i.place <= top]

    if len(entries) in (0, 1):
        return len(entries)

    longest = 0
    current_entry = entries.pop(0)

    while entries:
        streak = 1
        next_entry = entries.pop(0)

        while (
            (current_entry.end == next_entry.start)
            # standard mode where the next week charted too
            or (
                breaks
                and (current_entry.end + timedelta(days=7)) == next_entry.start
            )
        ):
            # with breaks mode where the next week didn't chart but we have
            # break mode turned on and the week after that charted.

            streak += 1
            if current_entry.end != next_entry.start:
                streak += 1

            current_entry = next_entry
            try:
                next_entry = entries.pop(0)
            except IndexError:
                break

        longest = max(longest, streak)
        current_entry = next_entry

    return longest


def all_consecutive(c: Charteable, breaks=False) -> list[tuple[date, int]]:
    """
    returns every streak that the charteable passed in has achived. returns a list
    of tuples, where the first item is the week that the streak started, and the
    second is how long the streak lasted. if breaks is turned on, then streaks
    that are separated by just one week missing will be combined together.
    so if something charted like `C_CCCC_CCCCC_CC` it will return
    `[(1, 1), (3, 4), (8, 5), (13, 2)]`.
    """

    entries = c.entries

    if len(entries) == 0:
        return []

    consecutive = []
    current_entry = entries.pop(0)

    while entries:
        starting_entry = current_entry
        streak = 1
        next_entry = entries.pop(0)

        while (
            (current_entry.end == next_entry.start)
            # standard mode where the next week charted too
            or (
                breaks
                and (current_entry.end + timedelta(days=7)) == next_entry.start
            )
        ):
            # with breaks mode where the next week didn't chart but we have
            # break mode turned on and the week after that charted.

            streak += 1
            current_entry = next_entry
            try:
                next_entry = entries.pop(0)
            except IndexError:
                break

        consecutive.append((starting_entry.end, streak))
        current_entry = next_entry

    return consecutive


def top_song_consecutive_weeks(uow: SongUOW, top: Optional[int]):
    units: list[tuple[Song, int]] = [
        (song, conweeks(song, top=top)) for song in uow.songs
    ]
    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] >= units[19][1] and i[1] > 1]

    print(
        f"Songs with most consecutive weeks {f'in the top {top}' if top else 'on chart'}:"
    )
    for (song, weeks) in units:
        place = len([unit for unit in units if unit[1] > weeks]) + 1
        print(
            f"{place:>2} | {f'{song.title} by {song.str_artists}':<55} | {weeks:>2} wks"
        )
    print('')


def top_collection_consecutive_weeks_infographic(
    collection: Union[SongRepository, AlbumRepository]
):
    THRESHOLD: Final[int] = 10
    kind = type(collection.get(collection.list()[0])).__name__
    print(f'{len(collection)} {kind}s stored')

    contenders: Iterable[Union[Song, Album]] = (
        c for c in collection if conweeks(c) >= THRESHOLD
    )

    units: list[tuple[Union[Song, Album], date, int]] = []
    for contender in contenders:
        units.extend(
            (contender, start, weeks)
            for (start, weeks) in all_consecutive(contender)
            if weeks >= THRESHOLD
        )

    print(f'{len(units)} {kind}s found\n')

    units.sort(key=lambda i: i[2], reverse=True)

    print(f'{kind}s with most consecutive weeks on chart')
    for (c, start, weeks) in units:
        place = len([unit for unit in units if unit[2] > weeks]) + 1
        end = start + timedelta(days=weeks * 7)
        active = end >= (datetime.now().date() - timedelta(days=7))
        # week start and week end are both inclusive of end weeks.
        print(
            f"{place:>2} | {f'{c.title} by {c.str_artists}':60} {'!!' if active else '  '} | "
            f'{start.isoformat()} to {end.isoformat()} '
            f'| {weeks:>3} wks | week {int((start - FIRST_DATE).days / 7) - 2:<3} '
            f'to {int((end - FIRST_DATE).days / 7) - 3 :<3}'
        )
    print('')


def top_album_song_weeks(uow: SongUOW, weeks: Optional[int]):
    units = [(album, album.song_charted_count(weeks)) for album in uow.albums]
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
    top = 20 if top is None else top
    units = [
        (album, len([entry for entry in album.entries if entry.place <= top]))
        for album in uow.albums
    ]
    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] > units[19][1]]

    print(
        f"Albums with most weeks {f'in the top {top}' if top else 'on chart'}:"
    )
    for album, weeks in units:
        place = len([i for i in units if i[1] > weeks]) + 1
        print(f'{place:>3} | {str(album):<50} | {weeks:<2} weeks')
    print('')


def get_song_units(
    song: Song, start: date, end: date
) -> tuple[Song, int, int]:
    return song, song.period_units(start, end), song.period_plays(start, end)


def top_songs_month(uow: SongUOW, start: date, end: date):
    with futures.ThreadPoolExecutor() as executor:
        units: list[tuple] = list(
            executor.map(
                functools.partial(get_song_units, start=start, end=end),
                (
                    song
                    for song in uow.songs
                    if song.period_points(start=start, end=end) > 0
                ),
            )
        )
    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] > units[19][1]]

    print(
        f'Bestselling songs between {start.isoformat()} and {end.isoformat()}.'
    )
    for song, unit, plays in units:
        place = len([i for i in units if i[1] > unit]) + 1
        print(
            f'{place:>3} | {str(song):<50} | {unit:<2} units | {plays:<2} plays'
        )
    print('')


def get_album_units(
    album: Album, start: date, end: date
) -> tuple[Album, int, int]:
    return (
        album,
        album.period_units(start, end),
        album.period_plays(start, end),
    )


def top_albums_month(uow: SongUOW, start: date, end: date):
    with futures.ThreadPoolExecutor() as executor:
        units: list[tuple] = list(
            executor.map(
                functools.partial(get_album_units, start=start, end=end),
                (
                    album
                    for album in uow.albums
                    if charted_between(album, start, end)
                ),
            )
        )
    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] > units[19][1]]

    print(
        f'Bestselling albums between {start.isoformat()} and {end.isoformat()}.'
    )
    for album, unit, plays in units:
        place = len([i for i in units if i[1] > unit]) + 1
        print(
            f'{place:>3} | {str(album):<50} | {unit:<2} units | {plays:<2} plays'
        )
    print('')


def all_number_one_weeks_album(uow: SongUOW):
    items = [
        (
            sum(
                weeks_top(song, top=1, variant=variant)
                for (variant, song) in album.songs
            )
            + weeks_top(album, top=1),
            album,
        )
        for album in uow.albums
    ]

    for weeks, album in sorted(
        filter(lambda g: g[0] > 9, items), key=itemgetter(0), reverse=True
    ):

        print(f'{weeks} {album}')
        album_weeks = weeks_top(album, top=1)
        if album_weeks > 0:
            print(f'  {album_weeks} album')
        for (variant, song) in album.songs:
            song_weeks = weeks_top(song, top=1, variant=variant)
            if song_weeks > 0:
                print(f'  {song_weeks} {song}')
        print('')


def display_all_songs(uow: SongUOW):
    all_songs = [song for song in uow.songs if song.units]   # >= 1000]
    list(map(lambda i: i._populate_listens(), all_songs))
    all_songs.sort(key=lambda i: i.units, reverse=True)
    for (count, song) in enumerate(all_songs):
        print(
            f'{count + 1:>4} | {song.title:<45} | {song.str_artists:<45} | peak: {song.peak:<2} '
            f'{(("(" + str(song.peakweeks) + ")") if (song.peak < 11 and song.peakweeks > 1) else " "):<4} '
            f'| weeks: {song.weeks:<2} | plays: {song.plays:<3} | {song.cert}'
        )


def _display_album_plays(album: Album):
    for song in album:
        song.update_plays()

    print('')
    print(f'{album!s} plays: {album.plays}')
    print('◆ combined songs:')

    for song in album:
        print(f'◆ {song!s}: {song.plays}')
        if len(song.ids) > 1:
            for bonus_id in song.ids:
                plays = spotistats.song_plays(bonus_id, adjusted=True)
                print(f'◇ {bonus_id}: {plays}')


def display_top_album_plays_infographic(uow: SongUOW, threshold: int):
    for album in uow.albums:
        if album.plays > threshold:
            _display_album_plays(album)


def album_first_year_months(
    uow: SongUOW, month_count: int = 12, threshold: int = 10_000
):
    """
    displays the first year monthly units for albums with at least `threshold` units.
    """

    for album in uow.albums:
        if album.units < threshold:
            continue

        months = [
            0
        ] * month_count   # we count months as all being 30 days for simplicity
        all_listens: dict[
            str, list[spotistats.Listen]
        ] = get_album_play_history(album)

        incomplete = False

        for (id, song) in album.songs:
            play_record = all_listens[id]
            date_counter = Counter(
                i.finished_playing.date() for i in play_record
            )

            play_record.sort(key=lambda i: i.finished_playing)
            start = play_record[0].finished_playing.date()
            cutoff = start + timedelta(days=30 * month_count)
            if cutoff > date.today():
                incomplete = True

            for day, plays in date_counter.items():
                if day >= cutoff:
                    continue
                if plays > MAX_ADJUSTED:
                    # filter plays so they cap out at 25 per day
                    plays = MAX_ADJUSTED
                months[(day - start).days // 30] += plays * 2

            for entry in song.entries:
                if entry.end >= cutoff:
                    continue
                if entry.variant in song.get_variant(id).ids:
                    months[(entry.end - start).days // 30] += 61 - entry.place

        print(
            f'{album} - first year monthly units {"!!" if incomplete else ""}'
        )
        print(months)


PLAYS_MILESTONES = [25, 50, 75] + list(range(100, 1500, 100))
CERT_UNITS = [100] + list(range(200, 6000, 200))
ALBUM_TOP = [1, 3, 5, 10, 15, None]
SONG_TOP = [1, 3, 5, 10, 20, 30, None]
SONG_WEEKS = [30, 20, 15, 10, 5, None]
CERTS = [SongCert.from_units(i) for i in CERT_UNITS]

if __name__ == '__main__':
    uow = SongUOW()

    # update_local_plays(uow, verbose=True)
    # display_top_album_plays_infographic(uow, 1_000)

    # album_first_year_months(uow, month_count=36)

    """
    for milestone in PLAYS_MILESTONES[::-1]:
        top_shortest_time_plays_milestones(uow, milestone)
 
    for milestone in MILESTONES[::-1]:
        top_albums_play_count(uow, milestone)

    top_shortest_time_units_milestones(uow, 2_000)
    top_shortest_time_units_milestones(uow, 4_000)

    for milestone in CERT_UNITS[::-1]:
        top_shortest_time_units_milestones(uow, milestone, cutoff=10)

    top_collection_consecutive_weeks_infographic(uow.songs)
    top_collection_consecutive_weeks_infographic(uow.albums)
    """

    update_local_plays(uow, verbose=True)

    top_shortest_time_units_milestones_infographic(uow, 2_000)
    print('')
    
    top_upcoming_projected_milestone(uow, 2_000, 400, 40)
    print('')
    for milestone in range(4_000, 14_000, 2_000):
        top_upcoming_projected_milestone(uow, milestone, 1_000)
        print('')
    
    """
    all_number_one_weeks_album(uow)

    for milestone in range(2_000, 12_000, 2_000):
        top_shortest_time_units_milestones_infographic(uow, milestone)
        print('')

    for milestone in (5_000, 10_000, 20_000, 30_000, 40_000, 50_000, 60_000, 70_000):
        top_shortest_time_album_units_milestones_infographic(uow, milestone)
        print('')

    for cert in CERTS[::-1]:
        top_albums_cert_count(uow, cert)

    top_albums_month(uow, date.fromisoformat('2021-01-01'), date.fromisoformat('2022-01-01'))
    top_albums_month(uow, date.fromisoformat('2022-01-01'), date.fromisoformat('2023-01-01'))
    top_albums_month(uow, date.fromisoformat('2023-01-01'), date.fromisoformat('2024-01-01'))
    top_albums_month(uow, date.fromisoformat('2024-01-01'), date.fromisoformat('2025-01-01'))
    top_albums_month(uow, date.fromisoformat('2025-01-01'), date.fromisoformat('2026-01-01'))

    for top in ALBUM_TOP:
        top_albums_consecutive_weeks(uow, top)
        # top_albums_weeks(uow, top)

    for top in SONG_TOP:
        # top_album_hits(uow, top)
        top_song_consecutive_weeks(uow, top)

    for weeks in SONG_WEEKS:
        top_album_song_weeks(uow, weeks)
    
    top_song_consecutive_weeks(uow, top=5)

    top_albums_month(uow, date(2023, 11, 1), date(2023, 12, 1))
    
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
