#!/usr/bin/env python3
"""
URL Resolver - Uruchom wszystkie przykłady

Uruchamia po kolei wszystkie przykłady użycia URL Resolver.
"""

import asyncio
import subprocess
import sys
import os

EXAMPLES = [
    ("🔍 Szukanie produktów", "example_find_products.py"),
    ("📧 Formularze kontaktowe", "example_find_contact.py"),
    ("📋 Informacje (FAQ, zwroty)", "example_find_info.py"),
    ("🛒 Flow zakupowy", "example_shopping_flow.py"),
    ("🎯 Auto-detect intencji", "example_auto_detect.py"),
]


def run_example(name: str, script: str):
    """Run single example script"""
    print(f"\n{'#'*70}")
    print(f"# {name}")
    print(f"# Skrypt: {script}")
    print(f"{'#'*70}\n")
    
    script_path = os.path.join(os.path.dirname(__file__), script)
    result = subprocess.run([sys.executable, script_path], capture_output=False)
    
    return result.returncode == 0


def main():
    print("="*70)
    print("🔍 URL RESOLVER - WSZYSTKIE PRZYKŁADY")
    print("="*70)
    print("\nDostępne przykłady:")
    for i, (name, script) in enumerate(EXAMPLES, 1):
        print(f"  {i}. {name} ({script})")
    
    print("\n" + "="*70)
    
    # Ask which to run
    choice = input("\nUruchom [A]ll, [1-5] konkretny, lub [Q]uit: ").strip().lower()
    
    if choice == 'q':
        print("Do widzenia!")
        return
    
    if choice == 'a':
        for name, script in EXAMPLES:
            run_example(name, script)
            input("\nNaciśnij Enter aby kontynuować...")
    elif choice.isdigit() and 1 <= int(choice) <= len(EXAMPLES):
        idx = int(choice) - 1
        run_example(EXAMPLES[idx][0], EXAMPLES[idx][1])
    else:
        print("Nieprawidłowy wybór")


if __name__ == "__main__":
    main()
