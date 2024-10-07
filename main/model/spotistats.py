"""
levboard/main/model/spotistats.py

A Module with common Spotistats requests to make it easier to make them.
I suggest importing the model and not the requests separately for readability.

Requests:
* `song_info`: Retrieves the info for a song.
* `song_plays`: Returns the song plays for a specific song id.
* `songs_week`: Returns the top songs for a specific time period.
* `song_play_history`: The history of the song's plays.
"""

import time
import tenacity
import requests
import string
import random

from datetime import date, datetime
from typing import Final, Literal, Union
from pydantic import NonNegativeInt

from . import config

MIN_PLAYS: Final[int] = 1
MAX_ENTRIES: Final[int] = 10000


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


@tenacity.retry(stop=tenacity.stop.stop_after_attempt(3))
def _get_address(address: str) -> requests.Response:
    """
    A retrying requests.get call that will try three times if it
    sends a bad gateway error like spotistats likes doing if it's
    servers are overloaded at the moment.
    """
    # this is for getting around bot identification for the cloud scraping
    # so they think the request is coming from an ipad
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit'
        '/605.1.15 (KHTML, like Gecko) Mobile/15E148'
    }

    addon = ''.join(random.choices(string.ascii_lowercase, k=6))
    if '?' in address:
        sneaky_address = address + '&korea=' + addon
    else:
        sneaky_address = address + '?korea=' + addon

    response = requests.get(sneaky_address, headers=HEADERS)
    response.raise_for_status()
    return response

def song_info(song_id: str) -> dict:
    """Returns the information about a song, from the song id."""
    r = _get_address(f'https://api.stats.fm/api/v1/tracks/{song_id}')
    return r.json()['item']


def song_plays(
    song_id: str,
    *,
    user: str = '',
    after: Union[int, date] = 0,
    before: Union[int, date] = 0,
) -> int:
    """
    Finds the plays for a song with the specified song id, between `after`
    and `before`, if specified. The `after` and `before` parameters can be
    either date objects or epoch timestamps.
    """

    if not user:
        user = config.get_username()
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

    r = _get_address(address)

    return r.json()['items']['count']


def songs_week(
    after: Union[int, date],
    before: Union[int, date],
    *,
    user: str = '',
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

    if not user:
        user = config.get_username()
    after = _timestamp_check(after)
    before = _timestamp_check(before)

    address = (
        f'https://api.stats.fm/api/v1/users/{user}/top/tracks'
        f'?after={after}&before={before}'
    )

    r = _get_address(address)

    return [
        {'plays': int(i['streams']), 'id': str(i['track']['id'])}
        for i in r.json()['items']
        if i['streams'] > min_plays
    ]


def song_play_history(
    song_id: str,
    *,
    user: str = '',
    max_entries: NonNegativeInt = MAX_ENTRIES,
) -> list[dict]:

    """Returns a list of song plays for the indicated song id."""

    if not user:
        user = config.get_username()

    address = (
        f'https://api.stats.fm/api/v1/users/{user}/streams/'
        f'tracks/{song_id}?limit={max_entries}'
    )

    r = _get_address(address)

    # datetime is formatted like '2022-04-11T05:03:15.000Z'
    # get rid of milliseconds with string slice
    # because they're gonna be 000 anyway

    return [
        {
            'played_for': int(i['playedMs']),
            'finished_playing': datetime.strptime(
                i['endTime'][:-5], r'%Y-%m-%dT%H:%M:%S'
            ),
        }
        for i in r.json()['items']
    ]


def user_play_history(
    user: str,
    *,
    after: Union[int, date] = 0,
    before: Union[int, date] = 0,
    max_entries: NonNegativeInt = MAX_ENTRIES,
    order: Literal['asc', 'desc'] = 'desc',
) -> list[dict]:
    """Returns a list of dicts of the user's streams."""

    after = _timestamp_check(after)
    before = _timestamp_check(before)

    args = [f'limit={max_entries}', f'order={order}']
    if after:
        args.append(f'after={after}')
    if before:
        args.append(f'before={before}')

    address = f'https://api.stats.fm/api/v1/users/{user}/streams/'

    if args:
        address += '?' + '&'.join(args)

    r = _get_address(address)

    return [
        {
            'song_id': info['trackId'],
            'song_name': info['trackName'],
            'artists': info['artistIds'],
            'finished_playing': datetime.strptime(
                info['endTime'][:-5], r'%Y-%m-%dT%H:%M:%S'
            ),
        }
        for info in r.json()['items']
    ]
