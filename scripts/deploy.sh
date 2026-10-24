#!/usr/bin/env bash
# Runs ON THE AZURE VM (Jenkins copies it over and starts it with ssh).
#
# Usage: deploy.sh <build-number> <path-to-package.tar.gz>
#
# Steps: unpack -> venv + pip install -> switch "current" symlink -> restart
#        -> health check -> (auto-rollback if unhealthy) -> keep last 5 releases
set -euo pipefail

BUILD="${1:?usage: deploy.sh <build-number> <package.tar.gz>}"
PACKAGE="${2:?usage: deploy.sh <build-number> <package.tar.gz>}"

BASE=/opt/depthub
RELEASES="$BASE/releases"
CURRENT="$BASE/current"
HISTORY="$BASE/deploy_history.jsonl"   # outside the release folders, so it survives every deploy
SERVICE=depthub
HEALTH_URL="http://127.0.0.1:8000/health"
HEALTH_TRIES=10
HEALTH_WAIT=3
KEEP=5

RELEASE="$RELEASES/$BUILD"
PREVIOUS=""

log() { echo "[deploy] $*"; }

# Point /opt/depthub/current at a release folder. ln+mv makes the switch atomic.
switch_to() {
  ln -sfn "$1" "$CURRENT.new"
  mv -T "$CURRENT.new" "$CURRENT"
}

# Add one line to the deploy history. $1 = status (success / rolled-back)
record_history() {
  python3 - "$RELEASE/version.json" "$HISTORY" "$1" <<'PY'
import json, sys
from datetime import datetime, timezone
version_file, history_file, status = sys.argv[1:4]
try:
    with open(version_file) as f:
        info = json.load(f)
except (OSError, ValueError):
    info = {}
entry = {
    "build": info.get("build", "?"),
    "commit": info.get("commit", "unknown"),
    "commit_short": info.get("commit_short", "unknown"),
    "message": info.get("message", "unknown"),
    "author": info.get("author", "unknown"),
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "status": status,
}
with open(history_file, "a") as f:
    f.write(json.dumps(entry) + "\n")
PY
}

healthy() {
  for i in $(seq 1 "$HEALTH_TRIES"); do
    if curl -fsS --max-time 5 "$HEALTH_URL" > /dev/null 2>&1; then
      return 0
    fi
    log "health check $i/$HEALTH_TRIES failed, retrying in ${HEALTH_WAIT}s..."
    sleep "$HEALTH_WAIT"
  done
  return 1
}

# ---- 1. unpack ----
log "Deploying build $BUILD"
if [ -L "$CURRENT" ]; then
  PREVIOUS="$(readlink -f "$CURRENT")"
  log "Current release is $PREVIOUS"
fi

rm -rf "$RELEASE"
mkdir -p "$RELEASE"
tar -xzf "$PACKAGE" -C "$RELEASE"

# ---- 2. virtualenv + dependencies (nothing is live yet, so a failure here is harmless) ----
if ! { python3 -m venv "$RELEASE/venv" && "$RELEASE/venv/bin/pip" install --quiet -r "$RELEASE/requirements.txt"; }; then
  log "ERROR: could not install dependencies. The running site was not touched."
  rm -rf "$RELEASE"
  exit 1
fi

# ---- 3. switch + restart ----
switch_to "$RELEASE"
sudo systemctl restart "$SERVICE"

# ---- 4. health check, with auto-rollback ----
if healthy; then
  record_history success
  log "Build $BUILD is healthy and live."
else
  log "ERROR: build $BUILD failed its health check."
  record_history rolled-back
  if [ -n "$PREVIOUS" ] && [ -d "$PREVIOUS" ]; then
    log "Rolling back to $PREVIOUS"
    switch_to "$PREVIOUS"
    sudo systemctl restart "$SERVICE"
    if healthy; then
      log "Rollback complete: the previous version is serving traffic again."
    else
      log "WARNING: previous release is not healthy either, check 'journalctl -u $SERVICE'."
    fi
  else
    log "No previous release to roll back to (this was the first deploy)."
  fi
  rm -rf "$RELEASE"
  rm -f "$PACKAGE"
  exit 1   # tells Jenkins the build failed
fi

# ---- 5. housekeeping: keep only the newest $KEEP releases ----
ls -1 "$RELEASES" | sort -rn | tail -n +"$((KEEP + 1))" | while read -r old; do
  log "Removing old release $old"
  rm -rf "${RELEASES:?}/$old"
done
rm -f "$PACKAGE"
log "Done."
