import json
import yaml
import requests

from storage import SongUOW
from spreadsheet import Spreadsheet
from config import LEVBOARD_SHEET

from model.spotistats import _get_address, album_tracks

data = _get_address(
    'http://api.stats.fm/api/v1/users/lev/top/albums?limit=1000'
)

name_to_id: dict[str, int] = {}
for info in data.json()['items']:
    position = info['position']
    name = info['album']['name']
    number = info['album']['id']
    # print(f'({position}) {name}: {number}')

    name_to_id[name] = number


name_to_image = {}
sheet = Spreadsheet(LEVBOARD_SHEET)
for name, type, _, _, link in sheet.get_range("'Album Info'!A2:E")['values']:
    if type == 'Album':
        name_to_image[name] = link


with open('data/albums.yml', 'r') as f:
    info: dict[int, dict] = yaml.safe_load(f)

loaded_albums = [
    item['title'] for item in info.values() if item.get('complete') is not None
]

print(sorted(loaded_albums))
quit()

uow = SongUOW()
for count, album in enumerate(uow.albums, start = 1):
    if album.title in loaded_albums: 
        print(f'({count}) already have loaded {album}')
        continue

    if album.title in name_to_id:
        album_object = {
            'title': album.title,
            'artists': album.artists,
            'versions': [
                {
                    'name': 'standard',
                    'image': name_to_image[album.title]
                    if album.title in name_to_image
                    else 'MISSING',
                    'songs': [song.main_id for song in album],
                }
            ],
        }
        info[name_to_id[album.title]] = album_object
        print(f'({count}) sucessfully loaded {album}')

    else:
        print(f'\n{album} stats fm id not found')
     
        title = input(f'Select an album to merge with {album}: ')
        if not title: continue
        while True:
            candidates = [a for a in name_to_id.keys() if a.startswith(title)]
            if not candidates or (len(candidates) == len(name_to_id)):
                print("no matching albums found. enter to skip.")
                title = input(f'Select an album to merge with {album}: ')
                if not title: break
            
            else:
                options = {}
                print("\nHere are the options:")
                for num, a in enumerate(candidates, start=1):
                    options[num] = a
                    print(f'({num}) {a}')
                
                selection = int(input("\nChoose a number: "))
                if selection in range(1, len(candidates) + 1):
                    break

        spotify_title = options[selection]
        statsfm_id = name_to_id[spotify_title]
        album_object = {
            'title': album.title,
            'artists': album.artists,
            'versions': [
                {
                    'name': 'standard',
                    'image': name_to_image[album.title]
                    if album.title in name_to_image
                    else 'MISSING',
                    'songs': [song.main_id for song in album],
                }
            ],
        }
        info[statsfm_id] = album_object
        print(f'({count}) sucessfully loaded {album}')

    if count % 10 == 0:
        print('saving albums to file')
        with open('data/albums.yml', 'w') as f:
            yaml.dump(info, f)


for album_title, album_number in name_to_id.values():
    if album_number in info: continue
    print(f'{album_title} ({album_number}) not found')


with open('data/albums.yml', 'w') as f:
    yaml.dump(info, f)
