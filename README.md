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
| `tariff_engine/tou.py` | TOU schedule classification (Peak/Standard/Off-Peak, HD/LD seasons) |
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
    calculate_hourly_savings,   # PV/BESS savings per hour
    list_tariffs,               # all available tariff display names
    TariffRates,                # dataclass
)
```

## Local development

```bash
# Editable install into your active venv
pip install -e .

# Run tests
pip install -e ".[dev]"
pytest
```

## Updating tariffs

1. Edit `tariff_engine/tariff_data.json` directly, or run the helper:
   ```bash
   py scripts/update_tariffs_2026.py
   ```
2. Run tests: `pytest`
3. Commit and push:
   ```bash
   git commit -am "tariffs: 2026/27 Eskom rates"
   git tag v2026.04
   git push --tags origin main
   ```
4. In each consumer repo (Solar Model, Dashboard), bump the pinned version in `requirements.txt`.

## Schema versioning

- **schema_version 1**: flat structure, single live version per tariff.
- **schema_version 2** (current): each provider/tariff wraps versions in a `versions` list with `effective` dates, supporting historical lookups.

Migration script: `scripts/migrate_tariff_v2.py` (one-off, already applied).

## Tariff calendar

| Provider | Rate-change anniversary |
|----------|------------------------|
| Eskom    | 1 April (1 Apr - 31 Mar) |
| Municipalities | 1 July (1 Jul - 30 Jun) |
