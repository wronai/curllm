#!/usr/bin/env python3
"""Installation verification script for curllm."""

import os
import sys
import subprocess
import shutil
import socket
from pathlib import Path
import importlib.metadata


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def print_check(text):
    """Print a check being performed."""
    print(f"Checking {text}...", end=" ")


def print_ok():
    """Print OK status."""
    print("✓ OK")


def print_fail(reason=""):
    """Print FAIL status."""
    if reason:
        print(f"✗ FAIL ({reason})")
    else:
        print("✗ FAIL")


def print_warn(reason=""):
    """Print WARNING status."""
    if reason:
        print(f"⚠ WARNING ({reason})")
    else:
        print("⚠ WARNING")


def check_python_version():
    """Check Python version."""
    print_check("Python version")
    version = sys.version_info
    if version >= (3, 10):
        print_ok()
        print(f"  Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_fail(f"Python 3.10+ required, found {version.major}.{version.minor}")
        return False


def check_package_installation():
    """Check if curllm package is installed."""
    print_check("curllm package")
    try:
        version = importlib.metadata.version("curllm")
        print_ok()
        print(f"  Version: {version}")
        return True
    except importlib.metadata.PackageNotFoundError:
        print_fail("not installed")
        return False


def check_dependencies():
    """Check if all dependencies are installed."""
    print_check("Python dependencies")
    required = [
        "flask", "flask_cors", "aiohttp", "playwright",
        "langchain_ollama", "PIL", "cv2", "pytesseract",
        "numpy", "websockets", "requests", "dotenv"
    ]
    
    missing = []
    for module in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if not missing:
        print_ok()
        return True
    else:
        print_fail(f"missing: {', '.join(missing)}")
        return False


def check_playwright_browsers():
    """Check if Playwright browsers are installed."""
    print_check("Playwright browsers")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Check if chromium is already installed
        list_result = subprocess.run(
            [sys.executable, "-m", "playwright", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if list_result.returncode == 0:
            print_ok()
            print(f"  Playwright {list_result.stdout.strip()}")
            return True
        else:
            print_warn("may need installation")
            print("  Run: playwright install chromium")
            return True  # Not critical
    except subprocess.TimeoutExpired:
        print_warn("check timed out")
        return True
    except Exception as e:
        print_fail(str(e))
        return False


def check_directories():
    """Check if necessary directories exist."""
    print_check("required directories")
    cwd = Path.cwd()
    dirs = ["logs", "screenshots", "downloads", "workspace"]
    
    missing = [d for d in dirs if not (cwd / d).exists()]
    
    if not missing:
        print_ok()
        return True
    else:
        print_warn(f"missing: {', '.join(missing)}")
        print("  Run: curllm-setup")
        return True  # Not critical


def check_env_file():
    """Check if .env file exists."""
    print_check(".env configuration")
    env_file = Path.cwd() / ".env"
    
    if env_file.exists():
        print_ok()
        return True
    else:
        print_warn("not found")
        print("  Run: curllm-setup")
        return True  # Not critical


def check_ollama():
    """Check if Ollama is installed and running."""
    print_check("Ollama installation")
    
    if not shutil.which("ollama"):
        print_fail("not installed")
        print("  Install from: https://ollama.ai")
        return False
    
    print_ok()
    
    # Check if Ollama is running
    print_check("Ollama service")
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print_ok()
            models = [line.split()[0] for line in result.stdout.strip().split('\n')[1:] if line.strip()]
            if models:
                print(f"  Available models: {', '.join(models[:3])}")
                if len(models) > 3:
                    print(f"  ... and {len(models) - 3} more")
            return True
        else:
            print_fail("not running")
            print("  Start with: ollama serve")
            return False
    except subprocess.TimeoutExpired:
        print_fail("timeout")
        return False
    except Exception as e:
        print_fail(str(e))
        return False


def check_port_available(port, service_name):
    """Check if a port is available or in use."""
    print_check(f"{service_name} port ({port})")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    
    if result == 0:
        print_ok()
        print(f"  Service appears to be running on port {port}")
        return True
    else:
        print_warn(f"port {port} not in use")
        return True  # Not critical for verification


def check_tesseract():
    """Check if Tesseract OCR is installed."""
    print_check("Tesseract OCR")
    
    if shutil.which("tesseract"):
        print_ok()
        try:
            result = subprocess.run(
                ["tesseract", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            version_line = result.stdout.split('\n')[0] if result.stdout else ""
            if version_line:
                print(f"  {version_line}")
        except:
            pass
        return True
    else:
        print_warn("not installed (needed for CAPTCHA)")
        print("  Install: apt-get install tesseract-ocr (Ubuntu/Debian)")
        print("           or check https://github.com/tesseract-ocr/tesseract")
        return True  # Not critical


def check_curllm_modules():
    """Check if curllm_core modules are importable."""
    print_check("curllm_core modules")
    
    try:
        from curllm_core import config, logger, llm, executor, server
        print_ok()
        return True
    except ImportError as e:
        print_fail(str(e))
        return False


def main():
    """Run all verification checks."""
    print_header("Curllm Installation Verification")
    
    checks = [
        ("Python Version", check_python_version, True),
        ("Package", check_package_installation, True),
        ("Dependencies", check_dependencies, True),
        ("Playwright", check_playwright_browsers, False),
        ("Directories", check_directories, False),
        ("Configuration", check_env_file, False),
        ("Ollama", check_ollama, False),
        ("Ports", lambda: check_port_available(8000, "Curllm API"), False),
        ("Tesseract", check_tesseract, False),
        ("Modules", check_curllm_modules, True),
    ]
    
    print("Running diagnostics...\n")
    
    passed = 0
    failed = 0
    warnings = 0
    critical_failed = False
    
    for name, check_func, critical in checks:
        try:
            result = check_func()
            if result:
                passed += 1
            else:
                if critical:
                    failed += 1
                    critical_failed = True
                else:
                    warnings += 1
        except Exception as e:
            print_fail(f"error: {e}")
            if critical:
                failed += 1
                critical_failed = True
            else:
                warnings += 1
    
    # Summary
    print_header("Summary")
    
    total = len(checks)
    print(f"Total checks: {total}")
    print(f"  ✓ Passed:   {passed}")
    if warnings > 0:
        print(f"  ⚠ Warnings: {warnings}")
    if failed > 0:
        print(f"  ✗ Failed:   {failed}")
    
    print()
    
    if critical_failed:
        print("✗ Critical issues found! Please fix the failed checks above.")
        print("\nRecommended actions:")
        print("  1. Make sure Python 3.10+ is installed")
        print("  2. Reinstall curllm: pip install -U curllm")
        print("  3. Run setup: curllm-setup")
        return 1
    elif warnings > 0:
        print("⚠ Installation is functional but some optional features may be limited.")
        print("\nRecommended actions:")
        print("  1. Run: curllm-setup")
        print("  2. Install Ollama if needed: https://ollama.ai")
        print("  3. Install Tesseract OCR if needed")
        return 0
    else:
        print("✓ All checks passed! Your installation is ready to use.")
        print("\nStart the server with:")
        print("  python -m curllm_core.server")
        return 0


if __name__ == "__main__":
    sys.exit(main())
