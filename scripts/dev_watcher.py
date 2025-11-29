#!/usr/bin/env python3
"""
Development File Watcher - Auto-reload/reinstall on code changes

Monitors project files and automatically:
- Reinstalls package when pyproject.toml/requirements.txt changes
- Restarts services when source code changes
- Re-runs tests when test files change (optional)

Usage:
    python scripts/dev_watcher.py [--restart-cmd CMD] [--test-on-change]
    
Examples:
    python scripts/dev_watcher.py
    python scripts/dev_watcher.py --restart-cmd "make restart"
    python scripts/dev_watcher.py --test-on-change
"""

import os
import sys
import time
import subprocess
import argparse
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Set, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class ChangeType(Enum):
    """Type of file change detected"""
    DEPENDENCY = auto()      # pyproject.toml, requirements.txt
    SOURCE_CODE = auto()     # curllm_core/**/*.py
    TEST = auto()            # tests/**/*.py
    CONFIG = auto()          # .env, *.yml, *.yaml
    STATIC = auto()          # templates, static files
    IGNORED = auto()         # __pycache__, .git, etc.


@dataclass
class WatchConfig:
    """Configuration for the file watcher"""
    project_root: Path
    watch_dirs: list = field(default_factory=lambda: ["curllm_core", "tests", "scripts"])
    dependency_files: list = field(default_factory=lambda: ["pyproject.toml", "requirements.txt", "setup.py"])
    config_files: list = field(default_factory=lambda: [".env", "docker-compose.yml", "docker-compose.test.yml"])
    ignore_patterns: list = field(default_factory=lambda: [
        "__pycache__", ".git", ".pytest_cache", "*.pyc", "*.pyo",
        ".eggs", "*.egg-info", "venv", ".venv", "node_modules",
        "screenshots", "logs", "test_results", "downloads", "uploads"
    ])
    debounce_seconds: float = 1.0
    restart_cmd: Optional[str] = None
    test_on_change: bool = False
    verbose: bool = True


class FileHashCache:
    """Cache file hashes to detect actual content changes"""
    
    def __init__(self):
        self._hashes: Dict[str, str] = {}
    
    def get_hash(self, filepath: Path) -> str:
        """Calculate MD5 hash of file content"""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def has_changed(self, filepath: Path) -> bool:
        """Check if file content has actually changed"""
        path_str = str(filepath)
        new_hash = self.get_hash(filepath)
        old_hash = self._hashes.get(path_str)
        
        if old_hash is None:
            # First time seeing this file
            self._hashes[path_str] = new_hash
            return True
        
        if new_hash != old_hash:
            self._hashes[path_str] = new_hash
            return True
        
        return False
    
    def remove(self, filepath: Path):
        """Remove file from cache"""
        path_str = str(filepath)
        self._hashes.pop(path_str, None)


class DevWatcher:
    """Development file watcher with auto-reload capabilities"""
    
    def __init__(self, config: WatchConfig):
        self.config = config
        self.hash_cache = FileHashCache()
        self._last_action_time: Dict[ChangeType, float] = {}
        self._pending_changes: Set[Path] = set()
        
    def log(self, msg: str, level: str = "INFO"):
        """Log message with timestamp"""
        if self.config.verbose or level in ("ERROR", "WARN"):
            timestamp = datetime.now().strftime("%H:%M:%S")
            color = {
                "INFO": "\033[94m",    # Blue
                "WARN": "\033[93m",    # Yellow
                "ERROR": "\033[91m",   # Red
                "SUCCESS": "\033[92m", # Green
                "ACTION": "\033[95m",  # Magenta
            }.get(level, "")
            reset = "\033[0m"
            print(f"{color}[{timestamp}] [{level}]{reset} {msg}")
    
    def classify_change(self, filepath: Path) -> ChangeType:
        """Classify what type of change this is"""
        path_str = str(filepath)
        filename = filepath.name
        
        # Check ignore patterns
        for pattern in self.config.ignore_patterns:
            if pattern.startswith("*"):
                if filename.endswith(pattern[1:]):
                    return ChangeType.IGNORED
            elif pattern in path_str:
                return ChangeType.IGNORED
        
        # Check dependency files
        if filename in self.config.dependency_files:
            return ChangeType.DEPENDENCY
        
        # Check config files
        if filename in self.config.config_files:
            return ChangeType.CONFIG
        
        # Check test files
        if "tests" in path_str and filename.endswith(".py"):
            return ChangeType.TEST
        
        # Check source code
        if filename.endswith(".py"):
            return ChangeType.SOURCE_CODE
        
        # Static files
        if any(d in path_str for d in ["templates", "static"]):
            return ChangeType.STATIC
        
        return ChangeType.IGNORED
    
    def should_debounce(self, change_type: ChangeType) -> bool:
        """Check if we should debounce this action"""
        now = time.time()
        last_time = self._last_action_time.get(change_type, 0)
        
        if now - last_time < self.config.debounce_seconds:
            return True
        
        self._last_action_time[change_type] = now
        return False
    
    def run_command(self, cmd: str, description: str) -> bool:
        """Run a shell command"""
        self.log(f"🔄 {description}: {cmd}", "ACTION")
        try:
            result = subprocess.run(
                cmd, 
                shell=True, 
                cwd=self.config.project_root,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.log(f"✅ {description} completed successfully", "SUCCESS")
                return True
            else:
                self.log(f"❌ {description} failed: {result.stderr[:200]}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ {description} error: {e}", "ERROR")
            return False
    
    def handle_dependency_change(self, filepath: Path):
        """Handle dependency file changes - reinstall package"""
        if self.should_debounce(ChangeType.DEPENDENCY):
            return
        
        self.log(f"📦 Dependency change detected: {filepath.name}", "WARN")
        
        # Reinstall package in development mode
        self.run_command("pip install -e . --quiet", "Package reinstall")
        
        # Clear Python cache
        self.clear_pycache()
    
    def handle_source_change(self, filepath: Path):
        """Handle source code changes"""
        if self.should_debounce(ChangeType.SOURCE_CODE):
            return
        
        self.log(f"📝 Source change: {filepath.relative_to(self.config.project_root)}")
        
        # Clear Python cache for this module
        self.clear_pycache_for_file(filepath)
        
        # Run restart command if configured
        if self.config.restart_cmd:
            self.run_command(self.config.restart_cmd, "Service restart")
        
        # Run tests if configured
        if self.config.test_on_change:
            self.run_quick_tests(filepath)
    
    def handle_test_change(self, filepath: Path):
        """Handle test file changes"""
        if self.should_debounce(ChangeType.TEST):
            return
        
        self.log(f"🧪 Test change: {filepath.relative_to(self.config.project_root)}")
        
        if self.config.test_on_change:
            # Run the specific test file that changed
            self.run_command(
                f"python -m pytest {filepath} -v --tb=short -x",
                f"Running {filepath.name}"
            )
    
    def handle_config_change(self, filepath: Path):
        """Handle config file changes"""
        if self.should_debounce(ChangeType.CONFIG):
            return
        
        self.log(f"⚙️ Config change: {filepath.name}", "WARN")
        
        if self.config.restart_cmd:
            self.run_command(self.config.restart_cmd, "Service restart (config change)")
    
    def clear_pycache(self):
        """Clear all __pycache__ directories"""
        self.log("🧹 Clearing Python cache...")
        for pycache in self.config.project_root.rglob("__pycache__"):
            try:
                import shutil
                shutil.rmtree(pycache)
            except Exception:
                pass
    
    def clear_pycache_for_file(self, filepath: Path):
        """Clear cached .pyc for a specific file"""
        if filepath.suffix == ".py":
            pycache_dir = filepath.parent / "__pycache__"
            if pycache_dir.exists():
                # Remove all .pyc files for this module
                module_name = filepath.stem
                for pyc in pycache_dir.glob(f"{module_name}*.pyc"):
                    try:
                        pyc.unlink()
                    except Exception:
                        pass
    
    def run_quick_tests(self, changed_file: Path):
        """Run quick tests related to the changed file"""
        # Try to find related test file
        if "curllm_core" in str(changed_file):
            # Map source file to potential test file
            rel_path = changed_file.relative_to(self.config.project_root / "curllm_core")
            test_file = self.config.project_root / "tests" / f"test_{rel_path}"
            
            if test_file.exists():
                self.run_command(
                    f"python -m pytest {test_file} -v --tb=short -x",
                    f"Running related tests"
                )
            else:
                # Run quick smoke tests
                self.run_command(
                    "python -m pytest tests/test_streamware.py -v --tb=short -x -q",
                    "Quick smoke tests"
                )
    
    def get_all_watched_files(self) -> Set[Path]:
        """Get all files being watched"""
        files = set()
        
        # Add dependency files
        for dep_file in self.config.dependency_files:
            path = self.config.project_root / dep_file
            if path.exists():
                files.add(path)
        
        # Add config files
        for conf_file in self.config.config_files:
            path = self.config.project_root / conf_file
            if path.exists():
                files.add(path)
        
        # Add files from watch directories
        for watch_dir in self.config.watch_dirs:
            dir_path = self.config.project_root / watch_dir
            if dir_path.exists():
                for py_file in dir_path.rglob("*.py"):
                    if self.classify_change(py_file) != ChangeType.IGNORED:
                        files.add(py_file)
        
        return files
    
    def check_for_changes(self) -> Dict[Path, ChangeType]:
        """Check all watched files for changes"""
        changes = {}
        
        for filepath in self.get_all_watched_files():
            if filepath.exists() and self.hash_cache.has_changed(filepath):
                change_type = self.classify_change(filepath)
                if change_type != ChangeType.IGNORED:
                    changes[filepath] = change_type
        
        return changes
    
    def process_changes(self, changes: Dict[Path, ChangeType]):
        """Process detected changes"""
        # Group changes by type
        by_type: Dict[ChangeType, list] = {}
        for path, change_type in changes.items():
            by_type.setdefault(change_type, []).append(path)
        
        # Process in priority order
        if ChangeType.DEPENDENCY in by_type:
            for path in by_type[ChangeType.DEPENDENCY]:
                self.handle_dependency_change(path)
        
        if ChangeType.CONFIG in by_type:
            for path in by_type[ChangeType.CONFIG]:
                self.handle_config_change(path)
        
        if ChangeType.SOURCE_CODE in by_type:
            # Only handle one source change to avoid spam
            self.handle_source_change(by_type[ChangeType.SOURCE_CODE][0])
        
        if ChangeType.TEST in by_type:
            for path in by_type[ChangeType.TEST]:
                self.handle_test_change(path)
    
    def watch(self):
        """Main watch loop"""
        self.log("👀 Starting development file watcher...", "SUCCESS")
        self.log(f"📂 Watching: {', '.join(self.config.watch_dirs)}")
        self.log(f"📦 Dependency files: {', '.join(self.config.dependency_files)}")
        
        if self.config.restart_cmd:
            self.log(f"🔄 Restart command: {self.config.restart_cmd}")
        if self.config.test_on_change:
            self.log("🧪 Tests will run on source changes")
        
        self.log("Press Ctrl+C to stop\n")
        
        # Initial hash of all files
        for filepath in self.get_all_watched_files():
            self.hash_cache.get_hash(filepath)
            self.hash_cache._hashes[str(filepath)] = self.hash_cache.get_hash(filepath)
        
        try:
            while True:
                changes = self.check_for_changes()
                if changes:
                    self.process_changes(changes)
                time.sleep(0.5)  # Check every 500ms
        except KeyboardInterrupt:
            self.log("\n👋 Watcher stopped", "SUCCESS")


def main():
    parser = argparse.ArgumentParser(
        description="Development file watcher with auto-reload",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Basic watching
  %(prog)s --restart-cmd "make restart"  # Restart service on changes
  %(prog)s --test-on-change         # Run tests on source changes
  %(prog)s --watch-dir src --watch-dir lib  # Custom watch directories
        """
    )
    
    parser.add_argument(
        "--restart-cmd", "-r",
        help="Command to restart services (e.g., 'make restart')"
    )
    parser.add_argument(
        "--test-on-change", "-t",
        action="store_true",
        help="Run tests when source files change"
    )
    parser.add_argument(
        "--watch-dir", "-w",
        action="append",
        dest="watch_dirs",
        help="Additional directories to watch"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress verbose output"
    )
    parser.add_argument(
        "--debounce",
        type=float,
        default=1.0,
        help="Debounce time in seconds (default: 1.0)"
    )
    
    args = parser.parse_args()
    
    # Build config
    config = WatchConfig(
        project_root=PROJECT_ROOT,
        restart_cmd=args.restart_cmd,
        test_on_change=args.test_on_change,
        verbose=not args.quiet,
        debounce_seconds=args.debounce
    )
    
    if args.watch_dirs:
        config.watch_dirs.extend(args.watch_dirs)
    
    # Start watcher
    watcher = DevWatcher(config)
    watcher.watch()


if __name__ == "__main__":
    main()


