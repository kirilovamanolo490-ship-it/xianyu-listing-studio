"""Start the upstream application with local-only runtime settings."""

import os
from pathlib import Path
import runpy
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "apps" / "xianyu-auto-reply-fix"

os.chdir(APP_ROOT)
sys.path.insert(0, str(APP_ROOT))
os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("SQL_LOG_ENABLED", "false")
os.environ.setdefault("TZ", "Asia/Shanghai")
os.environ.setdefault("DB_PATH", str(APP_ROOT / "data" / "xianyu_data.db"))

from browser_runtime import configure_browser_runtime

configure_browser_runtime()

# Upstream Start.py gives YAML settings priority over API_HOST/API_PORT.
# Override the in-memory settings so the checked-out upstream files stay intact.
from config import AUTO_REPLY

AUTO_REPLY.setdefault("api", {}).update(host="127.0.0.1", port=18790)
runpy.run_path(str(APP_ROOT / "Start.py"), run_name="__main__")
