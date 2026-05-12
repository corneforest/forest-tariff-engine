"""
tests/test_admin_fees.py
========================
Tests for Eskom Gen-Offset / Banking admin fee lookup and eligibility helpers.

Reference data: Schedule of Standard Prices effective 1 April 2026,
Tables 33 (urban) and 34 (rural). Values in R/POD/day, ex-VAT.
"""
from __future__ import annotations

import datetime as _dt

import pytest

from tariff_engine import (
    get_eskom_admin_fee,
    get_eskom_admin_fee_pa,
    supports_banking,
    supports_gen_offset,
)


# ============================================================================
# Section 1 - get_eskom_admin_fee tier lookup
# ============================================================================

class TestAdminFeeTiers:
    """Verify Table 33 / Table 34 tier values are looked up correctly."""

    def test_urban_tier_le_100(self):
        assert get_eskom_admin_fee("Eskom Megaflex", 50.0) == pytest.approx(0.79)
        assert get_eskom_admin_fee("Eskom Megaflex", 100.0) == pytest.approx(0.79)

    def test_urban_tier_100_500(self):
        assert get_eskom_admin_fee("Eskom Megaflex", 100.01) == pytest.approx(13.49)
        assert get_eskom_admin_fee("Eskom Megaflex", 500.0) == pytest.approx(13.49)

    def test_urban_tier_500_1mva(self):
        assert get_eskom_admin_fee("Eskom Miniflex", 750.0) == pytest.approx(21.07)
        assert get_eskom_admin_fee("Eskom Miniflex", 1000.0) == pytest.approx(21.07)

    def test_urban_tier_above_1mva(self):
        assert get_eskom_admin_fee("Eskom Megaflex", 5000.0) == pytest.approx(21.07)

    def test_rural_tier_le_100(self):
        # Rural ≤100 tier is the only urban-vs-rural divergence in admin column.
        assert get_eskom_admin_fee("Eskom Ruraflex", 50.0) == pytest.approx(1.47)
        assert get_eskom_admin_fee("Eskom Ruraflex", 100.0) == pytest.approx(1.47)

    def test_rural_tier_100_500(self):
        assert get_eskom_admin_fee("Eskom Ruraflex", 250.0) == pytest.approx(13.49)

    def test_rural_tier_above_500(self):
        assert get_eskom_admin_fee("Eskom Ruraflex", 1500.0) == pytest.approx(21.07)


class TestAdminFeeBehaviour:

    def test_banking_returns_same_as_gen_offset_for_now(self):
        a = get_eskom_admin_fee("Eskom Megaflex", 750.0, fee_type="gen_offset")
        b = get_eskom_admin_fee("Eskom Megaflex", 750.0, fee_type="banking")
        # Eskom does not publish a separate Banking admin fee in the 2026-04-01
        # schedule, so both should resolve to the same tier value.
        assert a == b == pytest.approx(21.07)

    def test_annual_helper_multiplies_by_365(self):
        daily = get_eskom_admin_fee("Eskom Megaflex", 750.0)
        annual = get_eskom_admin_fee_pa("Eskom Megaflex", 750.0)
        assert annual == pytest.approx(daily * 365)

    def test_unknown_tariff_raises(self):
        with pytest.raises(ValueError):
            get_eskom_admin_fee("CoCT LV TOU", 100.0)
        with pytest.raises(ValueError):
            get_eskom_admin_fee("Eskom Homeflex", 100.0)

    def test_invalid_fee_type_raises(self):
        with pytest.raises(ValueError):
            get_eskom_admin_fee("Eskom Megaflex", 100.0, fee_type="wheeling")

    def test_negative_nmd_raises(self):
        with pytest.raises(ValueError):
            get_eskom_admin_fee("Eskom Megaflex", -10.0)

    def test_zero_nmd_lands_in_first_tier(self):
        assert get_eskom_admin_fee("Eskom Megaflex", 0.0) == pytest.approx(0.79)

    def test_historical_version_without_admin_fees_returns_zero(self):
        # 2025-04-01 version has no admin_fees block; should fall back to 0.0.
        fee = get_eskom_admin_fee(
            "Eskom Miniflex", 750.0, date=_dt.date(2025, 6, 1)
        )
        assert fee == 0.0


# ============================================================================
# Section 2 - eligibility helpers
# ============================================================================

class TestSupportsBanking:

    @pytest.mark.parametrize("name", ["Eskom Megaflex", "Eskom Miniflex", "Eskom Ruraflex"])
    def test_eskom_three_tariffs_supported(self, name):
        assert supports_banking(name) is True

    @pytest.mark.parametrize("name", [
        "Eskom Homeflex",
        "CoCT LV TOU",
        "eThekwini Large TOU",
        "Unknown Tariff",
        "",
    ])
    def test_others_not_supported(self, name):
        assert supports_banking(name) is False


class TestSupportsGenOffset:

    def test_eskom_megaflex_supported(self):
        assert supports_gen_offset("Eskom Megaflex") is True

    def test_eskom_miniflex_supported(self):
        assert supports_gen_offset("Eskom Miniflex") is True

    def test_eskom_ruraflex_supported(self):
        assert supports_gen_offset("Eskom Ruraflex") is True

    def test_unknown_tariff_not_supported(self):
        assert supports_gen_offset("Made Up Tariff Name") is False
