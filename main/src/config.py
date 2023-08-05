"""
levboard/main/src/config.py

Contains the Config class to configure user input.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel
from .model.spotistats import get_first_stream_date


class Config(BaseModel):
    """
    The configurables for the charts.

    Attributes:
    *  `username` (`str`): The username of the person making the request.
    * `min_plays`
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

    def to_dict(self) -> dict:
        info = {
            'username': self.username,
            'min_plays': self.min_plays,
            'use_points': self.use_points,
            'current_weight': self.current_weight,
            'last_weight': self.last_weight,
            'second_last_weight': self.second_last_weight,
            'adjust_plays': self.adjust_plays,
            'max_adjusted': self.max_adjusted,
            'chart_length': self.chart_length,
        }
        if self._start_date:
            info['_start_date'] = self._start_date
        return info
