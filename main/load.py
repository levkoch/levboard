import itertools
from concurrent import futures

from config import LEVBOARD_SHEET
from model import Album, Song
from spreadsheet import Spreadsheet
from storage import SongUOW


def _create_new_song(ids: list[str], name: str) -> Song:
    new_song = Song(song_id=ids[0], song_name=name)
    if len(ids) > 1:
        for alt_id in ids[1:]:
            new_song.add_alt(alt_id)
    return new_song


def _add_song(song_name: str, str_ids: str, uow: SongUOW) -> Song:
    """adds a song into the uow."""
    # split by comma. not all songs will have multiple ids but we
    # don't care, because it will return a list regardless.
    ids = str_ids.split(', ')

    song = uow.songs.get(ids[0])
    if song is None:
        return _create_new_song(ids, song_name)
    return song


def load_songs(uow: SongUOW, verbose: bool = False):
    """
    Loads the songs in the spreadsheet to the file

    """

    sheet = Spreadsheet(LEVBOARD_SHEET)

    request = sheet.get_range('Song Info!A2:B')
    songs: list[list] = [i for i in request.get('values') if i[0]]

    if verbose:
        print(f'{len(songs)} items found.')

    with futures.ThreadPoolExecutor() as executor:
        to_do: list[futures.Future] = []

        for song_name, str_ids in songs:
            future = executor.submit(_add_song, song_name, str_ids, uow)
            to_do.append(future)

        for count, future in enumerate(futures.as_completed(to_do), 1):
            song: Song = future.result()
            uow.songs.add(song)
            percentage = count / len(songs) * 100
            if verbose:
                print(
                    f'{count:>5} of {len(songs)} ({percentage:.2f}%): {song} ({song.id})'
                )

    if verbose:
        print('Completed process. Saving all songs to database.')
    uow.commit()


def load_albums(uow: SongUOW, verbose: bool = False):
    """loads albums from the spreadsheet into the songuow provided."""

    sheet = Spreadsheet(LEVBOARD_SHEET)
    request = sheet.get_range('Albums!A1:G')
    info: list[list] = request.get('values')

    print(f'{len(info)} rows found.')

    row: list[str] = info.pop(0)
    album_count = itertools.count()

    while info:
        album_name: str = row[0]
        row = info.pop(0)

        if not row[0]:
            # if album has bonus row for weeks and peak
            row = info.pop(0)

        album_artists: str = row[0]  # will be parsed later if multiple artists
        row = info.pop(0)  # this is the headers row in the spreadsheet

        album = Album(album_name.strip(), album_artists.strip())
        uow.albums.add(album)
        if verbose:
            print(f'\r{len(info)} rows left to process.', flush=True)
            print(f'\r({next(album_count)}) Processing {album}', flush=True)

        row = info.pop(0)
        try:
            while row:
                song_id = row[6]
                if ', ' in song_id:
                    song_id = song_id.split(', ')[0]

                song = uow.songs.get(song_id)
                if song is None:
                    raise ValueError('song not found')
                album.add_song(song)
                row = info.pop(0)
                # will get new song row or the blank row
                # at the end, causing the while loop to end

        except IndexError:
            break  # from while info loop

        # get next album title row
        row = info.pop(0)

    uow.commit()


if __name__ == '__main__':
    uow = SongUOW()
    load_songs(uow, verbose=True)
    load_albums(uow, verbose=True)
