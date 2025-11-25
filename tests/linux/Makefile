# Makefile for Linux cross-platform tests

.PHONY: help test build clean ubuntu debian fedora alpine report

help:
	@echo "curllm Linux Cross-Platform Tests"
	@echo ""
	@echo "Available targets:"
	@echo "  make test        - Run all tests"
	@echo "  make ubuntu      - Test Ubuntu only"
	@echo "  make debian      - Test Debian only"
	@echo "  make fedora      - Test Fedora only"
	@echo "  make alpine      - Test Alpine only"
	@echo "  make build       - Build package"
	@echo "  make report      - Generate report from existing results"
	@echo "  make clean       - Clean results and containers"

test:
	@chmod +x run_tests.sh
	@./run_tests.sh

ubuntu:
	@mkdir -p results
	@docker-compose up --build test-ubuntu

debian:
	@mkdir -p results
	@docker-compose up --build test-debian

fedora:
	@mkdir -p results
	@docker-compose up --build test-fedora

alpine:
	@mkdir -p results
	@docker-compose up --build test-alpine

build:
	@echo "Building package..."
	@cd ../.. && python3 -m build

report:
	@echo "Generating report..."
	@python3 generate_report.py

clean:
	@echo "Cleaning up..."
	@rm -rf results/*.json
	@rm -f LINUX_TEST_RESULTS.md
	@docker-compose down
	@echo "✓ Cleaned"
