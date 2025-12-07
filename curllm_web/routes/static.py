"""Static file routes - screenshots and uploads"""

from pathlib import Path

from flask import Blueprint, jsonify, send_from_directory

from curllm_web.config import UPLOAD_FOLDER

static_bp = Blueprint('static', __name__)


@static_bp.route('/screenshots/<path:filename>')
def serve_screenshot(filename):
    """Serve screenshot files from subdirectories"""
    screenshots_dir = Path('./screenshots')
    file_path = screenshots_dir / filename
    
    # Security check - ensure file is within screenshots directory
    try:
        file_path.resolve().relative_to(screenshots_dir.resolve())
    except ValueError:
        return jsonify({'error': 'Invalid path'}), 403
    
    if file_path.exists() and file_path.is_file():
        return send_from_directory(screenshots_dir, filename)
    return jsonify({'error': 'Screenshot not found'}), 404


@static_bp.route('/uploads/<path:filename>')
def serve_upload(filename):
    """Serve uploaded files"""
    return send_from_directory(UPLOAD_FOLDER, filename)
