# Makefile for curlx package

.PHONY: help release publish publish-test clean

help:
	@echo "curlx - Proxy helper for curllm"
	@echo "Targets:"
	@echo "  make release       - Build sdist/wheel into dist/"
	@echo "  make publish       - Upload dist/* to PyPI (requires TWINE_PASSWORD token)"
	@echo "  make publish-test  - Upload dist/* to TestPyPI"
	@echo "  make clean         - Remove build artifacts"

release:
	@echo "Preparing curlx release..."
	@rm -rf dist build 2>/dev/null || true
	@python3 -m pip install -U build twine >/dev/null 2>&1 || true
	@python3 -m build
	@python3 -m twine check dist/*

publish: release
	@echo "Publishing curlx to PyPI..."
	@TWINE_USERNAME=$${TWINE_USERNAME:-__token__} python3 -m twine upload --non-interactive dist/*

publish-test: release
	@echo "Publishing curlx to TestPyPI..."
	@TWINE_USERNAME=$${TWINE_USERNAME:-__token__} python3 -m twine upload --repository testpypi --non-interactive dist/*

clean:
	@rm -rf dist build *.egg-info
