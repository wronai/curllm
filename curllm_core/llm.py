#!/usr/bin/env python3
import aiohttp

class SimpleOllama:
    """Minimal async Ollama client used when langchain_ollama is unavailable"""
    def __init__(self, base_url: str, model: str, num_ctx: int, num_predict: int, temperature: float, top_p: float, timeout: int = 300):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.options = {
            "num_ctx": num_ctx,
            "num_predict": num_predict,
            "temperature": temperature,
            "top_p": top_p,
        }
    async def ainvoke(self, prompt: str):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": self.options,
        }
        timeout_obj = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.post(f"{self.base_url}/api/generate", json=payload) as resp:
                data = await resp.json()
        text = data.get("response", "") if isinstance(data, dict) else str(data)
        return {"text": text}
