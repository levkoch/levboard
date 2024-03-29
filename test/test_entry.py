from datetime import date

import pytest

from ..main.model import Entry


@pytest.mark.parametrize(
    ('start', 'end', 'plays', 'place'),
    [
        (date(2000, 1, 1), date(2000, 1, 7), 20, 13),
        ('2000-01-01', '2000-01-07', 20, 13),
        (date(2000, 1, 1), date(2000, 1, 7), 20.0, 13.0),
    ],
)
def test_creating_entry_types(start, end, plays, place):
    entry = Entry(**locals())

    type_tuples = [
        (entry.start, date),
        (entry.end, date),
        (entry.plays, int),
        (entry.place, int),
    ]

    for items in type_tuples:
        assert isinstance(*items)


@pytest.mark.parametrize(
    ('start', 'end', 'plays', 'place'),
    [
        (date(2000, 1, 1), date(2000, 1, 7), 20, 13),
        ('2000-01-01', '2000-01-07', 20, 13),
        (date(2000, 1, 1), date(2000, 1, 7), 20.0, 13.0),
    ],
)
def test_creating_entry_values(start, end, plays, place):
    entry = Entry(**locals())

    type_tuples = [
        (entry.start, date(2000, 1, 1)),
        (entry.end, date(2000, 1, 7)),
        (entry.plays, 20),
        (entry.place, 13),
    ]

    for item, value in type_tuples:
        assert item == value


@pytest.mark.parametrize(
    ('info'),
    [
        {'start': '2000-01-01', 'end': '2000-01-07', 'plays': 30, 'place': 13},
        {'start': '2013-04-12', 'end': '2013-04-19', 'plays': 34, 'place': 5},
    ],
)
def test_creating_dict(info: dict):
    entry = Entry(**info)

    assert entry.to_dict() == info
