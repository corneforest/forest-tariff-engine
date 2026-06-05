"""
Add the City of Ekurhuleni 2026/27 tariff version block (effective 2026-07-01).

Source: CoE Schedule 2 of Electricity Tariffs, DRAFT version 2026.03.11
("Provisional increase for Council approval"). VAT EXCLUDED. Start 01 July 2026.

Increase factors (per the schedule's cover note, validated to the cent against
the 2025/26 block): all charges +9.01%, EXCEPT Tariff J and every tariff's
export credit, which rise +8.76% (Eskom Municflex-linked).

CoE TOU tariffs use the default "eskom" schedule (the engine's eskom weekend
bands were corrected in this same release to match the CoE/Eskom summer weekend
Standard window of 18:00-20:00), so no tou_schedule key is set.

Field mapping note: the "NAC" (network access charge, R/kVA) maps to
capacity_r_kva_month; the demand charge (R/kVA) maps to demand_r_kva_month.
Engine "D1 LV TOU" holds the PDF Tariff E 230/400V (LV non-direct) rates.

Values below are the PUBLISHED draft figures. The script cross-checks each
against old * factor and reports any deviation > 0.05 (rounding tolerance).
"""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "tariff_engine" / "tariff_data.json"
PROVIDER = "City of Ekurhuleni"
NEW_EFFECTIVE = "2026-07-01"
OLD_EFFECTIVE = "2025-07-01"

XHD, XLD = 152.85, 104.53   # standard CoE export credit (C/D/E/J)


def flat(hd, ld):
    return {"HD": {"P": hd, "S": hd, "O": hd}, "LD": {"P": ld, "S": ld, "O": ld}}


def tou(hd, ld):
    return {"HD": {"P": hd[0], "S": hd[1], "O": hd[2]},
            "LD": {"P": ld[0], "S": ld[1], "O": ld[2]}}


def export(hd, ld):
    return {"HD": {"P": hd, "S": hd, "O": hd}, "LD": {"P": ld, "S": ld, "O": ld}}


NEW = {
    "CoE Tariff B Mixed Three Phase": {
        "type": "municipal_flat",
        "energy_c_per_kwh": flat(379.82, 309.49),
        "export_c_per_kwh": export(114.61, 114.61),
        "service_r_month": 100.23, "capacity_r_kva_month": 28.96, "demand_r_kva_month": 0,
    },
    "CoE Tariff C LV (230/400V)": {
        "type": "municipal_flat",
        "energy_c_per_kwh": flat(503.00, 246.81),
        "export_c_per_kwh": export(XHD, XLD),
        "service_r_month": 3695.14, "capacity_r_kva_month": 108.08, "demand_r_kva_month": 264.01,
    },
    "CoE Tariff C LV Direct from Substation": {
        "type": "municipal_flat",
        "energy_c_per_kwh": flat(493.44, 240.01),
        "export_c_per_kwh": export(XHD, XLD),
        "service_r_month": 3695.14, "capacity_r_kva_month": 104.90, "demand_r_kva_month": 257.85,
    },
    "CoE Tariff C MV (>230/400V & <=11kV)": {
        "type": "municipal_flat",
        "energy_c_per_kwh": flat(485.33, 234.59),
        "export_c_per_kwh": export(XHD, XLD),
        "service_r_month": 5645.86, "capacity_r_kva_month": 98.21, "demand_r_kva_month": 247.63,
    },
    "CoE Tariff D1 LV TOU (NAC<1MVA)": {
        "type": "municipal_tou",
        "energy_c_per_kwh": tou((1184.71, 346.37, 214.05), (388.18, 255.37, 194.87)),
        "export_c_per_kwh": export(XHD, XLD),
        "service_r_month": 3345.78, "capacity_r_kva_month": 115.40, "demand_r_kva_month": 172.38,
    },
    "CoE Tariff D2 LV TOU Direct (NAC>=1MVA)": {
        "type": "municipal_tou",
        "energy_c_per_kwh": tou((780.75, 249.44, 190.40), (366.34, 237.64, 190.40)),
        "export_c_per_kwh": export(XHD, XLD),
        "service_r_month": 1122.16, "capacity_r_kva_month": 158.29, "demand_r_kva_month": 184.18,
    },
    "CoE Tariff D3 MV TOU (NAC>=1MVA)": {
        "type": "municipal_tou",
        "energy_c_per_kwh": tou((772.11, 240.79, 181.76), (357.69, 229.00, 181.76)),
        "export_c_per_kwh": export(XHD, XLD),
        "service_r_month": 3599.88, "capacity_r_kva_month": 131.43, "demand_r_kva_month": 153.36,
    },
    "CoE Tariff D4 HV TOU (NAC>=1MVA)": {
        "type": "municipal_tou",
        "energy_c_per_kwh": tou((766.27, 234.93, 175.89), (351.83, 223.12, 175.89)),
        "export_c_per_kwh": export(XHD, XLD),
        "service_r_month": 12887.64, "capacity_r_kva_month": 112.73, "demand_r_kva_month": 131.71,
    },
    "CoE Tariff E LV TOU Direct (NAC<1MVA)": {
        "type": "municipal_tou",
        "energy_c_per_kwh": tou((1163.23, 337.72, 207.70), (379.71, 248.74, 189.11)),
        "export_c_per_kwh": export(XHD, XLD),
        "service_r_month": 3345.78, "capacity_r_kva_month": 112.25, "demand_r_kva_month": 167.97,
    },
    "CoE Tariff E MV TOU (NAC<1MVA)": {
        "type": "municipal_tou",
        "energy_c_per_kwh": tou((1143.54, 331.42, 202.86), (372.27, 243.24, 184.51)),
        "export_c_per_kwh": export(XHD, XLD),
        "service_r_month": 5676.25, "capacity_r_kva_month": 105.33, "demand_r_kva_month": 159.25,
    },
    "CoE Tariff E HV TOU (NAC<1MVA)": {
        "type": "municipal_tou",
        "energy_c_per_kwh": tou((1069.02, 309.16, 189.36), (348.80, 227.45, 172.39)),
        "export_c_per_kwh": export(XHD, XLD),
        "service_r_month": 7533.81, "capacity_r_kva_month": 95.70, "demand_r_kva_month": 145.45,
    },
    "CoE Tariff J MV/HV Close-Coupled (NAC>=1MVA)": {
        "type": "municipal_tou",
        "energy_c_per_kwh": tou((760.96, 230.86, 171.96), (347.50, 219.10, 171.96)),
        "export_c_per_kwh": export(XHD, XLD),
        "service_r_month": 12858.09, "capacity_r_kva_month": 74.07, "demand_r_kva_month": 87.62,
    },
}


def _cross_check(old_tariffs):
    """Compare each new value to old * expected factor; report deltas > 0.05."""
    issues = []
    for name, new in NEW.items():
        old = old_tariffs[name]
        is_j = name.startswith("CoE Tariff J")
        chg_factor = 1.0876 if is_j else 1.0901   # non-export charges
        # energy
        for s in ("HD", "LD"):
            for p in ("P", "S", "O"):
                exp = round(old["energy_c_per_kwh"][s][p] * chg_factor, 2)
                got = new["energy_c_per_kwh"][s][p]
                if abs(got - exp) > 0.05:
                    issues.append(f"{name} energy {s}.{p}: got {got} vs ~{exp}")
        # export (always 8.76%)
        for s in ("HD", "LD"):
            exp = round((old.get("export_c_per_kwh") or {}).get(s, {}).get("P", 0) * 1.0876, 2)
            got = new["export_c_per_kwh"][s]["P"]
            if abs(got - exp) > 0.05:
                issues.append(f"{name} export {s}: got {got} vs ~{exp}")
        # fixed charges
        for fld in ("service_r_month", "capacity_r_kva_month", "demand_r_kva_month"):
            ofv = old.get(fld, 0) or 0
            exp = round(ofv * chg_factor, 2)
            got = new[fld]
            if abs(got - exp) > 0.05:
                issues.append(f"{name} {fld}: got {got} vs ~{exp}")
    return issues


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    prov = data["providers"][PROVIDER]
    versions = {v["effective"]: v for v in prov["versions"]}
    if NEW_EFFECTIVE in versions:
        raise SystemExit(f"{PROVIDER} already has a {NEW_EFFECTIVE} block; aborting.")
    old = versions[OLD_EFFECTIVE]["tariffs"]

    missing = set(old) ^ set(NEW)
    if missing:
        raise SystemExit(f"Tariff name mismatch vs {OLD_EFFECTIVE}: {sorted(missing)}")

    issues = _cross_check(old)
    if issues:
        print("CROSS-CHECK DEVIATIONS (>0.05 vs old*factor) - review before trusting:")
        for i in issues:
            print("  " + i)
    else:
        print("Cross-check OK: every value within rounding tolerance of old * factor.")

    prov["versions"].append({"effective": NEW_EFFECTIVE, "tariffs": NEW})
    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Added {PROVIDER} {NEW_EFFECTIVE} block with {len(NEW)} tariffs.")


if __name__ == "__main__":
    main()
