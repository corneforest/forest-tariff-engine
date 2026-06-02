"""
Add Stellenbosch "Large Power: Low Voltage > 80 Amp (IND1)" tariff.

Source: Stellenbosch electricity tariff schedule, "Application 2025/2026" column
(ex VAT), effective 2025-07-01. Added to the existing Stellenbosch 2025-07-01
version block.

Structure (demand-metered industrial tariff):
  - Flat import energy rate: 180.34 c/kWh (single Energy Rate, non-TOU).
  - TOU export/gen-offset credit: High Season -> HD, Low Season -> LD. These
    match the export block already stored on Stellenbosch TOU LV, confirming the
    reading.
  - Fixed charges combined into service_r_month: Reading cost 146.01 +
    Fixed Charge 3 381.54 = 3 527.55 R/month.
  - Notified Maximum Demand -> capacity_r_kva_month (NMD).
  - Maximum Demand Charge -> demand_r_kva_month (measured max demand).
"""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "tariff_engine" / "tariff_data.json"

EFFECTIVE = "2025-07-01"
NAME = "Stellenbosch Large Power LV >80A (IND1)"

ENERGY_FLAT = 180.34

TARIFF = {
    "type": "municipal_flat",
    "energy_c_per_kwh": {
        "HD": {"P": ENERGY_FLAT, "S": ENERGY_FLAT, "O": ENERGY_FLAT},
        "LD": {"P": ENERGY_FLAT, "S": ENERGY_FLAT, "O": ENERGY_FLAT},
    },
    "export_c_per_kwh": {
        "HD": {"P": 616.20, "S": 186.69, "O": 101.38},
        "LD": {"P": 201.00, "S": 138.31, "O": 87.75},
    },
    "service_r_month": round(146.01 + 3381.54, 2),
    "capacity_r_kva_month": 82.52,
    "demand_r_kva_month": 458.28,
}


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    versions = {v["effective"]: v for v in data["providers"]["Stellenbosch"]["versions"]}
    if EFFECTIVE not in versions:
        raise SystemExit(f"No Stellenbosch version block for {EFFECTIVE}; aborting.")
    block = versions[EFFECTIVE]["tariffs"]
    if NAME in block:
        raise SystemExit(f"{NAME} already exists in {EFFECTIVE}; aborting.")
    block[NAME] = TARIFF
    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{EFFECTIVE}: added {NAME} (service R/month {TARIFF['service_r_month']})")


if __name__ == "__main__":
    main()
