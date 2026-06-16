"""
Schema addition: split the bundled capacity charge into separate generation and
network components for Eskom Miniflex & Ruraflex (both rate years).

Background: capacity_r_kva_month bundles the generation capacity charge and the
network capacity charge into one R/kVA/month figure. Downstream programs need
them as two separate line items. This adds, next to capacity_r_kva_month:
    generation_capacity_r_kva_month   (constant per voltage, per the Eskom schedule)
    network_capacity_r_kva_month      (= capacity_r_kva_month - generation)
The combined capacity_r_kva_month is kept unchanged for backward compatibility.

The generation capacity charge is constant across transmission zones and varies
only by voltage (verified against the 2025/26 booklet PDFs and the 1 April 2026
Excel). network = combined - generation is therefore exact. The script asserts
generation + network == combined and checks the default cell against a known
network value.

Megaflex is intentionally excluded: its R/kVA/month charges are split across
generation, transmission network, distribution network capacity and a
distribution network demand charge, and need separate treatment.

Run dry:  py scripts/split_eskom_capacity.py --dry-run
Apply:    py scripts/split_eskom_capacity.py --apply
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tariff_engine" / "tariff_data.json"

# Generation capacity charge (R/kVA/month), constant across zones, by voltage.
GEN = {
    ("Eskom Miniflex", "2025-04-01"): {"<500V": 3.49, ">=500V<66kV": 8.09, ">=66kV<=132kV": 6.12, ">132kV": 7.02},
    ("Eskom Miniflex", "2026-04-01"): {"<500V": 5.29, ">=500V<66kV": 12.27, ">=66kV<=132kV": 9.28, ">132kV": 10.65},
    ("Eskom Ruraflex", "2025-04-01"): {"<500V": 3.34, ">=500V&<=22kV": 5.03},
    ("Eskom Ruraflex", "2026-04-01"): {"<500V": 5.07, ">=500V&<=22kV": 7.63},
}
# Known network value for the default cell (>900km, <500V) as a sanity check.
EXPECT_NET_900_LT500 = {
    ("Eskom Miniflex", "2025-04-01"): 50.18,
    ("Eskom Miniflex", "2026-04-01"): 54.58,
    ("Eskom Ruraflex", "2025-04-01"): 52.36,
    ("Eskom Ruraflex", "2026-04-01"): 56.95,
}
TOL = 0.005


def reinsert_after(d: dict, anchor: str, new_keys: dict) -> dict:
    """Return a new dict with new_keys inserted immediately after anchor key."""
    out = {}
    for k, v in d.items():
        out[k] = v
        if k == anchor:
            out.update(new_keys)
    return out


def main() -> int:
    if "--apply" not in sys.argv and "--dry-run" not in sys.argv:
        print("Pass --dry-run or --apply")
        return 2
    apply = "--apply" in sys.argv

    data = json.loads(DATA.read_text(encoding="utf-8"))

    for ver in data["eskom"]["versions"]:
        eff = ver["effective"]
        for name in ("Eskom Miniflex", "Eskom Ruraflex"):
            key = (name, eff)
            if key not in GEN:
                continue
            t = ver["tariffs"][name]
            combined = t["capacity_r_kva_month"]
            gen_by_v = GEN[key]
            gen_tbl, net_tbl = {}, {}
            for z, volts in combined.items():
                gen_tbl[z], net_tbl[z] = {}, {}
                for v, comb in volts.items():
                    g = gen_by_v[v]
                    n = round(comb - g, 2)
                    if n < 0:
                        raise SystemExit(f"NEGATIVE network {name} {eff} {z}/{v}: {comb}-{g}")
                    if abs(round(g + n, 2) - comb) >= TOL:
                        raise SystemExit(f"SUM MISMATCH {name} {eff} {z}/{v}")
                    gen_tbl[z][v], net_tbl[z][v] = g, n
            # sanity check the default cell
            exp = EXPECT_NET_900_LT500[key]
            got = net_tbl[">900km"]["<500V"]
            flag = "OK" if abs(got - exp) < TOL else "*** MISMATCH ***"
            print(f"{name} {eff}: >900/<500V  gen={gen_by_v['<500V']}  "
                  f"network={got} (expect {exp}) {flag}  combined={combined['>900km']['<500V']}")

            ver["tariffs"][name] = reinsert_after(
                t, "capacity_r_kva_month",
                {"generation_capacity_r_kva_month": gen_tbl,
                 "network_capacity_r_kva_month": net_tbl},
            )

    if apply:
        DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWROTE {DATA}")
    else:
        print("\nDry run - no file written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
