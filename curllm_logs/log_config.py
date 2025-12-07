"""
Log Configuration - Settings for logging behavior
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class LogConfig:
    """Configuration for logging"""
    
    # Directories
    log_dir: str = "logs"
    screenshot_dir: str = "screenshots"
    
    # Output formats
    output_formats: List[str] = field(default_factory=lambda: ["markdown"])  # markdown, json, html
    
    # Content options
    include_raw_log: bool = True
    include_images: bool = True
    include_environment: bool = True
    include_json_section: bool = True
    
    # Image embedding
    embed_images_base64: bool = False  # If True, embed as base64 in HTML
    max_screenshots: int = 10
    
    # Log retention
    keep_logs_days: int = 30
    max_log_size_mb: float = 10.0
    
    # Real-time logging
    log_to_console: bool = True
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> 'LogConfig':
        """Create config from environment variables"""
        return cls(
            log_dir=os.getenv("CURLLM_LOG_DIR", "logs"),
            screenshot_dir=os.getenv("CURLLM_SCREENSHOT_DIR", "screenshots"),
            include_raw_log=os.getenv("CURLLM_LOG_INCLUDE_RAW", "true").lower() == "true",
            include_images=os.getenv("CURLLM_LOG_INCLUDE_IMAGES", "true").lower() == "true",
            log_to_console=os.getenv("CURLLM_LOG_CONSOLE", "true").lower() == "true",
            log_level=os.getenv("CURLLM_LOG_LEVEL", "INFO"),
        )
    
    def get_log_path(self, session_id: str, format: str = "md") -> str:
        """Get the path for a log file"""
        os.makedirs(self.log_dir, exist_ok=True)
        return os.path.join(self.log_dir, f"run-{session_id}.{format}")
    
    def get_screenshot_path(self, session_id: str, step: int, suffix: str = "") -> str:
        """Get the path for a screenshot"""
        os.makedirs(self.screenshot_dir, exist_ok=True)
        name = f"{session_id}_step{step}"
        if suffix:
            name += f"_{suffix}"
        return os.path.join(self.screenshot_dir, f"{name}.png")
