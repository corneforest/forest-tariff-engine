"""
Update tariff_data.json with confirmed 2026/27 Eskom rates.
Effective date: 2026-04-01. Municipal tariffs untouched.

Export sections are IDEMPOTENT: they compute from hardcoded 2025/26 original
anchor values (≤300km) rather than reading from the current JSON, so re-running
the script always produces the same result.
"""
import json
from pathlib import Path

JSON_PATH = Path(__file__).resolve().parent.parent / "tariff_engine" / "tariff_data.json"

# ── HELPERS ──────────────────────────────────────────────────────────────
def r2(x):
    return round(x, 2)


# ── ZONE / VOLTAGE LISTS ─────────────────────────────────────────────────
MF_ZONES    = ["<=300km", ">300-600km", ">600-900km", ">900km"]
MF_VOLTAGES = ["<500V", ">=500V<66kV", ">=66kV<=132kV", ">132kV"]
RF_ZONES    = ["<=300km", ">300-600km", ">600-900km", ">900km"]
RF_VOLTAGES = ["<500V", ">=500V&<=22kV"]

# ── IMPORT ENERGY ANCHORS ────────────────────────────────────────────────
# Miniflex/Megaflex: ≤300km <500V anchor values (confirmed from PDF image)
MF_LV_BASE = {
    "HD": {"P": 739.28, "S": 184.82, "O": 123.20},
    "LD": {"P": 306.82, "S": 172.50, "O": 123.20},
}

# DLF ratios relative to <500V (1.1862)
DLF_RATIO = {
    "<500V":          1.0,
    ">=500V<66kV":    1.1556 / 1.1862,   # 0.97421
    ">=66kV<=132kV":  1.0724 / 1.1862,   # 0.90405
    ">132kV":         1.0000 / 1.1862,   # 0.84305
}
# TLF ratios relative to ≤300km (1.006)
TLF_RATIO = {
    "<=300km":    1.0,
    ">300-600km": 1.016 / 1.006,   # 1.009940
    ">600-900km": 1.026 / 1.006,   # 1.019881
    ">900km":     1.036 / 1.006,   # 1.029821
}

# Ruraflex energy — all 8 zone×voltage combos confirmed directly from image
RF_ENERGY = {
    "<=300km": {
        "<500V":         {"HD":{"P":746.19,"S":186.55,"O":124.36},"LD":{"P":309.68,"S":174.11,"O":124.36}},
        ">=500V&<=22kV": {"HD":{"P":726.93,"S":181.73,"O":121.16},"LD":{"P":301.85,"S":169.59,"O":121.16}},
    },
    ">300-600km": {
        "<500V":         {"HD":{"P":753.10,"S":188.27,"O":125.52},"LD":{"P":312.78,"S":175.85,"O":125.52}},
        ">=500V&<=22kV": {"HD":{"P":732.98,"S":183.25,"O":122.17},"LD":{"P":304.35,"S":170.93,"O":122.17}},
    },
    ">600-900km": {
        "<500V":         {"HD":{"P":761.12,"S":190.28,"O":126.84},"LD":{"P":316.43,"S":178.00,"O":126.84}},
        ">=500V&<=22kV": {"HD":{"P":740.90,"S":185.23,"O":123.48},"LD":{"P":308.37,"S":172.72,"O":123.48}},
    },
    ">900km": {
        "<500V":         {"HD":{"P":769.19,"S":192.29,"O":128.14},"LD":{"P":319.74,"S":180.14,"O":128.14}},
        ">=500V&<=22kV": {"HD":{"P":748.58,"S":187.14,"O":124.70},"LD":{"P":311.56,"S":174.55,"O":124.70}},
    },
}

# ── IMPORT LEVY CONSTANTS ────────────────────────────────────────────────
# Miniflex 2026/27 levies (electrification+affordability apply to ALL voltages)
MF_LEVIES = {
    "<500V":          {"legacy": 24.78, "ancillary": 0.45, "net_demand_ps": 32.30},
    ">=500V<66kV":    {"legacy": 22.40, "ancillary": 0.42, "net_demand_ps": 10.45},
    ">=66kV<=132kV":  {"legacy": 22.40, "ancillary": 0.39, "net_demand_ps": 10.21},
    ">132kV":         {"legacy": 20.89, "ancillary": 0.37, "net_demand_ps":  0.00},
}
MF_ELEC   = 5.37
MF_AFFORD = 5.10

# Ruraflex 2026/27 levies (network demand applies ALL periods, elec/afford = 0)
RF_LEVIES = {
    "<500V":         {"legacy": 25.01, "ancillary": 0.45, "net_demand_all": 52.55},
    ">=500V&<=22kV": {"legacy": 24.57, "ancillary": 0.45, "net_demand_all": 45.56},
}

# Megaflex 2026/27 levies (no network_demand_c_per_kwh, elec+afford all voltages)
MEG_LEVIES = {
    "<500V":          {"legacy": 24.78, "ancillary": 0.45},
    ">=500V<66kV":    {"legacy": 22.40, "ancillary": 0.42},
    ">=66kV<=132kV":  {"legacy": 22.40, "ancillary": 0.39},
    ">132kV":         {"legacy": 20.89, "ancillary": 0.37},
}
MEG_ELEC   = 5.37
MEG_AFFORD = 5.10

# ── CAPACITY CHARGES ─────────────────────────────────────────────────────
# ≤300km values confirmed from image
MF_CAP_LE300  = {"<500V": 54.22, ">=500V<66kV": 50.27, ">=66kV<=132kV": 24.33, ">132kV": 17.96}
MEG_CAP_LE300 = {"<500V": 42.84, ">=500V<66kV": 30.13, ">=66kV<=132kV": 14.16, ">132kV":  0.00}
RF_CAP = {
    "<=300km":    {"<500V": 56.60, ">=500V&<=22kV": 52.55},
    ">300-600km": {"<500V": 56.71, ">=500V&<=22kV": 52.66},
    ">600-900km": {"<500V": 56.83, ">=500V&<=22kV": 52.78},
    ">900km":     {"<500V": 56.95, ">=500V&<=22kV": 52.90},
}

# ── EXPORT CONSTANTS (IDEMPOTENT) ────────────────────────────────────────
# Scale factors from Table 43 (Gen-Offset PDF)
MF_EXPORT_SCALE = {
    "<500V":          1.09830,   # Urban LV:  714.47 / 650.52
    ">=500V<66kV":    1.08760,   # Urban MV:  688.29 / 632.85
    ">=66kV<=132kV":  1.08760,   # Urban HV:  636.07 / 584.84
    ">132kV":         1.08760,   # Urban EHV: 590.63 / 543.06
}
RF_EXPORT_SCALE = {"<500V": 1.08760, ">=500V&<=22kV": 1.08760}

# ── 2025/26 ORIGINAL EXPORT ANCHORS (≤300km zone) ─────────────────────────
# These are the PRE-UPDATE values. Hardcoded here so the export computation
# is fully idempotent — it never reads the existing JSON for export fields.
_MF_EXPORT_ORIG_LE300 = {
    "<500V":         {"HD":{"P":650.52,"S":162.63,"O":108.42},"LD":{"P":269.97,"S":151.79,"O":108.42}},
    ">=500V<66kV":   {"HD":{"P":632.85,"S":158.21,"O":105.48},"LD":{"P":262.63,"S":147.67,"O":105.48}},
    ">=66kV<=132kV": {"HD":{"P":584.84,"S":146.20,"O": 97.48},"LD":{"P":242.71,"S":136.47,"O": 97.48}},
    ">132kV":        {"HD":{"P":543.06,"S":135.76,"O": 90.52},"LD":{"P":225.37,"S":126.72,"O": 90.52}},
}
_MF_CBE_ORIG = {                # 2025/26 confirmed_base_export (Miniflex & Megaflex)
    "HD": {"P": 671.06, "S": 167.76, "O": 118.85},
    "LD": {"P": 230.60, "S": 167.76, "O": 118.85},
}

_RF_EXPORT_ORIG_LE300 = {       # 2025/26 Ruraflex ≤300km export anchors
    "<500V":          {"HD":{"P":656.92,"S":164.23,"O":109.49},"LD":{"P":272.62,"S":153.28,"O":109.49}},
    ">=500V&<=22kV":  {"HD":{"P":644.69,"S":161.16,"O":107.45},"LD":{"P":267.54,"S":150.43,"O":107.45}},
}
_RF_CBE_ORIG = {                # 2025/26 confirmed_base_export (Ruraflex)
    "HD": {"P": 677.66, "S": 169.40, "O": 119.94},
    "LD": {"P": 233.33, "S": 169.30, "O": 119.94},
}

# Compute 2026/27 export anchors (≤300km) = 2025/26 × scale factor
MF_EXPORT_BASE = {
    v: {s: {p: r2(_MF_EXPORT_ORIG_LE300[v][s][p] * MF_EXPORT_SCALE[v])
            for p in ("P","S","O")}
        for s in ("HD","LD")}
    for v in MF_VOLTAGES
}
MF_CBE = {                      # 2026/27 confirmed_base_export = 2025/26 × 1.09830 (LV Urban)
    s: {p: r2(_MF_CBE_ORIG[s][p] * 1.09830) for p in ("P","S","O")}
    for s in ("HD","LD")
}

RF_EXPORT_BASE = {
    v: {s: {p: r2(_RF_EXPORT_ORIG_LE300[v][s][p] * RF_EXPORT_SCALE[v])
            for p in ("P","S","O")}
        for s in ("HD","LD")}
    for v in RF_VOLTAGES
}
RF_CBE = {                      # 2026/27 confirmed_base_export = 2025/26 × 1.08760 (Rural)
    s: {p: r2(_RF_CBE_ORIG[s][p] * 1.08760) for p in ("P","S","O")}
    for s in ("HD","LD")
}


# ── BUILD FUNCTIONS ───────────────────────────────────────────────────────
def build_mf_energy():
    """Compute Miniflex/Megaflex energy_c_per_kwh from anchor via DLF/TLF ratios."""
    table = {}
    for zone, tlf in TLF_RATIO.items():
        table[zone] = {}
        for volt, dlf in DLF_RATIO.items():
            table[zone][volt] = {}
            for season in ("HD", "LD"):
                table[zone][volt][season] = {
                    p: r2(base * tlf * dlf)
                    for p, base in MF_LV_BASE[season].items()
                }
    return table


def build_mf_export_energy():
    """Build MF/MEG export_energy: ≤300km 2026/27 anchors × TLF for other zones.
    Idempotent — does not read from current JSON."""
    table = {}
    for zone, tlf in TLF_RATIO.items():
        table[zone] = {}
        for v in MF_VOLTAGES:
            base = MF_EXPORT_BASE[v]
            table[zone][v] = {
                s: {p: r2(base[s][p] * tlf) for p in ("P","S","O")}
                for s in ("HD","LD")
            }
    return table


def build_rf_export_energy():
    """Build Ruraflex export_energy: ≤300km 2026/27 anchors × TLF for other zones.
    Idempotent — does not read from current JSON."""
    table = {}
    for zone, tlf in TLF_RATIO.items():
        table[zone] = {}
        for v in RF_VOLTAGES:
            base = RF_EXPORT_BASE[v]
            table[zone][v] = {
                s: {p: r2(base[s][p] * tlf) for p in ("P","S","O")}
                for s in ("HD","LD")
            }
    return table


# ── UPDATE FUNCTIONS ──────────────────────────────────────────────────────
def update_miniflex(t):
    # 1. Import energy
    t["energy_c_per_kwh"] = build_mf_energy()

    # 2. Import levies (in-place update)
    lev = t["levies_c_per_kwh"]
    for v in MF_VOLTAGES:
        d = MF_LEVIES[v]
        lev["legacy_c_per_kwh"][v]    = d["legacy"]
        lev["ancillary_c_per_kwh"][v] = d["ancillary"]
        lev["network_demand_c_per_kwh"][v] = {
            "P": d["net_demand_ps"], "S": d["net_demand_ps"], "O": 0.0
        }
    lev["electrification_c_per_kwh"] = MF_ELEC
    lev["affordability_c_per_kwh"]   = MF_AFFORD

    # 3. Confirmed base import (>900km, <500V)
    e = t["energy_c_per_kwh"][">900km"]["<500V"]
    # P&S levy total: 24.78+0.45+32.30+5.37+5.10 = 68.00
    # O levy total:   24.78+0.45+ 0.00+5.37+5.10 = 35.70
    t["confirmed_base_import_c_per_kwh"] = {
        "HD": {"P": r2(e["HD"]["P"]+68.00), "S": r2(e["HD"]["S"]+68.00), "O": r2(e["HD"]["O"]+35.70)},
        "LD": {"P": r2(e["LD"]["P"]+68.00), "S": r2(e["LD"]["S"]+68.00), "O": r2(e["LD"]["O"]+35.70)},
    }

    # 4. Capacity (preserve zone increments from current JSON; ≤300km from image)
    cur = t["capacity_r_kva_month"]
    t["capacity_r_kva_month"] = {
        zone: {v: r2(MF_CAP_LE300[v] + cur[zone][v] - cur["<=300km"][v]) for v in MF_VOLTAGES}
        for zone in MF_ZONES
    }

    # 5. Export energy (IDEMPOTENT: computed from hardcoded 2026/27 anchors + TLF)
    t["export_energy_c_per_kwh"] = build_mf_export_energy()

    # 6. Confirmed base export (IDEMPOTENT: hardcoded 2026/27 value)
    t["confirmed_base_export_c_per_kwh"] = MF_CBE

    # 7. Service charge
    t["service_charge_pa"] = 5453.10


def update_ruraflex(t):
    # 1. Import energy (all values direct from image)
    t["energy_c_per_kwh"] = RF_ENERGY

    # 2. Import levies
    lev = t["levies_c_per_kwh"]
    for v in RF_VOLTAGES:
        d = RF_LEVIES[v]
        lev["legacy_c_per_kwh"][v]    = d["legacy"]
        lev["ancillary_c_per_kwh"][v] = d["ancillary"]
        nd = d["net_demand_all"]
        lev["network_demand_c_per_kwh"][v] = {"P": nd, "S": nd, "O": nd}
    lev["electrification_c_per_kwh"] = 0
    lev["affordability_c_per_kwh"]   = 0

    # 3. Confirmed base import (>900km, <500V; all-period levy = 25.01+0.45+52.55 = 78.01)
    e = RF_ENERGY[">900km"]["<500V"]
    lev_total = 25.01 + 0.45 + 52.55   # = 78.01
    t["confirmed_base_import_c_per_kwh"] = {
        s: {p: r2(e[s][p] + lev_total) for p in ("P","S","O")}
        for s in ("HD","LD")
    }

    # 4. Capacity (all zones confirmed from image)
    t["capacity_r_kva_month"] = RF_CAP

    # 5. Export energy (IDEMPOTENT: computed from hardcoded 2026/27 anchors + TLF)
    t["export_energy_c_per_kwh"] = build_rf_export_energy()

    # 6. Confirmed base export (IDEMPOTENT: hardcoded 2026/27 value)
    t["confirmed_base_export_c_per_kwh"] = RF_CBE

    # 7. Service charge (corrected to rural rate)
    t["service_charge_pa"] = 9190.70


def update_megaflex(t, mf_energy):
    # 1. Import energy (identical to Miniflex)
    t["energy_c_per_kwh"] = mf_energy

    # 2. Import levies (no network_demand; elec+afford all voltages)
    lev = t["levies_c_per_kwh"]
    for v in MF_VOLTAGES:
        d = MEG_LEVIES[v]
        lev["legacy_c_per_kwh"][v]    = d["legacy"]
        lev["ancillary_c_per_kwh"][v] = d["ancillary"]
        if "network_demand_c_per_kwh" in lev and v in lev["network_demand_c_per_kwh"]:
            lev["network_demand_c_per_kwh"][v] = {"P": 0.0, "S": 0.0, "O": 0.0}
    lev["electrification_c_per_kwh"] = MEG_ELEC
    lev["affordability_c_per_kwh"]   = MEG_AFFORD

    # 3. Confirmed base import (>900km, >=500V<66kV; levy = 22.40+0.42+5.37+5.10 = 33.29)
    e = mf_energy[">900km"][">=500V<66kV"]
    lev_mv    = MEG_LEVIES[">=500V<66kV"]
    lev_total = lev_mv["legacy"] + lev_mv["ancillary"] + MEG_ELEC + MEG_AFFORD  # = 33.29
    t["confirmed_base_import_c_per_kwh"] = {
        s: {p: r2(e[s][p] + lev_total) for p in ("P","S","O")}
        for s in ("HD","LD")
    }

    # 4. Capacity (preserve zone increments; EHV = 0.00 for all zones in 2026/27)
    cur = t["capacity_r_kva_month"]
    new_cap = {}
    for zone in MF_ZONES:
        new_cap[zone] = {}
        for v in MF_VOLTAGES:
            if v == ">132kV":
                new_cap[zone][v] = 0.00
            else:
                new_cap[zone][v] = r2(MEG_CAP_LE300[v] + cur[zone][v] - cur["<=300km"][v])
    t["capacity_r_kva_month"] = new_cap

    # 5. Export energy (IDEMPOTENT: same Urban table as Miniflex)
    t["export_energy_c_per_kwh"] = build_mf_export_energy()

    # 6. Confirmed base export (IDEMPOTENT: same as Miniflex — Urban LV scale)
    t["confirmed_base_export_c_per_kwh"] = MF_CBE

    # 7. Service charge
    t["service_charge_pa"] = 5453.10


# ── MAIN ──────────────────────────────────────────────────────────────────
with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)

eskom = data["eskom"]
eskom["effective"] = "2026-04-01"

mf_energy = build_mf_energy()

update_miniflex(eskom["tariffs"]["Eskom Miniflex"])
update_ruraflex(eskom["tariffs"]["Eskom Ruraflex"])
update_megaflex(eskom["tariffs"]["Eskom Megaflex"], mf_energy)

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("tariff_data.json updated for 2026/27.\n")

# ── CROSS-CHECKS ──────────────────────────────────────────────────────────
mf  = eskom["tariffs"]["Eskom Miniflex"]
rf  = eskom["tariffs"]["Eskom Ruraflex"]
meg = eskom["tariffs"]["Eskom Megaflex"]

checks = [
    ("effective",                              eskom["effective"],                                                "2026-04-01"),
    # Miniflex import
    ("Miniflex CB import HD P",                mf["confirmed_base_import_c_per_kwh"]["HD"]["P"],                 829.34),
    ("Miniflex CB import HD O",                mf["confirmed_base_import_c_per_kwh"]["HD"]["O"],                 162.57),
    ("Miniflex energy >900km LV HD P",         mf["energy_c_per_kwh"][">900km"]["<500V"]["HD"]["P"],             761.34),
    ("Miniflex capacity <=300km LV",           mf["capacity_r_kva_month"]["<=300km"]["<500V"],                   54.22),
    ("Miniflex service_charge_pa",             mf["service_charge_pa"],                                          5453.10),
    # Miniflex export
    ("Miniflex CBE HD P",                      mf["confirmed_base_export_c_per_kwh"]["HD"]["P"],                 737.04),
    ("Miniflex export <=300km LV HD P",        mf["export_energy_c_per_kwh"]["<=300km"]["<500V"]["HD"]["P"],     714.47),
    ("Miniflex export <=300km MV HD P",        mf["export_energy_c_per_kwh"]["<=300km"][">=500V<66kV"]["HD"]["P"],688.29),
    # Ruraflex import
    ("Ruraflex CB import HD P",                rf["confirmed_base_import_c_per_kwh"]["HD"]["P"],                 847.20),
    ("Ruraflex CB import HD O",                rf["confirmed_base_import_c_per_kwh"]["HD"]["O"],                 206.15),
    ("Ruraflex energy >900km LV HD P",         rf["energy_c_per_kwh"][">900km"]["<500V"]["HD"]["P"],             769.19),
    ("Ruraflex capacity >900km LV",            rf["capacity_r_kva_month"][">900km"]["<500V"],                    56.95),
    ("Ruraflex service_charge_pa",             rf["service_charge_pa"],                                          9190.70),
    # Ruraflex export
    ("Ruraflex CBE HD P",                      rf["confirmed_base_export_c_per_kwh"]["HD"]["P"],                 737.02),
    ("Ruraflex export <=300km LV HD P",        rf["export_energy_c_per_kwh"]["<=300km"]["<500V"]["HD"]["P"],     714.47),
    # Megaflex import
    ("Megaflex CB import HD P",                meg["confirmed_base_import_c_per_kwh"]["HD"]["P"],                774.98),
    ("Megaflex CB import HD O",                meg["confirmed_base_import_c_per_kwh"]["HD"]["O"],                156.90),
    ("Megaflex capacity <=300km MV",           meg["capacity_r_kva_month"]["<=300km"][">=500V<66kV"],            30.13),
    ("Megaflex capacity <=300km EHV",          meg["capacity_r_kva_month"]["<=300km"][">132kV"],                 0.00),
    ("Megaflex service_charge_pa",             meg["service_charge_pa"],                                         5453.10),
    # Megaflex export
    ("Megaflex CBE HD P",                      meg["confirmed_base_export_c_per_kwh"]["HD"]["P"],                737.04),
    ("Megaflex export <=300km LV HD P",        meg["export_energy_c_per_kwh"]["<=300km"]["<500V"]["HD"]["P"],    714.47),
]

all_ok = True
for name, got, expected in checks:
    ok = str(got) == str(expected) or abs(float(got) - float(expected)) < 0.02
    status = "OK  " if ok else "FAIL"
    if not ok:
        all_ok = False
    print(f"  {status}  {name}: {got}  (expected {expected})")

print()
print("All checks passed!" if all_ok else "SOME CHECKS FAILED -- review above.")
