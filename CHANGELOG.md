# Changelog

## [Unreleased]

### Fixed
- `pytest --collect-only` failed for the *entire* repo with
  `ModuleNotFoundError: No module named 'curlx'` before collecting a single
  test. `curlx_pkg/` is an independent sub-project with its own
  `pyproject.toml` and `.venv` (its `curlx` package is only ever installed
  there); nothing told the root pytest run to skip it, so `curlx_pkg/tests/`
  got swept into the root collection and failed to import `curlx`. Fixed by
  adding `norecursedirs = ["curlx_pkg", ".venv", "venv", "node_modules",
  "build", "dist"]` to `[tool.pytest.ini_options]` in `pyproject.toml`.
  `curlx_pkg`'s own tests still pass unchanged when run from within
  `curlx_pkg` with its own `.venv`. Verified: root collection now succeeds
  (445 tests, 0 errors); full non-e2e/non-playwright-integration suite
  passes (387 passed, 1 skipped) — the e2e/integration failures are
  pre-existing, unrelated network/browser-driver dependencies (confirmed to
  fail identically before this change). 2 new tests
  (`tests/test_pytest_collection_health.py`).

## [1.0.43] - 2026-07-05

### Docs
- Update CHANGELOG.md
- Update README.md

### Test
- Update tests/test_pytest_collection_health.py

### Other
- Update .gitignore
- Update .planfile/config.yaml
- Update .planfile/sprints/current.yaml
- Update project/planfile-tickets.yaml

## [1.0.42] - 2026-07-03

### Docs
- Update README.md

### Test
- Update tests/integration/conftest.py
- Update tests/integration/test_03_to_10.py

### Other
- Update project/planfile-tickets.yaml

## [1.0.41] - 2026-06-29

### Docs
- Update README.md

### Test
- Update tests/test_v2_imports.py

### Other
- Update curllm_mcp/testql_export.py
- Update uv.lock


All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.40] - 2026-02-24

### Changed
- Refactored core logic into `curllm_core` package
- Slimmed down `curllm_server.py` to thin shim
- Moved `bql_parser.py` into `curllm_core/bql.py`

### Fixed
- pyproject.toml: removed duplicate `license` field

## [1.0.0] - 2025-01-01

### Added
- Initial release of curllm
- Browser automation with local LLMs (Ollama)
- BQL (Browser Query Language) DSL
- Playwright integration for web scraping
- CAPTCHA detection support
- Visual scraping mode
- URL monitoring with cron support
