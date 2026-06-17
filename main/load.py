import itertools

from concurrent import futures
from typing import Iterable, Optional

from config import LEVBOARD_SHEET, GROUPBOARD_SHEET, ALBUM_FILE, SONG_FILE
from model import Album, Song, Variant
from spreadsheet import Spreadsheet
from storage import SongUOW
from localprocess import process_local_streams


def _create_new_song(ids: list[str], name: str) -> Song:
    new_song = Song(song_id=ids[0], song_title=name)
    if len(ids) > 1:
        for alt_id in ids[1:]:
            new_song.add_alt(alt_id)
    return new_song


def _add_song(song_title: str, str_ids: str, uow: SongUOW) -> Song:
    """adds a song into the uow."""
    # split by comma. not all songs will have multiple ids but we
    # don't care, because it will return a list regardless.
    ids = str_ids.split(', ')

    if any(uow.songs.get(id) is None for id in ids):
        return _create_new_song(ids, song_title)
    return uow.songs.get(ids[0])


def load_linked_songs(uow: SongUOW, sheet_link: str, verbose: bool = False):
    """
    Loads the songs with variant markers from the spreadsheet to local storage
    """

    sheet = Spreadsheet(sheet_link)
    values = sheet.get_range('Songs!A2:F').get('values')
    songs: list[list[str]] = [i for i in values if i[0]]

    counter = itertools.count(start=2)

    # prime first song
    # missing fields are variant indicator, sheet id, and spotify uris
    song_title, _, str_ids, _, spotify_uris, str_artists = songs[0]
    ids = str_ids.split(', ')
    prev_id: str = ids[0]
    variant = Variant(
        main_id=ids[0],
        title=song_title,
        ids=set(ids),
        spotify_uris=set(spotify_uris.split(', ')),
        artists=str_artists.split(', '),
    )
    variant_hold = [variant]

    if verbose:
        print(f'Loading all songs. {len(songs)} rows found.')

    # first song already primed so we skip it here
    for song_title, demarcator, str_ids, _, spotify_uris, str_artists in songs[
        1:
    ]:
        is_variant = demarcator == 'X'

        if not is_variant:
            song = Song.from_variants(main_id=prev_id, variants=variant_hold)
            uow.songs.add(song)
            prev_id = str_ids.split(', ')[0]
            variant_hold.clear()

        ids = str_ids.split(', ')
        variant = Variant(
            main_id=ids[0],
            title=song_title,
            ids=set(ids),
            spotify_uris=set(spotify_uris.split(', ')),
            artists=str_artists.split(', '),
        )
        variant_hold.append(variant)

        count = next(counter)
        percentage = count / len(songs) * 100

        if verbose:
            display = (
                f'\r <> [{count:04d}/{len(songs)}] ({percentage:.2f}%):'
                + (' # ' if is_variant else '   ')
                + f'{song_title} ({ids[0]})'
            )

            print(
                display,
                end=' ' * max(100 - len(display), 1),
                flush=True,
            )

    # process final song
    song = Song.from_variants(main_id=prev_id, variants=variant_hold)
    uow.songs.add(song)
    uow.commit()

    if verbose:
        print('\nAll songs saved.')


def load_songs(uow: SongUOW, sheet_link: str, verbose: bool = False):
    """
    !! DEPRECATED !!
    Loads the songs in the spreadsheet to the file, before we had variants.
    """

    sheet = Spreadsheet(sheet_link)

    values = sheet.get_range('Song Info!A2:B').get('values')
    if values is None:
        raise IndexError("shouldn't happen but who knows")
    songs: list[list] = [i for i in values if i[0]]

    if verbose:
        print(f'{len(songs)} items found.')

    with futures.ThreadPoolExecutor() as executor:
        to_do: list[futures.Future] = []

        for song_title, str_ids in songs:
            future = executor.submit(_add_song, song_title, str_ids, uow)
            to_do.append(future)

        for count, future in enumerate(futures.as_completed(to_do), 1):
            song: Song = future.result()
            uow.songs.add(song)
            percentage = count / len(songs) * 100
            if verbose:
                print(
                    f'{count:>5} of {len(songs)} ({percentage:.2f}%): {song} ({song.main_id})'
                )

    uow.commit()

    if verbose:
        print('Completed process. Saving all songs to database.')


def load_albums(uow: SongUOW, sheet_link: str, verbose: bool = False):
    """loads albums from the spreadsheet into the songuow provided."""

    print()
    sheet = Spreadsheet(sheet_link)
    values: Optional[list[list]] = sheet.get_range('Albums!A1:G').get('values')
    if values is None:
        raise IndexError("shouldn't happen but maybe range error")

    print(f'Loading all albums. {len(values)} rows found.')

    row: list[str] = values.pop(0)
    album_count = itertools.count(start=1)

    while values:
        album_name: str = row[0]
        row = values.pop(0)

        if not row[0]:
            # if album has bonus row for weeks and peak
            row = values.pop(0)

        album_artists: str = row[0]  # will be parsed later if multiple artists
        row = values.pop(0)  # this is the headers row in the spreadsheet

        album = Album(album_name.strip(), album_artists.strip())
        uow.albums.add(album)
        if verbose:
            print(
                f'\r<> [{next(album_count):03d}] {album}',
                end=' ' * 50,
                flush=True,
            )

        row = values.pop(0)
        try:
            while row:
                song_id = row[6].split(', ')[0]

                song = uow.songs.get(song_id)
                if song is None:
                    raise ValueError('song not found')
                album.add_song(song, song_id)
                row = values.pop(0)
                # will get new song row or the blank row
                # at the end, causing the while loop to end

        except IndexError:
            break  # from while values loop

        # get next album title row
        row = values.pop(0)

    print('\n All albums loaded.')
    uow.commit()


def blank_storage_files(files: Iterable[str]):
    """overwrites the given files with a blank json object."""

    for file in files:
        with open(file, 'w') as f:
            f.write(r'{}')


if __name__ == '__main__':

    blank_storage_files([ALBUM_FILE, SONG_FILE])
    process_local_streams()
    print('')

    uow = SongUOW()
    load_linked_songs(uow, LEVBOARD_SHEET, verbose=True)
    load_albums(uow, LEVBOARD_SHEET, verbose=True)

    """
    group_uow = SongUOW(
        song_file='../data/groupsongs.json',
        album_file='../data/groupalbums.json',
    )
    load_songs(group_uow, GROUPBOARD_SHEET, verbose=True)
    load_albums(group_uow, GROUPBOARD_SHEET, verbose=True)
    """
