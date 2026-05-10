"""
tariff_engine/tou.py
====================
South African TOU (Time-of-Use) schedule classification.

Public API
----------
    get_tou_period(month, hour, weekday_iso, is_holiday) -> (season, tou_period)
    build_hourly_tou(year) -> dict[str, np.ndarray]
    _is_holiday(year, month, day) -> bool

TOU period codes: 1 = Peak, 2 = Standard, 3 = Off-Peak.
Seasons: "HI" = High Demand (Jun/Jul/Aug), "LO" = Low Demand (all others).
"""
from __future__ import annotations

import functools

import numpy as np

# Public holidays for 2021-2030 (SA National Calendar)
# Format: (month, day) tuples; year-agnostic where dates are fixed.
# Variable dates (Easter, etc.) listed explicitly by year.
_SA_FIXED_HOLIDAYS = {
    (1, 1),   # New Year's Day
    (3, 21),  # Human Rights Day
    (4, 27),  # Freedom Day
    (5, 1),   # Workers' Day
    (6, 16),  # Youth Day
    (8, 9),   # National Women's Day
    (9, 24),  # Heritage Day
    (12, 16), # Day of Reconciliation
    (12, 25), # Christmas Day
    (12, 26), # Day of Goodwill
}

# Easter-derived holidays (Good Friday + Family Day) by year
_SA_EASTER_HOLIDAYS: dict[int, list[tuple[int, int]]] = {
    2021: [(4, 2), (4, 5)],
    2022: [(4, 15), (4, 18)],
    2023: [(4, 7), (4, 10)],
    2024: [(3, 29), (4, 1)],
    2025: [(4, 18), (4, 21)],
    2026: [(4, 3), (4, 6)],
    2027: [(3, 26), (3, 29)],
    2028: [(4, 14), (4, 17)],
    2029: [(3, 30), (4, 2)],
    2030: [(4, 19), (4, 22)],
}


def _is_holiday(year: int, month: int, day: int) -> bool:
    """Return True if the date is a South African public holiday."""
    if (month, day) in _SA_FIXED_HOLIDAYS:
        return True
    for m, d in _SA_EASTER_HOLIDAYS.get(year, []):
        if month == m and day == d:
            return True
    # If a fixed holiday falls on a Sunday, the Monday is the substitute
    import datetime as _dt
    dt = _dt.date(year, month, day)
    if dt.weekday() == 0:  # Monday: check if Sunday was a holiday
        prev = dt - _dt.timedelta(days=1)
        if (prev.month, prev.day) in _SA_FIXED_HOLIDAYS:
            return True
    return False


# High-Demand months (June = 6, July = 7, August = 8)
_HD_MONTHS = {6, 7, 8}


def get_tou_period(month: int, hour: int, weekday_iso: int, is_holiday: bool) -> tuple[str, int]:
    """
    Return (season, tou_period) for an hour.

    Parameters
    ----------
    month       : 1-12
    hour        : 0-23 (start of the hour)
    weekday_iso : 1=Mon ... 5=Fri, 6=Sat, 7=Sun  (matches Excel WEEKDAY(,11))
    is_holiday  : True if SA public holiday

    Returns
    -------
    season      : "HI" (High Demand) or "LO" (Low Demand)
    tou_period  : 1 (Peak), 2 (Standard), 3 (Off-Peak)
    """
    season = "HI" if month in _HD_MONTHS else "LO"
    is_weekend = weekday_iso in (6, 7)

    # Match Excel's WEEKDAY()-based logic: use the literal day of week.
    # Public holidays are NOT treated specially (Excel has no holiday override).
    if is_weekend:
        if weekday_iso == 7:  # Sunday
            if 17 <= hour < 19:
                return season, 2
            return season, 3
        else:  # Saturday
            if (7 <= hour < 12) or (17 <= hour < 19):
                return season, 2
            return season, 3

    # Weekday
    if season == "HI":
        if (6 <= hour < 8) or (17 <= hour < 20):
            return season, 1
        if (8 <= hour < 17) or (20 <= hour < 22):
            return season, 2
        return season, 3
    else:  # LO
        if (7 <= hour < 9) or (18 <= hour < 21):
            return season, 1
        if (hour == 6) or (9 <= hour < 18) or (21 <= hour < 22):
            return season, 2
        return season, 3


@functools.lru_cache(maxsize=8)
def build_hourly_tou(year: int = 2021) -> dict[str, np.ndarray]:
    """
    Build arrays of TOU data for all 8760 hours of ``year``.

    Returns a dict with keys:
        'months', 'hours', 'weekdays', 'seasons', 'tou_periods', 'is_holiday'
    Each value is a numpy integer (or string) array of length 8760.
    """
    import datetime as _dt
    months = np.zeros(8760, dtype=np.int8)
    hours = np.zeros(8760, dtype=np.int8)
    weekdays = np.zeros(8760, dtype=np.int8)
    seasons = np.empty(8760, dtype="U2")
    tou_periods = np.zeros(8760, dtype=np.int8)
    holidays = np.zeros(8760, dtype=bool)

    start = _dt.datetime(year, 1, 1, 0, 0)
    for i in range(8760):
        dt = start + _dt.timedelta(hours=i)
        m, h = dt.month, dt.hour
        # Python isoweekday(): Mon=1 ... Sun=7 (same as WEEKDAY(,11))
        wd = dt.isoweekday()
        hol = _is_holiday(year, m, dt.day)

        months[i] = m
        hours[i] = h
        weekdays[i] = wd
        holidays[i] = hol
        season, tou = get_tou_period(m, h, wd, hol)
        seasons[i] = season
        tou_periods[i] = tou

    return {
        "months": months,
        "hours": hours,
        "weekdays": weekdays,
        "seasons": seasons,
        "tou_periods": tou_periods,
        "is_holiday": holidays,
    }
