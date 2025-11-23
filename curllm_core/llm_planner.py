#!/usr/bin/env python3
import json
from typing import Any, Dict

from .logger import RunLogger

async def generate_action(llm: Any, instruction: str, page_context: Dict, step: int, run_logger: RunLogger | None = None, max_chars: int = 8000) -> Dict:
    context_str = json.dumps(page_context, indent=2)[: max(1000, int(max_chars))]
    prompt_text = (
        "You are a browser automation expert. Analyze the current page and determine the next action.\n\n"
        f"Instruction: {instruction}\n"
        f"Current Step: {step}\n"
        f"Page Context: {context_str}\n\n"
        "If 'interactive' or 'dom_preview' are present, prefer using selectors for existing elements.\n"
        "If the instruction asks to extract data (titles, prices, urls, emails, etc.), and clicking is unnecessary, respond with type=complete and return extracted_data only.\n"
        "Use 'headings' and 'article_candidates' when extracting article titles. Return a list under extracted_data.articles with {title, url}.\n"
        "For article titles, look for headings in <article>, <main>, <section> (h1/h2/h3) and anchor texts that look like article links.\n"
        "Generate a JSON action:\n"
        "{\n"
        "    \"type\": \"click|fill|scroll|wait|complete\",\n"
        "    \"selector\": \"CSS selector if applicable\",\n"
        "    \"value\": \"value to fill if applicable\",\n"
        "    \"waitFor\": \"optional selector to wait for\",\n"
        "    \"timeoutMs\": 8000\n"
        "    \"extracted_data\": \"data if task is complete (e.g., {\\\"articles\\\": [{\\\"title\\\": \\\"...\\\", \\\"url\\\": \\\"...\\\"}]})\"\n"
        "}\n\n"
        "Response (JSON only):"
    )
    if run_logger:
        run_logger.log_text("LLM Prompt:")
        run_logger.log_code("json", prompt_text)
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
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"type": "wait"}
