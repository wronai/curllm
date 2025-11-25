"""
Unit tests for Screenshot Organization.

Tests per-run screenshot organization and cleanup.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import shutil

from curllm_core.screenshots import (
    get_run_screenshot_dir,
    cleanup_old_screenshots,
    get_latest_run_screenshots
)
from curllm_core.config import config


@pytest.fixture
def temp_screenshot_dir(monkeypatch):
    """Create temporary screenshot directory for testing."""
    temp_dir = tempfile.mkdtemp()
    monkeypatch.setattr(config, 'screenshot_dir', Path(temp_dir))
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_get_run_screenshot_dir(temp_screenshot_dir):
    """Test run screenshot directory creation."""
    domain = "www.example.com"
    run_id = "20251125-081436"
    
    run_dir = get_run_screenshot_dir(domain, run_id)
    
    assert run_dir.exists()
    assert run_dir.is_dir()
    assert domain in str(run_dir)
    assert f"run-{run_id}" in str(run_dir)


def test_run_screenshot_dir_hierarchy(temp_screenshot_dir):
    """Test screenshot directory hierarchy."""
    domain = "www.example.com"
    run_id = "20251125-081436"
    
    run_dir = get_run_screenshot_dir(domain, run_id)
    
    # Check hierarchy: base/domain/run-id/
    assert run_dir.parent.name == domain
    assert run_dir.parent.parent == temp_screenshot_dir


def test_multiple_runs_same_domain(temp_screenshot_dir):
    """Test multiple runs for same domain."""
    domain = "www.example.com"
    run_id_1 = "20251125-080000"
    run_id_2 = "20251125-090000"
    
    run_dir_1 = get_run_screenshot_dir(domain, run_id_1)
    run_dir_2 = get_run_screenshot_dir(domain, run_id_2)
    
    assert run_dir_1.exists()
    assert run_dir_2.exists()
    assert run_dir_1 != run_dir_2
    assert run_dir_1.parent == run_dir_2.parent  # Same domain dir


def test_cleanup_old_screenshots_empty(temp_screenshot_dir):
    """Test cleanup with no screenshots."""
    removed = cleanup_old_screenshots(max_age_days=7)
    
    assert removed == 0


def test_cleanup_old_screenshots_recent(temp_screenshot_dir):
    """Test cleanup doesn't remove recent screenshots."""
    domain = "www.example.com"
    run_id = "20251125-081436"
    
    # Create recent run directory
    run_dir = get_run_screenshot_dir(domain, run_id)
    (run_dir / "step_0.png").touch()
    
    removed = cleanup_old_screenshots(max_age_days=7)
    
    assert removed == 0
    assert run_dir.exists()


def test_cleanup_old_screenshots_old(temp_screenshot_dir):
    """Test cleanup removes old screenshots."""
    domain = "www.example.com"
    run_id = "20251118-081436"  # 7 days ago
    
    # Create old run directory
    run_dir = get_run_screenshot_dir(domain, run_id)
    (run_dir / "step_0.png").touch()
    
    # Set modification time to 8 days ago
    old_time = (datetime.now() - timedelta(days=8)).timestamp()
    run_dir.touch()
    import os
    os.utime(run_dir, (old_time, old_time))
    
    removed = cleanup_old_screenshots(max_age_days=7)
    
    assert removed == 1
    assert not run_dir.exists()


def test_get_latest_run_screenshots_empty(temp_screenshot_dir):
    """Test getting latest runs with no screenshots."""
    domain = "www.example.com"
    
    latest = get_latest_run_screenshots(domain, limit=5)
    
    assert latest == []


def test_get_latest_run_screenshots_single(temp_screenshot_dir):
    """Test getting latest run with single run."""
    domain = "www.example.com"
    run_id = "20251125-081436"
    
    run_dir = get_run_screenshot_dir(domain, run_id)
    (run_dir / "step_0.png").touch()
    
    latest = get_latest_run_screenshots(domain, limit=5)
    
    assert len(latest) == 1
    assert latest[0] == run_dir


def test_get_latest_run_screenshots_multiple(temp_screenshot_dir):
    """Test getting latest runs with multiple runs."""
    domain = "www.example.com"
    
    # Create multiple run directories
    run_ids = [
        "20251125-080000",
        "20251125-090000",
        "20251125-100000",
    ]
    
    run_dirs = []
    for run_id in run_ids:
        run_dir = get_run_screenshot_dir(domain, run_id)
        (run_dir / "step_0.png").touch()
        run_dirs.append(run_dir)
    
    latest = get_latest_run_screenshots(domain, limit=5)
    
    assert len(latest) == 3
    # Should be sorted by modification time (newest first)
    assert all(d in latest for d in run_dirs)


def test_get_latest_run_screenshots_limit(temp_screenshot_dir):
    """Test limit parameter works correctly."""
    domain = "www.example.com"
    
    # Create 5 run directories
    for i in range(5):
        run_id = f"20251125-08{i:02d}00"
        run_dir = get_run_screenshot_dir(domain, run_id)
        (run_dir / "step_0.png").touch()
    
    latest = get_latest_run_screenshots(domain, limit=3)
    
    assert len(latest) == 3


def test_different_domains_isolated(temp_screenshot_dir):
    """Test that different domains are isolated."""
    domain1 = "www.example.com"
    domain2 = "www.test.com"
    run_id = "20251125-081436"
    
    run_dir_1 = get_run_screenshot_dir(domain1, run_id)
    run_dir_2 = get_run_screenshot_dir(domain2, run_id)
    
    (run_dir_1 / "step_0.png").touch()
    (run_dir_2 / "step_0.png").touch()
    
    latest_1 = get_latest_run_screenshots(domain1, limit=5)
    latest_2 = get_latest_run_screenshots(domain2, limit=5)
    
    assert len(latest_1) == 1
    assert len(latest_2) == 1
    assert latest_1[0] != latest_2[0]


def test_run_directory_naming(temp_screenshot_dir):
    """Test run directory naming convention."""
    domain = "www.example.com"
    run_id = "20251125-081436"
    
    run_dir = get_run_screenshot_dir(domain, run_id)
    
    # Should contain run- prefix
    assert run_dir.name.startswith("run-")
    assert run_id in run_dir.name
