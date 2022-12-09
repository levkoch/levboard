import itertools
from spreadsheet import Spreadsheet

from storage import SongUOW
from config import LEVBOARD_SHEET

uow = SongUOW()
sheet = Spreadsheet(LEVBOARD_SHEET)

request = sheet.get_range('Song Info!A2:B2000')
song_ids: list[list] = [i[1] for i in request.get('values') if i[0]]

print(len(song_ids), 'items found')

all_ids: list[str] = (','.join(itertools.chain.from_iterable(song_ids))).split(
    ','
)

missing_songs = [['Name', 'Ids', 'Artists']]

for song in uow.songs:
    if song.id in all_ids:
        continue

    ids = itertools.chain([song.id], song.alt_ids)

    missing_songs.append([song.name, ', '.join(ids), ', '.join(song.artists)])

range = f'MISSING_SONGS!A1:D{len(missing_songs) + 1}'
sheet.update_range(range, missing_songs)
