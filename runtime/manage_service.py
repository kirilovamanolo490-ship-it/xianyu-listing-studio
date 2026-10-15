"""Manage the local Xianyu pilot as a macOS user LaunchAgent."""

import argparse
import os
from pathlib import Path
import plistlib
import subprocess

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "xianyu-auto-reply-fix"
LABEL = "local.codex.xianyu-gudong"
DOMAIN = f"gui/{os.getuid()}"
PLIST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
PYTHON = APP / ".venv" / "bin" / "python"

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("command", choices=["install", "start", "stop", "restart", "status"])
args = parser.parse_args()

if args.command == "install":
    config = {
        "Label": LABEL,
        "ProgramArguments": [str(PYTHON), "-u", str(ROOT / "runtime" / "start_gudong.py")],
        "WorkingDirectory": str(APP),
        "EnvironmentVariables": {
            "PATH": f"{Path.home()}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            "PYTHONUNBUFFERED": "1",
            "PLAYWRIGHT_SKIP_BROWSER_GC": "1",
            "NO_PROXY": "127.0.0.1,localhost",
        },
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 15,
        "ExitTimeOut": 10,
        "StandardOutPath": str(ROOT / "runtime" / "service.stdout.log"),
        "StandardErrorPath": str(ROOT / "runtime" / "service.stderr.log"),
    }
    if PLIST.exists():
        previous = plistlib.loads(PLIST.read_bytes())
        if previous.get("ProgramArguments") != config["ProgramArguments"]:
            raise SystemExit("An unrelated LaunchAgent uses this label; no file was changed.")
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_bytes(plistlib.dumps(config))
    PLIST.chmod(0o600)
    subprocess.run(["launchctl", "bootstrap", DOMAIN, str(PLIST)], check=True)
    print(f"Installed {LABEL}; http://127.0.0.1:18790")
elif args.command == "start":
    subprocess.run(["launchctl", "bootstrap", DOMAIN, str(PLIST)], check=True)
elif args.command == "stop":
    subprocess.run(["launchctl", "bootout", f"{DOMAIN}/{LABEL}"], check=True)
elif args.command == "restart":
    subprocess.run(["launchctl", "kickstart", "-k", f"{DOMAIN}/{LABEL}"], check=True)
elif args.command == "status":
    subprocess.run(["launchctl", "print", f"{DOMAIN}/{LABEL}"], check=True)
