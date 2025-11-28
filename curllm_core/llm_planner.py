#!/usr/bin/env python3
import json
import os
import time
from typing import Any, Dict

from .logger import RunLogger
from .config import config

async def generate_action(
    llm: Any,
    instruction: str,
    page_context: Dict,
    step: int,
    run_logger: RunLogger | None = None,
    max_chars: int = None,
    growth_per_step: int = None,
    max_cap: int = None
) -> Dict:
    # Use config values if not explicitly provided
    max_chars = max_chars if max_chars is not None else config.planner_max_chars
    growth_per_step = growth_per_step if growth_per_step is not None else config.planner_growth_per_step
    max_cap = max_cap if max_cap is not None else config.planner_max_cap
    
    adaptive_chars = min(max_chars + (step * growth_per_step), max_cap)
    def _prune_nulls(obj):
        if isinstance(obj, dict):
            pruned = {k: _prune_nulls(v) for k, v in obj.items()}
            return {k: v for k, v in pruned.items() if v is not None and not (isinstance(v, (list, dict)) and len(v) == 0)}
        if isinstance(obj, list):
            pruned_list = [_prune_nulls(x) for x in obj]
            pruned_list = [x for x in pruned_list if x is not None and not (isinstance(x, (list, dict)) and len(x) == 0)]
            return pruned_list
        return obj
    _context_json = json.dumps(_prune_nulls(page_context), indent=2)
    _ctx_original_len = len(_context_json)
    context_str = _context_json[:adaptive_chars]
    _ctx_logged_len = len(context_str)
    _ctx_truncated_by = max(0, _ctx_original_len - _ctx_logged_len)

    th_summary = ""
    try:
        th = page_context.get("tool_history") or []
        if isinstance(th, list) and th:
            parts = []
            for item in th[-3:]:
                try:
                    name = item.get("tool")
                    res = item.get("result") or {}
                    if isinstance(res, dict):
                        if "links" in res and isinstance(res.get("links"), list):
                            cnt = len(res.get("links") or [])
                            sample = []
                            for e in (res.get("links") or [])[:5]:
                                try:
                                    sample.append(e.get("href") or e.get("url"))
                                except Exception:
                                    continue
                            parts.append(f"{name}: links={cnt} sample={sample}")
                        elif "form_fill" in res:
                            ff = res.get("form_fill") or {}
                            sub = ff.get("submitted")
                            parts.append(f"{name}: form_fill.submitted={sub}")
                        else:
                            keys = list(res.keys())
                            parts.append(f"{name}: keys={keys}")
                except Exception:
                    continue
            if parts:
                th_summary = "\nTool History (summary):\n- " + "\n- ".join(parts) + "\n"
    except Exception:
        th_summary = ""

    product_context = ""
    if "product" in (instruction or "").lower() or "cen" in (instruction or "").lower():
        product_context = (
            "\n"
            "IMPORTANT: You are looking for products with prices.\n"
            "❌ DO NOT manually extract products - this will NOT work!\n"
            "✅ You MUST use the products.extract TOOL to extract products:\n\n"
            "```json\n"
            "{\n"
            "  \"type\": \"tool\",\n"
            "  \"tool_name\": \"products.extract\",\n"
            "  \"args\": {},\n"
            "  \"reason\": \"Extracting products using dynamic pattern detection\"\n"
            "}\n"
            "```\n\n"
            "The dynamic extraction system automatically:\n"
            "- Detects product container patterns dynamically (NO hard-coded selectors!)\n"
            "- Analyzes DOM structure and finds repeating patterns with prices\n"
            "- Works on ANY e-commerce site without configuration\n\n"
            "WORKFLOW:\n"
            "1. If you see category links but no products yet: return type=\"click\" on relevant category\n"
            "2. If page shows products: call products.extract tool\n"
            "3. If tool_history contains products from products.extract: return type=\"complete\" with extracted_data={\"products\": products}\n"
            "4. If page needs more loading: return type=\"scroll\"\n"
        )

    forms_context = ""
    low_instr = (instruction or "").lower()
    try:
        looks_form = any(k in low_instr for k in ["form", "formularz", "fill", "wypełnij", "wypelnij", "submit", "contact"])
        forms = page_context.get("forms") if isinstance(page_context, dict) else None
        if looks_form and isinstance(forms, list) and forms:
            # Build a compact summary of fields
            sample_fields: list[str] = []
            try:
                for f in (forms[0].get("fields") or [])[:8]:
                    try:
                        t = (f.get("type") or "").strip()
                        n = (f.get("name") or "").strip()
                        vis = f.get("visible")
                        if t and (vis is True or vis is None):
                            sample_fields.append(f"{t}:{n}")
                    except Exception:
                        continue
            except Exception:
                sample_fields = []
            forms_context = (
                "\n"
                "████████████████████████████████████████████████████████████████\n"
                "█  FORM FILLING TASK - FOLLOW THESE RULES EXACTLY!             █\n"
                "████████████████████████████████████████████████████████████████\n\n"
                "❌ WRONG: type=\"fill\" - DO NOT USE THIS, IT WILL FAIL!\n"
                "✅ CORRECT: type=\"tool\" with tool_name=\"form.fill\"\n\n"
                "YOUR RESPONSE MUST BE EXACTLY:\n"
                "```json\n"
                "{\n"
                "  \"type\": \"tool\",\n"
                "  \"tool_name\": \"form.fill\",\n"
                "  \"args\": {\"email\": \"value\", \"message\": \"value\"},\n"
                "  \"reason\": \"Fill form\"\n"
                "}\n"
                "```\n\n"
                "RULES:\n"
                "1. type MUST be \"tool\" (not \"fill\"!)\n"
                "2. tool_name MUST be \"form.fill\"\n"
                "3. args should contain ONLY fields from instruction\n"
                "4. DO NOT include selector - the tool handles this!\n\n"
                f"Available form fields: {sample_fields}\n"
                "████████████████████████████████████████████████████████████████\n"
            )
    except Exception:
        forms_context = ""

    offers_context = ""
    if any(k in low_instr for k in ["offer", "offers", "oferta", "oferty", "zlecenia", "zlecenie", "rfp"]):
        offers_context = (
            "\n"
            "IMPORTANT: You are extracting offers/zlecenia links with titles.\n"
            "- Prefer calling extract.links with filtering, e.g.:\n"
            "  - href_includes: 'rfp' or 'zlecen' or domain-specific segment\n"
            "  - href_regex: '(?:/rfp/|/zlecen|/zlecenia|/zapytanie|/oferta)'\n"
            "- Keep only meaningful entries (exclude navigation like login, privacy, categories).\n"
            "- When you have the list of links, return type='complete' with extracted_data = {\"links\": links}.\n"
        )

    tools_desc = (
        "Available tools you MAY call by returning type='tool':\n"
        "- extract.emails(args: {}): returns {emails: string[]}\n"
        "- extract.links(args: {selector?, href_includes?, href_regex?, text_regex?, limit?}): returns {links: [{text, href}]}\n"
        "- extract.phones(args: {}): returns {phones: string[]}\n"
        "- articles.extract(args: {}): returns {articles: [{title, url}]}\n"
        "- products.extract(args: {max_items?}): returns {products: [{name, price, url}]}\n"
        "- dom.snapshot(args: {include_dom?, max_chars?}): returns page_context\n"
        "- cookies.accept(args: {}): returns {accepted: boolean}\n"
        "- human.verify(args: {}): returns {ok: boolean}\n"
        "- form.fill(args: {name?, email?, phone?, message?}): FULL form fill + submit\n"
        "\n"
        "ATOMIC form tools (for fine-grained control):\n"
        "- form.detect(args: {}): find forms -> {found, form_id, fields, score}\n"
        "- form.fields(args: {form_id?}): get fields -> {fields: [], count}\n"
        "- form.fill_field(args: {selector, value, type?}): fill ONE field -> {success, error}\n"
        "- form.validate(args: {}): check filled fields -> {valid, fields, errors}\n"
        "- form.check_required(args: {form_id?}): check required -> {ready, issues}\n"
        "- form.submit(args: {form_id?}): submit form -> {clicked, error}\n"
        "- form.check_success(args: {}): check submission -> {success, indicators}\n"
        "\n"
        "Tool call format: {\"type\": \"tool\", \"tool_name\": \"xxx\", \"args\": {...}, \"reason\": \"...\"}\n"
    )

    prompt_text = (
        "You are a browser automation expert. Analyze the current page and determine the next action.\n\n"
        f"Instruction: {instruction}\n"
        f"Current Step: {step + 1}\n"
        f"Page Context (truncated to {len(context_str)} chars): {context_str}\n\n"
        f"{th_summary}"
        f"{forms_context}"
        f"{product_context}\n"
        f"{offers_context}\n"
        f"{tools_desc}\n\n"
        "Analyze the DOM structure in 'dom_preview' and 'interactive' fields carefully.\n"
        "The 'headings' field shows main content structure.\n"
        "The 'article_candidates' may contain product links.\n\n"
        "If you see enough data to complete the task (including from tool_history), return type='complete' with extracted_data.\n"
        "If the task is to extract links/titles and tool_history already contains an array 'links', finalize with type='complete' and extracted_data = {\"links\": links}.\n"
        "If page needs interaction, return appropriate action (click/scroll/wait) or call a tool (type='tool').\n\n"
        "Generate a JSON action:\n"
        "{\n"
        "    \"type\": \"click|fill|scroll|wait|complete|tool\",\n"
        "    \"selector\": \"CSS selector if applicable\",\n"
        "    \"value\": \"value to fill if applicable\",\n"
        "    \"tool_name\": \"if type=tool, name of the tool\",\n"
        "    \"args\": \"if type=tool, arguments object\",\n"
        "    \"extracted_data\": \"data if task is complete\",\n"
        "    \"reason\": \"brief explanation of your decision\"\n"
        "}\n\n"
        "Response (JSON only):"
    )
    if run_logger:
        try:
            _pl = int(os.getenv("CURLLM_LOG_PROMPT_CHARS", "25000") or 25000)
        except Exception:
            _pl = 25000
        # Context usage and truncation details
        run_logger.log_text(
            f"LLM Prompt (step {step + 1}) context_used={_ctx_logged_len} / context_original={_ctx_original_len} chars; "
            f"truncated_by={_ctx_truncated_by}; limits: base={max_chars} (CURLLM_PLANNER_BASE_CHARS), "
            f"growth_per_step={growth_per_step} (CURLLM_PLANNER_GROWTH_PER_STEP), max_cap={max_cap} (CURLLM_PLANNER_MAX_CAP)"
        )
        # Prompt logging stats
        _pt_original = len(prompt_text)
        _pt_logged = min(_pt_original, _pl)
        _pt_truncated_by = max(0, _pt_original - _pt_logged)
        run_logger.log_text(
            f"Prompt logging: original={_pt_original}, logged={_pt_logged}, truncated_by={_pt_truncated_by}, "
            f"limit={_pl} (CURLLM_LOG_PROMPT_CHARS)"
        )
        run_logger.log_code("text", prompt_text[:_pl] + ("...[truncated]..." if _pt_truncated_by > 0 else ""))
    try:
        _t0 = time.time()
        response = await llm.ainvoke(prompt_text)
        try:
            if run_logger:
                run_logger.log_kv("fn:llm.ainvoke_ms", str(int((time.time() - _t0) * 1000)))
        except Exception:
            pass
        text = response["text"] if isinstance(response, dict) and "text" in response else str(response)
    except Exception as e:
        if run_logger:
            run_logger.log_text("LLM error, continuing with wait/fallback:")
            run_logger.log_code("text", str(e))
        return {"type": "wait"}
    if run_logger:
        run_logger.log_text("LLM Raw Response:")
        run_logger.log_code("json", text)
    # Robust JSON parsing: strip code fences, then load; if fails, scan for valid JSON action objects
    def _strip_fences(s: str) -> str:
        s = s.strip()
        if s.startswith("```"):
            # remove first fence line
            s = s.split("\n", 1)[1] if "\n" in s else s
            # remove trailing fence
            if s.rstrip().endswith("```"):
                s = s.rsplit("```", 1)[0]
        return s.strip()

    raw = _strip_fences(text)
    # Strategy 1: direct JSON
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            if "type" in obj or "extracted_data" in obj:
                return obj
            if "articles" in obj:
                return {"type": "complete", "extracted_data": {"articles": obj.get("articles")}}
    except Exception:
        pass

    # Strategy 2: collect all balanced JSON objects, ignoring braces in strings
    def _all_json_objects(s: str) -> list[str]:
        objs: list[str] = []
        start = -1
        depth = 0
        in_str = False
        esc = False
        for i, ch in enumerate(s):
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
                        objs.append(s[start : i + 1])
                        start = -1
        return objs

    try:
        candidates = _all_json_objects(raw)
        # Prefer later candidates in case the model echoed an example first
        for cand in reversed(candidates):
            try:
                obj = json.loads(cand)
            except Exception:
                continue
            if isinstance(obj, dict):
                if "type" in obj or "extracted_data" in obj:
                    return obj
                if "articles" in obj:
                    return {"type": "complete", "extracted_data": {"articles": obj.get("articles")}}
    except Exception as e:
        if run_logger:
            run_logger.log_text("Planner parse error (balanced scan):")
            run_logger.log_code("text", str(e))

    # Strategy 3: incremental closing brace trial from the last opening brace
    try:
        last_start = raw.rfind('{')
        if last_start != -1:
            positions = [i for i, ch in enumerate(raw) if ch == '}']
            for pos in positions:
                if pos <= last_start:
                    continue
                sl = raw[last_start : pos + 1]
                try:
                    obj = json.loads(sl)
                    if isinstance(obj, dict):
                        if "type" in obj or "extracted_data" in obj:
                            return obj
                        if "articles" in obj:
                            return {"type": "complete", "extracted_data": {"articles": obj.get("articles")}}
                except Exception:
                    continue
    except Exception as e:
        if run_logger:
            run_logger.log_text("Planner parse error (incremental):")
            run_logger.log_code("text", str(e))
    return {"type": "wait"}
