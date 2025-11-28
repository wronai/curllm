"""
Stealth Mode - Anti-detection for browser automation.
"""
from typing import List


class StealthConfig:
    """
    Anti-detection configuration for Playwright/Chromium.
    
    Bypasses common bot detection:
    - WebDriver flag
    - Navigator properties
    - Chrome runtime
    - Plugin/language fingerprints
    """
    
    def get_chrome_args(self) -> List[str]:
        """Get Chrome launch arguments for stealth."""
        return [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-setuid-sandbox',
            '--no-first-run',
            '--no-default-browser-check',
            '--window-size=1920,1080',
            '--start-maximized',
            f'--user-agent={self.get_user_agent()}',
        ]

    def get_user_agent(self) -> str:
        """Get realistic user agent string."""
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )

    async def apply_to_context(self, context):
        """Apply stealth scripts to browser context."""
        await apply_stealth(context)


# Stealth JavaScript to inject
STEALTH_SCRIPT = """
// Advanced anti-detection

// 1. Remove webdriver flag
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
delete navigator.__proto__.webdriver;

// 2. Mock plugins (realistic)
Object.defineProperty(navigator, 'plugins', { 
    get: () => [
        {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
        {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: ''},
        {name: 'Native Client', filename: 'internal-nacl-plugin', description: ''}
    ] 
});
Object.defineProperty(navigator.plugins, 'length', { get: () => 3 });

// 3. Mock languages
Object.defineProperty(navigator, 'languages', { get: () => ['pl-PL', 'pl', 'en-US', 'en'] });
Object.defineProperty(navigator, 'language', { get: () => 'pl-PL' });

// 4. Override chrome runtime
window.chrome = { 
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};

// 5. Mock permissions
const originalQuery = window.navigator.permissions?.query;
if (originalQuery) {
    window.navigator.permissions.query = (parameters) => (
      parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters)
    );
}

// 6. Override toString to hide proxy
const originalToString = Function.prototype.toString;
Function.prototype.toString = function() {
    if (this === navigator.permissions.query) {
        return 'function query() { [native code] }';
    }
    return originalToString.call(this);
};

// 7. Mock hardware concurrency
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });

// 8. Mock device memory
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });

// 9. Mock connection
Object.defineProperty(navigator, 'connection', {
    get: () => ({
        effectiveType: '4g',
        rtt: 50,
        downlink: 10,
        saveData: false
    })
});

// 10. Mock screen properties
Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
Object.defineProperty(screen, 'pixelDepth', { get: () => 24 });

// 11. WebGL fingerprint randomization
const getParameterOrig = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameterOrig.call(this, parameter);
};

// 12. Canvas fingerprint noise
const toDataURLOrig = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {
    if (type === 'image/png' && this.width > 16 && this.height > 16) {
        const ctx = this.getContext('2d');
        if (ctx) {
            const imgData = ctx.getImageData(0, 0, this.width, this.height);
            for (let i = 0; i < imgData.data.length; i += 4) {
                imgData.data[i] ^= (Math.random() * 2) | 0;
            }
            ctx.putImageData(imgData, 0, 0);
        }
    }
    return toDataURLOrig.apply(this, arguments);
};
"""


async def apply_stealth(context) -> None:
    """
    Apply stealth scripts to browser context.
    
    Args:
        context: Playwright browser context
    """
    await context.add_init_script(STEALTH_SCRIPT)


def get_stealth_headers() -> dict:
    """Get stealth HTTP headers."""
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
