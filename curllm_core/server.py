#!/usr/bin/env python3
import asyncio
import logging
from flask import Flask, request, jsonify
import json
from pathlib import Path
from typing import List
from .proxy import REGISTRY_JSON, REGISTRY_TXT
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
    use_v1 = data.get('use_v1', False)  # Legacy v1 API (deprecated)
    use_v2 = not use_v1  # v2 is now default
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
                use_v2=use_v2,
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

    return _run_in_new_loop()


@app.route('/api/proxy/register', methods=['POST'])
def proxy_register():
    try:
        data = request.get_json() or {}
        proxies: List[str] = []
        if isinstance(data.get('proxies'), list):
            proxies.extend([str(x).strip() for x in data['proxies'] if str(x).strip()])
        if isinstance(data.get('proxy'), str):
            p = data.get('proxy').strip()
            if p:
                proxies.append(p)
        if not proxies:
            return jsonify({"ok": False, "error": "No proxies provided"}), 400
        # Load existing registry
        REGISTRY_JSON.parent.mkdir(parents=True, exist_ok=True)
        current: List[str] = []
        try:
            if REGISTRY_JSON.exists():
                obj = json.loads(REGISTRY_JSON.read_text(encoding='utf-8'))
                arr = obj.get('proxies') if isinstance(obj, dict) else None
                if isinstance(arr, list):
                    current = [str(x).strip() for x in arr if str(x).strip()]
        except Exception:
            current = []
        merged = list(dict.fromkeys(current + proxies))
        # Write JSON and TXT
        try:
            REGISTRY_JSON.write_text(json.dumps({"proxies": merged}, indent=2), encoding='utf-8')
        except Exception:
            pass
        try:
            REGISTRY_TXT.write_text("\n".join(merged) + "\n", encoding='utf-8')
        except Exception:
            pass
        return jsonify({"ok": True, "count": len(merged)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/proxy/list', methods=['GET'])
def proxy_list():
    try:
        out: List[str] = []
        try:
            if REGISTRY_JSON.exists():
                obj = json.loads(REGISTRY_JSON.read_text(encoding='utf-8'))
                arr = obj.get('proxies') if isinstance(obj, dict) else None
                if isinstance(arr, list):
                    out.extend([str(x).strip() for x in arr if str(x).strip()])
        except Exception:
            pass
        try:
            if REGISTRY_TXT.exists():
                out.extend([l.strip() for l in REGISTRY_TXT.read_text(encoding='utf-8').splitlines() if l.strip()])
        except Exception:
            pass
        # unique
        out = list(dict.fromkeys(out))
        return jsonify({"proxies": out, "count": len(out)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/proxy/health', methods=['POST'])
def proxy_health():
    """Check proxy health and optionally prune dead entries from registry.
    Body JSON:
      - url: test URL (default: http://example.com)
      - timeout: seconds (default: 4)
      - limit: max proxies to test (0 or missing = all)
      - prune: bool (default: false) -> if true, remove dead from registry
    """
    try:
        data = request.get_json() or {}
        test_url = data.get('url') or 'http://example.com'
        timeout = float(data.get('timeout') or 4)
        limit = int(data.get('limit') or 0)
        prune = bool(data.get('prune') or False)

        # Load registry proxies
        reg: List[str] = []
        try:
            if REGISTRY_JSON.exists():
                obj = json.loads(REGISTRY_JSON.read_text(encoding='utf-8'))
                arr = obj.get('proxies') if isinstance(obj, dict) else None
                if isinstance(arr, list):
                    reg.extend([str(x).strip() for x in arr if str(x).strip()])
        except Exception:
            pass
        try:
            if REGISTRY_TXT.exists():
                reg.extend([l.strip() for l in REGISTRY_TXT.read_text(encoding='utf-8').splitlines() if l.strip()])
        except Exception:
            pass
        # unique
        reg = list(dict.fromkeys(reg))

        to_test = reg[:limit] if (limit and limit > 0) else reg
        import requests
        alive: List[str] = []
        statuses = []
        for px in to_test:
            ok = False
            err = None
            try:
                proxies = {"http": px, "https": px}
                r = requests.get(test_url, proxies=proxies, timeout=timeout, allow_redirects=True)
                ok = (200 <= r.status_code < 400)
            except Exception as e:
                err = str(e)
            statuses.append({"proxy": px, "ok": ok, "error": err})
            if ok:
                alive.append(px)

        pruned = 0
        if prune:
            # Keep original order but filter to alive
            if alive:
                try:
                    REGISTRY_JSON.parent.mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass
                try:
                    REGISTRY_JSON.write_text(json.dumps({"proxies": alive}, indent=2), encoding='utf-8')
                except Exception:
                    pass
                try:
                    REGISTRY_TXT.write_text("\n".join(alive) + "\n", encoding='utf-8')
                except Exception:
                    pass
            pruned = len(reg) - len(alive)

        return jsonify({
            "tested": len(to_test),
            "alive": len(alive),
            "dead": len(to_test) - len(alive),
            "pruned": pruned,
            "statuses": statuses,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

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
