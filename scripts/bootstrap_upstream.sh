#!/usr/bin/env bash
# Fetch a fixed upstream revision; never overwrite an existing checkout.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT/apps/xianyu-auto-reply-fix"
REMOTE='https://github.com/GuDong2003/xianyu-auto-reply-fix.git'
REVISION='e8fe7ba4239614fe64d194cf3bed8a3aa16d5ab6'
PATCH="$ROOT/patches/manual-verification-status-fix.patch"
if [[ ! -e "$APP" ]]; then
  mkdir -p "$ROOT/apps"
  git clone --no-checkout "$REMOTE" "$APP"
  git -C "$APP" checkout --detach "$REVISION"
fi
if [[ ! -d "$APP/.git" ]]; then
  echo 'Existing app directory is not the expected Git checkout; nothing changed.' >&2
  exit 1
fi
if [[ "$(git -C "$APP" remote get-url origin)" != "$REMOTE" ]] || \
   [[ "$(git -C "$APP" rev-parse HEAD)" != "$REVISION" ]]; then
  echo 'Existing upstream origin or revision differs; refusing to reset it.' >&2
  exit 1
fi
if git -C "$APP" apply --reverse --check "$PATCH" 2>/dev/null; then
  echo 'The verification-state patch is already applied.'
else
  if [[ -n "$(git -C "$APP" status --porcelain --untracked-files=no)" ]]; then
    echo 'Existing tracked modifications detected; refusing to overwrite.' >&2
    exit 1
  fi
  git -C "$APP" apply --check "$PATCH"
  git -C "$APP" apply "$PATCH"
fi
echo "Prepared upstream $REVISION. Continue with docs/getting-started.md."
