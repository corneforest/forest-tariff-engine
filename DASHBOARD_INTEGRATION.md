# Dashboard Migration Guide

How to migrate **Forest Energy Solar Dashboard** from its bundled `tariff_engine/` folder to the shared `forest-tariff-engine` package on GitHub.

This is the same migration that Solar Model went through on 2026-05-10 (commit `f266aee` in solar-model). You can hand this document to Claude inside the Dashboard project and ask it to follow the steps.

---

## Goal

| Before | After |
|--------|-------|
| Dashboard repo contains a local `tariff_engine/` folder with `tou.py`, `rates.py`, `history.py`, `savings.py`, `tariff_data.json` | Dashboard installs the package via pip from `github.com/corneforest/forest-tariff-engine` |
| Tariff updates require running `sync_to_dashboard.py` from Solar Model and committing the changes in two repos | Tariff updates happen once in `forest-tariff-engine`. Dashboard just bumps the version pin |
| Dashboard's `tariff_engine/` can drift from Solar Model's | Both apps use the exact same pinned version |

The Python imports inside Dashboard code do **not** change. Everything still imports from `tariff_engine.X`.

---

## Prerequisites

Before starting, confirm:

1. The Dashboard's `tariff_engine/` folder has the same files as Solar Model's snapshot (no Dashboard-only customisations). Run a diff if unsure.
2. You have the Dashboard repo cloned locally at, e.g., `C:\Users\CorneGroenewald\Documents\Solar Dashboard\`.
3. Your Dashboard Railway deploy currently works.
4. You can pip-install from a public GitHub URL (no firewall blocking, etc).

If the Dashboard's `tariff_engine/` does have local edits, **stop** and document them first. They need to be ported into the `forest-tariff-engine` repo before this migration begins.

---

## Step-by-step

### 1. Pre-flight: snapshot the current state

Inside the Dashboard repo:

```bash
mkdir -p "_archive/pre_tariff_engine_extraction_2026-MM-DD"
cp -r tariff_engine "_archive/pre_tariff_engine_extraction_2026-MM-DD/tariff_engine_snapshot"
```

This is belt-and-braces. Git history already has it, but a visible snapshot folder makes rollback easier.

### 2. Add the package to `requirements.txt`

Append this line:

```
forest-tariff-engine @ git+https://github.com/corneforest/forest-tariff-engine.git@v1.0.0
```

Pin to a tag (`@v1.0.0`), not `@main`. This guarantees the Dashboard never breaks because of a tariff-side change you haven't tested.

### 3. Install the package locally

```bash
py -m pip install "forest-tariff-engine @ git+https://github.com/corneforest/forest-tariff-engine.git@v1.0.0"
```

Confirm imports work:

```bash
py -c "
from tariff_engine.tou import get_tou_period, build_hourly_tou
from tariff_engine.rates import get_tariff_rates, list_tariffs, TariffRates
from tariff_engine.history import get_tariff_rates_for_date
from tariff_engine.savings import calculate_hourly_savings
print('OK', len(list_tariffs()), 'tariffs')
"
```

Expected output: `OK 81 tariffs` (or whatever the latest count is).

### 4. Delete the old folder

```bash
git rm -r tariff_engine/
```

If a `sync_to_dashboard.py` or similar sync helper exists in the Dashboard root, delete that too:

```bash
git rm sync_to_dashboard.py    # if present
```

### 5. Run the Dashboard test suite

```bash
py -m pytest -v
```

All tests that previously passed should still pass. The imports `from tariff_engine.X import Y` resolve to the installed package now instead of the local folder, but the API is identical.

If any test fails, read the error carefully. The two likely causes:

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: No module named 'tariff_engine'` | `pip install` didn't take, or you're in the wrong venv | Re-run step 3 |
| `KeyError: 'Some Tariff Name'` | The tariff was renamed or removed in the new package | Check `forest-tariff-engine`'s `tariff_data.json` for the current name |

### 6. Smoke-test the Dashboard locally

Start the Dashboard server and click through the parts that touch tariffs:

| Feature | What to verify |
|---------|---------------|
| Bill comparison | A historical bill calculates the same total as before |
| TOU classification | Hourly data shows the right Peak/Std/Off classification |
| Savings calculation | Hourly ZAR savings match what Dashboard produced before |
| Tariff dropdowns | All tariff names load |

Compare a known-good bill (one you've previously verified) against the same bill calculated after the migration. The numbers must match to the cent.

### 7. Commit

```bash
git add requirements.txt
git rm -r tariff_engine/
git add _archive/
git commit -m "tariff_engine: extract to standalone forest-tariff-engine package

Removes the local tariff_engine/ copy and pulls it from the shared
forest-tariff-engine repo instead. Single source of truth for all
tariff data and TOU logic across Solar Model and Dashboard.

- requirements.txt: adds forest-tariff-engine @ github.com/corneforest/forest-tariff-engine@v1.0.0
- tariff_engine/: deleted (now installed as a package)
- All imports unchanged (still 'from tariff_engine.X import Y')
- Tested: full suite passing after change"
```

### 8. Push to Railway

```bash
git push origin master    # or main, whichever Dashboard uses
```

Railway will rebuild. Watch the Railway build logs:

| Log line | Meaning |
|----------|---------|
| `Cloning https://github.com/corneforest/forest-tariff-engine.git` | Pip is fetching the package, good |
| `Successfully installed forest-tariff-engine-1.0.0` | Install worked |
| `ImportError: No module named 'tariff_engine'` | Fail, package install failed earlier in build |
| Boot succeeds, `/health` returns 200 | Done |

After the deploy, hit one or two pages in production that exercise the engine and confirm output is identical.

---

## Public API reference

Everything below is callable as `from tariff_engine import X` (or via the submodule path, `from tariff_engine.rates import X`).

| Function | Purpose | Used by |
|----------|---------|---------|
| `get_tou_period(month, hour, weekday_iso, is_holiday) -> (season, tou_period)` | Classify a single hour | both |
| `build_hourly_tou(year) -> dict` | Build 8760-hour TOU arrays | both |
| `get_tariff_rates(name, zone=None, voltage=None, sseg_option=None) -> TariffRates` | Latest rates for a tariff | both |
| `get_tariff_rates_for_date(name, date, zone=None, voltage=None) -> TariffRates` | Rates active on a specific past date | Dashboard |
| `calculate_hourly_savings(...)` | Hourly ZAR savings from plant data | Dashboard |
| `list_tariffs() -> list[str]` | All available tariff names | both |
| `TariffRates` (dataclass) | Container with `hd_peak`, `ld_off_peak`, `service_charge_pa`, etc. | both |

Schema versioning lives in `rates.py`. Currently on `schema_version 2` which supports historical lookups.

---

## Tariff update workflow (after migration)

When Eskom or a municipality publishes new rates:

1. Edit `tariff_engine/tariff_data.json` in the **forest-tariff-engine** repo (not in Dashboard).
2. Run tests in that repo: `pytest`.
3. Commit, tag, push:
   ```bash
   git commit -am "tariffs: 2026/27 Eskom rates effective 2026-04-01"
   git tag v1.1.0
   git push --tags origin main
   ```
4. In **Dashboard's** `requirements.txt`, change `@v1.0.0` to `@v1.1.0`.
5. Push Dashboard to master. Railway redeploys with new tariffs.
6. Repeat step 4-5 in **Solar Model**.

The version-pin model means each app deploys exactly when **you** decide to bump, not whenever the source of truth changes.

---

## Rollback

If something breaks after deploy and you need the old behaviour back fast:

```bash
git revert HEAD              # reverts the migration commit
git push origin master       # Railway redeploys old code
```

Because the snapshot in `_archive/` is in git history, you can also restore the folder manually:

```bash
git checkout HEAD~1 -- tariff_engine/
```

This is why we kept the snapshot — instant restore, no need to track down which commit removed it.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| Railway build hangs at `Cloning forest-tariff-engine` | Network issue or repo private | Confirm the repo is public, or add a deploy token |
| Local `pip install` fails with `git: not found` | Git not on PATH in the venv's environment | Install git, or use the absolute path to git |
| `ImportError: cannot import name 'X' from 'tariff_engine'` | The function exists in the bundled copy but not in v1.0.0 | Check `forest-tariff-engine`'s `__init__.py` `__all__` list. If the function is genuinely missing, port it into the repo |
| Numbers differ slightly after migration | Data file has changed since last sync | Diff the old snapshot's `tariff_data.json` against the installed one to find the cell that changed |

---

## Reference: how Solar Model did it

For comparison, here is the exact Solar Model migration commit that you can read on GitHub:

[corneforest/solar-model commit f266aee](https://github.com/corneforest/solar-model/commit/f266aee)

The diff is small. Most of the file changes are deletions of `tariff_engine/` files plus the `requirements.txt` one-liner.

---

## Questions before you start

If anything below is unclear in your Dashboard repo, **stop and ask**:

- Does the Dashboard have any `tariff_engine/` modifications that don't exist in Solar Model? (run a diff)
- Does the Dashboard import anything from `tariff_engine` that isn't in the public API listed above?
- Does Dashboard's CI/CD do anything custom that might depend on `tariff_engine/` being a folder rather than an installed package?

If all three are "no", this migration is mechanical and safe.
