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
from collections import Counter, defaultdict
from concurrent import futures
from datetime import date, datetime
from typing import Iterable, Optional, Union

import requests
import tenacity
from pydantic import BaseModel


class MissingStreamsException(ValueError):
    """
    An exception for when someone needs to have their streams imported
    for this to work.
    """


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

    response = requests.get(address, headers=HEADERS)
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


def get_first_stream_date(user: str) -> date:
    r = _get_address(
        f'http://api.stats.fm/api/v1/users/{user}/streams?limit=1&order=asc'
    ).json()
    if not len(r['items']):
        raise MissingStreamsException(
            'Must have stats.fm plus for this to work.'
        )
    return datetime.strptime(
        r['items'][0]['endTime'][:-5], r'%Y-%m-%dT%H:%M:%S'
    ).date()


def song_info(song_id: str) -> dict:
    """Returns the information about a song, from the song id."""
    r = _get_address(f'http://api.stats.fm/api/v1/tracks/{song_id}')
    return r.json()['item']


def top_artists(user: str) -> list[tuple[str, str]]:
    r = _get_address(
        f'http://api.stats.fm/api/v1/users/{user}/top/artists?limit=1000'
    )
    return [
        (artist['artist']['name'], artist['artist']['id'])
        for artist in r.json()['items']
    ]


def song_plays(
    user: str,
    song_id: str,
    *,
    after: Union[int, date] = 0,
    before: Union[int, date] = 0,
    adjusted: bool = False,
    max_adjusted: Optional[int] = None,
) -> int:
    """
    Finds the plays for a song with the specified song id, between `after`
    and `before`, if specified. The `after` and `before` parameters can be
    either date objects or epoch timestamps (if they are `0` then the plays
    will not be filtered by time). If `adjusted` is true, then the song
    plays will also be filtered.
    """

    if adjusted:
        if not max_adjusted:
            raise ValueError(
                'max_adjusted must be specified if calling for adjusted plays.'
            )
        return _adjusted_song_plays(user, song_id, after, before, max_adjusted)

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
    user: str,
    song_id: str,
    after: Union[date, int, None],
    before: Union[date, int, None],
    max_adjusted: int,
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
    return sum(min(max_adjusted, count) for count in date_counter.values())


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
    points: int

    def __hash__(self):
        return hash((self.id, self.plays, self.place, self.points))


class Week(BaseModel):
    """
    A dataclass for a loaded week of songs. Supports comparison &
    sorting (by week count.)

    Attributes:
    * start_day (`date`): The date when the week started.
    * end_day (`date`): The date when the week ended.
    * songs: (`list[spotistats.Position]`): The `spotistats.Positions`
    of all the songs that charted that week.
    """

    start_day: date
    end_day: date
    songs: list[Position]

    def __lt__(self, other):
        try:
            return self.end_day < other.end_day
        except AttributeError:
            return NotImplemented

    @classmethod
    def _merge_songs(cls, first: 'Week', second: 'Week') -> list[Position]:
        song_ids = {pos.id for pos in first.songs} | {
            pos.id for pos in second.songs
        }

        self_plays = defaultdict(int)
        for pos in first.songs:
            self_plays[pos.id] = pos.plays

        other_plays = defaultdict(int)
        for pos in second.songs:
            other_plays[pos.id] = pos.plays

        song_list = []
        for song_id in song_ids:
            song_list.append(
                Position(
                    id=song_id,
                    plays=self_plays[song_id] + other_plays[song_id],
                    place=0,
                )
            )

        return song_list

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


def album_tracks(album_id: str) -> list[str]:
    address = f'http://api.stats.fm/api/v1/albums/{album_id}/tracks'
    info = _get_address(address).json()

    return [str(i['id']) for i in info['items']]


def artist_tracks(artist_id: str) -> list[str]:
    address = (
        f'http://api.stats.fm/api/v1/artists/{artist_id}/tracks?limit=10000'
    )
    info = _get_address(address).json()

    # filter out all songs shorter than 30000 milliseconds (30 seconds)
    return [str(i['id']) for i in info['items'] if i['durationMs'] >= 30_000]


# this gets called by `main` in two places with the same values, so we cache
# the last result here to not have to make the multiple API call operator
# multiple times.
@functools.lru_cache(maxsize=1)
def songs_week(
    user: str,
    after: Union[int, date],
    before: Union[int, date],
    adjusted: bool = False,
    max_adjusted: Optional[int] = None,
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
        f'?after={after}&before={before}&limit=1000'
        # max limit for this request is 1000 songs and not the 10,000 like others have
    )

    r = _get_address(address)
    items: list[dict] = r.json()['items']

    if len(items) == 1000:   # if filled in everything
        offset = 1000
        while len(items) % 1000 == 0:
            address = (
                f'https://api.stats.fm/api/v1/users/{user}/top/tracks'
                f'?after={after}&before={before}'
                f'&limit=1000&offset={offset}'
            )
            r = _get_address(address)
            items.extend(r.json()['items'])
            offset += 1000

    info = [
        Position(
            id=i['track']['id'],
            plays=i['streams'],
            points=i['streams'],
            place=i['position'],
        )
        for i in items
        if str(i['track']['id'])
    ]

    if not adjusted:
        for pos in info:
            pos.place = len([i for i in info if i.plays > pos.plays]) + 1
        return info

    if max_adjusted is None:
        raise ValueError('max_adjusted must be specified')

    # adjust the song plays if requested to do so, but we are doing
    # this threaded to make this take less time.
    with futures.ThreadPoolExecutor() as executor:
        values: Iterable[tuple[str, int]] = executor.map(
            lambda i: (
                i,
                _adjusted_song_plays(user, i, after, before, max_adjusted),
            ),
            (i.id for i in info if i.plays > max_adjusted),
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
    user: str,
    *,
    after: Union[date, int, None] = None,
    before: Union[date, int, None] = None,
) -> list[Listen]:

    """Returns a list of song listens for the indicated song id."""

    address = (
        f'https://api.stats.fm/api/v1/users/{user}/streams/'
        f'tracks/{song_id}?limit=10000'
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