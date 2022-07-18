"""
A Module with common Spotistats requests to make it easier to make them.

Requests:
* `song_info`: Retrieves the info for a song.
* `song_plays`: Returns the song plays for a specific song id.
* `songs_week`: Returns the top songs for a specific time period.
"""

import requests
import time

from datetime import date
from typing import Union, Final

USER_NAME: Final[str] = 'lev'
MIN_PLAYS: Final[int] = 1


def date_to_timestamp(day: date) -> int:
    """
    Converts a `datetime.date` to a epoch timestamp, as an `int`,
    so that Spotistats registers the day correctly.
    """
    return int(time.mktime(day.timetuple()) * 1000)


def _timestamp_check(day: Union[date, int]) -> int:
    """submethod to make casting dates to timestamps easier."""
    if isinstance(day, date):
        return date_to_timestamp(day)
    return day


def song_info(song_id: str) -> dict:
    """Returns the information about a song, from the song id."""
    r = requests.get(f'https://api.stats.fm/api/v1/tracks/{song_id}')
    return r.json()['item']


def song_plays(
    song_id: str,
    *,
    user: str = USER_NAME,
    after: Union[int, date] = 0,
    before: Union[int, date] = 0,
) -> int:
    """
    Finds the plays for a song with the specified song id, between `after`
    and `before`, if specified. The `after` and `before` parameters can be
    either date objects or epoch timestamps.
    """

    after = _timestamp_check(after)
    before = _timestamp_check(before)

    address = (
        f'https://api.stats.fm/api/v1/users/{user}/'
        f'streams/tracks/{song_id}/stats'
    )

    if after or before:
        address += '?'

    if after:
        address += f'after={after}'

    if after and before:
        address += '&'

    if before:
        address += f'before={before}'

    r = requests.get(address)

    return r.json()['items']['count']


def songs_week(
    after: Union[int, date],
    before: Union[int, date],
    *,
    user: str = USER_NAME,
    min_plays: int = MIN_PLAYS,
) -> list[dict]:
    """
    Returns the "week" between `after` and `before` (it doesn't have to
    be a week, at all.) Optional parameters can specify a username, aside
    from the default one with `user`, and filter out all of the songs that
    got less than `min_plays` plays, if the default value isn't wanted.

    The return is a list of dictionaries with two values: `'plays'` with
    the number of plays, and `'id'` with the song id of the song they're for.
    """

    after = _timestamp_check(after)
    before = _timestamp_check(before)

    address = (
        f'https://api.stats.fm/api/v1/users/{user}/top/tracks'
        f'?after={after}&before={before}'
    )

    r = requests.get(address)

    return [
        {'plays': int(i['streams']), 'id': str(i['track']['id'])}
        for i in r.json()['items']
        if i['streams'] > min_plays
    ]
