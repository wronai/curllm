"""Re-export canonical SessionManager; keep streamware browser setup helpers."""
from curllm_core.browser_setup import SessionManager

__all__ = ["SessionManager", "setup_browser", "create_context"]

from typing import Any, Dict

from .stealth import StealthConfig, apply_stealth


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
        browser = await playwright.chromium.connect_over_cdp(browserless_url)
    else:
        launch_args = []
        if stealth:
            launch_args = StealthConfig().get_chrome_args()

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
    """Create browser context with optional stealth scripts."""
    context_options: Dict[str, Any] = {}

    if viewport:
        context_options["viewport"] = viewport
    else:
        context_options["viewport"] = {"width": 1920, "height": 1080}

    if user_agent:
        context_options["user_agent"] = user_agent
    elif stealth:
        context_options["user_agent"] = StealthConfig().get_user_agent()

    if proxy:
        context_options["proxy"] = proxy

    context_options.update(kwargs)

    context = await browser.new_context(**context_options)

    if stealth:
        await apply_stealth(context)

    return context
