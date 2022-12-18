"""
levboard/main/config.py

Contains all of the static and user-configurable variables.

Constats:
* ALBUM_FILE: The file to read stored album json from.
* SONG_FILE: The file to read stored song json from.
* SETTINGS_FILE: The file to read configuration json from.
"""

import json
import pathlib
from datetime import date
from typing import Any, Final, Union

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


def get_lazy_name() -> bool:
    """
    Retreieves the configured lazy naming for songs. Defaults to True,
    so users won't be asked to name their tracks.
    """
    return bool(_get_setting('lazy_name', True))


def update_settings(**kwargs: dict[str, Any]) -> None:
    """
    Update the settings of the system.

    Settings:
    * `username (str)`: The username of the account to find data for.
    * `min_plays (int)`: The minimum plays a song needs to get to chart.
    * `start_date (date)`: The date to start finding data from.

    All settings default to the ones that are already in config.
    """

    username: Union[Any, str] = kwargs.pop('username', get_username())
    min_plays: Union[Any, int] = kwargs.pop('min_plays', get_min_plays())
    start_date: Union[Any, date] = kwargs.pop('start_date', get_start_date())
    lazy_name: Union[Any, bool] = kwargs.pop('lazy_name', get_lazy_name())

    settings = {
        'username': str(username),
        'min_plays': int(min_plays),
        'start_date': start_date.isoformat(),
        'lazy_name': bool(lazy_name),
    }

    with open(SETTINGS_FILE, 'w', encoding='UTF-8') as f:
        json.dump(settings, f, indent=4)
