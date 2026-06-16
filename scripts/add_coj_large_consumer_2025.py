"""
Add City of Johannesburg (City Power) Large Consumer "Demand" tariffs (LV + MV)
to the 2025/26 block.

Source: City of Johannesburg Schedule of Tariffs July 2025 - June 2026,
ITEM_03C_ANNEXURE.pdf, section 4 (Large Consumers), "Large Customer Demand"
segment (three-part flat tariff: service + network + demand + flat seasonal
energy; NOT time-of-use). Page 22 summary cross-checked against the detailed
LPU table. All values ex-VAT.

Only LV and MV bands exist for the flat Demand tariff (HV is TOU only), matching
the official schedule.

Conventions matching the existing CoJ Industrial TOU entries:
  * Fixed monthly charge = Service charge + Network charge summed into
    service_r_month (e.g. LV 1401.44 + 2140.13 = 3541.57).
  * Energy charges carry the +6 c/kWh Network Surcharge. The booklet states
    rates are "exclusive of the 6c/kWh Network Surcharge"; the existing CoJ
    Industrial TOU values bake it in (PDF winter peak 702.91 -> stored 708.91),
    so the all-in import rate is consistent across CoJ tariffs.
  * Season split matches the default "eskom" schedule: HD = winter (Jun-Aug),
    LD = summer (Sep-May). Energy is flat within each season (P = S = O).
  * Export = Business and Large Power User Embedded Generator Energy Charge
    90.05 c/kWh (page 24), applied flat. Not subject to the network surcharge.
"""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "tariff_engine" / "tariff_data.json"
PROVIDER = "City of Johannesburg"
EFFECTIVE = "2025-07-01"

NETWORK_SURCHARGE = 6.00          # c/kWh, added to booklet energy charges
EXPORT = 90.05                    # c/kWh, LPU embedded generator energy charge


def season(winter: float, summer: float) -> dict:
    """Flat energy within each season: HD = winter, LD = summer."""
    return {
        "HD": {"P": winter, "S": winter, "O": winter},
        "LD": {"P": summer, "S": summer, "O": summer},
    }


def flat(v: float) -> dict:
    return {"HD": {"P": v, "S": v, "O": v}, "LD": {"P": v, "S": v, "O": v}}


# Booklet energy (ex network surcharge): (winter, summer) c/kWh
TARIFFS = {
    "CoJ Large Consumer Demand LV": {
        "type": "municipal_flat",
        "energy_c_per_kwh": season(
            winter=306.20 + NETWORK_SURCHARGE,   # 312.20
            summer=261.41 + NETWORK_SURCHARGE,   # 267.41
        ),
        "export_c_per_kwh": flat(EXPORT),
        "service_r_month": round(1401.44 + 2140.13, 2),   # service + network = 3541.57
        "capacity_r_kva_month": 0,
        "demand_r_kva_month": 423.10,
    },
    "CoJ Large Consumer Demand MV": {
        "type": "municipal_flat",
        "energy_c_per_kwh": season(
            winter=288.83 + NETWORK_SURCHARGE,   # 294.83
            summer=244.02 + NETWORK_SURCHARGE,   # 250.02
        ),
        "export_c_per_kwh": flat(EXPORT),
        "service_r_month": round(1681.71 + 9081.42, 2),   # service + network = 10763.13
        "capacity_r_kva_month": 0,
        "demand_r_kva_month": 395.48,
    },
}


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    versions = {v["effective"]: v for v in data["providers"][PROVIDER]["versions"]}
    if EFFECTIVE not in versions:
        raise SystemExit(f"No {PROVIDER} {EFFECTIVE} block; aborting.")
    block = versions[EFFECTIVE]["tariffs"]
    for name, tariff in TARIFFS.items():
        if name in block:
            raise SystemExit(f"{name} already exists; aborting.")
        block[name] = tariff
    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Added:", ", ".join(TARIFFS))


if __name__ == "__main__":
    main()
