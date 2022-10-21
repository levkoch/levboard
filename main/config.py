"""
levboard/main/config.py

Contains all of the static and user-configurable variables.

Constats:
* FIRST_DATE: The date to start making charts from.
* ALBUM_FILE: The file to read stored album json from.
* SONG_FILE: The file to read stored song json from.
"""

import pathlib

from datetime import date
from typing import Final

## constants ##

# the max plays a song can get in one day before getting adjusted
MAX_ADJUSTED: Final[int] = 25
# where my google sheet is located at
LEVBOARD_SHEET: Final[str] = '1_KNcoT92nfgQCRqLH7Iz4ZSxy9hxCd8ll0Hzn9hscqk'
# the first date of my listening
FIRST_DATE: Final[date] = date.fromisoformat('2021-05-13')
# my user name
USER_NAME: Final[str] = 'lev'

## files ##

# find path of where the __main__ program was run
data_dir = pathlib.Path().resolve().as_posix()

# so if someone ran that program inside of levboard/main
if data_dir.endswith('/main'):
    data_dir = data_dir[:-5]  # remove "/main"
data_dir += '/data'

ALBUM_FILE: Final[str] = data_dir + '/albums.json'
SONG_FILE: Final[str] = data_dir + '/songs.json'
TEST_SONG_FILE: Final[str] = data_dir + '/test_songs.json'
