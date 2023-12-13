from concurrent import futures
from datetime import date
import json
import yaml

from operator import itemgetter
from typing import Literal

from config import LEVBOARD_SHEET
from main import ask_new_song
from model import Song
from model.spotistats import (
    _get_address,
    album_tracks,
    artist_tracks,
    song_info,
    top_artists,
    songs_week,
)
from storage import SongUOW
from spreadsheet import Spreadsheet

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


def _load_images(image_type: Literal['Album', 'Single']) -> dict[str, str]:
    name_to_image: dict[str, str] = {}
    sheet = Spreadsheet(LEVBOARD_SHEET)
    for name, type, _, _, link in sheet.get_range("'Album Info'!A2:E")[
        'values'
    ]:
        if type == image_type:
            name_to_image[name] = link
    return name_to_image


def load_album_images():
    return _load_images('Album')


def load_song_images():
    return _load_images('Single')


def load_albums() -> dict[str, dict]:
    with open('data/albums.yml', 'r') as f:
        return yaml.safe_load(f)


def load_songs() -> dict[str, dict]:
    with open('data/songs.yml', 'r') as f:
        return yaml.safe_load(f)


def save_albums(data: dict[str, dict]) -> None:
    with open('data/albums.yml', 'w') as f:
        yaml.dump(data, f)


def save_songs(data: dict[str, dict]) -> None:
    with open('data/songs.yml', 'w') as f:
        yaml.dump(data, f)


def alphabetize_albums():
    info = load_albums()

    items = list(info.items())
    items.sort(key=lambda i: i[1]['title'].lower())
    thing = {str(album_id): album_item for album_id, album_item in items}

    save_albums(thing)


def save_albums_from_uow():
    name_to_image = load_album_images()
    info = load_albums()

    loaded_albums = [
        item['title']
        for item in info.values()
        if item.get('complete') is not None
    ]
    uow = SongUOW()
    for count, album in enumerate(uow.albums, start=1):
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
            if not title:
                continue
            while True:
                candidates = [
                    a for a in name_to_id.keys() if a.startswith(title)
                ]
                if not candidates or (len(candidates) == len(name_to_id)):
                    print('no matching albums found. enter to skip.')
                    title = input(f'Select an album to merge with {album}: ')
                    if not title:
                        break

                else:
                    options = {}
                    print('\nHere are the options:')
                    for num, a in enumerate(candidates, start=1):
                        options[num] = a
                        print(f'({num}) {a}')

                    selection = int(input('\nChoose a number: '))
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
        if album_number in info:
            continue
        print(f'{album_title} ({album_number}) not found')

    save_albums(info)


def save_songs_from_uow(uow: SongUOW):
    song_schemas = load_songs()   # what we currently have saved
    name_to_image = load_song_images()

    uow_songs_missing_ids = []

    total_songs = len(uow.songs.list())

    for count, song in enumerate(uow.songs, start=1):
        percentage = count / total_songs * 100
        print(f'{count} of {total_songs} ({percentage:.2f}%) loading {song}')

        if song.main_id in song_schemas:
            saved_song = song_schemas[song.main_id]
            saved_ids = set(saved_song['ids'])
            if song.ids == saved_ids:
                continue
            # if song.ids is a subset of saved_ids
            if (song.ids | saved_ids) == saved_ids:
                uow_songs_missing_ids.append(song)
                continue

        song_item = {
            'name': song.title,
            'artists': song.artists,
            'ids': list(song.ids),
            'standard': song.main_id,
            'image': 'MISSING'
            if song.title not in name_to_image
            else name_to_image[song.title],
        }

        if len(song.ids) > 1:
            song_item['versions'] = []

        for id in (id for id in song.ids if id != song.main_id):
            id_info = song_info(id)
            song_item['versions'].append(
                {
                    'id': id,
                    'name': id_info['name'],
                    'artists': [i['name'] for i in id_info['artists']],
                    'type': 'alternate'
                    if {i['name'] for i in id_info['artists']}
                    == set(song.artists)
                    else 'remix',
                }
            )

        song_schemas[song.main_id] = song_item

    print('process completed :)')
    save_songs(song_schemas)

    print("UOW missing id's for:")
    for song in uow_songs_missing_ids:
        print(song)


def save_songs_from_artist_to_uow(uow: SongUOW, artist: str):
    artist_songs = artist_tracks(artist)
    for count, song_id in enumerate(artist_songs, start=1):
        percentage = count / len(artist_songs) * 100
        if song_id in uow.songs.list():
            print(
                f'{count} of {len(artist_songs)} ({percentage:.2f}%) already have {uow.songs.get(song_id)} loaded'
            )
        else:
            song = ask_new_song(uow, song_id)
            if song is None:
                print('-- Finishing session')
                print('-- Saving songs to database.')
                uow.commit()
                return
            uow.songs.add(song)
            print(
                f'{count} of {len(artist_songs)} ({percentage:.2f}%) sucessfully loaded {song}'
            )
        if count % 40 == 0:
            print('-- Saving songs to database.')
            uow.commit()

    uow.commit()


def _load_song_from_ids(ids: set[str], name: str) -> Song:
    listened_ids = iter(ids)
    song = Song(next(listened_ids), name)
    for remaining_id in listened_ids:
        song.add_alt(remaining_id)
    return song


def load_uow_from_templates(uow: SongUOW):
    saved_songs = load_songs()
    this_year = date.today().year
    # songs listned to in the last 3 years (kinda but this clunky way will have to do)
    listened_songs = (
        {
            i.id
            for i in songs_week(
                after=date(this_year, 1, 1), before=date(this_year + 1, 1, 1)
            )
        }
        | {
            i.id
            for i in songs_week(
                after=date(this_year - 1, 1, 1), before=date(this_year, 1, 1)
            )
        }
        | {
            i.id
            for i in songs_week(
                after=date(this_year - 2, 1, 1),
                before=date(this_year - 1, 1, 1),
            )
        }
    )

    print(f'{len(listened_songs)} songs found')

    colliding = set(saved_songs.keys()) & listened_songs

    with futures.ThreadPoolExecutor() as executor:
        to_do: list[futures.Future] = []

        for saved_item in saved_songs.values():
            if len(listened_songs & set(saved_item['ids'])) != 0:
                future = executor.submit(
                    _load_song_from_ids,
                    ids=(listened_songs & set(saved_item['ids'])),
                    name=saved_item['name'],
                )
                to_do.append(future)

        for count, future in enumerate(futures.as_completed(to_do), start=1):
            song: Song = future.result()
            uow.songs.add(song)
            percentage = count / len(colliding) * 100
            print(
                f'{count} of {len(listened_songs)} ({percentage:.2f}%) '
                f'successfully added {song}'
            )

            if count % 100 == 0:
                uow.commit()

    uow.commit()


def save_songs_from_all_artists(uow: SongUOW):
    for artist_name, artist_id in top_artists()[:100]:
        print(f'Saving songs from {artist_name} ({artist_id})')
        save_songs_from_artist_to_uow(uow, artist_id)


if __name__ == '__main__':
    uow = SongUOW()
    # save_songs_from_artist_to_uow(uow, 18609)
    # load_uow_from_templates(uow)
    # save_songs_from_uow(uow)
    # save_songs_from_all_artists(uow = uow)
    # alphabetize_albums()
