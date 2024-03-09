import json

import pytest

from ..main.model import Album, Song, Variant
from ..main.storage import SongUOW

TEST_SONG_PATH = r'C:\Users\levpo\Documents\GitHub\levboard\test\test.json'
TEST_ALBUM_PATH = (
    r'C:\Users\levpo\Documents\GitHub\levboard\test\testalbum.json'
)
NO_BRAINER = '8191852'
NO_TEARS_LEFT_TO_CRY = '78715'
BREATHIN = '78710'
MERGE = '5207830'


@pytest.fixture()
def testuow() -> SongUOW:
    return SongUOW(song_file=TEST_SONG_PATH, album_file=TEST_ALBUM_PATH)


@pytest.fixture()
def ntltc(testuow: SongUOW) -> Song:
    return testuow.songs.get(NO_TEARS_LEFT_TO_CRY)


def test_con_weeks(ntltc: Song):
    info = ntltc.all_consecutive()
    largest = ntltc.get_conweeks()
    assert max(i[1] for i in info) == largest


def test_merge(testuow: SongUOW):
    NO_BRAINER = '8191852'
    MERGE = '5207830'
    with testuow:
        no_brainer = testuow.songs.get(NO_BRAINER)
        merge = testuow.songs.get(MERGE)
        assert merge is no_brainer


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


def test_add_songs_to_album(testuow: SongUOW):
    ntltc: Song = testuow.songs.get(NO_TEARS_LEFT_TO_CRY)
    breathin: Song = testuow.songs.get(BREATHIN)

    sweetener: Album = Album('Sweetener', 'Ariana Grande')
    sweetener.add_song(ntltc)
    assert ntltc in sweetener
    sweetener.add_song(breathin)
    assert ntltc in sweetener
    assert breathin in sweetener
    assert len(sweetener) == 2


def test_album_storage(testuow: SongUOW):
    with open(TEST_ALBUM_PATH, 'w') as f:
        f.write(r'{}')

    with testuow:
        sweetener = Album('Sweetener', 'Ariana Grande')
        sweetener.add_song(testuow.songs.get(NO_TEARS_LEFT_TO_CRY))
        testuow.albums.add(sweetener)
        testuow.commit()

    del testuow

    testuow = SongUOW(album_file=TEST_ALBUM_PATH, song_file=TEST_SONG_PATH)
    with testuow:
        assert testuow.albums.get('Sweetener') is not None


def test_song_regeneration(testuow: SongUOW):
    with testuow:
        assert testuow.albums.get('Sweetener') is not None


def test_song_from_variants():
    ntltc = Song.from_variants(
        main_id='78715',
        variants=(
            Variant(
                main_id='78715',
                title='no tears left to cry',
                ids={'78715'},
                artists=('Ariana Grande',),
            ),
            Variant(
                main_id='5443449',
                title='no tears left to cry - live',
                ids={'5443449'},
                artists=('Ariana Grande',),
            ),
        ),
    )

    expected_variants = [
        {
            'main_id': '5443449',
            'title': 'no tears left to cry - live',
            'ids': ['5443449'],
            'artists': ['Ariana Grande'],
        },
        {
            'main_id': '78715',
            'title': 'no tears left to cry',
            'ids': ['78715'],
            'artists': ['Ariana Grande'],
        },
    ]

    for variant in expected_variants:
        assert variant in ntltc.to_dict()['variants']

    assert ntltc.title == "no tears left to cry"
    assert ntltc.main_id == '78715'
    assert ntltc.ids == {'78715', '5443449'}
    assert ntltc.artists == ['Ariana Grande']

