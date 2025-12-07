"""Configuration for curllm web client"""

from pathlib import Path

# Upload configuration
UPLOAD_FOLDER = Path('./uploads')
UPLOAD_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx', 'json', 'txt', 'html'}

# Prompts configuration
PROMPTS_FILE = Path('./web_prompts.json')

# Logs configuration
LOGS_DIR = Path('./logs')
LOGS_DIR.mkdir(exist_ok=True)

# Max upload size: 16MB
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
