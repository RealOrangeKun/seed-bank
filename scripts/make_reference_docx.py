#!/usr/bin/env python3
"""Build a styled pandoc reference template -> docs/report/reference.docx.

Makes the Word export match the PDF's formatting rules: Times New Roman 12pt body,
1.5 line spacing, justified text, 2.5 cm margins on A4, black bold serif headings,
and single-spaced centred captions. Pandoc copies these styles (and the page
setup) into the generated .docx via --reference-doc.
"""
import os, re, subprocess, tempfile, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "report", "reference.docx")

tmp = tempfile.mkdtemp()
base = os.path.join(tmp, "base.docx")
subprocess.run(["pandoc", "-o", base, "--print-default-data-file", "reference.docx"], check=True)
ex = os.path.join(tmp, "ex"); os.makedirs(ex)
with zipfile.ZipFile(base) as z:
    z.extractall(ex)

def patch(rel, fn):
    p = os.path.join(ex, rel)
    with open(p, encoding="utf-8") as f:
        s = f.read()
    s = fn(s)
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)

# --- theme: serif fonts everywhere ---
def theme(s):
    s = re.sub(r'(<a:majorFont>\s*<a:latin typeface=")[^"]*(")', r'\1Times New Roman\2', s)
    s = re.sub(r'(<a:minorFont>\s*<a:latin typeface=")[^"]*(")', r'\1Times New Roman\2', s)
    return s
patch("word/theme/theme1.xml", theme)

def set_jc(s, style_id, val):
    """Force paragraph alignment (jc) on a named style, adding a pPr if absent.
    pPr must precede rPr / close, per the OOXML style child order."""
    def repl(m):
        b = m.group(0)
        if "<w:pPr>" in b:
            if "<w:jc " in b:
                b = re.sub(r"<w:jc [^/]*/>", f'<w:jc w:val="{val}" />', b, count=1)
            else:
                b = b.replace("<w:pPr>", f'<w:pPr><w:jc w:val="{val}" />', 1)
        elif "<w:rPr>" in b:
            b = b.replace("<w:rPr>", f'<w:pPr><w:jc w:val="{val}" /></w:pPr><w:rPr>', 1)
        else:
            b = b.replace("</w:style>", f'<w:pPr><w:jc w:val="{val}" /></w:pPr></w:style>', 1)
        return b
    return re.sub(r'<w:style [^>]*w:styleId="' + style_id + r'".*?</w:style>',
                  repl, s, count=1, flags=re.S)

# --- styles: 1.5 spacing default; per-style alignment; bold black headings ---
def styles(s):
    # document-wide default: 1.5 line spacing (alignment is set per style below)
    s = s.replace('<w:spacing w:after="200" />',
                  '<w:spacing w:after="120" w:line="360" w:lineRule="auto" />')

    # bold + explicit black on every heading (LibreOffice ignores the theme accent,
    # so set the colour literally rather than via themeColor)
    def head(m):
        b = re.sub(r"(<w:rPr>)", r"\1<w:b /><w:bCs />", m.group(0), count=1)
        b = re.sub(r'<w:color w:val="[0-9A-Fa-f]{6}" w:themeColor="accent1"[^/]*/>',
                   '<w:color w:val="000000" />', b)
        return b
    s = re.sub(r'<w:style w:type="paragraph" w:styleId="Heading[1-9]".*?</w:style>',
               head, s, flags=re.S)

    # alignment: cover (Normal) centred; body justified; lists/code/headings left
    s = set_jc(s, "Normal", "center")           # title page lines
    for sid in ("BodyText", "FirstParagraph", "Bibliography"):
        s = set_jc(s, sid, "both")              # justified body + references
    for sid in ("Compact", "SourceCode"):
        s = set_jc(s, sid, "left")              # lists, table cells, code
    for n in range(1, 10):
        s = set_jc(s, f"Heading{n}", "left")    # headings left-aligned
    return s
patch("word/styles.xml", styles)

# --- tables: a clean single-line grid (the default has only a header rule) ---
def tables(s):
    borders = ("<w:tblBorders>" + "".join(
        f'<w:{e} w:val="single" w:sz="4" w:space="0" w:color="auto" />'
        for e in ("top", "left", "bottom", "right", "insideH", "insideV")
    ) + "</w:tblBorders>")
    def repl(m):
        return m.group(0).replace("<w:tblPr>", "<w:tblPr>" + borders, 1)
    return re.sub(r'<w:style w:type="table"[^>]*w:styleId="Table".*?</w:style>',
                  repl, s, count=1, flags=re.S)
patch("word/styles.xml", tables)

# --- page setup: A4, 2.5 cm margins (1417 twips). Inserted after footnotePr so
#     the OOXML sectPr child order stays valid. ---
PG = ('<w:pgSz w:w="11906" w:h="16838" />'
      '<w:pgMar w:top="1417" w:right="1417" w:bottom="1417" w:left="1417" '
      'w:header="708" w:footer="708" w:gutter="0" />')
patch("word/document.xml", lambda s: s.replace('</w:sectPr>', PG + '</w:sectPr>', 1))

# --- repackage ---
if os.path.exists(OUT):
    os.remove(OUT)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(ex):
        for fn in files:
            full = os.path.join(root, fn)
            z.write(full, os.path.relpath(full, ex))
print("wrote", OUT)
