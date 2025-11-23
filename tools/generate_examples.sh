#!/usr/bin/env bash
set -euo pipefail

# Generate example scripts and per-example README docs for curllm
# Requirements: jq

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
EX_DIR="$ROOT_DIR/examples"
mkdir -p "$EX_DIR"

write_script() {
  local path="$1"; shift
  local cmd="$*"
  cat > "$path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Ensure services are running first:
#   curllm --start-services
#   curllm --status

EOF
  echo "$cmd" >> "$path"
  chmod +x "$path"
}

write_readme() {
  local dir="$1"; shift
  local title="$1"; shift
  local desc="$1"; shift
  local cmd="$*"
  local slug
  slug=$(basename "$dir")
  cat > "$dir/README.md" <<EOF
# $title

$desc

## Command

```bash
$cmd
```

## How to run

```bash
curllm --start-services
curllm --status
cd examples/$slug
./run.sh
```
EOF
}

EXAMPLES_JSON=$(cat <<'JSON'
[
  {
    "slug": "extract-links",
    "title": "Extract Links from a Page",
    "description": "Extract all hyperlinks from a given page.",
    "command": "curllm \"https://example.com\" -d \"extract all links\" -v"
  },
  {
    "slug": "bql-hn-links",
    "title": "BQL: Hacker News Links",
    "description": "Use BQL to collect article titles and URLs from Hacker News.",
    "command": "curllm --bql -d 'query {\n  page(url: \"https://news.ycombinator.com\") {\n    title\n    links: select(css: \"a.storylink, a.titlelink\") { text url: attr(name: \"href\") }\n  }\n}' -v"
  },
  {
    "slug": "fill-contact-form",
    "title": "Fill Contact Form (Visual + Stealth)",
    "description": "Open the contact page and fill form fields with sample data.",
    "command": "curllm --stealth --visual -d \"Fill contact form: name=John Doe, email=john@example.com, message=Hello\" https://www.prototypowanie.pl/kontakt/ -v"
  },
  {
    "slug": "login-download",
    "title": "Login and Download",
    "description": "Login to an app and download an invoice using provided credentials.",
    "command": "curllm -X POST --visual --stealth -d '{\"instruction\": \"Login and download invoice\", \"credentials\": {\"user\": \"john@example.com\", \"pass\": \"secret\"}}' https://app.example.com -v"
  },
  {
    "slug": "visual-scrape-products",
    "title": "Visual Scrape Products",
    "description": "Find top 10 products with prices using visual analysis.",
    "command": "curllm --visual \"https://shop.com\" -d \"extract top 10 products with prices\" -v"
  },
  {
    "slug": "captcha-demo",
    "title": "CAPTCHA Demo",
    "description": "Solve a CAPTCHA and submit the form (requires CAPTCHA_API_KEY for service).",
    "command": "curllm --visual --captcha \"https://example.com/captcha\" -d \"solve captcha and submit form\" -v"
  },
  {
    "slug": "bql-json-api",
    "title": "BQL JSON API",
    "description": "Use BQL to extract JSON-like structured data from a page.",
    "command": "curllm --bql -d 'query { page(url: \"https://example.com\") { title links { text url } }}' -v"
  },
  {
    "slug": "stealth-news",
    "title": "Stealth Scraping News Titles",
    "description": "Scrape first 30 titles with stealth mode enabled.",
    "command": "curllm --stealth \"https://news.ycombinator.com\" -d \"extract first 30 titles\" -v"
  },
  {
    "slug": "custom-model",
    "title": "Override Model per Command",
    "description": "Run a command with a smaller model for faster iteration.",
    "command": "curllm --model qwen2.5:3b \"https://example.com\" -d \"extract emails\" -v"
  },
  {
    "slug": "post-with-headers",
    "title": "POST with Custom Headers",
    "description": "Send a POST request with custom headers and instruction payload.",
    "command": "curllm -X POST -H 'Authorization: Bearer TOKEN' -H 'X-Trace: 1' -d '{\"instruction\": \"submit form with authenticated session\"}' https://httpbin.org/post -v"
  },
  {
    "slug": "only-email-phone",
    "title": "Only Email and Phone",
    "description": "Extract only emails and phone numbers (no other links).",
    "command": "curllm \"https://www.prototypowanie.pl/kontakt/\" -d \"extract only email and phone links\" -v"
  },
  {
    "slug": "domain-screenshot",
    "title": "Screenshot Saved in Domain Folder",
    "description": "Create a screenshot and save it under screenshots/<domain>.",
    "command": "curllm \"https://www.wikipedia.org\" -d \"Create screenshot in folder name of domain\" -v"
  },
  {
    "slug": "allegro-products-under-150",
    "title": "Products Under 150 (Visual + Locale)",
    "description": "Find products under 150 using visual mode with locale/timezone configured.",
    "command": "export CURLLM_HEADLESS=false\nexport CURLLM_LOCALE=pl-PL\nexport CURLLM_TIMEZONE=Europe/Warsaw\ncurllm --visual \"https://allegro.com\" -d \"Find all products under 150 and extract names, prices and urls\" -v"
  },
  {
    "slug": "stealth-detection-test",
    "title": "Stealth Detection Test",
    "description": "Visit a bot detection test page with stealth mode and take a screenshot.",
    "command": "curllm --stealth \"https://bot.sannysoft.com/\" -d \"Create screenshot of the results page\" -v"
  },
  {
    "slug": "use-proxy",
    "title": "Run via Proxy",
    "description": "Run curllm through an HTTP proxy (replace host:port).",
    "command": "CURLLM_PROXY=http://proxy:3128 curllm \"https://example.com\" -d \"extract title and first 10 links\" -v"
  },
  {
    "slug": "capture-run-log",
    "title": "Capture run_log Path",
    "description": "Capture and print run_log path from the JSON output (requires jq).",
    "command": "curllm \"https://www.wikipedia.org\" -d \"extract title\" | jq -r .run_log"
  },
  {
    "slug": "headless-off-visual",
    "title": "Headless Off with Visual Mode",
    "description": "Run in non-headless visual mode to debug actions and scrolling.",
    "command": "CURLLM_HEADLESS=false curllm --visual \"https://example.com\" -d \"scroll and extract top 5 links\" -v"
  }
]
JSON
)

echo "$EXAMPLES_JSON" | jq -c '.[]' | while read -r row; do
  slug=$(jq -r '.slug' <<<"$row")
  title=$(jq -r '.title' <<<"$row")
  desc=$(jq -r '.description' <<<"$row")
  cmd=$(jq -r '.command' <<<"$row")

  # Per-example folder with README and run.sh
  dir="$EX_DIR/$slug"
  mkdir -p "$dir"
  write_readme "$dir" "$title" "$desc" "$cmd"
  write_script "$dir/run.sh" "$cmd"

  # Top-level script for convenience
  top_script="$EX_DIR/curllm-${slug}.sh"
  write_script "$top_script" "$cmd"

  echo "Created: $dir/README.md"
  echo "Created: $dir/run.sh"
  echo "Created: $top_script"
done
