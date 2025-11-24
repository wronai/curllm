# Makefile for website monitoring with curllm

.PHONY: help deps setup run run-now install install-3h install-06 remove edit-env logs

help:
	@echo "Monitoring with curllm"
	@echo "Targets:"
	@echo "  make deps       - Install jq across common Linux distros (requires sudo)"
	@echo "  make setup       - Check dependencies and create .env if missing"
	@echo "  make run         - Run monitoring once (uses .env)"
	@echo "  make run-now     - Alias for run"
	@echo "  make install-3h  - Install cron job every 3 hours"
	@echo "  make install-06  - Install cron job daily at 06:00"
	@echo "  make install     - Install cron using CRON_EXPR env (fallback 3h)"
	@echo "  make remove      - Remove cron job"
	@echo "  make logs        - Show recent monitor logs"
	@echo "  make edit-env    - Create/open .env"

deps:
	@echo "Installing dependencies (jq)..."
	@set -e; \
	if command -v jq >/dev/null 2>&1; then \
	  echo "✓ jq already installed"; \
	else \
	  if command -v apt-get >/dev/null 2>&1; then \
	    echo "Using apt-get"; sudo apt-get update && sudo apt-get install -y jq; \
	  elif command -v dnf >/dev/null 2>&1; then \
	    echo "Using dnf"; sudo dnf install -y jq; \
	  elif command -v yum >/dev/null 2>&1; then \
	    echo "Using yum"; sudo yum install -y jq; \
	  elif command -v pacman >/dev/null 2>&1; then \
	    echo "Using pacman"; sudo pacman -Sy --noconfirm jq; \
	  elif command -v zypper >/dev/null 2>&1; then \
	    echo "Using zypper"; sudo zypper install -y jq; \
	  elif command -v apk >/dev/null 2>&1; then \
	    echo "Using apk"; sudo apk add --no-cache jq; \
	  else \
	    echo "Could not detect package manager. Please install 'jq' manually."; exit 2; \
	  fi; \
	fi

setup:
	@[ -f .env ] || cp -n .env.example .env || true
	@echo "Checking dependencies..."
	@command -v jq >/dev/null 2>&1 && echo "✓ jq found" || echo "✗ jq missing (install via your package manager)"
	@command -v curllm >/dev/null 2>&1 && echo "✓ curllm found" || echo "✗ curllm missing (see root README.md)"

run:
	@chmod +x website_monitor.sh
	@./website_monitor.sh run

run-now: run

install:
	@chmod +x website_monitor.sh
	@./website_monitor.sh install

install-3h:
	@chmod +x website_monitor.sh
	@CRON_EXPR="0 */3 * * *" ./website_monitor.sh install

install-06:
	@chmod +x website_monitor.sh
	@CRON_EXPR="0 6 * * *" ./website_monitor.sh install

remove:
	@chmod +x website_monitor.sh
	@./website_monitor.sh remove

edit-env:
	@[ -f .env ] || cp .env.example .env
	@${EDITOR:-nano} .env

logs:
	@tail -n 200 /tmp/curllm_monitor.log 2>/dev/null || echo "No logs yet"
