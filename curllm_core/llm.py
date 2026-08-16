#!/usr/bin/env python3
import aiohttp
import base64
from pathlib import Path
from typing import Dict, List


class SimpleOllama:
    """Minimal async Ollama client used when langchain_ollama is unavailable"""
    def __init__(
        self,
        base_url: str,
        model: str,
        num_ctx: int = 4096,
        num_predict: int = 1024,
        temperature: float = 0.1,
        top_p: float = 0.9,
        timeout: int = 300,
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

    async def ainvoke_with_image(self, prompt: str, image_path: str):
        """
        Invoke LLM with image (vision/multimodal).
        Requires vision-capable model (e.g., llava, minicpm-v, qwen2-vl).
        """
        try:
            image_file = Path(image_path)
            if not image_file.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")

            with open(image_file, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            raise ValueError(f"Failed to read image {image_path}: {e}") from e

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [image_data],
            "stream": False,
            "options": self.options,
        }

        timeout_obj = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.post(f"{self.base_url}/api/generate", json=payload) as resp:
                data = await resp.json()

        text = data.get("response", "") if isinstance(data, dict) else str(data)
        return {"text": text}

    async def generate(self, prompt: str) -> str:
        """Simple generate returning just text."""
        result = await self.ainvoke(prompt)
        return result.get("text", "")

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        """Chat completion style API."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": self.options,
        }
        timeout_obj = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.post(f"{self.base_url}/api/chat", json=payload) as resp:
                data = await resp.json()
        if isinstance(data, dict):
            message = data.get("message", {})
            return message.get("content", "")
        return str(data)
