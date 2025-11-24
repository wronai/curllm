# Monitoring Examples

Docs: [Monitoring Home](README.md) | [curllm (root)](../README.md) | [Remote Proxy Tutorial](../docs/REMOTE_PROXY_TUTORIAL.md)

Below are ready-to-run examples for the monitoring toolkit. Run them from this folder unless noted otherwise.

## 1) Run once (default)

```bash
make run
```

## 2) Run once with explicit recipient (override .env)

```bash
MAIL_TO=you@example.com make run
```

## 3) Install cron every 3 hours

```bash
make install-3h
```

## 4) Install cron daily at 06:00

```bash
make install-06
```

## 5) Remove cron job

```bash
make remove
```

## 6) Use public proxy rotation

```bash
# Recommended: set your own public list (URL/CSV/file)
export CURLLM_PUBLIC_PROXY_LIST="https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"
CURLLM_ARGS="--headless --stealth --proxy rotate:public" make run
```

## 7) Use registry rotation (after registering proxies)

```bash
# in project root (example):
# curlx register --host 203.0.113.10 --ports 3128,3129 --server http://localhost:8000
CURLLM_ARGS="--headless --stealth --proxy rotate:registry" make run
```

## 8) Custom CSV file

```bash
CSV_FILE="/path/to/my_urls.csv" make run
```

## 9) Tuning issue detection

```bash
# Only flag pages whose title matches these patterns (regex)
ISSUE_PATTERNS='error|forbidden|captcha|timeout|(5\d\d)' make run
```

## 10) Logs and quick debugging

```bash
make logs
bash -x ./website_monitor.sh run
```

---

Tips:
- You can combine overrides: `CSV_FILE=... CURLLM_ARGS="--headless --stealth" make run`
- If `MAIL_TO` is not set, the report is printed to stderr instead of sending an email.
- For more, see [README.md](README.md).
