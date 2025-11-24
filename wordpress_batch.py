#!/usr/bin/env python3
import os
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Optional

from curllm_core.executor import CurllmExecutor


async def batch_create_posts(
    articles_dir: Path,
    wordpress_config: Dict,
    proxy_config: Optional[Dict] = None,
):
    executor = CurllmExecutor()
    session_id = f"wp-batch-{wordpress_config['url'].replace('https://', '').replace('http://','').replace('/', '-')}"

    md_files = list(articles_dir.glob("*.md"))
    print(f"Found {len(md_files)} articles to publish")

    results = []
    for idx, md_file in enumerate(md_files, 1):
        print(f"\n[{idx}/{len(md_files)}] Processing: {md_file.name}")
        content = md_file.read_text(encoding="utf-8")

        lines = content.split("\n")
        title = lines[0].replace("#", "").strip() if lines else md_file.stem

        metadata: Dict[str, str] = {}
        if content.startswith("---"):
            try:
                fm_end = content.index("---", 3)
                fm = content[3:fm_end]
                for line in fm.split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        metadata[key.strip()] = val.strip()
                content = content[fm_end + 3 :].strip()
            except Exception:
                pass

        cfg = dict(wordpress_config)
        cfg.update(
            {
                "action": "create_post",
                "title": metadata.get("title", title),
                "content": content,
                "status": metadata.get("status", "draft"),
                "categories": [s.strip() for s in metadata.get("categories", "").split(",") if s.strip()] or None,
                "tags": [s.strip() for s in metadata.get("tags", "").split(",") if s.strip()] or None,
            }
        )

        try:
            result = await executor.execute_workflow(
                instruction="Create WordPress post",
                url=cfg["url"],
                wordpress_config=cfg,
                proxy=proxy_config,
                session_id=session_id,
            )
            results.append(
                {
                    "file": md_file.name,
                    "title": cfg["title"],
                    "success": result.get("success", False),
                    "url": (result.get("result") or {}).get("post_url"),
                }
            )
        except Exception as e:
            print(f"Error processing {md_file.name}: {e}")
            results.append({"file": md_file.name, "title": title, "success": False, "error": str(e)})

        with open(articles_dir / "publish_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        await asyncio.sleep(2)

    print("\n=== Summary ===")
    print(f"Total: {len(results)}")
    print(f"Success: {sum(1 for r in results if r.get('success'))}")
    print(f"Failed: {sum(1 for r in results if not r.get('success'))}")
    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python wordpress_batch.py <articles_dir>")
        raise SystemExit(1)

    wp_config = {
        "url": os.getenv("WP_URL", "https://example.wordpress.com"),
        "username": os.getenv("WP_USER", "admin"),
        "password": os.getenv("WP_PASS", ""),
    }

    proxy_cfg = None
    if os.getenv("PROXY_URL"):
        proxy_cfg = {"server": os.getenv("PROXY_URL")}

    asyncio.run(batch_create_posts(Path(sys.argv[1]), wp_config, proxy_cfg))
