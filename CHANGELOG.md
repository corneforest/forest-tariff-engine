# Changelog

All notable changes to the Forest Energy Tariff Engine are recorded here so
consuming programs (Solar Model, Solar Dashboard) know what changed when they
bump their pinned version.

The version is authored in `pyproject.toml` and released as git tag `v{version}`
(see [RELEASING.md](RELEASING.md)). This file follows
[Keep a Changelog](https://keepachangelog.com/) and
[Semantic Versioning](https://semver.org/): PATCH = data fix on existing
tariffs, MINOR = new tariffs/providers, MAJOR = schema or API break.

## [1.7.1] - 2026-06-15

### Fixed
- **Eskom Miniflex and Ruraflex 2025/26 active energy charge (data fix, raises
  all-in import rates).** The 2025/26 `energy_c_per_kwh` values were stored as
  the booklet "Active energy charge" MINUS all per-kWh levies, so the engine
  (which re-adds legacy + ancillary + network demand + electrification +
  affordability) only reproduced the active energy charge and never added the
  levies on top. Energy values are now set to the booklet active energy charge,
  so all-in = active energy + levies, matching the 2025/26 PDFs and the 2026/27
  blocks. Effect: +71.73 c/kWh (Ruraflex <500V) and +62.52/+32.82 c/kWh
  (Miniflex <500V peak-standard / off-peak) on the all-in import rate; smaller
  uplifts on higher-voltage bands. Example, >900km <500V HD Peak: Ruraflex
  711.73 -> 783.46 c/kWh, Miniflex 705.13 -> 767.65 c/kWh. 144 energy cells
  updated across all zones and voltages. Levies, capacity charges, service
  charges and 2026/27 rates are unchanged. Script:
  `scripts/fix_eskom_2025_energy_levies.py`.

## [1.7.0] - 2026-06-09

### Added
- **Ephraim Mogale Church/Schools/Charitable Single 80A** (2025/26, ex VAT):
  flat energy 253.47 c/kWh, basic R377.68/month, export = Energy Feedback
  172.00 c/kWh (matching the other Ephraim Mogale tariffs). Total count 103 -> 104.

## [1.6.0] - 2026-06-05

### Added
- **Eskom Businessrate 2 and 3** (three-phase, non-local authority) for both
  rate years 2025/26 (2025-04-01) and 2026/27 (2026-04-01). Flat tariff;
  all-in energy = energy + ancillary + network demand + electrification (244.82
  c/kWh in 2025/26, 264.53 in 2026/27). R/POD/day fixed charges annualised x365
  into service_charge_pa. No export. Total tariff count 101 -> 103.
- **City of Ekurhuleni 2026/27** version block (effective 2026-07-01), all 12
  tariffs. **Provisional** (draft schedule v.2026.03.11, pending Council
  approval). +9.01% on all charges except Tariff J and every export credit,
  which rise +8.76% (Eskom Municflex-linked).
- **City of Tshwane 2026/27** version block (effective 2026-07-01), all 6
  tariffs. **Provisional**: uniform +8.8% on every rate and charge.

### Fixed
- **Eskom TOU schedule weekend correction (behavioural — affects all
  Eskom-clock tariffs).** The summer (Low Demand) Saturday/Sunday Standard
  window was corrected from 17:00-19:00 to **18:00-20:00**; winter (High Demand)
  remains 17:00-19:00. This changes Standard vs Off-Peak classification for two
  summer-weekend hours and therefore TOU savings results for every tariff using
  the `eskom` schedule (Eskom + most municipalities). CoE TOU tariffs use the
  corrected `eskom` clock (no separate CoE schedule needed).

## [1.5.0] - 2026-06-02

### Added
- **Per-tariff TOU schedules.** TOU clocks (Peak/Standard/Off-Peak hours and
  High/Low season months) are now data-driven named entries in
  `tou.TOU_SCHEDULES`. A tariff selects one via the `tou_schedule` key in
  `tariff_data.json` (absent = `"eskom"`). New public helper
  `list_tou_schedules()`; `get_tou_period()` and `build_hourly_tou()` gain an
  optional `schedule` argument defaulting to `"eskom"`; `TariffRates` gains a
  `tou_schedule` field.
- **`stellenbosch-2025` TOU schedule** (Stellenbosch Municipality 2025/26 clock:
  Winter Jun-Aug, Summer Sep-May, Sunday off-peak all day). Applied to
  `Stellenbosch TOU LV`, `Stellenbosch TOU MV`, and the new IND1 tariff.
  Schedules are year-scoped so a future revision is added as a new entry without
  breaking historical lookups.
- **Stellenbosch Large Power LV >80A (IND1)** tariff (2025/26, ex VAT): flat
  import 180.34 c/kWh, TOU export (HD 616.20/186.69/101.38, LD
  201.00/138.31/87.75), service R3 527.55/month, NMD capacity R82.52/kVA, max
  demand R458.28/kVA.

### Consumer action required
- **Solar Dashboard:** none. `calculate_hourly_savings()` reads
  `tariff_rates.tou_schedule` automatically.
- **Solar Model:** pass the schedule when building the hourly TOU array:
  `build_hourly_tou(year, schedule=rates.tou_schedule)`. Otherwise non-Eskom
  TOU tariffs are classified on the Eskom clock.

### Changed
- Eskom TOU schedule refactored into the registry; behaviour is byte-identical
  (verified across all hour/day/season combinations). Total tariff count now 101.

## [1.4.0] - 2026-06-02

### Added
- **Eskom Landrate 2** and **Eskom Landrate 3** (three-phase, non-local
  authority) for both rate years: 2025/26 (effective 2025-04-01) and 2026/27
  (effective 2026-04-01). Source: Eskom Schedule of Standard Prices, all ex VAT.
  - Flat (non-TOU) tariff at supply voltage < 500 V; all-in energy rate (active +
    ancillary + network demand) = 287.00 c/kWh (2025/26), 310.41 c/kWh (2026/27),
    identical for Landrate 2 and 3.
  - Fixed R/POD/day charges (network capacity + service & administration +
    generation capacity) summed and annualised x365 into `service_charge_pa`:
    L2 R46 303.90 / L3 R69 466.80 (2025/26); L2 R51 205.85 / L3 R77 201.15 (2026/27).
  - No export tariff (grid-tied generation mandates a TOU tariff), so no export
    rates are returned. Three-phase NMD: L2 = 50 kVA, L3 = 100 kVA.

## [1.3.0] - 2026-06-01

### Added
- **Ephraim Mogale Local Municipality** 2025/26 provider with 8 tariffs (NERSA
  approval letter Ref NER/D/CBL4, effective 1 July 2025 - 30 June 2026, all ex
  VAT, flat energy, export = Energy Feedback 172.00 c/kWh):
  - Commercial/Industrial Conventional Three Phase 80A and 150A
  - Bulk Commercial 150A and Industrial Bulk 150A (with demand charges)
  - Agriculture Three Phase 80A, 150A, and Bulk (Bulk with demand charge)
  - Church/Schools/Charitable Three Phase 80A

### Changed
- Total tariff count now 98 (doc reference in DASHBOARD_INTEGRATION.md updated).

## [1.2.1] - 2026-05-29

### Fixed
- Saldanha Bay export set to R1.04/kWh ex VAT across all 6 tariffs.

## [1.2.0] - 2026-05-16

### Added
- New commercial tariffs for City of Ekurhuleni (CoE), Langeberg, and City of
  Tshwane.

### Fixed
- 2025/26 tariff corrections.

## [1.1.0] - 2026-05-12

### Added
- `admin_fees` and `eligibility` modules for Gen-Offset and Banking.

## [1.0.0] - 2026-05-10

### Added
- Initial release, extracted from the Solar Model: tariff data, TOU logic,
  rates/savings/history modules.
