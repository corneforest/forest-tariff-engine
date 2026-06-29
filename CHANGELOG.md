# Changelog

## [1.16.0] - 2026-06-29

### Added
- tariffs: Mangaung 2026/27 rates (Elecflex 1/2/3, effective 2026-07-01)

## [1.15.0] - 2026-06-29

### Added
- tariffs: Langeberg 2026/27 rates (Bulk LT/HT, Commercial 3-phase, TOU LT/HT, effective 2026-07-01)

## [1.14.0] - 2026-06-29

### Added
- tariffs: eThekwini 2026/27 rates (Business Scale 1, Industrial TOU, effective 2026-07-01)

## [1.13.0] - 2026-06-29

### Added
- tariffs: Drakenstein 2026/27 rates (Large Bulk, Bulk TOU MV/LV, effective 2026-07-01)

All notable changes to the Forest Energy Tariff Engine are recorded here so
consuming programs (Solar Model, Solar Dashboard) know what changed when they
bump their pinned version.

The version is authored in `pyproject.toml` and released as git tag `v{version}`
(see [RELEASING.md](RELEASING.md)). This file follows
[Keep a Changelog](https://keepachangelog.com/) and
[Semantic Versioning](https://semver.org/): PATCH = data fix on existing
tariffs, MINOR = new tariffs/providers, MAJOR = schema or API break.

## [1.12.0] - 2026-06-29

### Added
- **City of Cape Town 2026/27 tariff rates (draft budget, effective 2026-07-01).**
  Updated all four existing CoCT tariffs with 2026/27 rates from the City of Cape
  Town Draft Budget Annexure 6 (March 2026). Source is draft; confirm against the
  final approved budget before the July go-live.
  - CoCT Small Power Users 1: energy 298.10 c/kWh (+6.5%), service R4 204.18/month (+8.6%).
    SSEG Tariff 1: 96.18, Tariff 1+Incentive: 121.18, Tariff 2: 68.46 c/kWh.
  - CoCT LV TOU: HD Peak 783.74, HD Std 248.96, HD OP 189.53, LD Peak 366.62,
    LD Std 237.06, LD OP 189.53 c/kWh. Service R2 519.88/month, NMD capacity
    R39.00/kVA/month, demand R254.76/kVA/month. SSEG TOU HD P/S/O: 625.73/135.65/91.18,
    LD P/S/O: 243.47/124.74/81.18 c/kWh.
  - CoCT MV TOU: HD Peak 759.78, HD Std 242.26, HD OP 184.74, LD Peak 356.12,
    LD Std 230.74, LD OP 184.74 c/kWh. Service R2 610.22/month, NMD capacity
    R19.15/kVA/month, demand R82.38/kVA/month.
  - CoCT HV TOU: HD Peak 733.51, HD Std 234.90, HD OP 179.49, LD Peak 344.60,
    LD Std 223.80, LD OP 179.49 c/kWh. Service R2 610.22/month, NMD capacity
    R18.28/kVA/month, demand R78.67/kVA/month.
  All SSEG flat rates (Tariff 1/1+Incentive/2) and TOU rates are identical across
  LV, MV, and HV TOU tariffs.

## [1.11.0] - 2026-06-18

### Added
- **Eskom 2025/26 Gen-Offset (export) rates for Miniflex and Ruraflex.**
  Previously only 2026/27 carried Eskom export rates; the 2025/26 booklet does
  publish them (Gen-offset Urban/Rural, Non-local Authority, p45). Added
  `export_energy_c_per_kwh` + `confirmed_base_export_c_per_kwh` for both tariffs
  across all zones/voltages (ex VAT). Default cell >900km <500V, HD Peak:
  Miniflex 671.06 c/kWh, Ruraflex 677.66 c/kWh. Modelled exactly like the
  2026/27 blocks (all-in export = published gen-offset energy charge; ancillary
  credit omitted, as in 2026/27).
- **Eskom 2025/26 Gen-Offset admin fee block** (`admin_fees`, p42) so
  `get_eskom_admin_fee(...)` returns the correct R/POD/day for 2025/26 instead
  of 0: urban 0.73/12.40/19.37/19.37, rural 1.35/12.40/19.37/19.37 by NMD tier.
  The service + admin charge tiers (`service_charge_tiers`) already matched the
  gen-offset values and are unchanged.

  Script: `scripts/add_eskom_2025_export.py`.

## [1.10.1] - 2026-06-18

### Changed
- **Docs:** documented the v1.10.0 NMD service/admin API in README.md and
  DASHBOARD_INTEGRATION.md (`get_tariff_rates(..., nmd_kva=, key_customer=)`,
  `TariffRates.admin_charge_pa`, and the municipality-safe behaviour). No code
  or data change.

## [1.10.0] - 2026-06-16

### Added
- **Eskom service + administration charges by NMD bracket (Miniflex and
  Ruraflex, both rate years).** Previously `service_charge_pa` was hard-coded to
  the smallest (<=100 kVA) customer category and the admin charge was not
  represented at all. The data now carries a `service_charge_tiers` block per
  Eskom flex tariff (NMD brackets <=100 / <=500 / <=1000 / >1000 kVA plus a
  Key-customer category, each with service and admin R/POD/day, ex VAT). The
  resolver selects the bracket the same way it selects zone/voltage:
  `get_tariff_rates(...)` and `get_tariff_rates_for_date(...)` take an optional
  `nmd_kva` (and `key_customer`) and return the bracket's `service_charge_pa`
  plus a new `admin_charge_pa` field on `TariffRates`.
- **`TariffRates.admin_charge_pa`** (R/year). 0 for tariffs without an admin
  charge.

### Changed / compatibility
- `service_charge_pa` is **kept**. With no `nmd_kva` it returns the smallest
  bracket (<=100 kVA) for Eskom, identical to before, so existing callers are
  unaffected. Municipal tariffs ignore `nmd_kva` entirely and keep their flat
  `service_charge_pa` with `admin_charge_pa` = 0. Example: Ruraflex 2026/27 at
  NMD 1000 kVA now resolves service R78,807.15/yr + admin R7,690.55/yr, vs the
  flat R9,190.70/yr before. Script: `scripts/add_eskom_service_tiers.py`.

### Known gaps
- Megaflex service/admin brackets are **not** included here (folded into the
  Megaflex follow-up; Megaflex has only >1MVA + Key-customer categories and its
  saved service charge is currently wrong).

## [1.9.0] - 2026-06-16

### Added
- **Split capacity charge into separate generation and network components
  (Eskom Miniflex and Ruraflex, both rate years).** `TariffRates` now exposes
  `generation_capacity_charge_kva` and `network_capacity_charge_kva` (R/kVA/month)
  alongside the existing combined `capacity_charge_kva`, which is unchanged and
  still equals generation + network. In the data, `generation_capacity_r_kva_month`
  and `network_capacity_r_kva_month` are added next to `capacity_r_kva_month`.
  The generation capacity charge is constant per voltage (Miniflex: 3.49/8.09/6.12/7.02
  in 2025/26, 5.29/12.27/9.28/10.65 in 2026/27; Ruraflex: 3.34/5.03 then 5.07/7.63),
  verified against the Eskom booklets and the 1 April 2026 schedule. Backward
  compatible: tariffs without a split (all others, including municipal) report
  generation = 0 and network = the full capacity charge. Script:
  `scripts/split_eskom_capacity.py`.

### Known gaps
- **Eskom Megaflex 2026/27 is not yet split and is under-modelled.** Its saved
  capacity (42.66 R/kVA/month, <500V) is only the distribution network capacity
  charge; the generation capacity (5.29), transmission network (~11.92) and a
  distribution network demand charge (52.65 R/kVA/month on peak demand) are not
  yet captured. To be addressed in a separate change.

## [1.8.0] - 2026-06-16

### Added
- **City of Johannesburg (City Power) Large Consumer "Demand" tariffs, LV and
  MV (2025/26).** Three-part flat tariff for large consumers: service + network
  fixed charge, monthly demand charge (R/kVA), and a flat seasonal energy charge
  (no time-of-use). Source: CoJ Schedule of Tariffs July 2025 - June 2026,
  section 4 (Large Consumers), "Large Customer Demand" segment, ex VAT. Only LV
  and MV exist for this flat tariff (the HV band is TOU only), matching the
  official schedule.
  - `CoJ Large Consumer Demand LV`: energy 312.20 c/kWh winter / 267.41 c/kWh
    summer, demand 423.10 R/kVA/month, fixed 3541.57 R/month.
  - `CoJ Large Consumer Demand MV`: energy 294.83 c/kWh winter / 250.02 c/kWh
    summer, demand 395.48 R/kVA/month, fixed 10763.13 R/month.
  - Conventions match the existing CoJ Industrial TOU entries: service + network
    summed into `service_r_month`; energy carries the +6 c/kWh Network Surcharge
    that the booklet lists separately; season split follows the default schedule
    (winter Jun-Aug, summer Sep-May). Export = 90.05 c/kWh (Business and Large
    Power User embedded generator energy charge), applied flat.
  - Script: `scripts/add_coj_large_consumer_2025.py`.

### Fixed
- **City of Johannesburg Industrial TOU export rate (2025/26): 89.79 -> 90.05
  c/kWh** on all three bands (LV, MV, HV). The stored value was the prior-year
  embedded generator rate; the 2025/26 schedule (ITEM_03C_ANNEXURE.pdf, page 24)
  lists the Business and Large Power User Embedded Generator Energy Charge as
  90.05 c/kWh. Applied flat across both seasons and all TOU periods (18 cells).

## [1.7.2] - 2026-06-16

### Fixed
- **Eskom Miniflex and Ruraflex 2026/27 capacity charge (data fix, raises the
  R/kVA/month NMD charge).** `capacity_r_kva_month` was stored as the network
  capacity charge only, dropping the generation capacity charge. Verified
  against the official Eskom 1 April 2026 schedule, which lists both as separate
  R/kVA/month charges; the 2025/26 blocks already bundle generation + network.
  Capacity is now generation + network on all 24 cells (both tariffs, all zones
  and voltages). Effect by voltage: Ruraflex +5.07 (<500V) / +7.63 (≥500V&≤22kV);
  Miniflex +5.29 (<500V) / +12.27 (≥500V<66kV) / +9.28 (≥66kV≤132kV) / +10.65
  (>132kV). Example, >900km <500V: Ruraflex 56.95 -> 62.02, Miniflex
  54.58 -> 59.87 R/kVA/month. Energy, levies and service charges were already
  correct and are unchanged. Script: `scripts/fix_eskom_2026_gen_capacity.py`.

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
