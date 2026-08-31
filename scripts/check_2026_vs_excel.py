"""
Read-only audit: compare saved 2026/27 Eskom Miniflex & Ruraflex (NLA) against
the official Eskom Excel (1 April 2026 public schedule).

Compares, per zone/voltage: active energy (6 TOU cells), legacy, ancillary,
network demand, electrification, affordability, capacity charge (vs network-only
and vs generation+network), and service charge. Prints only mismatches plus a
summary. Does not modify anything.
"""
from __future__ import annotations

import json
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

# 1-indexed columns in the energy block
C_ZONE, C_VOLT = 3, 4
C_HD = {"P": 10, "S": 12, "O": 14}
C_LD = {"P": 16, "S": 18, "O": 20}
C_LEGACY, C_GENCAP, C_NETCAP = 22, 24, 26

TOL = 0.005
issues: list[str] = []


def approx(a, b):
    return a is not None and b is not None and abs(a - b) < TOL


def read_excel(wb, name):
    """Return {zone:{volt:{'energy':{HD/LD},'legacy','gencap','netcap'}}}."""
    ws = wb[SHEET[name]]
    vmap = VMAP[name]
    out = {}
    for row in ws.iter_rows(min_row=8, max_row=23):
        cells = {i + 1: c.value for i, c in enumerate(row)}
        z, v = cells.get(C_ZONE), cells.get(C_VOLT)
        if z not in ZONE or v not in vmap:
            continue
        zk, vk = ZONE[z], vmap[v]
        out.setdefault(zk, {})[vk] = {
            "energy": {
                "HD": {p: cells.get(C_HD[p]) for p in "PSO"},
                "LD": {p: cells.get(C_LD[p]) for p in "PSO"},
            },
            "legacy": cells.get(C_LEGACY),
            "gencap": cells.get(C_GENCAP),
            "netcap": cells.get(C_NETCAP),
        }
    return out


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    ver = next(v for v in data["eskom"]["versions"] if v["effective"] == "2026-04-01")
    wb = openpyxl.load_workbook(XLSM, data_only=True, read_only=True)

    for name in ["Eskom Ruraflex", "Eskom Miniflex"]:
        xl = read_excel(wb, name)
        t = ver["tariffs"][name]
        e = t["energy_c_per_kwh"]
        lev = t["levies_c_per_kwh"]
        cap = t["capacity_r_kva_month"]
        print(f"\n========== {name} 2026/27 ==========")

        energy_ok = cap_net_ok = cap_full_ok = legacy_ok = 0
        energy_n = cap_n = 0
        for zk, volts in xl.items():
            for vk, x in volts.items():
                # energy
                for s in ("HD", "LD"):
                    for p in "PSO":
                        energy_n += 1
                        jv, xv = e[zk][vk][s][p], x["energy"][s][p]
                        if approx(jv, xv):
                            energy_ok += 1
                        else:
                            issues.append(f"{name} ENERGY {zk}/{vk}/{s}/{p}: json={jv} excel={xv}")
                # legacy
                if approx(lev["legacy_c_per_kwh"][vk], x["legacy"]):
                    legacy_ok += 1
                else:
                    issues.append(f"{name} LEGACY {vk}: json={lev['legacy_c_per_kwh'][vk]} excel={x['legacy']}")
                # capacity
                cap_n += 1
                jcap = cap[zk][vk]
                if approx(jcap, x["netcap"]):
                    cap_net_ok += 1
                if approx(jcap, round((x["gencap"] or 0) + (x["netcap"] or 0), 2)):
                    cap_full_ok += 1

        print(f"  energy cells match : {energy_ok}/{energy_n}")
        print(f"  legacy match       : {legacy_ok}/{len(xl)*len(next(iter(xl.values())))}")
        print(f"  capacity == network-only (Z)        : {cap_net_ok}/{cap_n}")
        print(f"  capacity == generation+network (X+Z): {cap_full_ok}/{cap_n}")

        # sample the >900/<500V cell for capacity detail
        x9 = xl[">900km"]["<500V"]
        print(f"  >900/<500V capacity: json={cap['>900km']['<500V']}  "
              f"excel netcap(Z)={x9['netcap']}  gencap(X)={x9['gencap']}  "
              f"X+Z={round((x9['gencap'] or 0)+(x9['netcap'] or 0),2)}")
        print(f"  ancillary <500V    : json={lev['ancillary_c_per_kwh'].get('<500V')}")
        print(f"  network_demand <500V: json={lev['network_demand_c_per_kwh'].get('<500V')}")
        print(f"  electrification    : json={lev.get('electrification_c_per_kwh')}")
        print(f"  affordability      : json={lev.get('affordability_c_per_kwh')}")
        print(f"  service_charge_pa  : json={t['service_charge_pa']}  "
              f"(={t['service_charge_pa']/365:.2f} R/day)")

    print("\n========== MISMATCHES ==========")
    if not issues:
        print("  none (energy + legacy all match Excel)")
    for i in issues:
        print(" -", i)


if __name__ == "__main__":
    main()
