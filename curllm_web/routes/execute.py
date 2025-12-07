"""Execute route - run curllm tasks"""

import asyncio

from flask import Blueprint, request, jsonify

from curllm_web.api.curllm_api import call_curllm_api

execute_bp = Blueprint('execute', __name__)


@execute_bp.route('/api/execute', methods=['POST'])
def execute():
    """Execute curllm task"""
    data = request.json
    url = data.get('url', '')
    instruction = data.get('instruction', '')
    options = data.get('options', {})
    
    if not url or not instruction:
        return jsonify({'error': 'URL and instruction are required'}), 400
    
    # Run async call in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(call_curllm_api(url, instruction, options))
    loop.close()
    
    return jsonify(result)
