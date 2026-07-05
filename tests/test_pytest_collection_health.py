"""Guards against pytest collection breaking for the whole repo.

2026-07-05 incident: `pytest --collect-only` failed before collecting a
single test, with `ModuleNotFoundError: No module named 'curlx'`.
`curlx_pkg/` is an independent sub-project with its own `pyproject.toml`
and `.venv` (its `curlx` package is only ever installed there); nothing
told the root pytest run to skip it, so its `tests/` directory got swept
into the root collection and failed to import. Root cause + fix documented
in `pyproject.toml`'s `[tool.pytest.ini_options] norecursedirs`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_root_collection_succeeds_without_import_errors():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"pytest --collect-only failed (rc={result.returncode}):\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "ModuleNotFoundError" not in result.stdout
    assert "error during collection" not in result.stdout.lower()


def test_curlx_pkg_excluded_from_root_collection():
    """curlx_pkg has its own venv/pyproject.toml -- it must be tested with
    its own interpreter (`cd curlx_pkg && .venv/bin/python -m pytest`), not
    swept into the root collection where its `curlx` import can't resolve.

    Other suites legitimately reference "curlx_pkg" by name (e.g. pricing's
    tests exercise cross-package behavior), so this checks for collected
    test IDs *rooted at* curlx_pkg/ rather than a blanket substring search.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    collected_from_curlx_pkg = [
        line for line in result.stdout.splitlines() if line.startswith("curlx_pkg/")
    ]
    assert collected_from_curlx_pkg == []
