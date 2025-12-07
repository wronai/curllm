"""
Screenshot Manager - Capture and organize screenshots for logging

Handles:
- Screenshot capture with Playwright
- Organized directory structure per session/run
- Thumbnail generation
- Cleanup of old screenshots
- Embedding screenshots in logs
"""

import os
import logging
import base64
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


@dataclass
class ScreenshotInfo:
    """Information about a captured screenshot"""
    path: str
    filename: str
    step_index: int
    step_type: str
    timestamp: datetime
    
    # Metadata
    url: Optional[str] = None
    description: Optional[str] = None
    is_debug: bool = False
    
    # Dimensions
    width: int = 0
    height: int = 0
    
    # For embedding
    base64_data: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "filename": self.filename,
            "step_index": self.step_index,
            "step_type": self.step_type,
            "timestamp": self.timestamp.isoformat(),
            "url": self.url,
            "description": self.description,
            "is_debug": self.is_debug,
            "width": self.width,
            "height": self.height,
        }
    
    def get_relative_path(self, from_dir: str) -> str:
        """Get path relative to a directory"""
        try:
            return os.path.relpath(self.path, from_dir)
        except ValueError:
            return self.path
    
    def get_markdown_embed(self, relative_to: Optional[str] = None) -> str:
        """Get markdown image embed"""
        path = self.get_relative_path(relative_to) if relative_to else self.path
        alt = self.description or f"Step {self.step_index}: {self.step_type}"
        return f"![{alt}]({path})"
    
    def get_base64_embed(self) -> Optional[str]:
        """Get base64 data URI for embedding"""
        if self.base64_data:
            return f"data:image/png;base64,{self.base64_data}"
        return None
    
    def load_base64(self):
        """Load the image as base64"""
        if os.path.exists(self.path):
            with open(self.path, "rb") as f:
                self.base64_data = base64.b64encode(f.read()).decode("utf-8")


class ScreenshotManager:
    """
    Manages screenshot capture and organization for a logging session.
    
    Directory structure:
    screenshots/
    └── domain.com/
        └── run-20251207-151904/
            ├── step_0_navigate.png
            ├── step_1_resolve.png
            ├── step_2_fill_email.png
            ├── debug_before_submit.png
            └── final.png
    """
    
    def __init__(
        self,
        base_dir: str = "screenshots",
        session_id: Optional[str] = None,
        domain: Optional[str] = None,
        create_thumbnails: bool = False,
        max_screenshots: int = 50,
    ):
        self.base_dir = Path(base_dir)
        self.session_id = session_id or datetime.now().strftime("%Y%m%d-%H%M%S")
        self.domain = domain or "unknown"
        self.create_thumbnails = create_thumbnails
        self.max_screenshots = max_screenshots
        
        # Screenshots taken in this session
        self.screenshots: List[ScreenshotInfo] = []
        
        # Create session directory
        self.session_dir = self._get_session_dir()
        self.session_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_session_dir(self) -> Path:
        """Get the directory for this session's screenshots"""
        # Sanitize domain
        safe_domain = self.domain.replace("://", "_").replace("/", "_").replace(":", "_")
        return self.base_dir / safe_domain / f"run-{self.session_id}"
    
    def _generate_filename(
        self,
        step_index: int,
        step_type: str,
        is_debug: bool = False,
        suffix: str = ""
    ) -> str:
        """Generate a descriptive filename for a screenshot"""
        safe_type = step_type.replace(" ", "_").replace("/", "_")[:30]
        
        if is_debug:
            name = f"debug_{safe_type}"
        else:
            name = f"step_{step_index}_{safe_type}"
        
        if suffix:
            name += f"_{suffix}"
        
        # Add timestamp for uniqueness
        ts = datetime.now().strftime("%H%M%S")
        return f"{name}_{ts}.png"
    
    async def capture(
        self,
        page: "Page",
        step_index: int,
        step_type: str,
        description: Optional[str] = None,
        is_debug: bool = False,
        full_page: bool = False,
    ) -> ScreenshotInfo:
        """
        Capture a screenshot during execution.
        
        Args:
            page: Playwright page object
            step_index: Current step number
            step_type: Type of step (navigate, fill_field, etc.)
            description: Optional description for the screenshot
            is_debug: Whether this is a debug screenshot
            full_page: Whether to capture full page or just viewport
            
        Returns:
            ScreenshotInfo with path and metadata
        """
        if len(self.screenshots) >= self.max_screenshots:
            logger.warning(f"Max screenshots ({self.max_screenshots}) reached, skipping")
            return None
        
        filename = self._generate_filename(step_index, step_type, is_debug)
        filepath = self.session_dir / filename
        
        try:
            # Capture screenshot
            await page.screenshot(
                path=str(filepath),
                full_page=full_page,
            )
            
            # Get page info
            url = page.url
            viewport = page.viewport_size or {}
            
            # Create info object
            info = ScreenshotInfo(
                path=str(filepath),
                filename=filename,
                step_index=step_index,
                step_type=step_type,
                timestamp=datetime.now(),
                url=url,
                description=description or f"Step {step_index}: {step_type}",
                is_debug=is_debug,
                width=viewport.get("width", 0),
                height=viewport.get("height", 0),
            )
            
            self.screenshots.append(info)
            logger.debug(f"Screenshot captured: {filepath}")
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return None
    
    async def capture_step(
        self,
        page: "Page",
        step_index: int,
        step_type: str,
        before: bool = False,
        after: bool = True,
    ) -> Dict[str, Optional[ScreenshotInfo]]:
        """
        Capture screenshots before and/or after a step.
        
        Args:
            page: Playwright page
            step_index: Step number
            step_type: Type of step
            before: Capture before step execution
            after: Capture after step execution
            
        Returns:
            Dict with 'before' and 'after' ScreenshotInfo
        """
        result = {"before": None, "after": None}
        
        if before:
            result["before"] = await self.capture(
                page, step_index, step_type,
                description=f"Before: {step_type}",
                is_debug=True
            )
        
        if after:
            result["after"] = await self.capture(
                page, step_index, step_type,
                description=f"After: {step_type}"
            )
        
        return result
    
    async def capture_final(self, page: "Page") -> Optional[ScreenshotInfo]:
        """Capture final state screenshot"""
        return await self.capture(
            page,
            step_index=len(self.screenshots),
            step_type="final",
            description="Final state",
            full_page=True
        )
    
    async def capture_error(
        self,
        page: "Page",
        step_index: int,
        error_message: str
    ) -> Optional[ScreenshotInfo]:
        """Capture screenshot when an error occurs"""
        return await self.capture(
            page,
            step_index=step_index,
            step_type="error",
            description=f"Error: {error_message[:50]}",
            is_debug=True,
            full_page=True
        )
    
    def get_screenshots_for_log(
        self,
        log_dir: str,
        embed_base64: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get screenshot info formatted for log output.
        
        Args:
            log_dir: Directory where log file is saved (for relative paths)
            embed_base64: Whether to include base64 data
            
        Returns:
            List of screenshot info dicts with relative paths
        """
        result = []
        for ss in self.screenshots:
            info = ss.to_dict()
            info["relative_path"] = ss.get_relative_path(log_dir)
            info["markdown"] = ss.get_markdown_embed(log_dir)
            
            if embed_base64:
                ss.load_base64()
                info["base64"] = ss.get_base64_embed()
            
            result.append(info)
        
        return result
    
    def get_all_paths(self) -> List[str]:
        """Get list of all screenshot file paths"""
        return [ss.path for ss in self.screenshots]
    
    def cleanup(self):
        """Remove all screenshots from this session"""
        import shutil
        if self.session_dir.exists():
            shutil.rmtree(self.session_dir)
            logger.info(f"Cleaned up screenshots: {self.session_dir}")


def cleanup_old_screenshots(
    base_dir: str = "screenshots",
    max_age_days: int = 7
) -> int:
    """
    Remove screenshots older than max_age_days.
    
    Args:
        base_dir: Base screenshots directory
        max_age_days: Maximum age in days before deletion
        
    Returns:
        Number of directories removed
    """
    import shutil
    
    base = Path(base_dir)
    if not base.exists():
        return 0
    
    cutoff = datetime.now() - timedelta(days=max_age_days)
    removed = 0
    
    for domain_dir in base.iterdir():
        if not domain_dir.is_dir():
            continue
        
        for run_dir in domain_dir.iterdir():
            if not run_dir.is_dir():
                continue
            
            # Check modification time
            mtime = datetime.fromtimestamp(run_dir.stat().st_mtime)
            if mtime < cutoff:
                try:
                    shutil.rmtree(run_dir)
                    removed += 1
                    logger.info(f"Removed old screenshots: {run_dir}")
                except Exception as e:
                    logger.warning(f"Failed to remove {run_dir}: {e}")
    
    return removed


async def capture_page_screenshot(
    page: "Page",
    output_path: str,
    full_page: bool = False
) -> str:
    """
    Simple helper to capture a screenshot.
    
    Args:
        page: Playwright page
        output_path: Where to save the screenshot
        full_page: Whether to capture full page
        
    Returns:
        Path to saved screenshot
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=output_path, full_page=full_page)
    return output_path
