"""
Pre-flight release check for forest-tariff-engine.

Run this BEFORE bumping the version, committing, or tagging a release. It
enforces the rules that prevent version/tag drift (see RELEASING.md):

  1. pyproject.toml is the SINGLE SOURCE OF TRUTH for the version.
  2. The local branch must contain origin/main (never release from a stale
     checkout. This is what caused the v1.2.0/v1.2.1 confusion).
  3. The tag v{version} must NOT already exist (no collision / no re-use).
  4. The version must be valid semver (MAJOR.MINOR.PATCH).
  5. CHANGELOG.md must have an entry for the version, so consuming programs
     know what changed (never bump a version without update notes).

Usage:
    py scripts/check_release.py

Exit code 0 = safe to release. Non-zero = do not release; read the output.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True
    )


def get_version() -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not m:
        sys.exit(f"{RED}FAIL{RESET}  Could not find version in pyproject.toml")
    return m.group(1)


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []

    version = get_version()
    tag = f"v{version}"
    print(f"pyproject.toml version : {version}")
    print(f"expected release tag   : {tag}\n")

    # 1. Valid semver -------------------------------------------------------
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        failures.append(
            f"Version {version!r} is not valid MAJOR.MINOR.PATCH semver."
        )

    # 2. Fetch latest refs (best effort) -----------------------------------
    fetch = git("fetch", "origin", "--tags", "--quiet")
    if fetch.returncode != 0:
        warnings.append(
            "Could not 'git fetch origin' (offline?). Sync check may be stale:\n"
            f"    {fetch.stderr.strip()}"
        )

    # 3. Local branch must contain origin/main -----------------------------
    origin_main = git("rev-parse", "--verify", "origin/main")
    if origin_main.returncode != 0:
        warnings.append("No origin/main ref found; skipping sync check.")
    else:
        # origin/main must be an ancestor of (or equal to) HEAD.
        contains = git("merge-base", "--is-ancestor", "origin/main", "HEAD")
        if contains.returncode != 0:
            local = git("rev-parse", "--short", "HEAD").stdout.strip()
            remote = git("rev-parse", "--short", "origin/main").stdout.strip()
            failures.append(
                f"Local HEAD ({local}) is BEHIND or DIVERGED from origin/main "
                f"({remote}).\n"
                f"    Run: git fetch origin && git merge --ff-only origin/main\n"
                f"    Never release from a stale checkout."
            )

    # 4. Tag must not already exist (local or remote) ----------------------
    local_tag = git("tag", "--list", tag).stdout.strip()
    remote_tag = git("ls-remote", "--tags", "origin", tag).stdout.strip()
    if local_tag or remote_tag:
        where = []
        if local_tag:
            where.append("local")
        if remote_tag:
            where.append("origin")
        failures.append(
            f"Tag {tag} already exists ({', '.join(where)}).\n"
            f"    Bump the version in pyproject.toml. Never re-use a tag."
        )

    # 5. CHANGELOG.md must document this version ---------------------------
    if not CHANGELOG.exists():
        failures.append(
            "CHANGELOG.md is missing. Add update notes so consuming programs "
            "know what changed."
        )
    else:
        changelog_text = CHANGELOG.read_text(encoding="utf-8")
        if not re.search(rf"^##\s*\[{re.escape(version)}\]", changelog_text, re.MULTILINE):
            failures.append(
                f"CHANGELOG.md has no entry for {version}.\n"
                f"    Add a '## [{version}] - <YYYY-MM-DD>' section describing "
                f"what changed.\n"
                f"    Never bump a version without update notes."
            )

    # 6. Informational: uncommitted changes --------------------------------
    status = git("status", "--porcelain").stdout.strip()
    if status:
        warnings.append(
            "Working tree has uncommitted changes (fine if mid-release):\n"
            + "\n".join(f"    {line}" for line in status.splitlines())
        )

    # ── Report ────────────────────────────────────────────────────────────
    print("-" * 60)
    for w in warnings:
        print(f"{YELLOW}WARN{RESET}  {w}")
    for f in failures:
        print(f"{RED}FAIL{RESET}  {f}")

    if failures:
        print(f"\n{RED}NOT SAFE TO RELEASE{RESET}. Fix the FAIL items above.")
        return 1

    print(f"\n{GREEN}OK{RESET}  Safe to release {tag}.")
    print("Next: pytest  ->  py -m build  ->  commit  ->  "
          f"git tag -a {tag}  ->  git push origin main {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
