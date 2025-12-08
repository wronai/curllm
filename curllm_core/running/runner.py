from typing import Any, Dict, Optional
import json
import os
import logging
import time

logger = logging.getLogger(__name__)
LOG_PREVIEW_CHARS = int(os.getenv("CURLLM_LOG_PREVIEW_CHARS", "35000") or 35000)

from curllm_core.config import config
from curllm_core.extraction import (
    generic_fastpath,
    direct_fastpath,
    product_heuristics,
    fallback_extract,
    extract_articles_eval,
    validate_with_llm,
    extract_links_by_selectors,
    _extract_emails as _tool_extract_emails,
    _extract_phones as _tool_extract_phones,
    _extract_all_anchors as _tool_extract_all_anchors,
    _extract_anchors_filtered as _tool_extract_anchors_filtered,
    refine_instruction_llm,
)
from curllm_core.human_verify import handle_human_verification, looks_like_human_verify_text
from curllm_core.page_utils import auto_scroll as _auto_scroll, accept_cookies as _accept_cookies
from curllm_core.captcha_slider import attempt_slider_challenge
from curllm_core.slider_plugin import try_external_slider_solver
from curllm_core.result_store import previous_for_context as _previous_for_context
from curllm_core.tool_retry import ToolRetryManager
from curllm_core.task_runner_tools import execute_tool as _execute_tool
from curllm_core.task_runner_early import (
    smart_intent_check as _smart_intent_check,
    try_early_form_fill as _try_early_form_fill,
    try_early_articles as _try_early_articles,
    try_selector_links as _try_selector_links,
    try_fastpaths as _try_fastpaths,
    try_product_extraction as _try_product_extraction,
)
from curllm_core.task_runner_steps import (
    step_visual as _step_visual,
    step_page_context as _step_page_context,
    remediate_if_empty as _remediate_if_empty,
    progress_and_maybe_break as _progress_and_maybe_break,
)
from curllm_core.task_runner_fallback import (
    maybe_products_heuristics as _maybe_products_heuristics,
    maybe_articles_no_click as _maybe_articles_no_click,
    finalize_fallback as _finalize_fallback,
)


async def _planner_cycle(executor, instruction: str, page_context: Dict[str, Any], step: int, run_logger, runtime: Dict[str, Any], page, tool_history: list[Dict[str, Any]], domain_dir: Optional[str] = None, retry_manager=None):
    _t_gen = time.time()
    
    # Try hierarchical planner first (only for form-filling tasks)
    hierarchical_enabled = runtime.get("hierarchical_planner", True)
    if run_logger:
        run_logger.log_text(f"🔍 Checking hierarchical planner: enabled={hierarchical_enabled}, step={step}")
    
    if hierarchical_enabled and step == 1:  # Only on first step
        try:
            from .hierarchical_planner import hierarchical_plan, should_use_hierarchical
            
            # Smart bypass: check if hierarchical planner is worth the overhead
            if not should_use_hierarchical(instruction, page_context):
                if run_logger:
                    run_logger.log_text("✂️ Bypassing hierarchical planner (simple task detected)")
                # Fall through to standard planner
                action = await executor._generate_action(
                    instruction=instruction,
                    page_context=page_context,
                    step=step,
                    run_logger=run_logger,
                    runtime=runtime,
                )
            else:
                if run_logger:
                    run_logger.log_text("⚙️  Attempting hierarchical planner...")
                action = await hierarchical_plan(instruction, page_context, executor.llm, run_logger)
            if action is not None:
                # Hierarchical planner succeeded, use its action
                try:
                    run_logger.log_kv("fn:hierarchical_plan_ms", str(int((time.time() - _t_gen) * 1000)))
                except Exception:
                    pass
                if run_logger:
                    run_logger.log_text("✓ Hierarchical planner generated action")
            else:
                # Fall back to standard planner
                if run_logger:
                    run_logger.log_text("❌ Hierarchical planner returned None, falling back to standard planner")
                action = await executor._generate_action(
                    instruction=instruction,
                    page_context=page_context,
                    step=step,
                    run_logger=run_logger,
                    runtime=runtime,
                )
        except Exception as e:
            if run_logger:
                run_logger.log_text(f"Hierarchical planner failed: {e}, falling back to standard")
            action = await executor._generate_action(
                instruction=instruction,
                page_context=page_context,
                step=step,
                run_logger=run_logger,
                runtime=runtime,
            )
    else:
        action = await executor._generate_action(
            instruction=instruction,
            page_context=page_context,
            step=step,
            run_logger=run_logger,
            runtime=runtime,
        )
    try:
        run_logger.log_kv("fn:generate_action_ms", str(int((time.time() - _t_gen) * 1000)))
    except Exception:
        pass
    # FALLBACK: Fix LLM mistake - type="fill" or type="form.fill" should be type="tool" + tool_name="form.fill"
    # Also handles hybrid case where LLM returns both type="fill" AND tool_name="form.fill"
    should_convert_to_tool = (
        (action.get("type") == "fill") or
        (action.get("type") == "form.fill") or
        (action.get("tool_name") == "form.fill" and action.get("type") != "tool")
    )
    
    if should_convert_to_tool:
        if run_logger:
            run_logger.log_text(f"⚠️  Auto-correcting: LLM returned type='{action.get('type')}' - converting to type='tool' + tool_name='form.fill'")
        
        # Extract form field values from action or args
        form_args = action.get("args", {}) if isinstance(action.get("args"), dict) else {}
        for key in ["name", "email", "subject", "phone", "message"]:
            if key in action and key not in form_args:
                form_args[key] = action[key]
        
        # Reconstruct as proper tool call
        action = {
            "type": "tool",
            "tool_name": "form.fill",
            "args": form_args,
            "reason": action.get("reason", "Filling contact form (auto-corrected)")
        }
        
        if run_logger:
            run_logger.log_text(f"   ✓ Corrected to: {{'type': 'tool', 'tool_name': 'form.fill', 'args': {form_args}}}")
    
    if run_logger:
        run_logger.log_text("Planned action:")
        run_logger.log_code("json", json.dumps(action))
        try:
            if action.get("type"):
                run_logger.log_kv("action_type", str(action.get("type")))
            if action.get("reason"):
                run_logger.log_kv("action_reason", str(action.get("reason")))
            if action.get("tool_name"):
                run_logger.log_kv("tool_name", str(action.get("tool_name")))
        except Exception:
            pass
    if action.get("type") == "complete":
        data = action.get("extracted_data", page_context)
        try:
            is_empty = (data is None) or (isinstance(data, (list, dict)) and len(data) == 0)
        except Exception:
            is_empty = False
        if is_empty:
            try:
                items2 = await extract_articles_eval(page)
                if items2:
                    data = {"articles": items2}
                    if run_logger:
                        run_logger.log_text(f"Filled extracted_data from deterministic extractor: {len(items2)}")
            except Exception:
                pass
        return True, data
    # Tool call branch
    if action.get("type") == "tool":
        tool_name = action.get("tool_name")
        args = action.get("args") or {}
        tool_res = await _execute_tool(executor, page, instruction, str(tool_name or ""), args if isinstance(args, dict) else {}, runtime, run_logger, domain_dir)
        if run_logger:
            try:
                run_logger.log_text(f"Tool executed: {tool_name}")
                run_logger.log_code("json", json.dumps(tool_res))
            except Exception:
                pass
        
        # AUTO-COMPLETE: If form was successfully submitted, end task immediately
        if str(tool_name).lower() == "form.fill" and isinstance(tool_res, dict):
            form_fill_result = tool_res.get("form_fill")
            if isinstance(form_fill_result, dict) and form_fill_result.get("submitted") is True:
                if run_logger:
                    run_logger.log_text("✅ Form successfully submitted - auto-completing task")
                try:
                    tool_history.append({"tool": tool_name, "args": args, "result": tool_res})
                except Exception:
                    pass
                # Return True to signal task completion
                return True, {
                    "form_submitted": True,
                    "message": "Contact form submitted successfully",
                    "fields_filled": form_fill_result.get("filled", {}),
                }
        
        # Check for tool failures and apply retry logic
        if retry_manager and isinstance(tool_res, dict) and "error" in tool_res:
            error_msg = str(tool_res.get("error", ""))
            if not retry_manager.should_retry(str(tool_name), error_msg):
                if run_logger:
                    run_logger.log_text(f"🛑 Tool {tool_name} failed repeatedly with same error - SKIPPING further retries")
                    summary = retry_manager.get_failure_summary(str(tool_name))
                    run_logger.log_code("json", json.dumps(summary, indent=2))
                
                # Try alternative approach
                alternative = retry_manager.get_alternative_approach(str(tool_name))
                if alternative:
                    if run_logger:
                        run_logger.log_text(f"🔄 Suggested alternative: {alternative}")
        
        try:
            tool_history.append({"tool": tool_name, "args": args, "result": tool_res})
        except Exception:
            pass
        return False, None
    # Respect no_click runtime flag
    if runtime.get("no_click") and str(action.get("type")) == "click":
        if run_logger:
            run_logger.log_text("Skipping click due to no_click=true")
    else:
        _t_exec = time.time()
        await executor._execute_action(page, action, runtime)
        try:
            run_logger.log_kv("fn:_execute_action_ms", str(int((time.time() - _t_exec) * 1000)))
        except Exception:
            pass
    if run_logger:
        run_logger.log_text(f"Executed action: {action.get('type')}")
        try:
            sel = action.get("selector")
            val = action.get("value") if isinstance(action.get("value"), (str, int, float)) else None
            timeout = action.get("timeoutMs") or runtime.get("action_timeout_ms")
            details = {k: v for k, v in {"selector": sel, "value": (str(val)[:80] if val is not None else None), "timeoutMs": timeout}.items() if v is not None}
            if details:
                run_logger.log_code("json", json.dumps(details))
        except Exception:
            pass
    return False, None


async def run_task(
    executor,
    agent,
    instruction: str,
    url: Optional[str],
    visual_mode: bool,
    stealth_mode: bool,
    captcha_solver: bool,
    run_logger,
    runtime: Dict[str, Any],
) -> Dict:
    result: Dict[str, Any] = {"data": None, "steps": 0, "screenshots": [], "meta": {"hints": [], "suggested_commands": []}}
    lower_instr = (instruction or "").lower()
    
    # Detect form-filling tasks to enable optimized context extraction
    is_form_task = any(k in lower_instr for k in ["form", "formularz", "fill", "wypełnij", "wypelnij", "submit", "wyślij", "wyslij", "contact"])
    if run_logger and is_form_task:
        run_logger.log_text("🎯 Form task detected - enabling form-focused context extraction")

    page, domain_dir, stealth_mode, early = await executor._open_page_with_prechecks(
        agent=agent,
        url=url,
        instruction=instruction,
        stealth_mode=stealth_mode,
        captcha_solver=captcha_solver,
        runtime=runtime,
        run_logger=run_logger,
        result=result,
        lower_instr=lower_instr,
    )
    if early is not None:
        await page.close()
        return early

    # Expose canonical pairs (name/email/subject/phone/message) from instruction to the page for fill fallbacks
    try:
        canonical_pairs = executor._parse_form_pairs(instruction)
        if isinstance(canonical_pairs, dict):
            try:
                await page.evaluate("(data) => { window.__curllm_canonical = data; }", canonical_pairs)  # type: ignore[arg-type]
            except Exception:
                pass
    except Exception:
        pass

    try:
        if bool(runtime.get("refine_instruction")) and getattr(executor, "llm", None):
            pc = await executor._extract_page_context(
                page,
                include_dom=bool(runtime.get("include_dom_html")),
                dom_max_chars=int(runtime.get("dom_max_chars", 20000) or 20000),
            )
            refined = await refine_instruction_llm(executor.llm, instruction, pc, run_logger)
            if isinstance(refined, str) and refined.strip():
                instruction = refined
                lower_instr = (instruction or "").lower()
                if run_logger:
                    run_logger.log_text("Instruction refined; continuing with refined instruction.")
    except Exception:
        pass

    prev_ctx: Optional[Dict[str, Any]] = None
    try:
        if bool(runtime.get("include_prev_results")):
            fields = runtime.get("diff_fields") or ["href", "title", "url"]
            prev_ctx = _previous_for_context(url, instruction, runtime.get("result_key"), fields)
    except Exception:
        prev_ctx = None

    # Try DSL Executor FIRST (uses knowledge base for best strategy)
    dsl_keywords = ['product', 'produkt', 'extract', 'spec', 'parametr', 'techniczne', 'dane']
    if config.dsl_enabled and any(kw in lower_instr for kw in dsl_keywords):
        if run_logger:
            run_logger.log_text("📋 DSL Executor enabled - using knowledge base for optimal strategy")
        try:
            from .dsl import DSLExecutor
            
            dsl_executor = DSLExecutor(
                page=page,
                llm_client=executor.llm,
                run_logger=run_logger,
                kb_path=config.dsl_knowledge_db,
                dsl_dir=config.dsl_directory
            )
            
            dsl_result = await dsl_executor.execute(
                url=url or page.url,
                instruction=instruction,
                max_fallbacks=config.dsl_max_fallbacks
            )
            
            if dsl_result.success and dsl_result.data:
                if run_logger:
                    run_logger.log_text(f"✅ DSL Executor succeeded - algorithm: {dsl_result.algorithm_used}")
                    if isinstance(dsl_result.data, dict) and not any(k in dsl_result.data for k in ['name', 'url', 'price']):
                        run_logger.log_text(f"   Specs: {len(dsl_result.data)} parameters")
                    else:
                        run_logger.log_text(f"   Items: {len(dsl_result.data) if isinstance(dsl_result.data, list) else 1}")
                    run_logger.log_text(f"   Validation score: {dsl_result.validation_score:.2f}")
                    if dsl_result.fallbacks_tried:
                        run_logger.log_text(f"   Fallbacks tried: {dsl_result.fallbacks_tried}")
                
                # Check if it's a specs extraction (dict with key-value pairs)
                is_specs = isinstance(dsl_result.data, dict) and not any(k in dsl_result.data for k in ['name', 'url', 'price'])
                
                if is_specs:
                    result["data"] = {
                        "specifications": dsl_result.data,
                        "count": len(dsl_result.data),
                        "algorithm": dsl_result.algorithm_used,
                        "validation_score": dsl_result.validation_score,
                    }
                else:
                    result["data"] = {
                        "items": dsl_result.data if isinstance(dsl_result.data, list) else [dsl_result.data],
                        "count": len(dsl_result.data) if isinstance(dsl_result.data, list) else 1,
                        "algorithm": dsl_result.algorithm_used,
                        "validation_score": dsl_result.validation_score,
                        "selector": dsl_result.strategy_used.selector if dsl_result.strategy_used else None
                    }
                await page.close()
                return result
            else:
                if run_logger:
                    run_logger.log_text(f"⚠️ DSL Executor: {'; '.join(dsl_result.issues[:3]) if dsl_result.issues else 'No data'}")
        except Exception as e:
            if run_logger:
                run_logger.log_text(f"⚠️ DSL Executor failed: {e}")

    # Try LLM-guided extractor (LLM makes atomic decisions)
    if config.llm_guided_extractor_enabled and ("product" in lower_instr or "produkt" in lower_instr):
        if run_logger:
            run_logger.log_text("🤖 LLM-Guided Extractor enabled - LLM makes decisions at each atomic step")
        try:
            from .llm_guided_extractor import llm_guided_extract
            
            result_data = await llm_guided_extract(instruction, page, executor.llm, run_logger)
            
            if result_data and result_data.get("count", 0) > 0:
                if run_logger:
                    run_logger.log_text(f"✅ LLM-Guided Extractor succeeded - found {result_data['count']} items")
                result["data"] = result_data
                await page.close()
                return result
            else:
                reason = result_data.get("reason", "No items found") if result_data else "Extraction failed"
                if run_logger:
                    run_logger.log_text(f"⚠️ LLM-Guided Extractor returned no data: {reason}")
        except Exception as e:
            if run_logger:
                run_logger.log_text(f"⚠️ LLM-Guided Extractor failed: {e}")
    
    # Try dynamic detector first (generic, adaptive)
    if config.iterative_extractor_enabled and ("product" in lower_instr or "produkt" in lower_instr):
        if run_logger:
            run_logger.log_text("🔍 Dynamic Detector enabled - adaptive pattern recognition")
        try:
            from .dynamic_detector import dynamic_extract
            
            result_data = await dynamic_extract(page, instruction, run_logger)
            
            if result_data and result_data.get("count", 0) > 0:
                if run_logger:
                    run_logger.log_text(f"✅ Dynamic Detector succeeded - found {result_data['count']} items")
                    run_logger.log_text(f"   Container: {result_data.get('container', {}).get('selector', 'unknown')}")
                    run_logger.log_text(f"   Confidence: {result_data.get('container', {}).get('confidence', 0):.2f}")
                result["data"] = result_data
                await page.close()
                return result
            else:
                reason = result_data.get("reason", "No items found") if result_data else "Detection failed"
                if run_logger:
                    run_logger.log_text(f"⚠️ Dynamic Detector returned no data: {reason}")
        except Exception as e:
            if run_logger:
                run_logger.log_text(f"⚠️ Dynamic Detector failed: {e}")
    
    # Try iterative extractor second (pure JS, fast fallback)
    if config.iterative_extractor_enabled and ("product" in lower_instr or "produkt" in lower_instr):
        if run_logger:
            run_logger.log_text("🔄 Iterative Extractor enabled - trying atomic DOM queries")
        try:
            from .iterative_extractor import iterative_extract
            
            result_data = await iterative_extract(instruction, page, executor.llm, run_logger)
            
            if result_data and result_data.get("count", 0) > 0:
                if run_logger:
                    run_logger.log_text(f"✅ Iterative Extractor succeeded - found {result_data['count']} items")
                result["data"] = result_data
                await page.close()
                return result
            else:
                reason = result_data.get("reason", "No items found") if result_data else "Extraction failed"
                if run_logger:
                    run_logger.log_text(f"⚠️ Iterative Extractor returned no data: {reason}")
        except Exception as e:
            if run_logger:
                run_logger.log_text(f"⚠️ Iterative Extractor failed: {e}")
    
    # Try BQL extraction orchestrator (second priority)
    if config.bql_extraction_orchestrator_enabled and ("product" in lower_instr or "produkt" in lower_instr or "extract" in lower_instr):
        if run_logger:
            run_logger.log_text("🔍 BQL Extraction Orchestrator enabled - trying BQL-based extraction")
        try:
            from .bql_extraction_orchestrator import BQLExtractionOrchestrator
            from .page_context import extract_page_context
            import asyncio
            
            page_context = await extract_page_context(page, dom_max_chars=30000, include_dom=False)
            
            if not page_context:
                if run_logger:
                    run_logger.log_text("⚠️ Failed to extract page context, skipping BQL orchestrator")
                raise ValueError("Page context extraction failed")
            
            orchestrator = BQLExtractionOrchestrator(executor.llm, instruction, page, run_logger)
            
            data_ms = await asyncio.wait_for(
                orchestrator.orchestrate(page_context),
                timeout=config.bql_extraction_orchestrator_timeout
            )
            
            if data_ms is not None:
                if run_logger:
                    run_logger.log_text("✅ BQL Orchestrator succeeded - returning result")
                result["data"] = data_ms
                await page.close()
                return result
            else:
                if run_logger:
                    run_logger.log_text("⚠️ BQL Orchestrator returned no data, trying standard extraction orchestrator")
        except Exception as e:
            if run_logger:
                run_logger.log_text(f"⚠️ BQL Orchestrator failed: {e}, trying standard extraction orchestrator")
    
    # Try extraction orchestrator for product tasks (before planner loop)
    if config.extraction_orchestrator_enabled and ("product" in lower_instr or "produkt" in lower_instr):
        if run_logger:
            run_logger.log_text("🎭 Extraction Orchestrator enabled - trying orchestrated extraction")
        try:
            from .extraction_orchestrator import ExtractionOrchestrator
            from .page_context import extract_page_context
            import asyncio
            
            page_context = await extract_page_context(page, dom_max_chars=20000, include_dom=False)
            
            if not page_context:
                if run_logger:
                    run_logger.log_text("⚠️ Failed to extract page context, skipping extraction orchestrator")
                raise ValueError("Page context extraction failed")
            
            orchestrator = ExtractionOrchestrator(executor.llm, instruction, page, run_logger)
            
            data_ms = await asyncio.wait_for(
                orchestrator.orchestrate(page_context),
                timeout=config.extraction_orchestrator_timeout
            )
            
            if data_ms is not None:
                if run_logger:
                    run_logger.log_text("✅ Orchestrator succeeded - returning result")
                result["data"] = data_ms
                await page.close()
                return result
            else:
                if run_logger:
                    run_logger.log_text("⚠️ Orchestrator returned no data, continuing with standard planner")
        except Exception as e:
            if run_logger:
                run_logger.log_text(f"⚠️ Orchestrator failed: {e}, continuing with standard planner")

    # Planner-only mode: skip all early shortcuts (form/articles/selector/direct/product)

    # Planner loop
    last_sig: Optional[str] = None
    no_progress = 0
    stall_limit = int(runtime.get("stall_limit", 5) or 5)
    progressive_depth = 1
    last_screenshot_path: Optional[str] = None
    last_visual_analysis: Optional[Dict[str, Any]] = None
    tool_history: list[Dict[str, Any]] = []
    
    # Initialize Tool Retry Manager to prevent infinite loops
    retry_manager = ToolRetryManager(max_same_error=2)
    
    for step in range(config.max_steps):
        result["steps"] = step + 1
        if run_logger:
            run_logger.log_heading(f"Step {step + 1}")
        if visual_mode:
            last_screenshot_path, last_visual_analysis = await _step_visual(executor, page, step, domain_dir, captcha_solver, run_logger, result)

        # Try handle human verification banners/buttons each step
        try:
            _t_hv = time.time()
            await handle_human_verification(page, run_logger)
            try:
                run_logger.log_kv("fn:human.verify_ms", str(int((time.time() - _t_hv) * 1000)))
            except Exception:
                pass
        except Exception:
            pass
        try:
            _t_acc_each = time.time()
            await _accept_cookies(page)
            try:
                run_logger.log_kv("fn:accept_cookies(per_step)_ms", str(int((time.time() - _t_acc_each) * 1000)))
            except Exception:
                pass
        except Exception:
            pass

        _t_pc = time.time()
        page_context = await _step_page_context(executor, page, runtime, last_screenshot_path, last_visual_analysis, form_focused=is_form_task)
        try:
            run_logger.log_kv("fn:_extract_page_context_ms", str(int((time.time() - _t_pc) * 1000)))
        except Exception:
            pass
        if prev_ctx:
            try:
                page_context["previous_results"] = prev_ctx
            except Exception:
                pass
        try:
            page_context["tool_history"] = list(tool_history)
        except Exception:
            pass
        page_context = await _remediate_if_empty(page, runtime, run_logger, page_context)

        # progress
        last_sig, no_progress, progressive_depth, should_break = await _progress_and_maybe_break(
            executor,
            page_context,
            last_sig,
            no_progress,
            progressive_depth,
            runtime,
            run_logger,
            result,
            instruction,
            url,
            stall_limit,
        )
        if should_break:
            break

        if run_logger:
            try:
                preview_len = LOG_PREVIEW_CHARS
                dom_chars = int(runtime.get("dom_max_chars", 20000) or 20000)
                dom_cap = int(runtime.get("dom_max_cap", 60000) or 60000)
                incl = bool(runtime.get("include_dom_html", False))
                def _prune_nulls(obj):
                    if isinstance(obj, dict):
                        pruned = {k: _prune_nulls(v) for k, v in obj.items()}
                        return {k: v for k, v in pruned.items() if v is not None and not (isinstance(v, (list, dict)) and len(v) == 0)}
                    if isinstance(obj, list):
                        pruned_list = [_prune_nulls(x) for x in obj]
                        pruned_list = [x for x in pruned_list if x is not None and not (isinstance(x, (list, dict)) and len(x) == 0)]
                        return pruned_list
                    return obj
                pc_json = json.dumps(_prune_nulls(page_context), indent=2)
                original_len = len(pc_json)
                logged_len = min(original_len, preview_len)
                truncated_by = max(0, original_len - logged_len)
                run_logger.log_text(
                    f"Page context snapshot (preview {preview_len} via CURLLM_LOG_PREVIEW_CHARS; "
                    f"original={original_len} chars; logged={logged_len}; truncated_by={truncated_by}; "
                    f"dom_max_chars={dom_chars} via CURLLM_DOM_MAX_CHARS; dom_max_cap={dom_cap} via CURLLM_DOM_MAX_CAP; "
                    f"include_dom_html={incl} via CURLLM_INCLUDE_DOM_HTML)"
                )
                run_logger.log_code("json", pc_json[:preview_len])
            except Exception:
                pass

        # Apply progressive context if enabled
        if config.progressive_context_enabled:
            from .progressive_context import build_progressive_context, get_context_stats
            
            progressive_ctx = build_progressive_context(
                page_context=page_context,
                step=step,
                instruction=instruction
            )
            
            ctx_stats = get_context_stats(progressive_ctx)
            if run_logger:
                run_logger.log_text(
                    f"📊 Progressive Context: step={step}, size={ctx_stats['size_chars']} chars "
                    f"(links:{ctx_stats['link_count']}, headings:{ctx_stats['heading_count']}, "
                    f"forms:{ctx_stats['form_count']}, has_dom:{ctx_stats['has_dom']})"
                )
            
            # Use progressive context for LLM
            page_context_for_planner = progressive_ctx
        else:
            page_context_for_planner = page_context

        # Planner step
        done, data = await _planner_cycle(executor, instruction, page_context_for_planner, step, run_logger, runtime, page, tool_history, domain_dir, retry_manager)
        if done:
            result["data"] = data
            break

        if await executor._detect_honeypot(page):
            logger.warning("Honeypot detected, skipping field")

    if result.get("data") is None:
        await _finalize_fallback(executor, instruction, url, page, run_logger, result, domain_dir, runtime)

    await page.close()
    return result
