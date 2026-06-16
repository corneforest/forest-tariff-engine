"""
Data fix: add the generation capacity charge to Eskom Miniflex & Ruraflex
2026/27 (NLA) capacity_r_kva_month.

Bug: the 2026/27 capacity charge was stored as the NETWORK capacity charge only
(Excel col Z), dropping the GENERATION capacity charge (Excel col X). The
2025/26 blocks correctly bundle generation + network into one R/kVA/month value.

Fix: capacity := network + generation (Excel X + Z), matching 2025/26 and the
official 1 April 2026 Eskom schedule.

The generation capacity charge (X) is read straight from the Excel so the result
is exact. A precondition asserts every current value equals the Excel network
charge (Z) alone, so the fix cannot double-apply.

Run dry:  py scripts/fix_eskom_2026_gen_capacity.py --dry-run
Apply:    py scripts/fix_eskom_2026_gen_capacity.py --apply
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tariff_engine" / "tariff_data.json"
XLSM = Path(r"C:\Users\CorneGroenewald\Forest Energy\Forest Group - Engineering"
            r"\1. Sales Engineering\3. Tariffs\2026-27\Eskom"
            r"\Eskom-tariffs-1-April-2026-Public.xlsm")

ZONE = {0: "<=300km", 1: ">300-600km", 2: ">600-900km", 3: ">900km"}
VMAP = {
    "Eskom Ruraflex": {1: "<500V", 2: ">=500V&<=22kV"},
    "Eskom Miniflex": {1: "<500V", 2: ">=500V<66kV", 3: ">=66kV<=132kV", 4: ">132kV"},
}
SHEET = {"Eskom Ruraflex": "Ruraflex NLA", "Eskom Miniflex": "Miniflex NLA"}
C_ZONE, C_VOLT, C_GENCAP, C_NETCAP = 3, 4, 24, 26
TOL = 0.005


def read_excel_caps(wb, name):
    """Return {zone:{volt:(gencap, netcap)}}."""
    ws = wb[SHEET[name]]
    vmap = VMAP[name]
    out = {}
    for row in ws.iter_rows(min_row=8, max_row=23):
        cells = {i + 1: c.value for i, c in enumerate(row)}
        z, v = cells.get(C_ZONE), cells.get(C_VOLT)
        if z not in ZONE or v not in vmap:
            continue
        out.setdefault(ZONE[z], {})[vmap[v]] = (cells.get(C_GENCAP), cells.get(C_NETCAP))
    return out


def main() -> int:
    if "--apply" not in sys.argv and "--dry-run" not in sys.argv:
        print("Pass --dry-run or --apply")
        return 2
    apply = "--apply" in sys.argv

    data = json.loads(DATA.read_text(encoding="utf-8"))
    ver = next(v for v in data["eskom"]["versions"] if v["effective"] == "2026-04-01")
    wb = openpyxl.load_workbook(XLSM, data_only=True, read_only=True)

    changed = 0
    for name in ["Eskom Ruraflex", "Eskom Miniflex"]:
        caps = ver["tariffs"][name]["capacity_r_kva_month"]
        xl = read_excel_caps(wb, name)
        print(f"\n=== {name} 2026/27 ===")
        for zk, volts in xl.items():
            for vk, (gen, net) in volts.items():
                old = caps[zk][vk]
                if abs(old - net) >= TOL:
                    raise SystemExit(
                        f"PRECONDITION FAILED {name} {zk}/{vk}: stored {old} != "
                        f"Excel network {net}. Aborting (may already be fixed)."
                    )
                new = round(net + gen, 2)
                caps[zk][vk] = new
                changed += 1
                if vk == "<500V":
                    print(f"  {zk:11} {vk:13}: {old:6.2f} -> {new:6.2f}  (network {net} + gen {gen})")

    print(f"\nCapacity cells updated: {changed}")
    if apply:
        DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"WROTE {DATA}")
    else:
        print("Dry run - no file written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
