"""
levboard/main/model

This package contains all of the data and functional models.

Models:
* Song: Represents a chartable song.
* Album: Represents a collection of songs.
* SongCert, AlbumCert: Song and Album certifications, respectively.

Value Models:
* Entry, AlbumEntry: Represents when a Song or Album has charted.

Enums:
* CertType: The different certification statuses a song/album could have.
"""

from .album import Album
from .cert import AlbumCert, CertType, SongCert
from .entry import AlbumEntry, Entry
from .song import Song

# in alphabetical order
__all__ = [
    'Album',
    'AlbumCert',
    'AlbumEntry',
    'CertType',
    'Entry',
    'Entry',
    'Song',
    'SongCert',
]
