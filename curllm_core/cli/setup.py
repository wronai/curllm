#!/usr/bin/env python3
"""Post-installation setup script for curllm."""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def print_step(step_num, total, text):
    """Print a formatted step."""
    print(f"[{step_num}/{total}] {text}")


def print_success(text):
    """Print success message."""
    print(f"✓ {text}")


def print_error(text):
    """Print error message."""
    print(f"✗ {text}", file=sys.stderr)


def print_warning(text):
    """Print warning message."""
    print(f"⚠ {text}")


def check_python_version():
    """Check if Python version meets requirements."""
    version = sys.version_info
    if version < (3, 10):
        print_error(f"Python 3.10+ is required. You have {version.major}.{version.minor}")
        return False
    print_success(f"Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_command(cmd):
    """Check if a command is available."""
    return shutil.which(cmd) is not None


def install_playwright_browsers():
    """Install Playwright browsers."""
    print("Installing Playwright browsers (this may take a few minutes)...")
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True
        )
        print_success("Playwright Chromium browser installed")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install Playwright browsers: {e}")
        return False


def setup_directories():
    """Create necessary directories."""
    dirs = ["logs", "screenshots", "downloads", "workspace"]
    cwd = Path.cwd()
    
    for dir_name in dirs:
        dir_path = cwd / dir_name
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print_success(f"Created directory: {dir_name}/")
        else:
            print(f"  Directory already exists: {dir_name}/")
    
    return True


def create_env_file():
    """Create .env file from example if it doesn't exist."""
    cwd = Path.cwd()
    env_file = cwd / ".env"
    env_example = cwd / ".env.example"
    
    # Check if .env.example exists in package data
    package_root = Path(__file__).parent.parent.parent
    package_env_example = package_root / ".env.example"
    
    if env_file.exists():
        print("  .env file already exists")
        return True
    
    if env_example.exists():
        shutil.copy(env_example, env_file)
        print_success("Created .env from .env.example")
        return True
    elif package_env_example.exists():
        shutil.copy(package_env_example, env_file)
        print_success("Created .env from package template")
        return True
    else:
        # Create a minimal .env file
        default_env = """# Curllm Configuration
CURLLM_API_HOST=http://localhost:8000
CURLLM_OLLAMA_HOST=http://localhost:11434
CURLLM_MODEL=qwen2.5:7b
CURLLM_BROWSERLESS=false
CURLLM_DEBUG=false
"""
        env_file.write_text(default_env)
        print_success("Created default .env file")
        return True


def check_ollama():
    """Check if Ollama is installed."""
    if check_command("ollama"):
        print_success("Ollama is installed")
        return True
    else:
        print_warning("Ollama is not installed (required for LLM features)")
        print("  Install from: https://ollama.ai")
        return False


def main():
    """Run the setup process."""
    print_header("Curllm Post-Installation Setup")
    
    total_steps = 5
    success = True
    
    # Step 1: Check Python version
    print_step(1, total_steps, "Checking Python version")
    if not check_python_version():
        sys.exit(1)
    
    # Step 2: Create directories
    print_step(2, total_steps, "Creating necessary directories")
    setup_directories()
    
    # Step 3: Create .env file
    print_step(3, total_steps, "Setting up configuration")
    create_env_file()
    
    # Step 4: Install Playwright browsers
    print_step(4, total_steps, "Installing Playwright browsers")
    if not install_playwright_browsers():
        success = False
    
    # Step 5: Check for Ollama
    print_step(5, total_steps, "Checking for Ollama")
    check_ollama()
    
    # Final message
    print_header("Setup Complete!")
    
    if success:
        print("✓ All setup steps completed successfully!")
        print("\nNext steps:")
        print("  1. Review and configure .env file if needed")
        print("  2. Install Ollama if not already installed: https://ollama.ai")
        print("  3. Pull the LLM model: ollama pull qwen2.5:7b")
        print("  4. Verify your installation: curllm-doctor")
        print("\nStart the server with:")
        print("  python -m curllm_core.server")
        return 0
    else:
        print_warning("Setup completed with some warnings")
        print("\nRun 'curllm-doctor' to check your installation")
        return 1


if __name__ == "__main__":
    sys.exit(main())
