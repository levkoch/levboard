from collections import defaultdict
import itertools
from concurrent import futures
from typing import Optional

from config import LEVBOARD_SHEET, GROUPBOARD_SHEET
from model import Album, Song
from spreadsheet import Spreadsheet
from storage import SongUOW


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
    Loads the linked songs in the spreadsheet to the file
    """

    sheet = Spreadsheet(sheet_link)

    values = sheet.get_range('Songs!A2:C').get('values')
    songs: list[list[str]] = [i for i in values if i[0]]

    prev_id: str = songs[0][1].split(', ')[0]
    links: dict[str, list] = defaultdict(list)

    if verbose:
        print(f'{len(songs)} items found.')

    with futures.ThreadPoolExecutor() as executor:
        to_do: list[futures.Future] = []

        for song_title, is_variant, str_ids in songs:
            if is_variant == 'X':
                links[prev_id].append(str_ids.split(', ')[0])
            else:
                prev_id = str_ids.split(', ')[0]

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

    if verbose:
        print('binding songs together')

    for (main_id, variant_ids) in links.items():
        main_song = uow.songs.get(main_id)
        for variant_id in variant_ids:
            main_song.add_variant(uow.songs.get(variant_id))

    if verbose:
        print('Completed process. Saving all songs to database.')
    uow.commit()


def load_songs(uow: SongUOW, sheet_link: str, verbose: bool = False):
    """
    Loads the songs in the spreadsheet to the file
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

    if verbose:
        print('Completed process. Saving all songs to database.')
    uow.commit()


def load_albums(uow: SongUOW, sheet_link: str, verbose: bool = False):
    """loads albums from the spreadsheet into the songuow provided."""

    sheet = Spreadsheet(sheet_link)
    values: Optional[list[list]] = sheet.get_range('Albums!A1:G').get(
        'values'
    )
    if values is None:
        raise IndexError("shouldn't happen but maybe range error")

    print(f'{len(values)} rows found.')

    row: list[str] = values.pop(0)
    album_count = itertools.count()

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
            print(f'\r{len(values)} rows left to process.', flush=True)
            print(f'\r({next(album_count)}) Processing {album}', flush=True)

        row = values.pop(0)
        try:
            while row:
                song_id = row[6]
                if ', ' in song_id:
                    song_id = song_id.split(', ')[0]

                song = uow.songs.get(song_id)
                if song is None:
                    raise ValueError('song not found')
                album.add_song(song)
                row = values.pop(0)
                # will get new song row or the blank row
                # at the end, causing the while loop to end

        except IndexError:
            break  # from while values loop

        # get next album title row
        row = values.pop(0)

    uow.commit()


if __name__ == '__main__':
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
