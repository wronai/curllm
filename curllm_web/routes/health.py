"""Health check route"""

from datetime import datetime

from flask import Blueprint, jsonify

from curllm_web.config import LOGS_DIR, UPLOAD_FOLDER

health_bp = Blueprint('health', __name__)


@health_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'logs_count': len(list(LOGS_DIR.glob('run-*.md'))),
        'uploads_count': len(list(UPLOAD_FOLDER.glob('*')))
    })
