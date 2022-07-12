"""
A Module with common Spotistats requests to make it easier to make them.

Requests:
* song_info(): Retrieves the info for a song.
"""

from typing import Union
import requests
import time

from datetime import date

from ..config import USER_NAME


def date_to_timestamp(day: date) -> int:
    """
    Converts a `datetime.date` to a epoch timestamp, as an `int`,
    so that Spotistats registers the day correctly.
    """
    return int(time.mktime(day.timetuple()) * 1000)


def song_info(song_id: str) -> dict:
    """Returns the information about a song, from the song id."""
    r = requests.get(f'https://api.stats.fm/api/v1/tracks/{song_id}')
    return r.json()['item']


def song_plays(
    song_id: str, *, after: Union[int, date] = 0, before: Union[int, date] = 0
) -> int:
    """"""

    if isinstance(after, date):
        after = date_to_timestamp(after)
    if isinstance(before, date):
        before = date_to_timestamp(before)

    address = (
        f'https://api.stats.fm/api/v1/users/{USER_NAME}/streams/tracks/{song_id}/stats'
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
