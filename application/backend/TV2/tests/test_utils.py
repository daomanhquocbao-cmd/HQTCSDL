from datetime import datetime, timedelta

import pytest

from booking.utils import calc_duration_hours, calc_total_price, is_overlapping

T0 = datetime(2026, 1, 1, 8, 0)


def test_duration_hours():
    assert calc_duration_hours(T0, T0 + timedelta(hours=2, minutes=30)) == 2.5


def test_duration_invalid_range():
    with pytest.raises(ValueError):
        calc_duration_hours(T0, T0)


def test_total_price():
    assert calc_total_price(T0, T0 + timedelta(hours=3), 150000) == 450000


def test_total_price_negative_rate():
    with pytest.raises(ValueError):
        calc_total_price(T0, T0 + timedelta(hours=1), -1)


def test_overlap_true():
    assert is_overlapping(T0, T0 + timedelta(hours=2), T0 + timedelta(hours=1), T0 + timedelta(hours=3))


def test_back_to_back_is_not_overlap():
    end = T0 + timedelta(hours=2)
    assert is_overlapping(T0, end, end, end + timedelta(hours=1)) is False
