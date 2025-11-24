from typing import Any, Dict, Optional
from .human_verify import handle_human_verification, looks_like_human_verify_text
from .page_utils import auto_scroll as _auto_scroll, accept_cookies as _accept_cookies
from .slider_plugin import try_external_slider_solver
from .captcha_slider import attempt_slider_challenge


async def remediate_if_empty(executor, page, runtime: Dict[str, Any], run_logger, page_context: Dict[str, Any]) -> Dict[str, Any]:
    inter_len = len(page_context.get("interactive", []) or [])
    dom_len = len(page_context.get("dom_preview", "") or "")
    ifr_len = len(page_context.get("iframes", []) or [])
    head_len = len(page_context.get("headings", []) or [])
    artc_len = len(page_context.get("article_candidates", []) or [])
    try:
        hv_possible = looks_like_human_verify_text(page_context.get("text", ""))
    except Exception:
        hv_possible = False
    page_context.setdefault("status", {})
    page_context["status"].update({
        "interactive_count": inter_len,
        "dom_preview_len": dom_len,
        "iframes_count": ifr_len,
        "headings_count": head_len,
        "article_candidates_count": artc_len,
        "human_verify_possible": bool(hv_possible),
    })
    # remediation branch
    if inter_len == 0 and dom_len == 0 and bool(runtime.get("include_dom_html")):
        if run_logger:
            run_logger.log_text("DOM snapshot empty; running remediation: human_verify -> accept_cookies -> small scroll -> re-extract")
        try:
            hv2 = await handle_human_verification(page, run_logger)
            if run_logger:
                run_logger.log_kv("human_verify_remediation", str(bool(hv2)))
        except Exception as e:
            if run_logger:
                run_logger.log_kv("human_verify_remediation_error", str(e))
        try:
            await _accept_cookies(page)
        except Exception:
            pass
        try:
            await _auto_scroll(page, steps=1, delay_ms=300)
        except Exception:
            pass
        page_context = await executor._extract_page_context(
            page,
            include_dom=True,
            dom_max_chars=int(runtime.get("dom_max_chars", 20000) or 20000),
        )
        inter_len2 = len(page_context.get("interactive", []) or [])
        dom_len2 = len(page_context.get("dom_preview", "") or "")
        ifr_len2 = len(page_context.get("iframes", []) or [])
        try:
            hv_possible2 = looks_like_human_verify_text(page_context.get("text", ""))
        except Exception:
            hv_possible2 = False
        page_context.setdefault("status", {})
        page_context["status"].update({
            "interactive_count": inter_len2,
            "dom_preview_len": dom_len2,
            "iframes_count": ifr_len2,
            "human_verify_possible": bool(hv_possible2),
            "remediated": True,
        })
        if run_logger:
            run_logger.log_kv("interactive_count_after_remediate", str(inter_len2))
            run_logger.log_kv("dom_preview_len_after_remediate", str(dom_len2))
            run_logger.log_kv("iframes_count_after_remediate", str(ifr_len2))
    return page_context


async def maybe_solve_slider_block(page, run_logger, runtime: Dict[str, Any], page_context: Dict[str, Any]) -> None:
    try:
        inter_len = len(page_context.get("interactive", []) or [])
        dom_len = len(page_context.get("dom_preview", "") or "")
        ifr_len = len(page_context.get("iframes", []) or [])
        if inter_len == 0 and dom_len < 300 and ifr_len > 0:
            if bool(runtime.get("use_external_slider_solver")):
                try:
                    ext2 = await try_external_slider_solver(page, run_logger)
                    if ext2 is not None and run_logger:
                        run_logger.log_kv("ext_slider_solver_on_step", str(bool(ext2)))
                except Exception as e:
                    if run_logger:
                        run_logger.log_kv("ext_slider_solver_on_step_error", str(e))
            try:
                slid_step = await attempt_slider_challenge(page, run_logger)
                if slid_step and run_logger:
                    run_logger.log_kv("slider_attempt_on_step", "True")
            except Exception as e:
                if run_logger:
                    run_logger.log_kv("slider_attempt_on_step_error", str(e))
    except Exception:
        pass
