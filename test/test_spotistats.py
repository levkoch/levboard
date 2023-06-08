from datetime import date

import pytest

from ..main.model import spotistats

from ..main.model.spotistats import Position, Week

TEST_WEEK_START = date(2022, 1, 1)
TEST_WEEK_END = date(2022, 1, 7)


def test_song_week_merging():
    week_one = Week(TEST_WEEK_START, TEST_WEEK_END, [
        Position("a", 13, 0), Position("b", 6, 0), Position("c", 2, 0)
    ])
    week_two = Week(TEST_WEEK_START, TEST_WEEK_END, [
        Position("c", 6, 0), Position("a", 3, 0), Position("d", 2, 0)
    ])

    combined = week_one + week_two

    assert len(combined.songs) == 4
    assert set(combined.songs) == {
        Position("a", 16, 0), Position("b", 6, 0), 
        Position("c", 8, 0), Position("d", 2, 0)
    }


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
