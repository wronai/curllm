"""CurllmExecutor - Main browser automation executor with LLM support"""

import inspect
import json
import logging
import os
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from curllm_server.config import config
from curllm_server.llm.simple_ollama import SimpleOllama
from curllm_server.vision.analyzer import VisionAnalyzer
from curllm_server.captcha.solver import CaptchaSolver
from curllm_server.stealth.stealth_config import StealthConfig
from curllm_server.browser.browserless_context import BrowserlessContext
from curllm_server.agents.local_agent import LocalAgent
from curllm_server.logger.run_logger import RunLogger

from curllm_core.config_logger import log_all_config
from curllm_core.runtime import parse_runtime_from_instruction
from curllm_core.executor import CurllmExecutor as CoreExecutor

logger = logging.getLogger(__name__)

# Browser automation imports (optional) with robust fallback
try:
    from browser_use import Agent as BrowserUseAgent
except Exception:
    BrowserUseAgent = None


class CurllmExecutor:
    """Main browser automation executor with LLM support"""
    
    def __init__(self):
        self.llm = self._setup_llm()
        self.vision_analyzer = VisionAnalyzer()
        self.captcha_solver = CaptchaSolver()
        self.stealth_config = StealthConfig()
    
    def _setup_llm(self) -> Any:
        """Initialize Ollama LLM. Default to SimpleOllama for stability.
        Set env CURLLM_LLM_BACKEND=langchain to use langchain_ollama.
        """
        backend = os.getenv("CURLLM_LLM_BACKEND", "simple").lower()
        if backend == "langchain":
            try:
                from langchain_ollama import OllamaLLM
                return OllamaLLM(
                    base_url=config.ollama_host,
                    model=config.ollama_model,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    num_ctx=config.num_ctx,
                    num_predict=config.num_predict,
                )
            except Exception as e:
                logger.warning(f"langchain_ollama requested but unavailable, falling back to SimpleOllama: {e}")
        # Fallback / default
        return SimpleOllama(
            base_url=config.ollama_host,
            model=config.ollama_model,
            num_ctx=config.num_ctx,
            num_predict=config.num_predict,
            temperature=config.temperature,
            top_p=config.top_p,
        )
    
    async def execute_workflow(
        self,
        instruction: str,
        url: Optional[str] = None,
        visual_mode: bool = False,
        stealth_mode: bool = False,
        captcha_solver: bool = False,
        use_bql: bool = False,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute browser automation workflow - delegates to core executor with orchestrators"""
        # Parse runtime parameters embedded in JSON instruction and build command line for logging
        instruction, runtime = parse_runtime_from_instruction(instruction)
        cmd_parts = ["curllm"]
        if visual_mode:
            cmd_parts.append("--visual")
        if stealth_mode:
            cmd_parts.append("--stealth")
        if use_bql:
            cmd_parts.append("--bql")
        if captcha_solver:
            cmd_parts.append("--captcha-solver")
        if headers:
            for k, v in (headers or {}).items():
                cmd_parts.append(f'-H "{k}: {v}"')
        if url:
            cmd_parts.append(f'"{url}"')
        if instruction:
            escaped = instruction.replace('"', '\\"')
            cmd_parts.append(f'-d "{escaped}"')
        command_line = " ".join(cmd_parts)

        # Delegate to core executor (restores orchestrators, progressive context, multi-phase LLM interaction)
        try:
            core_executor = CoreExecutor()
            result = await core_executor.execute_workflow(
                instruction=instruction,
                url=url,
                visual_mode=visual_mode,
                stealth_mode=stealth_mode,
                captcha_solver=captcha_solver,
                use_bql=use_bql,
                headers=headers,
                runtime=runtime,
                command_line=command_line
            )
            return result
        except Exception as e:
            logger.error(f"Core executor failed: {e}", exc_info=True)
            # Prepare fallback logger for error case
            run_logger = RunLogger(instruction=instruction, url=url, command_line=command_line)
            run_logger.log_heading(f"curllm run: {datetime.now().isoformat()}")
            log_all_config(run_logger, visual_mode, stealth_mode, use_bql, runtime)
            run_logger.log_text("Error occurred (core executor):")
            run_logger.log_code("text", str(e))
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "run_log": str(run_logger.path)
            }

    def _create_agent(self, browser_context, instruction: str, visual_mode: bool):
        """Instantiate an Agent compatible with different browser_use versions."""
        if BrowserUseAgent is not None:
            try:
                params = inspect.signature(BrowserUseAgent.__init__).parameters
                kwargs = {
                    "browser": browser_context,
                    "llm": self.llm,
                    "max_steps": config.max_steps,
                    "visual_mode": visual_mode,
                }
                if "task" in params:
                    kwargs["task"] = instruction
                return BrowserUseAgent(**kwargs)
            except Exception as e:
                logger.warning(f"browser_use.Agent init failed: {e}. Falling back to LocalAgent.")
        return LocalAgent(browser_context, self.llm, config.max_steps, visual_mode, task=instruction)
    
    async def _setup_browser(self, stealth_mode: bool, storage_key: Optional[str] = None):
        """Setup browser with optional stealth mode"""
        if config.use_browserless:
            return await self._setup_browserless()
        else:
            return await self._setup_playwright(stealth_mode, storage_key)
    
    async def _setup_playwright(self, stealth_mode: bool, storage_key: Optional[str] = None):
        """Setup Playwright browser and return context with attached resources"""
        playwright = await async_playwright().start()
        launch_args = {
            "headless": bool(config.headless),
            "args": ["--no-sandbox", "--disable-dev-shm-usage"]
        }
        if stealth_mode:
            launch_args["args"].extend(self.stealth_config.get_chrome_args())
        if config.proxy:
            launch_args["proxy"] = {"server": config.proxy}
        browser = await playwright.chromium.launch(**launch_args)
        # Storage state per-domain
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
        # Human-like viewport and headers
        vw = 1366 + int(random.random() * 700)
        vh = 768 + int(random.random() * 400)
        context_args = {
            "viewport": {"width": vw, "height": vh},
            "user_agent": self.stealth_config.get_user_agent() if stealth_mode else None,
            "locale": config.locale,
            "timezone_id": config.timezone_id,
            "extra_http_headers": {"Accept-Language": f"{config.locale},en;q=0.8"}
        }
        if storage_path and storage_path.exists():
            context_args["storage_state"] = str(storage_path)
        context = await browser.new_context(**context_args)
        if stealth_mode:
            await self.stealth_config.apply_to_context(context)
        # Attach resources for later cleanup
        setattr(context, "_curllm_browser", browser)
        setattr(context, "_curllm_playwright", playwright)
        if storage_path:
            setattr(context, "_curllm_storage_path", str(storage_path))
        return context
    
    async def _setup_browserless(self):
        """Setup Browserless browser connection"""
        import websockets
        ws = await websockets.connect(config.browserless_url)
        return BrowserlessContext(ws)
    
    async def _take_screenshot(self, page, step: int, target_dir: Optional[Path] = None) -> str:
        """Take and save screenshot"""
        tdir = Path(target_dir) if target_dir else config.screenshot_dir
        tdir.mkdir(parents=True, exist_ok=True)
        filename = tdir / f"step_{step}_{datetime.now().timestamp()}.png"
        await page.screenshot(path=str(filename))
        return str(filename)
    
    async def _extract_page_context(self, page) -> Dict:
        """Extract page context for LLM (null-safe)."""
        return await page.evaluate("""
            () => {
                const safeText = (el) => { try { return (el && el.innerText) ? String(el.innerText) : ''; } catch(e){ return ''; } };
                const bodyText = (() => { try { return (document.body && document.body.innerText) ? document.body.innerText : ''; } catch(e){ return ''; } })();
                return {
                    title: document.title,
                    url: window.location.href,
                    text: bodyText.substring(0, 5000),
                    forms: Array.from(document.forms || []).map(f => ({
                        id: (f && f.id) || undefined,
                        action: (f && f.action) || undefined,
                        fields: Array.from((f && f.elements) || []).map(e => ({
                            name: (e && e.name) || undefined,
                            type: (e && e.type) || undefined,
                            value: (e && e.value) || '',
                            visible: !!(e && e.offsetParent !== null)
                        }))
                    })),
                    links: Array.from(document.links || []).slice(0, 50).map(l => ({
                        href: (l && l.href) ? l.href : '',
                        text: safeText(l)
                    })),
                    buttons: Array.from(document.querySelectorAll('button') || []).map(b => ({
                        text: safeText(b),
                        onclick: (b && b.onclick) ? 'has handler' : null
                    }))
                };
            }
        """)
    
    async def _generate_action(self, instruction: str, page_context: Dict, step: int, run_logger: 'RunLogger' = None) -> Dict:
        """Generate next action using LLM (robust JSON parsing)."""
        context_str = json.dumps(page_context, indent=2)[: config.log_prompt_chars]
        prompt_text = (
            "You are a browser automation expert. Analyze the current page and determine the next action.\n\n"
            f"Instruction: {instruction}\n"
            f"Current Step: {step}\n"
            f"Page Context: {context_str}\n\n"
            "Generate a JSON action:\n"
            "{\n"
            "    \"type\": \"click|fill|scroll|wait|complete\",\n"
            "    \"selector\": \"CSS selector if applicable\",\n"
            "    \"value\": \"value to fill if applicable\",\n"
            "    \"extracted_data\": \"data if task is complete\"\n"
            "}\n\n"
            "Response (JSON only):"
        )
        if run_logger:
            run_logger.log_text("LLM Prompt:")
            run_logger.log_code("json", prompt_text)
        try:
            response = await self.llm.ainvoke(prompt_text)
            text = response["text"] if isinstance(response, dict) and "text" in response else str(response)
        except Exception as e:
            if run_logger:
                run_logger.log_text("LLM error, continuing with wait/fallback:")
                run_logger.log_code("text", str(e))
            logger.warning(f"LLM ainvoke failed, using wait action: {e}")
            return {"type": "wait"}
        if run_logger:
            run_logger.log_text("LLM Raw Response:")
            run_logger.log_code("json", text)

        raw = self._strip_fences(text)
        # Try direct JSON
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
        # Scan for any balanced JSON object in the text
        return self._extract_json_from_text(raw)
    
    def _strip_fences(self, s: str) -> str:
        """Strip markdown code fences from text"""
        s = s.strip()
        if s.startswith("```"):
            s = s.split("\n", 1)[1] if "\n" in s else s
            if s.rstrip().endswith("```"):
                s = s.rsplit("```", 1)[0]
        return s.strip()
    
    def _extract_json_from_text(self, raw: str) -> Dict:
        """Extract JSON object from text by finding balanced braces"""
        try:
            objs = []
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
                    if ch == '{':
                        if depth == 0:
                            start = i
                        depth += 1
                        continue
                    if ch == '}' and depth > 0:
                        depth -= 1
                        if depth == 0 and start != -1:
                            objs.append(raw[start:i+1])
                            start = -1
            for cand in objs[::-1]:
                try:
                    obj = json.loads(cand)
                    if isinstance(obj, dict):
                        return obj
                except Exception:
                    continue
        except Exception:
            pass
        return {"type": "wait"}
    
    async def _execute_action(self, page, action: Dict):
        """Execute browser action"""
        action_type = action.get("type")
        
        if action_type == "click":
            await self._execute_click(page, action)
        elif action_type == "fill":
            await self._execute_fill(page, action)
        elif action_type == "scroll":
            await self._execute_scroll(page)
        elif action_type == "wait":
            await page.wait_for_timeout(800 + int(random.random()*1200))
    
    async def _execute_click(self, page, action: Dict):
        """Execute click action"""
        try:
            await page.wait_for_timeout(200 + int(random.random()*400))
        except Exception:
            pass
        try:
            loc = page.locator(str(action.get("selector")))
            await loc.first.wait_for(state="visible", timeout=5000)
            await loc.first.click(timeout=5000)
        except Exception:
            try:
                await page.evaluate(
                    "(s)=>{ const el=document.querySelector(s); if(el) el.click(); }",
                    str(action.get("selector"))
                )
            except Exception:
                pass
    
    async def _execute_fill(self, page, action: Dict):
        """Execute fill action"""
        try:
            sel = str(action.get("selector"))
            val = str(action.get("value", ""))
            loc = page.locator(sel)
            await loc.first.wait_for(state="visible", timeout=5000)
            await loc.first.fill(val)
            # Fire input/blur to trigger client-side validation
            try:
                await page.evaluate(
                    "(s) => { const el=document.querySelector(s); if(!el) return; "
                    "try{ el.dispatchEvent(new Event('input', {bubbles:true})); }catch(e){} "
                    "try{ el.blur(); }catch(e){} }",
                    sel
                )
            except Exception:
                pass
        except Exception:
            pass
        try:
            await page.wait_for_timeout(150 + int(random.random()*350))
        except Exception:
            pass
    
    async def _execute_scroll(self, page):
        """Execute scroll action"""
        dy = 300 + int(random.random()*700)
        try:
            await page.mouse.wheel(0, dy)
        except Exception:
            await page.evaluate(f"window.scrollBy(0, {dy})")
        await page.wait_for_timeout(500 + int(random.random()*800))
    
    async def _detect_honeypot(self, page) -> bool:
        """Detect honeypot fields"""
        honeypots = await page.evaluate("""
            () => {
                const suspicious = [];
                const inputs = document.querySelectorAll('input, textarea');
                
                inputs.forEach(input => {
                    // Check if hidden
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
        """)
        return honeypots

    async def _is_block_page(self, page) -> bool:
        """Detect common block/anti-bot pages"""
        try:
            txt = await page.evaluate(
                "() => (document.body && document.body.innerText || '').slice(0, 4000).toLowerCase()"
            )
            markers = [
                "you have been blocked",
                "access denied",
                "robot",
                "are you human",
                "verify you are human",
                "captcha"
            ]
            return any(m in txt for m in markers)
        except Exception:
            return False
    
    async def _accept_cookies(self, page):
        """Attempt to accept cookie banners on common sites (best effort)"""
        try:
            # Try by accessible name
            names = ["Akceptuj", "Zgadzam się", "Accept", "I agree"]
            for name in names:
                try:
                    btn = page.get_by_role("button", name=name)
                    if await btn.count() > 0:
                        await btn.first.click(timeout=1000)
                        return
                except Exception:
                    pass
            # Try common CSS selectors
            selectors = [
                'button:has-text("Akceptuj")',
                'button:has-text("Zgadzam się")',
                'button:has-text("Accept")',
                'button:has-text("I agree")',
                'button[aria-label*="accept" i]',
                '#onetrust-accept-btn-handler',
                '.cookie-accept', '.cookie-approve', '.cookies-accept',
                'button[mode="primary"]'
            ]
            for sel in selectors:
                try:
                    loc = page.locator(sel)
                    if await loc.count() > 0:
                        await loc.first.click(timeout=1000)
                        return
                except Exception:
                    pass
        except Exception:
            pass
    
    async def _auto_scroll(self, page, steps: int = 3, delay_ms: int = 500):
        """Scroll down the page a few times to trigger lazy-loading"""
        for _ in range(steps):
            try:
                await page.evaluate("window.scrollBy(0, window.innerHeight);")
                await page.wait_for_timeout(delay_ms)
            except Exception:
                break
    
    async def _handle_captcha(self, page, screenshot_path: str):
        """Handle CAPTCHA solving"""
        solution = await self.captcha_solver.solve(screenshot_path)
        if solution:
            # Find CAPTCHA input field
            await page.fill('input[name*="captcha"]', solution)
    
    def _parse_bql(self, query: str) -> str:
        """Parse BQL query to instruction"""
        # Simplified BQL parser
        if "query" in query and "{" in query:
            # Extract fields from BQL
            return f"Extract the following fields from the page: {query}"
        return query
