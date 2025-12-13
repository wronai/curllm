"""
Log Entry - Core data structures for logging
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path


class LogLevel(Enum):
    """Log severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    PHASE = "phase"
    STEP = "step"


@dataclass
class StepLog:
    """Log entry for a single execution step"""
    index: int
    step_type: str
    description: str
    status: str  # pending, running, completed, failed, skipped
    duration_ms: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Details
    selector_used: Optional[str] = None
    selector_confidence: float = 0.0
    method: str = "unknown"  # llm, heuristic, fallback
    
    # Results
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    # Screenshots
    screenshot_before: Optional[str] = None
    screenshot_after: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "step_type": self.step_type,
            "description": self.description,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "selector_used": self.selector_used,
            "selector_confidence": self.selector_confidence,
            "method": self.method,
            "result_data": self.result_data,
            "error_message": self.error_message,
            "screenshot_before": self.screenshot_before,
            "screenshot_after": self.screenshot_after,
        }


@dataclass
class LogEntry:
    """A single log entry with timestamp and level"""
    timestamp: datetime
    level: LogLevel
    message: str
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "message": self.message,
            "details": self.details,
        }
    
    def format(self, include_timestamp: bool = True) -> str:
        """Format entry as string"""
        ts = f"[{self.timestamp.strftime('%H:%M:%S.%f')[:-3]}] " if include_timestamp else ""
        level_icon = {
            LogLevel.DEBUG: "🔍",
            LogLevel.INFO: "ℹ️",
            LogLevel.WARNING: "⚠️",
            LogLevel.ERROR: "❌",
            LogLevel.SUCCESS: "✅",
            LogLevel.PHASE: "📋",
            LogLevel.STEP: "▶️",
        }.get(self.level, "")
        return f"{ts}{level_icon} {self.message}"


@dataclass
class CommandInfo:
    """Information about the executed command"""
    raw_command: str
    cli_format: str  # curllm "..."
    traditional_format: Optional[str] = None  # curllm "url" -d "..."
    
    # Parsed info
    target_url: Optional[str] = None
    target_domain: Optional[str] = None
    instruction: Optional[str] = None
    goal: Optional[str] = None
    
    # Form data
    email: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    message: Optional[str] = None
    
    # Confidence
    parse_confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_command": self.raw_command,
            "cli_format": self.cli_format,
            "traditional_format": self.traditional_format,
            "target_url": self.target_url,
            "target_domain": self.target_domain,
            "instruction": self.instruction,
            "goal": self.goal,
            "form_data": {
                "email": self.email,
                "name": self.name,
                "phone": self.phone,
                "message": self.message,
            },
            "parse_confidence": self.parse_confidence,
        }


@dataclass
class EnvironmentInfo:
    """Environment and configuration information"""
    model: str = "unknown"
    ollama_host: str = ""
    headless: bool = True
    stealth_mode: bool = False
    visual_mode: bool = False
    proxy: Optional[str] = None
    locale: str = "en-US"
    timezone: str = "UTC"
    
    # Browser info
    browser_type: str = "chromium"
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: Optional[str] = None
    
    # Additional config
    extra_config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "model": self.model,
            "ollama_host": self.ollama_host,
            "headless": self.headless,
            "stealth_mode": self.stealth_mode,
            "visual_mode": self.visual_mode,
            "proxy": self.proxy,
            "locale": self.locale,
            "timezone": self.timezone,
            "browser": {
                "type": self.browser_type,
                "viewport": f"{self.viewport_width}x{self.viewport_height}",
                "user_agent": self.user_agent,
            },
        }
        result.update(self.extra_config)
        return result


@dataclass 
class ResultInfo:
    """Execution result information"""
    success: bool
    final_url: Optional[str] = None
    duration_ms: int = 0
    steps_total: int = 0
    steps_completed: int = 0
    steps_failed: int = 0
    
    # Data
    extracted_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    # Files
    screenshots: List[str] = field(default_factory=list)
    downloads: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "final_url": self.final_url,
            "duration_ms": self.duration_ms,
            "steps": {
                "total": self.steps_total,
                "completed": self.steps_completed,
                "failed": self.steps_failed,
            },
            "extracted_data": self.extracted_data,
            "error": {
                "message": self.error_message,
                "type": self.error_type,
            } if self.error_message else None,
            "files": {
                "screenshots": [s.to_dict() if hasattr(s, 'to_dict') else s for s in self.screenshots],
                "downloads": self.downloads,
            },
        }
