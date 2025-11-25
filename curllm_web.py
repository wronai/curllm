#!/usr/bin/env python3
"""
curllm_web.py - Web Client for curllm
Modern web interface for browser automation with LLM
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import aiohttp
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = Path('./uploads')
UPLOAD_FOLDER.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx', 'json', 'txt', 'html'}
PROMPTS_FILE = Path('./web_prompts.json')
LOGS_DIR = Path('./logs')
LOGS_DIR.mkdir(exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Default prompts
DEFAULT_PROMPTS = [
    {
        "id": "extract_all",
        "name": "Wyciągnij wszystkie dane",
        "prompt": "Extract all important data from this page including links, emails, phones, and products"
    },
    {
        "id": "extract_products",
        "name": "Wyciągnij produkty",
        "prompt": "Extract all products with names, prices, and descriptions"
    },
    {
        "id": "extract_products_cheap",
        "name": "Produkty poniżej 100zł",
        "prompt": "Find all products priced under 100 PLN and extract their names, prices, and URLs"
    },
    {
        "id": "extract_articles",
        "name": "Wyciągnij artykuły",
        "prompt": "Extract all articles with titles, authors, dates, and content"
    },
    {
        "id": "extract_news",
        "name": "Najnowsze wiadomości",
        "prompt": "Extract the latest 10 news articles with headlines, summaries, and publication dates"
    },
    {
        "id": "extract_contacts",
        "name": "Wyciągnij kontakty",
        "prompt": "Extract all contact information including emails, phones, and addresses"
    },
    {
        "id": "extract_links",
        "name": "Wyciągnij linki",
        "prompt": "Extract all links from this page with their anchor text and URLs"
    },
    {
        "id": "extract_images",
        "name": "Wyciągnij obrazy",
        "prompt": "Extract all images from this page with their URLs, alt text, and dimensions if available"
    },
    {
        "id": "extract_tables",
        "name": "Wyciągnij tabele",
        "prompt": "Extract all tables from this page and convert them to structured data"
    },
    {
        "id": "extract_forms",
        "name": "Wykryj formularze",
        "prompt": "Find all forms on this page and list their fields, labels, and required status"
    },
    {
        "id": "fill_form",
        "name": "Wypełnij formularz",
        "prompt": "Fill the form on this page with provided data"
    },
    {
        "id": "fill_contact_form",
        "name": "Wypełnij formularz kontaktowy",
        "prompt": "Fill contact form with: name=Jan Kowalski, email=jan@example.com, phone=+48123456789, message=Test wiadomości"
    },
    {
        "id": "search_on_page",
        "name": "Szukaj na stronie",
        "prompt": "Search for specific keyword or phrase on this page and extract relevant context"
    },
    {
        "id": "compare_prices",
        "name": "Porównaj ceny",
        "prompt": "Find and compare prices for similar products on this page"
    },
    {
        "id": "extract_reviews",
        "name": "Wyciągnij opinie",
        "prompt": "Extract all user reviews with ratings, author names, dates, and review text"
    },
    {
        "id": "screenshot",
        "name": "Zrób screenshot",
        "prompt": "Take a screenshot of the page"
    },
    {
        "id": "navigate_and_extract",
        "name": "Nawiguj i wyciągnij",
        "prompt": "Navigate through multiple pages and extract data from each page"
    },
    {
        "id": "login_and_extract",
        "name": "Zaloguj i wyciągnij",
        "prompt": "Login to the website and extract data from authenticated pages"
    },
    {
        "id": "custom",
        "name": "Własny prompt",
        "prompt": ""
    }
]

def load_prompts() -> List[Dict]:
    """Load prompts from JSON file"""
    if PROMPTS_FILE.exists():
        try:
            with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading prompts: {e}")
    return DEFAULT_PROMPTS

def save_prompts(prompts: List[Dict]) -> bool:
    """Save prompts to JSON file"""
    try:
        with open(PROMPTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(prompts, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving prompts: {e}")
        return False

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_logs_list() -> List[Dict]:
    """Get list of all log files with metadata"""
    logs = []
    for log_file in sorted(LOGS_DIR.glob('run-*.md'), reverse=True):
        try:
            stat = log_file.stat()
            logs.append({
                'filename': log_file.name,
                'path': str(log_file),
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
        except Exception as e:
            logger.error(f"Error reading log file {log_file}: {e}")
    return logs

def read_log_content(filename: str) -> Optional[str]:
    """Read log file content"""
    log_path = LOGS_DIR / filename
    if log_path.exists() and log_path.is_file():
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading log {filename}: {e}")
    return None

async def call_curllm_api(url: str, instruction: str, options: Dict) -> Dict:
    """Call curllm API server"""
    api_host = os.getenv('CURLLM_API_HOST', 'http://localhost:8000')
    
    payload = {
        'url': url,
        'data': instruction,  # API server expects 'data' not 'instruction'
        'visual_mode': options.get('visual_mode', False),
        'stealth_mode': options.get('stealth_mode', False),
        'captcha_solver': options.get('captcha_solver', False),
        'use_bql': options.get('use_bql', False),
        'export_format': options.get('export_format', 'json')
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{api_host}/api/execute', json=payload, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    return {
                        'error': f'API error: {resp.status}', 
                        'details': error_text,
                        'help': f'Sprawdź czy serwer curllm API działa na {api_host}. Uruchom: python curllm_server.py'
                    }
    except aiohttp.ClientConnectorError as e:
        logger.error(f"Cannot connect to curllm API at {api_host}: {e}")
        return {
            'error': f'Nie można połączyć z API serwrem na {api_host}',
            'details': str(e),
            'help': 'Uruchom serwer API w osobnym terminalu: python curllm_server.py'
        }
    except asyncio.TimeoutError:
        logger.error("API request timeout")
        return {
            'error': 'Timeout - zadanie trwało zbyt długo (max 5 minut)',
            'help': 'Spróbuj prostszej instrukcji lub włącz tryb wizualny'
        }
    except Exception as e:
        logger.error(f"Error calling curllm API: {e}")
        return {
            'error': f'Błąd wywołania API: {str(e)}',
            'help': f'Sprawdź czy serwer działa: curl {api_host}/health'
        }

# ============================================================================
# Routes
# ============================================================================

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/prompts', methods=['GET'])
def get_prompts():
    """Get all prompts"""
    prompts = load_prompts()
    return jsonify({'prompts': prompts})

@app.route('/api/prompts', methods=['POST'])
def add_prompt():
    """Add new prompt"""
    data = request.json
    prompts = load_prompts()
    
    new_prompt = {
        'id': data.get('id', f"custom_{len(prompts)}"),
        'name': data.get('name', 'Nowy prompt'),
        'prompt': data.get('prompt', '')
    }
    
    prompts.append(new_prompt)
    if save_prompts(prompts):
        return jsonify({'success': True, 'prompt': new_prompt})
    return jsonify({'success': False, 'error': 'Failed to save prompt'}), 500

@app.route('/api/prompts/<prompt_id>', methods=['PUT'])
def update_prompt(prompt_id):
    """Update existing prompt"""
    data = request.json
    prompts = load_prompts()
    
    for i, prompt in enumerate(prompts):
        if prompt['id'] == prompt_id:
            prompts[i]['name'] = data.get('name', prompt['name'])
            prompts[i]['prompt'] = data.get('prompt', prompt['prompt'])
            if save_prompts(prompts):
                return jsonify({'success': True, 'prompt': prompts[i]})
            return jsonify({'success': False, 'error': 'Failed to save prompt'}), 500
    
    return jsonify({'success': False, 'error': 'Prompt not found'}), 404

@app.route('/api/prompts/<prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    """Delete prompt"""
    prompts = load_prompts()
    prompts = [p for p in prompts if p['id'] != prompt_id]
    
    if save_prompts(prompts):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Failed to save prompts'}), 500

@app.route('/api/execute', methods=['POST'])
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

@app.route('/api/upload', methods=['POST'])
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

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get list of log files"""
    logs = get_logs_list()
    return jsonify({'logs': logs})

@app.route('/api/logs/<filename>', methods=['GET'])
def get_log(filename):
    """Get specific log file content"""
    content = read_log_content(filename)
    if content:
        return jsonify({'success': True, 'content': content, 'filename': filename})
    return jsonify({'error': 'Log file not found'}), 404

@app.route('/screenshots/<path:filename>')
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

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """Serve uploaded files"""
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'logs_count': len(list(LOGS_DIR.glob('run-*.md'))),
        'uploads_count': len(list(UPLOAD_FOLDER.glob('*')))
    })

def get_pid_file():
    """Get PID file path"""
    return Path('/tmp/curllm_web.pid')

def is_running():
    """Check if server is already running"""
    pid_file = get_pid_file()
    if not pid_file.exists():
        return False
    
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        # Check if process with this PID exists
        import psutil
        if psutil.pid_exists(pid):
            try:
                proc = psutil.Process(pid)
                # Check if it's actually our process
                if 'curllm-web' in ' '.join(proc.cmdline()) or 'curllm_web' in ' '.join(proc.cmdline()):
                    return pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # PID file exists but process doesn't - clean up
        pid_file.unlink()
        return False
    except Exception:
        return False

def save_pid():
    """Save current process PID"""
    pid_file = get_pid_file()
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))

def start_server():
    """Start the web server"""
    # Check if already running
    running_pid = is_running()
    if running_pid:
        print(f"❌ curllm-web is already running (PID: {running_pid})")
        print(f"   Use 'curllm-web stop' to stop it first")
        return 1
    
    port = int(os.getenv('CURLLM_WEB_PORT', '5000'))
    host = os.getenv('CURLLM_WEB_HOST', '0.0.0.0')
    debug = os.getenv('CURLLM_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting curllm web client on {host}:{port}")
    logger.info(f"Logs directory: {LOGS_DIR.absolute()}")
    logger.info(f"Uploads directory: {UPLOAD_FOLDER.absolute()}")
    
    # Initialize prompts file if it doesn't exist
    if not PROMPTS_FILE.exists():
        save_prompts(DEFAULT_PROMPTS)
        logger.info(f"Created default prompts file: {PROMPTS_FILE}")
    
    # Save PID
    save_pid()
    
    try:
        print(f"✅ curllm-web started on http://{host}:{port}")
        print(f"   PID: {os.getpid()}")
        print(f"   Press Ctrl+C to stop")
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping server...")
    finally:
        # Clean up PID file
        pid_file = get_pid_file()
        if pid_file.exists():
            pid_file.unlink()
    
    return 0

def stop_server():
    """Stop the web server"""
    running_pid = is_running()
    
    if not running_pid:
        print("ℹ️  curllm-web is not running")
        return 1
    
    try:
        import psutil
        import signal
        import time
        
        print(f"⏹️  Stopping curllm-web (PID: {running_pid})...")
        
        proc = psutil.Process(running_pid)
        proc.send_signal(signal.SIGTERM)
        
        # Wait up to 5 seconds for graceful shutdown
        for i in range(50):
            if not psutil.pid_exists(running_pid):
                break
            time.sleep(0.1)
        
        # Force kill if still running
        if psutil.pid_exists(running_pid):
            print("   Force killing...")
            proc.kill()
            time.sleep(0.5)
        
        # Clean up PID file
        pid_file = get_pid_file()
        if pid_file.exists():
            pid_file.unlink()
        
        print("✅ curllm-web stopped")
        return 0
    except Exception as e:
        print(f"❌ Error stopping server: {e}")
        return 1

def restart_server():
    """Restart the web server"""
    print("🔄 Restarting curllm-web...")
    stop_server()
    import time
    time.sleep(1)
    return start_server()

def show_status():
    """Show server status"""
    running_pid = is_running()
    
    if running_pid:
        try:
            import psutil
            proc = psutil.Process(running_pid)
            
            # Get server info
            port = int(os.getenv('CURLLM_WEB_PORT', '5000'))
            
            print("✅ curllm-web is running")
            print(f"   PID: {running_pid}")
            print(f"   URL: http://localhost:{port}")
            print(f"   Memory: {proc.memory_info().rss / 1024 / 1024:.1f} MB")
            
            # Try to check if port is listening
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                if result == 0:
                    print(f"   Status: ✅ Responding on port {port}")
                else:
                    print(f"   Status: ⚠️  Not responding on port {port}")
            except:
                pass
                
            return 0
        except Exception as e:
            print(f"❌ Error getting status: {e}")
            return 1
    else:
        print("❌ curllm-web is not running")
        return 1

def main():
    """Main entry point"""
    import sys
    
    # Parse command
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'start':
            return start_server()
        elif command == 'stop':
            return stop_server()
        elif command == 'restart':
            return restart_server()
        elif command == 'status':
            return show_status()
        elif command in ['--help', '-h', 'help']:
            print("curllm-web - Web interface for curllm")
            print()
            print("Usage:")
            print("  curllm-web              Start server (default)")
            print("  curllm-web start        Start server")
            print("  curllm-web stop         Stop server")
            print("  curllm-web restart      Restart server")
            print("  curllm-web status       Show server status")
            print("  curllm-web --help       Show this help")
            print()
            print("Environment variables:")
            print("  CURLLM_WEB_PORT        Server port (default: 5000)")
            print("  CURLLM_WEB_HOST        Server host (default: 0.0.0.0)")
            print("  CURLLM_API_HOST        API server URL (default: http://localhost:8000)")
            print("  CURLLM_DEBUG           Enable debug mode (default: false)")
            return 0
        else:
            print(f"❌ Unknown command: {command}")
            print("   Use 'curllm-web --help' for usage")
            return 1
    
    # No command - default to start
    return start_server()

if __name__ == '__main__':
    import sys
    sys.exit(main())
