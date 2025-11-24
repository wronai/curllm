# curllm Examples

**[📚 Documentation Index](INDEX.md)** | **[⬅️ Back to Main README](../README.md)**

---

This document contains curated, end-to-end examples for common automation tasks with curllm. You can also generate runnable shell scripts for these examples into the `examples/` directory.

- Generate scripts: `make examples` (or `bash tools/generate_examples.sh`)
- Scripts will be created as `examples/curllm-*.sh`
- Ensure services are running: `curllm --start-services && curllm --status`

## Top 10 quick examples

1. Extract all links

   ```bash
   curllm "https://example.com" -d "extract all links"
   ```

2. Extract emails and phones

   ```bash
   curllm "https://example.com/contact" -d "extract all emails and phone numbers"
   ```

3. Take a screenshot

   ```bash
   curllm "https://example.com" -d "screenshot"
   ```

4. Products under 150 zł (public proxy rotation)

   ```bash
   export CURLLM_PUBLIC_PROXY_LIST="https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"
   curllm "https://ceneo.pl" -d "Find all products under 150zł and extract names, prices and urls" \
     --stealth --proxy rotate:public --csv -o products.csv
   ```

5. Products with registry rotation (after registering proxies)

   ```bash
   # register proxies via curlx or API, then:
   curllm "https://ceneo.pl" -d "Find all products under 150zł and extract names, prices and urls" \
     --stealth --proxy rotate:registry --html -o products.html
   ```

6. BQL: Hacker News links (CSS selectors)

   ```bash
   curllm --bql -d 'query { page(url: "https://news.ycombinator.com") { title links: select(css: "a.storylink, a.titlelink") { text url: attr(name: "href") } }}'
   ```

7. Visual fill contact form (stealth)

   ```bash
   curllm --visual --stealth "https://www.prototypowanie.pl/kontakt/" \
     -d "Fill contact form: name=John Doe, email=john@example.com, message=Hello"
   ```

8. Use a session (persist cookies between runs)

   ```bash
   curllm --session my-site "https://example.com" -d "screenshot"
   # later: same session reused automatically
   ```

9. Export results to XLS (Excel-compatible)

   ```bash
   curllm "https://example.com" -d "extract all links" --xls -o links.xls
   ```

10. WordPress: create a post using session

    ```bash
    curllm --session wp-s1 -d '{"wordpress_config":{"url":"https://example.wordpress.com","action":"create_post","title":"Hello","content":"Post body","status":"draft"}}'
    ```

## Table of Contents
- Extract links from a page
- BQL: Hacker News links
- Fill contact form (visual + stealth)
- Login and download
- Visual scrape products
- CAPTCHA demo
- BQL JSON API
- Stealth scraping news titles
- Override model per-command
- POST with custom headers

---

## LLM: Hacker News links

Command:

```bash
curllm "https://news.ycombinator.com" -d "Extract the page title and the first 30 news links. Use anchors matching CSS selectors 'a.titlelink' or 'a.storylink'. Return JSON shaped exactly as: {\"page\": {\"title\": string, \"links\": [{\"text\": string, \"url\": string}] } }" -v
```

Script:

- `examples/curllm-llm-hn-links.sh`

Notes:

- You can add `--html -o hn.html` to export links to an HTML table.
- For consistency with BQL example, the shape is `{page: {title, links: [{text, url}]}}`.

---

## Extract links from a page

Command:

```bash
curllm "https://example.com" -d "extract all links" -v
```

Script:

- `examples/curllm-extract-links.sh`

---

## BQL: Hacker News links

Command:

```bash
curllm --bql -d 'query {
  page(url: "https://news.ycombinator.com") {
    title
    links: select(css: "a.storylink, a.titlelink") { text url: attr(name: "href") }
  }
}' -v
```

Script:

- `examples/curllm-bql-hn-links.sh`

---

## Fill contact form (visual + stealth)

Command:

```bash
curllm --stealth --visual \
  -d "Fill contact form: name=John Doe, email=john@example.com, message=Hello" \
  https://www.prototypowanie.pl/kontakt/ -v
```

Script:

- `examples/curllm-fill-contact-form.sh`

---

## Login and download

Command:

```bash
curllm -X POST --visual --stealth \
  -d '{"instruction": "Login and download invoice", "credentials": {"user": "john@example.com", "pass": "secret"}}' \
  https://app.example.com -v
```

Script:

- `examples/curllm-login-download.sh`

---

## Visual scrape products

Command:

```bash
curllm --visual "https://shop.com" -d "extract top 10 products with prices" -v
```

Script:

- `examples/curllm-visual-scrape-products.sh`

---

## CAPTCHA demo

Command:

```bash
curllm --visual --captcha "https://example.com/captcha" -d "solve captcha and submit form" -v
```

Script:

- `examples/curllm-captcha-demo.sh`

Notes:

- For 2captcha, set `CAPTCHA_API_KEY` in `.env`. Otherwise local OCR will be attempted.

---

## BQL JSON API

Command:

```bash
curllm --bql -d 'query { page(url: "https://example.com") { title links { text url } }}' -v
```

Script:

- `examples/curllm-bql-json-api.sh`

---

## Stealth scraping news titles

Command:

```bash
curllm --stealth "https://news.ycombinator.com" -d "extract first 30 titles" -v
```

Script:

- `examples/curllm-stealth-news.sh`

---

## Override model per-command

Command:

```bash
curllm --model qwen2.5:3b "https://example.com" -d "extract emails" -v
```

Script:

- `examples/curllm-custom-model.sh`

---

## POST with custom headers

Command:

```bash
curllm -X POST -H 'Authorization: Bearer TOKEN' -H 'X-Trace: 1' \
  -d '{"instruction": "submit form with authenticated session"}' \
  https://httpbin.org/post -v
```

Script:

- `examples/curllm-post-with-headers.sh`

---

## Export results (CSV/HTML/XML/XLS)

Use the CLI export flags to transform JSON results into tabular formats.

Requires: `jq`.

```bash
# CSV
curllm "https://ceneo.pl" -d "Find all products under 150zł and extract names, prices and urls" \
  --csv -o products.csv

# HTML table
curllm "https://example.com" -d "extract all links" --html -o links.html

# XML
curllm "https://example.com" -d "extract all emails" --xml -o emails.xml

# Excel-compatible (.xls generated as HTML table)
curllm "https://ceneo.pl" -d "Find all products under 150zł and extract names, prices and urls" \
  --xls -o products.xls
```

If `-o` is not provided, files are saved as `curllm_export_YYYYMMDD-HHMMSS.(csv|html|xml|xls)`.

## Tips

- Always start services first: `curllm --start-services` and verify with `curllm --status`.
- If ports change, `.env` is auto-updated. Use `-v` to see diagnostics.
- Visual tasks may use more GPU. Consider smaller models or reduced steps for testing.
