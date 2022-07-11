"""
levboard/main/config.py

Contains all of the static and user-configurable variables.

Constats:
* FIRST_DATE: The date to start making charts from.
* ALBUM_FILE: The file to read stored album json from.
* SONG_FILE: The file to read stored song json from.
"""

import pathlib
import time

from datetime import date
from typing import Final

## constants ##

# the first date of my listening
FIRST_DATE: Final[date] = date.fromisoformat('2021-05-13')

## files ##

# find path of where the __main__ program was run
data_dir = pathlib.Path().resolve().as_posix()

# so if someone ran that program inside of levboard/main
if data_dir.endswith('/main'):
    data_dir = data_dir[:-5]   # remove "/main"
data_dir += '/data'

ALBUM_FILE: Final[str] = f'{data_dir}/albums.json'
SONG_FILE: Final[str] = f'{data_dir}/songs.json'

## utility functions ##
def date_to_timestamp(day: date) -> int:
    """
    Converts a `datetime.date` to a epoch timestamp, as an `int`,
    so that Spotistats registers the day correctly.
    """
    return int(time.mktime(day.timetuple()) * 1000)
