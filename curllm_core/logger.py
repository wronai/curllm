#!/usr/bin/env python3
"""
Legacy logger module - imports from curllm_logs for backward compatibility.

The RunLogger class has been moved to curllm_logs.run_logger.
This module re-exports it for backward compatibility.
"""

# Re-export from curllm_logs
from curllm_logs import RunLogger, create_run_logger

__all__ = ['RunLogger', 'create_run_logger']
