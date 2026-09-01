#!/usr/bin/env python3
"""
curllm MCP server — web research and browser automation tools for LLM agents.

Usage (from curllm repo root):
  pip install -e ".[mcp]"
  curllm-mcp
  python -m curllm_mcp.server
"""

from __future__ import annotations

import ipaddress
import json
import os
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from curllm_mcp.service import CurllmService

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def _enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in _TRUE_VALUES


def _require_execute() -> None:
    if not _enabled("CURLLM_MCP_ALLOW_EXECUTE"):
        raise PermissionError(
            "browser automation through MCP is disabled; set CURLLM_MCP_ALLOW_EXECUTE=1 to enable it"
        )


def _is_public_address(address: str) -> bool:
    try:
        return ipaddress.ip_address(address.split("%", 1)[0]).is_global
    except ValueError:
        return False


def _require_safe_url(text: str, url: str | None = None) -> None:
    target = CurllmService._extract_url(text, url)
    if target is None:
        return

    parsed = urlparse(target)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("curllm MCP accepts only absolute http(s) URLs")
    if parsed.username or parsed.password:
        raise PermissionError("credentials in curllm MCP URLs are not allowed")
    if _enabled("CURLLM_MCP_ALLOW_PRIVATE_NETWORK"):
        return

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise PermissionError(
            "private-network URLs are disabled; set CURLLM_MCP_ALLOW_PRIVATE_NETWORK=1 to enable them"
        )
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(hostname, parsed.port or 443)}
    except socket.gaierror as exc:
        raise ValueError(f"cannot resolve curllm MCP URL host: {hostname}") from exc
    if not addresses or any(not _is_public_address(address) for address in addresses):
        raise PermissionError(
            "private-network URLs are disabled; set CURLLM_MCP_ALLOW_PRIVATE_NETWORK=1 to enable them"
        )

try:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("curllm")
    _service = CurllmService()

    @mcp.tool()
    def curllm_interfaces() -> str:
        """List curllm integration surfaces (CLI, REST, MCP) and available tools."""
        return json.dumps(_service.interfaces_info(), indent=2, ensure_ascii=False)

    @mcp.tool()
    def curllm_health() -> str:
        """Check Ollama, curllm API, and configured model availability."""
        return json.dumps(_service.health(), indent=2, ensure_ascii=False)

    @mcp.tool()
    def curllm_list_models() -> str:
        """List Ollama models available to curllm."""
        return json.dumps(_service.list_models(), indent=2, ensure_ascii=False)

    @mcp.tool()
    def curllm_fetch_light(text: str, url: str | None = None) -> str:
        """Fast HTTP fetch: page title, summary and links (no Playwright/LLM)."""
        _require_safe_url(text, url)
        return json.dumps(_service.fetch_light(text, url=url), indent=2, ensure_ascii=False)

    @mcp.tool()
    def curllm_execute(
        instruction: str,
        url: str | None = None,
        visual_mode: bool = False,
        stealth_mode: bool = False,
        captcha_solver: bool = False,
        use_bql: bool = False,
        use_api: bool = False,
    ) -> str:
        """Run full curllm browser workflow (Playwright + local LLM) for any instruction."""
        _require_execute()
        _require_safe_url(instruction, url)
        return json.dumps(
            _service.execute(
                instruction,
                url=url,
                visual_mode=visual_mode,
                stealth_mode=stealth_mode,
                captcha_solver=captcha_solver,
                use_bql=use_bql,
                use_api=use_api,
            ),
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    @mcp.tool()
    def curllm_extract(
        url: str,
        instruction: str = "extract page title, summary, links and main data",
        stealth_mode: bool = False,
    ) -> str:
        """Extract structured data from a webpage using curllm LLM-DSL."""
        _require_execute()
        _require_safe_url(instruction, url)
        return json.dumps(
            _service.extract(url, instruction, stealth_mode=stealth_mode),
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    @mcp.tool()
    def curllm_fill_form(
        url: str,
        instruction: str,
        visual_mode: bool = False,
        captcha_solver: bool = False,
    ) -> str:
        """Fill and submit a web form from natural language (name, email, message, etc.)."""
        _require_execute()
        _require_safe_url(instruction, url)
        return json.dumps(
            _service.fill_form(
                url,
                instruction,
                visual_mode=visual_mode,
                captcha_solver=captcha_solver,
            ),
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    def main() -> None:
        mcp.run()

except ImportError:

    def main() -> None:
        print(
            "MCP SDK not installed. From curllm repo root run:\n"
            "  pip install -e '.[mcp]'\n"
            "Or use REST: curl -X POST $CURLLM_API_HOST/api/execute ...",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
