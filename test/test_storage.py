import pytest

from ..main.src.storage import Process


@pytest.fixture()
def example_config() -> dict:
    return {
        'username': 'lev',
        'songs': {
            '78715': {
                'name': 'no tears left to cry',
                'ids': ['78715', '5443449'],  # live version
                'main_id': '78715',
                'artists': [
                    'Ariana Grande',
                ],
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
