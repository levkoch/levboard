"""
levboard/main/model/song.py

Contains the central Song model.
"""

from copy import deepcopy
from typing import Optional
from datetime import date
from pydantic import ValidationError

from .cert import SongCert
from .entry import Entry
from .spotistats import song_info, song_plays


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
        self.alt_ids: set[str] = set()
        self.plays: int = 0
        self._entries: list[Entry] = []

        # configured by _load_info()
        # declared here for cpython reasons
        self.artists = []
        self.official_name: str = ''

        if load:
            self._load_info()

    def _load_info(self):
        """
        (internal method) Retreives the metadata for the song id from
        Spotistats, including the artists, the official name, and the song's
        current play count.
        """

        info = song_info(self.id)

        self.official_name = info['name']
        self.artists = [i['name'] for i in info['artists']]

        # for when the name wasn't specified (defaults to `None`)
        if self.name is None:
            self.name = self.official_name

    def __hash__(self) -> int:
        return hash((self.name, self.id))

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self.id == other.id
        return NotImplemented

    def __str__(self) -> str:
        return f'{self.name} by {self.str_artists}'

    def __repr__(self) -> str:
        return f'Song({self.id!r}, {self.name!r})'

    @property
    def str_artists(self) -> str:
        """
        (`str`): The artists of the song in a consumable form. Will be
        "artist" if there's one artist, "artist1 & artist2" if there are two,
        and "artist1, artist2 & artist3" if there are three or more artists.
        """

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
        Returns the song's plays for some period.
        """

        plays = song_plays(self.id, after=start, before=end)

        for alt_id in self.alt_ids:
            plays += song_plays(alt_id, after=start, before=end)

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

        self.plays = song_plays(self.id)

        for alt_id in self.alt_ids:
            self.plays += song_plays(alt_id)

    def add_alt(self, alt_id: str) -> None:
        """
        Adds an alternate id to the song. Alternate ids should only be song ids
        of songs that should be merged but aren't for some reason in the
        Spotistats system, such as remastered versions.
        """

        ids = self.alt_ids
        ids.add(alt_id)
        self.alt_ids = {i for i in ids if i != self.id}

    def get_weeks(self, top: Optional[int] = None) -> int:
        """
        Returns the total number of weeks the song has charted in the top `top`
        of the chart, or the total number of weeks charted if `top` is `None`
        or not specified.
        """

        if top is None:
            return self.weeks

        return len([entry for entry in self._entries if entry.place <= top])

    def get_conweeks(self, top: Optional[int] = None) -> int:
        """
        The greatest number of consecutive weeks the song has spent in the top
        `top` of the chart. Will return 0 if the song has never charted or
        never charted in that region.
        """

        entries = self.entries # returns a copy, so we can pop
        if top:
            entries = [i for i in entries if i.place <= top]

        if len(entries) in (0, 1):
            return len(entries)

        longest = 0
        current_entry = entries.pop(0)

        while entries:
            streak = 1
            next_entry = entries.pop(0)

            while current_entry.end == next_entry.start:
                streak += 1
                current_entry = next_entry
                try:
                    next_entry = entries.pop(0)
                except IndexError:
                    break

            longest = max(longest, streak)
            current_entry = next_entry

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

            new.alt_ids = set(info['alt_ids'])
            new.artists = info['artists']
            new.official_name = info['official_name']
            new.plays = info['plays']
            new._entries = [Entry(**i) for i in info['entries']]
            new._entries.sort(key=lambda i: i.end)  # from earliest to latest

        except (KeyError, AttributeError, ValidationError) as exc:
            raise ValueError(
                "Dictionary doesn't have the required fields, only ones with the same "
                'signature as the ones returned by `Song.to_dict()` are accepted.'
            ) from exc
        else:
            return new
