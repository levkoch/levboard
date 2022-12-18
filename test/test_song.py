import json

import pytest

from main.model import Album, Song
from main.storage import SongUOW

TEST_UOW_PATH = 'C:/Users/levpo/Documents/GitHub/lev-bot/song/test.json'
TEST_ALBUM_PATH = 'C:/Users/levpo/Documents/GitHub/lev-bot/song/testalbum.py'
NO_BRAINER = '8191852'
NO_TEARS_LEFT_TO_CRY = '78715'
BREATHIN = '78710'
MERGE = '5207830'


def test_merge():
    uow = SongUOW(song_file=TEST_UOW_PATH)
    NO_BRAINER = '8191852'
    MERGE = '5207830'
    with uow:
        no_brainer = uow.songs.get(NO_BRAINER)
        merge = uow.songs.get(MERGE)
        assert merge is no_brainer


def test_merge_storage():
    uow = SongUOW(song_file=TEST_UOW_PATH)
    with open(TEST_UOW_PATH, 'r') as f:
        initial_json = json.load(f)

    with uow:
        _ = uow.songs.get(NO_BRAINER)
        print(uow.songs._songs)
        uow.commit()

    with open(TEST_UOW_PATH, 'r') as f:
        assert initial_json == json.load(f)


def test_conweeks_unchanged_entries():
    uow = SongUOW()
    song: Song = uow.songs.get(NO_TEARS_LEFT_TO_CRY)

    prior = song.entries

    for top in (None, 40, 20, 10, 5, 3, 1):
        song.get_conweeks(top=top)

    after = song.entries

    assert prior == after


def test_add_to_album():
    uow = SongUOW()
    ntltc: Song = uow.songs.get(NO_TEARS_LEFT_TO_CRY)

    sweetener: Album = Album('Sweetener', 'Ariana Grande')

    sweetener.add_song(ntltc)
    assert ntltc in sweetener


def test_add_songs_to_album():
    uow = SongUOW()
    ntltc: Song = uow.songs.get(NO_TEARS_LEFT_TO_CRY)
    breathin: Song = uow.songs.get(BREATHIN)

    sweetener: Album = Album('Sweetener', 'Ariana Grande')
    sweetener.add_song(ntltc)
    assert ntltc in sweetener
    sweetener.add_song(breathin)
    assert ntltc in sweetener
    assert breathin in sweetener
    assert len(sweetener.songs) == 2


def test_album_storage():
    with open(TEST_ALBUM_PATH, 'w') as f:
        f.write(r'{}')

    uow = SongUOW(album_file=TEST_ALBUM_PATH)
    with uow:
        sweetener = Album('Sweetener', 'Ariana Grande')
        sweetener.add_song(uow.songs.get(NO_TEARS_LEFT_TO_CRY))
        uow.albums.add(sweetener)
        uow.commit()

    del uow

    uow = SongUOW(album_file=TEST_ALBUM_PATH)
    with uow:
        assert uow.albums.get('Sweetener') is not None


def test_song_regeneration():
    uow = SongUOW(album_file=TEST_ALBUM_PATH)
    with uow:
        sweetener = uow.albums.get('Sweetener')
        assert sweetener
