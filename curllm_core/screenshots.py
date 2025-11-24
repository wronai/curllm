from pathlib import Path
from datetime import datetime
from typing import Optional

from .config import config


async def take_screenshot(page, step: int, target_dir: Optional[Path] = None) -> str:
    tdir = Path(target_dir) if target_dir else config.screenshot_dir
    tdir.mkdir(parents=True, exist_ok=True)
    filename = tdir / f"step_{step}_{datetime.now().timestamp()}.png"
    await page.screenshot(path=str(filename))
    return str(filename)
