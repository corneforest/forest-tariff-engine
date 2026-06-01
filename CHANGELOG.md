# Changelog

All notable changes to the Forest Energy Tariff Engine are recorded here so
consuming programs (Solar Model, Solar Dashboard) know what changed when they
bump their pinned version.

The version is authored in `pyproject.toml` and released as git tag `v{version}`
(see [RELEASING.md](RELEASING.md)). This file follows
[Keep a Changelog](https://keepachangelog.com/) and
[Semantic Versioning](https://semver.org/): PATCH = data fix on existing
tariffs, MINOR = new tariffs/providers, MAJOR = schema or API break.

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
