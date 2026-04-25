#!/usr/bin/env sh
set -eu

# Resolve project root from this script location
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "Running Rush Hour test suite..."
echo "Project root: $PROJECT_ROOT"
echo

# -vv: show each test clearly
# -ra: show extra summary for skipped/xfailed/etc.
python -m pytest tests -vv -ra
