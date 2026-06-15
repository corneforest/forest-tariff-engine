"""
One-off data fix: Eskom Miniflex & Ruraflex 2025/26 active energy charge.

Bug: the 2025/26 `energy_c_per_kwh` values were stored as
(PDF active energy charge MINUS all per-kWh levies). The engine then re-adds
those same levies (legacy + ancillary + network demand + electrification +
affordability) to build the all-in rate, so the all-in only reproduced the
PDF "Active energy charge" column and never added the levies on top.

Correct structure (matches the 2026/27 blocks and the Eskom booklet):
    energy_c_per_kwh  := PDF active energy charge
    all_in            := energy + legacy + ancillary + network_demand[p]
                         + electrification + affordability

Fix: add the levies back into every energy cell so energy == PDF active.
Equivalently, the corrected energy == the value the engine currently (wrongly)
reports as the all-in. After the fix the engine adds the levies a second time,
giving the true all-in = PDF active + levies.

Run dry first:  py scripts/fix_eskom_2025_energy_levies.py --dry-run
Apply:          py scripts/fix_eskom_2025_energy_levies.py --apply
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tariff_engine" / "tariff_data.json"

TARIFFS = ["Eskom Miniflex", "Eskom Ruraflex"]
TARGET_EFFECTIVE = "2025-04-01"

# Parsed straight from the 2025/26 booklet PDFs (ex VAT) for the default cell
# (>900km, <500V). Used purely as an independent validation of the recompute.
PDF_ACTIVE_900_LT500 = {
    "Eskom Miniflex": {
        "HD": {"P": 705.13, "S": 176.28, "O": 117.52},
        "LD": {"P": 292.64, "S": 164.53, "O": 117.52},
    },
    "Eskom Ruraflex": {
        "HD": {"P": 711.73, "S": 177.93, "O": 118.61},
        "LD": {"P": 295.37, "S": 166.07, "O": 118.61},
    },
}


def adder(levies: dict, v: str, p: str) -> float:
    leg = levies["legacy_c_per_kwh"][v]
    anc = levies["ancillary_c_per_kwh"][v]
    nd = levies.get("network_demand_c_per_kwh", {}).get(v, {"P": 0.0, "S": 0.0, "O": 0.0})
    elec = levies.get("electrification_c_per_kwh", 0.0)
    afford = levies.get("affordability_c_per_kwh", 0.0)
    return leg + anc + nd[p] + elec + afford


def main() -> int:
    if "--apply" not in sys.argv and "--dry-run" not in sys.argv:
        print("Pass --dry-run or --apply")
        return 2
    apply = "--apply" in sys.argv

    data = json.loads(DATA.read_text(encoding="utf-8"))
    version = next(
        v for v in data["eskom"]["versions"] if v["effective"] == TARGET_EFFECTIVE
    )

    total_changed = 0
    for name in TARIFFS:
        t = version["tariffs"][name]
        levies = t["levies_c_per_kwh"]
        energy = t["energy_c_per_kwh"]
        zones = t["zones"]
        voltages = t["voltages"]

        print(f"\n=== {name} ({TARGET_EFFECTIVE}) ===")
        for z in zones:
            for v in voltages:
                for s in ("HD", "LD"):
                    for p in ("P", "S", "O"):
                        old = energy[z][v][s][p]
                        new = round(old + adder(levies, v, p), 2)
                        if z == ">900km" and v == "<500V":
                            exp = PDF_ACTIVE_900_LT500[name][s][p]
                            flag = "OK" if abs(new - exp) < 0.005 else "*** MISMATCH ***"
                            print(f"  {z:9} {v:7} {s} {p}: {old:8.2f} -> {new:8.2f} "
                                  f"(PDF active {exp:8.2f}) {flag}")
                        energy[z][v][s][p] = new
                        total_changed += 1

        # Recompute the reference all-in for the default cell (>900km, <500V).
        z0, v0 = ">900km", "<500V"
        cbi = {}
        for s in ("HD", "LD"):
            cbi[s] = {p: round(energy[z0][v0][s][p] + adder(levies, v0, p), 2)
                      for p in ("P", "S", "O")}
        t["confirmed_base_import_c_per_kwh"] = {
            "_note": ("Corrected all-in (active energy + levies) for >900km, <500V. "
                      "Reference only; engine computes from components."),
            **cbi,
        }
        print(f"  corrected all-in (>900km,<500V): "
              f"HD P{cbi['HD']['P']} S{cbi['HD']['S']} O{cbi['HD']['O']} | "
              f"LD P{cbi['LD']['P']} S{cbi['LD']['S']} O{cbi['LD']['O']}")

    print(f"\nTotal energy cells updated: {total_changed}")
    if apply:
        DATA.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"WROTE {DATA}")
    else:
        print("Dry run - no file written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
