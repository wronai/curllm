"""Convenience function for executing commands"""

from typing import Optional

from curllm_core.orchestration.models import OrchestratorConfig, OrchestratorResult
from curllm_core.orchestration.orchestrator import Orchestrator


async def execute_command(
    command: str,
    config: Optional[OrchestratorConfig] = None
) -> OrchestratorResult:
    """Convenience function to execute a command."""
    orchestrator = Orchestrator(config)
    return await orchestrator.execute(command)
