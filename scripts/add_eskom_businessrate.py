"""
Add Eskom Businessrate 2 and Businessrate 3 (three-phase) to both Eskom version
blocks: 2025/26 (effective 2025-04-01) and 2026/27 (effective 2026-04-01).

Source: Eskom Schedule of Standard Prices, "Businessrate non-local authority
tariff" (2025/26 Table 8, 2026/27 Table 5), ex VAT column. Flat (non-TOU).

Modelling (same conventions as Eskom Landrate):
  - Active energy charge already INCLUDES the legacy charge, so legacy = 0.
  - The "Electrification and rural network subsidy charge" (c/kWh) maps to the
    engine's electrification_c_per_kwh levy. All-in energy = energy + ancillary +
    network demand + electrification (244.82 c/kWh in 2025/26, 264.53 in 2026/27).
  - No transmission zones: single zone "Non-local Authority", voltage "<500V";
    energy flat across HD/LD/P/S/O.
  - Fixed R/POD/day charges (network capacity + service & administration +
    generation capacity) summed and annualised x365 into service_charge_pa.
  - No export tariff (grid-tied generation mandates a TOU tariff).
  - Three-phase NMD: Businessrate 2 = 50 kVA (80 A/phase),
    Businessrate 3 = 100 kVA (150 A/phase).
"""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "tariff_engine" / "tariff_data.json"

ZONE = "Non-local Authority"
VOLT = "<500V"
DAYS_PER_YEAR = 365


def flat_energy(value: float) -> dict:
    block = {"P": value, "S": value, "O": value}
    return {ZONE: {VOLT: {"HD": dict(block), "LD": dict(block)}}}


def businessrate(energy: float, ancillary: float, network_demand: float,
                 electrification: float, net_capacity_r_day: float,
                 service_admin_r_day: float, gen_capacity_r_day: float) -> dict:
    service_pa = round(
        (net_capacity_r_day + service_admin_r_day + gen_capacity_r_day) * DAYS_PER_YEAR, 2
    )
    nd = {"P": network_demand, "S": network_demand, "O": network_demand}
    return {
        "zones": [ZONE],
        "voltages": [VOLT],
        "default_zone": ZONE,
        "default_voltage": VOLT,
        "energy_c_per_kwh": flat_energy(energy),
        "levies_c_per_kwh": {
            "legacy_c_per_kwh": {VOLT: 0},
            "ancillary_c_per_kwh": {VOLT: ancillary},
            "network_demand_c_per_kwh": {VOLT: nd},
            "electrification_c_per_kwh": electrification,
            "affordability_c_per_kwh": 0,
        },
        "capacity_r_kva_month": {ZONE: {VOLT: 0}},
        "service_charge_pa": service_pa,
        "demand_charge_kva": 0.0,
    }


# effective date -> {tariff name: tariff dict}
ADDITIONS = {
    "2025-04-01": {
        "Eskom Businessrate 2": businessrate(
            energy=224.93, ancillary=0.41, network_demand=14.54, electrification=4.94,
            net_capacity_r_day=30.21, service_admin_r_day=14.70, gen_capacity_r_day=2.95,
        ),
        "Eskom Businessrate 3": businessrate(
            energy=224.93, ancillary=0.41, network_demand=14.54, electrification=4.94,
            net_capacity_r_day=75.38, service_admin_r_day=14.70, gen_capacity_r_day=7.37,
        ),
    },
    "2026-04-01": {
        "Eskom Businessrate 2": businessrate(
            energy=242.90, ancillary=0.45, network_demand=15.81, electrification=5.37,
            net_capacity_r_day=32.86, service_admin_r_day=15.99, gen_capacity_r_day=4.48,
        ),
        "Eskom Businessrate 3": businessrate(
            energy=242.90, ancillary=0.45, network_demand=15.81, electrification=5.37,
            net_capacity_r_day=81.98, service_admin_r_day=15.99, gen_capacity_r_day=11.18,
        ),
    },
}


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    versions = {v["effective"]: v for v in data["eskom"]["versions"]}
    for effective, tariffs in ADDITIONS.items():
        if effective not in versions:
            raise SystemExit(f"No Eskom version block for {effective}; aborting.")
        block = versions[effective]["tariffs"]
        for name, tariff in tariffs.items():
            if name in block:
                raise SystemExit(f"{name} already exists in {effective}; aborting.")
            block[name] = tariff
        print(f"{effective}: added {', '.join(tariffs)}")
    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
