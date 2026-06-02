"""
tariff_engine/savings.py
========================
Hourly energy savings calculation for actual plant data (Solar Dashboard).

Public API
----------
    calculate_hourly_savings(
        grid_import_actual_kwh,
        solar_gen_kwh,
        tariff_rates,
        year,
    ) -> dict

Usage
-----
    from tariff_engine.rates import get_tariff_rates
    from tariff_engine.savings import calculate_hourly_savings

    rates = get_tariff_rates("Eskom Megaflex")
    result = calculate_hourly_savings(grid_kwh, solar_kwh, rates, year=2026)
    print(f"Annual saving: R{result['annual_saving_zar']:,.2f}")

For historical periods, use get_tariff_rates_for_date() instead of
get_tariff_rates() to get the rates that applied at that time.
"""
from __future__ import annotations

import datetime as _dt
from typing import Sequence

from tariff_engine.tou import get_tou_period
from tariff_engine.rates import TariffRates


def calculate_hourly_savings(
    grid_import_actual_kwh: Sequence[float],
    solar_gen_kwh: Sequence[float],
    tariff_rates: TariffRates,
    year: int,
) -> dict:
    """
    Calculate per-hour energy savings from actual plant data.

    Method: counterfactual subtraction.
    What the meter would have read without solar = grid_import_actual + solar_gen.
    Saving per hour = (counterfactual cost) - (actual cost with solar).

    Parameters
    ----------
    grid_import_actual_kwh : sequence of float
        Actual hourly grid import after solar offset (kWh).
        Length must equal len(solar_gen_kwh). Can be a full year (8760) or
        any contiguous slice starting from 1 Jan 00:00 of ``year``.
    solar_gen_kwh : sequence of float
        Actual hourly solar generation (kWh), same length.
        Use inverter AC output or metered generation.
    tariff_rates : TariffRates
        Rates applicable to the period. Use get_tariff_rates() for current
        rates or get_tariff_rates_for_date() for historical periods.
    year : int
        Calendar year of the data. Used for TOU schedule (peak/standard/off-peak)
        and South African public holiday detection.

    Returns
    -------
    dict with keys:
        hourly_savings_zar      : list[float]   per-hour saving (ZAR ex-VAT)
        hourly_cost_without_zar : list[float]   counterfactual cost (no solar)
        hourly_cost_with_zar    : list[float]   actual cost with solar
        annual_saving_zar       : float         total saving across all hours
        annual_cost_without_zar : float         total counterfactual cost
        annual_cost_with_zar    : float         total actual cost
        hours                   : int           number of hours processed

    Notes
    -----
    All values are energy-only (kWh x tariff rate). Demand/capacity savings
    (kVA charges) are NOT included here -- they require interval demand readings
    and are handled separately using tariff_rates.demand_charge_kva and
    tariff_rates.capacity_charge_kva.

    Negative savings (e.g. export not credited) are possible; they indicate
    hours where solar export would have earned money but wasn't credited.
    """
    if len(grid_import_actual_kwh) != len(solar_gen_kwh):
        raise ValueError(
            f"grid_import_actual_kwh ({len(grid_import_actual_kwh)}) and "
            f"solar_gen_kwh ({len(solar_gen_kwh)}) must be the same length"
        )

    n = len(grid_import_actual_kwh)
    hourly_savings: list[float] = []
    hourly_cost_without: list[float] = []
    hourly_cost_with: list[float] = []

    start = _dt.datetime(year, 1, 1, 0, 0)

    for i in range(n):
        dt = start + _dt.timedelta(hours=i)
        season, tou_period = get_tou_period(
            dt.month, dt.hour, dt.isoweekday(), is_holiday=False,
            schedule=tariff_rates.tou_schedule,
        )
        rate = tariff_rates.rate(season, tou_period)

        grid_actual = max(0.0, float(grid_import_actual_kwh[i]))
        solar       = max(0.0, float(solar_gen_kwh[i]))
        counterfactual = grid_actual + solar

        cost_without = counterfactual * rate
        cost_with    = grid_actual * rate

        hourly_savings.append(round(cost_without - cost_with, 6))
        hourly_cost_without.append(round(cost_without, 6))
        hourly_cost_with.append(round(cost_with, 6))

    return {
        "hourly_savings_zar":      hourly_savings,
        "hourly_cost_without_zar": hourly_cost_without,
        "hourly_cost_with_zar":    hourly_cost_with,
        "annual_saving_zar":       round(sum(hourly_savings), 2),
        "annual_cost_without_zar": round(sum(hourly_cost_without), 2),
        "annual_cost_with_zar":    round(sum(hourly_cost_with), 2),
        "hours":                   n,
    }
