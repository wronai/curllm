#!/usr/bin/env python3
"""
LLMConfig - Universal LLM Provider Configuration

Supports multiple providers:
- ollama/model_name (default, local)
- openai/gpt-4o-mini, openai/gpt-4o, openai/o1-mini, openai/o3-mini
- anthropic/claude-3-haiku-20240307, claude-3-opus, claude-3-5-sonnet
- gemini/gemini-pro, gemini-1.5-pro, gemini-2.0-flash
- groq/llama3-70b-8192, groq/llama3-8b-8192
- deepseek/deepseek-chat

Usage:
    llm_config = LLMConfig(provider="openai/gpt-4o-mini", api_token="sk-...")
    llm_config = LLMConfig(provider="anthropic/claude-3-haiku-20240307")  # Uses env var
    llm_config = LLMConfig(provider="gemini/gemini-2.0-flash", api_token="env:GEMINI_API_KEY")
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


# Provider to environment variable mapping
PROVIDER_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "google": "GEMINI_API_KEY",  # alias
    "groq": "GROQ_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "ollama": None,  # Ollama doesn't need API key
}

# Provider to base URL mapping
PROVIDER_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    "google": "https://generativelanguage.googleapis.com/v1beta",
    "groq": "https://api.groq.com/openai/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "ollama": "http://localhost:11434",
}

# Default models per provider
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-haiku-20240307",
    "gemini": "gemini-2.0-flash",
    "google": "gemini-2.0-flash",
    "groq": "llama3-70b-8192",
    "deepseek": "deepseek-chat",
    "ollama": "qwen2.5:7b",
}


@dataclass
class LLMConfig:
    """
    Universal LLM provider configuration.
    
    Parameters:
        provider: Format "provider/model" e.g. "openai/gpt-4o-mini", "ollama/llama3"
                  Supported providers: ollama, openai, anthropic, gemini, groq, deepseek
        api_token: Optional. If not provided, reads from environment variable based on provider.
                   Can also use "env:VAR_NAME" format to specify custom env var.
        base_url: Optional. Custom API endpoint for the provider.
        temperature: LLM temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        timeout: Request timeout in seconds
        extra_params: Additional provider-specific parameters
    """
    provider: str = "ollama/qwen2.5:7b"
    api_token: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: int = 300
    top_p: float = 0.9
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Parse provider string
        parts = self.provider.split("/", 1)
        self._provider_name = parts[0].lower()
        self._model_name = parts[1] if len(parts) > 1 else DEFAULT_MODELS.get(self._provider_name, "")
        
        # Resolve API token
        self._resolved_token = self._resolve_api_token()
        
        # Set base URL if not provided
        if self.base_url is None:
            self.base_url = PROVIDER_BASE_URLS.get(self._provider_name, PROVIDER_BASE_URLS["ollama"])
    
    def _resolve_api_token(self) -> Optional[str]:
        """Resolve API token from various sources."""
        if self.api_token is None:
            # Read from default environment variable
            env_var = PROVIDER_ENV_VARS.get(self._provider_name)
            if env_var:
                return os.getenv(env_var)
            return None
        
        if self.api_token.startswith("env:"):
            # Read from specified environment variable
            env_var = self.api_token[4:].strip()
            return os.getenv(env_var)
        
        return self.api_token
    
    @property
    def provider_name(self) -> str:
        """Get provider name (openai, anthropic, etc.)"""
        return self._provider_name
    
    @property
    def model_name(self) -> str:
        """Get model name"""
        return self._model_name
    
    @property
    def resolved_api_token(self) -> Optional[str]:
        """Get resolved API token"""
        return self._resolved_token
    
    @property
    def is_local(self) -> bool:
        """Check if this is a local provider (ollama)"""
        return self._provider_name == "ollama"
    
    @property
    def requires_api_key(self) -> bool:
        """Check if this provider requires an API key"""
        return self._provider_name != "ollama"
    
    def validate(self) -> bool:
        """Validate configuration"""
        if self.requires_api_key and not self._resolved_token:
            env_var = PROVIDER_ENV_VARS.get(self._provider_name, "unknown")
            raise ValueError(
                f"API token required for {self._provider_name}. "
                f"Set api_token or {env_var} environment variable."
            )
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "provider": self.provider,
            "provider_name": self._provider_name,
            "model_name": self._model_name,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "top_p": self.top_p,
            "has_api_token": self._resolved_token is not None,
            "is_local": self.is_local,
        }
    
    @classmethod
    def from_env(cls, prefix: str = "CURLLM") -> "LLMConfig":
        """
        Create LLMConfig from environment variables.
        
        Reads:
            {prefix}_LLM_PROVIDER or falls back to ollama
            {prefix}_LLM_API_TOKEN
            {prefix}_LLM_BASE_URL
            {prefix}_TEMPERATURE
            {prefix}_NUM_PREDICT (max_tokens)
            {prefix}_LLM_TIMEOUT
        """
        provider = os.getenv(f"{prefix}_LLM_PROVIDER", "ollama/qwen2.5:7b")
        api_token = os.getenv(f"{prefix}_LLM_API_TOKEN")
        base_url = os.getenv(f"{prefix}_LLM_BASE_URL")
        temperature = float(os.getenv(f"{prefix}_TEMPERATURE", "0.3"))
        max_tokens = int(os.getenv(f"{prefix}_NUM_PREDICT", "4096"))
        timeout = int(os.getenv(f"{prefix}_LLM_TIMEOUT", "300"))
        
        return cls(
            provider=provider,
            api_token=api_token,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )


# Predefined configurations for common use cases
class LLMPresets:
    """Predefined LLM configurations"""
    
    @staticmethod
    def local_fast() -> LLMConfig:
        """Fast local model for quick tasks"""
        return LLMConfig(provider="ollama/qwen2.5:3b", temperature=0.2, max_tokens=1024)
    
    @staticmethod
    def local_balanced() -> LLMConfig:
        """Balanced local model (default)"""
        return LLMConfig(provider="ollama/qwen2.5:7b", temperature=0.3, max_tokens=4096)
    
    @staticmethod
    def local_smart() -> LLMConfig:
        """Smarter local model for complex tasks"""
        return LLMConfig(provider="ollama/qwen2.5:14b", temperature=0.3, max_tokens=8192)
    
    @staticmethod
    def openai_fast() -> LLMConfig:
        """Fast OpenAI model"""
        return LLMConfig(provider="openai/gpt-4o-mini", temperature=0.2)
    
    @staticmethod
    def openai_smart() -> LLMConfig:
        """Smart OpenAI model"""
        return LLMConfig(provider="openai/gpt-4o", temperature=0.3)
    
    @staticmethod
    def anthropic_fast() -> LLMConfig:
        """Fast Anthropic model"""
        return LLMConfig(provider="anthropic/claude-3-haiku-20240307", temperature=0.2)
    
    @staticmethod
    def anthropic_smart() -> LLMConfig:
        """Smart Anthropic model"""
        return LLMConfig(provider="anthropic/claude-3-5-sonnet-20240620", temperature=0.3)
    
    @staticmethod
    def gemini_fast() -> LLMConfig:
        """Fast Gemini model"""
        return LLMConfig(provider="gemini/gemini-2.0-flash", temperature=0.2)
    
    @staticmethod
    def groq_fast() -> LLMConfig:
        """Fast Groq model (cloud-hosted Llama)"""
        return LLMConfig(provider="groq/llama3-8b-8192", temperature=0.2)
    
    @staticmethod
    def groq_smart() -> LLMConfig:
        """Smart Groq model"""
        return LLMConfig(provider="groq/llama3-70b-8192", temperature=0.3)
    
    @staticmethod
    def deepseek() -> LLMConfig:
        """DeepSeek model"""
        return LLMConfig(provider="deepseek/deepseek-chat", temperature=0.3)
