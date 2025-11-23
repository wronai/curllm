#!/usr/bin/env python3
import os
import random
from pathlib import Path
from typing import Dict, Optional

from .browserless import BrowserlessContext

async def setup_browser(use_browserless: bool, browserless_url: str, stealth_mode: bool, storage_key: Optional[str], headers: Optional[Dict[str, str]], stealth_config, config):
    if use_browserless:
        import websockets  # lazy
        ws = await websockets.connect(browserless_url)
        return BrowserlessContext(ws)
    return await setup_playwright(stealth_mode, storage_key, headers, stealth_config, config)

async def setup_playwright(stealth_mode: bool, storage_key: Optional[str], headers: Optional[Dict[str, str]], stealth_config, config):
    from playwright.async_api import async_playwright  # lazy import
    playwright = await async_playwright().start()
    launch_args = {"headless": bool(config.headless), "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
    if stealth_mode:
        launch_args["args"].extend(stealth_config.get_chrome_args())
    if config.proxy:
        launch_args["proxy"] = {"server": config.proxy}
    browser = await playwright.chromium.launch(**launch_args)
    storage_path = None
    if storage_key:
        storage_dir = Path(os.getenv("CURLLM_STORAGE_DIR", "./workspace/storage"))
        try:
            storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            alt = Path("/tmp/curllm_workspace/storage")
            alt.mkdir(parents=True, exist_ok=True)
            storage_dir = alt
        storage_path = storage_dir / f"{storage_key}.json"
    vw = 1366 + int(random.random() * 700)
    vh = 768 + int(random.random() * 400)
    extra_headers: Dict[str, str] = {"Accept-Language": f"{config.locale},en;q=0.8"}
    if headers:
        extra_headers.update(headers)
    user_agent = stealth_config.get_user_agent() if stealth_mode else (headers.get("User-Agent") if headers else None)
    context_args = {
        "viewport": {"width": vw, "height": vh},
        "user_agent": user_agent,
        "locale": config.locale,
        "timezone_id": config.timezone_id,
        "extra_http_headers": extra_headers,
    }
    if storage_path and storage_path.exists():
        context_args["storage_state"] = str(storage_path)
    context = await browser.new_context(**context_args)
    if stealth_mode:
        await stealth_config.apply_to_context(context)
    setattr(context, "_curllm_browser", browser)
    setattr(context, "_curllm_playwright", playwright)
    if storage_path:
        setattr(context, "_curllm_storage_path", str(storage_path))
    return context
