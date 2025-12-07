import os
import logging
from typing import Optional, Any
from .config import config
from .llm import SimpleOllama
from .llm_config import LLMConfig

logger = logging.getLogger(__name__)

# Check if litellm is available
try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    logger.info("litellm not installed, using built-in clients for cloud providers")


def setup_llm(llm_config: Optional[LLMConfig] = None) -> Any:
    """
    Create LLM client based on configuration.
    
    Args:
        llm_config: Optional LLMConfig. If not provided, uses environment/config defaults.
    
    Returns:
        LLM client instance with ainvoke() method
    """
    if llm_config is None:
        # Check for new-style provider config
        provider_env = os.getenv("CURLLM_LLM_PROVIDER")
        if provider_env:
            llm_config = LLMConfig.from_env()
        else:
            # Legacy mode: use ollama with config settings
            return _setup_ollama_legacy()
    
    return create_llm_client(llm_config)


def create_llm_client(llm_config: LLMConfig) -> Any:
    """
    Create LLM client for any supported provider using litellm.
    
    Uses litellm for unified multi-provider support. Supports any provider
    that litellm supports, including:
    - ollama: Local Ollama server (ollama/model_name)
    - openai: OpenAI API (openai/gpt-4o-mini, openai/gpt-4o, etc.)
    - anthropic: Anthropic (anthropic/claude-3-haiku-20240307, etc.)
    - gemini: Google Gemini (gemini/gemini-2.0-flash, etc.)
    - groq: Groq (groq/llama3-70b-8192, etc.)
    - deepseek: DeepSeek (deepseek/deepseek-chat)
    - azure: Azure OpenAI
    - bedrock: AWS Bedrock
    - cohere: Cohere
    - huggingface: Hugging Face
    - And many more...
    
    See https://docs.litellm.ai/docs/providers for full list.
    """
    provider = llm_config.provider_name
    
    # For Ollama, use local SimpleOllama client (doesn't need litellm)
    if provider == "ollama":
        return _create_ollama_client(llm_config)
    
    # For cloud providers, prefer litellm if available
    if LITELLM_AVAILABLE:
        return LiteLLMClient(llm_config)
    
    # Fallback to built-in clients
    if provider == "openai":
        return _create_openai_client(llm_config)
    elif provider == "anthropic":
        return _create_anthropic_client(llm_config)
    elif provider in ("gemini", "google"):
        return _create_gemini_client(llm_config)
    elif provider == "groq":
        return _create_groq_client(llm_config)
    elif provider == "deepseek":
        return _create_deepseek_client(llm_config)
    else:
        raise ValueError(
            f"Unknown provider: {provider}. Install litellm for full provider support: pip install litellm"
        )


def _setup_ollama_legacy() -> Any:
    """Legacy Ollama setup using config.py settings"""
    backend = os.getenv("CURLLM_LLM_BACKEND", "simple").lower()
    if backend == "langchain":
        try:
            from langchain_ollama import OllamaLLM  # type: ignore
            return OllamaLLM(
                base_url=config.ollama_host,
                model=config.ollama_model,
                temperature=config.temperature,
                top_p=config.top_p,
                num_ctx=config.num_ctx,
                num_predict=config.num_predict,
            )
        except Exception as e:
            logger.warning(
                f"langchain_ollama requested but unavailable, falling back to SimpleOllama: {e}"
            )
    return SimpleOllama(
        base_url=config.ollama_host,
        model=config.ollama_model,
        num_ctx=config.num_ctx,
        num_predict=config.num_predict,
        temperature=config.temperature,
        top_p=config.top_p,
        timeout=config.llm_timeout,
    )


def _create_ollama_client(llm_config: LLMConfig) -> SimpleOllama:
    """Create Ollama client"""
    return SimpleOllama(
        base_url=llm_config.base_url or "http://localhost:11434",
        model=llm_config.model_name,
        num_ctx=llm_config.extra_params.get("num_ctx", config.num_ctx),
        num_predict=llm_config.max_tokens,
        temperature=llm_config.temperature,
        top_p=llm_config.top_p,
        timeout=llm_config.timeout,
    )


def _create_openai_client(llm_config: LLMConfig):
    """Create OpenAI-compatible client"""
    llm_config.validate()
    return OpenAICompatibleClient(
        api_key=llm_config.resolved_api_token,
        base_url=llm_config.base_url,
        model=llm_config.model_name,
        temperature=llm_config.temperature,
        max_tokens=llm_config.max_tokens,
        timeout=llm_config.timeout,
    )


def _create_anthropic_client(llm_config: LLMConfig):
    """Create Anthropic client"""
    llm_config.validate()
    return AnthropicClient(
        api_key=llm_config.resolved_api_token,
        model=llm_config.model_name,
        temperature=llm_config.temperature,
        max_tokens=llm_config.max_tokens,
        timeout=llm_config.timeout,
    )


def _create_gemini_client(llm_config: LLMConfig):
    """Create Google Gemini client"""
    llm_config.validate()
    return GeminiClient(
        api_key=llm_config.resolved_api_token,
        model=llm_config.model_name,
        temperature=llm_config.temperature,
        max_tokens=llm_config.max_tokens,
        timeout=llm_config.timeout,
    )


def _create_groq_client(llm_config: LLMConfig):
    """Create Groq client (OpenAI-compatible API)"""
    llm_config.validate()
    return OpenAICompatibleClient(
        api_key=llm_config.resolved_api_token,
        base_url=llm_config.base_url,
        model=llm_config.model_name,
        temperature=llm_config.temperature,
        max_tokens=llm_config.max_tokens,
        timeout=llm_config.timeout,
    )


def _create_deepseek_client(llm_config: LLMConfig):
    """Create DeepSeek client (OpenAI-compatible API)"""
    llm_config.validate()
    return OpenAICompatibleClient(
        api_key=llm_config.resolved_api_token,
        base_url=llm_config.base_url,
        model=llm_config.model_name,
        temperature=llm_config.temperature,
        max_tokens=llm_config.max_tokens,
        timeout=llm_config.timeout,
    )


class OpenAICompatibleClient:
    """
    OpenAI-compatible async client.
    Works with OpenAI, Groq, DeepSeek and other OpenAI-compatible APIs.
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int = 300,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
    
    async def ainvoke(self, prompt: str) -> dict:
        """Async invoke the LLM"""
        import aiohttp
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        
        timeout_obj = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"API error {resp.status}: {error_text}")
                data = await resp.json()
        
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"text": text}


class AnthropicClient:
    """Anthropic Claude async client"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-haiku-20240307",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int = 300,
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
    
    async def ainvoke(self, prompt: str) -> dict:
        """Async invoke Claude"""
        import aiohttp
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        
        # Only add temperature for non-thinking models
        if not self.model.startswith("claude-3-5-sonnet"):
            payload["temperature"] = self.temperature
        
        timeout_obj = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Anthropic API error {resp.status}: {error_text}")
                data = await resp.json()
        
        content = data.get("content", [])
        text = content[0].get("text", "") if content else ""
        return {"text": text}


class GeminiClient:
    """Google Gemini async client"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int = 300,
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
    
    async def ainvoke(self, prompt: str) -> dict:
        """Async invoke Gemini"""
        import aiohttp
        
        # Gemini API endpoint
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            }
        }
        
        timeout_obj = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Gemini API error {resp.status}: {error_text}")
                data = await resp.json()
        
        candidates = data.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            text = parts[0].get("text", "") if parts else ""
        else:
            text = ""
        
        return {"text": text}


class LiteLLMClient:
    """
    Universal LLM client using litellm.
    
    Supports any provider that litellm supports with automatic API key detection.
    Provider format: "provider/model" (e.g., "openai/gpt-4o", "anthropic/claude-3-haiku")
    
    See https://docs.litellm.ai/docs/providers for full list.
    """
    
    def __init__(self, llm_config: LLMConfig):
        self.config = llm_config
        # Model format for litellm: "provider/model"
        self.model = llm_config.provider
        self.temperature = llm_config.temperature
        self.max_tokens = llm_config.max_tokens
        self.timeout = llm_config.timeout
        
        # Set API key in environment if provided
        if llm_config.resolved_api_token:
            self._set_api_key(llm_config.provider_name, llm_config.resolved_api_token)
    
    def _set_api_key(self, provider: str, api_key: str):
        """Set API key for provider in environment"""
        env_var_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "google": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "cohere": "COHERE_API_KEY",
            "huggingface": "HUGGINGFACE_API_KEY",
            "azure": "AZURE_API_KEY",
            "mistral": "MISTRAL_API_KEY",
            "together": "TOGETHER_API_KEY",
            "anyscale": "ANYSCALE_API_KEY",
            "replicate": "REPLICATE_API_KEY",
        }
        env_var = env_var_map.get(provider)
        if env_var and api_key:
            os.environ[env_var] = api_key
    
    async def ainvoke(self, prompt: str) -> dict:
        """Async invoke the LLM using litellm"""
        import litellm
        
        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
            )
            
            text = response.choices[0].message.content
            return {"text": text}
            
        except Exception as e:
            logger.error(f"LiteLLM error for {self.model}: {e}")
            raise
    
    def invoke(self, prompt: str) -> dict:
        """Sync invoke the LLM using litellm"""
        import litellm
        
        try:
            response = litellm.completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
            )
            
            text = response.choices[0].message.content
            return {"text": text}
            
        except Exception as e:
            logger.error(f"LiteLLM error for {self.model}: {e}")
            raise
