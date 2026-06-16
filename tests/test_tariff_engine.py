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
    list_tou_schedules,
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

    def test_saturday_summer_evening_standard(self):
        # Summer (Low Demand) weekend Standard window is 18:00-20:00.
        assert get_tou_period(4, 17, 6, False) == ("LO", 3)   # 17:00 now off-peak
        assert get_tou_period(4, 18, 6, False) == ("LO", 2)   # 18:00 standard
        assert get_tou_period(4, 19, 6, False) == ("LO", 2)   # 19:00 standard
        assert get_tou_period(4, 20, 6, False) == ("LO", 3)   # 20:00 off-peak

    def test_saturday_off_peak_afternoon(self):
        assert get_tou_period(4, 14, 6, False) == ("LO", 3)

    def test_saturday_off_peak_midnight(self):
        assert get_tou_period(4, 0, 6, False) == ("LO", 3)

    def test_saturday_in_hi_season(self):
        assert get_tou_period(7, 9, 6, False) == ("HI", 2)

    # Sunday (summer Standard window 18:00-20:00)
    def test_sunday_summer_17_off_peak(self):
        assert get_tou_period(4, 17, 7, False) == ("LO", 3)

    def test_sunday_standard_18(self):
        assert get_tou_period(4, 18, 7, False) == ("LO", 2)

    def test_sunday_standard_boundary_end(self):
        assert get_tou_period(4, 19, 7, False) == ("LO", 2)

    def test_sunday_summer_20_off_peak(self):
        assert get_tou_period(4, 20, 7, False) == ("LO", 3)

    # Winter (High Demand) weekend Standard window stays 17:00-19:00.
    def test_weekend_winter_standard_17_19(self):
        assert get_tou_period(7, 17, 6, False) == ("HI", 2)   # Sat 17:00 standard
        assert get_tou_period(7, 19, 6, False) == ("HI", 3)   # Sat 19:00 off-peak
        assert get_tou_period(7, 17, 7, False) == ("HI", 2)   # Sun 17:00 standard
        assert get_tou_period(7, 19, 7, False) == ("HI", 3)   # Sun 19:00 off-peak

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
# Section 1b - Named TOU schedules (registry)
# ============================================================================

class TestTOUSchedules:
    """The schedule registry, the default, and the Stellenbosch 2025/26 clock."""

    def test_eskom_is_default(self):
        # Omitting schedule must equal explicitly asking for eskom.
        for m, h, wd in [(7, 7, 1), (3, 18, 1), (4, 9, 6), (7, 18, 7)]:
            assert get_tou_period(m, h, wd, False) == get_tou_period(m, h, wd, False, "eskom")

    def test_registry_lists_known_schedules(self):
        names = list_tou_schedules()
        assert "eskom" in names
        assert "stellenbosch-2025" in names

    def test_unknown_schedule_raises(self):
        with pytest.raises(KeyError):
            get_tou_period(7, 7, 1, False, "does-not-exist")

    # Stellenbosch differs from Eskom on weekday peak bands and Sundays.
    def test_stellenbosch_differs_from_eskom(self):
        # Winter weekday 08:00: Eskom peak ends at 08:00 (Standard), Stellenbosch
        # peak runs to 09:00 (Peak).
        assert get_tou_period(7, 8, 1, False, "eskom") == ("HI", 2)
        assert get_tou_period(7, 8, 1, False, "stellenbosch-2025") == ("HI", 1)
        # Sunday 18:00: Eskom is Standard, Stellenbosch is Off-Peak all Sunday.
        assert get_tou_period(4, 18, 7, False, "eskom") == ("LO", 2)
        assert get_tou_period(4, 18, 7, False, "stellenbosch-2025") == ("LO", 3)

    def test_stellenbosch_winter_weekday(self):
        S = "stellenbosch-2025"
        assert get_tou_period(7, 6, 1, False, S) == ("HI", 1)   # peak start
        assert get_tou_period(7, 9, 1, False, S) == ("HI", 2)   # peak ends 09:00
        assert get_tou_period(7, 17, 1, False, S) == ("HI", 1)  # evening peak
        assert get_tou_period(7, 19, 1, False, S) == ("HI", 2)  # peak ends 19:00
        assert get_tou_period(7, 0, 1, False, S) == ("HI", 3)   # off-peak

    def test_stellenbosch_summer_weekday(self):
        S = "stellenbosch-2025"
        assert get_tou_period(3, 7, 1, False, S) == ("LO", 1)   # peak start
        assert get_tou_period(3, 6, 1, False, S) == ("LO", 2)   # 06:00 standard
        assert get_tou_period(3, 10, 1, False, S) == ("LO", 2)  # peak ends 10:00
        assert get_tou_period(3, 18, 1, False, S) == ("LO", 1)  # evening peak
        assert get_tou_period(3, 20, 1, False, S) == ("LO", 2)  # peak ends 20:00

    def test_stellenbosch_saturday_and_sunday(self):
        S = "stellenbosch-2025"
        assert get_tou_period(3, 7, 6, False, S) == ("LO", 2)   # Sat standard
        assert get_tou_period(3, 12, 6, False, S) == ("LO", 3)  # Sat off-peak gap
        assert get_tou_period(3, 18, 6, False, S) == ("LO", 2)  # Sat evening standard
        assert get_tou_period(3, 12, 7, False, S) == ("LO", 3)  # Sunday all off-peak
        assert get_tou_period(7, 18, 7, False, S) == ("HI", 3)  # Sunday off-peak

    def test_stellenbosch_no_weekday_peak_outside_bands(self):
        # No peak at 12:00 on a Stellenbosch weekday in either season.
        assert get_tou_period(7, 12, 1, False, "stellenbosch-2025")[1] != 1
        assert get_tou_period(3, 12, 1, False, "stellenbosch-2025")[1] != 1

    def test_tariff_carries_schedule(self):
        assert get_tariff_rates("Stellenbosch TOU LV").tou_schedule == "stellenbosch-2025"
        assert get_tariff_rates("Eskom Miniflex").tou_schedule == "eskom"


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
        assert math.isclose(t.capacity_charge_kva, 59.87, rel_tol=1e-4)

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
        expected = 5453.10 + 59.87 * 3000 * 12
        assert math.isclose(annual, expected, rel_tol=1e-5)

    def test_miniflex_nmd_3000_exact(self):
        t = get_tariff_rates("Eskom Miniflex")
        annual = t.service_charge_pa + t.capacity_charge_kva * 3000 * 12 + t.demand_charge_kva * 3000 * 12
        assert math.isclose(annual, 2_160_773.10, rel_tol=1e-5)

    def test_zero_nmd(self):
        t = get_tariff_rates("Eskom Miniflex")
        annual = t.service_charge_pa + t.capacity_charge_kva * 0 * 12 + t.demand_charge_kva * 0 * 12
        assert math.isclose(annual, t.service_charge_pa, rel_tol=1e-5)


# ============================================================================
# Section 5 - Capacity charge split (generation + network)
# ============================================================================

class TestCapacitySplit:
    """The capacity charge is exposed split into generation + network, and the
    two must always sum back to the combined capacity_charge_kva."""

    def test_miniflex_2026_split(self):
        t = get_tariff_rates("Eskom Miniflex")  # current date -> 2026/27, >900km <500V
        assert math.isclose(t.generation_capacity_charge_kva, 5.29, rel_tol=1e-4)
        assert math.isclose(t.network_capacity_charge_kva, 54.58, rel_tol=1e-4)

    def test_ruraflex_2026_split(self):
        t = get_tariff_rates("Eskom Ruraflex")
        assert math.isclose(t.generation_capacity_charge_kva, 5.07, rel_tol=1e-4)
        assert math.isclose(t.network_capacity_charge_kva, 56.95, rel_tol=1e-4)

    @pytest.mark.parametrize("name", ["Eskom Miniflex", "Eskom Ruraflex"])
    def test_split_sums_to_combined(self, name):
        t = get_tariff_rates(name)
        assert math.isclose(
            t.generation_capacity_charge_kva + t.network_capacity_charge_kva,
            t.capacity_charge_kva,
            rel_tol=1e-6,
        )

    def test_unsplit_tariff_falls_back_to_network(self):
        # A tariff without a generation/network split: generation is 0 and the
        # whole capacity charge is reported as network.
        t = get_tariff_rates("Eskom Megaflex")
        assert t.generation_capacity_charge_kva == 0.0
        assert math.isclose(t.network_capacity_charge_kva, t.capacity_charge_kva, rel_tol=1e-9)
