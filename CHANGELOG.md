# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-11-23

- Dynamic ports persisted in `.env` for API and Ollama; CLI, Makefile, and install.sh keep them in sync.
- CLI fixes: argument parsing after function definitions; `--start-services`, `--status` working reliably.
- `.env.example` introduced; server and CLI load `.env` consistently.
- Docker Compose uses environment variables for ports.
- README updated with working examples; new docs at `docs/EXAMPLES.md`.
- Examples generator `tools/generate_examples.sh` added; creates `examples/<slug>/README.md` and `examples/curllm-*.sh`.
- Server: robust `Agent` instantiation compatible with `browser_use` versions; local fallback agent.
- Server: added Markdown RunLogger with step-by-step logs and LLM prompt/response; path returned in API responses.
- Server: fallback extraction (links/emails/basic context) when LLM chain yields no result.
- Server: fixed `Event loop is closed` by using a fresh asyncio loop per request and closing Playwright resources.
- Packaging: added `pyproject.toml`; Makefile `release/publish/publish-test` targets using Twine token from env.
- Misc: improved CLI payload handling (headers), better debug logs, server path resolution via symlink and Python import.

[1.0.0]: https://github.com/wronai/curllm/releases/tag/v1.0.0
