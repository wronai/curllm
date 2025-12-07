"""File utility functions"""

from curllm_web.config import ALLOWED_EXTENSIONS


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
