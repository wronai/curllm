#!/usr/bin/env python3
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

ProxyConfig = Union[str, Dict[str, Any], None]

STATE_DIR = Path(os.getenv("CURLLM_WORKSPACE", "./workspace")) / "proxy"
STATE_FILE = STATE_DIR / "rotation_state.json"
PUBLIC_FILE = STATE_DIR / "public_proxies.txt"


class ProxyStateManager:
    def __init__(self, state_file: Path = STATE_FILE):
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state: Dict[str, int] = {}
        try:
            if self.state_file.exists():
                self.state = json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            self.state = {}

    def next_index(self, key: str, size: int) -> int:
        if size <= 0:
            return 0
        idx = self.state.get(key, -1) + 1
        if idx >= size:
            idx = 0
        self.state[key] = idx
        try:
            self.state_file.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        except Exception:
            pass
        return idx


def _dict_to_playwright_proxy(d: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {"server": str(d.get("server"))}
    if d.get("username"):
        out["username"] = str(d.get("username", ""))
        out["password"] = str(d.get("password", ""))
    if d.get("bypass"):
        out["bypass"] = str(d.get("bypass", ""))
    return out


def _load_public_list() -> List[str]:
    # Priority: env var -> file in workspace -> none
    env = os.getenv("CURLLM_PUBLIC_PROXY_LIST", "").strip()
    items: List[str] = []
    if env:
        # env can be comma-separated or file://path
        if env.startswith("file://"):
            try:
                p = Path(env.replace("file://", ""))
                if p.exists():
                    items = [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
            except Exception:
                items = []
        else:
            items = [x.strip() for x in env.split(",") if x.strip()]
    if not items and PUBLIC_FILE.exists():
        try:
            items = [l.strip() for l in PUBLIC_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
        except Exception:
            items = []
    return items


def resolve_proxy(proxy_config: ProxyConfig, rotation_key: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Return a Playwright proxy dict or None.
    proxy_config supports:
      - string: "http://user:pass@host:port"
      - dict: {server, username?, password?, bypass?}
      - dict rotation: {rotate: true, list: ["http://...", ...], key?: "global"|"<custom>", strategy?: "round_robin"}
      - dict rotation from public: {rotate: "public"} (reads CURLLM_PUBLIC_PROXY_LIST or workspace/proxy/public_proxies.txt)
    rotation_key: used to persist per-target rotation; if None, uses "global".
    """
    if not proxy_config:
        return None

    # Simple string
    if isinstance(proxy_config, str):
        if proxy_config in ("public", "rotate:public"):
            lst = _load_public_list()
            if not lst:
                return None
            key = rotation_key or "global"
            mgr = ProxyStateManager()
            idx = mgr.next_index(f"public::{key}", len(lst))
            return {"server": lst[idx]}
        return {"server": proxy_config}

    # Dict config
    if isinstance(proxy_config, dict):
        if proxy_config.get("rotate"):
            # Public list rotation
            if isinstance(proxy_config.get("rotate"), str) and proxy_config.get("rotate") in ("public", "public_http", "public_https"):
                lst = _load_public_list()
                if not lst:
                    return None
                key = proxy_config.get("key") or rotation_key or "global"
                mgr = ProxyStateManager()
                idx = mgr.next_index(f"public::{key}", len(lst))
                return {"server": lst[idx]}
            # Provided list rotation
            raw_list = proxy_config.get("list") or []
            lst = [str(x) for x in raw_list if str(x).strip()]
            if not lst and proxy_config.get("file"):
                try:
                    p = Path(str(proxy_config.get("file")))
                    if p.exists():
                        lst = [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
                except Exception:
                    lst = []
            if not lst:
                return None
            key = proxy_config.get("key") or rotation_key or "global"
            mgr = ProxyStateManager()
            idx = mgr.next_index(f"list::{key}", len(lst))
            return {"server": lst[idx]}
        # Plain dict proxy
        if proxy_config.get("server"):
            return _dict_to_playwright_proxy(proxy_config)
    return None
