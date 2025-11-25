"""Tests for CLI commands (curllm-setup and curllm-doctor)."""

import sys
import subprocess
from pathlib import Path


def test_cli_setup_importable():
    """Test that setup module can be imported."""
    try:
        from curllm_core.cli import setup
        assert hasattr(setup, 'main')
        print("✓ curllm_core.cli.setup module imports successfully")
    except ImportError as e:
        print(f"✗ Failed to import setup module: {e}")
        sys.exit(1)


def test_cli_doctor_importable():
    """Test that doctor module can be imported."""
    try:
        from curllm_core.cli import doctor
        assert hasattr(doctor, 'main')
        print("✓ curllm_core.cli.doctor module imports successfully")
    except ImportError as e:
        print(f"✗ Failed to import doctor module: {e}")
        sys.exit(1)


def test_setup_help():
    """Test that setup script can be executed."""
    try:
        from curllm_core.cli.setup import main
        # Test functions exist
        from curllm_core.cli.setup import (
            check_python_version,
            setup_directories,
            create_env_file,
            check_ollama,
        )
        print("✓ Setup module functions are accessible")
    except ImportError as e:
        print(f"✗ Failed to access setup functions: {e}")
        sys.exit(1)


def test_doctor_help():
    """Test that doctor script can be executed."""
    try:
        from curllm_core.cli.doctor import main
        # Test functions exist
        from curllm_core.cli.doctor import (
            check_python_version,
            check_package_installation,
            check_dependencies,
            check_ollama,
        )
        print("✓ Doctor module functions are accessible")
    except ImportError as e:
        print(f"✗ Failed to access doctor functions: {e}")
        sys.exit(1)


def test_cli_module_structure():
    """Test CLI module structure."""
    cli_dir = Path(__file__).parent.parent / "curllm_core" / "cli"
    
    assert cli_dir.exists(), "CLI directory should exist"
    assert (cli_dir / "__init__.py").exists(), "__init__.py should exist"
    assert (cli_dir / "setup.py").exists(), "setup.py should exist"
    assert (cli_dir / "doctor.py").exists(), "doctor.py should exist"
    
    print("✓ CLI module structure is correct")


def main():
    """Run all tests."""
    print("Testing CLI commands...\n")
    
    test_cli_module_structure()
    test_cli_setup_importable()
    test_cli_doctor_importable()
    test_setup_help()
    test_doctor_help()
    
    print("\n✓ All CLI command tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
