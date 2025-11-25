# Fix: PyPI Installation Issue

## 🐛 Problem

Tests failed because they tried to install from PyPI, but package isn't published there yet.

```
ERROR: Could not find a version that satisfies the requirement curllm
ERROR: No matching distribution found for curllm
```

---

## ✅ Solution Applied

### Changed Files

**1. `docker-compose.yml`**
- Fixed volume mapping: `../../dist:/dist:ro` (was `/test/dist`)
- Fixed copy command: `cp /dist/*.whl /test/`
- All 4 services updated (ubuntu, debian, fedora, alpine)

**2. `test_pypi_install.sh`**
- Better wheel detection: `WHEEL_FILE=$(ls /test/curllm-*.whl 2>/dev/null | head -1)`
- Priority: local wheel > TestPyPI > PyPI
- Better error messages with tips

**3. `quick-test.sh`**
- Check if wheel exists before running
- Auto-build if missing
- Better feedback messages

**4. `TROUBLESHOOTING.md`** (new)
- 10+ common issues and solutions
- Debug commands
- Tips for faster iteration

---

## 🚀 How to Use Now

### Run Tests (Will Auto-Use Local Wheel)

```bash
# From project root
make test-linux
```

**System will:**
1. ✅ Check if wheel exists in `dist/`
2. ✅ Build package if needed
3. ✅ Mount wheel to containers
4. ✅ Install from wheel (NOT PyPI!)
5. ✅ Run all tests
6. ✅ Generate report

---

## 📊 Expected Behavior

### Before (Broken)
```
test-ubuntu  | [TEST] Installing from PyPI
test-ubuntu  | ERROR: Could not find curllm
test-ubuntu exited with code 1  ❌
```

### After (Fixed)
```
test-ubuntu  | [TEST] Local wheel found: curllm-1.0.21-py3-none-any.whl
test-ubuntu  | [PASS] Installed from local wheel  ✅
test-ubuntu  | [PASS] curllm_core module importable
test-ubuntu  | [PASS] All tests passed
```

---

## 🧪 Test Modes

### Mode 1: Local Wheel (Default - Recommended)

```bash
# Build package
python3 -m build

# Run tests (auto-detects wheel)
make test-linux
```

**Use when:**
- Developing locally
- Testing before PyPI publish
- CI/CD before release

### Mode 2: TestPyPI

```bash
cd tests/linux
USE_TEST_PYPI=true docker-compose up --build
```

**Use when:**
- Testing TestPyPI upload
- Verifying package metadata

### Mode 3: Production PyPI

```bash
# First, publish to PyPI
make publish

# Then remove local wheel to force PyPI install
rm dist/*.whl

# Run tests
make test-linux
```

**Use when:**
- Verifying published package
- Post-release validation

---

## ✅ Verification

### Check Wheel Exists
```bash
ls -lh dist/curllm-*.whl
# Should output: curllm-1.0.21-py3-none-any.whl
```

### Check Wheel in Container
```bash
cd tests/linux
docker-compose run test-ubuntu ls -lh /dist/
# Should show: curllm-1.0.21-py3-none-any.whl
```

### Test Single Platform
```bash
cd tests/linux
./quick-test.sh ubuntu
```

---

## 🔧 Troubleshooting

### Issue: Still can't find wheel

```bash
# Rebuild package
python3 -m build

# Verify
ls -lh dist/

# Check permissions
chmod 644 dist/*.whl
```

### Issue: Wrong wheel version

```bash
# Clean old wheels
rm dist/*.whl

# Build fresh
python3 -m build

# Verify version
ls -lh dist/
```

### Issue: Container permission denied

```bash
# Fix file permissions
chmod +x tests/linux/*.sh

# Rebuild containers
cd tests/linux
docker-compose build --no-cache
```

---

## 📚 Related Docs

- **Full Troubleshooting:** `TROUBLESHOOTING.md`
- **Linux Testing Guide:** `LINUX_TESTING.md`
- **Test README:** `tests/linux/README.md`

---

## 🎯 Summary

**Problem:** Tests tried PyPI, package not there
**Solution:** Auto-use local wheel from `dist/`
**Status:** ✅ FIXED

**Now run:** `make test-linux` 🚀
