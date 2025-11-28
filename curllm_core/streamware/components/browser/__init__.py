"""
Browser Component - Browser setup and management.

Features:
- Browser/context creation
- Stealth mode (anti-detection)
- Proxy configuration
- Session management
"""

from .setup import setup_browser, SessionManager, create_context
from .stealth import StealthConfig, apply_stealth
from .proxy import ProxyManager, get_proxy_config

__all__ = [
    'setup_browser',
    'SessionManager',
    'create_context',
    'StealthConfig',
    'apply_stealth',
    'ProxyManager',
    'get_proxy_config'
]
