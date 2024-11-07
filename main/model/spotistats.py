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
import random
import requests
import tenacity
import string

from collections import Counter, defaultdict
from concurrent import futures
from datetime import date, datetime
from typing import Final, Iterable, Optional, Union
from pydantic import BaseModel, NonNegativeInt

USER_NAME: Final[str] = 'lev'
MIN_PLAYS: Final[int] = 1
MAX_ENTRIES: Final[int] = 10000

MAX_ADJUSTED: Final[int] = 25
SONG_CHART_LENGTH = 60
BANNED_SONGS: Final[set[str]] = {'15225941'}

total_requests = 0
all_requests = Counter([])


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
    global total_requests, all_requests
    total_requests += 1
    all_requests.update(
        [
            address,
        ]
    )
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
    if isinstance(day, int):
        return day
    raise TypeError('please give a date or an int timestamp.')


def song_info(song_id: str) -> dict:
    """Returns the information about a song, from the song id."""
    r = _get_address(f'http://api.stats.fm/api/v1/tracks/{song_id}')
    return r.json()['item']


def top_artists() -> list[tuple[str, str]]:
    r = _get_address(
        f'http://api.stats.fm/api/v1/users/{USER_NAME}/top/artists?limit=1000'
    )
    return [
        (artist['artist']['name'], artist['artist']['id'])
        for artist in r.json()['items']
    ]


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

    after = _timestamp_check(after)
    before = _timestamp_check(before)

    if adjusted:
        return _adjusted_song_plays(song_id, user, after, before)

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

    def __hash__(self):
        return hash((self.id, self.plays, self.place))


class Week(BaseModel):
    """
    A dataclass for a loaded week of songs. Supports comparison &
    sorting (by week count.)

    Attributes:
    * start_day (`date`): The date when the week started.
    * end_day (`date`): The date when the week ended.
    * songs: (`dict[str, spotistats.Position]`): The `spotistats.Positions`
        of all the songs that charted that week, organized by the song id
        that the song charted under.
    """

    start_day: date
    end_day: date
    songs: dict[str, Position]

    def __lt__(self, other):
        try:
            return self.end_day < other.end_day
        except AttributeError:
            return NotImplemented

    @classmethod
    def _merge_songs(
        cls, first: 'Week', second: 'Week'
    ) -> dict[str, Position]:
        song_ids = {pos_id for pos_id in first.songs.keys()} | {
            pos_id for pos_id in second.songs.keys()
        }

        self_plays = defaultdict(int)
        for pos in first.songs.values():
            self_plays[pos.id] = pos.plays

        other_plays = defaultdict(int)
        for pos in second.songs.values():
            other_plays[pos.id] = pos.plays

        songs: dict[str, Position] = {
            song_id: Position(
                id=song_id,
                plays=self_plays[song_id] + other_plays[song_id],
                place=0,
            )
            for song_id in song_ids
        }

        return songs

    def __add__(self, other):
        # adding supported when either both of the dates match or
        # when one of the end dates is the other's start date

        if not isinstance(other, type(self)):
            return NotImplemented

        if self.start_day == other.start_day and self.end_day == other.end_day:
            return Week(
                start_day=self.start_day,
                end_day=self.end_day,
                songs=Week._merge_songs(self, other),
            )

        if self.start_day == other.end_day or self.end_day == other.start_day:
            all_days = (
                self.start_day,
                self.end_day,
                other.start_day,
                other.end_day,
            )
            return Week(
                start_day=min(all_days),
                end_day=max(all_days),
                songs=Week._merge_songs(self, other),
            )

        raise ValueError(
            'Can only add two weeks that are adjacent to each other or that '
            ' share the same start and end dates'
        )


def album_tracks(album_id: str):
    address = f'http://api.stats.fm/api/v1/albums/{album_id}/tracks'
    info = _get_address(address).json()

    return [i['id'] for i in info['items']]


def artist_tracks(artist_id: str) -> list[str]:
    address = f'http://api.stats.fm/api/v1/artists/{artist_id}/tracks?limit={MAX_ENTRIES}'
    info = _get_address(address).json()

    # filter out all songs shorter than 30000 milliseconds (30 seconds)
    return [str(i['id']) for i in info['items'] if i['durationMs'] >= 30_000]


def first_listen(user: str = USER_NAME) -> date:
    address = (
        f'http://api.stats.fm/api/v1/users/{user}/streams?limit=1&order=asc'
    )
    info = _get_address(address).json()
    return datetime.strptime(
        info['items'][0]['endTime'][:-5], r'%Y-%m-%dT%H:%M:%S'
    ).date()


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
        '&limit=500'  # max limit for this request is 500 songs and not the 10,000 like others have
    )

    r = _get_address(address)
    items: list[dict] = r.json()['items']
    print(f'{len(items)} items found.')

    if (
        len(items) % 500 == 0 or len(items) % 500 > 450
    ):   # filled in everything
        # might need to switch back to if len(items) % 500 > 450 but whatever
        offset = 500
        print('searching for more items')
        while len(items) % 500 == 0 or len(items) % 500 > 450:
            address = (
                f'https://api.stats.fm/api/v1/users/{user}/top/tracks'
                f'?after={after}&before={before}'
                f'&limit=500&offset={offset}'
            )
            r = _get_address(address)
            additions = r.json()['items']
            if not len(additions):
                break
            items.extend(additions)
            print(
                f'{offset} offset and {len(items)} total items after {len(additions)} added'
            )
            offset += 500

    info = [
        Position(
            id=str(i['track']['id']), plays=i['streams'], place=i['position']
        )
        for i in items
        if str(i['track']['id']) not in BANNED_SONGS
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
    * played_from (`int`): the song id we listened to the song from.
    """

    played_for: int
    finished_playing: datetime
    played_from: str


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
            played_from=song_id,
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
