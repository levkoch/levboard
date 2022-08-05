"""
levboard/main/config.py

Contains all of the static and user-configurable variables.

Constats:
* ALBUM_FILE: The file to read stored album json from.
* SONG_FILE: The file to read stored song json from.
* SETTINGS_FILE: The file to read configuration json from.
"""

import pathlib
import json

from datetime import date
from typing import Any, Final

## files ##

# find path of where the __main__ program was run
data_dir = pathlib.Path().resolve().as_posix()

# so if someone ran that program inside of levboard/main
if data_dir.endswith('/main'):
    data_dir = data_dir[:-5]  # remove "/main"
data_dir += '/data'

ALBUM_FILE: Final[str] = f'{data_dir}/albums.json'
SONG_FILE: Final[str] = f'{data_dir}/songs.json'
SETTINGS_FILE: Final[str] = f'{data_dir}/settings.json'


def _get_setting(setting_name: str, default: Any) -> Any:
    """
    Internal method to get a setting from the setting config file.

    Arguments:
    * setting_name (`str`): The setting name of the desired setting getter.
    * default (`Any`): The value to return when the setting name isn't found.

    Returns:
    * setting (`Any`): The requested setting.
    """

    with open(SETTINGS_FILE, 'r', encoding='UTF-8') as f:
        settings: dict = json.load(f)

    return settings.pop(setting_name, default)


def get_username() -> str:
    """
    Retrieves the configured username in the config file.
    Defaults to `"lev"` if none is in the file somehow.
    """
    return str(_get_setting('username', 'lev'))


def get_min_plays() -> int:
    """
    Retrieves the configured minimum plays from the config plays.
    Defaults to `2` if none is in the file.
    """
    return int(_get_setting('min_plays', 2))


def get_start_date() -> date:
    """
    Retrieves the configured first week from the config file.
    Defaults to May 13th, 2021 (Lev first date).
    """
    return date.fromisoformat(_get_setting('start_date', '2021-05-13'))


def update_settings(**kwargs: dict[str, Any]) -> None:
    """
    Update the settings of the system.

    Settings:
    * `username (str)`: The username of the account to find data for.
    * `min_plays (int)`: The minimum plays a song needs to get to chart.

    All settings default to the ones that are already in config.
    """

    username = kwargs.pop('username', get_username())
    min_plays = kwargs.pop('min_plays', get_min_plays())
    start_date = kwargs.pop('start_date', get_start_date())

    settings = {
        'username': str(username),
        'min_plays': int(min_plays),
        'start_date': start_date.isoformat(),
    }

    with open(SETTINGS_FILE, 'w', encoding='UTF-8') as f:
        json.dump(settings, f, indent=4)
