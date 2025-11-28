# Cross-Platform Linux Testing Guide

> **⚠️ IMPORTANT:** Tests now use **local wheel** from `dist/` by default (not PyPI).  
> **See:** `LINUX_TESTS_FIXED.md` for recent fixes.

## 🎯 Overview

Automated testing system for curllm package across multiple Linux distributions using Docker.

## 🐧 Supported Platforms

| Distribution | Version | Python | Status |
|--------------|---------|--------|--------|
| **Ubuntu** | 22.04 LTS | 3.10+ | ✅ Tested |
| **Debian** | 12 (Bookworm) | 3.11+ | ✅ Tested |
| **Fedora** | 39 | 3.12+ | ✅ Tested |
| **Alpine** | 3.19 | 3.11+ | ✅ Tested |

## 🚀 Quick Start

### Prerequisites

```bash
# Docker required
docker --version

# Docker Compose required
docker-compose --version  # or: docker compose version
```

### Run Tests

```bash
# From project root
make test-linux
```

**Expected output:**
```
╔════════════════════════════════════════════╗
║   curllm Cross-Platform Linux Tests       ║
╚════════════════════════════════════════════╝

Building package...
✓ Package built

Starting tests on all platforms...

[+] Running 4/4
 ⠿ Container curllm-test-ubuntu  Started  2.1s
 ⠿ Container curllm-test-debian  Started  2.3s
 ⠿ Container curllm-test-fedora  Started  2.2s
 ⠿ Container curllm-test-alpine  Started  2.4s

test-ubuntu_1  | [TEST] Python environment check
test-ubuntu_1  | [PASS] Python 3 installed: 3.10.12
test-ubuntu_1  | [PASS] pip installed
...

Tests completed. Generating report...
✓ Report generated: LINUX_TEST_RESULTS.md

═══════════════════════════════════════════
Test Summary:
| Distribution | Tests Passed | Tests Failed | Status |
| Ubuntu       | 15           | 0            | ✅ PASS |
| Debian       | 15           | 0            | ✅ PASS |
| Fedora       | 15           | 0            | ✅ PASS |
| Alpine       | 15           | 0            | ✅ PASS |
═══════════════════════════════════════════

✓ Results available in LINUX_TEST_RESULTS.md
```

## 📊 Test Coverage

### Test Categories

**1. Environment Tests**
- ✅ Python 3.8+ installed
- ✅ pip available
- ✅ venv module working

**2. Installation Tests**
- ✅ PyPI package installation
- ✅ Local wheel installation
- ✅ Dependencies resolution

**3. Import Tests**
- ✅ Core modules importable
- ✅ Executor class available
- ✅ Module structure intact

**4. Functionality Tests**
- ✅ Executor instantiation
- ✅ CLI command available
- ✅ Help/version commands

**5. Dependency Tests**
- ✅ Playwright installed
- ✅ Flask available
- ✅ Async libraries present

## 🔧 Advanced Usage

### Test Single Distribution

```bash
cd tests/linux

# Ubuntu only
make ubuntu

# Debian only
make debian

# Fedora only
make fedora

# Alpine only
make alpine
```

### Use TestPyPI

Test installation from TestPyPI:

```bash
cd tests/linux
USE_TEST_PYPI=true ./run_tests.sh
```

### Use Production PyPI

Test installation from production PyPI:

```bash
cd tests/linux
# Remove local wheel to force PyPI install
rm ../../dist/*.whl
./run_tests.sh
```

### Test Specific Python Version

Modify Dockerfile:

```dockerfile
# Dockerfile.ubuntu
FROM ubuntu:22.04
# Change to:
FROM ubuntu:24.04  # Uses Python 3.12
```

## 📝 Results

### Locations

- **JSON Results:** `tests/linux/results/*.json`
- **Markdown Report:** `tests/linux/LINUX_TEST_RESULTS.md`
- **Root Copy:** `LINUX_TEST_RESULTS.md` (project root)

### Report Contents

1. **Summary Table**
   - Distribution, version, Python version
   - Tests passed/failed count
   - Duration, status

2. **Detailed Results**
   - Per-distribution breakdown
   - Individual test status
   - Failed test details

3. **Compatibility Matrix**
   - Feature availability across platforms
   - Cross-platform comparison

4. **Recommendations**
   - Installation readiness
   - Platform notes
   - Known issues

## 🐛 Troubleshooting

### Problem: Docker permission denied

```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Or run with sudo (not recommended)
sudo make test-linux
```

### Problem: Port conflicts

```bash
# Docker might use ports
# Check and stop conflicting containers
docker ps
docker stop <container_id>
```

### Problem: Build fails

```bash
# Clean everything
cd tests/linux
make clean
docker system prune -f

# Rebuild
make test
```

### Problem: Slow builds

```bash
# Use local package cache
cd tests/linux
docker-compose build --parallel
```

### Problem: Out of disk space

```bash
# Clean Docker
docker system prune -a -f

# Clean old images
docker image prune -a -f
```

## 📦 File Structure

```
tests/linux/
├── README.md                    # Detailed documentation
├── Makefile                     # Local commands
├── .gitignore                   # Ignore results
├── Dockerfile.ubuntu            # Ubuntu environment
├── Dockerfile.debian            # Debian environment
├── Dockerfile.fedora            # Fedora environment
├── Dockerfile.alpine            # Alpine environment
├── docker-compose.yml           # Orchestration
├── test_pypi_install.sh         # Test script
├── run_tests.sh                 # Test runner
├── generate_report.py           # Report generator
├── results/                     # Test results (git-ignored)
│   ├── ubuntu.json
│   ├── debian.json
│   ├── fedora.json
│   └── alpine.json
├── LINUX_TEST_RESULTS.md        # Report (git-ignored)
└── LINUX_TEST_RESULTS.template.md  # Example report
```

## 🔄 CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/test-linux.yml
name: Linux Cross-Platform Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test-linux:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Build package
        run: |
          pip install build
          python -m build
      
      - name: Run Linux tests
        run: make test-linux
      
      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: linux-test-results
          path: LINUX_TEST_RESULTS.md
      
      - name: Comment PR with results
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const results = fs.readFileSync('LINUX_TEST_RESULTS.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: results
            });
```

### GitLab CI

```yaml
# .gitlab-ci.yml
test:linux:
  stage: test
  image: docker:latest
  services:
    - docker:dind
  
  before_script:
    - apk add --no-cache python3 py3-pip make
    - pip3 install build
  
  script:
    - python3 -m build
    - make test-linux
  
  artifacts:
    paths:
      - LINUX_TEST_RESULTS.md
    reports:
      junit: tests/linux/results/*.json
  
  only:
    - main
    - merge_requests
```

## 📊 Success Criteria

Tests pass if:

- ✅ **All tests pass** on all distributions
- ✅ **Package installs** without errors
- ✅ **Imports work** for all modules
- ✅ **Executor creates** successfully
- ✅ **Dependencies** are satisfied

## 🎯 Use Cases

### Before PyPI Release

```bash
# 1. Build package
python3 -m build

# 2. Test on all platforms
make test-linux

# 3. Review results
cat LINUX_TEST_RESULTS.md

# 4. If all pass, publish
make publish
```

### For PRs

```bash
# Test changes
git checkout feature-branch
make test-linux

# If tests pass, merge
git checkout main
git merge feature-branch
```

### For Bug Reports

```bash
# Reproduce on specific platform
cd tests/linux
make ubuntu  # or debian, fedora, alpine

# Check logs
docker logs curllm-test-ubuntu
```

## 📚 Related Documentation

- **Main Tests:** `tests/` directory
- **Docker Setup:** `docker-compose.yml`
- **Package Build:** `pyproject.toml`
- **Installation:** `README.md`

## ✨ Features

- 🐳 **Isolated environments** - Each distribution in separate container
- 🚀 **Parallel execution** - All tests run simultaneously
- 📊 **Detailed reports** - JSON + Markdown output
- 🔄 **CI/CD ready** - GitHub Actions / GitLab CI examples
- 📦 **Local & PyPI** - Test both installation methods
- 🎯 **Comprehensive** - 15+ tests per platform

## 🎉 Success Story

**Before:** Manual testing on different VMs, time-consuming, error-prone

**After:** `make test-linux` → Automated, fast, reliable

```
15 tests × 4 platforms = 60 tests in ~3 minutes ⚡
```

---

**Ready to test?** Run `make test-linux` now! 🚀
