"""
levboard/main/model/spotistats.py

A Module with common Spotistats requests to make it easier to make them.
I suggest importing the model and not the requests separately for readability.
Now it can access local listens.db data for quicker & more accurate readings.

Requests:
* `song_info`: Retrieves the info for a song.
* `song_plays`: Returns the song plays for a specific song id.
* `songs_week`: Returns the top songs for a specific time period.
* `song_play_history`: The history of the song's plays.
"""

import functools
import sqlite3
import time
import random
import requests
import tenacity
import string

from collections import Counter, defaultdict
from concurrent import futures
from contextlib import contextmanager
from datetime import date, datetime
from typing import Final, Iterable, Optional, Union
from pydantic import BaseModel

USER_NAME: Final[str] = 'lev'
MIN_PLAYS: Final[int] = 1
MAX_ENTRIES: Final[int] = 10000

MAX_ADJUSTED: Final[int] = 25
SONG_CHART_LENGTH = 60
BANNED_SONGS: Final[set[str]] = {'15225941'}

total_requests: int = 0
all_requests: Counter = Counter([])

DB_PATH: str = 'listens.db'
# epoch ms of the newest row in the DB
_latest_local_ts: Optional[int] = None


@contextmanager
def _db():
    """helper method to connect to database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _latest_stream_ts() -> Optional[int]:
    """
    Returns the epoch-ms timestamp of the most recent listen in the local DB,
    or None if the DB is unavailable / empty.
    """
    global _latest_local_ts
    if _latest_local_ts is not None:
        return _latest_local_ts
    if not DB_PATH:
        return None
    try:
        with _db() as conn:
            row = conn.execute('SELECT MAX(ts) as m FROM listens').fetchone()
            _latest_local_ts = row['m'] if row and row['m'] else None
            return _latest_local_ts
    except Exception:
        return None


def _ts(day: Union[date, int, None]) -> Optional[int]:
    """Convert a date or epoch-ms int to epoch-ms, or None if falsy."""
    if not day:
        return None
    if isinstance(day, date):
        return int(datetime(day.year, day.month, day.day).timestamp() * 1000)
    if isinstance(day, int):
        return day
    raise TypeError(f'Expected date or int, got {type(day)}')


def _within_local(before: Union[date, int, None]) -> bool:
    """
    True when the requested `before` bound is entirely covered by the local DB
    (i.e. the query does not extend past the latest stored stream).
    A None/0 `before` means "up to now", which the local DB cannot cover.
    """
    if not before:
        return False
    latest = _latest_stream_ts()
    if latest is None:
        return False
    return (_ts(before) or 0) <= latest


@tenacity.retry(stop=tenacity.stop.stop_after_attempt(3))
def _get_address(address: str) -> requests.Response:
    """
    A retrying requests.get call that will try three times if it
    sends a bad gateway error like spotistats likes doing if it's
    servers are overloaded at the moment.
    """
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
    all_requests.update([address])
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

    def __lt__(self, other):
        try:
            return self.finished_playing < other.finished_playing
        except AttributeError:
            return NotImplemented


class Week(BaseModel):
    """
    A dataclass for a loaded week of song positions. Supports comparison &
    sorting (by week count.)

    Attributes:
    * start_day (`date`): The date when the week started.
    * end_day (`date`): The date when the week ended.
    * positions: (`dict[str, spotistats.Position]`): The `spotistats.Positions`
        of all the songs that charted that week, organized by the song id
        that the song charted under.
    """

    start_day: date
    end_day: date
    positions: dict[str, Position]

    def __lt__(self, other):
        try:
            return self.end_day < other.end_day
        except AttributeError:
            return NotImplemented

    @classmethod
    def _merge_songs(
        cls, first: 'Week', second: 'Week'
    ) -> dict[str, Position]:
        song_ids = {pos_id for pos_id in first.positions.keys()} | {
            pos_id for pos_id in second.positions.keys()
        }

        self_plays = defaultdict(int)
        for pos in first.positions.values():
            self_plays[pos.id] = pos.plays

        other_plays = defaultdict(int)
        for pos in second.positions.values():
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
                positions=Week._merge_songs(self, other),
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
                positions=Week._merge_songs(self, other),
            )

        raise ValueError(
            'Can only add two weeks that are adjacent to each other or that '
            ' share the same start and end dates'
        )


def song_info(song_id: str) -> dict:
    """Returns the information about a song, from the song id."""
    if song_id.isnumeric():
        # yay it's a stats fm id
        r = _get_address(f'http://api.stats.fm/api/v1/tracks/{song_id}')
        return r.json()['item']

    # it's not a stats fm id. we need to do some more digging to find it.

    sql = """
        SELECT track_name, artist_name
        FROM   listens
        WHERE  statsfm_id = ?
    """
    params: list = [song_id]

    with _db() as conn:
        item = conn.execute(sql, params).fetchone()
    if item is None:
        raise ValueError('track not found in database.')
    return {
        'name': item['track_name'],
        'artists': [{'name': item['artist_name']}],
    }


def song_play_history(
    song_id: str,
    *,
    user: str = USER_NAME,
    after: Union[date, int, None] = None,
    before: Union[date, int, None] = None,
) -> list[Listen]:
    """Returns a list of song listens for the indicated song id."""

    if _within_local(before) or not song_id.isnumeric():
        # if we want to search in a range that's inside our local data, we look at the local data.
        # if the song isn't a stats fm id song (either untied, or a X____ id from a song that was
        # wrongly merged on stats fm), we also go look at local data only.
        return _local_song_play_history(song_id, after=after, before=before)

    if (after is None or _ts(after) < _latest_stream_ts()) and (
        before is None or _ts(before) > _latest_stream_ts()
    ):
        # we have a section which is covered by our current local data,
        # and then a section which isn't.

        local_plays = _local_song_play_history(
            song_id, after=after, before=_latest_stream_ts()
        )
        statsfm_plays = song_play_history(
            song_id, after=_latest_stream_ts(), before=before
        )

        return sorted(local_plays + statsfm_plays)

    address = (
        f'https://api.stats.fm/api/v1/users/{user}/streams/'
        f'tracks/{song_id}?limit={MAX_ENTRIES}'
    )

    if after:
        address += f'&after={_timestamp_check(after)}'
    if before:
        address += f'&before={_timestamp_check(before)}'

    r = _get_address(address)

    # datetime is formatted like '2022-04-11T05:03:15.000Z'
    # get rid of milliseconds with string slice because they're gonna be 000 anyway
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


def _local_song_play_history(
    song_id: str,
    *,
    after: Union[date, int, None] = None,
    before: Union[date, int, None] = None,
) -> list[Listen]:
    """Serves song_play_history entirely from the local DB."""

    after_ts = _ts(after)
    before_ts = _ts(before)

    sql = """
        SELECT ts, ms_played, statsfm_id
        FROM   listens
        WHERE  statsfm_id = ?
    """
    params: list = [song_id]

    if after_ts:
        sql += ' AND ts >= ?'
        params.append(after_ts)
    if before_ts:
        sql += ' AND ts <= ?'
        params.append(before_ts)

    sql += f' ORDER BY ts DESC'

    with _db() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [
        Listen(
            played_for=row['ms_played'],
            finished_playing=datetime.fromtimestamp(row['ts'] / 1000),
            played_from=row['statsfm_id'],
        )
        for row in rows
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

    if _within_local(before):
        return _local_song_plays(song_id, after=after, before=before)

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


def _local_song_plays(
    song_id: str,
    *,
    after: Union[int, None] = None,
    before: Union[int, None] = None,
) -> int:
    """Serves song_plays entirely from the local DB."""

    sql = 'SELECT COUNT(*) as cnt FROM listens WHERE statsfm_id = ?'
    params: list = [song_id]

    if after:
        sql += ' AND ts >= ?'
        params.append(after)
    if before:
        sql += ' AND ts <= ?'
        params.append(before)

    with _db() as conn:
        return conn.execute(sql, params).fetchone()['cnt']


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

    The return is a list of `Position` objects with related id, plays, and
    place information attached.
    """

    after = _timestamp_check(after)
    before = _timestamp_check(before)

    if _within_local(before):
        # local is auto adjusted
        return _local_songs_week(after, before)

    if _ts(after) < _latest_stream_ts() and _ts(before) > _latest_stream_ts():
        # we have a section which is covered by our current local data,
        # and then a section which isn't.

        local_week = _local_songs_week(after, _latest_stream_ts())
        statsfm_week = songs_week(_latest_stream_ts(), before)

        # and then we go ham with merging
        combined: dict[str, int] = defaultdict(int)
        for pos in local_week:
            combined[pos.id] += pos.plays
        for pos in statsfm_week:
            combined[pos.id] += pos.plays

        info = [
            Position(id=song_id, plays=plays, place=0)
            for song_id, plays in combined.items()
        ]

        for pos in info:
            pos.place = len([i for i in info if i.plays > pos.plays]) + 1
        return sorted(info, reverse=True, key=lambda i: i.plays)

    # max limit for this request is 500 songs and not the 10,000 like others have
    address = (
        f'https://api.stats.fm/api/v1/users/{user}/top/tracks'
        f'?after={after}&before={before}'
        '&limit=500'
    )

    r = _get_address(address)
    additions: list[dict] = r.json()['items']
    items: list[dict] = additions

    # spotistats has different moods: sometimes it will faithfully return all 500 items
    # if you ask for 500 items, other times there will be just a couple items missing,
    # and sometimes they have a big purge, and a request of 500 items will return like 350.
    # querying for the next 500 items isn't great when the system is actually working great,
    # because it's an additional blocking request we have to go through, but this also means
    # that we ensure no data gets lost.

    offset = 500
    while len(additions) > 0:
        address = (
            f'https://api.stats.fm/api/v1/users/{user}/top/tracks'
            f'?after={after}&before={before}'
            f'&limit=500&offset={offset}'
        )
        r = _get_address(address)
        additions = r.json()['items']
        items.extend(additions)
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


def _local_songs_week(
    after: int,
    before: int,
) -> list[Position]:
    """
    Serves songs_week entirely from the local DB.
    This call is automatically adjusted, as the local database
    pre-filters out the overstreamed songs.
    """

    sql = """
        SELECT   statsfm_id, COUNT(*) as streams
        FROM     listens
        WHERE    statsfm_id IS NOT NULL
          AND    ts >= ?
          AND    ts <= ?
        GROUP BY statsfm_id
        ORDER BY streams DESC
    """

    with _db() as conn:
        rows = conn.execute(sql, [after, before]).fetchall()

    info: list[Position] = [
        Position(id=row['statsfm_id'], plays=row['streams'], place=0)
        for row in rows
        # we also don't check for banned ids, as the pre-processing already does this.
    ]

    for pos in info:
        pos.place = sum(1 for i in info if i.plays > pos.plays) + 1
    return info
