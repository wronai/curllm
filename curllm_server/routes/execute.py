"""Execute endpoint for browser automation"""

import asyncio

from flask import Blueprint, request, jsonify

from curllm_server.executor.curllm_executor import CurllmExecutor

execute_bp = Blueprint('execute', __name__)

# Global executor instance
executor = CurllmExecutor()


@execute_bp.route('/api/execute', methods=['POST'])
def execute():
    """Main execution endpoint"""
    data = request.get_json()
    
    # Extract parameters
    instruction = data.get('data', '')
    url = data.get('url')
    visual_mode = data.get('visual_mode', False)
    stealth_mode = data.get('stealth_mode', False)
    captcha_solver = data.get('captcha_solver', False)
    use_bql = data.get('use_bql', False)
    headers = data.get('headers', {})
    
    # Run async task in a fresh event loop per request to avoid loop state issues
    def _run_in_new_loop():
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                executor.execute_workflow(
                    instruction=instruction,
                    url=url,
                    visual_mode=visual_mode,
                    stealth_mode=stealth_mode,
                    captcha_solver=captcha_solver,
                    use_bql=use_bql,
                    headers=headers
                )
            )
        finally:
            try:
                loop.run_until_complete(asyncio.sleep(0))
            except Exception:
                pass
            loop.close()
            try:
                asyncio.set_event_loop(asyncio.new_event_loop())
            except Exception:
                pass

    result = _run_in_new_loop()
    
    return jsonify(result)
