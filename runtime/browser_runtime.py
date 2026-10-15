"""Resolve the browser already installed for this local Playwright version."""

import os
import sys
from pathlib import Path


def configure_browser_runtime():
    # Use the standard installed Playwright browser cache, not a private profile.
    if sys.platform == "darwin":
        cache = Path.home() / "Library" / "Caches" / "ms-playwright"
    elif sys.platform == "win32":
        cache = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "ms-playwright"
    else:
        cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ms-playwright"
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(cache))
    os.environ.setdefault("PLAYWRIGHT_SKIP_BROWSER_GC", "1")
    # A platform verification must be visible and available for human input.
    os.environ.setdefault("XY_ENABLE_AUTO_SLIDER", "0")
    os.environ.setdefault("XY_SLIDER_DRISSION_FALLBACK", "0")
    os.environ.setdefault("XY_MANUAL_SLIDER_TIMEOUT", "600")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        executable = Path(playwright.chromium.executable_path)
    if not executable.is_file():
        raise RuntimeError(f"The installed Playwright Chromium is missing: {executable}")
    os.environ.setdefault("XY_SLIDER_BROWSER_PATH", str(executable))
    return {
        "cache": os.environ["PLAYWRIGHT_BROWSERS_PATH"],
        "executable": os.environ["XY_SLIDER_BROWSER_PATH"],
    }
