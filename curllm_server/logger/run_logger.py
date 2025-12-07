"""Run Logger - Alias to centralized RunLogger"""

from curllm_core.logger import RunLogger as CoreRunLogger


class RunLogger(CoreRunLogger):
    """Alias to centralized RunLogger with TOC and image support"""
    pass
