"""
LLM Client for Streamware Components

Provides async LLM calls for:
- Field mapping
- Success detection
- Selector extraction from DOM

All requests and responses are logged for debugging.
"""
import json
import re
from typing import Dict, Any, Optional, List

# Global logger for LLM calls
_llm_logger = None


def set_llm_logger(logger):
    """Set logger for LLM calls."""
    global _llm_logger
    _llm_logger = logger


def _log(msg: str):
    """Log message if logger is set."""
    if _llm_logger:
        _llm_logger.log_text(msg)
    print(f"[StreamwareLLM] {msg}")


class StreamwareLLM:
    """Async LLM client for Streamware atomic components."""
    
    def __init__(self, model: str = None, host: str = None):
        """Initialize with optional model/host override."""
        from curllm_core.config import config
        self.model = model or config.ollama_model
        self.host = host or config.ollama_host
        self._client = None
        self.call_count = 0
    
    async def _get_client(self):
        """Lazy init Ollama client."""
        if self._client is None:
            try:
                from ollama import AsyncClient
                self._client = AsyncClient(host=self.host)
                _log(f"✅ Ollama AsyncClient initialized: {self.host}")
            except ImportError:
                # Fallback to requests-based client
                self._client = "requests"
                _log(f"⚠️ Using requests fallback for LLM")
        return self._client
    
    async def generate(self, prompt: str, log_request: bool = True) -> str:
        """Generate response from LLM."""
        self.call_count += 1
        client = await self._get_client()
        
        # Log full request
        if log_request:
            _log(f"🤖 LLM Request #{self.call_count} to {self.model}:")
            _log(f"```\n{prompt[:1000]}{'...' if len(prompt) > 1000 else ''}\n```")
        
        if client == "requests":
            result = await self._generate_requests(prompt)
            _log(f"🤖 LLM Response #{self.call_count}:\n```\n{result[:500]}{'...' if len(result) > 500 else ''}\n```")
            return result
        
        try:
            response = await client.generate(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0.1, "num_predict": 500}
            )
            result = response.get("response", "")
            _log(f"🤖 LLM Response #{self.call_count}:\n```\n{result[:500]}{'...' if len(result) > 500 else ''}\n```")
            return result
        except Exception as e:
            return f"Error: {e}"
    
    async def _generate_requests(self, prompt: str) -> str:
        """Fallback using requests."""
        import aiohttp
        
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 500}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=30) as resp:
                    data = await resp.json()
                    return data.get("response", "")
        except Exception as e:
            return f"Error: {e}"
    
    async def map_fields(
        self, 
        fields: List[Dict[str, Any]], 
        user_data: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to map user data to form fields.
        
        Args:
            fields: Detected form fields with selectors
            user_data: User data to fill (email, message, etc.)
            
        Returns:
            List of {selector, value, type, name}
        """
        # Build concise field descriptions
        field_descs = []
        for i, f in enumerate(fields):
            field_descs.append({
                "i": i,
                "type": f.get("type", ""),
                "name": f.get("name", ""),
                "tag": f.get("tag", ""),
                "selector": f.get("selector", "")
            })
        
        # Handle "name" -> First/Last split
        expanded_data = dict(user_data)
        if "name" in user_data and " " in user_data["name"]:
            parts = user_data["name"].split(" ", 1)
            expanded_data["first_name"] = parts[0]
            expanded_data["last_name"] = parts[1] if len(parts) > 1 else ""
            # Remove 'name' since we split it - prevents confusing LLM
            del expanded_data["name"]
        
        # Only show keys that user provided (no field names)
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
            # Extract JSON array
            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                mappings = json.loads(match.group())
                result = []
                for m in mappings:
                    idx = m.get("field_index", -1)
                    data_key = m.get("data_key")
                    if 0 <= idx < len(fields) and data_key in user_data:
                        result.append({
                            "selector": fields[idx].get("selector"),
                            "value": user_data[data_key],
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
        """
        Use LLM to evaluate if form submission was successful.
        
        Args:
            page_diff: Changes detected after submission
            
        Returns:
            {success: bool, confidence: float, reason: str}
        """
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
        
        # Fallback
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
        """
        Use LLM to find CSS selector from DOM context.
        
        Args:
            dom_context: HTML/DOM snippet
            description: What to find (e.g., "submit button", "email field")
            
        Returns:
            CSS selector or None
        """
        prompt = f"""Find CSS selector for: {description}

DOM snippet:
{dom_context[:2000]}

Output ONLY the CSS selector, nothing else.
Example: #submit-btn or .form-submit or button[type="submit"]

Selector:"""
        
        response = await self.generate(prompt)
        
        # Clean up response
        selector = response.strip().split('\n')[0].strip()
        
        # Validate it looks like a selector
        if selector and (selector.startswith('#') or selector.startswith('.') or 
                        selector.startswith('[') or re.match(r'^[a-z]', selector)):
            return selector
        
        return None


# Global instance for easy access
_llm_instance: Optional[StreamwareLLM] = None


def get_llm() -> StreamwareLLM:
    """Get or create global LLM instance."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = StreamwareLLM()
    return _llm_instance


async def llm_map_fields(fields: List[Dict], user_data: Dict[str, str]) -> List[Dict]:
    """Convenience function for field mapping."""
    return await get_llm().map_fields(fields, user_data)


async def llm_evaluate_success(page_diff: Dict) -> Dict[str, Any]:
    """Convenience function for success evaluation."""
    return await get_llm().evaluate_success(page_diff)


async def llm_find_selector(dom_context: str, description: str) -> Optional[str]:
    """Convenience function for selector finding."""
    return await get_llm().find_selector(dom_context, description)


async def generate_missing_field_data(
    missing_fields: List[Dict],
    existing_data: Dict[str, str],
    logger=None
) -> Dict[str, str]:
    """
    Generate values for missing required fields using LLM.
    
    Args:
        missing_fields: List of {name, type, tag, placeholder, required}
        existing_data: Existing user data for context
        logger: Optional logger
        
    Returns:
        Dict of generated field values
    """
    if not missing_fields:
        return {}
    
    llm = get_llm()
    
    # Build prompt
    field_descs = []
    for f in missing_fields:
        desc = f"{f['name']} ({f['type']})"
        if f.get('placeholder'):
            desc += f" - placeholder: {f['placeholder']}"
        field_descs.append(desc)
    
    prompt = f"""Generate realistic test values for these form fields.

Missing fields:
{chr(10).join(f'- {d}' for d in field_descs)}

Existing data for context:
{json.dumps(existing_data, ensure_ascii=False)}

Rules:
- Generate realistic, appropriate values
- For textarea/message: generate a short professional message (1-2 sentences)
- For phone: use format like "+48 123 456 789"
- For name: generate a realistic name
- Match the language/style of existing data

Return ONLY JSON object:
{{"field_name": "generated_value", ...}}

JSON:"""

    response = await llm.generate(prompt)
    
    try:
        match = re.search(r'\{[^}]+\}', response, re.DOTALL)
        if match:
            generated = json.loads(match.group())
            
            # Map to simple semantic keys for LLM mapping
            result = {}
            for field in missing_fields:
                field_name = field['name']
                field_type = field.get('type', '').lower()
                
                # Try to find value in generated data
                value = generated.get(field_name)
                if not value:
                    # Try common variations
                    for key in generated:
                        if key.lower() in field_name.lower() or field_name.lower() in key.lower():
                            value = generated[key]
                            break
                
                if value:
                    # Use SIMPLE semantic key (not raw HTML field name)
                    # This makes LLM mapping easier
                    if 'first' in field_name.lower():
                        result['first_name'] = value
                    elif 'last' in field_name.lower():
                        result['last_name'] = value
                    elif field_type == 'email':
                        result['email'] = value
                    elif field_type == 'tel' or 'phone' in field_name.lower():
                        result['phone'] = value
                    elif field.get('tag') == 'textarea':
                        result['message'] = value
                    else:
                        # Keep simple field names as-is
                        simple_name = field_name.split('[')[-1].rstrip(']') if '[' in field_name else field_name
                        result[simple_name] = value
            
            if logger:
                _log(f"🤖 Generated {len(result)} field value(s)")
            
            return result
    except Exception as e:
        if logger:
            _log(f"⚠️ Failed to generate field data: {e}")
    
    return {}
