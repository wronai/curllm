#!/usr/bin/env bash
set -euo pipefail

# curllm Website Monitor
# - Reads monitoring/url.csv (one URL per line)
# - Uses curllm to take a screenshot and detect issues
# - Sends a single email with attachments if any URL looks bad
# - Manage cron: install/remove job (every 3 hours)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CSV_FILE_DEFAULT="$REPO_DIR/monitoring/url.csv"
CSV_FILE="${CSV_FILE:-$CSV_FILE_DEFAULT}"
ENV_FILE="$REPO_DIR/monitoring/.env"
PY_SEND="$REPO_DIR/monitoring/send_email.py"
TAG="# curllm-website-monitor"
LOG_FILE="/tmp/curllm_monitor.log"

# Load optional environment for SMTP and monitor settings
# Autoload .env; create from example if missing
if [ ! -f "$ENV_FILE" ] && [ -f "$REPO_DIR/monitoring/.env.example" ]; then
  cp "$REPO_DIR/monitoring/.env.example" "$ENV_FILE"
fi
if [ -f "$ENV_FILE" ]; then
  # Safe loader: do not source directly to avoid interpreting pipes/spaces
  while IFS= read -r __line; do
    # strip comments
    case "$__line" in
      ''|\#*) continue;;
    esac
    # keep everything after first '=' as value (can contain spaces/pipes)
    __key="${__line%%=*}"
    __val="${__line#*=}"
    # trim whitespace around key
    __key="${__key%%[[:space:]]*}"
    __key="${__key##[[:space:]]}"
    [ -z "$__key" ] && continue
    # export as single argument to avoid word-splitting
    declare -x "${__key}=${__val}"
  done < "$ENV_FILE"
fi

# Recompute effective CSV_FILE after env load (empty CSV_FILE in .env should fallback to default)
if [ -z "${CSV_FILE:-}" ]; then
  CSV_FILE="$CSV_FILE_DEFAULT"
fi

MAIL_TO_DEFAULT="${MAIL_TO:-}"
CURLLM_BIN="${CURLLM_BIN:-curllm}"
JQ_BIN="${JQ_BIN:-jq}"
CURLLM_ARGS="${CURLLM_ARGS:-}"

# Keywords indicating issues in title/content
ISSUE_PATTERNS=${ISSUE_PATTERNS:-"error|not found|forbidden|access denied|bad gateway|service unavailable|502|503|504|timeout|captcha|verification"}

run_check() {
  local mail_to="$1"
  if ! command -v "$CURLLM_BIN" >/dev/null 2>&1; then
    echo "curllm not found in PATH" >&2; return 2
  fi
  if ! command -v "$JQ_BIN" >/dev/null 2>&1; then
    echo "jq not found in PATH" >&2; return 2
  fi
  if [ ! -f "$CSV_FILE" ]; then
    echo "Missing $CSV_FILE" >&2; return 2
  fi
  local attachments=()
  local body_lines=()
  local ts
  ts=$(date -Is)
  while IFS= read -r url; do
    url="${url%%#*}"  # strip comments
    url="${url//[$'\t\r\n ']*/}" # trim spaces (bash-safe)
    if [ -z "$url" ]; then continue; fi
    echo "["$(date -Is)"] Checking $url" | tee -a "$LOG_FILE"
    # Ask for screenshot, rely on fast-paths in curllm
    # Build extra args array safely
    IFS=' ' read -r -a _EXTRA <<< "$CURLLM_ARGS"
    set +e
    out=$($CURLLM_BIN "${_EXTRA[@]}" "$url" -d "screenshot" 2>/dev/null)
    rc=$?
    set -e
    if [ $rc -ne 0 ] || [ -z "$out" ]; then
      body_lines+=("$url: curllm failed (rc=$rc)")
      continue
    fi
    # Parse JSON
    local ok title shot
    ok=$(printf '%s' "$out" | $JQ_BIN -r '(.success // true)')
    title=$(printf '%s' "$out" | $JQ_BIN -r '(.result.title // .result // .page.title // .data.title // "")' 2>/dev/null || echo "")
    shot=$(printf '%s' "$out" | $JQ_BIN -r '(.screenshots // []) | last // empty' 2>/dev/null || true)
    # Heuristic detection
    local bad=0
    if [ "$ok" != "true" ]; then bad=1; fi
    if [ -z "$title" ]; then bad=1; fi
    if printf '%s' "$title" | grep -Eiq "$ISSUE_PATTERNS"; then bad=1; fi
    if [ $bad -eq 1 ]; then
      body_lines+=("$url: issue detected (title='$title')")
      if [ -n "$shot" ] && [ -f "$shot" ]; then
        attachments+=("$shot")
      fi
    fi
  done < "$CSV_FILE"

  if [ ${#body_lines[@]} -gt 0 ]; then
    local subject="curllm monitor: issues detected ($ts)"
    local body
    body=$(printf '%s\n' "Detected issues:" "" "${body_lines[@]}")
    if [ -n "$mail_to" ]; then
      # Send email
      if command -v python3 >/dev/null 2>&1; then
        python3 "$PY_SEND" --to "$mail_to" --subject "$subject" --body "$body" ${attachments[@]/#/--attach }
      else
        echo "Python not available to send email. Report:" >&2
        printf '%s\n' "$subject" "$body" >&2
      fi
    else
      echo "MAIL_TO not set; printing report instead:" >&2
      printf '%s\n' "$subject" "$body" >&2
    fi
  else
    echo "No issues detected at $ts" | tee -a "$LOG_FILE"
  fi
}

install_cron() {
  local mail_to="$1"
  if [ -z "$mail_to" ]; then
    echo "MAIL_TO is required (set in $ENV_FILE or pass --mail)" >&2
    exit 2
  fi
  local cron_expr
  cron_expr="${CRON_EXPR:-0 */3 * * *}"
  local cmd="$REPO_DIR/monitoring/website_monitor.sh run --mail '$mail_to'"
  # Filter existing crontab
  local tmp
  tmp=$(mktemp)
  crontab -l 2>/dev/null | grep -v "$TAG" > "$tmp" || true
  echo "$cron_expr $cmd $TAG" >> "$tmp"
  crontab "$tmp"
  rm -f "$tmp"
  echo "Installed cron job: $cron_expr"
}

remove_cron() {
  local tmp
  tmp=$(mktemp)
  crontab -l 2>/dev/null | grep -v "$TAG" > "$tmp" || true
  crontab "$tmp" || true
  rm -f "$tmp"
  echo "Removed cron job (if existed)"
}

usage() {
  cat <<EOF
curllm website monitor

Usage:
  website_monitor.sh run --mail you@example.com
  website_monitor.sh install --mail you@example.com
  website_monitor.sh remove

Env (optional):
  MAIL_TO, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_SSL, MAIL_FROM
  CURLLM_BIN (default: curllm), JQ_BIN (default: jq)
  ISSUE_PATTERNS (regex, default: $ISSUE_PATTERNS)
  Config file auto-loaded if present: $ENV_FILE
EOF
}

action=${1:-}
shift || true
MAIL_ARG="${MAIL_TO_DEFAULT}"
while [ $# -gt 0 ]; do
  case "$1" in
    --mail) MAIL_ARG="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) break;;
  esac
done

case "$action" in
  run) run_check "$MAIL_ARG";;
  install) install_cron "$MAIL_ARG";;
  remove) remove_cron;;
  *) usage; exit 1;;
esac
