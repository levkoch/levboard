from typing import Union
from datetime import date
from pydantic import BaseModel, PositiveInt, validator, conint


class AlbumEntry(BaseModel):
    """
    A frozen dataclass representing a chart entry.

    Attributes / Arguments:
    * start (`datetime.date`): The date that the week's entry started.
        (NOTE: `start` and `end` can be passed in as ISO date strings, they
        will be parsed as the correct type.)
    * end (`datetime.date`): The date that the week's entry ended.
    * plays (`int`): The plays the song got that week. Will be greater than `1`.
    * place (`int`): The chart position attained by that song. A positive integer.

    Methods:
    * to_dict (`dict` method): Collects the Entry into a dictionary.
    """

    start: Union[date, str]  # will always be a date
    end: Union[date, str]  # also will always be a date
    units: conint(gt=1)
    place: PositiveInt

    @validator('start', 'end')
    def validate_date(cls, v_date: Union[date, str]):
        if isinstance(v_date, str):
            return date.fromisoformat(v_date)
        if isinstance(v_date, date):
            return v_date
        raise ValueError('Only iso date string or date accepted.')

    def to_dict(self) -> dict:
        """Dictionary representation of entry for storage."""
        return {
            'start': self.start.isoformat(),
            'end': self.end.isoformat(),
            'units': self.units,
            'place': self.place,
        }
