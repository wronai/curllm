"""Simple Ollama client for async LLM calls"""

import aiohttp


class SimpleOllama:
    """Minimal async Ollama client used when langchain_ollama is unavailable"""
    
    def __init__(
        self, 
        base_url: str, 
        model: str, 
        num_ctx: int, 
        num_predict: int, 
        temperature: float, 
        top_p: float
    ):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.options = {
            "num_ctx": num_ctx,
            "num_predict": num_predict,
            "temperature": temperature,
            "top_p": top_p,
        }
    
    async def ainvoke(self, prompt: str):
        """Invoke the LLM with a prompt"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": self.options,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/api/generate", json=payload) as resp:
                data = await resp.json()
        text = data.get("response", "") if isinstance(data, dict) else str(data)
        return {"text": text}
