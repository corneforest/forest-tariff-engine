"""
tariff_engine/tou.py
====================
South African TOU (Time-of-Use) schedule classification.

Public API
----------
    get_tou_period(month, hour, weekday_iso, is_holiday, schedule="eskom")
                                                 -> (season, tou_period)
    build_hourly_tou(year, schedule="eskom")     -> dict[str, np.ndarray]
    list_tou_schedules()                         -> list[str]
    _is_holiday(year, month, day)                -> bool

TOU period codes: 1 = Peak, 2 = Standard, 3 = Off-Peak.
Seasons: "HI" = High Demand, "LO" = Low Demand.

TOU schedules
-------------
A schedule defines (a) which months are High Demand, and (b) which clock hours
are Peak/Standard/Off-Peak for weekday/Saturday/Sunday in each season. Different
utilities use different schedules: Eskom is the default; municipalities such as
Stellenbosch publish their own. Schedules are data-driven entries in
TOU_SCHEDULES, so adding a utility's schedule is a data edit, not new code.

Each schedule is shaped:

    {
      "hd_months": [6, 7, 8],
      "weekday":  {"HI": {"peak": [[h0, h1], ...], "standard": [[h0, h1], ...]},
                   "LO": {...}},
      "saturday": {"HI": {...}, "LO": {...}},
      "sunday":   {"HI": {...}, "LO": {...}},
    }

Hour ranges are half-open [start, end) in 0-23 clock hours. An hour is Peak (1)
if it falls in any "peak" range, else Standard (2) if in any "standard" range,
else Off-Peak (3). A tariff selects its schedule via the "tou_schedule" key in
tariff_data.json (default "eskom"); TariffRates carries it through to savings.
"""
from __future__ import annotations

import functools

import numpy as np

DEFAULT_SCHEDULE = "eskom"

# Registry of named TOU schedules. Add a utility's schedule here as data.
TOU_SCHEDULES: dict[str, dict] = {
    # Eskom national TOU clock (Megaflex / Miniflex / Ruraflex). High Demand =
    # Jun/Jul/Aug. Weekend Standard window shifts by an hour between seasons:
    # Winter (High Demand) 17:00-19:00, Summer (Low Demand) 18:00-20:00.
    "eskom": {
        "hd_months": [6, 7, 8],
        "weekday": {
            "HI": {"peak": [[6, 8], [17, 20]], "standard": [[8, 17], [20, 22]]},
            "LO": {"peak": [[7, 9], [18, 21]], "standard": [[6, 7], [9, 18], [21, 22]]},
        },
        "saturday": {
            "HI": {"peak": [], "standard": [[7, 12], [17, 19]]},
            "LO": {"peak": [], "standard": [[7, 12], [18, 20]]},
        },
        "sunday": {
            "HI": {"peak": [], "standard": [[17, 19]]},
            "LO": {"peak": [], "standard": [[18, 20]]},
        },
    },
    # Stellenbosch Municipality TOU clock for the 2025/26 rate year. High Demand
    # (Winter) = Jun/Jul/Aug; Low Demand (Summer) = Sep-May. Sundays are off-peak
    # all day; Saturday bands are season-independent. Schedules are year-scoped
    # because a municipality may revise its clock: never edit an existing entry,
    # add a new one (e.g. "stellenbosch-2026") and point the new rate-year version
    # block at it, so historical date lookups stay accurate.
    "stellenbosch-2025": {
        "hd_months": [6, 7, 8],
        "weekday": {
            "HI": {"peak": [[6, 9], [17, 19]], "standard": [[9, 17], [19, 22]]},
            "LO": {"peak": [[7, 10], [18, 20]], "standard": [[6, 7], [10, 18], [20, 22]]},
        },
        "saturday": {
            "HI": {"peak": [], "standard": [[7, 12], [18, 20]]},
            "LO": {"peak": [], "standard": [[7, 12], [18, 20]]},
        },
        "sunday": {
            "HI": {"peak": [], "standard": []},
            "LO": {"peak": [], "standard": []},
        },
    },
}


def list_tou_schedules() -> list[str]:
    """Return the names of all registered TOU schedules."""
    return sorted(TOU_SCHEDULES)


def _in_ranges(hour: int, ranges: list) -> bool:
    """True if hour falls in any half-open [start, end) range."""
    return any(start <= hour < end for start, end in ranges)


def _day_key(weekday_iso: int) -> str:
    """Map ISO weekday (1=Mon..7=Sun) to a schedule day-type key."""
    if weekday_iso == 6:
        return "saturday"
    if weekday_iso == 7:
        return "sunday"
    return "weekday"

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


# High-Demand months for the default (Eskom) schedule. Kept for backward
# compatibility; the authoritative source is TOU_SCHEDULES[schedule]["hd_months"].
_HD_MONTHS = set(TOU_SCHEDULES[DEFAULT_SCHEDULE]["hd_months"])


def get_tou_period(
    month: int,
    hour: int,
    weekday_iso: int,
    is_holiday: bool,
    schedule: str = DEFAULT_SCHEDULE,
) -> tuple[str, int]:
    """
    Return (season, tou_period) for an hour under a given TOU schedule.

    Parameters
    ----------
    month       : 1-12
    hour        : 0-23 (start of the hour)
    weekday_iso : 1=Mon ... 5=Fri, 6=Sat, 7=Sun  (matches Excel WEEKDAY(,11))
    is_holiday  : True if SA public holiday
    schedule    : name of a registered TOU schedule (default "eskom")

    Returns
    -------
    season      : "HI" (High Demand) or "LO" (Low Demand)
    tou_period  : 1 (Peak), 2 (Standard), 3 (Off-Peak)

    Public holidays are NOT treated specially (matches Excel WEEKDAY() logic,
    which has no holiday override).
    """
    try:
        sched = TOU_SCHEDULES[schedule]
    except KeyError:
        raise KeyError(
            f"Unknown TOU schedule {schedule!r}. Available: {list_tou_schedules()}"
        )

    season = "HI" if month in sched["hd_months"] else "LO"
    bands = sched[_day_key(weekday_iso)][season]

    if _in_ranges(hour, bands["peak"]):
        return season, 1
    if _in_ranges(hour, bands["standard"]):
        return season, 2
    return season, 3


@functools.lru_cache(maxsize=32)
def build_hourly_tou(year: int = 2021, schedule: str = DEFAULT_SCHEDULE) -> dict[str, np.ndarray]:
    """
    Build arrays of TOU data for all 8760 hours of ``year`` under ``schedule``.

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
        season, tou = get_tou_period(m, h, wd, hol, schedule)
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
