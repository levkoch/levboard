from extras.spreadsheet import Spreadsheet
from main.model.song import Song
from main.storage import SongUOW

uow = SongUOW()
sheet = Spreadsheet('1_KNcoT92nfgQCRqLH7Iz4ZSxy9hxCd8ll0Hzn9hscqk')
request = sheet.get_range('Song Info!A2:B2000')
songs: list[list] = [i for i in request.get('values') if i[0]]

print(f'{len(songs)} items found.')

final_songs: list[list] = []

for count, sheet_song in enumerate(songs):
    song_name: str
    song_ids: str
    song_name, song_ids = sheet_song

    percentage = (count + 1) / len(songs) * 100

    if ', ' in song_ids:
        ids = song_ids.split(', ')
    else:
        ids = [song_ids]

    print(
        f'{count + 1:>5} of {len(songs)} ({percentage:.2f}%): {song_name} ({ids[0]})'
    )

    with uow:
        if ids[0] not in uow.songs.list():
            new_song: Song = Song(song_id=ids[0], song_name=song_name)
            if len(ids) > 1:
                for alt_id in ids[1:]:
                    new_song.add_alt(alt_id)
            uow.songs.add(new_song)

            uow.commit()
