# Releasing the Tariff Engine

This document exists to prevent version/tag drift. In May 2026 a release was
nearly cut from a stale local checkout, which would have collided with an
existing `v1.2.0` tag and silently dropped released tariff data. The rules
below stop that from happening again.

## The one rule: a single source of truth

**`pyproject.toml` `version` is the ONLY place the version is authored.**

Everything else is either derived from it or must match it exactly:

| Where version appears | Status | Rule |
|-----------------------|--------|------|
| `pyproject.toml` `version` | **Source of truth** | The only value you edit by hand |
| Git tag `v{version}` | Must match exactly | Created at release, never re-used or moved |
| `forest_tariff_engine.egg-info/PKG-INFO` | Derived build output | Never edit; never trust as the version |
| `dist/*.whl`, `dist/*.tar.gz` | Derived build output | Rebuilt every release; delete stale versions |

If you ever see these disagree, `pyproject.toml` wins. Rebuild the artifacts;
do not hand-edit egg-info or dist.

## Before you start: never release from a stale checkout

The single biggest risk. The local branch can be behind `origin/main` even
when it looks fine. **Always sync first:**

```bash
git fetch origin --tags
git merge --ff-only origin/main   # fails loudly if you have diverged
```

If `--ff-only` fails, stop and reconcile before doing anything else.

## Release procedure

1. **Sync** (see above). Local must contain `origin/main`.

2. **Make the change.** Edit `tariff_engine/tariff_data.json` (directly or via
   a `scripts/update_*.py` helper).

3. **Bump the version** in `pyproject.toml` using semver:

   | Change | Bump | Example |
   |--------|------|---------|
   | Fix or add export/data to **existing** tariffs | PATCH | 1.2.0 -> 1.2.1 |
   | **New** tariffs, providers, or corrected published rates | MINOR | 1.2.1 -> 1.3.0 |
   | Schema change or breaking API change | MAJOR | 1.x -> 2.0.0 |

4. **Add update notes.** Add a new entry to [CHANGELOG.md](CHANGELOG.md) under a
   `## [<version>] - <YYYY-MM-DD>` heading describing what changed (Added /
   Changed / Fixed). This is how consuming programs (Solar Model, Dashboard)
   know what each version pin brings. Never bump a version without it.

5. **Pre-flight check.** This enforces sync, semver, and tag-collision rules:

   ```bash
   py scripts/check_release.py
   ```

   Do not proceed unless it prints `OK  Safe to release`.

6. **Test:**

   ```bash
   py -m pytest -q
   ```

7. **Build** (regenerates dist + egg-info at the new version; clear stale ones):

   ```bash
   py -m build
   ```

8. **Commit, tag (matching pyproject exactly), push:**

   ```bash
   git commit -am "tariffs: <summary> (v<version>)"
   git tag -a v<version> -m "v<version> - <summary>"
   git push origin main
   git push origin v<version>
   ```

9. **Bump downstream consumers.** Update the pin in `requirements.txt` of the
   Solar Model and Solar Dashboard repos from the old `@v<old>` to `@v<new>`.

## Quick reference

```bash
git fetch origin --tags && git merge --ff-only origin/main
# ...make change, bump pyproject.toml version, add CHANGELOG.md entry...
py scripts/check_release.py && py -m pytest -q && py -m build
git commit -am "tariffs: ... (v1.2.x)"
git tag -a v1.2.x -m "v1.2.x - ..."
git push origin main && git push origin v1.2.x
```
