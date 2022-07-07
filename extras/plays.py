from spreadsheet import Spreadsheet
from main import Song
from storage import SongUOW

SONGS_FILE = 'C:/Users/levpo/Documents/GitHub/lev-bot/song/songs.json'

sheet = Spreadsheet('1_KNcoT92nfgQCRqLH7Iz4ZSxy9hxCd8ll0Hzn9hscqk')
uow = SongUOW()
request = sheet.get_range('Song Info!A2:D1000')
songs: list[list] = request.get('values')
songs = [i for i in songs if i[0]]
print(f'{len(songs)} items found.')

final_songs: list[list] = []

for count, sheet_song in enumerate(songs):
    song_name, song_id, song_albums, _ = sheet_song

    percentage = (count + 1) / len(songs) * 100

    print(
        f'{count + 1:>5} of {len(songs)} ({percentage:.2f}%): {song_name} ({song_id})'
    )

    fount = False

    with uow:
        if song_id in uow.songs.list():
            new_song: Song = uow.songs.get(song_id)
            # new_song.update_plays()

        else:
            new_song: Song = Song(song_name, song_id)
            new_song.update_plays()
            uow.songs.add(new_song)

        uow.commit()

    final_songs.append(
        [
            new_song.name,
            new_song.id,
            ', '.join(new_song.artists),
            new_song.plays,
        ]
    )

sheet_song_ids = [i[1] for i in songs]
with uow:
    missing = [i for i in uow.songs.list() if i not in sheet_song_ids]
    print(missing)
    for missing_id in missing:
        new_song = uow.songs.get(missing_id)
        new_song.update_plays()

        final_songs.append(
            [
                new_song.name,
                new_song.id,
                ', '.join(new_song.artists),
                new_song.plays,
            ]
        )
    uow.commit()

sheet.update_range(f'Song Info!A2:D{len(final_songs) + 1}', final_songs)
