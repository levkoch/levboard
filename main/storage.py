import json

from typing import Iterator, Optional, Generator

from model import Song, Album
from config import SONG_FILE, ALBUM_FILE


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

    def __init__(self, *, song_file: str = SONG_FILE):
        self._songs: dict[str, Song] = []
        self._file = song_file
        self._load()
        self.seen: set[Song] = set()

    def _load(self) -> None:
        with open(self._file, 'r') as f:
            songs: dict[str, dict] = json.load(f)

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
        Retrieves a `Song` by song id, or `None` if none with the specified id are found.
        """
        song = self._songs.get(song_id)
        if song:
            self.seen.add(song)
        return song

    def get_by_name(self, song_name: str) -> Optional[Song]:
        """
        Retrieves a song by the song name. Is NOT case sensitive. Will first
        try to match the whole song name, and then will match the beginning
        of the song name from the query, and returns `None` if nothing
        fitting was found in either case.
        """
        try:
            match = next(
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
        else:
            return match

    def __iter__(self) -> Iterator[Song]:
        # this is implemented this way, as using iter(self._songs.values())
        # causes songs with multiple ids to be sent out multiple times,
        # which is not what is intended

        sent_ids: list[str] = []
        for song in self._songs.values():
            # check if has already sent a song with that id and send if hasn't
            if song.id not in sent_ids:
                sent_ids.append(song.id)
                yield song

    def add(self, song: Song) -> None:
        """Adds a `Song` into the repository."""
        self._songs[song.id] = song
        self.seen.add(song)
        for alt_id in song.alt_ids:
            self._songs[alt_id] = song

    def list(self) -> list[str]:
        """Returns all of the song ids stored."""
        return list(self._songs.keys())


class AlbumRepository:
    __slots__ = ['seen', '_albums', '_file']

    def __init__(self, *, album_file: str = ALBUM_FILE):
        self._albums: dict[str, Album] = []
        self._file = album_file
        self._load()
        self.seen: set[Album] = set()

    def _load(self) -> None:
        with open(self._file, 'r') as f:
            albums: dict[str, dict] = json.load(f)

        self._albums = {}

        for album_name, album_dict in albums.items():
            self._albums[album_name] = Album.from_dict(album_dict)

    def __iter__(self) -> Iterator[Album]:
        return iter(self._albums.values())

    def get(self, album_name: str) -> Optional[Album]:
        """
        Retrieves a `Album` by name, or `None` if that name isn't found found.
        """
        album = self._albums.get(album_name)
        if album:
            self.seen.add(album)
        return album

    def add(self, album: Album) -> None:
        """Adds a `Album` into the repository."""
        self._albums[album._title] = album
        self.seen.add(album)

    def list(self) -> list[str]:
        """Returns all of the album names stored."""
        return list(self._albums.keys())


class SongUOW:
    """
    A unit of work infrastructure ease of access thingy.

    Arguments:
    * song_file (optional keyword-only `str`): The full path to the song file the
    UOW will read data to and from.
    * album_file (optional keyword-only `str`): The full path to the album file
    to read data to and from.

    Attributes:
    * songs (`SongRepository`): The songs stored in the song file.
    * albums (`AlbumRepository`): The albums stored in the album file.

    Methods:
    * commit (method): Saves any changes made while using objects from the UOW.
    * collect_new_events (`Generator[Event]` method): Makes events created by
        any of the objects avaliable.
    """

    __slots__ = ['songs', 'albums']

    def __init__(
        self, *, song_file: str = SONG_FILE, album_file: str = ALBUM_FILE
    ):
        self.songs = SongRepository(song_file=song_file)
        self.albums = AlbumRepository(album_file=album_file)
        self._attach_songs()

    def _attach_songs(self) -> None:
        for album in self.albums._albums.values():
            for stored_id in album.stored_ids:
                album.add_song(self.songs.get(stored_id))
            del album.stored_ids

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

        albums = {k: v.to_dict() for k, v in self.albums._albums.items()}
        with open(self.albums._file, 'w') as f:
            json.dump(albums, f, indent=4)

    def collect_new_events(self) -> Generator:
        """Makes events avaliable for later usage"""

        for song in self.songs.seen:
            while song.events:
                yield song.events.pop(0)
        self.songs.seen.clear()

        for album in self.albums.seen:
            while album.events:
                yield song.events.pop(0)
        self.albums.seen.clear()
