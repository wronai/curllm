"""
Config Component - Configuration and runtime settings.
"""

# Re-export from main config
def get_config():
    from curllm_core.config import config
    return config

def get_runtime():
    from curllm_core.runtime import get_runtime as _get
    return _get()

def get_logger(*args, **kwargs):
    from curllm_core.logger import RunLogger
    return RunLogger(*args, **kwargs)

__all__ = ['get_config', 'get_runtime', 'get_logger']
