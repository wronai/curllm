"""Server management functions - start, stop, restart, status"""

import logging
import os
import signal
import socket
import time

from curllm_web.config import LOGS_DIR, PROMPTS_FILE
from curllm_web.prompts.default_prompts import DEFAULT_PROMPTS
from curllm_web.prompts.prompt_manager import save_prompts
from curllm_web.server.pid_manager import get_pid_file, is_running, save_pid

logger = logging.getLogger(__name__)


def start_server() -> int:
    """Start the web server"""
    # Import here to avoid circular imports
    from curllm_web.app import app
    
    # Check if already running
    running_pid = is_running()
    if running_pid:
        print(f"❌ curllm-web is already running (PID: {running_pid})")
        print("   Use 'curllm-web stop' to stop it first")
        return 1
    
    port = int(os.getenv('CURLLM_WEB_PORT', '5000'))
    host = os.getenv('CURLLM_WEB_HOST', '0.0.0.0')
    debug = os.getenv('CURLLM_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting curllm web client on {host}:{port}")
    logger.info(f"Logs directory: {LOGS_DIR.absolute()}")
    
    # Initialize prompts file if it doesn't exist
    if not PROMPTS_FILE.exists():
        save_prompts(DEFAULT_PROMPTS)
        logger.info(f"Created default prompts file: {PROMPTS_FILE}")
    
    # Save PID
    save_pid()
    
    try:
        print(f"✅ curllm-web started on http://{host}:{port}")
        print(f"   PID: {os.getpid()}")
        print("   Press Ctrl+C to stop")
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping server...")
    finally:
        # Clean up PID file
        pid_file = get_pid_file()
        if pid_file.exists():
            pid_file.unlink()
    
    return 0


def stop_server() -> int:
    """Stop the web server"""
    running_pid = is_running()
    
    if not running_pid:
        print("ℹ️  curllm-web is not running")
        return 1
    
    try:
        import psutil
        
        print(f"⏹️  Stopping curllm-web (PID: {running_pid})...")
        
        proc = psutil.Process(running_pid)
        proc.send_signal(signal.SIGTERM)
        
        # Wait up to 5 seconds for graceful shutdown
        for _ in range(50):
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


def restart_server() -> int:
    """Restart the web server"""
    print("🔄 Restarting curllm-web...")
    stop_server()
    time.sleep(1)
    return start_server()


def show_status() -> int:
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
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                if result == 0:
                    print(f"   Status: ✅ Responding on port {port}")
                else:
                    print(f"   Status: ⚠️  Not responding on port {port}")
            except Exception:
                pass
                
            return 0
        except Exception as e:
            print(f"❌ Error getting status: {e}")
            return 1
    else:
        print("❌ curllm-web is not running")
        return 1
