"""
tests/test_tariff_engine.py
===========================
Standalone test suite for the forest-tariff-engine package.

Covers:
  - TOU period classification (Section 1)
  - 8760-hour TOU array construction (Section 2)
  - Tariff rate lookup via JSON (Section 3)
  - Fixed-charge formula sanity check (Section 4)

Run with: pytest -v
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from tariff_engine import (
    get_tou_period,
    build_hourly_tou,
    get_tariff_rates,
    list_tariffs,
)


# ============================================================================
# Section 1 - TOU period mapping
# ============================================================================

class TestTOUPeriod:
    """Spot-check get_tou_period() against the Eskom TOU schedule."""

    # High Demand (Jun-Aug) weekday
    def test_hd_weekday_peak_morning(self):
        assert get_tou_period(7, 7, 1, False) == ("HI", 1)

    def test_hd_weekday_peak_evening(self):
        assert get_tou_period(7, 18, 2, False) == ("HI", 1)

    def test_hd_weekday_peak_boundary_start(self):
        assert get_tou_period(7, 6, 3, False) == ("HI", 1)

    def test_hd_weekday_peak_boundary_end(self):
        assert get_tou_period(7, 8, 3, False) == ("HI", 2)

    def test_hd_weekday_standard_day(self):
        assert get_tou_period(7, 10, 3, False) == ("HI", 2)

    def test_hd_weekday_standard_evening(self):
        assert get_tou_period(7, 20, 4, False) == ("HI", 2)

    def test_hd_weekday_off_peak_midnight(self):
        assert get_tou_period(7, 0, 5, False) == ("HI", 3)

    def test_hd_weekday_off_peak_early(self):
        assert get_tou_period(7, 3, 5, False) == ("HI", 3)

    def test_hd_weekday_off_peak_late(self):
        assert get_tou_period(7, 22, 5, False) == ("HI", 3)

    # Low Demand weekday
    def test_ld_weekday_peak_morning(self):
        assert get_tou_period(3, 8, 1, False) == ("LO", 1)

    def test_ld_weekday_peak_boundary_start(self):
        assert get_tou_period(3, 7, 1, False) == ("LO", 1)

    def test_ld_weekday_peak_boundary_end(self):
        assert get_tou_period(3, 9, 1, False) == ("LO", 2)

    def test_ld_weekday_peak_evening(self):
        assert get_tou_period(3, 19, 2, False) == ("LO", 1)

    def test_ld_weekday_peak_evening_boundary(self):
        assert get_tou_period(3, 21, 2, False) == ("LO", 2)

    def test_ld_weekday_standard_midday(self):
        assert get_tou_period(3, 12, 3, False) == ("LO", 2)

    def test_ld_weekday_standard_hour6(self):
        assert get_tou_period(3, 6, 5, False) == ("LO", 2)

    def test_ld_weekday_off_peak(self):
        assert get_tou_period(3, 4, 5, False) == ("LO", 3)

    def test_ld_weekday_off_peak_night(self):
        assert get_tou_period(3, 23, 5, False) == ("LO", 3)

    # Saturday
    def test_saturday_standard_morning(self):
        assert get_tou_period(4, 9, 6, False) == ("LO", 2)

    def test_saturday_standard_evening(self):
        assert get_tou_period(4, 17, 6, False) == ("LO", 2)

    def test_saturday_off_peak_afternoon(self):
        assert get_tou_period(4, 14, 6, False) == ("LO", 3)

    def test_saturday_off_peak_midnight(self):
        assert get_tou_period(4, 0, 6, False) == ("LO", 3)

    def test_saturday_in_hi_season(self):
        assert get_tou_period(7, 9, 6, False) == ("HI", 2)

    # Sunday
    def test_sunday_standard(self):
        assert get_tou_period(4, 17, 7, False) == ("LO", 2)

    def test_sunday_standard_18(self):
        assert get_tou_period(4, 18, 7, False) == ("LO", 2)

    def test_sunday_standard_boundary_end(self):
        assert get_tou_period(4, 19, 7, False) == ("LO", 3)

    def test_sunday_off_peak_morning(self):
        assert get_tou_period(4, 10, 7, False) == ("LO", 3)

    # Holidays: Excel does NOT treat holidays specially.
    def test_holiday_weekday_treated_as_saturday(self):
        assert get_tou_period(4, 9, 5, True) == ("LO", 2)

    def test_holiday_standard_evening(self):
        assert get_tou_period(4, 17, 5, True) == ("LO", 2)

    def test_holiday_off_peak(self):
        assert get_tou_period(4, 14, 5, True) == ("LO", 2)

    # Seasons
    def test_hi_season_months(self):
        for m in (6, 7, 8):
            s, _ = get_tou_period(m, 12, 1, False)
            assert s == "HI", f"Month {m} should be HI"

    def test_lo_season_months(self):
        for m in (1, 2, 3, 4, 5, 9, 10, 11, 12):
            s, _ = get_tou_period(m, 12, 1, False)
            assert s == "LO", f"Month {m} should be LO"


# ============================================================================
# Section 2 - build_hourly_tou
# ============================================================================

class TestBuildHourlyTOU:
    """Verify 8760-array construction and TOU distribution."""

    @pytest.fixture(scope="class")
    def tou(self):
        return build_hourly_tou(2021)

    def test_length(self, tou):
        assert len(tou["months"]) == 8760
        assert len(tou["tou_periods"]) == 8760
        assert len(tou["seasons"]) == 8760

    def test_months_range(self, tou):
        assert tou["months"].min() == 1
        assert tou["months"].max() == 12

    def test_hours_range(self, tou):
        assert tou["hours"].min() == 0
        assert tou["hours"].max() == 23

    def test_weekdays_range(self, tou):
        assert tou["weekdays"].min() >= 1
        assert tou["weekdays"].max() <= 7

    def test_tou_periods_valid(self, tou):
        assert set(np.unique(tou["tou_periods"])) <= {1, 2, 3}

    def test_seasons_valid(self, tou):
        assert set(np.unique(tou["seasons"])) <= {"HI", "LO"}

    def test_hi_season_hours(self, tou):
        hi_count = np.sum(tou["seasons"] == "HI")
        assert hi_count == 2208, f"Expected 2208 HI hours, got {hi_count}"

    def test_lo_season_hours(self, tou):
        lo_count = np.sum(tou["seasons"] == "LO")
        assert lo_count == 6552, f"Expected 6552 LO hours, got {lo_count}"

    def test_no_peak_on_weekends(self, tou):
        is_weekend = (tou["weekdays"] == 6) | (tou["weekdays"] == 7)
        weekend_peak = np.sum((tou["tou_periods"] == 1) & is_weekend & ~tou["is_holiday"])
        assert weekend_peak == 0

    def test_public_holidays_2021(self, tou):
        holiday_count = int(np.sum(tou["is_holiday"]))
        assert holiday_count >= 240

    def test_january_1_hour_0_is_holiday(self, tou):
        assert tou["is_holiday"][0] == True

    def test_christmas_is_holiday(self, tou):
        import datetime as dt
        start = dt.datetime(2021, 1, 1)
        target = dt.datetime(2021, 12, 25, 0)
        i = int((target - start).total_seconds() // 3600)
        assert tou["is_holiday"][i] == True


# ============================================================================
# Section 3 - Tariff rates (2026/27 Eskom Miniflex >900km <500V)
# ============================================================================

class TestTariffRates:
    """Verify TOU rates match 2026/27 Eskom tariff values (effective 2026-04-01)."""

    def test_miniflex_hd_peak(self):
        t = get_tariff_rates("Eskom Miniflex")
        assert math.isclose(t.hd_peak, 8.2946, rel_tol=1e-4)

    def test_miniflex_hd_standard(self):
        t = get_tariff_rates("Eskom Miniflex")
        assert math.isclose(t.hd_standard, 2.5836, rel_tol=1e-4)

    def test_miniflex_hd_off_peak(self):
        t = get_tariff_rates("Eskom Miniflex")
        assert math.isclose(t.hd_off_peak, 1.6261, rel_tol=1e-4)

    def test_miniflex_ld_peak(self):
        t = get_tariff_rates("Eskom Miniflex")
        assert math.isclose(t.ld_peak, 3.8402, rel_tol=1e-3)

    def test_miniflex_ld_standard(self):
        t = get_tariff_rates("Eskom Miniflex")
        assert math.isclose(t.ld_standard, 2.4567, rel_tol=1e-4)

    def test_miniflex_ld_off_peak(self):
        t = get_tariff_rates("Eskom Miniflex")
        assert math.isclose(t.ld_off_peak, 1.6261, rel_tol=1e-4)

    def test_miniflex_service_charge(self):
        t = get_tariff_rates("Eskom Miniflex")
        assert math.isclose(t.service_charge_pa, 5453.10, rel_tol=1e-4)

    def test_miniflex_capacity_charge(self):
        t = get_tariff_rates("Eskom Miniflex")
        assert math.isclose(t.capacity_charge_kva, 54.58, rel_tol=1e-4)

    def test_miniflex_export_hd_peak(self):
        t = get_tariff_rates("Eskom Miniflex")
        assert t.export_hd_peak is not None
        assert math.isclose(t.export_hd_peak, 7.2984, rel_tol=1e-3)

    def test_rate_method_hi_peak(self):
        t = get_tariff_rates("Eskom Miniflex")
        assert math.isclose(t.rate("HI", 1), 8.2946, rel_tol=1e-4)

    def test_rate_method_lo_standard(self):
        t = get_tariff_rates("Eskom Miniflex")
        assert math.isclose(t.rate("LO", 2), 2.4567, rel_tol=1e-4)

    def test_unknown_tariff_raises(self):
        with pytest.raises(KeyError, match="Unknown tariff"):
            get_tariff_rates("Nonexistent Tariff XYZ")

    def test_list_tariffs_contains_miniflex(self):
        tariffs = list_tariffs()
        assert "Eskom Miniflex" in tariffs

    def test_list_tariffs_contains_expected_providers(self):
        tariffs = list_tariffs()
        expected = [
            "Eskom Megaflex", "Eskom Ruraflex",
            "CoCT LV TOU", "CoCT MV TOU",
            "eThekwini Industrial TOU", "NMB LV Medium Business TOU (Scale 32X/33Y/32Y)",
            "Tshwane LV TOU", "Stellenbosch TOU LV",
        ]
        for t in expected:
            assert t in tariffs, f"Missing tariff: {t}"


# ============================================================================
# Section 4 - Fixed-charge formula sanity check
# ============================================================================

class TestFixedChargeFormula:
    """
    The fixed-charge formula (service + capacity x kva x 12 + demand x kva x 12)
    lives in solar_calculation_engine.compute_fixed_charges, but the inputs come
    from this package. Verify the inputs produce the expected R/year totals.
    """

    def test_miniflex_nmd_3000(self):
        t = get_tariff_rates("Eskom Miniflex")
        annual = t.service_charge_pa + t.capacity_charge_kva * 3000 * 12 + t.demand_charge_kva * 3000 * 12
        expected = 5453.10 + 54.58 * 3000 * 12
        assert math.isclose(annual, expected, rel_tol=1e-5)

    def test_miniflex_nmd_3000_exact(self):
        t = get_tariff_rates("Eskom Miniflex")
        annual = t.service_charge_pa + t.capacity_charge_kva * 3000 * 12 + t.demand_charge_kva * 3000 * 12
        assert math.isclose(annual, 1_970_333.10, rel_tol=1e-5)

    def test_zero_nmd(self):
        t = get_tariff_rates("Eskom Miniflex")
        annual = t.service_charge_pa + t.capacity_charge_kva * 0 * 12 + t.demand_charge_kva * 0 * 12
        assert math.isclose(annual, t.service_charge_pa, rel_tol=1e-5)
