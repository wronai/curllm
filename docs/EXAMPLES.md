# curllm Examples

This document contains curated, end-to-end examples for common automation tasks with curllm. You can also generate runnable shell scripts for these examples into the `examples/` directory.

- Generate scripts: `make examples` (or `bash tools/generate_examples.sh`)
- Scripts will be created as `examples/curllm-*.sh`
- Ensure services are running: `curllm --start-services && curllm --status`

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

## Tips

- Always start services first: `curllm --start-services` and verify with `curllm --status`.
- If ports change, `.env` is auto-updated. Use `-v` to see diagnostics.
- Visual tasks may use more GPU. Consider smaller models or reduced steps for testing.
