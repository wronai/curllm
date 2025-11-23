# Makefile for curllm project

.PHONY: help install setup start stop test clean docker-build docker-up docker-down benchmark

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
	@echo "Setting up curllm..."
	@ollama pull qwen2.5:7b
	@ollama pull mistral:7b-instruct-q4_0
	@playwright install chromium
	@mkdir -p ~/.config/curllm
	@mkdir -p /tmp/curllm_screenshots
	@echo "Setup complete!"

# Service management
start:
	@echo "Starting curllm services..."
	@PORT=$${CURLLM_API_PORT:-$$(if [ -f /tmp/curllm_api_port ]; then cat /tmp/curllm_api_port; else echo 8000; fi)}; \
	while ss -ltn | grep -q ":$${PORT}\\b"; do PORT=$$((PORT+1)); done; \
	OPORT=$${CURLLM_OLLAMA_PORT:-$$(if [ -f /tmp/ollama_port ]; then cat /tmp/ollama_port; else echo 11434; fi)}; \
	while ss -ltn | grep -q ":$${OPORT}\\b"; do OPORT=$$((OPORT+1)); done; \
	echo $$PORT > /tmp/curllm_api_port; echo $$OPORT > /tmp/ollama_port; \
	if [ ! -f .env ]; then touch .env; fi; \
	if grep -q '^CURLLM_API_PORT=' .env; then sed -i "s/^CURLLM_API_PORT=.*/CURLLM_API_PORT=$$PORT/" .env; else echo "CURLLM_API_PORT=$$PORT" >> .env; fi; \
	if grep -q '^CURLLM_OLLAMA_PORT=' .env; then sed -i "s/^CURLLM_OLLAMA_PORT=.*/CURLLM_OLLAMA_PORT=$$OPORT/" .env; else echo "CURLLM_OLLAMA_PORT=$$OPORT" >> .env; fi; \
	if grep -q '^CURLLM_API_HOST=' .env; then sed -i "s#^CURLLM_API_HOST=.*#CURLLM_API_HOST=http://localhost:$$PORT#" .env; else echo "CURLLM_API_HOST=http://localhost:$$PORT" >> .env; fi; \
	if grep -q '^CURLLM_OLLAMA_HOST=' .env; then sed -i "s#^CURLLM_OLLAMA_HOST=.*#CURLLM_OLLAMA_HOST=http://localhost:$$OPORT#" .env; else echo "CURLLM_OLLAMA_HOST=http://localhost:$$OPORT" >> .env; fi; \
	if ! pgrep -x "ollama" > /dev/null; then \
		OLLAMA_HOST="127.0.0.1:$${OPORT}" ollama serve > /tmp/ollama.log 2>&1 & \
		echo "Started Ollama service on port $$OPORT"; \
		sleep 2; \
	else \
		for p in "$$CURLLM_OLLAMA_PORT" $$(cat /tmp/ollama_port 2>/dev/null) 11434 11435 11436; do \
			if [ -n "$$p" ] && curl -s "http://localhost:$$p/api/tags" > /dev/null 2>&1; then \
				OPORT="$$p"; echo $$OPORT > /tmp/ollama_port; \
				sed -i "s/^CURLLM_OLLAMA_PORT=.*/CURLLM_OLLAMA_PORT=$$OPORT/" .env 2>/dev/null || echo "CURLLM_OLLAMA_PORT=$$OPORT" >> .env; \
				sed -i "s#^CURLLM_OLLAMA_HOST=.*#CURLLM_OLLAMA_HOST=http://localhost:$$OPORT#" .env 2>/dev/null || echo "CURLLM_OLLAMA_HOST=http://localhost:$$OPORT" >> .env; \
				break; \
			fi; \
		done; \
	fi; \
	if ! curl -s http://localhost:$${PORT}/health > /dev/null 2>&1; then \
		CURLLM_OLLAMA_HOST="http://localhost:$${OPORT}" CURLLM_API_PORT=$${PORT} python3 curllm_server.py > /tmp/curllm.log 2>&1 & \
		echo $$! > /tmp/curllm.pid; \
		echo "Started curllm API server on port $$PORT"; \
		sleep 3; \
	fi; \
	echo "Services started. Check status with: curllm --status"

stop:
	@echo "Stopping curllm services..."
	@if [ -f /tmp/curllm.pid ]; then \
		kill $$(cat /tmp/curllm.pid) 2>/dev/null || true; \
		rm /tmp/curllm.pid; \
		echo "Stopped curllm API server"; \
	fi
	@pkill -f "ollama serve" 2>/dev/null || true
	@docker compose stop browserless redis 2>/dev/null || docker-compose stop browserless redis 2>/dev/null || true
	@echo "Services stopped"

restart: stop start

status:
	@echo "Service Status:"
	@echo "==============="
	@OPORT=$$(if [ -f /tmp/ollama_port ]; then cat /tmp/ollama_port; else echo 11434; fi); \
	if pgrep -x "ollama" > /dev/null; then \
		echo "✓ Ollama: Running on :$${OPORT}"; \
	else \
		echo "✗ Ollama: Not running"; \
	fi
	@PORT=$$(if [ -f /tmp/curllm_api_port ]; then cat /tmp/curllm_api_port; else echo 8000; fi); \
	if curl -s http://localhost:$${PORT}/health > /dev/null 2>&1; then \
		echo "✓ curllm API: Running on :$${PORT}"; \
	else \
		echo "✗ curllm API: Not running"; \
	fi
	@if docker ps | grep -q "browserless"; then \
		echo "✓ Browserless: Running"; \
	else \
		echo "✗ Browserless: Not running"; \
	fi

# Testing
test:
	@echo "Running tests..."
	@python3 -m pytest tests/ -v

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

release:
	@echo "Preparing release..."
	@python3 -m pip install -U build twine >/dev/null 2>&1 || true
	@python3 -m build
	@python3 -m twine check dist/*

publish: release
	@echo "Publishing to PyPI..."
	@echo "Using TWINE_USERNAME=__token__ and TWINE_PASSWORD (or PYPI_TOKEN) from environment"
	@set -e; \
	if [ -z "$$TWINE_PASSWORD" ] && [ -z "$$PYPI_TOKEN" ]; then \
		echo "Error: Set TWINE_PASSWORD or PYPI_TOKEN environment variable"; exit 1; \
	fi; \
	if [ -n "$$PYPI_TOKEN" ]; then export TWINE_USERNAME=__token__; export TWINE_PASSWORD=$$PYPI_TOKEN; fi; \
	if [ -n "$$TWINE_PASSWORD" ] && [ -z "$$TWINE_USERNAME" ]; then export TWINE_USERNAME=__token__; fi; \
	python3 -m twine upload --non-interactive dist/*

publish-test: release
	@echo "Publishing to TestPyPI..."
	@set -e; \
	if [ -z "$$TWINE_PASSWORD" ] && [ -z "$$PYPI_TOKEN" ]; then \
		echo "Error: Set TWINE_PASSWORD or PYPI_TOKEN environment variable"; exit 1; \
	fi; \
	if [ -n "$$PYPI_TOKEN" ]; then export TWINE_USERNAME=__token__; export TWINE_PASSWORD=$$PYPI_TOKEN; fi; \
	if [ -n "$$TWINE_PASSWORD" ] && [ -z "$$TWINE_USERNAME" ]; then export TWINE_USERNAME=__token__; fi; \
	python3 -m twine upload --repository testpypi --non-interactive dist/*

# Installation from scratch
bootstrap:
	@echo "Bootstrapping curllm from scratch..."
	@curl -fsSL https://ollama.ai/install.sh | sh
	@pip install --user pipx
	@pipx install playwright
	@playwright install chromium
	@make setup
	@make start
	@echo "Bootstrap complete! curllm is ready to use."
