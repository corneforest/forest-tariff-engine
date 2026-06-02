# Forest Tariff Engine

South African electricity tariff engine (Eskom + municipalities). Single source of truth for tariff data and Time-of-Use (TOU) logic, shared across Forest Energy software tools.

## Consumed by

| Project | How |
|---------|-----|
| Forest Energy Solar Model | `pip install` from this repo via `requirements.txt` |
| Forest Energy Solar Dashboard | `pip install` from this repo via `requirements.txt` |

## What's in here

| Path | Purpose |
|------|---------|
| `tariff_engine/` | The Python package (importable as `tariff_engine`) |
| `tariff_engine/tariff_data.json` | Master rates file (Eskom + all municipalities, all schema versions) |
| `tariff_engine/tou.py` | TOU schedule classification (Peak/Standard/Off-Peak, HD/LD seasons); named `TOU_SCHEDULES` registry (Eskom default + municipal clocks) |
| `tariff_engine/rates.py` | `TariffRates` dataclass, rate lookup, JSON loading |
| `tariff_engine/history.py` | Historical date-aware rate lookup (`get_tariff_rates_for_date`) |
| `tariff_engine/savings.py` | Hourly savings calculation helpers |
| `scripts/` | Tariff data update + migration helpers |
| `tests/` | Standalone test suite |

## Public API

```python
from tariff_engine import (
    get_tariff_rates,           # latest rates by tariff name
    get_tariff_rates_for_date,  # rates active on a given date
    get_tou_period,             # classify (month, hour, weekday) into Peak/Std/Off
    build_hourly_tou,           # 8760-hour TOU array for a year
    list_tou_schedules,         # names of available TOU schedules
    calculate_hourly_savings,   # PV/BESS savings per hour
    list_tariffs,               # all available tariff display names
    TariffRates,                # dataclass (carries .tou_schedule)
)
```

## TOU schedules (per-tariff)

A TOU **schedule** defines which months are High/Low Demand and which clock
hours are Peak/Standard/Off-Peak. Different utilities use different schedules
(Eskom is the default; some municipalities, e.g. Stellenbosch, publish their
own). Schedules are data-driven entries in `tou.TOU_SCHEDULES`, and each tariff
names its schedule via the `tou_schedule` key in `tariff_data.json` (absent =
`"eskom"`). `TariffRates.tou_schedule` carries that name to consumers.

`get_tou_period(...)` and `build_hourly_tou(...)` take a `schedule` argument that
**defaults to `"eskom"`**, so existing calls keep working unchanged.

**What each consumer must do:**

| Consumer | Required change |
|----------|-----------------|
| Solar Dashboard | **None.** `calculate_hourly_savings()` reads `tariff_rates.tou_schedule` and applies the correct schedule automatically. |
| Solar Model | When building the hourly TOU array, pass the tariff's schedule: `build_hourly_tou(year, schedule=rates.tou_schedule)` instead of `build_hourly_tou(year)`. Without this, non-Eskom tariffs (e.g. Stellenbosch TOU) are classified on the Eskom clock. |

Schedules are **year-scoped when a utility revises its clock** (e.g.
`stellenbosch-2025`). Never edit an existing schedule entry; add a new one and
point the new rate-year's version block at it, so historical date lookups stay
accurate.

## Local development

```bash
# Editable install into your active venv
pip install -e .

# Run tests
pip install -e ".[dev]"
pytest
```

## Updating tariffs / releasing

**Read [`RELEASING.md`](RELEASING.md) before cutting a release.** It is the
canonical procedure and exists to prevent version/tag drift.

Key rules:

- `pyproject.toml` `version` is the **single source of truth**. The git tag is
  always `v{that version}`; egg-info and `dist/` are derived build output.
- **Never release from a stale checkout.** Always `git fetch origin --tags &&
  git merge --ff-only origin/main` first.
- Run the pre-flight check before tagging. It fails if the branch is behind
  origin, the tag already exists, or the version is malformed:
  ```bash
  py scripts/check_release.py
  ```

Short version:

1. Sync: `git fetch origin --tags && git merge --ff-only origin/main`
2. Edit `tariff_engine/tariff_data.json` (directly or via a `scripts/update_*.py` helper).
3. Bump `version` in `pyproject.toml` (PATCH = data on existing tariffs, MINOR = new tariffs, MAJOR = schema break).
4. `py scripts/check_release.py` (must print OK), then `py -m pytest -q`, then `py -m build`.
5. Commit, then `git tag -a v<version> ...`, then `git push origin main && git push origin v<version>`.
6. Bump the pinned version in each consumer repo (Solar Model, Dashboard) `requirements.txt`.

## Schema versioning

- **schema_version 1**: flat structure, single live version per tariff.
- **schema_version 2** (current): each provider/tariff wraps versions in a `versions` list with `effective` dates, supporting historical lookups.

Migration script: `scripts/migrate_tariff_v2.py` (one-off, already applied).

## Tariff calendar

| Provider | Rate-change anniversary |
|----------|------------------------|
| Eskom    | 1 April (1 Apr - 31 Mar) |
| Municipalities | 1 July (1 Jul - 30 Jun) |
