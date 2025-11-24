#!/usr/bin/env python3
import json
from typing import Any, Dict

from .logger import RunLogger

async def generate_action(llm: Any, instruction: str, page_context: Dict, step: int, run_logger: RunLogger | None = None, max_chars: int = 8000, growth_per_step: int = 2000, max_cap: int = 20000) -> Dict:
    adaptive_chars = min(max_chars + (step * growth_per_step), max_cap)
    context_str = json.dumps(page_context, indent=2)[:adaptive_chars]

    product_context = ""
    if "product" in (instruction or "").lower() or "cen" in (instruction or "").lower():
        product_context = (
            "\n"
            "IMPORTANT: You are looking for products with prices. Analyze the DOM carefully:\n"
            "1. Look for repeating patterns that contain both text and numbers\n"
            "2. Prices in Polish format: \"XXX,YY zł\" or \"od XXX,YY zł\" or just \"XXX.YY\"\n"
            "3. If you see products, extract them in the extracted_data field\n"
            "4. If the page doesn't show products yet, suggest navigation action (scroll, click on category)\n"
            "5. Check interactive elements for filters or sorting options\n\n"
            "Signs that indicate product listings:\n"
            "- Multiple similar DOM structures with prices\n"
            "- Links with product IDs (numbers in URLs)\n"
            "- Text patterns like \"od XXX zł\", \"cena:\", \"price:\"\n\n"
            "If you found products matching the criteria, return type=\"complete\" with extracted_data.\n"
            "If page needs more loading, return type=\"scroll\".\n"
            "If you see category links but no products, return type=\"click\" on relevant category.\n"
        )

    tools_desc = (
        "Available tools you MAY call by returning type='tool':\n"
        "- extract.emails(args: {}): returns {emails: string[]}\n"
        "- extract.links(args: {}): returns {links: [{text, href}]}\n"
        "- extract.phones(args: {}): returns {phones: string[]}\n"
        "- articles.extract(args: {}): returns {articles: [{title, url}]}\n"
        "- products.heuristics(args: {threshold?: number}): returns {products: [{name, price, url}]}\n"
        "- dom.snapshot(args: {include_dom?: boolean, max_chars?: number}): returns a 'page_context' snapshot\n"
        "- cookies.accept(args: {}): attempts to accept cookie banners, returns {accepted: boolean}\n"
        "- human.verify(args: {}): tries to bypass human verification, returns {ok: boolean}\n"
        "- form.fill(args: {name?: string, email?: string, subject?: string, phone?: string, message?: string}): returns {submitted: boolean, errors?: object}\n"
        "When you decide to call a tool, respond with an action of shape: {\n"
        "  \"type\": \"tool\", \n"
        "  \"tool_name\": \"one of the above\",\n"
        "  \"args\": { ... },\n"
        "  \"reason\": \"why you call this tool now\"\n"
        "}. After seeing tool results in next context (tools/tool_history), decide next action.\n"
    )

    prompt_text = (
        "You are a browser automation expert. Analyze the current page and determine the next action.\n\n"
        f"Instruction: {instruction}\n"
        f"Current Step: {step + 1}\n"
        f"Page Context (truncated to {len(context_str)} chars): {context_str}\n\n"
        f"{product_context}\n"
        f"{tools_desc}\n\n"
        "Analyze the DOM structure in 'dom_preview' and 'interactive' fields carefully.\n"
        "The 'headings' field shows main content structure.\n"
        "The 'article_candidates' may contain product links.\n\n"
        "If you see enough data to complete the task, return type='complete' with extracted_data.\n"
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
        run_logger.log_text(f"LLM Prompt (step {step + 1}, context: {len(context_str)} chars)")
        run_logger.log_code("text", prompt_text[:1000] + "...[truncated]...")
    try:
        response = await llm.ainvoke(prompt_text)
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
