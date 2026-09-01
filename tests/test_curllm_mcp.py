"""Tests for curllm_mcp service layer (no Playwright)."""

import socket

import pytest

from curllm_mcp.service import CurllmService


def test_interfaces_info():
    info = CurllmService().interfaces_info()
    assert info["name"] == "curllm"
    assert "curllm-mcp" in info["mcp_entrypoint"]
    assert "curllm_execute" in info["mcp_tools"]


def test_fetch_light_example_com():
    svc = CurllmService()
    result = svc.fetch_light("check https://example.com")
    assert result["success"] is True
    assert result["url"] == "https://example.com"
    assert "Example" in (result.get("title") or result.get("summary") or "")


def test_fetch_light_missing_url():
    result = CurllmService().fetch_light("no url here")
    assert result["success"] is False
    assert "URL" in result["error"]


def test_extract_url_helper():
    assert CurllmService._extract_url("visit https://foo.bar/page", None) == "https://foo.bar/page"
    assert CurllmService._extract_url("text", "https://x.test") == "https://x.test"


def test_mcp_browser_automation_is_disabled_by_default(monkeypatch: pytest.MonkeyPatch):
    from curllm_mcp.server import _require_execute

    monkeypatch.delenv("CURLLM_MCP_ALLOW_EXECUTE", raising=False)
    with pytest.raises(PermissionError, match="CURLLM_MCP_ALLOW_EXECUTE"):
        _require_execute()
    monkeypatch.setenv("CURLLM_MCP_ALLOW_EXECUTE", "yes")
    _require_execute()


def test_mcp_rejects_private_and_credential_urls(monkeypatch: pytest.MonkeyPatch):
    from curllm_mcp.server import _require_safe_url

    monkeypatch.delenv("CURLLM_MCP_ALLOW_PRIVATE_NETWORK", raising=False)
    with pytest.raises(PermissionError, match="private-network"):
        _require_safe_url("open http://127.0.0.1/admin")
    with pytest.raises(PermissionError, match="credentials"):
        _require_safe_url("open https://user:secret@example.com")


def test_mcp_allows_public_url_and_private_opt_in(monkeypatch: pytest.MonkeyPatch):
    from curllm_mcp.server import _require_safe_url

    def public_dns(*_args):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]

    monkeypatch.delenv("CURLLM_MCP_ALLOW_PRIVATE_NETWORK", raising=False)
    monkeypatch.setattr(socket, "getaddrinfo", public_dns)
    _require_safe_url("open https://example.com")

    monkeypatch.setenv("CURLLM_MCP_ALLOW_PRIVATE_NETWORK", "1")
    _require_safe_url("open http://localhost:8080")
