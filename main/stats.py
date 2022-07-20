import functools

from datetime import timedelta, datetime
from concurrent import futures

from storage import SongUOW
from model import SongCert, Song, spotistats


uow = SongUOW()


def time_to_plays(song: Song, plays: int) -> timedelta:
    if song.plays < plays:
        raise ValueError('not enough plays for song')

    play_record = spotistats.song_play_history(song.id)

    play_record.sort(key=lambda i: i['finished_playing'])

    first_play: datetime = play_record[0]['finished_playing']
    wanted_play: datetime = play_record[plays - 1]['finished_playing']

    time = wanted_play - first_play

    # print(f'{song.name} took {time.days} days to reach {plays} plays')

    return (song, time)


def top_shortest_time_plays_milestones(uow: SongUOW, plays: int):
    contenders = (
        song for song in uow.songs if song.plays >= plays and not song.alt_ids
    )

    with futures.ThreadPoolExecutor() as executor:
        mapped = executor.map(
            functools.partial(time_to_plays, plays=plays), contenders
        )

    units = [i for i in mapped if i[1].days > 1]
    units.sort(key=lambda i: i[1])
    if len(units) > 16:
        units = [i for i in units if i[1] <= units[19][1]]
    print(f'Fastest songs to reach {plays} plays:')
    for (song, time) in units:
        place = len([unit for unit in units if unit[1].days < time.days]) + 1
        print(f'{place:<2} | {song:<45} | {time.days} days')


MILESTONES = [25, 50, 75, 100, 150, 200, 250, 300, 350, 400]

if __name__ == '__main__':
    uow = SongUOW()

    for milestone in MILESTONES[::-1]:
        top_shortest_time_plays_milestones(uow, milestone)
        print('')

    quit()

certs = (
    SongCert.from_symbol(i)
    for i in (
        'G',
        'P',
        '2xP',
        '3xP',
        '4xP',
        '5xP',
        '6xP',
        '7xP',
        '8xP',
        '9xP',
        '10xD',
    )
)

for cert in certs:
    with uow:
        units = []
        for album_name in uow.albums.list():
            album = uow.albums.get(album_name)
            units.append((album, album.get_certs(cert)))

    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] >= units[16][1] and i[1] > 1]
    print(f'Albums with most songs {cert:F} or higher:')
    for (count, (album, songs)) in enumerate(units, 1):
        print(
            f"{count:>2} | {f'{album.title} by {album.str_artists}':<55} | {songs:>2} songs"
        )

for top in (1, 3, 5, 10, 15, None):
    with uow:
        units = []
        for album_name in uow.albums.list():
            album = uow.albums.get(album_name)
            units.append((album, album.get_conweeks(top)))

    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] >= units[16][1] and i[1] > 1]
    print(
        f"Albums with most consecutive weeks {f'in the top {top}' if top else 'on chart'}:"
    )
    for (count, (album, weeks)) in enumerate(units):
        print(
            f"{count + 1:>2} | {f'{album.title} by {album.str_artists}':<55} | {weeks:>2} wks"
        )


for top in (1, 3, 5, 10, 20, 30, None):
    units = []
    for album_title in uow.albums.list():
        album = uow.albums.get(album_title)
        units.append((album, album.get_weeks(top)))
    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] > units[16][1]]

    print(
        f"Albums with most weeks {f'in the top {top}' if top else 'on chart'}:"
    )
    for album, weeks in units:
        place = len([i for i in units if i[1] > weeks]) + 1
        print(f'{place:>3} | {str(album):<50} | {weeks:<3} weeks')
    print('')

for top in (1, 3, 5, 10, 20, 30, None):
    units = []
    for album_title in uow.albums.list():
        album = uow.albums.get(album_title)
        units.append((album, album.get_hits(top)))
    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] > units[16][1]]

    print(
        f"Albums with most songs {f'peaking in the top {top}' if top else 'charted'}:"
    )
    for album, songs in units:
        place = len([i for i in units if i[1] > songs]) + 1
        print(f'{place:>3} | {str(album):<50} | {songs:<3} songs')
    print('')

for weeks in (30, 20, 15, 10, 5, None):
    units = []
    for album_title in uow.albums.list():
        album = uow.albums.get(album_title)
        units.append((album, album.get_charted(weeks)))
    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] > units[20][1]]

    print(
        f"Albums with most songs {f'charting for {weeks} weeks or more' if weeks else 'charted'}:"
    )
    for album, songs in units:
        place = len([i for i in units if i[1] > songs]) + 1
        print(f'{place:>3} | {str(album):<50} | {songs:<2} songs')
    print('')

for top in (None, 30, 20, 15, 10, 5, 3, 1):
    with uow:
        units = []
        for song_id in uow.songs.list():
            song = uow.songs.get(song_id)
            units.append((song, song.get_conweeks(top)))

    units.sort(key=lambda i: i[1], reverse=True)
    units = [i for i in units if i[1] >= units[16][1] and i[1] > 1]
    print(
        f"Songs with most consecutive weeks {f'in the top {top}' if top else 'on chart'}:"
    )
    for (count, (song, weeks)) in enumerate(units):
        print(
            f"{count + 1:>2} | {f'{song.name} by {song.str_artists}':<55} | {weeks:>2} wks"
        )

"""
with uow:
    all_songs = [uow.songs.get(i) for i in uow.songs.list()]
    all_songs.sort(key=lambda i: i.units, reverse=True)
    for (count, song) in enumerate(all_songs):
        print(
            f"{count + 1:>4} | {song.name:<45} | {', '.join(song.artists):<45} | peak: {song.peak:<2} "
            f'{(("(" + str(song.peakweeks) + ")") if (song.peak < 11 and song.peakweeks > 1) else " "):<4} '
            f"| weeks: {song.weeks:<2} | plays: {song.plays:<3} | {song.cert}"
        )
"""
