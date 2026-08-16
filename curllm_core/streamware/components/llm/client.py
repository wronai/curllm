"""
LLM Client - Async Ollama client for text and vision.
"""
import json
import re
from typing import Any, Dict, List, Optional

from curllm_core.llm import SimpleOllama

__all__ = ["SimpleOllama", "OllamaClient"]


class OllamaClient(SimpleOllama):
    """Extended Ollama client with additional features."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = None

    def set_logger(self, logger):
        """Set logger for request/response logging."""
        self._logger = logger

    def _log(self, msg: str):
        """Log message if logger available."""
        if self._logger:
            self._logger.log_text(msg)

    async def map_fields(
        self,
        fields: List[Dict],
        user_data: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Map user data to form fields using LLM."""
        field_descs = []
        for i, f in enumerate(fields):
            field_descs.append({
                "i": i,
                "type": f.get("type", ""),
                "name": f.get("name", ""),
                "tag": f.get("tag", ""),
                "selector": f.get("selector", "")
            })

        expanded_data = dict(user_data)
        if "name" in user_data and " " in user_data["name"]:
            parts = user_data["name"].split(" ", 1)
            expanded_data["first_name"] = parts[0]
            expanded_data["last_name"] = parts[1] if len(parts) > 1 else ""
            del expanded_data["name"]

        data_keys = list(expanded_data.keys())

        prompt = f"""Map user data to form fields. Output ONLY JSON array.

Fields: {json.dumps(field_descs, ensure_ascii=False)}

Available data keys: {data_keys}
Data values: {json.dumps(expanded_data, ensure_ascii=False)}

Rules:
- email → field with type="email"
- message → field with tag="textarea"
- phone → field with type="tel" or name contains "phone"
- first_name → field with name containing "first"
- last_name → field with name containing "last"
- NEVER map name/first_name/last_name to textarea

IMPORTANT: data_key MUST be one of: {data_keys}

Output format:
[{{"field_index": 0, "data_key": "email"}}, ...]

JSON:"""

        response = await self.generate(prompt)

        try:
            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                mappings = json.loads(match.group())
                result = []
                for m in mappings:
                    idx = m.get("field_index", -1)
                    data_key = m.get("data_key")
                    if 0 <= idx < len(fields) and data_key in expanded_data:
                        result.append({
                            "selector": fields[idx].get("selector"),
                            "value": expanded_data[data_key],
                            "type": fields[idx].get("type", "text"),
                            "name": data_key
                        })
                return result
        except Exception:
            pass

        return []

    async def evaluate_success(
        self,
        page_diff: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate if form submission was successful."""
        prompt = f"""Was the form submission successful? Analyze these page changes:

URL changed: {page_diff.get('url_changed', False)}
Form disappeared: {page_diff.get('form_disappeared', False)}
New errors: {page_diff.get('new_errors', False)}
New text: {page_diff.get('new_text', '')[:500]}
Messages: {page_diff.get('messages', [])}

Output JSON:
{{"success": true/false, "confidence": 0.0-1.0, "reason": "brief explanation"}}

JSON:"""

        response = await self.generate(prompt)

        try:
            match = re.search(r'\{[^}]+\}', response)
            if match:
                return json.loads(match.group())
        except Exception:
            pass

        return {
            "success": page_diff.get("form_disappeared", False) or page_diff.get("url_changed", False),
            "confidence": 0.5,
            "reason": "LLM parsing failed, using heuristics"
        }

    async def find_selector(
        self,
        dom_context: str,
        description: str
    ) -> Optional[str]:
        """Find CSS selector from DOM context."""
        prompt = f"""Find a CSS selector for: "{description}"

DOM context:
{dom_context[:3000]}

Output ONLY the CSS selector, nothing else:"""

        response = await self.generate(prompt)

        response = response.strip()
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        if response.startswith("'") and response.endswith("'"):
            response = response[1:-1]

        if response and (
            response.startswith('#') or
            response.startswith('.') or
            response.startswith('[') or
            re.match(r'^[a-z]+', response, re.I)
        ):
            return response

        return None
