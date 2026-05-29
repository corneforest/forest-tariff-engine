"""
Set Saldanha Bay export (Gen-Offset) tariff to R1.04/kWh ex VAT on ALL tariffs.

Saldanha Bay tariffs are flat (municipal_flat), so the export is applied flat
across all TOU periods and both seasons: 104.0 c/kWh ex VAT.

Idempotent: re-running always produces the same flat 104.0 export block.
"""
import json
from pathlib import Path

JSON_PATH = Path(__file__).resolve().parent.parent / "tariff_engine" / "tariff_data.json"

PROVIDER = "Saldanha Bay"
EXPORT_C_PER_KWH = 104.0  # R1.04/kWh ex VAT, stored in c/kWh ex-VAT

FLAT_EXPORT = {
    "HD": {"P": EXPORT_C_PER_KWH, "S": EXPORT_C_PER_KWH, "O": EXPORT_C_PER_KWH},
    "LD": {"P": EXPORT_C_PER_KWH, "S": EXPORT_C_PER_KWH, "O": EXPORT_C_PER_KWH},
}

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)

provider = data["providers"][PROVIDER]
# Apply to the latest version (highest effective date).
latest = max(provider["versions"], key=lambda v: v["effective"])

updated = []
for name, t in latest["tariffs"].items():
    t["export_c_per_kwh"] = {
        "HD": dict(FLAT_EXPORT["HD"]),
        "LD": dict(FLAT_EXPORT["LD"]),
    }
    updated.append(name)

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"{PROVIDER} export set to {EXPORT_C_PER_KWH} c/kWh (R{EXPORT_C_PER_KWH/100:.2f}/kWh ex VAT) "
      f"on version effective {latest['effective']}:")
for name in updated:
    print(f"  - {name}")
print(f"\n{len(updated)} tariffs updated.")
