from __future__ import annotations

from pathlib import Path

REQUIRED_CODEOWNER_PATTERNS = {
    "*",
    "/.github/CODEOWNERS",
    "/.github/workflows/",
    "/docker/",
    "/pyproject.toml",
    "/requirements/",
    "/docs/BRANCH_PROTECTION.md",
    "/docs/RELEASE_GOVERNANCE.md",
    "/docs/RELEASE_SECURITY.md",
    "/docs/SECURITY_BASELINE.md",
    "/src/tuc/backends/",
    "/src/tuc/compiler/",
    "/src/tuc/frontend/",
    "/src/tuc/ir/",
    "/src/tuc/runtime/",
    "/src/tuc/manifests.py",
    "/examples/manifests/",
    "/tests/golden/",
    "/rfcs/",
}


def _codeowners_entries() -> dict[str, list[str]]:
    codeowners_path = Path(__file__).resolve().parents[1] / ".github" / "CODEOWNERS"
    entries: dict[str, list[str]] = {}
    for raw_line in codeowners_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        entries[parts[0]] = parts[1:]
    return entries


def test_codeowners_covers_security_critical_paths() -> None:
    entries = _codeowners_entries()

    assert entries.keys() >= REQUIRED_CODEOWNER_PATTERNS
    for pattern in REQUIRED_CODEOWNER_PATTERNS:
        assert entries[pattern] == ["@kirchherr"]


def test_codeowners_owns_itself() -> None:
    entries = _codeowners_entries()

    assert entries["/.github/CODEOWNERS"] == ["@kirchherr"]
