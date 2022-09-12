from concurrent import futures
import itertools

from spreadsheet import Spreadsheet
from model import Song
from config import LEVBOARD_SHEET


sheet = Spreadsheet(LEVBOARD_SHEET)
request = sheet.get_range('Song Info!A2:D2000')
songs: list[list] = request.get('values')
songs = [i for i in songs if i[0]]
print(f'{len(songs)} items found.')

final_songs: list[list] = []


def create_song(song_id: str, song_name: str) -> tuple[Song, int]:
    if ',' in song_id:
        song = Song(song_id.split(',')[0], song_name)
        for alt in song_id.split(',')[1:]:
            song.add_alt(alt)

    else:
        song = Song(song_id, song_name)

    return update_song_plays(song)


def update_song_plays(song: Song) -> tuple[Song, int]:
    song.update_plays(adjusted=True)
    return (song, song.plays)


with futures.ThreadPoolExecutor() as executor:
    to_do: list[futures.Future] = []

    for sheet_song in songs:
        song_name, song_id, _, _ = sheet_song
        future = executor.submit(create_song, song_id, song_name)
        to_do.append(future)

    for count, future in enumerate(futures.as_completed(to_do), 1):
        song: Song
        plays: int
        song, plays = future.result()

        song_ids = itertools.chain([song.id], song.alt_ids)
        final_songs.append(
            [
                "'" + song.name if song.name.isnumeric() else song.name,
                ','.join(song_ids),
                ', '.join(song.artists),
                plays,
            ]
        )
        print(f'({count}) updated {song} -> {plays} plays')

sheet.update_range(f'Song Info!A2:D{len(final_songs) + 1}', final_songs)
