import json
from typing import Iterator, Optional

from .model import Song, config


class SongRepository:
    """
    Stores all of the songs in the song file.

    Arguments:
    * song_file (optional keyword-only `str`): The full path to the song file the
    repository will read data to and from.

    Attributes:
    * seen (`set[Song]`): All of the songs used by the repository already.
    * _songs (`dict[str, Song]`): The songs stored in the repository, mapping from
        song id to the song object.
    * _file (`str`): The file path to the song file.

    Methods:
    * get (optional `Song` method): Retrieves a `Song` by song id, or `None` if none
        with the specified id are found.
    * add (method): Adds a `Song` into the repository.
    * list (`list[str]` method): Returns all of the song ids stored.
    """

    __slots__ = ['seen', '_songs', '_file']

    def __init__(self, *, song_file: str = config.SONG_FILE):
        self._songs: dict[str, Song] = {}
        self._file = song_file
        self._load()

    def _load(self) -> None:
        with open(self._file, 'r') as f:
            songs: dict[str, dict] = json.load(f)

        self._songs.clear()
        merged = {}

        for song_id, song_dict in songs.items():
            try:
                merge_to = song_dict['merge']
            except KeyError:
                self._songs[song_id] = Song.from_dict(song_dict)
            else:
                merged[song_id] = merge_to

        for alt_id, merge_to in merged.items():
            merged_into: Song = self._songs[merge_to]
            merged_into.add_alt(alt_id)
            self._songs[alt_id] = merged_into

    def get(self, song_id: str) -> Optional[Song]:
        """
        Retrieves a `Song` by song id, or `None` if none with the specified id are found.
        """

        return self._songs.get(song_id)

    def get_by_name(self, song_name: str) -> Optional[Song]:
        """
        Retrieves a song by the song name. Is NOT case sensitive. Will first
        try to match the whole song name, and then will match the beginning
        of the song name from the query, and returns `None` if nothing
        fitting was found in either case.
        """

        # match entire complete song name (not case sensitive)
        match = next(
            (
                i
                for i in self._songs.values()
                if i.name.lower() == song_name.lower()
            ),
            None,
        )
        # try matching from beginning
        if match is None:
            return next(
                (
                    i
                    for i in self._songs.values()
                    if i.name.lower().startswith(song_name.lower())
                ),
                None,
            )
        return match

    def __iter__(self) -> Iterator[Song]:
        return iter(self._songs.values())

    def add(self, song: Song) -> None:
        """Adds a `Song` into the repository."""
        self._songs[song.id] = song
        for alt_id in song.alt_ids:
            self._songs[alt_id] = song

    def list(self) -> list[str]:
        """Returns all of the song ids stored."""
        return list(self._songs.keys())


class SongUOW:
    """
    A unit of work infrastructure ease of access thingy.

    Arguments:
    * song_file (optional keyword-only `str`): The full path to the song file the
    UOW will read data to and from.

    Attributes:
    * songs (`SongRepository`): The songs stored in the song file.

    Methods:
    * commit (method): Saves any changes made while using objects from the UOW.
    * collect_new_events (`Generator[Event]` method): Makes events created by
        any of the objects avaliable.
    """

    __slots__ = ('songs',)

    def __init__(self, *, song_file: str = config.SONG_FILE):
        self.songs = SongRepository(song_file=song_file)

    def __enter__(self) -> 'SongUOW':
        return self

    def __exit__(self, *args) -> None:
        pass  # we might want to do something here i'm not sure

    def commit(self) -> None:
        """Saves any changes made while using objects from the UOW."""
        songs = {k: v.to_dict() for k, v in self.songs._songs.items()}

        for song_id, song in songs.items():
            if song_id != song['id']:
                songs[song_id] = {'merge': song['id']}

        with open(self.songs._file, 'w') as f:
            json.dump(songs, f, indent=4)
