"""Main entry point for curllm_web"""

import sys

from curllm_web.server.server_manager import start_server, stop_server, restart_server, show_status


def main() -> int:
    """Main entry point"""
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
    sys.exit(main())
