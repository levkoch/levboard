import requests
import time

from copy import deepcopy
from typing import Optional, Union
from datetime import date
from pydantic import (
    BaseModel,
    PositiveInt,
    conint,
    validator,
    ValidationError,
)

from .cert import SongCert


def date_to_timestamp(day: date) -> int:
    """
    Converts a `datetime.date` to a epoch timestamp, as an `int`,
    so that Spotistats registers the day correctly.
    """
    return int(time.mktime(day.timetuple()) * 1000)


class Entry(BaseModel):
    """
    A frozen dataclass representing a chart entry.

    Attributes / Arguments:
    * start (`datetime.date`): The date that the week's entry started. Accepts
        and ISO date string, and will convert it to a `datetime.date` object.
    * end (`datetime.date`): The date that the week's entry ended. Alsoc accepts
        and ISO date string.
    * plays (`int`): The plays the song got that week. Will be greater than `1`.
    * place (`int`): The chart position attained by that song. A positive integer.

    Methods:
    * to_dict (`dict` method): Collects the Entry into a dictionary.
    """

    start: date
    end: date
    plays: conint(gt=1)
    place: PositiveInt

    @validator('start', 'end')
    def format_date(cls, v_date: Union[date, str]):
        if isinstance(v_date, str):
            return date.fromisoformat(v_date)
        if isinstance(v_date, date):
            return v_date
        raise TypeError('Only iso date string or date accepted.')

    def to_dict(self) -> dict:
        """Dictionary representation of entry for storage."""
        return {
            'start': self.start.isoformat(),
            'end': self.end.isoformat(),
            'plays': self.plays,
            'place': self.place,
        }


class Song:
    """
    Represents a song in a user's listening charts.

    Arguments:
    * song_id (`str`): The song's unique Spotistats id, as a numeric string.
    * song_name (optional `str`): The name of the song that the system will use.
        Needs to be unique across all songs. Defualts to the song's official
        name if none is specified.
    * load (keyword-only `bool`): If the song metadata needs to be loaded or not.
        Defaults to `True`, but should be overwritten only if is being constructed
        from storage.

    Attributes:
    * id (`str`): The Spotistats id of the song.
    * name (`str`): The specified name of the song.
    * plays (`int`): The song's plays. Updated by the update_plays() method.
    * last_updated (`datetime.date`): The date of the song plays were updated last.
    * peak (property `int`): The highest peak of the song on the chart. Defaults to
        `0` if the song has never charted.
    * peakweeks (property `int`): The number of weeks the song has spent at peak,
        defaulting to `0` if the song has never charted.
    * weeks (property `int`): The total number of weeks the song has charted for.
    * units (property `int`): The total number of units for the song across all time.
    * entries (property `list[Entry]`): A view-only access to the weeks that the
        song has charted.
    * cert (property `SongCert`): The song's certification, as a `SongCert` object.

    Methods:
    * add_entry (method): Adds an entry, as an `Entry` object into the song data.
    * get_entry (optional `Entry` method): Retrieves a stored `Entry` by the week
        end date, or `None` if it wasn't found.
    * update_plays (method): Updates the lifetime plays for the song.
    * to_dict (`dict` method): Collects the song as a simple dictionary object.
    * from_dict (class method): Forms a new song from a simple dictionary object.
    * Additionally supports hashing, equality comparison, and putting into sets.
    * _load_info (internal method): Retreives the metadata for the song id from
        Spotistats, including the artists, the official name, and the song's
        current play count.
    """

    def __init__(
        self,
        song_id: str,
        song_name: Optional[str] = None,
        *,
        load: bool = True,
    ):
        self.id: str = song_id
        self.name: str = song_name
        self.alt_ids: list[str] = []
        self.plays: int = 0
        self.last_updated: date = date.today()
        self._entries: list[Entry] = []
        self.events = []

        if load:
            self._load_info()

    def __hash__(self) -> int:
        return hash(self.__class__) * 101 + int(self.id)

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self.id == other.id
        raise NotImplementedError(
            f'Unable to compare objects of type Song and {other.__class__}.'
        )

    def __str__(self) -> str:
        return f'{self.name} ({self.id}) by {self.str_artists}'

    __repr__ = __str__

    def _load_info(self):
        """
        (internal method) Retreives the metadata for the song id from
        Spotistats, including the artists, the official name, and the song's
        current play count.
        """

        r = requests.get(f'https://api.stats.fm/api/v1/tracks/{self.id}')
        info = r.json()['item']

        self.official_name = info['name']
        self.artists = [i['name'] for i in info['artists']]

        # for when the name wasn't specified (defaults to `None`)
        if self.name is None:
            self.name = self.official_name

    @property
    def str_artists(self) -> str:
        if len(self.artists) == 1:
            return self.artists[0]
        if len(self.artists) == 2:
            return ' & '.join(self.artists)
        return (
            f'{", ".join(self.artists[:-2])}, {" & ".join(self.artists[-2:])}'
        )

    @property
    def peak(self) -> int:
        """
        (`int`): The highest peak of the song on the chart. Defaults to
        `0` if the song has never charted.
        """

        return min([i.place for i in self.entries], default=0)

    @property
    def peakweeks(self) -> int:
        """
        (`int`): The number of weeks the song has spent at peak,
        defaulting to `0` if the song has never charted.
        """

        return len([i for i in self.entries if i.place == self.peak])

    @property
    def weeks(self) -> int:
        """
        (`int`): The total number of weeks the song has charted for.
        """

        return len(self.entries)

    @property
    def points(self) -> int:
        """
        (`int`): The total number of points for the song.
        """
        return sum((61 - i.place) for i in self.entries)

    @property
    def units(self) -> int:
        """
        (`int`): The total number of units for the song across all time.
        """

        return (2 * self.plays) + self.points

    @property
    def entries(self) -> list[Entry]:
        """
        (`list[Entry]`): A view-only access to the weeks that the
        song has charted.
        """

        return deepcopy(self._entries)

    @property
    def cert(self) -> SongCert:
        """
        (`SongCert`): The song's certification.
        """

        return SongCert(self.units)

    def period_plays(self, start: date, end: date) -> int:
        """
        Returns the plays for a period.
        """

        r = requests.get(
            f'https://api.stats.fm/api/v1/users/lev/streams/tracks/{self.id}/stats'
            f'?after={date_to_timestamp(start)}'
            f'&before={date_to_timestamp(end)}'
        )

        plays = r.json()['items']['count']

        for _id in self.alt_ids:
            r = requests.get(
                f'https://api.stats.fm/api/v1/users/lev/streams/tracks/{_id}/stats'
                f'?after={date_to_timestamp(start)}'
                f'&before={date_to_timestamp(end)}'
            )
            plays += r.json()['items']['count']

        return plays

    def add_entry(self, entry: Entry) -> None:
        """
        Adds an entry, as an `Entry` object into the song data.

        Arguments:
            entry (`Entry`): The entry to add to the song.
        """

        if entry.end in [i.end for i in self._entries]:
            if entry.plays > next(
                (i.plays for i in self._entries if i.end == entry.end)
            ):
                self._entries = [
                    i for i in self._entries if i.end != entry.end
                ]
                self._entries.append(entry)
        else:
            self._entries.append(entry)

        self._entries.sort(key=lambda i: i.end)  # from earliest to latest

    def get_entry(self, end_date: date) -> Optional[Entry]:
        """
        Retrieves a stored entry.

        Arguements:
        * end_date (`datetime.date`): The week end of the entry to be found.

        Returns:
        * entry (Optional `Entry`): The entry at that end date, if there is one,
            or `None` otherwise.
        """

        return next((i for i in self._entries if i.end == end_date), None)

    def update_plays(self) -> None:
        """
        Updates the lifetime plays for the song.
        """

        r = requests.get(
            f'https://api.stats.fm/api/v1/users/lev/streams/tracks/{self.id}/stats'
        )

        self.plays = r.json()['items']['count']

        for _id in self.alt_ids:
            r = requests.get(
                f'https://api.stats.fm/api/v1/users/lev/streams/tracks/{_id}/stats'
            )
            self.plays += r.json()['items']['count']

        self.last_updated = date.today()

    def add_alt(self, alt_id: str) -> None:
        ids = self.alt_ids
        ids.append(alt_id)
        self.alt_ids = list(set([i for i in ids if i != self.id]))

        if self.plays:  # will be `0` if not found already
            self.update_plays()

    def get_weeks(self, top: Optional[int] = None) -> int:
        if top is None:
            return self.weeks

        return len([entry for entry in self._entries if entry.place <= top])

    def get_conweeks(self, top: Optional[int] = None) -> int:
        entries = deepcopy(self._entries)
        if top:
            entries = [i for i in entries if i.place <= top]

        if len(entries) == 0:
            return 0
        if len(entries) == 1:
            return 1

        longest = 0
        current = entries.pop(0)

        while entries:
            streak = 1
            next = entries.pop(0)

            while current.end == next.start:
                streak += 1
                current = next
                try:
                    next = entries.pop(0)
                except IndexError:
                    break

            longest = max(longest, streak)
            current = next

        return longest

    def to_dict(self) -> dict:
        """
        Collects the song as a simple dictionary object for storing.

        Returns:
        * song_dict (`dict`): The song and all of the contained objects as a dictionary.
        """

        return {
            'name': self.name,
            'id': self.id,
            'alt_ids': self.alt_ids,
            'artists': self.artists,
            'official_name': self.official_name,
            'plays': self.plays,
            'last_updated': self.last_updated.isoformat(),
            'entries': [i.to_dict() for i in self._entries],
        }

    @classmethod
    def from_dict(cls, info: dict) -> 'Song':
        """Forms a new song from a simple dictionary object.

        Arguments:
        * info (`dict`): The song as a simple dictionary, as made by a to_dict method.

        Returns:
        * new_song (`Song`): The song back as a Song class.

        Raises:
        * `ValueError`: If `info` doens't have all of the required fields. Check that
            they match the ones returned by the `.to_dict()` method.
        """

        try:
            new = cls(song_id=info['id'], song_name=info['name'], load=False)

            new.alt_ids = info['alt_ids']
            new.artists = info['artists']
            new.official_name = info['official_name']
            new.plays = info['plays']
            new.last_updated = date.fromisoformat(info['last_updated'])
            new._entries = [Entry(**i) for i in info['entries']]
            new._entries.sort(key=lambda i: i.end)  # from earliest to latest

        except (KeyError, ValidationError, AttributeError):
            raise ValueError(
                "Dictionary doesn't have the required fields, only ones with the same "
                'signature as the ones returned by `Song.to_dict()` are accepted.'
            )
        else:
            return new
