"""Log utility functions"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from curllm_web.config import LOGS_DIR

logger = logging.getLogger(__name__)


def get_logs_list() -> List[Dict]:
    """Get list of all log files with metadata"""
    logs = []
    for log_file in sorted(LOGS_DIR.glob('run-*.md'), reverse=True):
        try:
            stat = log_file.stat()
            logs.append({
                'filename': log_file.name,
                'path': str(log_file),
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
        except Exception as e:
            logger.error(f"Error reading log file {log_file}: {e}")
    return logs


def read_log_content(filename: str) -> Optional[str]:
    """Read log file content"""
    log_path = LOGS_DIR / filename
    if log_path.exists() and log_path.is_file():
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading log {filename}: {e}")
    return None
