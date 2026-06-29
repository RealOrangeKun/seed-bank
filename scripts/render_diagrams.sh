#!/usr/bin/env bash
# Render every Mermaid diagram in docs/diagrams/ to a PDF in docs/report/figures/
# so the LaTeX report can \includegraphics them.
#
#   - docs/diagrams/NN-*.md   -> the first ```mermaid fenced block is extracted
#   - docs/diagrams/NN-*.mmd  -> rendered directly
#
# Output: docs/report/figures/NN-*.pdf  (vector, ideal for print)
#
# Renderer (auto-detected, override with RENDERER=npx|docker):
#   npx     -> npx -y @mermaid-js/mermaid-cli   (needs Node + a headless Chromium)
#   docker  -> minlag/mermaid-cli image         (needs Docker)
#
# Re-run any time a diagram changes. Idempotent: it overwrites the PDFs.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/docs/diagrams"
OUT="$ROOT/docs/report/figures"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$OUT"

# puppeteer needs --no-sandbox in most CI / container environments
PCFG="$TMP/puppeteer.json"
printf '{ "args": ["--no-sandbox", "--disable-setuid-sandbox"] }\n' > "$PCFG"

RENDERER="${RENDERER:-}"
if [[ -z "$RENDERER" ]]; then
  if command -v npx >/dev/null 2>&1; then RENDERER=npx
  elif command -v docker >/dev/null 2>&1; then RENDERER=docker
  else echo "ERROR: need either 'npx' (Node) or 'docker' to render Mermaid." >&2; exit 1
  fi
fi
echo ">> renderer: $RENDERER"

render() { # <input.mmd> <output.pdf>
  local in="$1" out="$2"
  case "$RENDERER" in
    npx)
      npx -y @mermaid-js/mermaid-cli -p "$PCFG" -i "$in" -o "$out" -b transparent ;;
    docker)
      docker run --rm -v "$TMP:/data" -v "$OUT:/out" minlag/mermaid-cli \
        -i "/data/$(basename "$in")" -o "/out/$(basename "$out")" -b transparent ;;
  esac
}

extract_mermaid() { # <file.md> -> stdout (mermaid body)
  awk '/^```mermaid[[:space:]]*$/{f=1;next} /^```[[:space:]]*$/{if(f)exit} f' "$1"
}

shopt -s nullglob
count=0
failed=""
for f in "$SRC"/*.md "$SRC"/*.mmd; do
  base="$(basename "$f")"; base="${base%.*}"
  [[ "$base" == "README" ]] && continue
  mmd="$TMP/$base.mmd"
  if [[ "$f" == *.md ]]; then
    extract_mermaid "$f" > "$mmd"
    [[ -s "$mmd" ]] || { echo "  -- skip $base (no mermaid block)"; continue; }
  else
    cp "$f" "$mmd"
  fi
  echo ">> rendering $base"
  if render "$mmd" "$OUT/$base.pdf" 2> "$TMP/$base.err"; then
    count=$((count+1))
  else
    echo "  !! FAILED $base (left as a report placeholder):"
    sed 's/^/     /' "$TMP/$base.err" | head -4
    failed="$failed $base"
  fi
done
echo ">> done: $count diagram(s) rendered -> $OUT"
[[ -n "${failed:-}" ]] && echo ">> failed:${failed}" || echo ">> no failures"
