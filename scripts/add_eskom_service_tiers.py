"""
Schema addition: store Eskom service + administration charges by NMD bracket.

Eskom Miniflex/Ruraflex service and admin charges (R/POD/day) step up by
customer category, which is set by the customer's NMD. The engine previously
stored only the flat smallest-bracket service charge in `service_charge_pa`
(and no admin charge at all). This adds a `service_charge_tiers` block per
tariff (next to `service_charge_pa`, which is kept as the smallest-bracket
default) so the resolver can pick the right bracket from an NMD - the same way
zone/voltage already select energy and capacity.

Values ex VAT, R/POD/day, verified against the 2025/26 booklets and the
1 April 2026 schedule. Megaflex is intentionally excluded (handled in its own
follow-up: it only has >1MVA + Key Customer categories and other gaps).

Run dry:  py scripts/add_eskom_service_tiers.py --dry-run
Apply:    py scripts/add_eskom_service_tiers.py --apply
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tariff_engine" / "tariff_data.json"


def tiers(b100s, b100a, b500s, b500a, b1ks, b1ka, keys, keya):
    return {
        "_note": "Service + admin charge by customer category, R/POD/day ex VAT. "
                 "nmd_brackets matched by NMD (kVA); max_kva=null = upper-open. "
                 "key_customer is a special Eskom designation, not NMD-derived.",
        "nmd_brackets": [
            {"max_kva": 100,  "service_r_per_pod_per_day": b100s, "admin_r_per_pod_per_day": b100a},
            {"max_kva": 500,  "service_r_per_pod_per_day": b500s, "admin_r_per_pod_per_day": b500a},
            {"max_kva": 1000, "service_r_per_pod_per_day": b1ks,  "admin_r_per_pod_per_day": b1ka},
            {"max_kva": None, "service_r_per_pod_per_day": b1ks,  "admin_r_per_pod_per_day": b1ka},
        ],
        "key_customer": {"service_r_per_pod_per_day": keys, "admin_r_per_pod_per_day": keya},
    }


# (tariff, effective) -> tiers
TIERS = {
    ("Eskom Miniflex", "2025-04-01"): tiers(13.74, 0.73, 64.28, 12.40, 198.52, 19.37, 1118.46, 19.37),
    ("Eskom Miniflex", "2026-04-01"): tiers(14.94, 0.79, 69.91, 13.49, 215.91, 21.07, 1216.44, 21.07),
    ("Eskom Ruraflex", "2025-04-01"): tiers(23.15, 1.35, 64.28, 12.40, 198.52, 19.37, 1118.46, 19.37),
    ("Eskom Ruraflex", "2026-04-01"): tiers(25.18, 1.47, 69.91, 13.49, 215.91, 21.07, 1216.44, 21.07),
}
TOL = 0.01


def reinsert_after(d, anchor, new_keys):
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
        for name in ("Eskom Miniflex", "Eskom Ruraflex"):
            key = (name, ver["effective"])
            if key not in TIERS:
                continue
            t = ver["tariffs"][name]
            block = TIERS[key]
            # Consistency: existing service_charge_pa must equal smallest bracket service x365.
            smallest = block["nmd_brackets"][0]["service_r_per_pod_per_day"]
            expect = round(smallest * 365.0, 2)
            got = t["service_charge_pa"]
            flag = "OK" if abs(got - expect) < TOL else "*** MISMATCH ***"
            print(f"{name} {ver['effective']}: service_charge_pa={got} vs <=100kVA*365={expect} {flag}  "
                  f"| >500-1MVA service/day={block['nmd_brackets'][2]['service_r_per_pod_per_day']} "
                  f"admin/day={block['nmd_brackets'][2]['admin_r_per_pod_per_day']}")
            ver["tariffs"][name] = reinsert_after(t, "service_charge_pa",
                                                  {"service_charge_tiers": block})

    if apply:
        DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWROTE {DATA}")
    else:
        print("\nDry run - no file written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
