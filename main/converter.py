import json
import yaml
import requests

from storage import SongUOW
from spreadsheet import Spreadsheet
from config import LEVBOARD_SHEET

from model.spotistats import _get_address
data = _get_address('http://api.stats.fm/api/v1/users/lev/top/albums?limit=1000')

name_to_id = {}
for info in data.json()['items']:
    position = info['position']
    name = info['album']['name']
    number = info['album']['id']
    print(f"({position}) {name}: {number}")

    name_to_id[name] = number



name_to_image = {}
for name, type, _, _, link in Spreadsheet(LEVBOARD_SHEET).get_range("'Album Info'!A2:E")['values']:
    if type == "Album":
        name_to_image[name] = link

print(name_to_image)

with open('data/album_template.yml', 'r') as f:
    info: dict = yaml.load(f)
    print(info)

loaded_albums = [item['title'] for item in info.values()]

uow = SongUOW()
for album in uow.albums:
    print(album)
    if (album.title in name_to_id) and (album.title not in loaded_albums):
        album_object = {
            'title': album.title,
            'artists': album.artists,
            'versions': [{
                'name': 'standard',
                'image': name_to_image[album.title] if album.title in name_to_image else'MISSING',
                'songs': [song.main_id for song in album]
                }
            ],
        }
        print(album_object)
        info[name_to_id[album.title]] = album_object

    else: print(f"{album} stats fm id not found")

print(info)

with open('data/albums.yml', 'w') as f:
    yaml.dump(info, f)