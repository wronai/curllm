"""
curllm_logs - Standardized logging package for curllm

This package provides:
- Unified log format for all curllm operations
- Markdown, JSON, HTML report generation
- Screenshot capture and organization
- Image embedding support
- Parameter tracking
- Multi-domain session logging

Usage:
    from curllm_logs import LogSession, ScreenshotManager, MarkdownLogWriter
    
    # Create session
    session = create_session(session_type="orchestrator")
    
    # Setup screenshots
    screenshots = ScreenshotManager(session_id=session.session_id, domain="example.com")
    
    # Capture during execution
    await screenshots.capture(page, step_index=0, step_type="navigate")
    
    # Save log with screenshots
    writer = MarkdownLogWriter(include_images=True)
    writer.write(session, "logs/run.md")
"""

from .log_entry import (
    LogEntry, LogLevel, StepLog,
    CommandInfo, EnvironmentInfo, ResultInfo
)
from .log_session import LogSession, create_session
from .log_writer import LogWriter, MarkdownLogWriter, JSONLogWriter, HTMLLogWriter
from .log_config import LogConfig
from .screenshots import (
    ScreenshotManager, ScreenshotInfo,
    cleanup_old_screenshots, capture_page_screenshot
)
from .run_logger import RunLogger, create_run_logger

__all__ = [
    # Log entries
    'LogEntry',
    'LogLevel', 
    'StepLog',
    'CommandInfo',
    'EnvironmentInfo',
    'ResultInfo',
    
    # Session management
    'LogSession',
    'create_session',
    
    # Writers
    'LogWriter',
    'MarkdownLogWriter',
    'JSONLogWriter',
    'HTMLLogWriter',
    
    # Configuration
    'LogConfig',
    
    # Screenshots
    'ScreenshotManager',
    'ScreenshotInfo',
    'cleanup_old_screenshots',
    'capture_page_screenshot',
    
    # Run Logger (legacy compatibility)
    'RunLogger',
    'create_run_logger',
]

__version__ = '1.0.0'
