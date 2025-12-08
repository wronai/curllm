#!/usr/bin/env python3
"""
CLI for Orchestrator - Execute complex natural language commands

This module provides backward compatibility.
The implementation is in curllm_core.deprecated.cli_orchestrator.

Usage:
    python -m curllm_core.cli_orchestrator "Wejdź na example.com i wyślij formularz..."
    
    # Dry run (parse and plan only)
    python -m curllm_core.cli_orchestrator --dry-run "..."
    
    # With visible browser
    python -m curllm_core.cli_orchestrator --visible "..."
"""

import asyncio
import sys

# Re-export everything from deprecated module
from curllm_core.deprecated.cli_orchestrator import *

if __name__ == "__main__":
    from curllm_core.deprecated.cli_orchestrator import main
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
