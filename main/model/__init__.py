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

from .cert import SongCert, CertType
from .entry import Entry
from .song import Song

# in alphabetical order
__all__ = [
    'CertType',
    'Entry',
    'Song',
    'SongCert',
]
