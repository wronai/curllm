"""
Browser helper for URL Resolver examples.

Provides a simple async browser setup using Playwright directly.
"""

from playwright.async_api import async_playwright


async def create_browser(headless: bool = True, stealth_mode: bool = True):
    """
    Create browser, context and page for examples.
    
    Args:
        headless: Run browser in headless mode
        stealth_mode: Apply basic stealth settings
        
    Returns:
        Tuple of (playwright, browser, context, page)
    """
    playwright = await async_playwright().start()
    
    browser = await playwright.chromium.launch(
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]
    )
    
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        locale="pl-PL",
    )
    
    if stealth_mode:
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['pl-PL', 'pl', 'en-US', 'en']});
        """)
    
    page = await context.new_page()
    
    return playwright, browser, context, page


async def close_browser(playwright, browser, context=None, page=None):
    """Close browser resources safely."""
    try:
        if page:
            await page.close()
        if context:
            await context.close()
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()
    except Exception:
        pass
