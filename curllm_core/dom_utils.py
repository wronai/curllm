async def detect_honeypot(page) -> bool:
    honeypots = await page.evaluate(
        """
        () => {
            const suspicious = [];
            const inputs = document.querySelectorAll('input, textarea');
            inputs.forEach(input => {
                const style = window.getComputedStyle(input);
                if (style.display === 'none' || 
                    style.visibility === 'hidden' ||
                    input.type === 'hidden' ||
                    style.opacity === '0' ||
                    input.offsetHeight === 0) {
                    suspicious.push(input.name || input.id);
                }
            });
            return suspicious.length > 0;
        }
        """
    )
    return bool(honeypots)
