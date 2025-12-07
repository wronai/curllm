#!/usr/bin/env python3
import os
import random
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta

from .browserless import BrowserlessContext

class SessionManager:
    def __init__(self, base_dir: Path = None):
        if base_dir is None:
            base = Path(os.getenv("CURLLM_WORKSPACE", "./workspace"))
            base_dir = base / "sessions"
        self.base_dir = base_dir
        # Ensure directory exists and is writable, otherwise fallback
        self._ensure_writable_base()

    def _ensure_writable_base(self):
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
                    test.unlink(missing_ok=True)  # type: ignore[arg-type]
                except Exception:
                    pass
                self.base_dir = cand
                return
            except Exception:
                continue
        # If all fail, keep original; writes may fail later but that's unrecoverable here

    def get_session_path(self, session_id: str) -> Path:
        return self.base_dir / f"{session_id}.json"

    def save_session_metadata(self, session_id: str, metadata: Dict):
        metadata["last_updated"] = datetime.now().isoformat()
        meta_path = self.base_dir / f"{session_id}.meta.json"
        try:
            with open(meta_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception:
            # Try fallback bases if write failed (e.g., permission denied)
            old = self.base_dir
            self._ensure_writable_base()
            if self.base_dir != old:
                meta_path = self.base_dir / f"{session_id}.meta.json"
                try:
                    with open(meta_path, 'w') as f:
                        json.dump(metadata, f, indent=2)
                except Exception:
                    pass

    def load_session_metadata(self, session_id: str) -> Optional[Dict]:
        meta_path = self.base_dir / f"{session_id}.meta.json"
        if meta_path.exists():
            with open(meta_path, 'r') as f:
                return json.load(f)
        return None

    def is_session_valid(self, session_id: str, max_age_hours: int = 24) -> bool:
        metadata = self.load_session_metadata(session_id)
        if not metadata:
            return False
        last_updated = datetime.fromisoformat(metadata["last_updated"])  # type: ignore[arg-type]
        age = datetime.now() - last_updated
        return age < timedelta(hours=max_age_hours)

async def setup_browser(
    use_browserless: bool,
    browserless_url: str,
    stealth_mode: bool,
    storage_key: Optional[str],
    headers: Optional[Dict[str, str]],
    stealth_config,
    config,
    proxy_config: Optional[Dict] = None,
    session_id: Optional[str] = None,
):
    if use_browserless:
        import websockets
        ws = await websockets.connect(browserless_url)
        return BrowserlessContext(ws)
    return await setup_playwright(
        stealth_mode,
        storage_key,
        headers,
        stealth_config,
        config,
        proxy_config,
        session_id,
    )

def _ensure_playwright_browsers():
    """Check if Playwright browsers are installed, auto-install if missing."""
    import subprocess
    import sys
    
    # Check if chromium exists by looking at expected path
    cache_dir = Path.home() / ".cache" / "ms-playwright"
    chromium_dirs = list(cache_dir.glob("chromium*")) if cache_dir.exists() else []
    
    needs_install = True
    for d in chromium_dirs:
        if (d / "chrome-linux" / "chrome").exists() or \
           (d / "chrome-linux" / "headless_shell").exists():
            needs_install = False
            break
    
    if needs_install:
        print("🔧 Playwright browsers not found. Installing automatically...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            if result.returncode == 0:
                print("✅ Playwright browsers installed successfully!")
            else:
                print(f"⚠️ Playwright install warning: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            print("⚠️ Playwright install timed out, continuing anyway...")
        except Exception as e:
            print(f"⚠️ Failed to auto-install Playwright: {e}")


async def setup_playwright(
    stealth_mode: bool,
    storage_key: Optional[str],
    headers: Optional[Dict[str, str]],
    stealth_config,
    config,
    proxy_config: Optional[Dict] = None,
    session_id: Optional[str] = None,
):
    from playwright.async_api import async_playwright
    
    # Auto-install browsers if missing
    _ensure_playwright_browsers()
    
    session_mgr = SessionManager()
    playwright = await async_playwright().start()
    launch_args = {
        "headless": bool(config.headless),
        "args": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
        ],
    }
    if stealth_mode:
        launch_args["args"].extend(stealth_config.get_chrome_args())
    if proxy_config:
        if isinstance(proxy_config, str):
            launch_args["proxy"] = {"server": proxy_config}
        elif isinstance(proxy_config, dict):
            proxy_settings: Dict[str, str] = {"server": str(proxy_config.get("server"))}
            if proxy_config.get("username"):
                proxy_settings["username"] = proxy_config.get("username", "")
                proxy_settings["password"] = proxy_config.get("password", "")
            if proxy_config.get("bypass"):
                proxy_settings["bypass"] = proxy_config.get("bypass", "")
            launch_args["proxy"] = proxy_settings
    elif config.proxy:
        launch_args["proxy"] = {"server": config.proxy}
    
    # Try to launch, with retry after auto-install on failure
    try:
        browser = await playwright.chromium.launch(**launch_args)
    except Exception as e:
        if "Executable doesn't exist" in str(e):
            print("🔧 Browser missing, forcing reinstall...")
            import subprocess
            import sys
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                capture_output=True,
                timeout=300
            )
            browser = await playwright.chromium.launch(**launch_args)
        else:
            raise

    storage_path = None
    if session_id:
        storage_path = session_mgr.get_session_path(session_id)
        if not storage_path.exists() and storage_key:
            old_storage = Path(f"./workspace/storage/{storage_key}.json")
            if old_storage.exists():
                storage_path = old_storage
    elif storage_key:
        storage_dir = Path(os.getenv("CURLLM_STORAGE_DIR", "./workspace/storage"))
        try:
            storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            try:
                sfb = Path(os.path.expanduser("~")) / ".cache" / "curllm" / "storage"
                sfb.mkdir(parents=True, exist_ok=True)
                storage_dir = sfb
            except Exception:
                try:
                    sfb2 = Path("/tmp/curllm/storage")
                    sfb2.mkdir(parents=True, exist_ok=True)
                    storage_dir = sfb2
                except Exception:
                    pass
        storage_path = storage_dir / f"{storage_key}.json"

    vw = 1366 + int(random.random() * 700)
    vh = 768 + int(random.random() * 400)
    extra_headers: Dict[str, str] = {
        "Accept-Language": f"{config.locale},en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    if headers:
        extra_headers.update(headers)
    user_agent = stealth_config.get_user_agent() if stealth_mode else (headers.get("User-Agent") if headers else None)
    context_args = {
        "viewport": {"width": vw, "height": vh},
        "user_agent": user_agent,
        "locale": config.locale,
        "timezone_id": config.timezone_id,
        "extra_http_headers": extra_headers,
        "accept_downloads": True,
        "ignore_https_errors": proxy_config is not None,
    }
    if storage_path and storage_path.exists():
        try:
            context_args["storage_state"] = str(storage_path)
            if session_id and session_mgr.is_session_valid(session_id):
                pass
        except Exception:
            pass
    context = await browser.new_context(**context_args)
    if stealth_mode:
        await stealth_config.apply_to_context(context)
    setattr(context, "_curllm_browser", browser)
    setattr(context, "_curllm_playwright", playwright)
    setattr(context, "_curllm_storage_path", str(storage_path) if storage_path else None)
    setattr(context, "_curllm_session_id", session_id)
    setattr(context, "_curllm_session_manager", session_mgr)
    return context
