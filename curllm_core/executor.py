"""DEPRECATED: Use curllm_core.execution instead"""
from curllm_core.execution.executor import CurllmExecutor
from curllm_core.llm_config import LLMConfig
__all__ = ['CurllmExecutor', 'LLMConfig']
