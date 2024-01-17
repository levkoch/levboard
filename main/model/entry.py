"""
levboard/main/model/entry.py

Where the two entry types are held, for albums and songs.

Data Classes:
* SongEntry: An entry for a single `Song`.
* AlbumEntry: An entry for a single `Album`.
"""

from datetime import date
from typing import Union

from pydantic import BaseModel, NonNegativeInt, PositiveInt, conint, validator


class _BaseEntry(BaseModel):
    """Base class for entries. Do Not Construct, it's not complete."""

    start: date
    end: date
    place: PositiveInt

    @validator('start', 'end')
    def format_date(cls, v_date: Union[date, str]):
        """
        Format the two date parameters so that ISO strings can be passed in.
        """

        if isinstance(v_date, str):
            return date.fromisoformat(v_date)
        if isinstance(v_date, date):
            return v_date
        raise TypeError('Only iso date string or date accepted.')

    def to_dict(self) -> dict:
        """Dictionary representation of entry for storage."""
        return {
            'start': self.start.isoformat(),
            'end': self.end.isoformat(),
            'place': self.place,
        }


class Entry(_BaseEntry):
    """
    A frozen dataclass representing a chart entry.

    Attributes / Arguments:
    * start (`datetime.date`): The date that the week's entry started. Accepts
        and ISO date string, and will convert it to a `datetime.date` object.
    * end (`datetime.date`): The date that the week's entry ended. Alsoc accepts
        and ISO date string.
    * plays (`int`): The plays the song got that week. Will be greater than `1`.
    * points (`int`): The number of points that song got that week. Will be
        greater than `1`.
    * place (`int`): The chart position attained by that song. A positive integer.
    * variant (`str`): The ID of the song variant that charted.

    Methods:
    * to_dict (`dict` method): Collects the Entry into a dictionary.
    """

    plays: NonNegativeInt
    points: NonNegativeInt
    variant: str

    def to_dict(self) -> dict:
        """Dictionary representation of entry for storage."""

        info = super().to_dict()
        info['plays'] = self.plays
        info['points'] = self.points
        info['variant'] = self.variant
        return info


class AlbumEntry(_BaseEntry):
    """
    A frozen dataclass representing a chart entry.

    Attributes / Arguments:
    * start (`datetime.date`): The date that the week's entry started.
        (NOTE: `start` and `end` can be passed in as ISO date strings,
        they will be parsed as the correct type.)
    * end (`datetime.date`): The date that the week's entry ended.
    * plays (`int`): The plays the song got that week. Will be greater
        than `1`.
    * place (`int`): The chart position attained by that song. A
        positive integer.

    Methods:
    * to_dict (`dict` method): Collects the Entry into a dictionary.
    """

    units: conint(gt=1)

    def to_dict(self) -> dict:
        """Dictionary representation of entry for storage."""

        info = super().to_dict()
        info['units'] = self.units
        return info
