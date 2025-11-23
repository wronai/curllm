#!/usr/bin/env python3
import asyncio
import json
import logging
import os
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import aiohttp

# optional browser_use agent
try:
    from browser_use import Agent as BrowserUseAgent  # type: ignore
except Exception:
    BrowserUseAgent = None

class LocalAgent:
    def __init__(self, browser, llm, max_steps, visual_mode, task=None):
        self.browser = browser
        self.llm = llm
        self.max_steps = max_steps
        self.visual_mode = visual_mode

from .config import config
from .logger import RunLogger
from .llm import SimpleOllama
from .vision import VisionAnalyzer
from .captcha import CaptchaSolver
from .stealth import StealthConfig
from .browserless import BrowserlessContext
from .runtime import parse_runtime_from_instruction
from .headers import normalize_headers
from .browser_setup import setup_browser
from .page_context import extract_page_context
from .actions import execute_action
from .human_verify import handle_human_verification, looks_like_human_verify_text

logger = logging.getLogger(__name__)

class CurllmExecutor:
    """Main browser automation executor with LLM support"""
    def __init__(self):
        self.llm = self._setup_llm()
        self.vision_analyzer = VisionAnalyzer()
        self.captcha_solver = CaptchaSolver()
        self.stealth_config = StealthConfig()

    def _setup_llm(self) -> Any:
        backend = os.getenv("CURLLM_LLM_BACKEND", "simple").lower()
        if backend == "langchain":
            try:
                from langchain_ollama import OllamaLLM  # type: ignore
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
        headers: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        # Parse optional runtime params embedded in JSON instruction
        instruction, runtime = parse_runtime_from_instruction(instruction)
        run_logger = RunLogger(instruction=instruction, url=url)
        run_logger.log_heading(f"curllm run: {datetime.now().isoformat()}")
        run_logger.log_kv("Model", config.ollama_model)
        run_logger.log_kv("Ollama Host", config.ollama_host)
        run_logger.log_kv("Visual Mode", str(visual_mode))
        run_logger.log_kv("Stealth Mode", str(stealth_mode))
        run_logger.log_kv("Use BQL", str(use_bql))

        browser_context = None
        try:
            if use_bql:
                instruction = self._parse_bql(instruction)
                run_logger.log_text("BQL parsed instruction:")
                run_logger.log_code("text", instruction)

            host = urlparse(url).hostname if url else None
            if host and any(h in host for h in ["allegro.pl", "allegro.com"]):
                stealth_mode = True
            # Normalize headers for Playwright context
            norm_headers = normalize_headers(headers)
            browser_context = await self._setup_browser(stealth_mode, storage_key=host, headers=norm_headers)
            run_logger.log_text("Browser context initialized.")

            agent = self._create_agent(
                browser_context=browser_context,
                instruction=instruction,
                visual_mode=visual_mode,
            )

            result = await self._execute_task(
                agent=agent,
                instruction=instruction,
                url=url,
                visual_mode=visual_mode,
                stealth_mode=stealth_mode,
                captcha_solver=captcha_solver,
                run_logger=run_logger,
                runtime=runtime,
            )

            if browser_context is not None:
                try:
                    try:
                        storage_path = getattr(browser_context, "_curllm_storage_path", None)
                        if storage_path:
                            await browser_context.storage_state(path=storage_path)
                    except Exception:
                        logger.warning("Unable to persist storage state", exc_info=True)
                    await browser_context.close()
                except Exception as e:
                    logger.warning(f"Error during browser close: {e}")
                try:
                    br = getattr(browser_context, "_curllm_browser", None)
                    if br is not None:
                        await br.close()
                    pw = getattr(browser_context, "_curllm_playwright", None)
                    if pw is not None:
                        await pw.stop()
                except Exception as e:
                    logger.warning(f"Error closing Playwright resources: {e}")

            res = {
                "success": True,
                "result": result.get("data"),
                "steps_taken": result.get("steps", 0),
                "screenshots": result.get("screenshots", []),
                "timestamp": datetime.now().isoformat(),
                "run_log": str(run_logger.path),
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
                except Exception as e2:
                    logger.warning(f"Error closing Playwright resources after failure: {e2}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "run_log": str(run_logger.path),
            }

    def _create_agent(self, browser_context, instruction: str, visual_mode: bool):
        if BrowserUseAgent is not None:
            try:
                import inspect
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

    async def _setup_browser(self, stealth_mode: bool, storage_key: Optional[str] = None, headers: Optional[Dict[str, str]] = None):
        return await setup_browser(
            use_browserless=config.use_browserless,
            browserless_url=config.browserless_url,
            stealth_mode=stealth_mode,
            storage_key=storage_key,
            headers=headers,
            stealth_config=self.stealth_config,
            config=config,
        )

    async def _setup_browserless(self):
        import websockets  # lazy import
        ws = await websockets.connect(config.browserless_url)
        return BrowserlessContext(ws)

    async def _execute_task(
        self,
        agent,
        instruction: str,
        url: Optional[str],
        visual_mode: bool,
        stealth_mode: bool,
        captcha_solver: bool,
        run_logger: RunLogger,
        runtime: Dict[str, Any],
    ) -> Dict:
        result: Dict[str, Any] = {"data": None, "steps": 0, "screenshots": []}
        lower_instr = (instruction or "").lower()
        if url:
            page = await agent.browser.new_page()
            await page.goto(url)
            try:
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_load_state("networkidle")
            except Exception:
                pass
            try:
                await handle_human_verification(page, run_logger)
            except Exception:
                pass
            # Optional initial scroll to load content
            if runtime.get("scroll_load"):
                try:
                    await self._auto_scroll(page, steps=4, delay_ms=600)
                except Exception:
                    pass
            # Attempt widget CAPTCHA solving right after navigation if enabled
            if captcha_solver:
                try:
                    await self._handle_widget_captcha(page, current_url=url, run_logger=run_logger)
                except Exception:
                    pass
        else:
            page = await agent.browser.new_page()
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
        domain_dir = config.screenshot_dir
        try:
            host = await page.evaluate("() => window.location.hostname")
            if host:
                domain_dir = config.screenshot_dir / host
                domain_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            try:
                if url:
                    host = urlparse(url).hostname
                    if host:
                        domain_dir = config.screenshot_dir / host
                        domain_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
        try:
            if ("screenshot" in lower_instr) or ("zrzut" in lower_instr):
                shot_path = await self._take_screenshot(page, 0, target_dir=domain_dir)
                result["screenshots"].append(shot_path)
                if run_logger:
                    run_logger.log_text(f"Initial screenshot saved: {shot_path}")
                result["data"] = {"screenshot_saved": shot_path}
                if not ("extract" in lower_instr or "product" in lower_instr or "produkt" in lower_instr):
                    await page.close()
                    return result
        except Exception:
            pass
        try:
            await self._accept_cookies(page)
        except Exception:
            pass
        try:
            lower_instr = (instruction or "").lower()
            generic_triggers = ("extract" in lower_instr or "scrape" in lower_instr)
            specific_keywords = [
                "link",
                "email",
                "mail",
                "phone",
                "tel",
                "telefon",
                "product",
                "produkt",
                "form",
                "screenshot",
                "captcha",
                "bql",
            ]
            if generic_triggers and not any(k in lower_instr for k in specific_keywords):
                ctx = await self._extract_page_context(page)
                try:
                    text = await page.evaluate("() => document.body.innerText")
                except Exception:
                    text = ""
                anchors = await page.evaluate(
                    """
                        () => Array.from(document.querySelectorAll('a')).map(a => ({
                            text: (a.innerText||'').trim(),
                            href: a.href
                        }))
                    """
                )
                emails = list(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))
                phones = list(
                    set(re.findall(r"(?:\+\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d[\d\s-]{6,}\d", text))
                )
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
        try:
            lower_instr = (instruction or "").lower()
            direct = {}
            if "link" in lower_instr and not (
                ("only" in lower_instr)
                and ("email" in lower_instr or "mail" in lower_instr or "phone" in lower_instr or "tel" in lower_instr or "telefon" in lower_instr)
            ):
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
                def _norm(p: str) -> str:
                    return p.replace(" ", "").replace("-", "")
                phones = list(sorted(set([_norm(p) for p in (phones_text + phones_tel) if p])))
                direct["phones"] = phones[:100]
            if direct:
                if "only" in lower_instr and (
                    "email" in lower_instr or "mail" in lower_instr or "phone" in lower_instr or "tel" in lower_instr or "telefon" in lower_instr
                ):
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
        last_sig = None
        no_progress = 0
        stall_limit = 3
        for step in range(config.max_steps):
            result["steps"] = step + 1
            if run_logger:
                run_logger.log_heading(f"Step {step + 1}")
            if visual_mode:
                screenshot_path = await self._take_screenshot(page, step, target_dir=domain_dir)
                result["screenshots"].append(screenshot_path)
                visual_analysis = await self.vision_analyzer.analyze(screenshot_path)
                if captcha_solver and visual_analysis.get("has_captcha"):
                    await handle_captcha(page, screenshot_path, run_logger)
            # Try handle human verification banners/buttons each step
            try:
                await handle_human_verification(page, run_logger)
            except Exception:
                pass
            # Try widget CAPTCHA solving per step if enabled
            if captcha_solver:
                try:
                    await handle_widget_captcha(page, current_url=url, run_logger=run_logger)
                    # Try to obtain current URL from page if available
                    cur_url = None
                    try:
                        cur_url = await page.evaluate("() => window.location.href")
                    except Exception:
                        cur_url = url
                    await self._handle_widget_captcha(page, current_url=cur_url, run_logger=run_logger)
                except Exception:
                    pass
            page_context = await self._extract_page_context(
                page,
                include_dom=bool(runtime.get("include_dom_html")),
                dom_max_chars=int(runtime.get("dom_max_chars", 20000) or 20000),
            )
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
            try:
                if ("product" in lower_instr or "produkt" in lower_instr) and (
                    "under" in lower_instr or "poniżej" in lower_instr or "below" in lower_instr or re.search(r"\b(<=?|mniej niż)\b", lower_instr)
                ):
                    m = re.search(r"under\s*(\d+)|poniżej\s*(\d+)|below\s*(\d+)|mniej\s*niż\s*(\d+)", lower_instr)
                    thr = None
                    if m:
                        for g in m.groups():
                            if g:
                                thr = int(g)
                                break
                    if thr is None:
                        thr = 150
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
                        thr,
                    )
                    if isinstance(items, list) and items:
                        result["data"] = {"products": items}
                        if run_logger:
                            run_logger.log_text("Heuristic product extraction used:")
                            run_logger.log_code("json", json.dumps(result["data"], indent=2))
                        break
            except Exception:
                pass
            action = await self._generate_action(
                instruction=instruction,
                page_context=page_context,
                step=step,
                run_logger=run_logger,
            )
            if run_logger:
                run_logger.log_text("Planned action:")
                run_logger.log_code("json", json.dumps(action))
            if action.get("type") == "complete":
                result["data"] = action.get("extracted_data", page_context)
                break
            # Respect no_click runtime flag
            if runtime.get("no_click") and str(action.get("type")) == "click":
                if run_logger:
                    run_logger.log_text("Skipping click due to no_click=true")
            else:
                await self._execute_action(page, action, runtime)
            if run_logger:
                run_logger.log_text(f"Executed action: {action.get('type')}")
            if await self._detect_honeypot(page):
                logger.warning("Honeypot detected, skipping field")
        if result.get("data") is None:
            try:
                lower_instr = (instruction or "").lower()
                fallback: Dict[str, Any] = {}
                if "link" in lower_instr:
                    anchors = await page.evaluate(
                        """
                        () => Array.from(document.querySelectorAll('a')).map(a => ({
                            text: (a.innerText||'').trim(),
                            href: a.href
                        }))
                        """
                    )
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
                    def _norm2(p: str) -> str:
                        return p.replace(" ", "").replace("-", "")
                    phones = list(sorted(set([_norm2(p) for p in (phones_text + phones_tel) if p])))
                    fallback["phones"] = phones[:100]
                if not fallback:
                    ctx = await self._extract_page_context(page)
                    fallback = {"title": ctx.get("title"), "url": ctx.get("url")}
                result["data"] = fallback
                if run_logger:
                    run_logger.log_text("Fallback extraction used:")
                    run_logger.log_code("json", json.dumps(result["data"], indent=2))
            except Exception:
                pass
        try:
            if "only" in lower_instr and (
                "email" in lower_instr or "mail" in lower_instr or "phone" in lower_instr or "tel" in lower_instr or "telefon" in lower_instr
            ):
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
        tdir = Path(target_dir) if target_dir else config.screenshot_dir
        tdir.mkdir(parents=True, exist_ok=True)
        filename = tdir / f"step_{step}_{datetime.now().timestamp()}.png"
        await page.screenshot(path=str(filename))
        return str(filename)

    async def _extract_page_context(self, page, include_dom: bool = False, dom_max_chars: int = 20000) -> Dict:
        return await extract_page_context(page, include_dom=include_dom, dom_max_chars=dom_max_chars)

    async def _generate_action(self, instruction: str, page_context: Dict, step: int, run_logger: RunLogger | None = None) -> Dict:
        context_str = json.dumps(page_context, indent=2)[:3000]
        prompt_text = (
            "You are a browser automation expert. Analyze the current page and determine the next action.\n\n"
            f"Instruction: {instruction}\n"
            f"Current Step: {step}\n"
            f"Page Context: {context_str}\n\n"
            "If 'interactive' or 'dom_preview' are present, prefer using selectors for existing elements.\n"
            "Generate a JSON action:\n"
            "{\n"
            "    \"type\": \"click|fill|scroll|wait|complete\",\n"
            "    \"selector\": \"CSS selector if applicable\",\n"
            "    \"value\": \"value to fill if applicable\",\n"
            "    \"waitFor\": \"optional selector to wait for\",\n"
            "    \"timeoutMs\": 8000\n"
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
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"type": "wait"}

    async def _execute_action(self, page, action: Dict, runtime: Dict[str, Any]):
        return await execute_action(page, action, runtime)

    # Backward-compat wrappers for tests
    def _looks_like_human_verify_text(self, txt: str) -> bool:  # noqa: N802
        return looks_like_human_verify_text(txt)

    async def _handle_human_verification(self, page, run_logger: RunLogger | None = None):  # noqa: N802
        return await handle_human_verification(page, run_logger)

    async def _detect_honeypot(self, page) -> bool:
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

    async def _is_block_page(self, page) -> bool:
        try:
            txt = await page.evaluate("() => (document.body && document.body.innerText || '').slice(0, 4000).toLowerCase()")
            markers = [
                "you have been blocked",
                "access denied",
                "robot",
                "are you human",
                "verify you are human",
                "potwierdź, że jesteś człowiekiem",
                "potwierdz, że jesteś człowiekiem",
                "potwierdzam",
            ]
            return any(m in txt for m in markers)
        except Exception:
            return False

    async def _accept_cookies(self, page):
        try:
            names = ["Akceptuj", "Zgadzam się", "Accept", "I agree"]
            for name in names:
                try:
                    btn = page.get_by_role("button", name=name)
                    if await btn.count() > 0:
                        await btn.first.click(timeout=1000)
                        return
                except Exception:
                    pass
            selectors = [
                'button:has-text("Akceptuj")',
                'button:has-text("Zgadzam się")',
                'button:has-text("Accept")',
                'button:has-text("I agree")',
                'button[aria-label*="accept" i]',
                '#onetrust-accept-btn-handler',
                '.cookie-accept', '.cookie-approve', '.cookies-accept',
                'button[mode="primary"]',
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
        for _ in range(steps):
            try:
                await page.evaluate("window.scrollBy(0, window.innerHeight);")
                await page.wait_for_timeout(delay_ms)
            except Exception:
                break

    async def _handle_captcha(self, page, screenshot_path: str):
        solution = await self.captcha_solver.solve(screenshot_path)
        if solution:
            await page.fill('input[name*="captcha"]', solution)

    def _parse_bql(self, query: str) -> str:
        if "query" in query and "{" in query:
            return f"Extract the following fields from the page: {query}"
        return query

    def _looks_like_human_verify_text(self, txt: str) -> bool:
        t = (txt or "").lower()
        patterns = [
            "potwierdź, że jesteś człowiekiem",
            "potwierdz, że jesteś człowiekiem",
            "potwierdzam",
            "jestem człowiekiem",
            "jestem czlowiekiem",
            "przejdź dalej",
            "przejdz dalej",
            "kontynuuj",
            "confirm you are human",
            "verify you are human",
        ]
        return any(p in t for p in patterns)

    async def _handle_human_verification(self, page, run_logger: RunLogger | None = None) -> bool:
        try:
            txt = await page.evaluate("() => (document.body && document.body.innerText) || ''")
        except Exception:
            txt = ""
        if not self._looks_like_human_verify_text(txt):
            # Also check for presence of specific button text even if page text filter missed
            try:
                has_btn = await page.evaluate("() => !!Array.from(document.querySelectorAll('button, a, [role=button]')).find(el => (el.innerText||'').toLowerCase().includes('potwierdzam'))")
            except Exception:
                has_btn = False
            if not has_btn:
                return False
        # Try various strategies to click the confirmation button
        clicked = False
        try:
            btn = page.get_by_role("button", name=re.compile("potwierdzam|potwierdź|confirm|kontynuuj|przej(d|dz)\s+dalej|jestem", re.I))
            if await btn.count() > 0:
                await btn.first.click(timeout=1500)
                clicked = True
        except Exception:
            pass
        if not clicked:
            for sel in [
                'button:has-text("Potwierdzam")',
                'button:has-text("Potwierdź")',
                'button:has-text("Kontynuuj")',
                'button:has-text("Jestem człowiekiem")',
                'button:has-text("Jestem czlowiekiem")',
                'button:has-text("Przejdź dalej")',
                'button:has-text("Przejdz dalej")',
                'button[aria-label*="potwierd" i]',
                '[role="button"]:has-text("Potwierdzam")',
                '[role="button"]:has-text("Kontynuuj")',
                '[role="button"]:has-text("Jestem człowiekiem")',
            ]:
                try:
                    loc = page.locator(sel)
                    if await loc.count() > 0:
                        await loc.first.click(timeout=1500)
                        clicked = True
                        break
                except Exception:
                    continue
        if not clicked:
            try:
                # Last resort: evaluate and click first matching button by text
                await page.evaluate(
                    """
                    () => {
                      const el = Array.from(document.querySelectorAll('button, a, [role=button]'))
                        .find(e => {
                          const t=(e.innerText||'').toLowerCase();
                          return t.includes('potwierdzam') || t.includes('potwierdź') || t.includes('kontynuuj') || t.includes('jestem cz') || t.includes('przejdź dalej') || t.includes('przejdz dalej');
                        });
                      if (el) el.click();
                    }
                    """
                )
                clicked = True
            except Exception:
                pass
        if clicked:
            if run_logger:
                run_logger.log_text("Clicked human verification button (Potwierdzam)")
            # Give page a moment to transition
            try:
                await page.wait_for_load_state("networkidle")
            except Exception:
                try:
                    await page.wait_for_timeout(800)
                except Exception:
                    pass
        return clicked

    async def _handle_widget_captcha(self, page, current_url: Optional[str], run_logger: RunLogger | None = None) -> bool:
        """Detect common widget CAPTCHAs (reCAPTCHA/hCaptcha/Turnstile) and solve via 2captcha.
        Returns True if a token was obtained and injected.
        """
        # Find sitekey and type
        try:
            info = await page.evaluate(
                """
                () => {
                  const q = (sel) => document.querySelector(sel);
                  const byAttr = document.querySelector('[data-sitekey]');
                  const recaptchaEl = q('.g-recaptcha[data-sitekey], [class*="recaptcha"][data-sitekey]') || (byAttr && /recaptcha/i.test(byAttr.className) ? byAttr : null);
                  const hcaptchaEl = q('.h-captcha[data-sitekey]') || (byAttr && /hcaptcha/i.test(byAttr.className) ? byAttr : null);
                  const turnstileEl = q('.cf-turnstile[data-sitekey]') || (byAttr && /turnstile/i.test(byAttr.className) ? byAttr : null);
                  const getKey = (el) => el && (el.getAttribute('data-sitekey') || el.dataset.sitekey);
                  if (recaptchaEl) return {type: 'recaptcha', sitekey: getKey(recaptchaEl)};
                  if (hcaptchaEl) return {type: 'hcaptcha', sitekey: getKey(hcaptchaEl)};
                  if (turnstileEl) return {type: 'turnstile', sitekey: getKey(turnstileEl)};
                  // Try to infer from scripts
                  const scripts = Array.from(document.scripts).map(s => s.src||'');
                  if (scripts.some(s => /recaptcha\.google\.com|google\.com\/recaptcha/i.test(s))) return {type: 'recaptcha', sitekey: (q('[data-sitekey]')||{}).dataset?.sitekey || null};
                  if (scripts.some(s => /hcaptcha\.com/i.test(s))) return {type: 'hcaptcha', sitekey: (q('[data-sitekey]')||{}).dataset?.sitekey || null};
                  if (scripts.some(s => /challenges\.cloudflare\.com|turnstile/i.test(s))) return {type: 'turnstile', sitekey: (q('[data-sitekey]')||{}).dataset?.sitekey || null};
                  return null;
                }
                """
            )
        except Exception:
            info = None
        if not info or not isinstance(info, dict) or not info.get('sitekey') or not info.get('type'):
            return False
        wtype = str(info.get('type'))
        sitekey = str(info.get('sitekey'))
        if not self.captcha_solver or not getattr(self.captcha_solver, 'solve_sitekey', None):
            return False
        token = await self.captcha_solver.solve_sitekey(wtype, sitekey, current_url or '')
        if not token:
            return False
        # Inject token into expected response input(s)
        try:
            await page.evaluate(
                """
                (token) => {
                  const ensureInput = (name) => {
                    let el = document.querySelector('input[name="'+name+'"]');
                    if (!el) { el = document.createElement('input'); el.type='hidden'; el.name=name; document.body.appendChild(el); }
                    el.value = token;
                  };
                  // Common targets
                  ensureInput('g-recaptcha-response');
                  ensureInput('h-recaptcha-response');
                  ensureInput('hcaptcha-response');
                  ensureInput('cf-turnstile-response');
                  // Fire events to notify frameworks
                  ['g-recaptcha-response','h-recaptcha-response','hcaptcha-response','cf-turnstile-response'].forEach(n => {
                    const el = document.querySelector('input[name="'+n+'"]');
                    if (el) {
                      el.dispatchEvent(new Event('change', {bubbles: true}));
                      el.dispatchEvent(new Event('input', {bubbles: true}));
                    }
                  });
                }
                """,
                token,
            )
        except Exception:
            return False
        if run_logger:
            run_logger.log_text(f"Widget CAPTCHA solved via 2captcha ({wtype})")
        # Give page time to process token
        try:
            await page.wait_for_timeout(1000)
        except Exception:
            pass
        return True
