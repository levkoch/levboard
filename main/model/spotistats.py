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

import functools
import time
from collections import Counter
from concurrent import futures
from datetime import date, datetime
from typing import Final, Iterable, Optional, Union

import requests
import tenacity
from pydantic import BaseModel, NonNegativeInt

USER_NAME: Final[str] = 'lev'
MIN_PLAYS: Final[int] = 1
MAX_ENTRIES: Final[int] = 10000
MAX_ADJUSTED: Final[int] = 25


@tenacity.retry(stop=tenacity.stop.stop_after_attempt(3))
def _get_address(address: str) -> requests.Response:
    """
    A retrying requests.get call that will try three times if it
    sends a bad gateway error like spotistats likes doing if it's
    servers are overloaded at the moment.
    """
    response = requests.get(address)
    response.raise_for_status()
    return response


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
    r = _get_address(f'https://api.stats.fm/api/v1/tracks/{song_id}')
    return r.json()['item']


def song_plays(
    song_id: str,
    *,
    user: str = USER_NAME,
    after: Union[int, date] = 0,
    before: Union[int, date] = 0,
    adjusted: bool = False,
) -> int:
    """
    Finds the plays for a song with the specified song id, between `after`
    and `before`, if specified. The `after` and `before` parameters can be
    either date objects or epoch timestamps (if they are `0` then the plays
    will not be filtered by time). If `adjusted` is true, then the song
    plays will also be filtered.
    """

    if adjusted:
        return _adjusted_song_plays(song_id, user, after, before)

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


def _adjusted_song_plays(
    song_id: str,
    user: str,
    after: Union[date, int, None],
    before: Union[date, int, None],
) -> int:
    """
    Internal helper method to find the adjusted plays for a song between
    a certain period.
    """

    plays: list[Listen] = song_play_history(
        song_id, user=user, after=after, before=before
    )

    play_dates: Iterable[date] = (i.finished_playing.date() for i in plays)
    date_counter = Counter(play_dates)
    return sum(min(MAX_ADJUSTED, count) for count in date_counter.values())


class Position(BaseModel):
    """
    A single song's entry on a basic spotistats chart.

    Attributes:
    * id (`str`): The song id which got the streams.
    * plays (`int`): The number of plays the song got.
    * place (`int`): The place that song got.
    """

    id: str
    plays: int
    place: int


# this gets called by `main` in two places with the same values, so we cache
# the last result here to not have to make the multiple API call operator
# multiple times.
@functools.lru_cache(maxsize=1)
def songs_week(
    after: Union[int, date],
    before: Union[int, date],
    *,
    user: str = USER_NAME,
    adjusted: bool = False,
) -> list[Position]:
    """
    Returns the "week" between `after` and `before` (it doesn't have to
    be a week, at all.) Optional parameters can specify a username, aside
    from the default one with `user`, and filter out all of the songs that
    got less than `min_plays` plays, if the default value isn't wanted.
    Additionally allows for plays to be filtered, if `adjusted` is set to
    `True`.

    The return is a list of dictionaries with two values: `'plays'` with
    the number of plays, and `'id'` with the song id of the song they're for.
    """

    after = _timestamp_check(after)
    before = _timestamp_check(before)

    address = (
        f'https://api.stats.fm/api/v1/users/{user}/top/tracks'
        f'?after={after}&before={before}'
    )

    r = _get_address(address)

    info = [
        Position(id=i['track']['id'], plays=i['streams'], place=i['position'])
        for i in r.json()['items']
    ]

    if not adjusted:
        for pos in info:
            pos.place = len([i for i in info if i.plays > pos.plays]) + 1
        return info

    # adjust the song plays if requested to do so, but we are doing
    # this threaded to make this take less time.
    with futures.ThreadPoolExecutor() as executor:
        values: Iterable[tuple[str, int]] = executor.map(
            lambda i: (i, _adjusted_song_plays(i, user, after, before)),
            (i.id for i in info if i.plays > MAX_ADJUSTED),
        )

        for song_id, song_plays in values:
            song_dict = next(i for i in info if i.id == song_id)
            song_dict.plays = song_plays

    # when calling the API it comes pre-sorted, but because we might have
    # replaced some values, it needs to be sorted again
    for pos in info:
        pos.place = len([i for i in info if i.plays > pos.place]) + 1
    return sorted(info, reverse=True, key=lambda i: i.plays)


class Listen(BaseModel):
    """
    A song listen.

    * played_for (`int`): The number of milliseconds the song was played for.
    * finished_playing (`datetime`): The time the song was finished being
        listened to.
    """

    played_for: int
    finished_playing: datetime


def song_play_history(
    song_id: str,
    *,
    user: str = USER_NAME,
    after: Union[date, int, None] = None,
    before: Union[date, int, None] = None,
    max_entries: NonNegativeInt = MAX_ENTRIES,
) -> list[Listen]:

    """Returns a list of song listens for the indicated song id."""

    address = (
        f'https://api.stats.fm/api/v1/users/{user}/streams/'
        f'tracks/{song_id}?limit={max_entries}'
    )

    if after:
        address += f'&after={_timestamp_check(after)}'

    if before:
        address += f'&before={_timestamp_check(before)}'

    r = _get_address(address)

    # datetime is formatted like '2022-04-11T05:03:15.000Z'
    # get rid of milliseconds with string slice
    # because they're gonna be 000 anyway

    return [
        Listen(
            played_for=int(i['playedMs']),
            finished_playing=datetime.strptime(
                i['endTime'][:-5], r'%Y-%m-%dT%H:%M:%S'
            ),
        )
        for i in r.json()['items']
    ]


def track_top_listener(song_id: str, user: str = USER_NAME) -> Optional[int]:
    """
    Returns the position `user` has in the world listening chart for the
    song corresponding to `song_id`. Will return `None` if they're not in
    the top 1000 users.
    """

    address = f'https://api.stats.fm/api/v1/tracks/{song_id}/top/listeners'
    r = _get_address(address)
    return next(
        (i['position'] for i in r.json()['items'] if i['customId'] == user),
        None,
    )
