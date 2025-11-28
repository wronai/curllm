"""
Browser Setup - Browser and context creation.
"""
import os
import json
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timedelta


class SessionManager:
    """
    Manage browser sessions with persistence.
    
    Sessions are stored as JSON files with metadata.
    """
    
    def __init__(self, base_dir: Path = None):
        if base_dir is None:
            base = Path(os.getenv("CURLLM_WORKSPACE", "./workspace"))
            base_dir = base / "sessions"
        self.base_dir = base_dir
        self._ensure_writable_base()

    def _ensure_writable_base(self):
        """Find a writable directory for sessions."""
        candidates = [
            self.base_dir,
            Path(os.path.expanduser("~")) / ".cache" / "curllm" / "sessions",
            Path("/tmp/curllm/sessions"),
        ]
        for cand in candidates:
            try:
                cand.mkdir(parents=True, exist_ok=True)
                test = cand / ".writetest"
                with open(test, "w") as f:
                    f.write("ok")
                try:
                    test.unlink(missing_ok=True)
                except Exception:
                    pass
                self.base_dir = cand
                return
            except Exception:
                continue

    def get_session_path(self, session_id: str) -> Path:
        """Get path for session storage."""
        return self.base_dir / f"{session_id}.json"

    def save_session_metadata(self, session_id: str, metadata: Dict):
        """Save session metadata."""
        metadata["last_updated"] = datetime.now().isoformat()
        meta_path = self.base_dir / f"{session_id}.meta.json"
        try:
            with open(meta_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception:
            self._ensure_writable_base()
            meta_path = self.base_dir / f"{session_id}.meta.json"
            try:
                with open(meta_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
            except Exception:
                pass

    def load_session_metadata(self, session_id: str) -> Optional[Dict]:
        """Load session metadata."""
        meta_path = self.base_dir / f"{session_id}.meta.json"
        if meta_path.exists():
            with open(meta_path, 'r') as f:
                return json.load(f)
        return None

    def is_session_valid(self, session_id: str, max_age_hours: int = 24) -> bool:
        """Check if session is still valid."""
        metadata = self.load_session_metadata(session_id)
        if not metadata:
            return False
        last_updated = datetime.fromisoformat(metadata["last_updated"])
        age = datetime.now() - last_updated
        return age < timedelta(hours=max_age_hours)


async def setup_browser(
    use_browserless: bool = False,
    browserless_url: str = None,
    headless: bool = True,
    stealth: bool = True,
    proxy: Dict = None,
    user_data_dir: str = None,
    **kwargs
) -> Any:
    """
    Set up browser with Playwright.
    
    Args:
        use_browserless: Use browserless.io service
        browserless_url: Browserless WebSocket URL
        headless: Run headless
        stealth: Apply stealth mode
        proxy: Proxy configuration
        user_data_dir: User data directory for persistence
        **kwargs: Additional browser options
        
    Returns:
        Playwright browser instance
    """
    from playwright.async_api import async_playwright
    
    playwright = await async_playwright().start()
    
    if use_browserless and browserless_url:
        # Connect to browserless
        browser = await playwright.chromium.connect_over_cdp(browserless_url)
    else:
        # Local browser
        from .stealth import StealthConfig
        
        launch_args = []
        if stealth:
            config = StealthConfig()
            launch_args = config.get_chrome_args()
        
        browser = await playwright.chromium.launch(
            headless=headless,
            args=launch_args,
            **kwargs
        )
    
    return browser


async def create_context(
    browser,
    stealth: bool = True,
    proxy: Dict = None,
    viewport: Dict = None,
    user_agent: str = None,
    **kwargs
) -> Any:
    """
    Create browser context with options.
    
    Args:
        browser: Playwright browser instance
        stealth: Apply stealth scripts
        proxy: Proxy configuration
        viewport: Viewport size {width, height}
        user_agent: Custom user agent
        **kwargs: Additional context options
        
    Returns:
        Browser context
    """
    context_options = {}
    
    if viewport:
        context_options["viewport"] = viewport
    else:
        context_options["viewport"] = {"width": 1920, "height": 1080}
    
    if user_agent:
        context_options["user_agent"] = user_agent
    elif stealth:
        from .stealth import StealthConfig
        context_options["user_agent"] = StealthConfig().get_user_agent()
    
    if proxy:
        context_options["proxy"] = proxy
    
    context_options.update(kwargs)
    
    context = await browser.new_context(**context_options)
    
    if stealth:
        from .stealth import apply_stealth
        await apply_stealth(context)
    
    return context
