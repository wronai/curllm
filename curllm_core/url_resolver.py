"""DEPRECATED: Use curllm_core.url_resolution instead"""
from curllm_core.url_resolution.resolver import UrlResolver
from curllm_core.url_types import TaskGoal, PageMatchResult, ResolvedUrl
__all__ = ['UrlResolver', 'TaskGoal', 'PageMatchResult', 'ResolvedUrl']
