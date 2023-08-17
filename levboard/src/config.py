"""
levboard/main/src/config.py

Contains the Config class to configure user input.
"""

from datetime import date
from typing import Optional, Union

from pydantic import BaseModel, conint, validator
from .model.spotistats import get_first_stream_date


class Config(BaseModel):
    """
    The configurables for the charts.

    Attributes:
    *  `username` (`str`): The username of the person making the request.
    * `min_plays` (`int`): The minimum amount of plays a song needs to chart.

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
    chart_length: conint(ge=10, le=60) = 40

    # computed attributes
    start_date: date

    def __init__(self, info: dict):
        username = info.get('username')
        if not username:
            raise ValueError('username must be provided')

        start_date = info.get('start_date')
        if not start_date:
            info['start_date'] = get_first_stream_date(info['username'])

        super().__init__(**info)

    @validator('start_date', check_fields=False)
    def convert_date(cls, item: Union[date, str, None]) -> Optional[date]:
        if not item:
            return None
        if isinstance(item, date):
            return item
        return date.fromisoformat(item)

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
            'start_date': self.start_date.isoformat(),
        }
        return info
