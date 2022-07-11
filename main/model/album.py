from datetime import date
from typing import Generator, Iterable, Union, Optional
from copy import deepcopy

from .song import Song
from .cert import AlbumCert
from .entry import AlbumEntry


class Album:
    def __init__(self, title: str, artists: Union[Iterable[str], str]):
        self._title: str = title

        if isinstance(artists, str):
            self._artists: list[str] = artists.split(', ')
        else:   # is an iterable of str
            self._artists: list[str] = list(artists)

        self.songs: list[Song] = []
        self.entries: list[AlbumEntry] = []

    def __str__(self) -> str:
        return f'{self.title} by {self.str_artists}'

    __repr__ = __str__

    def __hash__(self) -> int:
        return hash((self.__class__, self._title))

    def __contains__(self, song: Song) -> bool:
        return song in self.songs

    def __len__(self) -> int:
        return len(self.songs)

    def __iter__(self) -> Generator:
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

        return sum(i.units for i in self.songs)

    @property
    def plays(self) -> int:
        """
        (`int`): The total streams of the album.
        """
        return sum(i.plays for i in self.songs)

    @property
    def points(self) -> int:
        """(`int`): The total song points for the album."""
        return sum(i.points for i in self.songs)

    @property
    def song_weeks(self) -> int:
        """
        (`int`): The total weeks charted by songs in the album.
        """
        return sum(song.weeks for song in self.songs)

    @property
    def song_peak(self) -> int:
        """
        (`int`): The highest peak among songs in the album.
        """
        return min(song.peak for song in self.songs)

    @property
    def song_peakweeks(self) -> int:
        """
        (`int`): The total number of weeks spent by songs in the album at the
        songs' peaks. (If two songs both are the highest peak among songs on
        the album, and peaked at #2 for 2 weeks, it'll return `4`.)
        """
        return sum(
            song.peakweeks
            for song in self.songs
            if song.peak == self.song_peak
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

        return AlbumCert(self.units)

    def get_conweeks(self, top: Optional[int] = None) -> int:
        entries = deepcopy(self.entries)
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

    def get_weeks(self, top: Optional[int] = None) -> int:
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

    def get_charted(self, weeks: Optional[int]) -> int:
        """The number of songs that charted for at least `weeks` weeks."""
        if weeks is None:
            return len([song for song in self.songs if song.weeks != 0])
        return len([song for song in self.songs if song.weeks >= weeks])

    def add_song(self, song: Song):
        """
        Adds a song into the album, if not already in album.
        """

        if song not in self.songs:
            self.songs.append(song)

    def add_entry(self, entry: AlbumEntry) -> None:
        if entry.end not in [i.end for i in self.entries]:
            self.entries.append(entry)
            self.entries.sort(key=lambda i: i.end)

    def get_entry(self, end_date: date) -> Optional[AlbumEntry]:
        return next((i for i in self.entries if i.end == end_date), None)

    def period_plays(self, start: date, end: date) -> int:
        """
        Returns the plays for a period of time.
        """

        plays = 0
        for song in self.songs:
            plays += song.period_plays(start, end)
        return plays

    def get_points(self, end_date: date) -> int:
        """
        Returns the total points collected by the album that tracking week.
        """

        points = 0
        for song in self.songs:
            entry = song.get_entry(end_date)
            if entry:  # (is not None)
                points += 61 - entry.place
        return points

    def to_dict(self) -> dict:
        return {
            'title': self._title,
            'artists': ', '.join(self._artists),
            'songs': [song.id for song in self.songs],
            'entries': [i.to_dict() for i in self.entries],
        }

    @classmethod
    def from_dict(cls, info: dict) -> 'Album':
        new = cls(info['title'], info['artists'])
        try:
            new.entries = [AlbumEntry(**i) for i in info['entries']]
        except KeyError:
            new.entries = []
        new.entries.sort(key=lambda i: i.end)  # from earliest to latest
        new.stored_ids = []
        for song_id in info['songs']:
            new.stored_ids.append(song_id)
        return new
