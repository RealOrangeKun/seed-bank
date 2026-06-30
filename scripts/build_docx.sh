#!/usr/bin/env bash
# Build a Word (.docx) version of the graduation report with pandoc (no Docker).
#
# pandoc parses the LaTeX directly (it does NOT run XeLaTeX), so this script works
# around the three things a plain `pandoc main.tex` cannot handle:
#   1. Word cannot embed PDF -> diagram PDFs are rasterised to PNG.
#   2. The custom \figslot macro -> redefined to a plain figure for the docx pass.
#   3. biblatex citations -> rendered with citeproc + an IEEE CSL.
# Screenshots that haven't been supplied yet are shown as labelled placeholder
# images (same as the PDF), generated with ImageMagick.
#
# Everything happens in a temp dir; docs/report/figures/ is left untouched.
# Output: docs/report/graduation-project.docx
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/report"
OUT="$DOC/graduation-project.docx"

command -v pandoc   >/dev/null 2>&1 || { echo "pandoc not found:    sudo dnf install pandoc";        exit 1; }
command -v pdftoppm >/dev/null 2>&1 || { echo "pdftoppm not found:  sudo dnf install poppler-utils"; exit 1; }
HAVE_MAGICK=1; command -v magick >/dev/null 2>&1 || command -v convert >/dev/null 2>&1 || HAVE_MAGICK=0

# Styled Word template (Times New Roman 12pt, 1.5 spacing, justified, 2.5cm A4,
# bold serif headings) so the docx matches the PDF's formatting. Regenerate if absent.
[ -f "$DOC/reference.docx" ] || python3 "$ROOT/scripts/make_reference_docx.py"

BUILD="$(mktemp -d)"; trap 'rm -rf "$BUILD"' EXIT
cp "$DOC/main.tex" "$DOC/references.bib" "$DOC/ieee.csl" "$BUILD/"
cp -r "$DOC/chapters" "$BUILD/chapters"
mkdir -p "$BUILD/figures"

mkpng() { # rasterise one diagram PDF -> PNG
  pdftoppm -png -r 200 -singlefile "$DOC/figures/$1" "$BUILD/figures/${1%.pdf}" 2>/dev/null
}
placeholder() { # make a labelled grey box for a not-yet-supplied screenshot
  local name="$1" out="$BUILD/figures/$1"
  if [ "$HAVE_MAGICK" = 1 ]; then
    ${MAGICK:-magick} -size 1100x340 xc:'#ededed' -bordercolor '#999999' -border 2 \
      -gravity center -fill '#555555' -pointsize 30 \
      -annotate 0 "FIGURE PLACEHOLDER\n\nfigures/$name" "$out" 2>/dev/null \
      || convert -size 1100x340 xc:'#ededed' -bordercolor '#999999' -border 2 \
         -gravity center -fill '#555555' -pointsize 30 \
         -annotate 0 "FIGURE PLACEHOLDER\n\nfigures/$name" "$out" 2>/dev/null || true
  fi
}

# Resolve every figure referenced by \figslot into a PNG in the build dir.
refs="$(grep -rhoE '\\figslot(\[[0-9.]*\])?\{[^}]+\}' "$DOC"/chapters/*.tex \
        | sed -E 's/\\figslot(\[[0-9.]*\])?\{//; s/\}.*//' | sort -u)"
for ref in $refs; do
  case "$ref" in
    *.pdf) mkpng "$ref" ;;                                   # diagram -> PNG
    *.png) if [ -f "$DOC/figures/$ref" ]; then cp "$DOC/figures/$ref" "$BUILD/figures/"; \
           else placeholder "$ref"; fi ;;                    # real screenshot or placeholder
  esac
done

# Chapters reference diagrams as .pdf; point them at the rasterised .png.
sed -i 's/\.pdf}/.png}/g' "$BUILD"/chapters/*.tex

# Rewrite longtables into a pandoc-friendly shape (single header, no \multicolumn,
# no rule machinery) so they convert to real Word tables instead of literal '&'.
python3 "$ROOT/scripts/_docx_fix_tables.py" "$BUILD"/chapters/*.tex

# The Arabic abstract is wrapped in `\begin{otherlanguage*}{arabic}` for XeLaTeX's
# bidi; pandoc has no such environment and would print the literal word "arabic".
# Strip the wrapper (the Arabic UTF-8 text passes through regardless); RTL direction
# is reapplied to those paragraphs in _docx_polish.py.
sed -i -E 's/\\begin\{otherlanguage\*\}\{arabic\}//; s/\\end\{otherlanguage\*\}//' "$BUILD/main.tex"

# Redefine \figslot to a plain figure pandoc can convert (replaces the PDF-only,
# \IfFileExists-based definition just for this pass).
awk '/\\begin\{document\}/ && !d {print "\\renewcommand{\\figslot}[4][0.85]{\\begin{figure}\\centering\\includegraphics[width=#1\\linewidth]{figures/#2}\\caption{#3}\\label{#4}\\end{figure}}"; d=1} {print}' \
  "$BUILD/main.tex" > "$BUILD/main.docx.tex"

( cd "$BUILD" && pandoc main.docx.tex \
    --from=latex --to=docx \
    --reference-doc="$DOC/reference.docx" \
    --citeproc --bibliography=references.bib --csl=ieee.csl \
    --resource-path=.:figures \
    --number-sections \
    --output="$OUT" )
# Note: no static --toc. The cover page comes first; generate the Table of
# Contents (and Lists of Figures/Tables) natively in Word via References ->
# Table of Contents, so page numbers track Word's own pagination.

# Post-process the docx to match the PDF's structure: numbered Figure/Table
# captions (SEQ fields), live page-numbered Contents + List of Figures + List of
# Tables, RTL Arabic paragraphs, and a centred title page. See _docx_polish.py.
python3 "$ROOT/scripts/_docx_polish.py" "$OUT"

echo "DOCX generated at $OUT"
