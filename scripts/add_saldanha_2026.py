"""
Add Saldanha Bay 2026/27 rates (effective 2026-07-01).

Source: Saldanha Bay Municipality "2026/27 Rates and tariffs document",
section 3 (Electricity), page 5.

Structural note
---------------
In the 2026/27 schedule the six "Bulk LV/MV" tariff names are marked
"Deleted" and replaced by a single set of "Industrial Consumers" kVA bands
(Tariff 3). The published band values are exactly the 2025/26 Bulk figures
escalated by the stated 9.26% electricity increase (~9.24% realised):

  Energy (all bands)  R1.7412/kWh  = 174.12 c/kWh   (159.39 -> 174.12)
  Demand (all bands)  R533/kVA/month                (488   -> 533)
  Service charge:
    71 - 500 kVA      R4 895/month                  (4 480/4 481 -> 4 895)
    501 - 630 kVA     R36 816/month                 (33 702 -> 36 816)
    631 - 999 kVA     R46 510/month                 (42 576 -> 46 510)
    1 - 5 MVA         R72 030/month                 (65 937 -> 72 030)

We keep the established six Bulk tariff NAMES (downstream lookups are by
name, and the repo convention is to keep names continuous across rate years
- see Stellenbosch v1.20.1). Each name is mapped to the escalated band value
that covers its kVA range.

Export/SSEG: the only feed-in tariff published is Tariff 4 "Domestic Infeed"
at R1.14/kWh (SSEG). This is applied flat across all periods/seasons, matching
how the 2025/26 export (R1.04/kWh) was stored.

Idempotent: re-running replaces the 2026-07-01 version block in place.
"""
import json
from pathlib import Path

JSON_PATH = Path(__file__).resolve().parent.parent / "tariff_engine" / "tariff_data.json"

PROVIDER = "Saldanha Bay"
EFFECTIVE = "2026-07-01"

ENERGY_C = 174.12   # R1.7412/kWh ex VAT
DEMAND_R = 533.0    # R/kVA/month
EXPORT_C = 114.0    # R1.14/kWh ex VAT (Tariff 4 Domestic Infeed, SSEG)

# Established Bulk name -> escalated 2026/27 service charge (R/month) for the
# kVA band that name covers.
SERVICE_R = {
    "Saldanha Bay Bulk LV up to 70 kVA": 4895.0,
    "Saldanha Bay Bulk LV 71 to 500 kVA": 4895.0,
    "Saldanha Bay Bulk LV 501 to 630 kVA": 36816.0,
    "Saldanha Bay Bulk MV 71 to 500 kVA": 4895.0,
    "Saldanha Bay Bulk MV 501 to 1000 kVA": 46510.0,
    "Saldanha Bay Bulk MV Above 1000 kVA": 72030.0,
}


def flat(value):
    return {"HD": {"P": value, "S": value, "O": value},
            "LD": {"P": value, "S": value, "O": value}}


def build_tariff(service_r_month):
    return {
        "type": "municipal_flat",
        "energy_c_per_kwh": flat(ENERGY_C),
        "export_c_per_kwh": flat(EXPORT_C),
        "service_r_month": service_r_month,
        "capacity_r_kva_month": 0,
        "demand_r_kva_month": DEMAND_R,
    }


def main():
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    provider = data["providers"][PROVIDER]

    tariffs = {name: build_tariff(service) for name, service in SERVICE_R.items()}
    new_version = {"effective": EFFECTIVE, "tariffs": tariffs}

    # Replace any existing 2026-07-01 block, then keep versions sorted.
    provider["versions"] = [v for v in provider["versions"] if v["effective"] != EFFECTIVE]
    provider["versions"].append(new_version)
    provider["versions"].sort(key=lambda v: v["effective"])

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"{PROVIDER}: added version effective {EFFECTIVE} with {len(tariffs)} tariffs:")
    for name, t in tariffs.items():
        print(f"  - {name}: service R{t['service_r_month']:.0f}/m, "
              f"demand R{DEMAND_R:.0f}/kVA, energy {ENERGY_C} c/kWh, export {EXPORT_C} c/kWh")


if __name__ == "__main__":
    main()
