"""
Log Session - Manages a complete logging session
"""

import os
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

from .log_entry import (
    LogEntry, LogLevel, StepLog,
    CommandInfo, EnvironmentInfo, ResultInfo
)


@dataclass
class LogSession:
    """
    A complete logging session for a curllm execution.
    
    Collects all information during execution and can be
    serialized to various formats (Markdown, JSON, HTML).
    """
    
    # Session identity
    session_id: str
    session_type: str = "orchestrator"  # orchestrator, api, bql
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    # Command info
    command: Optional[CommandInfo] = None
    
    # Environment
    environment: Optional[EnvironmentInfo] = None
    
    # Execution plan
    plan_steps: List[str] = field(default_factory=list)
    
    # Step logs
    steps: List[StepLog] = field(default_factory=list)
    
    # Raw log entries
    entries: List[LogEntry] = field(default_factory=list)
    
    # Result
    result: Optional[ResultInfo] = None
    
    # Related domains/URLs visited
    domains_visited: List[str] = field(default_factory=list)
    urls_visited: List[str] = field(default_factory=list)
    
    # Files
    log_dir: str = "logs"
    screenshot_dir: str = "screenshots"
    screenshots: List[str] = field(default_factory=list)
    
    def log(self, level: LogLevel, message: str, details: Optional[Dict] = None):
        """Add a log entry"""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            details=details
        )
        self.entries.append(entry)
        return entry
    
    def info(self, message: str, details: Optional[Dict] = None):
        return self.log(LogLevel.INFO, message, details)
    
    def error(self, message: str, details: Optional[Dict] = None):
        return self.log(LogLevel.ERROR, message, details)
    
    def success(self, message: str, details: Optional[Dict] = None):
        return self.log(LogLevel.SUCCESS, message, details)
    
    def warning(self, message: str, details: Optional[Dict] = None):
        return self.log(LogLevel.WARNING, message, details)
    
    def phase(self, message: str, details: Optional[Dict] = None):
        return self.log(LogLevel.PHASE, message, details)
    
    def step(self, message: str, details: Optional[Dict] = None):
        return self.log(LogLevel.STEP, message, details)
    
    def add_step(self, step: StepLog):
        """Add a step log"""
        self.steps.append(step)
    
    def add_url(self, url: str):
        """Track a visited URL"""
        if url and url not in self.urls_visited:
            self.urls_visited.append(url)
            # Extract domain
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain and domain not in self.domains_visited:
                self.domains_visited.append(domain)
    
    def add_screenshot(self, path: str):
        """Add a screenshot"""
        if path and path not in self.screenshots:
            self.screenshots.append(path)
    
    def finish(self, success: bool, error: Optional[str] = None):
        """Finish the session"""
        self.end_time = datetime.now()
        
        if not self.result:
            self.result = ResultInfo(success=success)
        
        self.result.success = success
        if error:
            self.result.error_message = error
        
        # Calculate duration
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.result.duration_ms = int(delta.total_seconds() * 1000)
        
        # Count steps
        self.result.steps_total = len(self.steps)
        self.result.steps_completed = sum(1 for s in self.steps if s.status == "completed")
        self.result.steps_failed = sum(1 for s in self.steps if s.status == "failed")
        self.result.screenshots = self.screenshots
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "session_id": self.session_id,
            "session_type": self.session_type,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "command": self.command.to_dict() if self.command else None,
            "environment": self.environment.to_dict() if self.environment else None,
            "plan": self.plan_steps,
            "steps": [s.to_dict() for s in self.steps],
            "domains_visited": self.domains_visited,
            "urls_visited": self.urls_visited,
            "screenshots": [s.to_dict() if hasattr(s, 'to_dict') else s for s in self.screenshots],
            "result": self.result.to_dict() if self.result else None,
            "entries": [e.to_dict() for e in self.entries],
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogSession':
        """Create session from dictionary"""
        session = cls(
            session_id=data.get("session_id", ""),
            session_type=data.get("session_type", "orchestrator"),
        )
        
        if data.get("start_time"):
            session.start_time = datetime.fromisoformat(data["start_time"])
        if data.get("end_time"):
            session.end_time = datetime.fromisoformat(data["end_time"])
        
        session.plan_steps = data.get("plan", [])
        session.domains_visited = data.get("domains_visited", [])
        session.urls_visited = data.get("urls_visited", [])
        session.screenshots = data.get("screenshots", [])
        
        return session


def create_session(
    session_type: str = "orchestrator",
    log_dir: str = "logs"
) -> LogSession:
    """Create a new logging session"""
    session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    return LogSession(
        session_id=session_id,
        session_type=session_type,
        log_dir=log_dir
    )
