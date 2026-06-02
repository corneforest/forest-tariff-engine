"""
Add Eskom Landrate 2 and Landrate 3 (three-phase) to both Eskom version blocks.

Source: Eskom Schedule of Standard Prices (non-local authority), Table 18
(2025/26, effective 2025-04-01) and Table 20 (2026/27, effective 2026-04-01).
All rates ex VAT. Landrate is a flat (non-TOU) tariff at supply voltage < 500 V.

Modelling decisions (confirmed with user):
  - Active energy charge already INCLUDES the c/kWh legacy charge (PDF footnote),
    so legacy = 0. The engine sums energy + ancillary + network demand to give the
    all-in flat rate (286.99 c/kWh in 2025/26, 310.41 c/kWh in 2026/27).
  - Landrate has no transmission-distance zones, so a single zone "Non-local
    Authority" and single voltage "<500V" are used; energy is flat across HD/LD/P/S/O.
  - Fixed R/POD/day charges (network capacity + service & administration +
    generation capacity) are summed and annualised x365 into service_charge_pa.
  - No export tariff (grid-tied generation mandates a TOU tariff), so export keys
    are omitted -> the engine returns no export rates for Landrate.
  - Three-phase NMD: Landrate 2 = 50 kVA (80 A/phase), Landrate 3 = 100 kVA
    (150 A/phase). The rate table is per sub-tariff and phase-agnostic.
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


def landrate(energy: float, ancillary: float, network_demand: float,
             net_capacity_r_day: float, service_admin_r_day: float,
             gen_capacity_r_day: float) -> dict:
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
            "electrification_c_per_kwh": 0,
            "affordability_c_per_kwh": 0,
        },
        "capacity_r_kva_month": {ZONE: {VOLT: 0}},
        "service_charge_pa": service_pa,
        "demand_charge_kva": 0.0,
    }


# effective date -> {tariff name: tariff dict}
ADDITIONS = {
    "2025-04-01": {
        "Eskom Landrate 2": landrate(
            energy=224.93, ancillary=0.41, network_demand=61.66,
            net_capacity_r_day=96.99, service_admin_r_day=24.50, gen_capacity_r_day=5.37,
        ),
        "Eskom Landrate 3": landrate(
            energy=224.93, ancillary=0.41, network_demand=61.66,
            net_capacity_r_day=155.32, service_admin_r_day=24.50, gen_capacity_r_day=10.50,
        ),
    },
    "2026-04-01": {
        "Eskom Landrate 2": landrate(
            energy=242.90, ancillary=0.45, network_demand=67.06,
            net_capacity_r_day=105.49, service_admin_r_day=26.65, gen_capacity_r_day=8.15,
        ),
        "Eskom Landrate 3": landrate(
            energy=242.90, ancillary=0.45, network_demand=67.06,
            net_capacity_r_day=168.93, service_admin_r_day=26.65, gen_capacity_r_day=15.93,
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
