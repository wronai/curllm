"""
Proxy Management - Proxy configuration and rotation.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union


ProxyConfig = Union[str, Dict[str, Any], None]

# Default paths
STATE_DIR = Path(os.getenv("CURLLM_WORKSPACE", "./workspace")) / "proxy"
STATE_FILE = STATE_DIR / "rotation_state.json"


class ProxyStateManager:
    """
    Manage proxy rotation state.
    
    Persists rotation index for round-robin proxy selection.
    """
    
    def __init__(self, state_file: Path = STATE_FILE):
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state: Dict[str, int] = {}
        self._load_state()

    def _load_state(self):
        """Load state from file."""
        try:
            if self.state_file.exists():
                self.state = json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            self.state = {}

    def _save_state(self):
        """Save state to file."""
        try:
            self.state_file.write_text(
                json.dumps(self.state, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    def next_index(self, key: str, size: int) -> int:
        """Get next rotation index."""
        if size <= 0:
            return 0
        idx = self.state.get(key, -1) + 1
        if idx >= size:
            idx = 0
        self.state[key] = idx
        self._save_state()
        return idx


class ProxyManager:
    """
    Manage proxy configuration and rotation.
    
    Supports:
    - Single proxy
    - Proxy list with rotation
    - Environment-based configuration
    """
    
    def __init__(self, proxies: List[str] = None):
        """
        Initialize proxy manager.
        
        Args:
            proxies: List of proxy URLs (optional)
        """
        self.proxies = proxies or []
        self.state_manager = ProxyStateManager()
        
        # Load from environment if not provided
        if not self.proxies:
            env_proxy = os.getenv("CURLLM_PROXY")
            if env_proxy:
                self.proxies = [p.strip() for p in env_proxy.split(",")]
    
    def get_proxy(self, domain: str = None) -> Optional[Dict[str, str]]:
        """
        Get proxy configuration for domain.
        
        Args:
            domain: Target domain (used for rotation key)
            
        Returns:
            Playwright proxy config or None
        """
        if not self.proxies:
            return None
        
        key = domain or "default"
        idx = self.state_manager.next_index(key, len(self.proxies))
        proxy_url = self.proxies[idx]
        
        return parse_proxy_url(proxy_url)
    
    def add_proxy(self, proxy_url: str):
        """Add proxy to rotation list."""
        if proxy_url not in self.proxies:
            self.proxies.append(proxy_url)
    
    def remove_proxy(self, proxy_url: str):
        """Remove proxy from rotation list."""
        if proxy_url in self.proxies:
            self.proxies.remove(proxy_url)


def parse_proxy_url(proxy_url: str) -> Dict[str, str]:
    """
    Parse proxy URL to Playwright format.
    
    Formats supported:
    - http://host:port
    - http://user:pass@host:port
    - socks5://host:port
    
    Args:
        proxy_url: Proxy URL string
        
    Returns:
        Playwright proxy config dict
    """
    from urllib.parse import urlparse
    
    parsed = urlparse(proxy_url)
    
    result: Dict[str, str] = {
        "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port or 80}"
    }
    
    if parsed.username:
        result["username"] = parsed.username
        result["password"] = parsed.password or ""
    
    return result


def get_proxy_config(
    proxy: ProxyConfig = None,
    domain: str = None
) -> Optional[Dict[str, str]]:
    """
    Get proxy configuration.
    
    Args:
        proxy: Proxy config (string URL, dict, or None)
        domain: Target domain
        
    Returns:
        Playwright proxy config or None
    """
    if proxy is None:
        # Try environment
        env_proxy = os.getenv("CURLLM_PROXY")
        if env_proxy:
            return parse_proxy_url(env_proxy.split(",")[0])
        return None
    
    if isinstance(proxy, str):
        return parse_proxy_url(proxy)
    
    if isinstance(proxy, dict):
        # Already in Playwright format
        return {
            "server": str(proxy.get("server", "")),
            "username": str(proxy.get("username", "")),
            "password": str(proxy.get("password", "")),
        }
    
    return None
