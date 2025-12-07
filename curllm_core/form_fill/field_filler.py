"""Robust field filling with multiple fallback strategies"""


async def robust_fill_field(page, selector: str, value: str) -> bool:
    """Robust field filling with multiple fallbacks and event triggering.
    
    Tries multiple strategies:
    1. page.fill (native Playwright)
    2. page.type (slower but more reliable)
    3. Direct DOM setValue via evaluate
    """
    try:
        # Attempt 1: page.fill (native Playwright)
        try:
            await page.fill(selector, value, timeout=3000)
            await _trigger_field_events(page, selector)
            return True
        except Exception:
            pass
        
        # Attempt 2: page.type (slower but more reliable for some fields)
        try:
            await page.evaluate(
                "(sel) => { const el = document.querySelector(sel); if (el) el.value = ''; }", 
                selector
            )
            await page.type(selector, value, delay=20, timeout=3000)
            await _trigger_field_events(page, selector)
            return True
        except Exception:
            pass
        
        # Attempt 3: Direct DOM setValue via evaluate
        try:
            await page.evaluate(
                """(args) => {
                  const el = document.querySelector(args.sel);
                  if (el) {
                    el.value = args.val;
                    el.dispatchEvent(new Event('input', {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                    el.blur();
                  }
                }""", 
                {"sel": selector, "val": value}
            )
            return True
        except Exception:
            pass
        
        return False
    except Exception:
        return False


async def _trigger_field_events(page, selector: str) -> None:
    """Trigger input/change/blur events on a field to activate client-side validation."""
    await page.evaluate(
        """(sel) => {
          const el = document.querySelector(sel);
          if (el) {
            el.dispatchEvent(new Event('input', {bubbles:true}));
            el.dispatchEvent(new Event('change', {bubbles:true}));
            el.blur();
          }
        }""", 
        selector
    )


async def check_checkbox(page, selector: str) -> bool:
    """Check a checkbox using multiple strategies."""
    try:
        await page.check(selector)
        return True
    except Exception:
        try:
            await page.click(selector)
            return True
        except Exception:
            return False
