from datetime import date
from pydantic import BaseModel

from model import spotistats


class Week(BaseModel):
    start_day: date
    end_day: date
    songs: list[dict]


def load_week(start_day: date, end_day: date) -> Week:
    songs = spotistats.songs_week(
        start_day, end_day, min_plays=0, adjusted=True
    )

    return Week(start_day, end_day, songs)
