"""
tariff_engine/history.py
========================
Historical tariff lookup for the Solar Dashboard.

Public API
----------
    get_tariff_rates_for_date(name, date, ...) -> TariffRates

Escalation schedule (South Africa)
-----------------------------------
    Eskom        : new tariffs effective 1 April each year
    Municipalities: new tariffs effective 1 July each year

Schema_version 1 (current): tariff_data.json contains a single version. This
function returns current rates regardless of date -- correct for dates after
the current effective date, an approximation for earlier dates.

Schema_version 2 (when past-year data is added): tariff_data.json wraps each
provider's tariffs in a "versions" list with "effective" dates. This function
then automatically selects the version active on the requested date. See
rates._get_tariff_data() for the version-selection logic.

To add a new year's rates, add a new version block to tariff_data.json:

    "eskom": {
      "escalation_month": 4,
      "escalation_day": 1,
      "versions": [
        { "effective": "2026-04-01", "tariffs": { ...2026 rates... } },
        { "effective": "2027-04-01", "tariffs": { ...2027 rates... } }
      ]
    }
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional

from tariff_engine.rates import (
    TariffRates,
    _load_tariff_json_for_date,
    _resolve_tariff_rates,
)


def get_tariff_rates_for_date(
    tariff_name: str,
    date: _dt.date,
    zone: Optional[str] = None,
    voltage: Optional[str] = None,
    sseg_option: Optional[str] = None,
) -> TariffRates:
    """
    Return TOU rates applicable on a specific past or future date.

    Parameters
    ----------
    tariff_name : str
        Display name, e.g. "Eskom Megaflex", "CoCT LV TOU".
    date : datetime.date
        The date for which rates should apply.
        For Eskom: rate year runs 1 Apr to 31 Mar.
        For municipalities: rate year runs 1 Jul to 30 Jun.
    zone : str, optional
        Eskom transmission zone. Defaults to JSON default_zone.
    voltage : str, optional
        Eskom supply voltage. Defaults to JSON default_voltage.
    sseg_option : str, optional
        CoCT SSEG export option key.

    Returns
    -------
    TariffRates
        Rates (R/kWh, ex-VAT) and fixed charges applicable on the given date.

    Notes
    -----
    With schema_version 1 (single version), returns current rates regardless
    of date. Migrate tariff_data.json to schema_version 2 to support true
    historical lookups for dates before the current effective period.
    """
    data = _load_tariff_json_for_date(tariff_name, date)
    return _resolve_tariff_rates(tariff_name, data, zone, voltage, sseg_option)
