from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse
from pathlib import Path

from .config import config
from .page_utils import auto_scroll as _auto_scroll, accept_cookies as _accept_cookies, is_block_page as _is_block_page
from .human_verify import handle_human_verification
from .captcha_widget import handle_widget_captcha as _handle_widget_captcha
from .slider_plugin import try_external_slider_solver
from .captcha_slider import attempt_slider_challenge
from .diagnostics import diagnose_url_issue
from .screenshots import take_screenshot


async def open_page_with_prechecks(
    agent,
    url: Optional[str],
    instruction: str,
    stealth_mode: bool,
    captcha_solver: bool,
    runtime: Dict[str, Any],
    run_logger,
    result: Dict[str, Any],
    lower_instr: str,
    setup_browser_fn,
    captcha_solver_instance,
    build_rerun_curl_fn,
) -> Tuple[Any, Path, bool, Optional[Dict[str, Any]]]:
    if url:
        page = await agent.browser.new_page()
        try:
            await page.goto(url)
            try:
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_load_state("networkidle")
            except Exception:
                pass
        except Exception as e:
            # Diagnose URL issues and return early with structured error info
            diag = diagnose_url_issue(url)
            if run_logger:
                run_logger.log_kv("navigation_error", str(e))
                try:
                    import json as _json
                    run_logger.log_code("json", _json.dumps({"diagnostics": diag}, ensure_ascii=False, indent=2)[:2000])
                except Exception:
                    pass
            result["data"] = {
                "error": {
                    "type": "navigation_error",
                    "message": str(e),
                    "diagnostics": diag,
                }
            }
            # Suggest retry with http if https handshake failed but HTTP reachable
            try:
                host = urlparse(url).hostname or ""
                if isinstance(diag, dict):
                    https = diag.get("https", {}) or {}
                    http_probe = diag.get("http_probe", {}) or {}
                    if (https.get("handshake_ok") is False) and http_probe.get("status") in (200, 301, 302, 303, 307, 308):
                        http_url = f"http://{host}/"
                        cmd = build_rerun_curl_fn(instruction, http_url, {"include_dom_html": True}, top_level={"url": http_url})
                        result["meta"]["hints"].append("HTTPS handshake failed but HTTP is reachable. Try HTTP.")
                        if cmd:
                            result["meta"]["suggested_commands"].append(cmd)
            except Exception:
                pass
            return page, config.screenshot_dir, stealth_mode, result
        try:
            hv = await handle_human_verification(page, run_logger)
            run_logger.log_kv("human_verify_clicked_on_nav", str(bool(hv)))
        except Exception as e:
            run_logger.log_kv("human_verify_on_nav_error", str(e))
        if runtime.get("scroll_load"):
            try:
                await _auto_scroll(page, steps=4, delay_ms=600)
            except Exception:
                pass
        if captcha_solver:
            try:
                solved = await _handle_widget_captcha(page, current_url=url, solver=captcha_solver_instance, run_logger=run_logger)
                run_logger.log_kv("widget_captcha_on_nav", str(bool(solved)))
            except Exception as e:
                run_logger.log_kv("widget_captcha_on_nav_error", str(e))
        if bool(runtime.get("use_external_slider_solver")):
            try:
                ext = await try_external_slider_solver(page, run_logger)
                if ext is not None:
                    run_logger.log_kv("ext_slider_solver_on_nav", str(bool(ext)))
            except Exception as e:
                run_logger.log_kv("ext_slider_solver_on_nav_error", str(e))
        try:
            slid = await attempt_slider_challenge(page, run_logger)
            if slid:
                run_logger.log_kv("slider_attempt_on_nav", "True")
        except Exception as e:
            run_logger.log_kv("slider_attempt_on_nav_error", str(e))
    else:
        page = await agent.browser.new_page()
    try:
        if await _is_block_page(page) and not stealth_mode:
            if run_logger:
                run_logger.log_text("Block page detected; retrying with stealth mode...")
            try:
                # Suggest rerun with stealth mode
                params = {
                    "include_dom_html": True,
                    "scroll_load": True,
                }
                cmd = build_rerun_curl_fn(instruction, url or "", params, top_level={"stealth_mode": True, "url": url or ""})
                result["meta"]["hints"].append("Block page detected. Retry with stealth_mode=true or use a proxy.")
                result["meta"]["suggested_commands"].append(cmd)
            except Exception:
                pass
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
            new_ctx = await setup_browser_fn(True, host, headers=None)
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
            shot_path = await take_screenshot(page, 0, target_dir=domain_dir)
            result.setdefault("screenshots", []).append(shot_path)
            if run_logger:
                try:
                    run_logger.log_image(shot_path, alt="Initial screenshot")
                except Exception:
                    run_logger.log_text(f"Initial screenshot saved: {shot_path}")
            result["data"] = {"screenshot_saved": shot_path}
            if not ("extract" in lower_instr or "product" in lower_instr or "produkt" in lower_instr):
                return page, domain_dir, stealth_mode, result
    except Exception:
        pass
    try:
        await _accept_cookies(page)
        run_logger.log_kv("accept_cookies", "attempted")
    except Exception as e:
        run_logger.log_kv("accept_cookies_error", str(e))
    return page, domain_dir, stealth_mode, None
