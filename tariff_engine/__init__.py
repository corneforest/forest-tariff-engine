"""
tariff_engine
=============
Shared South African electricity tariff engine for Forest Energy tools.

Used by:
  - Solar Model  : get_tariff_rates(), TariffRates, get_tou_period(), build_hourly_tou()
  - Solar Dashboard: all of the above + get_tariff_rates_for_date(), calculate_hourly_savings()

Copy this entire tariff_engine/ folder (including tariff_data.json) to any
Python project that needs tariff calculations. No external dependencies beyond
numpy. Update tariff_data.json annually when new rates are published.
"""
from tariff_engine.tou import (
    get_tou_period,
    build_hourly_tou,
    _is_holiday,
    _HD_MONTHS,
    _SA_FIXED_HOLIDAYS,
    _SA_EASTER_HOLIDAYS,
)
from tariff_engine.rates import (
    TariffRates,
    get_tariff_rates,
    list_tariffs,
    _load_tariff_json,
    _get_raw_tariff_data,
    _resolve_tariff_rates,
)
from tariff_engine.history import get_tariff_rates_for_date
from tariff_engine.savings import calculate_hourly_savings
from tariff_engine.admin_fees import get_eskom_admin_fee, get_eskom_admin_fee_pa
from tariff_engine.eligibility import supports_banking, supports_gen_offset

__all__ = [
    # TOU schedule
    "get_tou_period",
    "build_hourly_tou",
    # Rate lookup
    "TariffRates",
    "get_tariff_rates",
    "list_tariffs",
    # Dashboard extras
    "get_tariff_rates_for_date",
    "calculate_hourly_savings",
    # Eskom Gen-Offset / Banking
    "get_eskom_admin_fee",
    "get_eskom_admin_fee_pa",
    "supports_banking",
    "supports_gen_offset",
]
