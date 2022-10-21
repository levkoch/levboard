from concurrent import futures

from spreadsheet import Spreadsheet
from model import Song
from storage import SongUOW
from config import LEVBOARD_SHEET, SONG_FILE


def create_new_song(ids: list[str], name: str) -> Song:
    new_song = Song(song_id=ids[0], song_name=name)
    if len(ids) > 1:
        for alt_id in ids[1:]:
            new_song.add_alt(alt_id)
    return new_song


def add_song(song_name: str, str_ids: str, uow: SongUOW) -> Song:
    if ', ' in str_ids:
        ids = str_ids.split(', ')
    else:
        ids = [str_ids]

    if ids[0] not in uow.songs.list():
        return create_new_song(ids, song_name)
    return uow.songs.get(ids[0])


def load_songs(file=SONG_FILE, verbose=False):
    """
    Loads the songs in the spreadsheet to the file

    """

    uow = SongUOW(song_file=file)
    sheet = Spreadsheet(LEVBOARD_SHEET)

    request = sheet.get_range('Song Info!A2:B2000')
    songs: list[list] = [i for i in request.get('values') if i[0]]

    if verbose:
        print(f'{len(songs)} items found.')

    with futures.ThreadPoolExecutor() as executor:
        to_do: list[futures.Future] = []

        for song_name, str_ids in songs:
            future = executor.submit(add_song, song_name, str_ids, uow)
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


if __name__ == '__main__':
    load_songs(verbose=True)
