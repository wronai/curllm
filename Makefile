# Makefile for curllm project

.PHONY: help install setup start stop restart fresh-start test clean clean-cache reinstall docker-build docker-up docker-down benchmark examples

# Default target
help:
	@echo "curllm - Browser Automation with Local LLM"
	@echo ""
	@echo "Available targets:"
	@echo "  make install         - Install all dependencies"
	@echo "  make install-browsers - Install Playwright browsers only"
	@echo "  make setup           - Complete setup (install + pull models)"
	@echo "  make start           - Start services (auto: clean-cache + reinstall + browsers)"
	@echo "  make stop            - Stop services (auto: clean-cache)"
	@echo "  make restart         - Restart services (stop + start)"
	@echo "  make fresh-start     - Complete fresh start with full cache cleanup"
	@echo "  make test            - Run tests"
	@echo "  make test-linux      - Run cross-platform Linux tests (Docker)"
	@echo "  make benchmark       - Run performance benchmarks"
	@echo "  make clean           - Clean temporary files"
	@echo "  make clean-cache     - Deep clean: remove all Python cache"
	@echo "  make reinstall       - Fast reinstall (editable mode only)"
	@echo "  make reinstall-full  - Full reinstall with all dependencies (slow)"
	@echo ""
	@echo "Docker targets:"
	@echo "  make docker-build - Build Docker images"
	@echo "  make docker-up    - Start Docker services"
	@echo "  make docker-down  - Stop Docker services"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start in development mode"
	@echo "  make lint         - Run code linting"
	@echo "  make format       - Format code"
	@echo "  make examples     - Generate runnable scripts in examples/"
	@echo "  make release      - Build sdist/wheel into dist/"
	@echo "  make publish      - Upload dist/* to PyPI using TWINE env token"
	@echo "  make publish-test - Upload dist/* to TestPyPI using TWINE env token"

# Installation targets
install:
	@echo "Installing curllm dependencies..."
	@chmod +x install.sh
	@./install.sh

install-browsers:
	@echo "🌐 Installing Playwright browsers..."
	@if [ -d "venv" ]; then \
		./venv/bin/python -m playwright install chromium 2>&1 | grep -v "Downloading" || true; \
		./venv/bin/python -m playwright install-deps chromium > /dev/null 2>&1 || true; \
	elif [ -n "$$VIRTUAL_ENV" ]; then \
		python -m playwright install chromium 2>&1 | grep -v "Downloading" || true; \
		python -m playwright install-deps chromium > /dev/null 2>&1 || true; \
	else \
		python3 -m playwright install chromium 2>&1 | grep -v "Downloading" || true; \
		python3 -m playwright install-deps chromium > /dev/null 2>&1 || true; \
	fi
	@echo "✅ Playwright browsers ready!"

setup: install
	@chmod +x scripts/setup.sh 2>/dev/null || true
	@bash scripts/setup.sh

# Service management
start: clean-cache reinstall install-browsers
	@chmod +x scripts/start.sh 2>/dev/null || true
	@bash scripts/start.sh

stop:
	@chmod +x scripts/stop.sh 2>/dev/null || true
	@bash scripts/stop.sh
	@echo "🧹 Cleaning Python cache..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache 2>/dev/null || true
	@rm -rf build dist 2>/dev/null || true
	@echo "✅ Cache cleaned!"

restart: stop start

fresh-start: clean-cache reinstall start

status:
	@chmod +x scripts/status.sh 2>/dev/null || true
	@bash scripts/status.sh

# Testing
test:
	@echo "Running tests..."
	@PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/ -v

test-e2e-diff:
	@echo "Running E2E diff test..."
	@chmod +x tests/e2e_diff.sh
	@bash tests/e2e_diff.sh

test-curlx-e2e:
	@echo "Running curlx e2e (single-container)..."
	@chmod +x curlx_pkg/tests/e2e/test_e2e.sh
	@bash curlx_pkg/tests/e2e/test_e2e.sh

test-curlx-compose:
	@echo "Running curlx e2e with docker-compose (api + remote-proxy)..."
	@chmod +x curlx_pkg/tests/e2e/test_compose.sh
	@bash curlx_pkg/tests/e2e/test_compose.sh

test-integration:
	@echo "Running integration tests..."
	@python3 examples.py

test-linux:
	@echo "Running cross-platform Linux tests..."
	@chmod +x tests/linux/run_tests.sh
	@cd tests/linux && ./run_tests.sh
	@echo ""
	@echo "✓ Results available in tests/linux/LINUX_TEST_RESULTS.md"
	@echo "✓ Also copied to LINUX_TEST_RESULTS.md in project root"

benchmark:
	@echo "Running performance benchmark..."
	@python3 -c "import asyncio; from examples import benchmark_models; asyncio.run(benchmark_models())"

# Docker management
docker-build:
	@echo "Building Docker images..."
	@docker-compose build

docker-up:
	@echo "Starting Docker services..."
	@docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 10
	@docker-compose ps

docker-down:
	@echo "Stopping Docker services..."
	@docker-compose down

docker-logs:
	@docker-compose logs -f --tail=100

docker-clean:
	@docker-compose down -v
	@docker system prune -f

# Development
dev:
	@echo "Starting in development mode..."
	@CURLLM_DEBUG=true python3 curllm_server.py

watch:
	@echo "Watching for changes..."
	@while true; do \
		inotifywait -e modify *.py; \
		echo "Restarting server..."; \
		make restart; \
	done

lint:
	@echo "Running linters..."
	@python3 -m flake8 *.py --max-line-length=120
	@python3 -m pylint *.py --disable=C0114,C0115,C0116

format:
	@echo "Formatting code..."
	@python3 -m black *.py --line-length=120
	@python3 -m isort *.py

# Docs & examples
examples:
	@echo "Generating example scripts..."
	@chmod +x tools/generate_examples.sh || true
	@bash tools/generate_examples.sh
	@echo "Done. See examples/curllm-*.sh"

# Utilities
clean:
	@echo "Cleaning temporary files..."
	@rm -rf __pycache__ *.pyc
	@rm -rf .pytest_cache
	@rm -rf /tmp/curllm_screenshots/*
	@rm -f /tmp/curllm.log /tmp/ollama.log
	@echo "Cleaned!"

clean-cache:
	@echo "🧹 Cleaning Python cache..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache 2>/dev/null || true
	@rm -rf build dist 2>/dev/null || true
	@echo "✅ Cache cleaned!"

reinstall:
	@echo "🔄 Reinstalling curllm package (fast - editable mode only)..."
	@if [ -d "venv" ]; then \
		./venv/bin/pip install -e . -q 2>/dev/null || ./venv/bin/pip install -e .; \
	elif [ -n "$$VIRTUAL_ENV" ]; then \
		pip install -e . -q 2>/dev/null || pip install -e .; \
	else \
		python3 -m pip install -e . --break-system-packages -q 2>/dev/null || python3 -m pip install -e . --break-system-packages; \
	fi
	@echo "✅ Package reinstalled!"

reinstall-full:
	@echo "🔄 Full reinstall with all dependencies (slow - downloads from internet)..."
	@if [ -d "venv" ]; then \
		./venv/bin/pip install -e . --force-reinstall --no-cache-dir -q 2>/dev/null || ./venv/bin/pip install -e . --force-reinstall --no-cache-dir; \
	elif [ -n "$$VIRTUAL_ENV" ]; then \
		pip install -e . --force-reinstall --no-cache-dir -q 2>/dev/null || pip install -e . --force-reinstall --no-cache-dir; \
	else \
		python3 -m pip install -e . --force-reinstall --no-cache-dir --break-system-packages -q 2>/dev/null || python3 -m pip install -e . --force-reinstall --no-cache-dir --break-system-packages; \
	fi
	@echo "✅ Full reinstall complete!"

logs:
	@echo "=== Ollama Logs ==="
	@tail -n 50 /tmp/ollama.log 2>/dev/null || echo "No Ollama logs"
	@echo ""
	@echo "=== curllm API Logs ==="
	@tail -n 50 /tmp/curllm.log 2>/dev/null || echo "No API logs"

# Model management
models-list:
	@echo "Available models:"
	@ollama list

models-pull:
	@echo "Pulling recommended models..."
	@ollama pull qwen2.5:7b
	@ollama pull mistral:7b-instruct-q4_0
	@ollama pull llama3.2:3b
	@ollama pull phi3:mini

models-clean:
	@echo "Removing unused models..."
	@ollama rm $$(ollama list | tail -n +2 | awk '{print $$1}' | grep -v "qwen2.5:7b")

# Quick examples
example-extract:
	@curllm "https://example.com" -d "extract all email addresses"

example-form:
	@curllm --visual --stealth -d "fill contact form with test data" https://example.com/contact

example-bql:
	@curllm --bql -d 'query { page(url: "https://example.com") { title links { href text } } }'

# Release

version-bump:
	@echo "Bumping patch version in pyproject.toml..."
	@python3 -c "import re,sys; p='pyproject.toml'; s=open(p,'r',encoding='utf-8').read(); m=re.search(r'(?m)^version\\s*=\\s*\"(\\d+)\\.(\\d+)\\.(\\d+)\"', s);\
	import sys as _s;\
	[(_s.stderr.write('Could not find version in pyproject.toml\n'), _s.exit(1)) for _ in []] if m else (_s.stderr.write('Could not find version in pyproject.toml\n') or _s.exit(1));\
	a,b,c=map(int,m.groups()); new=f'{a}.{b}.{c+1}'; s=re.sub(r'(?m)^version\\s*=\\s*\".*?\"', f'version = \"{new}\"', s, 1); open(p,'w',encoding='utf-8').write(s); print(new)"

release:
	@echo "Preparing release..."
	@rm -rf dist build 2>/dev/null || true
	@python3 -m pip install -U build twine >/dev/null 2>&1 || true
	@python3 -m build
	@python3 -m twine check dist/*

publish: version-bump release
	@echo "Publishing to PyPI..."
	@TWINE_USERNAME=$${TWINE_USERNAME:-__token__} python3 -m twine upload --non-interactive dist/*

publish-test: version-bump release
	@echo "Publishing to TestPyPI..."
	@TWINE_USERNAME=$${TWINE_USERNAME:-__token__} python3 -m twine upload --repository testpypi --non-interactive dist/*

# Installation from scratch
bootstrap:
	@echo "Bootstrapping curllm from scratch..."
	@chmod +x scripts/bootstrap.sh 2>/dev/null || true
	@bash scripts/bootstrap.sh
