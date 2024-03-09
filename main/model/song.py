"""
levboard/main/model/song.py

Contains the central Song model.
"""

from itertools import chain
from collections import Counter
from datetime import date, timedelta
from operator import attrgetter
from pydantic import ValidationError, BaseModel
from typing import Iterable, Iterator, Optional

from . import spotistats
from .cert import SongCert
from .entry import Entry
from .spotistats import MAX_ADJUSTED, SONG_CHART_LENGTH


class Variant(BaseModel):
    main_id: str
    title: str
    ids: set[str]
    artists: tuple[str, ...]

    def to_dict(self):
        return {
            'main_id': self.main_id,
            'title': self.title,
            'ids': list(self.ids),
            'artists': list(self.artists),
        }

    def __hash__(self):
        return hash((self.title, self.main_id))

    def __eq__(self, other):
        return self.ids == other.ids

    @classmethod
    def from_id(cls, main_id) -> 'Variant':
        info = spotistats.song_info(main_id)
        title = info['name']
        artists = tuple(i['name'] for i in info['artists'])

        return cls(
            main_id=main_id, title=title, ids={main_id}, artists=artists
        )


class Song:
    """
    Represents a song in a user's listening charts.

    Arguments:
    * song_id (`str`): The song's unique Spotistats id, as a numeric string.
    * song_title (optional `str`): The title of the song that the system will use.
        Needs to be unique across all songs. Defualts to the song's official
        title if none is specified.
    * load (keyword-only `bool`): If the song metadata needs to be loaded or not.
        Defaults to `True`, but should be overwritten only if is being constructed
        from storage.

    Attributes:
    * id (`str`): The Spotistats id of the song.
    * title (`str`): The specified title of the song.
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
        Spotistats, including the artists, the official title, and the song's
        current play count.
    """

    def __init__(
        self,
        song_id: str,
        song_title: Optional[str] = None,
        *,
        load: bool = True,
    ):
        self.main_id: str = song_id
        self.title: str = song_title
        self.main_variant = Variant(
            main_id=self.main_id,
            title=self.title,
            ids={
                self.main_id,
            },
            artists=[],
        )
        self.variants: set[Variant] = {self.main_variant}
        self.active = self.main_variant
        self._plays: int = 0
        self._entries: dict[date, Entry] = {}
        self.__listens: Optional[list[spotistats.Listen]] = None

        # configured by _load_info()
        # declared here for cpython reasons
        self.artists: list[str] = []
        self.official_name: str = ''

        if load:
            self._load_info()

    def _load_info(self):
        """
        (internal method) Retreives the metadata for the song id from
        Spotistats, including the artists, the official name, and the song's
        current play count.
        """

        info = spotistats.song_info(self.main_id)

        self.official_name = info['name']
        self.artists = [i['name'] for i in info['artists']]

        # for when the name wasn't specified (defaults to `None`)
        if self.title is None:
            self.title = self.official_name

        if self.__listens is None:
            self._populate_listens()

    def __hash__(self) -> int:
        return hash((self.title, tuple(self.ids)))

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self.ids == other.ids
        return NotImplemented

    def __str__(self) -> str:
        return f'{self.title} by {self.str_artists}'

    def __repr__(self) -> str:
        return f'Song({self.main_id!r}, {self.title!r})'

    def __format__(self, fmt: str) -> str:
        # flags are "o" and "s"
        fmt = fmt.lower().strip()

        if not fmt or fmt == 's':
            # simple version / same as str
            return str(self)

        if fmt[-1] not in ('o', 's'):
            # format flag not passed in so probably was some sort of str
            # formatting. will throw an error if it doens't work for it
            return format(str(self), fmt)

        if len(fmt) != 1:
            # format flags for both how we want the song and alignment.
            # such as {song:5<o} will process it with the "o" flag and
            # then align the str result 5 spaces to the left.
            return format(format(self, fmt[-1]), fmt[:-1])

        if fmt == 'o':
            # official formatting, like "No Lie (ft. Dua Lipa) by Sean Paul"
            artists = [
                artist
                for artist in self.artists
                if artist not in self.official_name
            ]
            return f'{self.official_name} by {self._combine_artists(artists)}'

        # something didn't work correctly
        raise ValueError(
            'Improper Song formatting. Only the `"o"` and `"s"` flags are '
            'allowed, at the END of any string formatting you want to do '
            'with the string afterwards. (Such as "12<o" will find the '
            'official song name and then left align it in 12 characters '
            'of space.)'
        )

    def _combine_artists(self, iter: Iterable[str]) -> str:
        artists = list(iter)
        if len(artists) == 1:
            return artists[0]
        if len(artists) == 2:
            return ' & '.join(artists)
        return f'{", ".join(artists[:-2])}, {" & ".join(artists[-2:])}'

    @property
    def ids(self) -> set[str]:
        return set(
            chain.from_iterable(variant.ids for variant in self.variants)
        )

    @property
    def sheet_id(self) -> str:
        return min(self.ids)

    @property
    def plays(self) -> int:
        if self.__listens is None:
            return self._plays
        # filtered plays
        play_dates = (i.finished_playing.date() for i in self.__listens)
        date_counter = Counter(play_dates)
        plays = sum(
            min(MAX_ADJUSTED, count) for count in date_counter.values()
        )
        self._plays = plays
        return plays

    def variant_plays(self, variant_id) -> int:
        """
        (`int`): The number of plays a certain variant attached to this
        song has recieved.
        """
        if self.__listens is None:
            self._populate_listens()

        # filtered plays
        play_dates = (
            i.finished_playing.date()
            for i in self.__listens
            if i.played_from in self.get_variant(variant_id).ids
        )
        date_counter = Counter(play_dates)
        return sum(min(MAX_ADJUSTED, count) for count in date_counter.values())

    def variant_points(self, variant_id) -> str:
        """
        (`int`): The number of chart points a certain variant attached to this
        song has recieved.
        """
        return sum(
            ((SONG_CHART_LENGTH + 1) - i.place)
            for i in self.entries
            if i.variant in self.get_variant(variant_id).ids
        )

    def variant_units(self, variant_id) -> int:
        """
        (`int`): The total number of units for a certain variant of this song.
        """

        return (2 * self.variant_plays(variant_id)) + self.variant_points(
            variant_id
        )

    def variant_weeks(self, variant_id) -> int:
        """
        (`int`): The total number of weeks for a certain variant of this song.
        """

        return sum(
            1
            for entry in self.entries
            if entry.variant in self.get_variant(variant_id).ids
        )

    def variant_peak(self, variant_id) -> int:
        """
        (`int`): The chart peak for a certain variant of this song.
            Defaults to 0 if the song never charted.
        """

        return min(
            (
                entry.place
                for entry in self.entries
                if entry.variant in self.get_variant(variant_id).ids
            ),
            default=0,
        )
    
    def variant_weeks(self, variant_id) -> int:
        """
        (`int`): The total number of weeks for a certain variant of this song.
        """

        return sum(
            1
            for entry in self.entries
            if entry.variant in self.get_variant(variant_id).ids and entry.place == self.variant_peak(variant_id)
        )
    


    @property
    def str_artists(self) -> str:
        """
        (`str`): The artists of the song in a consumable form. Will be
        "artist" if there's one artist, "artist1 & artist2" if there are two,
        and "artist1, artist2 & artist3" if there are three or more artists.
        """

        return self._combine_artists(self.artists)

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

        return sum(1 for i in self.entries if i.place == self.peak)

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
        return sum(((SONG_CHART_LENGTH + 1) - i.place) for i in self.entries)

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

        return sorted(self._entries.values(), key=attrgetter('end'))

    @property
    def cert(self) -> SongCert:
        """
        (`SongCert`): The song's certification.
        """

        return SongCert.from_units(self.units)

    def _populate_listens(self) -> None:
        """Adds listens to the song."""

        self.__listens = list(
            chain.from_iterable(
                spotistats.song_play_history(i) for i in self.ids
            )
        )

        if len(self.ids) > 1:
            self._update_version()

    def _update_version(self):
        common = Counter(l.played_from for l in self.__listens)
        self.main_id = common.most_common(1)[0][0]
        self._load_info()

    def period_plays(self, start: date, end: date, adjusted=True) -> int:
        """
        Returns the song's plays for some period.
        """

        if self.__listens is None:
            self._populate_listens()

        listens = (
            listen
            for listen in self.__listens
            if listen.finished_playing.date() >= start
            and listen.finished_playing.date() <= end
        )

        if not adjusted:
            # we don't have to filter out any days that have
            # too many streams, so simple route
            return len(list(listens))

        play_dates: Iterator[date] = (
            listen.finished_playing.date() for listen in listens
        )

        date_counter = Counter(play_dates)

        return sum(min(MAX_ADJUSTED, count) for count in date_counter.values())

    def period_points(self, start: date, end: date, strict=True) -> int:
        """Returns the song's points gained for some period."""

        return sum(
            ((SONG_CHART_LENGTH + 1) - i.place)
            for i in self.entries
            if i.end >= start
            and i.end <= end
            and (not strict or i.variant in self.ids)
        )

    def period_weeks(self, start: date, end: date, strict=True) -> int:
        return sum(
            1
            for w in self.entries
            if w.end >= start
            and w.end <= end
            and (not strict or w.variant in self.ids)
        )

    def period_units(
        self,
        start: date,
        end: date,
        adjusted=True,
    ) -> int:
        """
        Returns the song's units gained for some period.
        """
        return self.period_plays(
            start, end, adjusted
        ) * 2 + self.period_points(start, end)

    def add_variant(self, variant: Variant) -> None:
        """Links together a new variant into the song."""
        self.variants.add(variant)
        self.ids.update(variant.ids)

    def get_variant(self, variant_id: str) -> Variant:
        # TODO: rewrite variant storage to speed up lookup
        try:
            return next(
                variant
                for variant in self.variants
                if variant_id in variant.ids
            )
        except StopIteration:
            raise KeyError(
                f'No variant of id {variant_id} found attached to instance.'
            )

    def add_entry(self, entry: Entry) -> None:
        """
        Adds an entry, as an `Entry` object into the song data.

        Arguments:
            entry (`Entry`): The entry to add to the song.
        """

        if entry.end in self._entries.keys():
            if entry.plays > self.get_entry(entry.end, strict=False).plays:
                self._entries[entry.end] = entry
            return
        else:
            self._entries[entry.end] = entry

        self.active = next(
            (var for var in self.variants if entry.variant in var.ids),
            self.main_variant,
        )

    def get_entry(
        self, end_date: date, variant: Optional[str] = None
    ) -> Optional[Entry]:
        """
        Retrieves a stored entry.

        Arguments:
        * end_date (`datetime.date`): The week end of the entry to be found.
        * strict (optional `bool`): Whether the entry returned must be of this
            specific variant. Defaults to `True`.

        Returns:
        * entry (Optional `Entry`): The entry at that end date, if there is one,
            or `None` otherwise.
        """
        possible = self._entries.get(end_date)

        if not variant:
            return possible

        try:
            variant_ids = next(
                v.ids for v in self.variants if variant in v.ids
            )
        except StopIteration:
            raise KeyError('variant not found')

        return (
            possible
            if ((possible is not None) and (possible.variant in variant_ids))
            else None
        )

    def update_plays(self, adjusted=True) -> None:
        """
        Updates the lifetime plays for the song.
        The `adjusted` flag marks if play data will be filtered or not.
        """

        if adjusted:
            self._plays = self.adjusted_plays()
            return

        if self.__listens is None:
            self._populate_listens()

        self._plays = len(self.__listens)

    def adjusted_plays(self) -> int:
        """
        Returns the adjusted plays for a song. Adjusted plays count all
        streams, unless a song got over a benchmark within a day, so it
        will count up to that mark and no more.
        """

        self._populate_listens()

        if self.plays <= MAX_ADJUSTED:
            return self.plays

        play_dates: Iterable[date] = (
            listen.finished_playing.date() for listen in self.__listens
        )
        date_counter = Counter(play_dates)

        total = 0

        for count in date_counter.values():
            total += count if count < MAX_ADJUSTED else MAX_ADJUSTED

        return total

    def add_alt(self, alt_id: str) -> None:
        """
        Adds an alternate id to the song. Alternate ids should only be song ids
        of songs that should be merged but aren't for some reason in the
        Spotistats system, such as remastered versions.
        """

        if alt_id not in self.ids:
            self.add_variant(Variant.from_id(alt_id))

    def get_weeks(self, top: Optional[int] = None) -> int:
        """
        Returns the total number of weeks the song has charted in the top `top`
        of the chart, or the total number of weeks charted if `top` is `None`
        or not specified.
        """

        if top is None:
            return self.weeks

        return len(1 for entry in self._entries if entry.place <= top)

    def get_conweeks(
        self, breaks: bool = False, top: Optional[int] = None
    ) -> int:
        """
        The greatest number of consecutive weeks the song has spent in the top
        `top` of the chart. Will return 0 if the song has never charted or
        never charted in that region. Allows for songs to leave for 1 week if
        `breaks` is true. CCC_CCCCC_C will return 5 if `breaks` is false but 11
        if it's true.
        """

        entries = self.entries  # returns a copy, so we can pop
        if top:
            entries = [i for i in entries if i.place <= top]

        if len(entries) in (0, 1):
            return len(entries)

        longest = 0
        current_entry = entries.pop(0)

        while entries:
            streak = 1
            next_entry = entries.pop(0)

            while (
                (current_entry.end == next_entry.start)
                # standard mode where the next week charted too
                or (
                    breaks
                    and (current_entry.end + timedelta(days=7))
                    == next_entry.start
                )
            ):
                # with breaks mode where the next week didn't chart but we have
                # break mode turned on and the week after that charted.

                streak += 1
                if current_entry.end != next_entry.start:
                    streak += 1

                current_entry = next_entry
                try:
                    next_entry = entries.pop(0)
                except IndexError:
                    break

            longest = max(longest, streak)
            current_entry = next_entry

        return longest

    def all_consecutive(self, breaks=False) -> list[tuple[date, int]]:
        entries = self.entries

        if len(entries) == 0:
            return []

        consecutive = []
        current_entry = entries.pop(0)

        while entries:
            starting_entry = current_entry
            streak = 1
            next_entry = entries.pop(0)

            while (
                (current_entry.end == next_entry.start)
                # standard mode where the next week charted too
                or (
                    breaks
                    and (current_entry.end + timedelta(days=7))
                    == next_entry.start
                )
            ):
                # with breaks mode where the next week didn't chart but we have
                # break mode turned on and the week after that charted.

                streak += 1
                current_entry = next_entry
                try:
                    next_entry = entries.pop(0)
                except IndexError:
                    break

            consecutive.append((starting_entry.end, streak))
            current_entry = next_entry

        return consecutive

    def to_dict(self) -> dict:
        """
        Collects the song as a simple dictionary object for storing.

        Returns:
        * song_dict (`dict`): The song and all of the contained objects as a dictionary.
        """

        return {
            'title': self.title,
            'main_id': self.main_id,
            'ids': list(self.ids),
            'artists': self.artists,
            'official_name': self.official_name,
            'plays': self.plays,
            'entries': [i.to_dict() for i in self.entries],
            'variants': list(variant.to_dict() for variant in self.variants),
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
            new = cls(
                song_id=info['main_id'],
                song_title=info['title'],
                load=False,
            )

            new.artists = list(info['artists'])
            new.official_name = str(info['official_name'])
            new.variants = set(Variant(**i) for i in info['variants'])
            new._plays = int(info['plays'])
            new._entries = {
                date.fromisoformat(i['end']): Entry(**i)
                for i in info['entries']
            }

        except (KeyError, AttributeError, ValidationError) as exc:
            raise ValueError(
                "Dictionary doesn't have the required fields, only ones with the same "
                'signature as the ones returned by `Song.to_dict()` are accepted.'
            ) from exc
        else:
            return new

    @classmethod
    def from_variants(
        cls, main_id: str, variants: Iterable[Variant]
    ) -> 'Song':
        """Forms a new song from the song's variants and a main id denoting which one
        is the most important.

        Arguments:
        * main_id (`str`): The song to be created's main id.
        * variants (`Iterable[Variant]`): All variants of that song.

        Returns:
        * new_song (`Song`): The song back as a Song class.

        Raises:
        * `ValueError`: If main_id doens't match up with any of the variants provided.
        """

        try:
            main_variant = next(
                variant for variant in variants if main_id in variant.ids
            )
        except StopIteration:
            raise ValueError(
                f'Missing the variant `main_id` ({main_id}) belongs to in `variants`.'
            )

        new = cls(
            song_id=main_variant.main_id,
            song_title=main_variant.title,
            load=False,
        )

        new.artists = list(main_variant.artists)
        new.variants = set(variants)

        return new
