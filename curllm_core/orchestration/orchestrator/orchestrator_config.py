import os
from pathlib import Path
from dataclasses import dataclass


def default_log_dir() -> str:
    """
    Resolve log directory anchored to repo root.
    - If CURLLM_LOG_DIR is set:
        * absolute path is used as-is
        * relative path is resolved against repo root (then cwd as last resort)
    - Otherwise defaults to <repo_root>/logs (or cwd/logs if repo root missing)
    """
    env_dir = os.getenv("CURLLM_LOG_DIR")
    try:
        # /curllm_core/orchestration/orchestrator/orchestrator_config.py -> parents[4] == repo root (curllm)
        repo_root = Path(__file__).resolve().parents[4]
    except Exception:
        repo_root = None

    if env_dir:
        path = Path(env_dir).expanduser()
        if not path.is_absolute():
            if repo_root:
                path = repo_root / path
            else:
                path = Path.cwd() / path
        return str(path)

    if repo_root:
        return str(repo_root / "logs")

    return str(Path.cwd() / "logs")


@dataclass
class OrchestratorConfig:
    """Configuration for orchestrator"""
    headless: bool = True
    stealth_mode: bool = True
    timeout_seconds: int = 120
    screenshot_on_error: bool = True
    screenshot_on_success: bool = True
    screenshot_each_step: bool = False  # Capture after each step
    log_to_file: bool = True
    log_dir: str = default_log_dir()
    screenshot_dir: str = "screenshots"
    dry_run: bool = False  # Parse and plan only, don't execute
    auto_captcha_visible: bool = True  # Auto-switch to visible mode on CAPTCHA
    captcha_wait_seconds: int = 60  # How long to wait for user to solve CAPTCHA

