from datetime import date

from config import LEVBOARD_SHEET
from spreadsheet import Spreadsheet
from storage import SongUOW

sheet = Spreadsheet(LEVBOARD_SHEET)
r = "'Year-End'!B106:B135"
songs = sheet.get_range(r).get('values')
uow = SongUOW()
"""
for [song_name] in songs:
    song = uow.songs.get_by_name(song_name)
    print(song, song.period_plays(
        date(2021, 1, 1), date(2022, 1, 1))
    )
"""
for album in uow.albums:
    if 'Charli XCX' in album.artists:
        print(album, album.peak)
