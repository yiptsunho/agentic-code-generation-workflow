#!/usr/bin/env bash
# Reset the frontend tree to match the current Git HEAD (tracked files only by default).
set -euo pipefail

usage() {
  echo "Usage: $0 [--clean-untracked] [--yes]" >&2
  echo "  Discards local changes under frontend/ to match HEAD (staged + unstaged)." >&2
  echo "  Always removes frontend/node_modules/ if present." >&2
  echo "  --clean-untracked  also remove untracked files and directories under frontend/" >&2
  echo "  --yes              skip confirmation for --clean-untracked" >&2
}

CLEAN_UNTRACKED=0
SKIP_CONFIRM=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --clean-untracked) CLEAN_UNTRACKED=1 ;;
    --yes) SKIP_CONFIRM=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
  shift
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: not inside a Git repository." >&2
  exit 1
fi

if [[ ! -d frontend ]]; then
  echo "Error: frontend/ not found at $ROOT/frontend" >&2
  exit 1
fi

echo "Restoring tracked files under frontend/ to HEAD..."
git restore --source=HEAD --staged --worktree frontend

REMOVED_NODE_MODULES=0
if [[ -d frontend/node_modules ]]; then
  echo "Removing frontend/node_modules/ ..."
  rm -rf frontend/node_modules
  REMOVED_NODE_MODULES=1
fi

if [[ "$CLEAN_UNTRACKED" -eq 1 ]]; then
  echo
  echo "Untracked paths under frontend/ (preview):"
  git clean -nd frontend
  echo
  if [[ "$SKIP_CONFIRM" -ne 1 ]]; then
    read -r -p "Remove these untracked files? [y/N] " reply
    if [[ ! "${reply:-}" =~ ^[Yy]$ ]]; then
      echo "Skipped untracked cleanup."
      exit 0
    fi
  fi
  git clean -fd frontend
  echo "Removed untracked files under frontend/."
fi

echo "Done."
