# Cross-Platform Linux Tests for curllm

## 🎯 Purpose

Test curllm package installation and functionality across multiple Linux distributions to ensure PyPI compatibility.

## 🐧 Tested Distributions

- **Ubuntu** 22.04 LTS
- **Debian** 12 (Bookworm)
- **Fedora** 39
- **Alpine** 3.19

## 🚀 Quick Start

### Run All Tests

```bash
make test-linux
```

This will:
1. Build the package (if needed)
2. Run tests on all distributions in parallel (Docker)
3. Generate Markdown report
4. Save results to `LINUX_TEST_RESULTS.md`

### Expected Output

```
╔════════════════════════════════════════════╗
║   curllm Cross-Platform Linux Tests       ║
╚════════════════════════════════════════════╝

Starting tests on all platforms...

test-ubuntu_1  | [PASS] Python 3 installed: 3.10.12
test-ubuntu_1  | [PASS] pip installed
test-ubuntu_1  | [PASS] Virtual environment created
test-ubuntu_1  | [PASS] Installed from local wheel
...

✓ Report generated: LINUX_TEST_RESULTS.md
```

## 📊 Test Coverage

### Test Categories

1. **Environment Tests**
   - Python version check
   - pip availability
   - Virtual environment creation

2. **Installation Tests**
   - PyPI installation
   - Local wheel installation
   - TestPyPI installation (optional)

3. **Package Tests**
   - Module imports
   - Class instantiation
   - CLI command availability

4. **Dependency Tests**
   - Playwright installation
   - Flask availability
   - Required packages

5. **Functionality Tests**
   - Executor creation
   - Basic operations
   - Module structure

## 🛠️ Usage

### Run Tests

```bash
# From project root
make test-linux

# Or from tests/linux directory
cd tests/linux
./run_tests.sh
```

### Run Single Distribution

```bash
cd tests/linux

# Ubuntu only
docker-compose up --build test-ubuntu

# Debian only
docker-compose up --build test-debian

# Fedora only
docker-compose up --build test-fedora

# Alpine only
docker-compose up --build test-alpine
```

### Use TestPyPI

```bash
cd tests/linux
USE_TEST_PYPI=true docker-compose up --build
```

### Use Local Wheel

```bash
# Build package first
cd ../..
python3 -m build

# Run tests (will auto-detect dist/*.whl)
cd tests/linux
./run_tests.sh
```

## 📝 Results

### JSON Results

Individual results saved to `results/*.json`:

```
results/
  ubuntu.json
  debian.json
  fedora.json
  alpine.json
```

Example JSON:
```json
{
  "distro": "ubuntu",
  "version": "22.04",
  "python_version": "3.10.12",
  "tests_passed": 15,
  "tests_failed": 0,
  "duration": 42,
  "timestamp": "2025-11-25T10:30:00Z",
  "tests": [
    {"name": "Python 3 installed", "status": "pass"},
    ...
  ]
}
```

### Markdown Report

Generated report: `LINUX_TEST_RESULTS.md`

Contains:
- Summary table
- Detailed results per distribution
- Platform compatibility matrix
- Recommendations
- Installation instructions

## 🔧 Configuration

### Environment Variables

- `USE_TEST_PYPI` - Use TestPyPI instead of PyPI (default: false)

### Dockerfile Customization

Each distribution has its own Dockerfile:
- `Dockerfile.ubuntu` - Ubuntu 22.04
- `Dockerfile.debian` - Debian 12
- `Dockerfile.fedora` - Fedora 39
- `Dockerfile.alpine` - Alpine 3.19

Modify these to test different versions.

## 🐛 Troubleshooting

### Docker Not Found

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Or use docker-compose instead
pip install docker-compose
```

### Build Fails

```bash
# Clean and rebuild
cd tests/linux
docker-compose down
docker-compose build --no-cache
```

### Tests Timeout

Increase timeout in `docker-compose.yml`:
```yaml
services:
  test-ubuntu:
    ...
    stop_grace_period: 5m
```

### Missing Wheel

```bash
# Build package manually
cd ../..
python3 -m build

# Check dist/
ls -lh dist/
```

## 📚 Files

```
tests/linux/
├── README.md                    # This file
├── Dockerfile.ubuntu            # Ubuntu test environment
├── Dockerfile.debian            # Debian test environment
├── Dockerfile.fedora            # Fedora test environment
├── Dockerfile.alpine            # Alpine test environment
├── docker-compose.yml           # Orchestration config
├── test_pypi_install.sh         # Main test script
├── run_tests.sh                 # Test runner
├── generate_report.py           # Report generator
├── results/                     # JSON results (generated)
│   ├── ubuntu.json
│   ├── debian.json
│   ├── fedora.json
│   └── alpine.json
└── LINUX_TEST_RESULTS.md        # Markdown report (generated)
```

## 🎯 Test Success Criteria

Tests are considered successful if:

- ✅ Package installs without errors
- ✅ All modules are importable
- ✅ Executor can be instantiated
- ✅ Dependencies are satisfied
- ✅ CLI commands work (if applicable)

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
name: Linux Cross-Platform Tests

on: [push, pull_request]

jobs:
  test-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: make test-linux
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: LINUX_TEST_RESULTS.md
```

### GitLab CI Example

```yaml
test:linux:
  stage: test
  image: docker:latest
  services:
    - docker:dind
  script:
    - make test-linux
  artifacts:
    paths:
      - LINUX_TEST_RESULTS.md
```

## 📊 Expected Results

All tests should pass on all distributions:

```
| Distribution | Tests Passed | Tests Failed | Status |
|--------------|--------------|--------------|--------|
| Ubuntu       | 15           | 0            | ✅ PASS |
| Debian       | 15           | 0            | ✅ PASS |
| Fedora       | 15           | 0            | ✅ PASS |
| Alpine       | 15           | 0            | ✅ PASS |
```

## 🚀 Next Steps

After successful tests:

1. ✅ Review `LINUX_TEST_RESULTS.md`
2. ✅ Fix any failing tests
3. ✅ Update package dependencies if needed
4. ✅ Commit results to repo
5. ✅ Proceed with PyPI release

## 📝 Contributing

To add a new distribution:

1. Create `Dockerfile.<distro>`
2. Add service to `docker-compose.yml`
3. Update this README
4. Run tests: `make test-linux`

## 📄 License

Same as curllm project.

---

**Generated by curllm test suite** 🚀
