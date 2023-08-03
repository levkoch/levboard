"""
levboard/main/config.py

Contains all of the static and user-configurable variables.

Constats:
* ALBUM_FILE: The file to read stored album json from.
* SONG_FILE: The file to read stored song json from.
* SETTINGS_FILE: The file to read configuration json from.
"""

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, validator
from model.spotistats import get_first_stream_date


class Config(BaseModel):
    """
    The configurables for the charts.
    """

    
    username: str

    # default values for config
    min_plays: int = 2
    use_points: bool = True
    current_weight: int = 10
    last_weight: int = 2
    second_last_weight: int = 2
    adjust_plays: bool = False
    max_adjusted: int = 25
    chart_length: int = 60

    # computed & cached attributes
    _start_date: Optional[date] = None

    @property
    def start_date(self) -> date:
        if self._start_date is None:
            self._start_date = get_first_stream_date(self.username)
        return self._start_date

    @classmethod
    def from_dict(self, mapping: dict[str, Any]):
        """
        Constructs a Config from a mapping provided.
        A username of some sort must be provided.
        """
        
        try:
            self.username = mapping['username']
        except IndexError:
            raise ValueError('Username must be provided.')

        self.start_date = mapping.get(
            'start_date', get_first_stream_date(self.username)
        )

        other_attrs = (
            'min_plays',
            'use_points',
            'current_weight',
            'last_weight',
            'second_last_weight',
            'adjust_plays',
            'max_adjusted',
            'chart_length',
        )

        for attr in other_attrs:
            if val := mapping.get(attr) is not None:
                setattr(self, attr, val)

    def to_dict():
        return {

        }

    
