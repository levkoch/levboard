from datetime import date, timedelta
import pytest

from ..levboard.src.charts import create_song_chart
from ..levboard.src.storage import Process


"""
@pytest.mark.parametrize(
    ('start',),
    [(date(2021, 9, 23),), (date(2023, 4, 1),), (date(2022, 11, 4),)],
)
def test_load_week_returns_positions(start: date):
    positions = load_week(
        Config({'username': 'lev'}), start, start + timedelta(days=7)
    )
    expected_positions_order = sorted(
        positions, key=lambda p: p.plays, reverse=True
    )
    assert positions == expected_positions_order
    """


def test_point_charts():
    with Process(
        {'username': 'lev', 'start_date': '2023-04-04', 'use_points': True}
    ) as process:
        song_rows = create_song_chart(process)
