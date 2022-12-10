from datetime import date

import pytest

from ..main.model import spotistats

TEST_WEEK_START = date(2022, 1, 1)
TEST_WEEK_END = date(2022, 1, 7)


@pytest.fixture()
def sample_songs_week():
    return spotistats.songs_week(TEST_WEEK_START, TEST_WEEK_END)


def test_songs_week_returns_positions(sample_songs_week):
    info = sample_songs_week
    for i in info:
        assert isinstance(i, spotistats.Position)


def test_songs_week_positions(sample_songs_week):
    info = sample_songs_week

    got_places = [i.place for i in info]
    wanted_places = sorted([i.place for i in info])

    assert got_places == wanted_places


def test_songs_week_last_place_is_one_play(sample_songs_week):
    last_place = max(i.place for i in sample_songs_week)

    assert all(
        1 == i.plays for i in sample_songs_week if i.place == last_place
    )
