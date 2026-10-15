"""Initialize credentials for this local deployment once."""

import json
import os
from pathlib import Path
import secrets
import sys

RUNTIME_ROOT = Path(__file__).resolve().parent
APP_ROOT = RUNTIME_ROOT.parent / "apps" / "xianyu-auto-reply-fix"
CREDENTIALS_PATH = RUNTIME_ROOT / "admin-credentials.json"

os.chdir(APP_ROOT)
sys.path.insert(0, str(APP_ROOT))
os.environ["SQL_LOG_ENABLED"] = "false"
os.environ["DB_PATH"] = str(APP_ROOT / "data" / "xianyu_data.db")

from db_manager import db_manager

if not CREDENTIALS_PATH.exists():
    credentials = {
        "url": "http://127.0.0.1:18790",
        "username": "admin",
        "password": secrets.token_urlsafe(21),
    }
    if not db_manager.update_user_password("admin", credentials["password"]):
        raise RuntimeError("Could not initialize the local admin password")
    descriptor = os.open(CREDENTIALS_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        json.dump(credentials, handle, ensure_ascii=False, indent=2)
    db_manager.set_system_setting("show_default_login_info", "false")
    db_manager.set_system_setting("registration_enabled", "false")
    print("Initialized the local admin account; credentials saved with mode 0600.")
else:
    print("Existing local credentials preserved.")
