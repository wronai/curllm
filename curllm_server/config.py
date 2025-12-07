"""Application configuration for curllm server"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration"""
    ollama_host: str = os.getenv("CURLLM_OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("CURLLM_MODEL", "qwen2.5:7b")
    browserless_url: str = os.getenv("BROWSERLESS_URL", "ws://localhost:3000")
    use_browserless: bool = os.getenv("CURLLM_BROWSERLESS", "false").lower() == "true"
    max_steps: int = int(os.getenv("CURLLM_MAX_STEPS", "20"))
    screenshot_dir: Path = Path(os.getenv("CURLLM_SCREENSHOT_DIR", "./screenshots"))
    enable_debug: bool = os.getenv("CURLLM_DEBUG", "false").lower() == "true"
    api_port: int = int(os.getenv("CURLLM_API_PORT", os.getenv("API_PORT", "8000")))
    num_ctx: int = int(os.getenv("CURLLM_NUM_CTX", "8192"))
    num_predict: int = int(os.getenv("CURLLM_NUM_PREDICT", "512"))
    temperature: float = float(os.getenv("CURLLM_TEMPERATURE", "0.3"))
    top_p: float = float(os.getenv("CURLLM_TOP_P", "0.9"))
    headless: bool = os.getenv("CURLLM_HEADLESS", "true").lower() == "true"
    locale: str = os.getenv("CURLLM_LOCALE", os.getenv("LOCALE", "pl-PL"))
    timezone_id: str = os.getenv("CURLLM_TIMEZONE", os.getenv("TIMEZONE", "Europe/Warsaw"))
    proxy: Optional[str] = (
        os.getenv("CURLLM_PROXY") or 
        os.getenv("HTTPS_PROXY") or 
        os.getenv("HTTP_PROXY") or 
        None
    )
    # Logging and truncation controls
    log_preview_chars: int = int(os.getenv("CURLLM_LOG_PREVIEW_CHARS", "1500"))
    log_prompt_chars: int = int(os.getenv("CURLLM_LOG_PROMPT_CHARS", "3000"))
    no_progress_text_chars: int = int(os.getenv("CURLLM_NO_PROGRESS_TEXT_CHARS", "500"))
    # Collection limits
    max_links: int = int(os.getenv("CURLLM_MAX_LINKS", "100"))
    max_emails: int = int(os.getenv("CURLLM_MAX_EMAILS", "100"))
    max_phones: int = int(os.getenv("CURLLM_MAX_PHONES", "100"))
    # Planner behavior
    stall_limit_default: int = int(os.getenv("CURLLM_STALL_LIMIT", "3"))
    
    def __post_init__(self):
        self.screenshot_dir.mkdir(exist_ok=True)


# Global config instance
config = Config()
