#!/usr/bin/env bash
# Populate slidev/media/ from the shared assets/ dir.
# Slidev references images relatively (./media/...), and the Vite import-guard
# rejects paths that resolve outside the project — so media/ must live INSIDE
# slidev/ (a symlink to ../assets would resolve outside and fail). This copies.
# Run once after a fresh clone / after regenerating assets, before `npm run dev`.
set -euo pipefail
cd "$(dirname "$0")/.."            # docs/presentation
mkdir -p slidev/media
cp -r assets/diagrams assets/screenshots assets/heatmaps assets/logos assets/icons slidev/media/
echo "synced assets/ -> slidev/media/"
