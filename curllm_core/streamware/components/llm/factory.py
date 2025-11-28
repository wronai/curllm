"""
LLM Factory - Create and configure LLM instances.
"""
import os
import logging
from typing import Optional, Any

from .client import SimpleOllama, OllamaClient

logger = logging.getLogger(__name__)

# Singleton LLM instance
_llm_instance: Optional[OllamaClient] = None


def setup_llm(
    backend: str = None,
    model: str = None,
    base_url: str = None,
    **kwargs
) -> Any:
    """
    Set up and return an LLM instance.
    
    Args:
        backend: "simple" or "langchain"
        model: Model name
        base_url: Ollama host URL
        **kwargs: Additional options (temperature, num_ctx, etc.)
        
    Returns:
        LLM instance
    """
    # Get config (lazy import to avoid circular deps)
    try:
        from curllm_core.config import config
        default_host = config.ollama_host
        default_model = config.ollama_model
        default_temp = config.temperature
        default_top_p = config.top_p
        default_ctx = config.num_ctx
        default_predict = config.num_predict
        default_timeout = config.llm_timeout
    except ImportError:
        default_host = os.getenv("CURLLM_OLLAMA_HOST", "http://localhost:11434")
        default_model = os.getenv("CURLLM_MODEL", "qwen2.5:7b")
        default_temp = 0.1
        default_top_p = 0.9
        default_ctx = 4096
        default_predict = 1024
        default_timeout = 300
    
    backend = backend or os.getenv("CURLLM_LLM_BACKEND", "simple").lower()
    base_url = base_url or default_host
    model = model or default_model
    
    if backend == "langchain":
        try:
            from langchain_ollama import OllamaLLM
            return OllamaLLM(
                base_url=base_url,
                model=model,
                temperature=kwargs.get("temperature", default_temp),
                top_p=kwargs.get("top_p", default_top_p),
                num_ctx=kwargs.get("num_ctx", default_ctx),
                num_predict=kwargs.get("num_predict", default_predict),
            )
        except Exception as e:
            logger.warning(
                f"langchain_ollama requested but unavailable, falling back to SimpleOllama: {e}"
            )
    
    return SimpleOllama(
        base_url=base_url,
        model=model,
        num_ctx=kwargs.get("num_ctx", default_ctx),
        num_predict=kwargs.get("num_predict", default_predict),
        temperature=kwargs.get("temperature", default_temp),
        top_p=kwargs.get("top_p", default_top_p),
        timeout=kwargs.get("timeout", default_timeout),
    )


def get_llm() -> OllamaClient:
    """
    Get singleton LLM instance.
    
    Creates instance on first call.
    
    Returns:
        OllamaClient instance
    """
    global _llm_instance
    
    if _llm_instance is None:
        try:
            from curllm_core.config import config
            base_url = config.ollama_host
            model = config.ollama_model
            num_ctx = config.num_ctx
            num_predict = config.num_predict
            temperature = config.temperature
            top_p = config.top_p
            timeout = config.llm_timeout
        except ImportError:
            base_url = os.getenv("CURLLM_OLLAMA_HOST", "http://localhost:11434")
            model = os.getenv("CURLLM_MODEL", "qwen2.5:7b")
            num_ctx = 4096
            num_predict = 1024
            temperature = 0.1
            top_p = 0.9
            timeout = 300
        
        _llm_instance = OllamaClient(
            base_url=base_url,
            model=model,
            num_ctx=num_ctx,
            num_predict=num_predict,
            temperature=temperature,
            top_p=top_p,
            timeout=timeout
        )
        
        logger.debug(f"LLM initialized: {model} @ {base_url}")
    
    return _llm_instance


def reset_llm():
    """Reset singleton LLM instance."""
    global _llm_instance
    _llm_instance = None


def set_llm_logger(llm_logger):
    """Set logger for LLM instance."""
    llm = get_llm()
    llm.set_logger(llm_logger)
