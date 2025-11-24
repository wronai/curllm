#!/usr/bin/env python3
import asyncio
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

from .config import config
from .executor import CurllmExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

executor = CurllmExecutor()

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "model": config.ollama_model,
        "ollama_host": config.ollama_host,
        "version": "1.0.0",
    })

@app.route('/api/execute', methods=['POST'])
def execute():
    data = request.get_json() or {}
    instruction = data.get('data', '')
    url = data.get('url')
    visual_mode = data.get('visual_mode', False)
    stealth_mode = data.get('stealth_mode', False)
    captcha_solver = data.get('captcha_solver', False)
    use_bql = data.get('use_bql', False)
    headers = data.get('headers', {})
    proxy = data.get('proxy')
    session_id = data.get('session_id')
    wordpress_config = data.get('wordpress_config')

    def _run_in_new_loop():
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(executor.execute_workflow(
                instruction=instruction,
                url=url,
                visual_mode=visual_mode,
                stealth_mode=stealth_mode,
                captcha_solver=captcha_solver,
                use_bql=use_bql,
                headers=headers,
                proxy=proxy,
                session_id=session_id,
                wordpress_config=wordpress_config,
            ))
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

@app.route('/api/models', methods=['GET'])
def list_models():
    try:
        import requests
        response = requests.get(f"{config.ollama_host}/api/tags")
        return jsonify(response.json())
    except Exception:
        return jsonify({"error": "Failed to fetch models"}), 500

@app.route('/api/screenshot/<path:filename>', methods=['GET'])
def get_screenshot(filename):
    from flask import send_file
    from pathlib import Path
    filepath = (config.screenshot_dir / filename)
    if filepath.exists():
        return send_file(str(filepath), mimetype='image/png')
    return jsonify({"error": "Screenshot not found"}), 404


def run_server():
    import requests
    try:
        requests.get(f"{config.ollama_host}/api/tags")
        logger.info(f"✓ Connected to Ollama at {config.ollama_host}")
    except Exception:
        logger.warning(f"✗ Cannot connect to Ollama at {config.ollama_host}")
        logger.warning("  The API server will start, but requests may fail until Ollama is running (run: 'ollama serve').")
    logger.info(f"Starting curllm API server on port {config.api_port}...")
    logger.info(f"Model: {config.ollama_model}")
    logger.info("Visual mode: Available")
    logger.info("Stealth mode: Available")
    logger.info(f"CAPTCHA solver: {'Enabled' if __import__('os').getenv('CAPTCHA_API_KEY') else 'Local OCR only'}")
    app.run(host='0.0.0.0', port=config.api_port, debug=False, use_reloader=False)
