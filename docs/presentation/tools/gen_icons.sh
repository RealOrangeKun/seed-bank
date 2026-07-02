#!/usr/bin/env bash
# Generate the Lucide icon PNG library used by BOTH decks (Slidev + PPTX).
# Colourises Lucide SVGs (stroke="currentColor") to the deck palette and rasterises
# to PNG. Output -> docs/presentation/assets/icons/ (mirrored into slidev/media/icons/).
set -euo pipefail
cd "$(dirname "$0")/.."           # docs/presentation
SRC=slidev/node_modules/lucide-static/icons
OUT=assets/icons
mkdir -p "$OUT"

LEAF="#1E7A40"; AMBER="#E08A1E"; RED="#C0392B"

emit() {  # emit <icon-name> <hex> <out-name>
  local svg="$SRC/$1.svg"; local hex="$2"; local out="$OUT/$3.png"
  if [ -f "$svg" ]; then
    sed "s/currentColor/$hex/g" "$svg" > /tmp/_ic.svg
    rsvg-convert -w 96 -h 96 /tmp/_ic.svg -o "$out"
  else
    echo "  MISSING $1.svg"
  fi
}

# --- leaf-green set (default) ---
for n in camera cpu bar-chart-3 server database monitor-smartphone workflow layers scan crop \
 badge-check git-branch package flask-conical rocket shield key users scroll-text link sprout leaf \
 dna dollar-sign tags microscope globe ruler eye shuffle zoom-in binary target zap scissors copy \
 file-output refresh-cw recycle monitor smartphone warehouse brain-circuit tractor wheat clock \
 trending-up trending-down hand factory languages split move-diagonal rotate-cw flip-horizontal-2 \
 wind sun mountain square-minus lock network file-text help-circle box list-checks image combine \
 wand-2 contrast aperture; do
  emit "$n" "$LEAF" "$n"
done

# --- status-coloured variants ---
emit circle-check   "$LEAF"  check-green
emit alert-triangle "$AMBER" alert-amber
emit circle-x       "$RED"   x-red
emit star           "$AMBER" star-amber
emit trending-down  "$RED"   trending-down-red

echo "generated $(ls "$OUT" | wc -l) icons -> $OUT"
mkdir -p slidev/media/icons
cp "$OUT"/*.png slidev/media/icons/
echo "mirrored -> slidev/media/icons/"
