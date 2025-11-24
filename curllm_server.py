#!/usr/bin/env python3
"""
curllm_server.py - API Server for Browser Automation with Local LLM
Supports visual analysis, CAPTCHA solving, and stealth mode
"""

import asyncio
import base64
import json
import re
import logging
import os
import sys
import tempfile
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

from flask import Flask, request, jsonify
from flask_cors import CORS
import aiohttp
from dotenv import load_dotenv

import inspect
from dataclasses import dataclass as _dc_dataclass

# Browser automation imports (optional) with robust fallback
try:
    from browser_use import Agent as BrowserUseAgent
except Exception:
    BrowserUseAgent = None

class LocalAgent:
    def __init__(self, browser, llm, max_steps, visual_mode, task=None):
        self.browser = browser
        self.llm = llm
        self.max_steps = max_steps
        self.visual_mode = visual_mode

from playwright.async_api import async_playwright
from PIL import Image
import cv2
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ============================================================================
# Configuration
# ============================================================================

@dataclass
class Config:
    """Application configuration"""
    ollama_host: str = os.getenv("CURLLM_OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("CURLLM_MODEL", "qwen2.5:7b")
    browserless_url: str = os.getenv("BROWSERLESS_URL", "ws://localhost:3000")
    use_browserless: bool = os.getenv("CURLLM_BROWSERLESS", "false").lower() == "true"
    max_steps: int = int(os.getenv("CURLLM_MAX_STEPS", "20"))
    screenshot_dir: Path = Path(os.getenv("CURLLM_SCREENSHOT_DIR", "./screenshots"))
    enable_debug: bool = os.getenv("CURLLM_DEBUG", "false").lower() == "true"
    api_port: int = int(os.getenv("CURLLM_API_PORT", os.getenv("API_PORT", "8000")))
    num_ctx: int = int(os.getenv("CURLLM_NUM_CTX", "8192"))
    num_predict: int = int(os.getenv("CURLLM_NUM_PREDICT", "512"))
    temperature: float = float(os.getenv("CURLLM_TEMPERATURE", "0.3"))
    top_p: float = float(os.getenv("CURLLM_TOP_P", "0.9"))
    headless: bool = os.getenv("CURLLM_HEADLESS", "true").lower() == "true"
    locale: str = os.getenv("CURLLM_LOCALE", os.getenv("LOCALE", "pl-PL"))
    timezone_id: str = os.getenv("CURLLM_TIMEZONE", os.getenv("TIMEZONE", "Europe/Warsaw"))
    proxy: Optional[str] = (os.getenv("CURLLM_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or None)
    
    def __post_init__(self):
        self.screenshot_dir.mkdir(exist_ok=True)

load_dotenv()
config = Config()

# ============================================================================
# Core Execution Engine
# ============================================================================

class RunLogger:
    """Markdown run logger for step-by-step diagnostics"""
    def __init__(self, instruction: str, url: Optional[str]):
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        self.dir = Path('./logs')
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / f'run-{ts}.md'
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write(f"# curllm Run Log ({ts})\n\n")
            if url:
                f.write(f"- URL: {url}\n")
            if instruction:
                f.write(f"- Instruction: {instruction}\n\n")

    def _write(self, text: str):
        with open(self.path, 'a', encoding='utf-8') as f:
            f.write(text)

    def log_heading(self, text: str):
        self._write(f"\n## {text}\n\n")

    def log_text(self, text: str):
        self._write(f"{text}\n\n")

    def log_kv(self, key: str, value: str):
        self._write(f"- {key}: {value}\n")

    def log_code(self, lang: str, code: str):
        self._write(f"```{lang}\n{code}\n```\n\n")

class SimpleOllama:
    """Minimal async Ollama client used when langchain_ollama is unavailable"""
    def __init__(self, base_url: str, model: str, num_ctx: int, num_predict: int, temperature: float, top_p: float):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.options = {
            "num_ctx": num_ctx,
            "num_predict": num_predict,
            "temperature": temperature,
            "top_p": top_p,
        }
    async def ainvoke(self, prompt: str):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": self.options,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/api/generate", json=payload) as resp:
                data = await resp.json()
        text = data.get("response", "") if isinstance(data, dict) else str(data)
        return {"text": text}

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
        """Execute browser automation workflow"""
        # Prepare run logger
        run_logger = RunLogger(instruction=instruction, url=url)
        run_logger.log_heading(f"curllm run: {datetime.now().isoformat()}")
        run_logger.log_kv("CURLLM_MODEL", config.ollama_model)
        run_logger.log_kv("CURLLM_OLLAMA_HOST", config.ollama_host)
        run_logger.log_kv("VISUAL_MODE", str(visual_mode))
        run_logger.log_kv("STEALTH_MODE", str(stealth_mode))
        run_logger.log_kv("USE_BQL", str(use_bql))

        browser_context = None
        try:
            # Parse instruction if BQL mode
            if use_bql:
                instruction = self._parse_bql(instruction)
                run_logger.log_text("BQL parsed instruction:")
                run_logger.log_code("text", instruction)
            
            # Setup browser context
            host = urlparse(url).hostname if url else None
            if host and any(h in host for h in ["allegro.pl", "allegro.com"]):
                stealth_mode = True
            browser_context = await self._setup_browser(stealth_mode, storage_key=host)
            run_logger.log_text("Browser context initialized.")
            
            # Create agent (supports browser_use.Agent if available; else LocalAgent)
            agent = self._create_agent(
                browser_context=browser_context,
                instruction=instruction,
                visual_mode=visual_mode
            )
            
            # Execute main task
            result = await self._execute_task(
                agent=agent,
                instruction=instruction,
                url=url,
                visual_mode=visual_mode,
                stealth_mode=stealth_mode,
                captcha_solver=captcha_solver,
                run_logger=run_logger
            )
            
            # Cleanup
            if browser_context is not None:
                try:
                    try:
                        storage_path = getattr(browser_context, "_curllm_storage_path", None)
                        if storage_path:
                            await browser_context.storage_state(path=storage_path)
                    except Exception as e:
                        logger.warning(f"Unable to persist storage state: {e}")
                    await browser_context.close()
                except Exception as e:
                    logger.warning(f"Error during browser close: {e}")
                # Close browser and playwright if attached
                try:
                    br = getattr(browser_context, "_curllm_browser", None)
                    if br is not None:
                        await br.close()
                    pw = getattr(browser_context, "_curllm_playwright", None)
                    if pw is not None:
                        await pw.stop()
                except Exception as e:
                    logger.warning(f"Error closing Playwright resources: {e}")
            
            # Attach run log path
            res = {
                "success": True,
                "result": result.get("data"),
                "steps_taken": result.get("steps", 0),
                "screenshots": result.get("screenshots", []),
                "timestamp": datetime.now().isoformat(),
                "run_log": str(run_logger.path)
            }
            run_logger.log_text("Run finished successfully.")
            return res
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}", exc_info=True)
            run_logger.log_text("Error occurred:")
            run_logger.log_code("text", str(e))
            if browser_context is not None:
                try:
                    try:
                        storage_path = getattr(browser_context, "_curllm_storage_path", None)
                        if storage_path:
                            await browser_context.storage_state(path=storage_path)
                    except Exception:
                        pass
                    await browser_context.close()
                except Exception as ce:
                    logger.warning(f"Error during browser close after failure: {ce}")
                try:
                    br = getattr(browser_context, "_curllm_browser", None)
                    if br is not None:
                        await br.close()
                    pw = getattr(browser_context, "_curllm_playwright", None)
                    if pw is not None:
                        await pw.stop()
                except Exception as e:
                    logger.warning(f"Error closing Playwright resources after failure: {e}")
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
        # Connect to Browserless WebSocket endpoint
        import websockets
        ws = await websockets.connect(config.browserless_url)
        # Return wrapped context (simplified for example)
        return BrowserlessContext(ws)
    
    async def _execute_task(
        self,
        agent,
        instruction: str,
        url: Optional[str],
        visual_mode: bool,
        stealth_mode: bool,
        captcha_solver: bool,
        run_logger: RunLogger
    ) -> Dict:
        """Execute the main browser task"""
        
        result = {
            "data": None,
            "steps": 0,
            "screenshots": []
        }
        lower_instr = (instruction or "").lower()
        
        # Navigate to URL if provided
        if url:
            page = await agent.browser.new_page()
            await page.goto(url)
            try:
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_load_state("networkidle")
            except Exception:
                pass
        else:
            page = await agent.browser.new_page()
        
        # Detect block page and auto-retry with stealth once
        try:
            if await self._is_block_page(page) and not stealth_mode:
                if run_logger:
                    run_logger.log_text("Block page detected; retrying with stealth mode...")
                try:
                    await page.close()
                except Exception:
                    pass
                host = None
                try:
                    host = await page.evaluate("() => window.location.hostname")
                except Exception:
                    try:
                        if url:
                            host = urlparse(url).hostname
                    except Exception:
                        pass
                new_ctx = await self._setup_playwright(True, host)
                agent.browser = new_ctx
                page = await agent.browser.new_page()
                await page.goto(url)
                try:
                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_load_state("networkidle")
                except Exception:
                    pass
                stealth_mode = True
        except Exception:
            pass
        
        # Determine domain-specific screenshot directory (after navigation/redirects)
        domain_dir = config.screenshot_dir
        try:
            host = await page.evaluate("() => window.location.hostname")
            if host:
                domain_dir = config.screenshot_dir / host
                domain_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            try:
                # Fallback from input URL
                if url:
                    host = urlparse(url).hostname
                    if host:
                        domain_dir = config.screenshot_dir / host
                        domain_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
        
        # If instruction asks for screenshot, take one even without visual_mode
        try:
            if ("screenshot" in lower_instr) or ("zrzut" in lower_instr):
                shot_path = await self._take_screenshot(page, 0, target_dir=domain_dir)
                result["screenshots"].append(shot_path)
                if run_logger:
                    try:
                        run_logger.log_image(shot_path, alt="Initial screenshot")
                    except Exception:
                        run_logger.log_text(f"Initial screenshot saved: {shot_path}")
                # Also reflect in data
                result["data"] = {"screenshot_saved": shot_path}
                # If it's purely a screenshot task, finish early
                if not ("extract" in lower_instr or "product" in lower_instr or "produkt" in lower_instr):
                    await page.close()
                    return result
        except Exception:
            pass
        
        # Try to accept cookie banners if present
        try:
            await self._accept_cookies(page)
        except Exception:
            pass
        
        # Early generic-extract fast-path: if instruction is too generic, avoid LLM loop
        try:
            lower_instr = (instruction or "").lower()
            generic_triggers = ("extract" in lower_instr or "scrape" in lower_instr)
            specific_keywords = ["link", "email", "mail", "phone", "tel", "telefon", "product", "produkt", "form", "screenshot", "captcha", "bql"]
            if False and generic_triggers and not any(k in lower_instr for k in specific_keywords):
                ctx = await self._extract_page_context(page)
                try:
                    text = await page.evaluate("() => document.body.innerText")
                except Exception:
                    text = ""
                # Collect basic signals
                anchors = await page.evaluate(
                    """
                        () => Array.from(document.querySelectorAll('a')).map(a => ({
                            text: (a.innerText||'').trim(),
                            href: a.href
                        }))
                    """
                )
                emails = list(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))
                phones = list(set(re.findall(r"(?:\+\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d[\d\s-]{6,}\d", text)))
                result["data"] = {
                    "title": ctx.get("title"),
                    "url": ctx.get("url"),
                    "links": anchors[:50],
                    "emails": emails[:50],
                    "phones": [p.replace(" ", "").replace("-", "") for p in phones][:50],
                }
                if run_logger:
                    run_logger.log_text("Generic fast-path used (title/url/links/emails/phones)")
                    run_logger.log_code("json", json.dumps(result["data"], indent=2))
                await page.close()
                return result
        except Exception:
            pass
        
        # Direct extraction fast-path (avoid LLM for common queries)
        try:
            lower_instr = (instruction or "").lower()
            direct = {}
            if "link" in lower_instr and not ("only" in lower_instr and ("email" in lower_instr or "mail" in lower_instr or "phone" in lower_instr or "tel" in lower_instr or "telefon" in lower_instr)):
                anchors = await page.evaluate(
                    """
                        () => Array.from(document.querySelectorAll('a')).map(a => ({
                            text: (a.innerText||'').trim(),
                            href: a.href
                        }))
                    """
                )
                direct["links"] = anchors[:100]
            if "email" in lower_instr or "mail" in lower_instr:
                text = await page.evaluate("() => document.body.innerText")
                emails_text = list(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))
                emails_mailto = await page.evaluate(
                    """
                        () => Array.from(document.querySelectorAll('a[href^=\"mailto:\"]'))
                            .map(a => (a.getAttribute('href')||'')
                                .replace(/^mailto:/,'')
                                .split('?')[0]
                                .trim())
                            .filter(Boolean)
                    """
                )
                emails = list(sorted(set(emails_text + emails_mailto)))
                direct["emails"] = emails[:100]
            if "phone" in lower_instr or "tel" in lower_instr or "telefon" in lower_instr:
                text = await page.evaluate("() => document.body.innerText")
                phones_text = list(set(re.findall(r"(?:\\+\\d{1,3}[\\s-]?)?(?:\\(?\\d{2,4}\\)?[\\s-]?)?\\d[\\d\\s-]{6,}\\d", text)))
                phones_tel = await page.evaluate(
                    """
                        () => Array.from(document.querySelectorAll('a[href^=\"tel:\"]'))
                            .map(a => (a.getAttribute('href')||'')
                                .replace(/^tel:/,'')
                                .split('?')[0]
                                .trim())
                            .filter(Boolean)
                    """
                )
                # Normalize: keep digits and leading +
                import re as _re
                def _norm(p):
                    p = p.strip()
                    # keep leading + and digits
                    m = _re.findall(r"^\\+?|\\d+", p)
                    # simple cleanup: remove spaces and dashes
                    return p.replace(" ", "").replace("-", "")
                phones = list(sorted(set([_norm(p) for p in (phones_text + phones_tel) if p])))
                direct["phones"] = phones[:100]
            if False and direct:
                # Apply 'only' filter if requested
                if "only" in lower_instr and ("email" in lower_instr or "mail" in lower_instr or "phone" in lower_instr or "tel" in lower_instr or "telefon" in lower_instr):
                    filtered = {}
                    if ("email" in lower_instr or "mail" in lower_instr) and "emails" in direct:
                        filtered["emails"] = direct["emails"]
                    if ("phone" in lower_instr or "tel" in lower_instr or "telefon" in lower_instr) and "phones" in direct:
                        filtered["phones"] = direct["phones"]
                    direct = filtered
                result["data"] = direct
                if run_logger:
                    run_logger.log_text("Direct extraction fast-path used:")
                    run_logger.log_code("json", json.dumps(result["data"], indent=2))
                await page.close()
                return result
        except Exception:
            pass
        
        # Main execution loop
        last_sig = None
        no_progress = 0
        stall_limit = 3
        for step in range(config.max_steps):
            result["steps"] = step + 1
            if run_logger:
                run_logger.log_heading(f"Step {step + 1}")
            
            # Take screenshot if visual mode
            if visual_mode:
                screenshot_path = await self._take_screenshot(page, step, target_dir=domain_dir)
                result["screenshots"].append(screenshot_path)
                if run_logger:
                    try:
                        run_logger.log_image(screenshot_path, alt=f"Step {step + 1} screenshot")
                    except Exception:
                        run_logger.log_text(f"Screenshot saved: {screenshot_path}")
                
                # Analyze visual state
                visual_analysis = await self.vision_analyzer.analyze(screenshot_path)
                
                # Check for CAPTCHA
                if captcha_solver and visual_analysis.get("has_captcha"):
                    await self._handle_captcha(page, screenshot_path)
            
            # Get page context
            page_context = await self._extract_page_context(page)
            # No-progress detection based on URL+title+text snippet signature
            try:
                sig = f"{page_context.get('url','')}|{page_context.get('title','')}|{(page_context.get('text','') or '')[:500]}"
                if last_sig is None:
                    last_sig = sig
                    no_progress = 0
                elif sig == last_sig:
                    no_progress += 1
                else:
                    last_sig = sig
                    no_progress = 0
                if no_progress >= stall_limit:
                    if run_logger:
                        run_logger.log_text(f"No progress detected for {stall_limit} consecutive steps. Stopping early.")
                    break
            except Exception:
                pass
            if run_logger:
                try:
                    run_logger.log_text("Page context snapshot (truncated):")
                    run_logger.log_code("json", json.dumps(page_context, indent=2)[:1500])
                except Exception:
                    pass
            # Heuristic product extraction when instruction requests products under a price
            try:
                if ("product" in lower_instr or "produkt" in lower_instr) and ("under" in lower_instr or "poniżej" in lower_instr or "below" in lower_instr or re.search(r"\b(<=?|mniej niż)\b", lower_instr)):
                    m = re.search(r"under\s*(\d+)|poniżej\s*(\d+)|below\s*(\d+)|mniej\s*niż\s*(\d+)", lower_instr)
                    thr = None
                    if m:
                        for g in m.groups():
                            if g:
                                thr = int(g)
                                break
                    # default threshold if not parsed
                    if thr is None:
                        thr = 150
                    # try to scroll to load more products
                    try:
                        await self._auto_scroll(page, steps=4, delay_ms=700)
                    except Exception:
                        pass
                    items = await page.evaluate(
                        r"""
                        (thr) => {
                          const asNumber = (t) => {
                            const m = (t||'').replace(/\s/g,'').match(/(\d+[\.,]\d{2}|\d+)(?=\s*(?:zł|PLN|\$|€)?)/i);
                            if (!m) return null;
                            return parseFloat(m[1].replace(',', '.'));
                          };
                          const cards = Array.from(document.querySelectorAll('article, li, div'));
                          const out = [];
                          for (const el of cards) {
                            const text = el.innerText || '';
                            const price = asNumber(text);
                            if (price == null || price > thr) continue;
                            let a = el.querySelector('a[href]');
                            const name = (a && a.innerText && a.innerText.trim()) || (text.split('\n')[0]||'').trim();
                            const url = a ? a.href : null;
                            if (!url || !name) continue;
                            out.push({ name, price, url });
                            if (out.length >= 50) break;
                          }
                          return out;
                        }
                        """,
                        thr
                    )
                    if isinstance(items, list) and items:
                        result["data"] = {"products": items}
                        if run_logger:
                            run_logger.log_text("Heuristic product extraction used:")
                            run_logger.log_code("json", json.dumps(result["data"], indent=2))
                        break
            except Exception:
                pass
            
            # Generate next action using LLM
            action = await self._generate_action(
                instruction=instruction,
                page_context=page_context,
                step=step,
                run_logger=run_logger
            )
            if run_logger:
                run_logger.log_text("Planned action:")
                run_logger.log_code("json", json.dumps(action))
            
            # Execute action
            if action["type"] == "complete":
                result["data"] = action.get("extracted_data", page_context)
                break
            
            await self._execute_action(page, action)
            if run_logger:
                run_logger.log_text(f"Executed action: {action.get('type')}")
            
            # Check for honeypots
            if await self._detect_honeypot(page):
                logger.warning("Honeypot detected, skipping field")
        
        # Fallback extraction if no result produced
        if result.get("data") is None:
            try:
                lower_instr = (instruction or "").lower()
                fallback = {}
                if "link" in lower_instr:
                    anchors = await page.evaluate("""
                        () => Array.from(document.querySelectorAll('a')).map(a => ({
                            text: (a.innerText||'').trim(),
                            href: a.href
                        }))
                    """)
                    fallback["links"] = anchors[:100]
                if "email" in lower_instr or "mail" in lower_instr:
                    text = await page.evaluate("() => document.body.innerText")
                    emails = list(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))
                    fallback["emails"] = emails[:100]
                if "phone" in lower_instr or "tel" in lower_instr or "telefon" in lower_instr:
                    text = await page.evaluate("() => document.body.innerText")
                    phones_text = list(set(re.findall(r"(?:\+\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d[\d\s-]{6,}\d", text)))
                    phones_tel = await page.evaluate(
                        """
                            () => Array.from(document.querySelectorAll('a[href^=\"tel:\"]'))
                                .map(a => (a.getAttribute('href')||'')
                                    .replace(/^tel:/,'')
                                    .split('?')[0]
                                    .trim())
                                .filter(Boolean)
                        """
                    )
                    def _norm(p: str) -> str:
                        return p.replace(" ", "").replace("-", "")
                    phones = list(sorted(set([_norm(p) for p in (phones_text + phones_tel) if p])))
                    fallback["phones"] = phones[:100]
                if not fallback:
                    ctx = await self._extract_page_context(page)
                    fallback = {"title": ctx.get("title"), "url": ctx.get("url")}
                result["data"] = fallback
                if run_logger:
                    run_logger.log_text("Fallback extraction used:")
                    run_logger.log_code("json", json.dumps(result["data"], indent=2))
            except Exception as _:
                pass
        # Final result filter for 'only email/phone' instructions
        try:
            if "only" in lower_instr and ("email" in lower_instr or "mail" in lower_instr or "phone" in lower_instr or "tel" in lower_instr or "telefon" in lower_instr):
                data = result.get("data")
                if isinstance(data, dict):
                    filtered = {}
                    if ("email" in lower_instr or "mail" in lower_instr) and "emails" in data:
                        filtered["emails"] = data["emails"]
                    if ("phone" in lower_instr or "tel" in lower_instr or "telefon" in lower_instr) and "phones" in data:
                        filtered["phones"] = data["phones"]
                    result["data"] = filtered
        except Exception:
            pass
        await page.close()
        return result
    
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
        context_str = json.dumps(page_context, indent=2)[:3000]
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

        def _strip_fences(s: str) -> str:
            s = s.strip()
            if s.startswith("```"):
                s = s.split("\n", 1)[1] if "\n" in s else s
                if s.rstrip().endswith("```"):
                    s = s.rsplit("```", 1)[0]
            return s.strip()

        raw = _strip_fences(text)
        # Try direct JSON
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
        # Scan for any balanced JSON object in the text
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
                    await page.evaluate("(s)=>{ const el=document.querySelector(s); if(el) el.click(); }", str(action.get("selector")))
                except Exception:
                    pass
        elif action_type == "fill":
            try:
                sel = str(action.get("selector"))
                val = str(action.get("value", ""))
                loc = page.locator(sel)
                await loc.first.wait_for(state="visible", timeout=5000)
                await loc.first.fill(val)
                # Fire input/blur to trigger client-side validation
                try:
                    await page.evaluate("(s) => { const el=document.querySelector(s); if(!el) return; try{ el.dispatchEvent(new Event('input', {bubbles:true})); }catch(e){} try{ el.blur(); }catch(e){} }", sel)
                except Exception:
                    pass
            except Exception:
                pass
            try:
                await page.wait_for_timeout(150 + int(random.random()*350))
            except Exception:
                pass
        elif action_type == "scroll":
            dy = 300 + int(random.random()*700)
            try:
                await page.mouse.wheel(0, dy)
            except Exception:
                await page.evaluate(f"window.scrollBy(0, {dy})")
            await page.wait_for_timeout(500 + int(random.random()*800))
        elif action_type == "wait":
            await page.wait_for_timeout(800 + int(random.random()*1200))
    
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
            txt = await page.evaluate("() => (document.body && document.body.innerText || '').slice(0, 4000).toLowerCase()")
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
            names = [
                "Akceptuj", "Zgadzam się", "Accept", "I agree"
            ]
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

# ============================================================================
# Vision Analysis
# ============================================================================

class VisionAnalyzer:
    """Visual analysis using CV and OCR"""
    
    async def analyze(self, image_path: str) -> Dict:
        """Analyze screenshot for elements"""
        img = cv2.imread(image_path)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect buttons/forms using edge detection
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Check for CAPTCHA patterns
        has_captcha = self._detect_captcha_pattern(img)
        
        return {
            "has_captcha": has_captcha,
            "num_forms": len([c for c in contours if cv2.contourArea(c) > 5000]),
            "has_images": self._has_distorted_text(gray)
        }
    
    def _detect_captcha_pattern(self, img) -> bool:
        """Detect common CAPTCHA patterns"""
        # Look for distorted text patterns
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        # Check for noise patterns common in CAPTCHAs
        kernel = np.ones((2,2), np.uint8)
        erosion = cv2.erode(thresh, kernel, iterations=1)
        dilation = cv2.dilate(erosion, kernel, iterations=1)
        
        diff = cv2.absdiff(thresh, dilation)
        noise_level = np.sum(diff) / (img.shape[0] * img.shape[1])
        
        return noise_level > 30  # Threshold for CAPTCHA detection
    
    def _has_distorted_text(self, gray_img) -> bool:
        """Check for distorted text patterns"""
        # Apply FFT to detect periodic noise
        f_transform = np.fft.fft2(gray_img)
        f_shift = np.fft.fftshift(f_transform)
        magnitude_spectrum = np.abs(f_shift)
        
        # Check for high frequency components (noise)
        center = tuple(np.array(magnitude_spectrum.shape) // 2)
        high_freq = magnitude_spectrum[center[0]-10:center[0]+10, center[1]-10:center[1]+10]
        
        return np.mean(high_freq) > 100

# ============================================================================
# CAPTCHA Solver
# ============================================================================

class CaptchaSolver:
    """CAPTCHA solving integration"""
    
    def __init__(self):
        self.use_2captcha = os.getenv("CAPTCHA_API_KEY") is not None
        self.api_key = os.getenv("CAPTCHA_API_KEY", "")
    
    async def solve(self, image_path: str) -> Optional[str]:
        """Solve CAPTCHA from image"""
        if not self.use_2captcha:
            # Try local OCR first
            return await self._solve_local(image_path)
        
        # Use 2captcha service
        return await self._solve_2captcha(image_path)
    
    async def _solve_local(self, image_path: str) -> Optional[str]:
        """Local CAPTCHA solving using OCR"""
        try:
            import pytesseract
            
            # Preprocess image
            img = Image.open(image_path)
            img = img.convert('L')  # Grayscale
            
            # Apply filters to improve OCR
            img = img.point(lambda p: p > 128 and 255)
            
            # OCR
            text = pytesseract.image_to_string(img, config='--psm 8')
            return text.strip()
        except:
            return None
    
    async def _solve_2captcha(self, image_path: str) -> Optional[str]:
        """Solve using 2captcha API"""
        async with aiohttp.ClientSession() as session:
            # Upload image
            with open(image_path, 'rb') as f:
                data = {
                    'key': self.api_key,
                    'method': 'post'
                }
                files = {'file': f}
                
                async with session.post(
                    'http://2captcha.com/in.php',
                    data=data,
                    files=files
                ) as resp:
                    result = await resp.text()
                    if 'OK' in result:
                        captcha_id = result.split('|')[1]
                        
                        # Poll for result
                        await asyncio.sleep(20)
                        
                        async with session.get(
                            f'http://2captcha.com/res.php?key={self.api_key}&action=get&id={captcha_id}'
                        ) as resp2:
                            result = await resp2.text()
                            if 'OK' in result:
                                return result.split('|')[1]
        return None

# ============================================================================
# Stealth Configuration
# ============================================================================

class StealthConfig:
    """Anti-detection configuration"""
    
    def get_chrome_args(self) -> List[str]:
        """Get stealth Chrome arguments"""
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
            '--user-agent=' + self.get_user_agent()
        ]
    
    def get_user_agent(self) -> str:
        """Get realistic user agent"""
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    
    async def apply_to_context(self, context):
        """Apply stealth patches to browser context"""
        await context.add_init_script("""
            // Remove webdriver flag
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Override chrome detection
            window.chrome = {
                runtime: {}
            };
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

# ============================================================================
# BrowserlessContext Wrapper
# ============================================================================

class BrowserlessContext:
    """Wrapper for Browserless WebSocket connection"""
    
    def __init__(self, websocket):
        self.ws = websocket
    
    async def new_page(self):
        """Create new page via Browserless"""
        # Send BQL query to create page
        await self.ws.send(json.dumps({
            "type": "newPage",
            "stealth": True
        }))
        # Return page wrapper
        return BrowserlessPage(self.ws)
    
    async def close(self):
        """Close connection"""
        await self.ws.close()

class BrowserlessPage:
    """Browserless page wrapper"""
    
    def __init__(self, websocket):
        self.ws = websocket
    
    async def goto(self, url: str):
        """Navigate to URL"""
        await self.ws.send(json.dumps({
            "type": "goto",
            "url": url
        }))
    
    async def click(self, selector: str):
        """Click element"""
        await self.ws.send(json.dumps({
            "type": "click",
            "selector": selector
        }))
    
    async def fill(self, selector: str, value: str):
        """Fill input field"""
        await self.ws.send(json.dumps({
            "type": "fill",
            "selector": selector,
            "value": value
        }))
    
    async def screenshot(self, path: str):
        """Take screenshot"""
        await self.ws.send(json.dumps({
            "type": "screenshot"
        }))
        # Wait for base64 response
        response = await self.ws.recv()
        data = json.loads(response)
        
        # Save to file
        with open(path, 'wb') as f:
            f.write(base64.b64decode(data['screenshot']))
    
    async def evaluate(self, script: str):
        """Execute JavaScript"""
        await self.ws.send(json.dumps({
            "type": "evaluate",
            "script": script
        }))
        response = await self.ws.recv()
        return json.loads(response).get('result')
    
    async def close(self):
        """Close page"""
        await self.ws.send(json.dumps({
            "type": "closePage"
        }))

# ============================================================================
# Flask API Endpoints
# ============================================================================

executor = CurllmExecutor()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "model": config.ollama_model,
        "ollama_host": config.ollama_host,
        "version": "1.0.0"
    })

@app.route('/api/execute', methods=['POST'])
def execute():
    """Main execution endpoint"""
    data = request.get_json()
    
    # Extract parameters
    instruction = data.get('data', '')
    url = data.get('url')
    visual_mode = data.get('visual_mode', False)
    stealth_mode = data.get('stealth_mode', False)
    captcha_solver = data.get('captcha_solver', False)
    use_bql = data.get('use_bql', False)
    headers = data.get('headers', {})
    
    # Run async task in a fresh event loop per request to avoid loop state issues
    def _run_in_new_loop():
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                executor.execute_workflow(
                    instruction=instruction,
                    url=url,
                    visual_mode=visual_mode,
                    stealth_mode=stealth_mode,
                    captcha_solver=captcha_solver,
                    use_bql=use_bql,
                    headers=headers
                )
            )
        finally:
            try:
                loop.run_until_complete(asyncio.sleep(0))
            except Exception:
                pass
            loop.close()
            try:
                asyncio.set_event_loop(asyncio.new_event_loop())
            except Exception:
                pass

    result = _run_in_new_loop()
    
    return jsonify(result)

@app.route('/api/models', methods=['GET'])
def list_models():
    """List available Ollama models"""
    try:
        import requests
        response = requests.get(f"{config.ollama_host}/api/tags")
        return jsonify(response.json())
    except:
        return jsonify({"error": "Failed to fetch models"}), 500

@app.route('/api/screenshot/<path:filename>', methods=['GET'])
def get_screenshot(filename):
    """Serve screenshot files"""
    from flask import send_file
    filepath = config.screenshot_dir / filename
    if filepath.exists():
        return send_file(str(filepath), mimetype='image/png')
    return jsonify({"error": "Screenshot not found"}), 404

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    try:
        from curllm_core.server import run_server as _run_server
        _run_server()
    except Exception:
        # Fallback to legacy in-file server start if package import fails
        import requests
        try:
            requests.get(f"{config.ollama_host}/api/tags")
            logger.info(f"✓ Connected to Ollama at {config.ollama_host}")
        except Exception:
            logger.warning(f"✗ Cannot connect to Ollama at {config.ollama_host}")
            logger.warning("  The API server will start, but requests may fail until Ollama is running (run: 'ollama serve').")
        logger.info(f"Starting curllm API server on port {config.api_port}...")
        logger.info(f"Model: {config.ollama_model}")
        logger.info(f"Visual mode: Available")
        logger.info(f"Stealth mode: Available")
        logger.info(f"CAPTCHA solver: {'Enabled' if os.getenv('CAPTCHA_API_KEY') else 'Local OCR only'}")
        app.run(host='0.0.0.0', port=config.api_port, debug=False, use_reloader=False)
