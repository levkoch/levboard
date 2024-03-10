"""
levboard/main/model/album.py

Where the Album model is held.
"""

from concurrent import futures
from copy import deepcopy
from datetime import date
from operator import methodcaller
from typing import Iterable, Iterator, Optional, Union

from .cert import AlbumCert, SongCert
from .entry import AlbumEntry
from .song import SONG_CHART_LENGTH, Song


class Album:
    def __init__(self, title: str, artists: Union[Iterable[str], str]):
        self._title: str = title
        self._artists: list[str]

        if isinstance(artists, str):
            self._artists = artists.split(', ')
        else:  # is an iterable of str
            self._artists = list(artists)

        self.songs: list[tuple[str, Song]] = []
        self.entries: list[AlbumEntry] = []

    def __str__(self) -> str:
        return f'{self.title} by {self.str_artists}'

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return f'{name}({self.title!r}, {self.artists!r})'

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self.title == other.title
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.__class__, self._title))

    def __contains__(self, song: Song) -> bool:
        return song in self.songs

    def __len__(self) -> int:
        return len(self.songs)

    def __iter__(self) -> Iterator[tuple[str, Song]]:
        return iter(self.songs)

    @property
    def title(self) -> str:
        """
        (`str`): The title of the album.
        """
        return self._title

    @property
    def artists(self) -> list[str]:
        """
        (`list[str]`): The album's artist(s).
        """
        return deepcopy(self._artists)

    @property
    def str_artists(self) -> str:
        """
        (`str`): The album's artists, in a human-friendly form.
        """
        if len(self.artists) == 1:
            return self.artists[0]
        if len(self.artists) == 2:
            return ' & '.join(self.artists)
        return (
            f'{", ".join(self.artists[:-2])}, {" & ".join(self.artists[-2:])}'
        )

    @property
    def units(self) -> int:
        """
        (`int`): The total amount of units from the album.
        """

        return sum(
            song.variant_units(variant_id) for variant_id, song in self.songs
        )

    @property
    def plays(self) -> int:
        """
        (`int`): The total streams of the album.
        """
        return sum(
            song.variant_plays(variant_id) for variant_id, song in self.songs
        )

    @property
    def points(self) -> int:
        """(`int`): The total song points for the album."""
        return sum(
            song.variant_points(variant_id) for variant_id, song in self.songs
        )

    @property
    def total_song_weeks(self) -> int:
        """
        (`int`): The total weeks charted by songs in the album.
        """
        return sum(
            song.variant_weeks(variant_id) for variant_id, song in self.songs
        )

    @property
    def top_song_peak(self) -> int:
        """
        (`int`): The highest peak among songs in the album.
        """
        return min(
            song.variant_peak(variant_id) for variant_id, song in self.songs
        )

    @property
    def total_song_peak_weeks(self) -> int:
        """
        (`int`): The total number of weeks spent by songs in the album at the
        songs' peaks. (If two songs both are the highest peak among songs on
        the album, and peaked at #2 for 2 weeks, it'll return `4`.)
        """
        return sum(
            song.peakweeks
            for _, song in self.songs
            if song.peak == self.top_song_peak
        )

    @property
    def peak(self) -> int:
        """
        (`int`): The highest peak of the album on the chart. Defaults to
        `0` if the album has never charted.
        """

        return min([i.place for i in self.entries], default=0)

    @property
    def peakweeks(self) -> int:
        """
        (`int`): The number of weeks the album has spent at peak,
        defaulting to `0` if the album has never charted.
        """

        return len([i for i in self.entries if i.place == self.peak])

    @property
    def weeks(self) -> int:
        """
        (`int`): The total number of weeks the album has charted for.
        """

        return len(self.entries)

    @property
    def cert(self) -> AlbumCert:
        """
        (`AlbumCert`): The album's certification.
        """

        return AlbumCert.from_units(self.units)

    def charting_songs(self, end_date: date) -> int:
        """The number of songs that charted the week of"""
        return len(
            [
                song
                for song in self.songs
                if song.get_entry(end_date) is not None
            ]
        )

    def get_con_weeks(
        self, top: Optional[int] = None, before: Optional[date] = None
    ) -> int:
        """
        The greatest number of consecutive weeks the album has spent in the top
        `top` of the chart and before the `before` date, both if specified. Will
        return 0 if the album has never charted or never charted in that region.
        """

        if None not in (top, before):
            entries = [
                i for i in self.entries if i.place <= top and i.end <= before
            ]
        elif not top is None:
            entries = [i for i in self.entries if i.place <= top]
        elif not before is None:
            entries = [i for i in self.entries if i.end <= before]
        else:
            entries = list(self.entries)

        if len(entries) in {0, 1}:
            return len(entries)

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

    def get_weeks_top(
        self, *, top: Optional[int] = None, before: Optional[date] = None
    ) -> int:
        """
        the number of weeks the album spent in the top `top` before &
        including the week ending `before`, both arguments are optional
        and including just one works as well. Defaults to the number
        of weeks the album has spent charting.
        """

        if top and before:   # filter by both
            return len(
                [
                    1
                    for entry in self.entries
                    if entry.place <= top and entry.end <= before
                ]
            )
        if top:   # filter only by top
            return len([1 for entry in self.entries if entry.place <= top])
        if before:   # filter only by weeks before
            return len([1 for entry in self.entries if entry.end <= before])
        return self.weeks   # dont filter whatsoever

    def get_song_weeks(self, top: Optional[int] = None) -> int:
        """(`int`): The total weeks charted in the top `top` by songs from the album."""
        return sum(song.get_weeks(top) for song in self.songs)

    def get_hits(self, top: Optional[int] = None) -> int:
        """The number of songs from the album that entered the top `top`."""
        if top is None:
            return len([song for song in self.songs if song.peak != 0])

        return len(
            [
                song
                for song in self.songs
                if song.peak <= top and song.peak != 0
            ]
        )

    def song_cert_count(self, cert: Optional[SongCert] = None):
        """The number of songs on the album that have reached `cert` level or higher."""
        if cert is None:
            return len(self)

        return len([song for song in self.songs if song.cert >= cert])

    def song_charted_count(self, weeks: Optional[int]) -> int:
        """The number of songs that charted for at least `weeks` weeks."""
        if weeks is None:
            return len([song for song in self.songs if song.weeks != 0])
        return len([song for song in self.songs if song.weeks >= weeks])

    def add_song(self, song: Song, variant_id: str):
        """
        Adds a song into the album, if not already in album.
        """

        if song not in self.songs:
            self.songs.append((variant_id, song))

    def add_entry(self, entry: AlbumEntry) -> None:
        """Adds an entry to the album."""
        if entry.end not in [i.end for i in self.entries]:
            self.entries.append(entry)
            self.entries.sort(key=lambda i: i.end)

    def get_entry(self, end_date: date) -> Optional[AlbumEntry]:
        """
        Returns the entry for the week ending in `end_date`, or None if the
        album didn't chart that week.
        """
        return next((i for i in self.entries if i.end == end_date), None)

    def period_plays(self, start: date, end: date) -> int:
        """
        Returns the plays for a period of time.
        """
        with futures.ThreadPoolExecutor() as executor:
            return sum(
                executor.map(
                    methodcaller('period_plays', start=start, end=end),
                    self.songs,
                )
            )

    def period_units(self, start: date, end: date) -> int:
        with futures.ThreadPoolExecutor() as executor:
            return sum(
                executor.map(
                    methodcaller('period_units', start=start, end=end),
                    self.songs,
                )
            )

    def period_weeks(self, start: date, end: date) -> int:
        return sum(
            1 for w in self.entries if w.start >= start and w.end <= end
        )

    def get_points(self, end_date: date) -> int:
        """
        Returns the total points collected by the album that tracking week.
        """

        points = 0
        for variant_id, song in self.songs:
            entry = song.get_entry(end_date, variant_id=variant_id)
            if entry:  # (is not None)
                points += (SONG_CHART_LENGTH + 1) - entry.place
        return points

    def to_dict(self) -> dict:
        return {
            'title': self._title,
            'artists': ', '.join(self._artists),
            'songs': [variant_id for variant_id, _ in self.songs],
            'entries': [i.to_dict() for i in self.entries],
        }

    @classmethod
    def from_dict(cls, info: dict) -> 'Album':
        new = cls(info['title'], info['artists'])
        new.entries = [AlbumEntry(**i) for i in info['entries']]
        new.entries.sort(key=lambda i: i.end)  # from earliest to latest

        new.stored_ids = []
        for song_id in info['songs']:
            new.stored_ids.append(song_id)
        return new
