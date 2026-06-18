"""
Add Eskom 2025/26 Gen-Offset (export) energy rates + gen-offset admin_fees block
for Miniflex (urban) and Ruraflex (rural), Non-local Authority.

Source: Eskom Tariffs & Charges Booklet 2025/2026:
  - p45 "Gen-offset Urban / Rural - Non-local Authority" active energy charge
    (c/kWh, ex VAT) -> export_energy_c_per_kwh
  - p42 Gen-offset DUoS service + administration charges -> already present in
    service_charge_tiers (identical to the standard tariff service/admin); the
    admin tier values are added here as the version-level admin_fees block so
    get_eskom_admin_fee works for 2025/26 (mirrors the 2026/27 block).

Export is modelled exactly like the 2026/27 blocks: the engine returns
export_all_in = confirmed_base_export + export_energy[z][v] - export_energy[ref],
and confirmed_base_export is set to export_energy at the default cell
(>900km, <500V), so the all-in export equals the published gen-offset energy
charge. Ancillary credit is omitted (negligible; matches 2026/27).

Run dry:  py scripts/add_eskom_2025_export.py --dry-run
Apply:    py scripts/add_eskom_2025_export.py --apply
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tariff_engine" / "tariff_data.json"

def hd_ld(hp, hs, ho, lp, ls, lo):
    return {"HD": {"P": hp, "S": hs, "O": ho}, "LD": {"P": lp, "S": ls, "O": lo}}

# ── Miniflex (Gen-offset Urban) export energy c/kWh ex VAT, p45 ───────────────
MINI = {
    "<=300km": {
        "<500V":          hd_ld(650.52, 162.63, 108.42, 269.97, 151.79, 108.42),
        ">=500V<66kV":    hd_ld(632.85, 158.21, 105.48, 262.63, 147.67, 105.48),
        ">=66kV<=132kV":  hd_ld(584.84, 146.20,  97.48, 242.71, 136.47,  97.48),
        ">132kV":         hd_ld(543.06, 135.76,  90.52, 225.37, 126.72,  90.52),
    },
    ">300-600km": {
        "<500V":          hd_ld(657.36, 164.34, 109.56, 272.81, 153.39, 109.56),
        ">=500V<66kV":    hd_ld(639.53, 159.88, 106.60, 265.40, 149.22, 106.60),
        ">=66kV<=132kV":  hd_ld(591.03, 147.76,  98.51, 245.28, 137.91,  98.51),
        ">132kV":         hd_ld(548.83, 137.20,  91.48, 227.76, 128.06,  91.48),
    },
    ">600-900km": {
        "<500V":          hd_ld(664.21, 166.04, 110.70, 275.65, 154.98, 110.70),
        ">=500V<66kV":    hd_ld(646.20, 161.55, 107.70, 268.17, 150.78, 107.70),
        ">=66kV<=132kV":  hd_ld(597.22, 149.30,  99.54, 247.85, 139.36,  99.54),
        ">132kV":         hd_ld(554.60, 138.65,  92.44, 230.16, 129.41,  92.44),
    },
    ">900km": {
        "<500V":          hd_ld(671.06, 167.76, 111.85, 278.49, 156.58, 111.85),
        ">=500V<66kV":    hd_ld(652.87, 163.21, 108.82, 270.94, 152.33, 108.82),
        ">=66kV<=132kV":  hd_ld(603.41, 150.85, 100.58, 250.41, 140.80, 100.58),
        ">132kV":         hd_ld(560.37, 140.09,  93.39, 232.55, 130.76,  93.39),
    },
}

# ── Ruraflex (Gen-offset Rural) export energy c/kWh ex VAT, p45 ───────────────
RURA = {
    "<=300km": {
        "<500V":          hd_ld(656.92, 164.23, 109.49, 272.62, 153.28, 109.49),
        ">=500V&<=22kV":  hd_ld(644.69, 161.16, 107.45, 267.54, 150.43, 107.45),
    },
    ">300-600km": {
        "<500V":          hd_ld(663.84, 165.95, 110.64, 275.49, 154.89, 110.64),
        ">=500V&<=22kV":  hd_ld(651.48, 162.86, 108.58, 270.36, 152.02, 108.58),
    },
    ">600-900km": {
        "<500V":          hd_ld(670.75, 167.68, 111.79, 278.36, 156.51, 111.79),
        ">=500V&<=22kV":  hd_ld(658.27, 164.57, 109.72, 273.18, 153.60, 109.72),
    },
    ">900km": {
        "<500V":          hd_ld(677.66, 169.40, 112.94, 281.22, 158.12, 112.94),
        ">=500V&<=22kV":  hd_ld(665.05, 166.26, 110.85, 276.00, 155.19, 110.85),
    },
}

EXPORT = {"Eskom Miniflex": MINI, "Eskom Ruraflex": RURA}

# ── Gen-offset admin charge tiers (R/POD/day ex VAT), p42 ─────────────────────
ADMIN_FEES = {
    "_comment": ("Eskom Gen-Offset/Banking admin fee tier table (ex-VAT, R/POD/day). "
                 "Source: Tariffs & Charges Booklet 2025/2026 p42 (Gen-offset DUoS "
                 "service + administration charges). Tier matched by NMD/utilised "
                 "capacity (kVA). max_kva=null = upper-open tier."),
    "urban": [
        {"max_kva": 100,  "admin_r_per_pod_per_day": 0.73},
        {"max_kva": 500,  "admin_r_per_pod_per_day": 12.40},
        {"max_kva": 1000, "admin_r_per_pod_per_day": 19.37},
        {"max_kva": None, "admin_r_per_pod_per_day": 19.37},
    ],
    "rural": [
        {"max_kva": 100,  "admin_r_per_pod_per_day": 1.35},
        {"max_kva": 500,  "admin_r_per_pod_per_day": 12.40},
        {"max_kva": 1000, "admin_r_per_pod_per_day": 19.37},
        {"max_kva": None, "admin_r_per_pod_per_day": 19.37},
    ],
}


def reinsert_after(d, anchor, new_keys):
    out = {}
    for k, v in d.items():
        out[k] = v
        if k == anchor:
            out.update(new_keys)
    if not any(k == anchor for k in d):  # anchor missing: append
        out.update(new_keys)
    return out


def main():
    if "--apply" not in sys.argv and "--dry-run" not in sys.argv:
        print("Pass --dry-run or --apply"); return 2
    apply = "--apply" in sys.argv

    data = json.loads(DATA.read_text(encoding="utf-8"))
    ver = next(v for v in data["eskom"]["versions"] if v["effective"] == "2025-04-01")

    # admin_fees block (version level)
    if "admin_fees" in ver:
        raise SystemExit("2025/26 already has admin_fees; aborting.")
    ver_keys = list(ver.keys())
    # insert admin_fees right before tariffs for readability
    new_ver = {}
    for k in ver_keys:
        if k == "tariffs":
            new_ver["admin_fees"] = ADMIN_FEES
        new_ver[k] = ver[k]
    ver.clear(); ver.update(new_ver)

    for name, exp in EXPORT.items():
        t = ver["tariffs"][name]
        if "export_energy_c_per_kwh" in t:
            raise SystemExit(f"{name} already has export; aborting.")
        dz, dv = t["default_zone"], t["default_voltage"]
        cbe = exp[dz][dv]   # confirmed_base_export = export_energy at default cell
        # validate every cell present for the tariff's zones/voltages
        for z in t["zones"]:
            for v in t["voltages"]:
                assert z in exp and v in exp[z], f"missing {name} {z}/{v}"
        t2 = reinsert_after(t, "energy_c_per_kwh",
                            {"export_energy_c_per_kwh": exp})
        t2 = reinsert_after(t2, "confirmed_base_import_c_per_kwh",
                            {"confirmed_base_export_c_per_kwh": {
                                "HD": dict(cbe["HD"]), "LD": dict(cbe["LD"])}})
        ver["tariffs"][name] = t2
        print(f"{name}: export added. default {dz}/{dv} "
              f"HD P{cbe['HD']['P']} S{cbe['HD']['S']} O{cbe['HD']['O']} | "
              f"LD P{cbe['LD']['P']} S{cbe['LD']['S']} O{cbe['LD']['O']}")

    if apply:
        DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWROTE {DATA}")
    else:
        print("\nDry run - no file written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
