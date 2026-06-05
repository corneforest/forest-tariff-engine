"""
Add the City of Tshwane 2026/27 tariff version block (effective 2026-07-01).

Provisional: a uniform 8.8% increase on ALL rates and charges (energy, export,
service, capacity, demand) over the 2025/26 block. Built by scaling the existing
2025-07-01 values by 1.088 (rounded to 2 dp), so structure, nulls, type and any
tou_schedule are preserved exactly. VAT excluded; municipal year starts 1 July.
"""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "tariff_engine" / "tariff_data.json"
PROVIDER = "City of Tshwane"
OLD_EFFECTIVE = "2025-07-01"
NEW_EFFECTIVE = "2026-07-01"
FACTOR = 1.088

# Numeric scalar fields to escalate.
SCALAR_FIELDS = ("service_r_month", "capacity_r_kva_month", "demand_r_kva_month")
# Nested season -> period rate blocks to escalate.
RATE_BLOCKS = ("energy_c_per_kwh", "export_c_per_kwh")
# Fields copied through unchanged.
PASS_THROUGH = ("type", "tou_schedule")


def _scale(x):
    return round(x * FACTOR, 2)


def _scale_block(block):
    if block is None:
        return None
    return {season: {p: _scale(v) for p, v in periods.items()}
            for season, periods in block.items()}


def escalate(tariff: dict) -> dict:
    out = {}
    unknown = set(tariff) - set(SCALAR_FIELDS) - set(RATE_BLOCKS) - set(PASS_THROUGH)
    if unknown:
        raise SystemExit(f"Unexpected field(s) {sorted(unknown)} - update the script.")
    for k in PASS_THROUGH:
        if k in tariff:
            out[k] = tariff[k]
    for k in RATE_BLOCKS:
        if k in tariff:
            out[k] = _scale_block(tariff[k])
    for k in SCALAR_FIELDS:
        if k in tariff:
            out[k] = _scale(tariff[k])
    # Preserve original key order of the source tariff.
    return {k: out[k] for k in tariff}


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    prov = data["providers"][PROVIDER]
    versions = {v["effective"]: v for v in prov["versions"]}
    if NEW_EFFECTIVE in versions:
        raise SystemExit(f"{PROVIDER} already has a {NEW_EFFECTIVE} block; aborting.")
    old = versions[OLD_EFFECTIVE]["tariffs"]

    new = {name: escalate(t) for name, t in old.items()}
    prov["versions"].append({"effective": NEW_EFFECTIVE, "tariffs": new})
    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Added {PROVIDER} {NEW_EFFECTIVE}: {len(new)} tariffs at +8.8%.")


if __name__ == "__main__":
    main()
