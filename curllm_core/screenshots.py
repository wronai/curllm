"""
Screenshot utilities.

Core capture functions are in curllm_core.streamware.components.screenshot
This file adds organization/cleanup utilities.
"""
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import shutil
import logging

from .config import config

logger = logging.getLogger(__name__)


# Lazy re-exports to avoid circular imports
def capture_page(*args, **kwargs):
    from curllm_core.streamware.components.screenshot import capture_page as _cap
    return _cap(*args, **kwargs)


def capture_element(*args, **kwargs):
    from curllm_core.streamware.components.screenshot import capture_element as _cap
    return _cap(*args, **kwargs)


def get_run_screenshot_dir(domain: str, run_id: str) -> Path:
    """
    Get screenshot directory for a specific run.
    
    Organizes screenshots as:
    screenshots/
    └── domain/
        └── run-TIMESTAMP/
            ├── step_0.png
            ├── step_1.png
            └── debug_*.png
    
    Args:
        domain: Domain name (e.g., "www.example.com")
        run_id: Run identifier (e.g., "20251125-081436")
        
    Returns:
        Path to run-specific screenshot directory
    """
    base = Path(config.screenshot_dir)
    run_dir = base / domain / f"run-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


async def take_screenshot(page, step: int, target_dir: Optional[Path] = None) -> str:
    """Take screenshot for a specific step."""
    tdir = Path(target_dir) if target_dir else config.screenshot_dir
    tdir.mkdir(parents=True, exist_ok=True)
    filename = tdir / f"step_{step}_{datetime.now().timestamp()}.png"
    await page.screenshot(path=str(filename))
    return str(filename)


async def take_screenshot_organized(
    page, 
    step: int, 
    domain: str, 
    run_id: str,
    debug_name: Optional[str] = None
) -> str:
    """
    Take screenshot with organized directory structure per run.
    
    Args:
        page: Playwright page object
        step: Step number
        domain: Domain name
        run_id: Run identifier
        debug_name: Optional debug screenshot name (e.g., "before_submit")
        
    Returns:
        Path to saved screenshot
    """
    run_dir = get_run_screenshot_dir(domain, run_id)
    
    if debug_name:
        filename = run_dir / f"debug_{debug_name}_{datetime.now().timestamp()}.png"
    else:
        filename = run_dir / f"step_{step}.png"
    
    await page.screenshot(path=str(filename))
    logger.debug(f"Screenshot saved: {filename}")
    return str(filename)


def cleanup_old_screenshots(max_age_days: int = 7) -> int:
    """
    Remove screenshots older than max_age_days.
    
    Args:
        max_age_days: Maximum age in days before deletion
        
    Returns:
        Number of directories removed
    """
    base = Path(config.screenshot_dir)
    if not base.exists():
        return 0
    
    cutoff = datetime.now() - timedelta(days=max_age_days)
    removed_count = 0
    
    # Find all run-* directories
    for domain_dir in base.iterdir():
        if not domain_dir.is_dir():
            continue
            
        for run_dir in domain_dir.glob("run-*"):
            if not run_dir.is_dir():
                continue
            
            # Check directory modification time
            mtime = datetime.fromtimestamp(run_dir.stat().st_mtime)
            
            if mtime < cutoff:
                try:
                    shutil.rmtree(run_dir)
                    removed_count += 1
                    logger.info(f"Removed old screenshot dir: {run_dir}")
                except Exception as e:
                    logger.warning(f"Failed to remove {run_dir}: {e}")
    
    return removed_count


def get_latest_run_screenshots(domain: str, limit: int = 5) -> list[Path]:
    """
    Get paths to the most recent run screenshot directories for a domain.
    
    Args:
        domain: Domain name
        limit: Maximum number of runs to return
        
    Returns:
        List of paths to run directories, newest first
    """
    base = Path(config.screenshot_dir)
    domain_dir = base / domain
    
    if not domain_dir.exists():
        return []
    
    # Find all run-* directories and sort by modification time
    run_dirs = []
    for run_dir in domain_dir.glob("run-*"):
        if run_dir.is_dir():
            mtime = run_dir.stat().st_mtime
            run_dirs.append((mtime, run_dir))
    
    # Sort by time (newest first) and return paths
    run_dirs.sort(reverse=True, key=lambda x: x[0])
    return [path for _, path in run_dirs[:limit]]
