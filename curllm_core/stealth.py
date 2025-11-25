#!/usr/bin/env python3
from typing import List

class StealthConfig:
    """Anti-detection configuration"""
    def get_chrome_args(self) -> List[str]:
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
            '--user-agent=' + self.get_user_agent(),
        ]

    def get_user_agent(self) -> str:
        # Nowszy Chrome 131 (Ceneo sprawdza wersję)
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )

    async def apply_to_context(self, context):
        await context.add_init_script(
            """
            // Advanced anti-detection for Ceneo.pl
            
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
            
            // 3. Mock languages (Polish for Ceneo)
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
            
            // 10. Prevent automation detection via iframe
            Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
                get: function() {
                    return window;
                }
            });
            
            // 11. Mock battery (realistic)
            if (navigator.getBattery) {
                navigator.getBattery = () => Promise.resolve({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1,
                    addEventListener: () => {},
                    removeEventListener: () => {}
                });
            }
            
            // 12. Screen properties (realistic desktop)
            Object.defineProperty(screen, 'width', { get: () => 1920 });
            Object.defineProperty(screen, 'height', { get: () => 1080 });
            Object.defineProperty(screen, 'availWidth', { get: () => 1920 });
            Object.defineProperty(screen, 'availHeight', { get: () => 1040 });
            Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
            Object.defineProperty(screen, 'pixelDepth', { get: () => 24 });
            
            // 13. Remove Playwright/Puppeteer traces
            delete window.playwright;
            delete window.puppeteer;
            delete window.__playwright;
            delete window.__puppeteer;
            delete window.__webdriver_script_fn;
            delete window.__driver_evaluate;
            delete window.__webdriver_evaluate;
            delete window.__selenium_evaluate;
            delete window.__fxdriver_evaluate;
            delete window.__driver_unwrapped;
            delete window.__webdriver_unwrapped;
            delete window.__selenium_unwrapped;
            delete window.__fxdriver_unwrapped;
            delete window._Selenium_IDE_Recorder;
            delete window._selenium;
            delete window.callSelenium;
            delete window._WEBDRIVER_ELEM_CACHE;
            delete document.__webdriver_script_fn;
            delete document.__driver_evaluate;
            delete document.__webdriver_evaluate;
            delete document.__selenium_evaluate;
            delete document.__fxdriver_evaluate;
            delete document.__driver_unwrapped;
            delete document.__webdriver_unwrapped;
            delete document.__selenium_unwrapped;
            delete document.__fxdriver_unwrapped;
            
            console.log('[Stealth] Advanced anti-detection initialized for Ceneo.pl');
            """
        )
