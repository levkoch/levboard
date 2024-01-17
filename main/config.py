"""
levboard/main/config.py

Contains all of the static and user-configurable variables.

Constats:
* FIRST_DATE: The date to start making charts from.
* ALBUM_FILE: The file to read stored album json from.
* SONG_FILE: The file to read stored song json from.
"""

import pathlib
import platform
from datetime import date
from typing import Final

## constants ##

# the max plays a song can get in one day before getting adjusted
MAX_ADJUSTED: Final[int] = 25
# where my google sheet is located at
LEVBOARD_SHEET: Final[str] = '1_KNcoT92nfgQCRqLH7Iz4ZSxy9hxCd8ll0Hzn9hscqk'
# where the group charts sheet is located at
GROUPBOARD_SHEET: Final[str] = '16ZJCz0AU5WM-e2YytmFtzLRhJ1Pd5bJpuAVv2y8XmM0'
# the first date of my listening
FIRST_DATE: Final[date] = date.fromisoformat('2023-11-23')   #'2021-05-13')
# the date the group charts started
GROUP_DATE: Final[date] = date.fromisoformat('2022-12-30')
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

SERVICE_ACCOUNT_FILE: str = (
    # on laptop
    'C:/Users/levpo/Documents/GitHub/lev-bot/extras/google_token.json'
    if platform.system() == 'Windows'
    else '../data/google_token.json'  # on ipad
)
