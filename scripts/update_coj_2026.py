"""
Add City of Johannesburg 2026/27 rates (effective 2026-07-01).

All charges on every CoJ tariff are escalated by 8.63% off the 2025/26
version, per the City Power 2026/27 increase. This includes energy, export,
service, capacity and demand charges. Rounded to 2 decimals.

IDEMPOTENT: the 2026-07-01 version is always recomputed from the 2025-07-01
version, so re-running the script always produces the same result.
"""
import copy
import json
from pathlib import Path

JSON_PATH = Path(__file__).resolve().parent.parent / "tariff_engine" / "tariff_data.json"

ESCALATION = 1.0863
BASE_EFFECTIVE = "2025-07-01"
NEW_EFFECTIVE = "2026-07-01"

RATE_FIELDS = (
    "energy_c_per_kwh",
    "export_c_per_kwh",
    "service_r_month",
    "capacity_r_kva_month",
    "demand_r_kva_month",
)


def escalate(value):
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: escalate(v) for k, v in value.items()}
    return round(value * ESCALATION, 2)


with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)

coj = data["providers"]["City of Johannesburg"]

base = next(v for v in coj["versions"] if v["effective"] == BASE_EFFECTIVE)

new_tariffs = {}
for name, tariff in base["tariffs"].items():
    t = copy.deepcopy(tariff)
    for field in RATE_FIELDS:
        t[field] = escalate(t[field])
    new_tariffs[name] = t

new_version = {"effective": NEW_EFFECTIVE, "tariffs": new_tariffs}

# Replace an existing 2026-07-01 version, or append.
coj["versions"] = [v for v in coj["versions"] if v["effective"] != NEW_EFFECTIVE]
coj["versions"].append(new_version)
coj["versions"].sort(key=lambda v: v["effective"])

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"CoJ {NEW_EFFECTIVE} version written ({len(new_tariffs)} tariffs, +8.63%).\n")

# ── CROSS-CHECKS ──────────────────────────────────────────────────────────
checks = []
for name, old in base["tariffs"].items():
    new = new_tariffs[name]
    checks.append((f"{name} energy HD P", new["energy_c_per_kwh"]["HD"]["P"],
                   round(old["energy_c_per_kwh"]["HD"]["P"] * ESCALATION, 2)))
    checks.append((f"{name} service", new["service_r_month"],
                   round(old["service_r_month"] * ESCALATION, 2)))
    checks.append((f"{name} demand", new["demand_r_kva_month"],
                   round(old["demand_r_kva_month"] * ESCALATION, 2)))
    checks.append((f"{name} export HD P", new["export_c_per_kwh"]["HD"]["P"],
                   round(old["export_c_per_kwh"]["HD"]["P"] * ESCALATION, 2)))

all_ok = True
for name, got, expected in checks:
    ok = abs(float(got) - float(expected)) < 0.005
    if not ok:
        all_ok = False
    print(f"  {'OK  ' if ok else 'FAIL'}  {name}: {got}  (expected {expected})")

print()
print("All checks passed!" if all_ok else "SOME CHECKS FAILED -- review above.")
