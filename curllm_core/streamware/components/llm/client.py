"""
LLM Client - Async Ollama client for text and vision.
"""
import aiohttp
import base64
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List


class SimpleOllama:
    """
    Minimal async Ollama client.
    
    Used when langchain_ollama is unavailable or for direct API access.
    """
    
    def __init__(
        self,
        base_url: str,
        model: str,
        num_ctx: int = 4096,
        num_predict: int = 1024,
        temperature: float = 0.1,
        top_p: float = 0.9,
        timeout: int = 300
    ):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.options = {
            "num_ctx": num_ctx,
            "num_predict": num_predict,
            "temperature": temperature,
            "top_p": top_p,
        }
    
    async def ainvoke(self, prompt: str) -> Dict[str, Any]:
        """
        Invoke LLM with text prompt.
        
        Args:
            prompt: Text prompt
            
        Returns:
            {"text": "response text"}
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": self.options,
        }
        
        timeout_obj = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload
            ) as resp:
                data = await resp.json()
        
        text = data.get("response", "") if isinstance(data, dict) else str(data)
        return {"text": text}
    
    async def ainvoke_with_image(
        self,
        prompt: str,
        image_path: str
    ) -> Dict[str, Any]:
        """
        Invoke LLM with image (vision/multimodal).
        
        Requires vision-capable model (llava, minicpm-v, qwen2-vl).
        
        Args:
            prompt: Text prompt
            image_path: Path to image file
            
        Returns:
            {"text": "response text"}
        """
        # Read and encode image
        image_file = Path(image_path)
        if not image_file.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        with open(image_file, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Build multimodal payload
        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [image_data],
            "stream": False,
            "options": self.options,
        }
        
        timeout_obj = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload
            ) as resp:
                data = await resp.json()
        
        text = data.get("response", "") if isinstance(data, dict) else str(data)
        return {"text": text}
    
    async def generate(self, prompt: str) -> str:
        """Simple generate returning just text."""
        result = await self.ainvoke(prompt)
        return result.get("text", "")
    
    async def chat(self, messages: List[Dict[str, str]]) -> str:
        """
        Chat completion style API.
        
        Args:
            messages: List of {"role": "user/assistant", "content": "..."}
            
        Returns:
            Response text
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": self.options,
        }
        
        timeout_obj = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as resp:
                data = await resp.json()
        
        if isinstance(data, dict):
            message = data.get("message", {})
            return message.get("content", "")
        return str(data)


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
        """
        Map user data to form fields using LLM.
        
        Args:
            fields: Detected form fields
            user_data: User data to fill
            
        Returns:
            List of {selector, value, type, name}
        """
        # Build field descriptions
        field_descs = []
        for i, f in enumerate(fields):
            field_descs.append({
                "i": i,
                "type": f.get("type", ""),
                "name": f.get("name", ""),
                "tag": f.get("tag", ""),
                "selector": f.get("selector", "")
            })
        
        # Handle name split
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
        """
        Evaluate if form submission was successful.
        
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
        Find CSS selector from DOM context.
        
        Args:
            dom_context: HTML/DOM snippet
            description: What to find
            
        Returns:
            CSS selector or None
        """
        prompt = f"""Find a CSS selector for: "{description}"

DOM context:
{dom_context[:3000]}

Output ONLY the CSS selector, nothing else:"""

        response = await self.generate(prompt)
        
        # Extract selector from response
        response = response.strip()
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        if response.startswith("'") and response.endswith("'"):
            response = response[1:-1]
        
        # Validate it looks like a selector
        if response and (
            response.startswith('#') or
            response.startswith('.') or
            response.startswith('[') or
            re.match(r'^[a-z]+', response, re.I)
        ):
            return response
        
        return None
