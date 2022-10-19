import json
import pytest
from ..main.model import Song, Album
from ..main.storage import SongUOW

TEST_UOW_PATH = r'C:\Users\levpo\Documents\GitHub\levboard\test\test.json'
TEST_ALBUM_PATH = r'C:\Users\levpo\Documents\GitHub\levboard\test\testalbum.json'
NO_BRAINER = '8191852'
NO_TEARS_LEFT_TO_CRY = '78715'
BREATHIN = '78710'
MERGE = '5207830'

@pytest.fixture()
def uow() -> SongUOW:
    return SongUOW(song_file = TEST_UOW_PATH, album_file = TEST_ALBUM_PATH)

@pytest.fixture()
def ntltc(uow: SongUOW) -> Song:
    return uow.songs.get(NO_TEARS_LEFT_TO_CRY)

def test_merge(uow: SongUOW):
    NO_BRAINER = '8191852'
    MERGE = '5207830'
    with uow:
        no_brainer = uow.songs.get(NO_BRAINER)
        merge = uow.songs.get(MERGE)
        assert merge is no_brainer


def test_merge_storage(uow: SongUOW):
    with open(TEST_UOW_PATH, 'r') as f:
        initial_json = json.load(f)

    with uow:
        _ = uow.songs.get(NO_BRAINER)
        print(uow.songs._songs)
        uow.commit()

    with open(TEST_UOW_PATH, 'r') as f:
        assert initial_json == json.load(f)


def test_conweeks_unchanged_entries(ntltc: Song):
    prior = ntltc.entries

    for top in (None, 40, 20, 10, 5, 3, 1):
        ntltc.get_conweeks(top=top)

    after = ntltc.entries

    assert prior == after


def test_add_to_album(ntltc: Song):
    sweetener: Album = Album('Sweetener', 'Ariana Grande')
    sweetener.add_song(ntltc)

    assert ntltc in sweetener


def test_add_songs_to_album(uow: SongUOW):
    ntltc: Song = uow.songs.get(NO_TEARS_LEFT_TO_CRY)
    breathin: Song = uow.songs.get(BREATHIN)

    sweetener: Album = Album('Sweetener', 'Ariana Grande')
    sweetener.add_song(ntltc)
    assert ntltc in sweetener
    sweetener.add_song(breathin)
    assert ntltc in sweetener
    assert breathin in sweetener
    assert len(sweetener) == 2


def test_album_storage(uow: SongUOW):
    with open(TEST_ALBUM_PATH, 'w') as f:
        f.write(r'{}')

    with uow:
        sweetener = Album('Sweetener', 'Ariana Grande')
        sweetener.add_song(uow.songs.get(NO_TEARS_LEFT_TO_CRY))
        uow.albums.add(sweetener)
        uow.commit()

    del uow

    uow = SongUOW(album_file=TEST_ALBUM_PATH)
    with uow:
        assert uow.albums.get('Sweetener') is not None


def test_song_regeneration(uow: SongUOW):
    with uow:
        assert uow.albums.get('Sweetener') is not None
