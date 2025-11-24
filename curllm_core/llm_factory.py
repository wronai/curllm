import os
import logging
from .config import config
from .llm import SimpleOllama


def setup_llm():
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
            logging.getLogger(__name__).warning(
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
