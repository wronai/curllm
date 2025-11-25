# Linux Tests Troubleshooting Guide

## 🔧 Common Issues and Solutions

### Issue 1: "Could not find a version that satisfies the requirement curllm"

**Symptom:**
```
ERROR: Could not find a version that satisfies the requirement curllm (from versions: none)
ERROR: No matching distribution found for curllm
```

**Cause:** Package not published on PyPI, and local wheel not found.

**Solution:**
```bash
# Build package first
cd /path/to/curllm
python3 -m build

# Verify wheel exists
ls -lh dist/curllm-*.whl

# Run tests (will auto-detect wheel)
make test-linux
```

---

### Issue 2: Alpine - Playwright dependency conflict

**Symptom:**
```
ERROR: Cannot install curllm because these package versions have conflicting dependencies.
The conflict is caused by:
    curllm depends on playwright
```

**Cause:** Alpine Linux uses musl libc instead of glibc, which can cause compatibility issues with some Python packages.

**Solution:**

**Option A:** Skip Alpine tests (test on Ubuntu, Debian, Fedora only)
```bash
cd tests/linux
docker-compose up --build test-ubuntu test-debian test-fedora
```

**Option B:** Use Alpine-specific Dockerfile with pre-compiled dependencies
```dockerfile
# Dockerfile.alpine - Add playwright deps manually
RUN apk add --no-cache \
    chromium \
    chromium-chromedriver
```

**Option C:** Accept Alpine limitations - Mark as "partial support"

---

### Issue 3: Tests abort early (exit code 1 or 137)

**Symptom:**
```
curllm-test-ubuntu exited with code 1
Aborting on container exit...
```

**Cause:** `--abort-on-container-exit` flag in docker-compose causes all tests to stop if one fails.

**Solution:**

**For development (see all results):**
```bash
cd tests/linux

# Edit docker-compose.yml temporarily
# Comment out abort-on-container-exit

# Or run individually
make ubuntu
make debian
make fedora
```

**For CI/CD (keep as-is):**
- Fast failure is good for CI/CD
- Fix failing test first before running all

---

### Issue 4: Volume mounting issues

**Symptom:**
```
cp: cannot stat '/dist/*.whl': No such file or directory
```

**Cause:** dist/ directory not properly mounted or wheel not present.

**Solution:**
```bash
# Check if dist exists
ls -lh ../../dist/

# If empty, build package
python3 -m build

# Check permissions
ls -ld dist/
chmod 755 dist/

# Verify mount in container
docker run --rm -v "$(pwd)/../../dist:/dist:ro" alpine ls -lh /dist
```

---

### Issue 5: "Permission denied" errors

**Symptom:**
```
bash: /test/test_pypi_install.sh: Permission denied
```

**Cause:** Script not executable.

**Solution:**
```bash
chmod +x tests/linux/*.sh
chmod +x tests/linux/*.py
```

---

### Issue 6: Old images cached

**Symptom:**
Tests run old code even after changes.

**Solution:**
```bash
cd tests/linux

# Rebuild without cache
docker-compose build --no-cache

# Or clean everything
docker-compose down
docker system prune -f
docker-compose up --build
```

---

### Issue 7: Results not generated

**Symptom:**
```
No results file generated - test may have failed early
```

**Cause:** Test script exited before writing results.

**Solution:**
```bash
# Check container logs
docker logs curllm-test-ubuntu

# Run interactively
docker-compose run test-ubuntu /bin/bash
# Then manually run: /test/test_pypi_install.sh
```

---

### Issue 8: Python version mismatch

**Symptom:**
```
ImportError: cannot import name 'X' from 'Y'
```

**Cause:** Package requires specific Python version.

**Solution:**

Check requirements:
```bash
grep "python_requires" pyproject.toml
```

Update Dockerfile:
```dockerfile
# For newer Python on Ubuntu
FROM ubuntu:24.04  # Python 3.12
# instead of:
FROM ubuntu:22.04  # Python 3.10
```

---

### Issue 9: Network timeouts

**Symptom:**
```
Timeout: PyPI download taking too long
```

**Solution:**
```bash
# Use local wheel (faster)
python3 -m build
make test-linux

# Or increase timeout
docker-compose up --timeout 600
```

---

### Issue 10: Disk space issues

**Symptom:**
```
no space left on device
```

**Solution:**
```bash
# Clean Docker
docker system prune -a -f

# Remove old images
docker image prune -a -f

# Check disk usage
docker system df

# Remove unused volumes
docker volume prune -f
```

---

## 🔍 Debugging Commands

### View logs
```bash
# Live logs
docker-compose logs -f

# Specific container
docker logs curllm-test-ubuntu

# Save logs
docker logs curllm-test-ubuntu > ubuntu-logs.txt
```

### Interactive debugging
```bash
# Run container with bash
docker-compose run test-ubuntu /bin/bash

# Inside container:
source /test/venv/bin/activate
python3 --version
pip list
ls -lh /test/
/test/test_pypi_install.sh
```

### Check file permissions
```bash
# In container
docker-compose run test-ubuntu ls -lah /test/
docker-compose run test-ubuntu ls -lah /dist/
```

### Verify wheel
```bash
# Check wheel contents
unzip -l dist/curllm-*.whl

# Check metadata
python3 -m pip show curllm
```

---

## 💡 Tips

### Faster iteration
```bash
# Test one platform only
./quick-test.sh ubuntu

# Skip build step
docker-compose up --no-build test-ubuntu
```

### Parallel debugging
```bash
# Open multiple terminals
# Terminal 1:
docker-compose logs -f test-ubuntu

# Terminal 2:
docker-compose logs -f test-debian

# Terminal 3:
docker exec -it curllm-test-ubuntu /bin/bash
```

### Clean slate
```bash
# Full cleanup
make clean
docker-compose down -v
docker system prune -a -f

# Rebuild
make test-linux
```

---

## 📚 Related Docs

- **Main README:** `tests/linux/README.md`
- **Linux Testing Guide:** `LINUX_TESTING.md`
- **Docker Compose:** `docker-compose.yml`

---

## 🆘 Still Having Issues?

1. **Check logs:** `docker-compose logs`
2. **Run individually:** `make ubuntu` (one at a time)
3. **Interactive mode:** `docker-compose run test-ubuntu bash`
4. **Clean rebuild:** `docker-compose build --no-cache`
5. **Verify wheel:** `ls -lh dist/` and `unzip -l dist/*.whl`

---

**Happy Testing!** 🚀
