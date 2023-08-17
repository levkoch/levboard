import pytest

from ..levboard.src.storage import Process
from ..levboard.src.model import Song


@pytest.fixture()
def example_config() -> dict:
    return {
        'username': 'lev',
        'songs': {
            '78715': {
                'name': 'no tears left to cry',
                'ids': ['78715', '5443449'],  # standard & live version
                'main_id': '78715',
                'artists': [
                    'Ariana Grande',
                ],
                'image': 'https://i.imgur.com/6v564qs.png',
                'official_name': 'No Tears Left To Cry',
                'plays': 302,
                'entries': [
                    {
                        'start': '2021-05-27',
                        'end': '2021-06-03',
                        'place': 12,
                        'plays': 2,
                        'points': 24,
                    }
                ],
            },
            '5443449': {'merge': '78715'},
        },
    }


def test_process_mutates_original_config(example_config: dict):
    config = example_config
    config['use_points'] = True

    with Process(config) as process:
        process.config.use_points = False

    assert config['use_points'] == False


def test_process_binds_songs(example_config: dict):

    with Process(example_config) as process:
        ntltc = process.songs.get('78715')

    assert ntltc is not None
    assert ntltc.artists == ['Ariana Grande']
    assert ntltc.main_id == '78715'
    assert ntltc.official_name == 'No Tears Left To Cry'
    assert ntltc.plays == 302


def test_song_merge_points_to_same(example_config: dict):
    with Process(example_config) as process:
        standard_ntltc = process.songs.get('78715')
        live_ntltc = process.songs.get('5443449')
    assert standard_ntltc is live_ntltc


def test_process_with_no_plus_raises_error():
    with pytest.raises(ValueError):
        with Process({'username': 'banana'}):
            pass


def test_song_image_from_images_links_correctly(example_config: dict):
    expected_link = 'https://i.imgur.com/6v564qs.png'
    with Process(example_config) as process:
        ntltc = process.songs.get_by_name('no tears left to cry')
        assert ntltc.image == expected_link


def test_username_injected_into_song(example_config: dict):
    with Process(example_config) as process:
        ntltc = process.songs.get_by_name('no tears left to cry')
        assert ntltc.username == 'lev'


@pytest.fixture()
def search_config() -> dict:
    config = {'username': 'lev'}
    with Process(config) as process:
        process.songs.create('1', 'Apple')
        process.songs.create('11', 'Banana')
        process.songs.create('111', 'Strawberry')
        process.songs.create('1111', 'apple')

    return config


def test_search_by_full_name(search_config: tuple):
    apple = Song('1', 'Apple')
    banana = Song('11', 'Banana')
    apple_lower = Song('1111', 'apple')

    with Process(search_config) as process:
        # full title searches
        assert apple == process.songs.get_by_name('Apple')
        assert banana == process.songs.get_by_name('Banana')

        # matches correct lowercase first
        assert apple_lower == process.songs.get_by_name('apple')


def test_search_by_partial_name(search_config: tuple):

    banana = Song('11', 'Banana')
    strawberry = Song('111', 'Strawberry')

    with Process(search_config) as process:
        # matching first part of title
        assert strawberry == process.songs.get_by_name('Straw')
        assert banana == process.songs.get_by_name('Ban')


def test_search_by_cased_name(search_config: tuple):
    apple = Song('1', 'Apple')
    banana = Song('11', 'Banana')
    strawberry = Song('111', 'Strawberry')

    with Process(search_config) as process:
        # is case-insensitive
        assert apple == process.songs.get_by_name('APPLE')
        assert banana == process.songs.get_by_name('bAnAnA')
        assert banana == process.songs.get_by_name('banana')
        assert strawberry == process.songs.get_by_name('strawberry')


def test_search_by_nonexistent_name(search_config: tuple):
    with Process(search_config) as process:
        # not coming up with things
        assert process.songs.get_by_name('orange') is None
        assert process.songs.get_by_name('fruit') is None
