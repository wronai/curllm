"""Upload route - file uploads"""

from datetime import datetime

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from curllm_web.config import UPLOAD_FOLDER
from curllm_web.utils.file_utils import allowed_file

upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = UPLOAD_FOLDER / filename
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'path': str(filepath),
            'size': filepath.stat().st_size
        })
    
    return jsonify({'error': 'File type not allowed'}), 400
