#!/bin/bash
# Build a digest on this machine, then commit and push it so GitHub Pages deploys it.
# Any arguments are passed to `digest build`, e.g. scripts/publish.sh --days 3
set -euo pipefail

# launchd starts jobs with a bare PATH; add where uv and claude usually live.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

cd "$(dirname "$0")/.."
echo "=== $(date '+%Y-%m-%d %H:%M:%S') digest run ==="

git pull --rebase --autostash --quiet
uv run digest build "$@"

git add data site
if git diff --cached --quiet; then
  echo "Nothing new to publish."
  exit 0
fi
git commit --quiet -m "Digest for $(date +%F)"
if [ "${NO_PUSH:-}" = "1" ]; then
  echo "Committed locally; NO_PUSH=1 so not pushing."
else
  git push --quiet
  echo "Pushed. GitHub Pages will deploy the new digest."
fi
