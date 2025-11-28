"""
Playwright + BQL framework (Python, synchronous Playwright)

File: playwright_bql_framework.py

What this module provides:
- Semantic DOM snapshot generator (reduced DOM) to pass to LLM
- BQLExecutor: execute BQL actions in Playwright safely
- Captcha & consent detection helpers (detect only; do not bypass captchas)
- Small agent example that: takes snapshot, sends to LLM (user-supplied call_llm), receives BQL, executes it
- Logging, timeouts, and safe fallbacks (human-in-loop when captcha detected)

Usage summary (short):
1. Install dependencies: pip install playwright
   then: playwright install
2. Implement call_llm(snapshot, instruction) -> list_of_actions (see placeholder)
   - You must supply an LLM-calling function that returns a JSON array of BQL actions
3. Run the example at bottom or import classes into your project

Security & ethics note:
- This framework DOES NOT solve or bypass captchas programmatically.
  If a captcha is detected, the framework will surface it and optionally pause for
  human intervention or return a special BQL action ("interrupt": "captcha_detected").
- It will attempt to interact with cookie-consent banners where obvious (click "Accept" buttons)
  because cookie consent is a legitimate UX element. You can disable that behavior.

BQL action format (JSON array):
[
  {"action": "fill", "selector": "#user_login", "value": "admin"},
  {"action": "click", "selector": "#wp-submit"},
  {"action": "wait", "value": 1500}
]

Supported actions implemented by BQLExecutor:
- fill, click, wait (ms), select, submit, screenshot, evaluate, scroll, type

"""

from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeoutError
from typing import List, Dict, Any, Optional
import json
import time
import logging
import os
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# -------------------- Semantic DOM snapshot --------------------

SKIP_TAGS = {"script", "style", "meta", "link", "noscript"}

def extract_semantic_dom(page: Page, text_limit: int = 200) -> Dict[str, Any]:
    """Return a reduced DOM snapshot as a nested dict. Suitable to pass to an LLM.

    Includes: tag, attrs (id/class/href/type/role/aria-*), short text, children.
    """
    script = f"""
    () => {{
        function serialize(node) {{
            if (!node || node.nodeType !== Node.ELEMENT_NODE) return null;
            const tag = node.tagName.toLowerCase();
            const skip = {list(SKIP_TAGS)};
            if (skip.includes(tag)) return null;

            const attrs = {{}};
            for (const attr of node.attributes) {{
                if (['id','class','href','type','role','aria-label','aria-labelledby'].includes(attr.name)) {{
                    attrs[attr.name] = attr.value;
                }}
            }}

            let text = node.innerText?.trim();
            if (text && text.length > {text_limit}) text = undefined;

            const obj = {{ tag, attrs: Object.keys(attrs).length ? attrs : undefined, text: text || undefined }};
            const children = [];
            for (const ch of node.children) {{
                const c = serialize(ch);
                if (c) children.push(c);
            }}
            if (children.length) obj.children = children;
            return obj;
        }}
        return serialize(document.body);
    }}
    """
    try:
        return page.evaluate(script)
    except Exception as e:
        logger.exception("extract_semantic_dom failed: %s", e)
        return {"error": str(e)}


# -------------------- Interactive elements snapshot --------------------

def extract_interactive_elements(page: Page) -> List[Dict[str, Any]]:
    """Return list of interactive elements: a[href], button, input, textarea, select, [role=button], [onclick]"""
    selector_list = ["a[href]", "button", "input", "textarea", "select", "[role=button]", "[onclick]"]
    selector = ",".join(selector_list)
    script = f"""
    () => {{
        const out = [];
        for (const el of document.querySelectorAll('{selector}')) {{
            out.push({{
                tag: el.tagName.toLowerCase(),
                text: el.innerText?.trim() || undefined,
                attrs: {{
                    id: el.id || undefined,
                    class: el.className || undefined,
                    href: el.getAttribute('href') || undefined,
                    type: el.getAttribute('type') || undefined,
                    role: el.getAttribute('role') || undefined
                }}
            }});
        }}
        return out;
    }}
    """
    try:
        return page.evaluate(script)
    except Exception as e:
        logger.exception("extract_interactive_elements failed: %s", e)
        return []


# -------------------- Iframe snapshot (useful for recaptcha detection) --------------------

def extract_iframe_info(page: Page) -> List[Dict[str, Any]]:
    """Return list of frames with url and a small DOM signature."""
    frames = []
    try:
        for frame in page.frames:
            try:
                # Some frames are cross-origin -- accessing inner DOM may throw
                url = frame.url
                # we attempt a small probe: count of inputs/buttons and presence of known recaptcha markers
                info = frame.evaluate("""() => {
                    const res = {inputs: document.querySelectorAll('input').length, buttons: document.querySelectorAll('button').length};
                    res.hasRecaptcha = !!document.querySelector('[class*="g-recaptcha"], iframe[src*="recaptcha"], div.recaptcha');
                    return res;
                }""")
                frames.append({"url": url, "probe": info})
            except Exception:
                # cross-origin or blocked frame
                frames.append({"url": frame.url, "probe": "cross-origin or blocked"})
    except Exception as e:
        logger.exception("extract_iframe_info failed: %s", e)
    return frames


# -------------------- Captcha & consent detection --------------------

COMMON_CONSENT_SELECTORS = [
    "#onetrust-accept-btn-handler",
    "button[aria-label*='accept']",
    "button[data-cookiebanner]",
    "button[class*='cookie']",
    "div.cookie-consent",
    "#cookie-consent",
    "[id*=consent]",
    "[class*=consent]",
]

COMMON_RECAPTCHA_SELECTORS = [
    # reCAPTCHA
    "iframe[src*='recaptcha']",
    "[class*='g-recaptcha']",
    "div.recaptcha",
    "iframe[src*='api2/anchor']",
    # hCaptcha
    "iframe[src*='hcaptcha']",
    "[class*='h-captcha']",
    "div.hcaptcha",
    # Cloudflare Turnstile
    "iframe[src*='challenges.cloudflare']",
    "iframe[src*='turnstile']",
    "div[class*='cf-turnstile']",
]


def detect_consent_or_captcha(page: Page) -> Dict[str, Any]:
    """Return whether a cookie-consent or captcha-like element was detected.

    Returns dict like: {consent: True/False, consent_candidates: [...], captcha_like: True/False, frames: [...]}
    """
    consent_candidates = []
    captcha_like = False
    try:
        for s in COMMON_CONSENT_SELECTORS:
            try:
                exists = page.query_selector(s)
                if exists:
                    consent_candidates.append(s)
            except Exception:
                continue

        for s in COMMON_RECAPTCHA_SELECTORS:
            try:
                exists = page.query_selector(s)
                if exists:
                    captcha_like = True
                    break
            except Exception:
                continue

        # check frames probe
        frames = extract_iframe_info(page)
        frame_has_recaptcha = any((f.get('probe') != 'cross-origin or blocked' and f.get('probe', {}).get('hasRecaptcha')) for f in frames)
        if frame_has_recaptcha:
            captcha_like = True

        return {
            "consent": bool(consent_candidates),
            "consent_selectors": consent_candidates,
            "captcha_like": captcha_like,
            "iframes": frames,
        }
    except Exception as e:
        logger.exception("detect_consent_or_captcha failed: %s", e)
        return {"error": str(e)}


# -------------------- BQL Executor --------------------

class BQLExecutor:
    def __init__(self, page: Page, default_timeout: int = 5000, safe: bool = True):
        self.page = page
        self.default_timeout = default_timeout
        self.safe = safe  # if true, perform bounds checks and avoid dangerous evaluate calls

    def run(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute BQL actions sequentially. Returns a list of results for each step."""
        results = []
        for idx, a in enumerate(actions):
            try:
                res = self._run_action(a)
                results.append({"ok": True, "action": a, "result": res})
            except Exception as e:
                logger.exception("Action failed: %s", a)
                results.append({"ok": False, "action": a, "error": str(e)})
                # if a step fails, stop to avoid cascading side effects
                break
        return results

    def _run_action(self, a: Dict[str, Any]):
        action = a.get("action")
        selector = a.get("selector")
        if action == "fill":
            if not selector:
                raise ValueError("fill requires selector")
            value = a.get("value", "")
            self.page.locator(selector).fill(value, timeout=self.default_timeout)
            return {"filled": selector}

        elif action == "type":
            if not selector:
                raise ValueError("type requires selector")
            value = a.get("value", "")
            self.page.locator(selector).type(value, timeout=self.default_timeout)
            return {"typed": selector}

        elif action == "click":
            if not selector:
                raise ValueError("click requires selector")
            # support optional 'force' and 'timeout'
            opts = {}
            if "force" in a:
                opts["force"] = bool(a.get("force"))
            if "timeout" in a:
                opts["timeout"] = int(a.get("timeout"))
            self.page.locator(selector).click(**opts)
            return {"clicked": selector}

        elif action == "select":
            if not selector:
                raise ValueError("select requires selector")
            val = a.get("value")
            if val is None:
                raise ValueError("select requires value")
            self.page.locator(selector).select_option(val)
            return {"selected": selector, "value": val}

        elif action == "wait":
            # wait in ms or wait_for_selector
            if "selector" in a:
                self.page.wait_for_selector(a["selector"], timeout=int(a.get("value", self.default_timeout)))
                return {"waited_for": a["selector"]}
            else:
                ms = int(a.get("value", 1000))
                time.sleep(ms / 1000.0)
                return {"slept_ms": ms}

        elif action == "submit":
            if not selector:
                raise ValueError("submit requires selector")
            # evaluate submit on element
            self.page.locator(selector).evaluate("el => el.submit()")
            return {"submitted": selector}

        elif action == "screenshot":
            path = a.get("path", f"screenshot-{int(time.time())}.png")
            self.page.screenshot(path=path)
            return {"screenshot": path}

        elif action == "evaluate":
            # only allow short safe snippets unless safe==False
            expr = a.get("expr")
            if not expr:
                raise ValueError("evaluate requires expr")
            if self.safe and len(expr) > 500:
                raise ValueError("evaluate expr too long in safe mode")
            return self.page.evaluate(expr)

        elif action == "scroll":
            selector = a.get("selector")
            if not selector:
                # scroll to bottom
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                return {"scrolled": "bottom"}
            else:
                self.page.locator(selector).scroll_into_view_if_needed()
                return {"scrolled": selector}

        else:
            raise ValueError(f"Unknown action: {action}")


# -------------------- Agent glue: snapshot -> LLM -> execute --------------------

class BQLAgent:
    def __init__(self, page: Page, call_llm, executor: Optional[BQLExecutor] = None):
        """
        page: Playwright page
        call_llm: function(snapshot: dict, instruction: str) -> list_of_actions (JSON-serializable)
        executor: optional BQLExecutor
        """
        self.page = page
        self.call_llm = call_llm
        self.executor = executor or BQLExecutor(page)

    def run_instruction(self, instruction: str, allow_consent_click: bool = True) -> Dict[str, Any]:
        """Take an instruction for the page, snapshot, ask LLM for BQL and execute.

        Returns a dict with: snapshot, llm_response, execution_results, detection
        """
        # 1. Build snapshot
        snapshot = {
            "url": self.page.url,
            "dom_tree": extract_semantic_dom(self.page),
            "interactive": extract_interactive_elements(self.page),
            "iframes": extract_iframe_info(self.page),
        }

        # 2. Detect consent/captcha
        detection = detect_consent_or_captcha(self.page)

        # 3. Optionally try to click obvious consent accept buttons
        if allow_consent_click and detection.get("consent"):
            logger.info("Consent candidates found: %s", detection.get("consent_selectors"))
            for sel in detection.get("consent_selectors", []):
                try:
                    logger.info("Attempting to click consent selector: %s", sel)
                    self.page.locator(sel).click(timeout=2000)
                    # small wait for UI to update
                    time.sleep(0.8)
                except Exception:
                    logger.debug("Consent selector click failed: %s", sel)

            # refresh snapshot after possible dismissal
            snapshot["dom_tree"] = extract_semantic_dom(self.page)
            snapshot["interactive"] = extract_interactive_elements(self.page)

        # 4. If captcha-like present, do not ask LLM to bypass; instead return an interrupt
        if detection.get("captcha_like"):
            logger.warning("Captcha-like element detected. Aborting automated run and returning interrupt.")
            return {
                "snapshot": snapshot,
                "detection": detection,
                "llm_response": None,
                "execution_results": [{"ok": False, "action": None, "error": "captcha_detected"}],
            }

        # 5. Call the LLM (user-supplied) with a stable prompt template
        prompt = self._build_prompt(instruction, snapshot)
        llm_out = self.call_llm(snapshot, prompt)

        # Expect llm_out to be a JSON array of actions; attempt to parse robustly
        try:
            actions = _parse_actions_from_llm(llm_out)
        except Exception as e:
            logger.exception("Failed to parse LLM output as JSON actions: %s", e)
            return {"snapshot": snapshot, "detection": detection, "llm_response": llm_out, "execution_results": [{"ok": False, "error": "invalid_llm_output"}]}

        # 6. Execute actions
        exec_results = self.executor.run(actions)

        return {"snapshot": snapshot, "detection": detection, "llm_response": llm_out, "execution_results": exec_results}

    def _build_prompt(self, instruction: str, snapshot: dict) -> str:
        # A compact prompt template that instructs the LLM to return BQL only
        template = (
            "You are a browser automation agent.\n"
            "Return ONLY a JSON array of BQL actions (no explanation).\n"
            "Supported actions: fill(selector,value), click(selector), select(selector,value), submit(selector), wait(value ms), scroll(selector optional), screenshot(path optional).\n"
            "Selectors must be CSS selectors.\n"
            "Page snapshot (reduced DOM) is provided below. Use it to choose selectors.\n\n"
            "INSTRUCTION:\n" + instruction + "\n\n"
            "SNAPSHOT:\n" + json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
        )
        # Keep prompt compact if snapshot very large -- real deployments should respect LLM token limits
        return template


# -------------------- Example: placeholder LLM caller --------------------

def call_llm_placeholder(snapshot: dict, prompt: str) -> List[Dict[str, Any]]:
    """Placeholder LLM function. Replace with real LLM calls (OpenAI, Ollama, local model, etc.)

    This example returns a static BQL used for testing.
    """
    logger.info("[call_llm_placeholder] Prompt length: %d", len(prompt))
    # Example: if snapshot contains an input with id 'user_login', auto-fill
    interactive = snapshot.get("interactive", [])
    # naive heuristic test
    actions = []
    for el in interactive:
        attrs = el.get("attrs") or {}
        if attrs.get("id") == "user_login":
            actions.append({"action": "fill", "selector": "#user_login", "value": "admin"})
        if attrs.get("id") == "user_pass":
            actions.append({"action": "fill", "selector": "#user_pass", "value": "admin123"})
    # if submit button exists
    for el in interactive:
        if el.get("tag") == "input" and (el.get("attrs") or {}).get("type") == "submit":
            if el.get("attrs", {}).get("id"):
                actions.append({"action": "click", "selector": f"#{el.get('attrs').get('id')}"})
    # fallback: no actions -> return empty array
    return actions


# -------------------- Real LLM integrations --------------------

def call_llm_ollama(snapshot: dict, prompt: str) -> str:
    """Call a local Ollama server synchronously and return text.

    Env vars:
    - CURLLM_OLLAMA_HOST (default http://localhost:11434)
    - CURLLM_MODEL (default qwen2.5:7b)
    """
    host = os.getenv("CURLLM_OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    model = os.getenv("CURLLM_MODEL", "qwen2.5:7b")
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": float(os.getenv("CURLLM_TEMPERATURE", "0.1")),
            "top_p": float(os.getenv("CURLLM_TOP_P", "0.9")),
            "num_ctx": int(os.getenv("CURLLM_NUM_CTX", "8192")),
            "num_predict": int(os.getenv("CURLLM_NUM_PREDICT", "512")),
        },
    }
    r = requests.post(f"{host}/api/generate", json=payload, timeout=120)
    r.raise_for_status()
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    text = data.get("response", "") if isinstance(data, dict) else str(data)
    return text


def call_llm_openai(snapshot: dict, prompt: str) -> str:
    """Call OpenAI Chat Completions API using requests and return text.

    Requires OPENAI_API_KEY env. Uses gpt-4o-mini by default (configurable via OPENAI_MODEL).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set for call_llm_openai")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return ONLY a JSON array of BQL actions. No prose."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }
    resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body, timeout=120)
    resp.raise_for_status()
    j = resp.json()
    return j.get("choices", [{}])[0].get("message", {}).get("content", "")


def select_llm_caller() -> Any:
    """Pick LLM caller based on env. Defaults to Ollama; uses OpenAI if OPENAI_API_KEY set and BQL_FRAMEWORK_LLM=openai."""
    prefer = os.getenv("BQL_FRAMEWORK_LLM", "").lower()
    if prefer == "openai" and os.getenv("OPENAI_API_KEY"):
        return call_llm_openai
    # fallback to Ollama
    return call_llm_ollama


def _parse_actions_from_llm(llm_out: Any) -> List[Dict[str, Any]]:
    """Robustly parse a JSON array of action dicts from an LLM output string or list.
    - Accepts list directly
    - For strings, strips code-fences and scans for a balanced top-level JSON array
    """
    if isinstance(llm_out, list):
        return llm_out
    if not isinstance(llm_out, str):
        # last resort
        return []

    def _strip_fences(s: str) -> str:
        s = s.strip()
        if s.startswith("```"):
            s = s.split("\n", 1)[1] if "\n" in s else s
            if s.rstrip().endswith("```"):
                s = s.rsplit("```", 1)[0]
        return s.strip()

    raw = _strip_fences(llm_out)
    # direct parse
    try:
        arr = json.loads(raw)
        if isinstance(arr, list):
            return arr
    except Exception:
        pass
    # scan for a balanced array ignoring brackets in strings
    start = -1
    depth = 0
    in_str = False
    esc = False
    for i, ch in enumerate(raw):
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
            continue
        else:
            if ch == '"':
                in_str = True
                continue
            if ch == '[':
                if depth == 0:
                    start = i
                depth += 1
                continue
            if ch == ']' and depth > 0:
                depth -= 1
                if depth == 0 and start != -1:
                    sl = raw[start : i + 1]
                    try:
                        arr = json.loads(sl)
                        if isinstance(arr, list):
                            return arr
                    except Exception:
                        pass
                    start = -1
    # nothing parsed
    return []


# -------------------- If run as script: demo --------------------

if __name__ == "__main__":
    # demo usage (requires playwright installed and browsers available)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://example.com", wait_until="networkidle")

        llm_caller = select_llm_caller()
        agent = BQLAgent(page, call_llm=llm_caller)
        instruction = "Find any login inputs and fill them with demo credentials; then click submit if found."
        res = agent.run_instruction(instruction)
        print(json.dumps(res, ensure_ascii=False, indent=2))

        browser.close()

"""
Examples of usage on various websites (pseudo-code)

Example 1: WordPress Login Page
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://www.prototypowanie.pl/wp-login.php", wait_until="networkidle")
    agent = BQLAgent(page, call_llm=select_llm_caller())
    res = agent.run_instruction("Zaloguj się do WordPress. Login: admin, Hasło: test123.")
    print(res)
    browser.close()

Example 2: Allegro – wyszukiwanie produktów poniżej 150 zł
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://ceneo.pl", wait_until="networkidle")
    agent = BQLAgent(page, call_llm=select_llm_caller())
    res = agent.run_instruction("Znajdź wszystkie produkty poniżej 150 zł i zwróć nazwy, ceny i URL-e.")
    print(res)
    browser.close()

Example 3: Formularz Kontaktowy
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://softreck.com/contact", wait_until="networkidle")
    agent = BQLAgent(page, call_llm=select_llm_caller())
    res = agent.run_instruction("Wypełnij formularz kontaktowy: Imię Jan, Email jan@example.com, Wiadomość 'Test wysyłki'. Wyślij formularz.")
    print(res)
    browser.close()
"""

