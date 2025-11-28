import socket
import ssl
from typing import Any, Dict
from urllib.parse import urlparse
import requests
import logging
import os


_LOGGER_CACHE: Dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger.

    Respects CURLLM_DEBUG env var to set DEBUG/INFO level.
    Ensures we don't duplicate handlers across multiple imports.
    """
    lg = _LOGGER_CACHE.get(name)
    if lg:
        return lg
    lg = logging.getLogger(name)
    # Configure only if not configured yet
    if not lg.handlers:
        level = logging.DEBUG if str(os.getenv("CURLLM_DEBUG", "false")).lower() == "true" else logging.INFO
        lg.setLevel(level)
        handler = logging.StreamHandler()
        handler.setLevel(level)
        fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(fmt)
        lg.addHandler(handler)
        try:
            lg.propagate = False
        except Exception:
            pass
    _LOGGER_CACHE[name] = lg
    return lg


def diagnose_url_issue(url: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {"url": url}
    try:
        pr = urlparse(url)
        host = pr.hostname or ""
        scheme = pr.scheme or ""
        out["host"] = host
        out["scheme"] = scheme
        # DNS resolution
        try:
            infos = socket.getaddrinfo(host, None)
            ips = []
            for i in infos:
                ip = i[4][0]
                if ip not in ips:
                    ips.append(ip)
            out["dns_resolves"] = True
            out["ips"] = ips
        except Exception as e:
            out["dns_resolves"] = False
            out["dns_error"] = str(e)
            return out

        # TCP connectivity
        def _tcp(port: int) -> bool:
            try:
                with socket.create_connection((host, port), timeout=5):
                    return True
            except Exception:
                return False

        out["tcp_443_open"] = _tcp(443)
        out["tcp_80_open"] = _tcp(80)

        # HTTPS handshake
        https_info: Dict[str, Any] = {}
        if out["tcp_443_open"]:
            try:
                ctx = ssl.create_default_context()
                with socket.create_connection((host, 443), timeout=5) as sock:
                    with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                        cert = ssock.getpeercert()
                        https_info["handshake_ok"] = True
                        try:
                            https_info["cert_subject"] = cert.get("subject")
                        except Exception:
                            pass
            except Exception as e:
                https_info["handshake_ok"] = False
                https_info["ssl_error"] = str(e)
        out["https"] = https_info

        # HTTP probe
        http_url = f"http://{host}/"
        try:
            r = requests.get(http_url, timeout=6, allow_redirects=True)
            out["http_probe"] = {"url": http_url, "status": getattr(r, "status_code", None)}
        except Exception as e:
            out["http_probe"] = {"url": http_url, "error": str(e)}

        # HTTPS probe
        if scheme == "https":
            try:
                r2 = requests.get(url, timeout=6, allow_redirects=True)
                out["https_probe"] = {"status": getattr(r2, "status_code", None)}
            except requests.exceptions.SSLError as e:
                out["https_probe"] = {"ssl_error": str(e)}
            except Exception as e:
                out["https_probe"] = {"error": str(e)}
    except Exception as e:
        out["diagnostic_error"] = str(e)
    return out
