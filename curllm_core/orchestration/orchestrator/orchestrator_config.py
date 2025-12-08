from dataclasses import dataclass


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
    log_dir: str = "logs"
    screenshot_dir: str = "screenshots"
    dry_run: bool = False  # Parse and plan only, don't execute
    auto_captcha_visible: bool = True  # Auto-switch to visible mode on CAPTCHA
    captcha_wait_seconds: int = 60  # How long to wait for user to solve CAPTCHA

