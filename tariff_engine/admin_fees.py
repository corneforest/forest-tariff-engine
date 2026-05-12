"""
tariff_engine/admin_fees.py
===========================
Eskom Gen-Offset / Banking administration fee lookup.

Per the Schedule of Standard Prices effective 1 April 2026, paragraph 46 pt 6:
the Gen-Offset (and by extension Banking) tariff includes a R/POD/day
administration charge based on the monthly utilised capacity (NMD) of the
Gen-Offset service agreement linked to an account. This fee is IN ADDITION
to the underlying tariff's service+admin charge (already represented by
TariffRates.service_charge_pa). Source values: Table 33 (urban) / 34 (rural).

Tier breakpoints (NMD in kVA) and rates are stored in tariff_data.json under
each Eskom version's `admin_fees` block. Values are ex-VAT, R/POD/day.
"""
from __future__ import annotations

import datetime as _dt
from typing import Literal, Optional

from tariff_engine.rates import _get_raw_tariff_data, _find_version


_URBAN_TARIFFS = {"Eskom Megaflex", "Eskom Miniflex"}
_RURAL_TARIFFS = {"Eskom Ruraflex"}

FeeType = Literal["gen_offset", "banking"]


def _is_rural(tariff_name: str) -> bool:
    if tariff_name in _RURAL_TARIFFS:
        return True
    if tariff_name in _URBAN_TARIFFS:
        return False
    raise ValueError(
        f"Eskom admin fee lookup is only defined for {_URBAN_TARIFFS | _RURAL_TARIFFS}, "
        f"got {tariff_name!r}."
    )


def _pick_tier(tiers: list[dict], nmd_kva: float) -> dict:
    """Return the tier dict whose max_kva covers nmd_kva. None = upper-open tier."""
    for t in tiers:
        cap = t.get("max_kva")
        if cap is None:
            return t
        if nmd_kva <= cap:
            return t
    return tiers[-1]


def get_eskom_admin_fee(
    tariff_name: str,
    nmd_kva: float,
    fee_type: FeeType = "gen_offset",
    date: Optional[_dt.date] = None,
) -> float:
    """
    Return the additional Eskom Gen-Offset / Banking admin fee in R/POD/day (ex-VAT).

    Looked up by NMD (monthly utilised capacity) and tariff family (urban vs rural)
    against the tier table in tariff_data.json for the version active on `date`.

    Parameters
    ----------
    tariff_name : str
        One of "Eskom Megaflex", "Eskom Miniflex" (urban) or "Eskom Ruraflex" (rural).
    nmd_kva : float
        Notified Maximum Demand / monthly utilised capacity in kVA.
    fee_type : "gen_offset" | "banking"
        Currently both return the same tier value (Eskom does not publish a
        separate Banking admin fee in the 2026-04-01 schedule). Kept as a
        parameter so we can split them when Eskom publishes distinct values.
    date : date, optional
        Effective date for tariff version selection. None = latest.

    Returns
    -------
    float
        R/POD/day admin fee, ex-VAT. 0.0 if the active version does not yet
        carry an admin_fees block (older versions pre-1.1.0).

    Raises
    ------
    ValueError if tariff_name is not an Eskom Megaflex/Miniflex/Ruraflex.
    """
    if fee_type not in ("gen_offset", "banking"):
        raise ValueError(f"fee_type must be 'gen_offset' or 'banking', got {fee_type!r}")
    if nmd_kva < 0:
        raise ValueError(f"nmd_kva must be non-negative, got {nmd_kva}")

    rural = _is_rural(tariff_name)

    raw = _get_raw_tariff_data()
    eskom = raw.get("eskom", {})
    versions = eskom.get("versions", [])
    if not versions:
        return 0.0

    version = _find_version(versions, date)
    admin_fees_block = version.get("admin_fees")
    if admin_fees_block is None:
        return 0.0

    tiers = admin_fees_block["rural" if rural else "urban"]
    tier = _pick_tier(tiers, nmd_kva)
    return float(tier["admin_r_per_pod_per_day"])


def get_eskom_admin_fee_pa(
    tariff_name: str,
    nmd_kva: float,
    fee_type: FeeType = "gen_offset",
    date: Optional[_dt.date] = None,
) -> float:
    """Convenience: annualised admin fee = R/day * 365."""
    return get_eskom_admin_fee(tariff_name, nmd_kva, fee_type, date) * 365.0
