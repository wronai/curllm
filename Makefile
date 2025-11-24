# Makefile for curllm project

.PHONY: help install setup start stop test clean docker-build docker-up docker-down benchmark examples

# Default target
help:
	@echo "curllm - Browser Automation with Local LLM"
	@echo ""
	@echo "Available targets:"
	@echo "  make install      - Install all dependencies"
	@echo "  make setup        - Complete setup (install + pull models)"
	@echo "  make start        - Start all services"
	@echo "  make stop         - Stop all services"
	@echo "  make test         - Run tests"
	@echo "  make benchmark    - Run performance benchmarks"
	@echo "  make clean        - Clean temporary files"
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

setup: install
	@chmod +x scripts/setup.sh 2>/dev/null || true
	@bash scripts/setup.sh

# Service management
start:
	@chmod +x scripts/start.sh 2>/dev/null || true
	@bash scripts/start.sh

stop:
	@chmod +x scripts/stop.sh 2>/dev/null || true
	@bash scripts/stop.sh

restart: stop start

status:
	@chmod +x scripts/status.sh 2>/dev/null || true
	@bash scripts/status.sh

# Testing
test:
	@echo "Running tests..."
	@PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/ -v

test-integration:
	@echo "Running integration tests..."
	@python3 examples.py

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
