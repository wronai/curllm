"""PID file management for server process"""

import os
from pathlib import Path
from typing import Union


def get_pid_file() -> Path:
    """Get PID file path"""
    return Path('/tmp/curllm_web.pid')


def is_running() -> Union[int, bool]:
    """Check if server is already running. Returns PID if running, False otherwise."""
    pid_file = get_pid_file()
    if not pid_file.exists():
        return False
    
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        # Check if process with this PID exists
        import psutil
        if psutil.pid_exists(pid):
            try:
                proc = psutil.Process(pid)
                # Check if it's actually our process
                if 'curllm-web' in ' '.join(proc.cmdline()) or 'curllm_web' in ' '.join(proc.cmdline()):
                    return pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # PID file exists but process doesn't - clean up
        pid_file.unlink()
        return False
    except Exception:
        return False


def save_pid():
    """Save current process PID"""
    pid_file = get_pid_file()
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))
