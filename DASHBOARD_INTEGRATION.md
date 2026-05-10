# tariff_engine — Handoff Brief for Solar Dashboard

## What this is

This `tariff_engine/` folder is a shared Python package maintained in the **Solar Model** project (Forest Energy). It is the single source of truth for all South African electricity tariff data and calculations. Do not edit the files in this folder directly in the Dashboard — changes must be made in Solar Model and synced across.

## What is inside

| File | Purpose |
|------|---------|
| `tou.py` | TOU schedule: which period (Peak/Standard/Off-Peak) applies to any hour |
| `rates.py` | Rate lookup: return import/export rates and fixed charges for any named tariff |
| `history.py` | Historical lookup: return rates that applied on a specific past date |
| `savings.py` | Savings calculation: compute hourly ZAR savings from actual plant data |
| `tariff_data.json` | Master data file: all tariff rates in c/kWh ex-VAT |

## How to install

No pip install needed. The folder is a local Python package. Place it in the root of the Dashboard project alongside your FastAPI `main.py`. Python will find it automatically.

```
solar-dashboard/
  tariff_engine/        ← this folder (copied from Solar Model)
    __init__.py
    tou.py
    rates.py
    history.py
    savings.py
    tariff_data.json
  main.py
  requirements.txt
  ...
```

The only external dependency is `numpy` (already in requirements for most data projects).

---

## Core concepts

### TOU periods

South African Eskom/municipal tariffs have three periods per hour:

| Code | Name | When (weekday, Low Demand season) |
|------|------|-----------------------------------|
| 1 | Peak | 07:00-09:00 and 18:00-21:00 |
| 2 | Standard | 06:00, 09:00-18:00, 21:00-22:00 |
| 3 | Off-Peak | 00:00-06:00, 22:00-24:00 |

High Demand season (June/July/August) has different peak windows.

### Seasons

| Code | Months |
|------|--------|
| "HI" | June, July, August |
| "LO" | All other months |

### Escalation dates

| Provider | New rates effective |
|----------|-------------------|
| Eskom | 1 April each year |
| All municipalities | 1 July each year |

---

## API reference

### 1. Get TOU period for any hour

```python
from tariff_engine.tou import get_tou_period

season, period = get_tou_period(
    month=7,          # 1-12
    hour=8,           # 0-23
    weekday_iso=1,    # 1=Mon ... 7=Sun  (use datetime.isoweekday())
    is_holiday=False, # SA public holiday flag
)
# Returns: ("HI", 1)  — High Demand, Peak
```

### 2. Build full-year TOU array (8760 hours)

```python
from tariff_engine.tou import build_hourly_tou

tou = build_hourly_tou(year=2026)
# Returns dict with numpy arrays: months, hours, weekdays, seasons, tou_periods, is_holiday
# tou["tou_periods"][h]  -> 1/2/3 for hour h
# tou["seasons"][h]      -> "HI" or "LO"
```

### 3. Get current tariff rates

```python
from tariff_engine.rates import get_tariff_rates

rates = get_tariff_rates(
    tariff_name="Eskom Megaflex",
    zone=">900km",       # optional, defaults to >900km
    voltage="<500V",     # optional, defaults to <500V
    sseg_option=None,    # optional, for CoCT SSEG export options
)

# Import rates (R/kWh ex-VAT)
rates.hd_peak        # High Demand Peak
rates.hd_standard
rates.hd_off_peak
rates.ld_peak        # Low Demand Peak
rates.ld_standard
rates.ld_off_peak

# Export rates (R/kWh, None if not available)
rates.export_hd_peak
# ...

# Fixed charges
rates.service_charge_pa    # R/year
rates.capacity_charge_kva  # R/kVA/month (NMD)
rates.demand_charge_kva    # R/kVA/month (actual max demand)

# Helper method
rate = rates.rate("HI", 1)      # R/kWh for HI Peak
export = rates.export_rate("LO", 3)  # export R/kWh for LO Off-Peak
```

### 4. Get historical rates for a past date

```python
from tariff_engine.history import get_tariff_rates_for_date
import datetime

rates_2025 = get_tariff_rates_for_date(
    tariff_name="Eskom Megaflex",
    date=datetime.date(2025, 9, 15),   # any past date
    zone=">900km",
    voltage="<500V",
)
# Returns TariffRates with the rates that applied on that date.
# Currently returns the 2026 rates (only one version in tariff_data.json).
# Once past-year data is added to tariff_data.json, this automatically
# selects the correct historical version.
```

### 5. Calculate hourly savings from actual plant data

```python
from tariff_engine.savings import calculate_hourly_savings

result = calculate_hourly_savings(
    grid_import_actual_kwh=[...],  # list/array of hourly actual grid import (kWh)
    solar_gen_kwh=[...],           # list/array of hourly solar generation (kWh)
    tariff_rates=rates,            # TariffRates object (from get_tariff_rates or historical)
    year=2026,                     # calendar year of the data
)

result["annual_saving_zar"]       # float: total annual saving (ZAR)
result["hourly_savings_zar"]      # list[float]: per-hour savings
result["hourly_cost_without_zar"] # list[float]: what it would have cost without solar
result["hourly_cost_with_zar"]    # list[float]: actual cost with solar
result["hours"]                   # int: number of hours processed
```

**How savings are calculated:**
- Counterfactual (without solar) = `grid_import_actual + solar_gen`
- Saving per hour = `(counterfactual × rate) - (grid_import_actual × rate)`
- This assumes the inverter gives you: actual net grid import AND solar generation separately.

**Note:** These are energy-only savings (kWh × rate). Demand/kVA savings require separate handling using `tariff_rates.demand_charge_kva`.

### 6. List all available tariffs

```python
from tariff_engine.rates import list_tariffs

names = list_tariffs()
# Returns sorted list of all tariff names:
# ['CoCT HV TOU', 'CoCT LV TOU', ..., 'Eskom Megaflex', 'Eskom Miniflex', ...]
```

---

## Supported tariffs

**Eskom** (zone + voltage options):
- Eskom Miniflex, Eskom Megaflex, Eskom Ruraflex

**City of Cape Town** (with optional SSEG export):
- CoCT Small Power Users 1, CoCT LV TOU, CoCT MV TOU, CoCT HV TOU
- Export options: "SSEG Tariff 1", "SSEG Tariff 1 + Incentive", "SSEG Tariff 2", "SSEG TOU"

**Municipalities:**
Nelson Mandela Bay, Drakenstein, City of Ekurhuleni, eThekwini, City of Johannesburg,
City of Mbombela, Midvaal, Mogale City, Rustenburg, Overstrand, Stellenbosch,
Saldanha Bay, City of Tshwane, Hessequa, Langeberg, Newcastle, Buffalo City, Msunduzi

---

## Typical Dashboard usage pattern

```python
import datetime
from tariff_engine.history import get_tariff_rates_for_date
from tariff_engine.savings import calculate_hourly_savings

# For a billing period in the past
billing_date = datetime.date(2025, 10, 1)
rates = get_tariff_rates_for_date("Eskom Megaflex", billing_date)

# Fetch actual hourly data from your database for that period
grid_kwh  = db.get_hourly_grid_import(site_id, billing_date)
solar_kwh = db.get_hourly_solar_gen(site_id, billing_date)

# Calculate savings
result = calculate_hourly_savings(grid_kwh, solar_kwh, rates, year=billing_date.year)
print(f"Saving for {billing_date}: R{result['annual_saving_zar']:,.2f}")
```

---

## Adding new tariff year data (annual update)

When Eskom publishes new rates (effective 1 April) or municipalities update (effective 1 July):

1. In the **Solar Model** project, update `tariff_engine/tariff_data.json`
2. Run `py sync_to_dashboard.py` in Solar Model to copy the updated folder to Dashboard
3. Commit and push both repos

To support true historical lookups, migrate `tariff_data.json` to schema_version 2 by wrapping each provider's tariffs in a `versions` array:

```json
{
  "schema_version": 2,
  "eskom": {
    "escalation_month": 4,
    "escalation_day": 1,
    "versions": [
      { "effective": "2026-04-01", "tariffs": { ...2026 rates... } },
      { "effective": "2027-04-01", "tariffs": { ...2027 rates... } }
    ]
  }
}
```

`get_tariff_rates_for_date()` will automatically select the correct version once schema_version 2 is in place. `get_tariff_rates()` (used by Solar Model) always returns the latest version regardless.

---

## Do not edit these files in the Dashboard repo

All changes to tariff logic or data must be made in **Solar Model** and synced across. If you edit here directly, the two projects will diverge and next sync will overwrite your changes.
