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

# Center the title page. Cover lines share the justified body styles, so they
# can only be told apart by position: every paragraph before the first heading is
# title-page content. Apply direct centre alignment there (overrides the style).
python3 - "$OUT" <<'PY'
import sys, re, zipfile, os
out = sys.argv[1]
zin = zipfile.ZipFile(out); data = {n: zin.read(n) for n in zin.namelist()}; zin.close()
doc = data['word/document.xml'].decode()
m = re.search(r'<w:p\b(?:(?!</w:p>).)*?<w:pStyle w:val="Heading', doc, re.S)
cut = m.start() if m else len(doc)
head, tail = doc[:cut], doc[cut:]
def center(p):
    if '<w:jc ' in p:
        return re.sub(r'<w:jc w:val="[^"]*"', '<w:jc w:val="center"', p, count=1)
    if '</w:pPr>' in p:
        return p.replace('</w:pPr>', '<w:jc w:val="center" /></w:pPr>', 1)
    return re.sub(r'(<w:p\b[^>]*>)', r'\1<w:pPr><w:jc w:val="center" /></w:pPr>', p, count=1)
head = re.sub(r'<w:p\b.*?</w:p>', lambda mm: center(mm.group(0)), head, flags=re.S)
data['word/document.xml'] = (head + tail).encode()
tmp = out + '.tmp'
zo = zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED)
for n, d in data.items(): zo.writestr(n, d)
zo.close(); os.replace(tmp, out)
PY

echo "DOCX generated at $OUT"
