"""
Add Ephraim Mogale Local Municipality 2025/26 tariffs.

Source: NERSA approval letter Ref NER/D/CBL4, effective 1 July 2025 - 30 June 2026.
All rates ex VAT. Energy charges are flat (no TOU). Export = Energy Feedback 172.00 c/kWh.

Only the tariffs explicitly requested are added:
  - Commercial / Industrial Conventional (Three Phase - 80A)
  - Commercial / Industrial Conventional (Three Phase - 150A)
  - Bulk Commercial 150A
  - Industrial Bulk 150A
  - Agriculture - Three Phase 80A
  - Agriculture - Three Phase 150A
  - Agriculture Bulk
  - Church / Schools / Charitable - Three Phase 80A
"""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "tariff_engine" / "tariff_data.json"

EXPORT_FEEDBACK = 172.00  # c/kWh, "Energy Feedback"


def flat(value: float) -> dict:
    """Build a flat HD/LD x P/S/O block from a single c/kWh value."""
    block = {"P": value, "S": value, "O": value}
    return {"HD": dict(block), "LD": dict(block)}


def tariff(energy: float, service: float, demand: float = 0.0) -> dict:
    return {
        "type": "municipal_flat",
        "energy_c_per_kwh": flat(energy),
        "export_c_per_kwh": flat(EXPORT_FEEDBACK),
        "service_r_month": service,
        "capacity_r_kva_month": 0,
        "demand_r_kva_month": demand,
    }


TARIFFS = {
    "Ephraim Mogale Commercial/Industrial Conventional Three Phase 80A": tariff(264.00, 2739.74),
    "Ephraim Mogale Commercial/Industrial Conventional Three Phase 150A": tariff(264.00, 5190.02),
    "Ephraim Mogale Bulk Commercial 150A": tariff(190.00, 9976.40, 292.22),
    "Ephraim Mogale Industrial Bulk 150A": tariff(188.00, 9927.55, 282.74),
    "Ephraim Mogale Agriculture Three Phase 80A": tariff(231.30, 2316.04),
    "Ephraim Mogale Agriculture Three Phase 150A": tariff(231.30, 4964.40),
    "Ephraim Mogale Agriculture Bulk": tariff(187.00, 9642.17, 258.01),
    "Ephraim Mogale Church/Schools/Charitable Three Phase 80A": tariff(276.00, 755.57),
}


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    providers = data["providers"]

    if "Ephraim Mogale" in providers:
        raise SystemExit("Ephraim Mogale already exists; aborting to avoid overwrite.")

    providers["Ephraim Mogale"] = {
        "escalation_month": 7,
        "escalation_day": 1,
        "versions": [
            {
                "effective": "2025-07-01",
                "tariffs": TARIFFS,
            }
        ],
    }

    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Added Ephraim Mogale with {len(TARIFFS)} tariffs.")


if __name__ == "__main__":
    main()
