"""
tariff_engine/rates.py
======================
Tariff rate data: TariffRates dataclass, rate lookup, JSON loading.

Public API
----------
    TariffRates                          dataclass
    get_tariff_rates(name, ...)       -> TariffRates   (latest version)
    list_tariffs()                    -> list[str]
    _load_tariff_json(name)           -> dict          (latest, cached)
    _load_tariff_json_for_date(name, date) -> dict     (historical, uncached)
    _get_raw_tariff_data()            -> dict          (raw JSON)
    _resolve_tariff_rates(name, data, ...) -> TariffRates

tariff_data.json lives alongside this file in tariff_engine/.
All rates stored in c/kWh ex-VAT; get_tariff_rates() divides by 100.

Schema versioning
-----------------
schema_version 1 (current): flat structure with single "eskom" + "providers" blocks.
schema_version 2 (future):  each block has a "versions" list with "effective" dates,
    supporting historical lookups. _get_tariff_data(date) selects the right version.
"""
from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_TARIFF_DATA_PATH = Path(__file__).parent / "tariff_data.json"

_raw_tariff_cache: Optional[dict] = None       # raw JSON, loaded once per process
_tariff_resolved_cache: dict[str, dict] = {}   # display name -> resolved flat dict


def _get_raw_tariff_data() -> dict:
    """Load and cache the raw tariff_data.json (once per process)."""
    global _raw_tariff_cache
    if _raw_tariff_cache is None:
        with open(_TARIFF_DATA_PATH, encoding="utf-8") as fh:
            _raw_tariff_cache = json.load(fh)
    return _raw_tariff_cache


def _find_version(versions: list, date: Optional[_dt.date]) -> dict:
    """
    Return the version active on date (highest effective <= date).
    If date is None, returns the latest version.
    Falls back to the earliest version if date precedes all known versions.
    """
    if date is None:
        return max(versions, key=lambda v: v["effective"])
    applicable = [v for v in versions if _dt.date.fromisoformat(v["effective"]) <= date]
    if not applicable:
        return min(versions, key=lambda v: v["effective"])
    return max(applicable, key=lambda v: v["effective"])


def _get_tariff_data(date: Optional[_dt.date] = None) -> dict:
    """
    Return tariff data in flat v1-compatible format.

    date=None  : returns the latest (or only) version — used by Solar Model.
    date=<date>: returns the version active on that date — used by Dashboard.

    Handles both schema_version 1 (flat, single version) and
    schema_version 2 (versioned with effective dates).
    """
    raw = _get_raw_tariff_data()
    if raw.get("schema_version", 1) == 1:
        return raw  # already flat; single version only

    # schema_version 2: extract the right version for each provider
    result: dict = {"providers": {}}
    eskom = raw.get("eskom", {})
    eskom_ver = _find_version(eskom.get("versions", []), date)
    result["eskom"] = {"effective": eskom_ver["effective"], "tariffs": eskom_ver["tariffs"]}

    for pname, pdata in raw.get("providers", {}).items():
        ver = _find_version(pdata.get("versions", []), date)
        result["providers"][pname] = {"tariffs": ver["tariffs"]}

    return result


def _eskom_import_all_in(
    energy: dict,
    levies: dict,
    zones: list,
    voltages: list,
) -> dict:
    """
    Compute all-in import rate table (c/kWh) for every zone/voltage using direct
    component summation:

        import_all_in[z][v][s][p] = energy[z][v][s][p]
                                  + legacy[v]
                                  + ancillary[v]
                                  + network_demand[v][p]   (0 if not present)
                                  + electrification
                                  + affordability

    This correctly applies voltage-specific levies to each voltage band.

    Returns rates in c/kWh shaped:
        { zone: { voltage: { "HD": {"P":...,"S":...,"O":...}, "LD": {...} } } }
    """
    elec   = levies.get("electrification_c_per_kwh", 0.0)
    afford = levies.get("affordability_c_per_kwh", 0.0)
    nd_tbl = levies.get("network_demand_c_per_kwh", {})

    imp: dict = {}
    for z in zones:
        imp[z] = {}
        for v in voltages:
            leg = levies["legacy_c_per_kwh"][v]
            anc = levies["ancillary_c_per_kwh"][v]
            nd  = nd_tbl.get(v, {"P": 0.0, "S": 0.0, "O": 0.0})
            imp[z][v] = {
                s: {p: round(energy[z][v][s][p] + leg + anc + nd[p] + elec + afford, 4)
                    for p in ("P", "S", "O")}
                for s in ("HD", "LD")
            }
    return imp


def _eskom_export_delta(
    export_energy: dict,
    confirmed_base_export: dict,
    default_zone: str,
    default_voltage: str,
    zones: list,
    voltages: list,
) -> dict:
    """
    Compute all-in export/gen-offset rate table (c/kWh) using the delta formula.
    Kept for exports because export levy differences across voltage bands are very
    small (~0.66 c/kWh max), so the anchored delta remains acceptably accurate.

        export_all_in[z][v][s][p] = confirmed_base_export[s][p]
                                  + export_energy[z][v][s][p]
                                  - export_energy[default_zone][default_voltage][s][p]

    Returns rates in c/kWh, same shape as _eskom_import_all_in.
    """
    ref_hd = export_energy[default_zone][default_voltage]["HD"]
    ref_ld = export_energy[default_zone][default_voltage]["LD"]

    def _delta(base: dict, new_e: dict, ref_e: dict) -> dict:
        return {p: round(base[p] + new_e[p] - ref_e[p], 4) for p in ("P", "S", "O")}

    exp: dict = {}
    for z in zones:
        exp[z] = {}
        for v in voltages:
            exp[z][v] = {
                "HD": _delta(confirmed_base_export["HD"], export_energy[z][v]["HD"], ref_hd),
                "LD": _delta(confirmed_base_export["LD"], export_energy[z][v]["LD"], ref_ld),
            }
    return exp


def _resolve_from_flat_td(name: str, td: dict) -> dict:
    """
    Resolve a tariff display name to a flat dict from a pre-flattened tariff data dict.
    Shared by _load_tariff_json (latest, cached) and _load_tariff_json_for_date (historical).
    """
    # ── Eskom tariffs ────────────────────────────────────────────────────────
    eskom_tariffs = td.get("eskom", {}).get("tariffs", {})
    if name in eskom_tariffs:
        t = eskom_tariffs[name]
        imp = _eskom_import_all_in(
            energy=t["energy_c_per_kwh"],
            levies=t["levies_c_per_kwh"],
            zones=t["zones"],
            voltages=t["voltages"],
        )
        exp = None
        if t.get("export_energy_c_per_kwh") and t.get("confirmed_base_export_c_per_kwh"):
            exp = _eskom_export_delta(
                export_energy=t["export_energy_c_per_kwh"],
                confirmed_base_export=t["confirmed_base_export_c_per_kwh"],
                default_zone=t["default_zone"],
                default_voltage=t["default_voltage"],
                zones=t["zones"],
                voltages=t["voltages"],
            )
        return {
            "type": "eskom",
            "zones": t["zones"],
            "voltages": t["voltages"],
            "default_zone": t["default_zone"],
            "default_voltage": t["default_voltage"],
            "import_c_per_kwh": imp,
            "export_c_per_kwh": exp,
            "capacity_r_kva_month": t["capacity_r_kva_month"],
            "generation_capacity_r_kva_month": t.get("generation_capacity_r_kva_month"),
            "network_capacity_r_kva_month": t.get("network_capacity_r_kva_month"),
            "service_charge_pa": t["service_charge_pa"],
            "service_charge_tiers": t.get("service_charge_tiers"),
            "demand_charge_kva": t.get("demand_charge_kva", 0.0),
            "tou_schedule": t.get("tou_schedule", "eskom"),
        }

    # ── Municipal / provider tariffs ─────────────────────────────────────────
    for _prov, pdata in td.get("providers", {}).items():
        if name in pdata.get("tariffs", {}):
            t = pdata["tariffs"][name]
            service_r_month = t.get("service_r_month", 0.0) or 0.0
            return {
                "type": "municipal",
                "import_c_per_kwh": t.get("energy_c_per_kwh"),
                "export_c_per_kwh": t.get("export_c_per_kwh"),
                "service_charge_pa": round(service_r_month * 12, 2),
                "capacity_charge_kva": t.get("capacity_r_kva_month", 0.0) or 0.0,
                "demand_charge_kva": t.get("demand_r_kva_month", 0.0) or 0.0,
                "sseg_options": t.get("sseg_options"),
                "tou_schedule": t.get("tou_schedule", "eskom"),
            }

    # Not found
    all_names = list(eskom_tariffs.keys()) + [
        n for p in td.get("providers", {}).values() for n in p.get("tariffs", {})
    ]
    raise KeyError(f"Unknown tariff {name!r}. Available: {sorted(all_names)}")


def _load_tariff_json(name: str) -> dict:
    """
    Resolve a tariff display name to a flat dict (latest version, cached per process).
    Raises KeyError if the tariff name is not found.
    """
    if name in _tariff_resolved_cache:
        return _tariff_resolved_cache[name]
    result = _resolve_from_flat_td(name, _get_tariff_data())
    _tariff_resolved_cache[name] = result
    return result


def _load_tariff_json_for_date(name: str, date: _dt.date) -> dict:
    """
    Resolve a tariff display name for a specific historical date (not cached).
    With schema_version 1 (single version), returns current rates regardless of date.
    With schema_version 2, selects the version active on date.
    """
    return _resolve_from_flat_td(name, _get_tariff_data(date))


@dataclass
class TariffRates:
    """TOU rates (R/kWh) and fixed charges for a tariff."""
    name: str
    hd_peak: float       # High Demand Peak (R/kWh)
    hd_standard: float   # High Demand Standard
    hd_off_peak: float   # High Demand Off-Peak
    ld_peak: float       # Low Demand Peak
    ld_standard: float   # Low Demand Standard
    ld_off_peak: float   # Low Demand Off-Peak
    export_hd_peak: Optional[float] = None
    export_hd_standard: Optional[float] = None
    export_hd_off_peak: Optional[float] = None
    export_ld_peak: Optional[float] = None
    export_ld_standard: Optional[float] = None
    export_ld_off_peak: Optional[float] = None
    service_charge_pa: float = 0.0      # R/year (NMD bracket for Eskom; flat for municipal)
    admin_charge_pa: float = 0.0        # R/year administration charge (Eskom NMD bracket; 0 otherwise)
    capacity_charge_kva: float = 0.0   # R/kVA/month (NMD) - combined generation + network
    generation_capacity_charge_kva: float = 0.0  # R/kVA/month (NMD) - generation component
    network_capacity_charge_kva: float = 0.0      # R/kVA/month (NMD) - network component
    demand_charge_kva: float = 0.0     # R/kVA/month (actual max demand)
    tou_schedule: str = "eskom"        # name of the TOU schedule (see tou.py)

    def rate(self, season: str, tou_period: int) -> float:
        """Return the import rate (R/kWh) for a given season and TOU period."""
        if season == "HI":
            return [None, self.hd_peak, self.hd_standard, self.hd_off_peak][tou_period]
        return [None, self.ld_peak, self.ld_standard, self.ld_off_peak][tou_period]

    def export_rate(self, season: str, tou_period: int) -> float:
        """Return the export/gen-offset rate (R/kWh), 0 if not available."""
        if season == "HI":
            rates = [None, self.export_hd_peak, self.export_hd_standard, self.export_hd_off_peak]
        else:
            rates = [None, self.export_ld_peak, self.export_ld_standard, self.export_ld_off_peak]
        r = rates[tou_period]
        return r if r is not None else 0.0


def _pick_service_tier(tiers: dict, nmd_kva: Optional[float], key_customer: bool) -> dict:
    """Select the service/admin charge tier for an NMD (kVA), or the key-customer
    category. Defaults to the smallest bracket when nmd_kva is None (matching the
    historical flat service_charge_pa)."""
    if key_customer and tiers.get("key_customer"):
        return tiers["key_customer"]
    brackets = tiers["nmd_brackets"]
    if nmd_kva is None:
        return brackets[0]
    for b in brackets:
        cap = b.get("max_kva")
        if cap is None or nmd_kva <= cap:
            return b
    return brackets[-1]


def _resolve_tariff_rates(
    name: str,
    data: dict,
    zone: Optional[str] = None,
    voltage: Optional[str] = None,
    sseg_option: Optional[str] = None,
    nmd_kva: Optional[float] = None,
    key_customer: bool = False,
) -> TariffRates:
    """Convert a pre-loaded tariff flat dict to a TariffRates object."""
    if data["type"] == "eskom":
        z = zone if (zone and zone in data["import_c_per_kwh"]) else data["default_zone"]
        v = voltage if (voltage and voltage in data["import_c_per_kwh"].get(z, {})) \
            else data["default_voltage"]
        imp = data["import_c_per_kwh"][z][v]
        exp_by_zone = data.get("export_c_per_kwh") or {}
        exp = exp_by_zone.get(z, {}).get(v)
        cap = data["capacity_r_kva_month"][z][v]
        gen_tbl = data.get("generation_capacity_r_kva_month")
        net_tbl = data.get("network_capacity_r_kva_month")
        if gen_tbl and net_tbl:
            gen_cap = gen_tbl[z][v]
            net_cap = net_tbl[z][v]
        else:
            # No split available: treat the whole capacity charge as network.
            gen_cap = 0.0
            net_cap = cap
    else:
        imp = data["import_c_per_kwh"]
        exp = data.get("export_c_per_kwh")
        cap = data.get("capacity_charge_kva", 0.0)
        # Municipal tariffs have no generation capacity charge.
        gen_cap = 0.0
        net_cap = cap

    # CoCT SSEG export override
    if sseg_option and "sseg_options" in data:
        sseg = data["sseg_options"].get(sseg_option)
        if sseg:
            if sseg.get("type") == "flat":
                rate = sseg["c_per_kwh"]
                exp = {
                    "HD": {"P": rate, "S": rate, "O": rate},
                    "LD": {"P": rate, "S": rate, "O": rate},
                }
            elif sseg.get("type") == "tou":
                exp = {"HD": sseg["HD"], "LD": sseg["LD"]}

    def c(x: Optional[float]) -> Optional[float]:
        return x / 100.0 if x is not None else None

    # Service + admin charge. Eskom flex tariffs carry an NMD bracket table;
    # everything else (incl. municipal) uses the flat service_charge_pa, no admin.
    tiers = data.get("service_charge_tiers")
    if tiers:
        tier = _pick_service_tier(tiers, nmd_kva, key_customer)
        service_pa = round(tier["service_r_per_pod_per_day"] * 365.0, 2)
        admin_pa = round(tier["admin_r_per_pod_per_day"] * 365.0, 2)
    else:
        service_pa = data.get("service_charge_pa", 0.0)
        admin_pa = 0.0

    return TariffRates(
        name=name,
        hd_peak         = c(imp["HD"]["P"]),
        hd_standard     = c(imp["HD"]["S"]),
        hd_off_peak     = c(imp["HD"]["O"]),
        ld_peak         = c(imp["LD"]["P"]),
        ld_standard     = c(imp["LD"]["S"]),
        ld_off_peak     = c(imp["LD"]["O"]),
        export_hd_peak      = c(exp["HD"]["P"]) if exp else None,
        export_hd_standard  = c(exp["HD"]["S"]) if exp else None,
        export_hd_off_peak  = c(exp["HD"]["O"]) if exp else None,
        export_ld_peak      = c(exp["LD"]["P"]) if exp else None,
        export_ld_standard  = c(exp["LD"]["S"]) if exp else None,
        export_ld_off_peak  = c(exp["LD"]["O"]) if exp else None,
        service_charge_pa   = service_pa,
        admin_charge_pa     = admin_pa,
        capacity_charge_kva = cap,
        generation_capacity_charge_kva = gen_cap,
        network_capacity_charge_kva    = net_cap,
        demand_charge_kva   = data.get("demand_charge_kva", 0.0),
        tou_schedule        = data.get("tou_schedule", "eskom"),
    )


def get_tariff_rates(
    tariff_name: str,
    zone: Optional[str] = None,
    voltage: Optional[str] = None,
    sseg_option: Optional[str] = None,
    nmd_kva: Optional[float] = None,
    key_customer: bool = False,
) -> TariffRates:
    """
    Return TOU rates and fixed charges for a named tariff (latest version).

    Parameters
    ----------
    tariff_name : str
        Display name, e.g. "Eskom Miniflex", "CoCT LV TOU".
    zone : str, optional
        Eskom transmission zone (e.g. ">900km"). Defaults to JSON default_zone.
    voltage : str, optional
        Eskom supply voltage (e.g. "<500V"). Defaults to JSON default_voltage.
    sseg_option : str, optional
        CoCT SSEG export option key (e.g. "SSEG Tariff 1", "SSEG TOU").
    nmd_kva : float, optional
        Notified Maximum Demand (kVA). For Eskom flex tariffs this selects the
        service + admin charge bracket; defaults to the smallest (<=100 kVA)
        bracket. Ignored for municipal tariffs (their service charge is flat).
    key_customer : bool
        Eskom "Key customer" category (overrides nmd_kva for service/admin).

    Raises
    ------
    KeyError if the tariff name is not found.
    """
    data = _load_tariff_json(tariff_name)
    return _resolve_tariff_rates(tariff_name, data, zone, voltage, sseg_option,
                                 nmd_kva, key_customer)


def list_tariffs() -> list[str]:
    """Return sorted list of available tariff names from tariff_data.json."""
    td = _get_tariff_data()
    names: list[str] = list(td.get("eskom", {}).get("tariffs", {}).keys())
    for pdata in td.get("providers", {}).values():
        names.extend(pdata.get("tariffs", {}).keys())
    return sorted(names)
