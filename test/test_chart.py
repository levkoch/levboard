from datetime import date, timedelta
import pytest

from ..main.src.charts import load_week


@pytest.mark.parametrize(
    ('start',),
    [(date(2021, 9, 23),), (date(2023, 4, 1),), (date(2022, 11, 4),)],
)
def test_load_week_returns_positions(start: date):
    positions = load_week('lev', start, start + timedelta(days=7))
    expected_positions_order = sorted(
        positions, key=lambda p: p.plays, reverse=True
    )
    assert positions == expected_positions_order
