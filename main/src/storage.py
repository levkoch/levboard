from typing import Any, Iterator, Optional

from .model import Song
from .config import Config


class SongRepository:
    """
    Stores all of the songs in the song file.

    Arguments:
    * song_dict (`Optional[dict]`): The dictionary to recreate a repository from.
        Defaults to None, which starts the repository with no songs in it.

    Attributes:
    * _songs (`dict[str, Song]`): The songs stored in the repository, mapping from
        song id to the song object.

    Methods:
    * get (optional `Song` method): Retrieves a `Song` by song id, or `None` if none
        with the specified id are found.
    * add (method): Adds a `Song` into the repository.
    * list (`list[str]` method): Returns all of the song ids stored.
    """

    __slots__ = ('_songs',)

    def __init__(self, songs: Optional[dict] = None):
        self._songs: dict[str, Song] = []
        self._load(songs if songs is not None else {})

    def _load(self, songs) -> None:
        self._songs = {}
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
        Retrieves a `Song` by song id, or `None` if none with the specified
        id are found.
        """
        return self._songs.get(song_id)

    def get_by_name(self, song_name: str) -> Optional[Song]:
        """
        Retrieves a song by the song name. Is NOT case sensitive. Will first
        try to match the whole song name, and then will match the beginning
        of the song name from the query, and returns `None` if nothing
        fitting was found in either case.
        """
        try:
            return next(
                i
                for i in self._songs.values()
                if i.name.lower() == song_name.lower()
            )
        except StopIteration:
            return next(
                (
                    i
                    for i in self._songs.values()
                    if i.name.lower().startswith(song_name.lower())
                ),
                None,
            )

    def __iter__(self) -> Iterator[Song]:
        # this is implemented this way, as using iter(self._songs.values())
        # causes songs with multiple ids to be sent out multiple times,
        # which is not what is intended

        sent_ids: set[str] = set()
        for song in self._songs.values():
            # check if has already sent a song with that id and send if hasn't
            if song.main_id not in sent_ids:
                sent_ids.add(song.main_id)
                yield song

    def add(self, song: Song) -> None:
        """Adds a `Song` into the repository."""
        self._songs[song.main_id] = song

        # for every alternate id (so the symmetric difference [appears in one
        # but not both] between the set of all ids and the set of just the
        # main id.)
        for alt_id in song.ids ^ {song.main_id}:
            self._songs[alt_id] = song

    def list(self) -> list[str]:
        """Returns all of the song ids stored."""
        return list(self._songs.keys())

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """returns the song respository as a dictionary."""
        return {song.main_id: song.to_dict() for song in self}


class Process:
    """
    A single process for managing user data. Contains their settings along
    with all of the songs they've charted.

    Arguments:
    - `session` (`dict`): A dictionary to create a config instance from.
        Must include a "username" field so that we know who's data to look at.

    Attributes:
    - `config` (`config.Config`): The user's information and settings.
    - `songs` (`storage.SongRepository`): The user's songs.

    Using:
    ```python
    with Process({'username': 'lev'}) as process:
        # start a process to page through their data somehow
    ```
    """

    __slots__ = ('config', 'songs', '_session')

    songs: SongRepository
    config: Config

    def __init__(self, session: dict):
        self._session = session

    def __enter__(self):
        self.config = Config(self._session)
        self.songs = SongRepository(self._session.get('songs'))
        return self

    def __exit__(self, *_):
        self._session.update(self.config.to_dict())
