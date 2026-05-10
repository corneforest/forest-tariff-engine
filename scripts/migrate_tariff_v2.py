"""
scripts/migrate_tariff_v2.py
============================
One-off migration: converts tariff_data.json from schema_version 1 to 2.

Adds Eskom Miniflex and Ruraflex 2025/26 version blocks (effective 2025-04-01).
Existing 2026/27 data becomes the "2026-04-01" version.
All municipal providers are wrapped in a single "2025-07-01" version (no rate
change required for historical Dashboard use, as all Dashboard savings start
from 2026-01-01 which already falls in the 2025-07-01 municipal year).

Run once:
    py scripts/migrate_tariff_v2.py
"""
import json
import copy
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC  = ROOT / "tariff_engine" / "tariff_data.json"
DST  = ROOT / "tariff_engine" / "tariff_data.json"   # overwrite in place

# ---------------------------------------------------------------------------
# 2025/26 Miniflex tariff block (effective 2025-04-01)
# Base energy c/kWh: all-in PDF value minus all levies (see notes in rates.py)
# Levies sourced from Eskom Miniflex Schedule of Standard Prices 2025/26 PDF
# ---------------------------------------------------------------------------
MINIFLEX_2526 = {
    "zones":            ["<=300km", ">300-600km", ">600-900km", ">900km"],
    "voltages":         ["<500V", ">=500V<66kV", ">=66kV<=132kV", ">132kV"],
    "default_zone":     ">900km",
    "default_voltage":  "<500V",
    "energy_c_per_kwh": {
        "<=300km": {
            "<500V": {
                "HD": {"P": 622.07, "S": 108.63, "O": 81.27},
                "LD": {"P": 221.60, "S":  97.22, "O": 81.27},
            },
            ">=500V<66kV": {
                "HD": {"P": 625.09, "S": 124.90, "O": 78.93},
                "LD": {"P": 234.95, "S": 113.79, "O": 78.93},
            },
            ">=66kV<=132kV": {
                "HD": {"P": 578.93, "S": 114.74, "O": 72.56},
                "LD": {"P": 216.88, "S": 104.44, "O": 72.56},
            },
            ">132kV": {
                "HD": {"P": 547.95, "S": 115.10, "O": 67.01},
                "LD": {"P": 210.34, "S": 105.49, "O": 67.01},
            },
        },
        ">300-600km": {
            "<500V": {
                "HD": {"P": 628.91, "S": 110.34, "O": 82.41},
                "LD": {"P": 224.44, "S":  98.82, "O": 82.41},
            },
            ">=500V<66kV": {
                "HD": {"P": 631.77, "S": 126.57, "O": 80.05},
                "LD": {"P": 237.72, "S": 115.34, "O": 80.05},
            },
            ">=66kV<=132kV": {
                "HD": {"P": 585.12, "S": 116.30, "O": 73.59},
                "LD": {"P": 219.45, "S": 105.88, "O": 73.59},
            },
            ">132kV": {
                "HD": {"P": 553.72, "S": 116.55, "O": 67.97},
                "LD": {"P": 212.73, "S": 106.83, "O": 67.97},
            },
        },
        ">600-900km": {
            "<500V": {
                "HD": {"P": 635.76, "S": 112.05, "O": 83.55},
                "LD": {"P": 227.28, "S": 100.41, "O": 83.55},
            },
            ">=500V<66kV": {
                "HD": {"P": 638.44, "S": 128.24, "O": 81.15},
                "LD": {"P": 240.49, "S": 116.90, "O": 81.15},
            },
            ">=66kV<=132kV": {
                "HD": {"P": 591.31, "S": 117.84, "O": 74.62},
                "LD": {"P": 222.02, "S": 107.33, "O": 74.62},
            },
            ">132kV": {
                "HD": {"P": 559.49, "S": 117.99, "O": 68.93},
                "LD": {"P": 215.13, "S": 108.18, "O": 68.93},
            },
        },
        ">900km": {
            "<500V": {
                "HD": {"P": 642.61, "S": 113.76, "O": 84.70},
                "LD": {"P": 230.12, "S": 102.01, "O": 84.70},
            },
            ">=500V<66kV": {
                "HD": {"P": 645.11, "S": 129.91, "O": 82.27},
                "LD": {"P": 243.26, "S": 118.45, "O": 82.27},
            },
            ">=66kV<=132kV": {
                "HD": {"P": 597.50, "S": 119.39, "O": 75.66},
                "LD": {"P": 224.58, "S": 108.77, "O": 75.66},
            },
            ">132kV": {
                "HD": {"P": 565.26, "S": 119.43, "O": 69.88},
                "LD": {"P": 217.52, "S": 109.52, "O": 69.88},
            },
        },
    },
    "levies_c_per_kwh": {
        "legacy_c_per_kwh": {
            "<500V":          22.78,
            ">=500V<66kV":    22.20,
            ">=66kV<=132kV":  20.60,
            ">132kV":         19.21,
        },
        "ancillary_c_per_kwh": {
            "<500V":          0.41,
            ">=500V<66kV":    0.39,
            ">=66kV<=132kV":  0.36,
            ">132kV":         0.34,
        },
        "network_demand_c_per_kwh": {
            "<500V":         {"P": 29.70, "S": 29.70, "O": 0.0},
            ">=500V<66kV":   {"P":  9.61, "S":  9.61, "O": 0.0},
            ">=66kV<=132kV": {"P":  9.39, "S":  9.39, "O": 0.0},
            ">132kV":        {"P":  0.00, "S":  0.00, "O": 0.0},
        },
        "electrification_c_per_kwh": 4.94,
        "affordability_c_per_kwh":   4.69,
    },
    "capacity_r_kva_month": {
        "<=300km":   {"<500V": 53.34, ">=500V<66kV": 54.31, ">=66kV<=132kV": 28.49, ">132kV": 23.36},
        ">300-600km":{"<500V": 53.46, ">=500V<66kV": 54.41, ">=66kV<=132kV": 28.59, ">132kV": 23.53},
        ">600-900km":{"<500V": 53.56, ">=500V<66kV": 54.52, ">=66kV<=132kV": 28.68, ">132kV": 23.68},
        ">900km":    {"<500V": 53.67, ">=500V<66kV": 54.62, ">=66kV<=132kV": 28.77, ">132kV": 23.85},
    },
    "confirmed_base_import_c_per_kwh": {
        "_note": "All-in from PDF (>900km, <500V). Reference only.",
        "HD": {"P": 705.13, "S": 176.28, "O": 117.52},
        "LD": {"P": 292.64, "S": 164.53, "O": 117.52},
    },
    "service_charge_pa": 5015.10,   # 13.74 R/day (<=100 kVA service) x 365
    "demand_charge_kva": 0.0,
}

# ---------------------------------------------------------------------------
# 2025/26 Ruraflex tariff block (effective 2025-04-01)
# Note: network_demand applies to ALL TOU periods (unlike Miniflex Peak&Standard only)
# Note: electrification and affordability levies are 0 for Ruraflex
# Note: export rates not included (not available from 2025/26 PDF)
# ---------------------------------------------------------------------------
RURAFLEX_2526 = {
    "zones":            ["<=300km", ">300-600km", ">600-900km", ">900km"],
    "voltages":         ["<500V", ">=500V&<=22kV"],
    "default_zone":     ">900km",
    "default_voltage":  "<500V",
    "energy_c_per_kwh": {
        "<=300km": {
            "<500V": {
                "HD": {"P": 619.26, "S": 101.02, "O": 43.43},
                "LD": {"P": 215.04, "S":  89.50, "O": 43.43},
            },
            ">=500V&<=22kV": {
                "HD": {"P": 613.87, "S": 104.79, "O": 48.23},
                "LD": {"P": 216.80, "S":  93.49, "O": 48.23},
            },
        },
        ">300-600km": {
            "<500V": {
                "HD": {"P": 626.18, "S": 102.75, "O": 44.58},
                "LD": {"P": 217.91, "S":  91.11, "O": 44.58},
            },
            ">=500V&<=22kV": {
                "HD": {"P": 620.66, "S": 106.50, "O": 49.36},
                "LD": {"P": 219.62, "S":  95.08, "O": 49.36},
            },
        },
        ">600-900km": {
            "<500V": {
                "HD": {"P": 633.09, "S": 104.47, "O": 45.73},
                "LD": {"P": 220.77, "S":  92.72, "O": 45.73},
            },
            ">=500V&<=22kV": {
                "HD": {"P": 627.45, "S": 108.20, "O": 50.50},
                "LD": {"P": 222.44, "S":  96.66, "O": 50.50},
            },
        },
        ">900km": {
            "<500V": {
                "HD": {"P": 640.00, "S": 106.20, "O": 46.88},
                "LD": {"P": 223.64, "S":  94.34, "O": 46.88},
            },
            ">=500V&<=22kV": {
                "HD": {"P": 634.23, "S": 109.89, "O": 51.63},
                "LD": {"P": 225.26, "S":  98.24, "O": 51.63},
            },
        },
    },
    "levies_c_per_kwh": {
        "legacy_c_per_kwh": {
            "<500V":        23.00,
            ">=500V&<=22kV": 22.59,
        },
        "ancillary_c_per_kwh": {
            "<500V":        0.41,
            ">=500V&<=22kV": 0.41,
        },
        "network_demand_c_per_kwh": {
            "<500V":        {"P": 48.32, "S": 48.32, "O": 48.32},
            ">=500V&<=22kV": {"P": 41.89, "S": 41.89, "O": 41.89},
        },
        "electrification_c_per_kwh": 0,
        "affordability_c_per_kwh":   0,
    },
    "capacity_r_kva_month": {
        "<=300km":    {"<500V": 55.38, ">=500V&<=22kV": 53.35},
        ">300-600km": {"<500V": 55.48, ">=500V&<=22kV": 53.45},
        ">600-900km": {"<500V": 55.59, ">=500V&<=22kV": 53.56},
        ">900km":     {"<500V": 55.70, ">=500V&<=22kV": 53.67},
    },
    "confirmed_base_import_c_per_kwh": {
        "_note": "All-in from PDF (>900km, <500V). Reference only.",
        "HD": {"P": 711.73, "S": 177.93, "O": 118.61},
        "LD": {"P": 295.37, "S": 166.07, "O": 118.61},
    },
    "service_charge_pa": 8449.75,   # 23.15 R/day (<=100 kVA/kW service) x 365
    "demand_charge_kva": 0.0,
}


def main() -> None:
    with open(SRC, encoding="utf-8") as fh:
        data = json.load(fh)

    if data.get("schema_version", 1) != 1:
        print(f"Already schema_version {data['schema_version']}. Aborting.")
        return

    # ── Build 2025/26 Eskom version block (Miniflex + Ruraflex only) ----------
    tariffs_2526 = {
        "Eskom Miniflex": MINIFLEX_2526,
        "Eskom Ruraflex": RURAFLEX_2526,
    }

    # ── Promote existing 2026/27 eskom tariffs to a version block ------------
    eskom_2627_tariffs = copy.deepcopy(data["eskom"]["tariffs"])

    new_eskom = {
        "escalation_month": 4,
        "escalation_day":   1,
        "versions": [
            {"effective": "2025-04-01", "tariffs": tariffs_2526},
            {"effective": "2026-04-01", "tariffs": eskom_2627_tariffs},
        ],
    }

    # ── Wrap each provider in a versions list --------------------------------
    new_providers: dict = {}
    for pname, pdata in data["providers"].items():
        effective = pdata.get("effective", "2025-07-01")
        tariffs   = copy.deepcopy(pdata["tariffs"])
        new_providers[pname] = {
            "escalation_month": 7,
            "escalation_day":   1,
            "versions": [
                {"effective": effective, "tariffs": tariffs},
            ],
        }

    # ── Assemble new root structure -------------------------------------------
    new_data = {
        "_comment": (
            "SA Commercial Electricity Tariff Master Data. "
            "schema_version 2: versioned with effective dates per provider. "
            "Eskom escalates 1 April; all municipalities escalate 1 July. "
            "Add new version blocks each year; do NOT edit existing versions."
        ),
        "schema_version": 2,
        "eskom":     new_eskom,
        "providers": new_providers,
    }

    with open(DST, "w", encoding="utf-8") as fh:
        json.dump(new_data, fh, indent=2, ensure_ascii=False)

    print(f"Migrated to schema_version 2 -> {DST}")
    print("Eskom versions:")
    for v in new_data["eskom"]["versions"]:
        tariff_names = list(v["tariffs"].keys())
        print(f"  {v['effective']}: {tariff_names}")
    print(f"Providers: {len(new_data['providers'])} (each with 1 version)")


if __name__ == "__main__":
    main()
