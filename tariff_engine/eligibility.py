"""
tariff_engine/eligibility.py
============================
Tariff-family eligibility for export schemes (Gen-Offset, Banking).

Source: Schedule of Standard Prices effective 1 April 2026, paragraph 46
(Gen-offset tariff). Banking is a derivative of Gen-Offset that carries
surplus credits across months within the Eskom financial year (1 Apr - 31 Mar).
Banking is an Eskom-only scheme and does not apply to municipal tariffs.
"""
from __future__ import annotations

_ESKOM_BANKING_ELIGIBLE = {
    "Eskom Megaflex",
    "Eskom Miniflex",
    "Eskom Ruraflex",
}


def supports_banking(tariff_name: str) -> bool:
    """True only for Eskom Megaflex / Miniflex / Ruraflex."""
    return tariff_name in _ESKOM_BANKING_ELIGIBLE


def supports_gen_offset(tariff_name: str) -> bool:
    """
    True if the tariff supports per-TOU monthly Gen-Offset (net-metering with
    per-bracket cap). Eskom Megaflex/Miniflex/Ruraflex qualify directly.
    Municipal tariffs that expose SSEG export options qualify under their own
    municipal rules (the model uses the same per-TOU monthly cap logic).
    """
    if tariff_name in _ESKOM_BANKING_ELIGIBLE:
        return True

    from tariff_engine.rates import _load_tariff_json

    try:
        data = _load_tariff_json(tariff_name)
    except KeyError:
        return False

    if data.get("type") == "municipal" and data.get("sseg_options"):
        return True

    return False
