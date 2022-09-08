from spreadsheet import Spreadsheet
from model import Album
from storage import SongUOW
from config import LEVBOARD_SHEET

uow = SongUOW()
sheet = Spreadsheet(LEVBOARD_SHEET)
request = sheet.get_range('Albums!A1:G2000')
info: list[list] = request.get('values')

print(f'{len(info)} rows found.')

row: list[str] = info.pop(0)
album_count = 0
while info:
    album_count += 1

    album_name: str = row[0]
    row = info.pop(0)
    album_artists: str = row[0]  # will be parsed later if multiple artists
    row = info.pop(0)  # this is the headers row in the spreadsheet

    album = Album(album_name.strip(), album_artists.strip())
    uow.albums.add(album)
    print('')
    print(f'{len(info)} rows left to process.')
    print('')
    print(f'({album_count}) Processing {album}')

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
            print(f'- Adding {song}')

            row = info.pop(0)
            # will get new song row or the blank row
            # at the end, causing the while loop to end

    except IndexError:
        break  # from while info loop

    # get next album title row
    row = info.pop(0)

uow.commit()
