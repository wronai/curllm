# Result storage and diffing (new | changed | delta)

This document describes how to persist extraction results between runs and how to return only the differences (e.g. only new items) in subsequent runs.

## Quick start (CLI)

Save results, attach history to a stable key, and return only new items since the last run:

```bash
curllm --visual -H "Accept-Language: pl-PL,pl;q=0.9" "https://oferteo.pl/zlecenia-it" -d '{
  "instruction": "Save all offers and extract titles and urls",
  "params": {
    "store_results": true,
    "include_prev_results": true,
    "result_key": "oferteo-it-rfp",
    "diff_mode": "new",
    "diff_fields": ["href"],
    "keep_history": 50,
    "refine_instruction": true
  }
}'
```

- `result_key` is a stable series identifier. Use the same value on every periodic run (e.g. hourly).
- `diff_mode`: one of `none | new | changed | delta | all`.
- `diff_fields`: which fields identify an item; for links, `href` is usually enough.
- `store_results`: enable snapshotting to the workspace.
- `include_prev_results`: optional; allows the planner to consider previous items during reasoning.

Snapshots are stored under: `${CURLLM_WORKSPACE:-./workspace}/results/<result_key>/`.

## Modes

- `new`: return only items that did not exist in the previous snapshot.
- `changed`: return only items that exist with the same key but with changed content (`[{ previous, current }]`).
- `delta`: return `{ new, changed, removed }` groups.
- `all`: store a snapshot and compute metrics, but return the full current result.
- `none`: disable diffing; no snapshots unless `store_results=true` is set.

## Environment defaults

You can set global defaults in `.env`:

```ini
CURLLM_STORE_RESULTS=false
CURLLM_RESULT_KEY=
CURLLM_DIFF_MODE=none
CURLLM_DIFF_FIELDS=href,title,url
CURLLM_KEEP_HISTORY=10
CURLLM_INCLUDE_PREV_RESULTS=false
CURLLM_REFINE_INSTRUCTION=false
```

All of these can be overridden per-run via `params` in the `-d` JSON payload.

## Notes

- Diffing is performed on the primary array in the result (e.g. `links`, `articles`, or `products`).
- When `diff_mode` is not `none`, a `diff` summary with counts is included at the top level of the API response.
- When `include_prev_results=true`, the planner receives a `previous_results` object in the page context: `{ key, items, fields }`.
