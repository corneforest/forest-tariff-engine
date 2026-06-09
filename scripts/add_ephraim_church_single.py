"""
Add "Ephraim Mogale Church/Schools/Charitable Single 80A" to the 2025/26 block.

Source: Ephraim Mogale NERSA approval letter 2025/26 (ex VAT). Flat tariff.
Export = Energy Feedback 172.00 c/kWh, matching the other Ephraim Mogale tariffs.
"""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "tariff_engine" / "tariff_data.json"
EFFECTIVE = "2025-07-01"
NAME = "Ephraim Mogale Church/Schools/Charitable Single 80A"
ENERGY = 253.47
EXPORT = 172.00
SERVICE = 377.68


def flat(v):
    return {"HD": {"P": v, "S": v, "O": v}, "LD": {"P": v, "S": v, "O": v}}


TARIFF = {
    "type": "municipal_flat",
    "energy_c_per_kwh": flat(ENERGY),
    "export_c_per_kwh": flat(EXPORT),
    "service_r_month": SERVICE,
    "capacity_r_kva_month": 0,
    "demand_r_kva_month": 0,
}


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    versions = {v["effective"]: v for v in data["providers"]["Ephraim Mogale"]["versions"]}
    if EFFECTIVE not in versions:
        raise SystemExit(f"No Ephraim Mogale {EFFECTIVE} block; aborting.")
    block = versions[EFFECTIVE]["tariffs"]
    if NAME in block:
        raise SystemExit(f"{NAME} already exists; aborting.")
    block[NAME] = TARIFF
    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Added {NAME}")


if __name__ == "__main__":
    main()
