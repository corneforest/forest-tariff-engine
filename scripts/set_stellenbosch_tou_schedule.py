"""
Point the Stellenbosch 2025/26 TOU tariffs at the "stellenbosch-2025" schedule.

Stellenbosch publishes its own TOU clock (different weekday peak/standard bands
from Eskom). The schedule itself is defined in tariff_engine/tou.py. This script
sets the "tou_schedule" key on the affected tariffs in the 2025-07-01 version
block. Absent the key, a tariff defaults to the Eskom schedule.
"""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "tariff_engine" / "tariff_data.json"

EFFECTIVE = "2025-07-01"
SCHEDULE = "stellenbosch-2025"
TARIFFS = [
    "Stellenbosch TOU LV",
    "Stellenbosch TOU MV",
    "Stellenbosch Large Power LV >80A (IND1)",
]


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    versions = {v["effective"]: v for v in data["providers"]["Stellenbosch"]["versions"]}
    if EFFECTIVE not in versions:
        raise SystemExit(f"No Stellenbosch version block for {EFFECTIVE}; aborting.")
    block = versions[EFFECTIVE]["tariffs"]
    for name in TARIFFS:
        if name not in block:
            raise SystemExit(f"{name} not found in {EFFECTIVE}; aborting.")
        block[name]["tou_schedule"] = SCHEDULE
        print(f"set tou_schedule={SCHEDULE} on {name}")
    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
