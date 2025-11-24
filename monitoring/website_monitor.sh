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
DRY_RUN_FLAG="${DRY_RUN:-}"
HTML_REPORT_FLAG="${HTML_REPORT:-}"
HTML_REPORT_PATH="${HTML_REPORT_PATH:-}"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"

# Keywords indicating issues in title/content
ISSUE_PATTERNS=${ISSUE_PATTERNS:-"error|not found|forbidden|access denied|bad gateway|service unavailable|502|503|504|timeout|captcha|verification"}

matches_issue() {
  # Case-insensitive pattern check with safe fallback when grep regex fails
  local text="$1"
  local pat="$ISSUE_PATTERNS"
  # Try grep -E first, suppressing stderr to avoid noisy class errors
  if printf '%s' "$text" | grep -Eiq "$pat" 2>/dev/null; then
    return 0
  fi
  # Fallback: simple token contains check (split by |)
  local tl="${text,,}"
  IFS='|' read -r -a toks <<< "$pat"
  for tok in "${toks[@]}"; do
    # trim spaces
    tok="$(printf '%s' "$tok" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    [ -z "$tok" ] && continue
    local tkl="${tok,,}"
    case "$tl" in
      *"$tkl"*) return 0;;
    esac
  done
  return 1
}

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
  local html_report=""
  while IFS= read -r url; do
    url="${url%%#*}"  # strip comments
    # trim leading/trailing whitespace (portable)
    url="$(printf '%s' "$url" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    if [ -z "$url" ]; then continue; fi
    # Skip CSV header like 'Domain'
    case "$(printf '%s' "$url" | tr '[:upper:]' '[:lower:]')" in
      domain|domena) continue;;
    esac
    echo "["$(date -Is)"] Checking $url" | tee -a "$LOG_FILE"
    # Build candidate URLs if bare domain was provided
    candidates=()
    if printf '%s' "$url" | grep -Eq '^https?://'; then
      candidates=("$url")
    else
      # IDN (non-ascii) punycode conversion for host part if python3 available
      host_part="${url%%/*}"; rest_part="${url#${host_part}}"
      if command -v python3 >/dev/null 2>&1; then
        idn_host=$(python3 - "$host_part" <<'PY'
import sys
h=sys.argv[1]
try:
    print(h.encode('idna').decode())
except Exception:
    print(h)
PY
)
        [ -n "$idn_host" ] && host_part="$idn_host"
      fi
      url_no_scheme="${host_part}${rest_part}"
      candidates=(
        "https://$url_no_scheme"
        "https://www.$url_no_scheme"
        "http://$url_no_scheme"
        "http://www.$url_no_scheme"
      )
    fi
    IFS=' ' read -r -a _EXTRA <<< "$CURLLM_ARGS"
    use_url=""
    out=""
    for cand in "${candidates[@]}"; do
      set +e
      out=$($CURLLM_BIN "${_EXTRA[@]}" "$cand" -d "screenshot" 2>/dev/null)
      rc=$?
      set -e
      if [ $rc -eq 0 ] && [ -n "$out" ]; then
        use_url="$cand"
        break
      fi
    done
    if [ -z "$use_url" ]; then
      body_lines+=("$url: curllm failed for all candidates")
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
    if matches_issue "$title"; then bad=1; fi
    if [ $bad -eq 1 ]; then
      body_lines+=("$use_url: issue detected (title='$title')")
      if [ -n "$shot" ] && [ -f "$shot" ]; then
        attachments+=("$shot")
      fi
    fi
  done < "$CSV_FILE"

  if [ ${#body_lines[@]} -gt 0 ]; then
    local subject="curllm monitor: issues detected ($ts)"
    local body
    body=$(printf '%s\n' "Detected issues:" "" "${body_lines[@]}")
    # Optional HTML report
    if [ -n "$HTML_REPORT_FLAG" ]; then
      local rp
      rp="${HTML_REPORT_PATH:-/tmp/curllm_monitor_report-${ts//:/-}.html}"
      {
        printf '<!doctype html>\n<html><head><meta charset="utf-8"><title>%s</title>' "$subject"
        printf '<style>body{font-family:sans-serif} table{border-collapse:collapse} td,th{border:1px solid #ccc;padding:6px}</style></head><body>'
        printf '<h2>%s</h2><p>%s</p>' "curllm Website Monitor" "$ts"
        printf '<table><thead><tr><th>URL</th><th>Title</th><th>Screenshot</th></tr></thead><tbody>'
        for a in "${attachments[@]}"; do :; done # keep shellcheck quiet if empty
        # rebuild rows from body_lines and available screenshots
        while IFS= read -r line; do
          url_part="${line%%:*}"
          shot=""; title="";
          # try to find matching screenshot among attachments (best-effort)
          for f in "${attachments[@]}"; do
            case "$f" in *$(echo "$url_part" | sed 's#https\?://##;s#/.*$##')*) shot="$f";; esac
          done
          title=$(printf '%s' "$line" | sed -n "s/.*title='\(.*\)'.*/\1/p")
          printf '<tr><td>%s</td><td>%s</td><td>%s</td></tr>' \
            "$(printf '%s' "$url_part" | sed 's/&/&amp;/g;s/</&lt;/g')" \
            "$(printf '%s' "$title" | sed 's/&/&amp;/g;s/</&lt;/g')" \
            "$( [ -n "$shot" ] && printf '<code>%s</code>' "$shot" || printf '-' )"
        done <<EOF
$(printf '%s\n' "${body_lines[@]}")
EOF
        printf '</tbody></table>'
        printf '<p>Note: image files are attached to the email. Local paths are shown above for reference.</p>'
        printf '</body></html>'
      } > "$rp"
      html_report="$rp"
      attachments+=("$rp")
    fi

    # Optional Slack notification
    if [ -n "$SLACK_WEBHOOK_URL" ] && command -v curl >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
      printf '%s\n\n%s' "$subject" "$body" | jq -Rs '{text: .}' > /tmp/curllm_slack_payload.json 2>/dev/null || true
      curl -s -X POST -H 'Content-Type: application/json' \
        --data @/tmp/curllm_slack_payload.json "$SLACK_WEBHOOK_URL" >/dev/null 2>&1 || true
    fi

    # Optional Telegram notification
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ] && command -v curl >/dev/null 2>&1; then
      curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
        --data-urlencode "text=${subject}

${body}" >/dev/null 2>&1 || true
    fi
    if [ -n "$DRY_RUN_FLAG" ]; then
      echo "[DRY-RUN] Would send email to: ${mail_to:-<unset>}" >&2
      printf '%s\n' "$subject" "$body" >&2
      if [ ${#attachments[@]} -gt 0 ]; then
        printf '[DRY-RUN] Attachments:%s\n' "" >&2
        for a in "${attachments[@]}"; do printf ' - %s\n' "$a" >&2; done
      fi
    elif [ -n "$mail_to" ]; then
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
  # Ensure cron environment has sensible defaults
  if ! grep -q '^SHELL=' "$tmp"; then echo 'SHELL=/bin/bash' >> "$tmp"; fi
  if ! grep -q '^PATH=' "$tmp"; then echo 'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' >> "$tmp"; fi
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
