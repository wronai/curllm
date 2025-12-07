"""Logs routes - log file management"""

from flask import Blueprint, jsonify

from curllm_web.utils.log_utils import get_logs_list, read_log_content

logs_bp = Blueprint('logs', __name__)


@logs_bp.route('/api/logs', methods=['GET'])
def get_logs():
    """Get list of log files"""
    logs = get_logs_list()
    return jsonify({'logs': logs})


@logs_bp.route('/api/logs/<filename>', methods=['GET'])
def get_log(filename):
    """Get specific log file content"""
    content = read_log_content(filename)
    if content:
        return jsonify({'success': True, 'content': content, 'filename': filename})
    return jsonify({'error': 'Log file not found'}), 404
