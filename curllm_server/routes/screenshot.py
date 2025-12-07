"""Screenshot endpoint for serving screenshot files"""

from flask import Blueprint, jsonify, send_file

from curllm_server.config import config

screenshot_bp = Blueprint('screenshot', __name__)


@screenshot_bp.route('/api/screenshot/<path:filename>', methods=['GET'])
def get_screenshot(filename):
    """Serve screenshot files"""
    filepath = config.screenshot_dir / filename
    if filepath.exists():
        return send_file(str(filepath), mimetype='image/png')
    return jsonify({"error": "Screenshot not found"}), 404
