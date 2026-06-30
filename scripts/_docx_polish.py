#!/usr/bin/env python3
r"""Post-process the pandoc-generated .docx so the Word export matches the PDF's
structure as closely as a reflowable document can. Operates in place on the
given .docx. Applied by scripts/build_docx.sh after pandoc.

What it does (all by editing word/document.xml + word/settings.xml in the zip):
  1. Numbered captions  - prefixes every figure caption with a live `SEQ Figure`
     field ("Figure N: ...") and every table caption with `SEQ Table`
     ("Table N: ..."), so captions read like the PDF AND the lists below can find
     them.
  2. Front matter        - injects three live Word fields after the title page and
     before the first heading: Contents (TOC \o "1-3"), List of Figures
     (TOC \c "Figure") and List of Tables (TOC \c "Table"), each page-numbered.
  3. Arabic RTL          - marks every paragraph containing Arabic letters as
     right-to-left (w:bidi + run w:rtl) so the Arabic abstract reads correctly.
  4. Title page          - centres every paragraph before the first heading.
  5. updateFields        - sets <w:updateFields/> so Word/LibreOffice populate the
     TOC/SEQ fields on first open (otherwise they show empty until F9).
"""

import re
import sys
import zipfile

DOC = "word/document.xml"
SETTINGS = "word/settings.xml"
ARABIC = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
PARA = re.compile(r"<w:p\b.*?</w:p>", re.S)


def _seq_runs(label: str, ident: str) -> str:
    """A run sequence: 'Label ' + {SEQ ident} field + ': '."""
    return (
        f'<w:r><w:t xml:space="preserve">{label} </w:t></w:r>'
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        f'<w:r><w:instrText xml:space="preserve"> SEQ {ident} \\* ARABIC </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        "<w:r><w:t>1</w:t></w:r>"
        '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
        '<w:r><w:t xml:space="preserve">: </w:t></w:r>'
    )


def number_captions(doc: str) -> str:
    """Insert a SEQ field at the start of each figure/table caption paragraph."""

    def repl(m: re.Match) -> str:
        p = m.group(0)
        if 'w:val="ImageCaption"' in p:
            runs = _seq_runs("Figure", "Figure")
        elif 'w:val="TableCaption"' in p:
            runs = _seq_runs("Table", "Table")
        else:
            return p
        # place the field runs immediately after the paragraph properties
        return p.replace("</w:pPr>", "</w:pPr>" + runs, 1)

    return PARA.sub(repl, doc)


def _toc_block(heading: str, instr: str) -> str:
    """A styled heading paragraph followed by a single TOC field paragraph."""
    return (
        f'<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
        f'<w:r><w:t xml:space="preserve">{heading}</w:t></w:r></w:p>'
        "<w:p>"
        '<w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r>'
        f'<w:r><w:instrText xml:space="preserve">{instr}</w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        '<w:r><w:t xml:space="preserve">Right-click and choose "Update field" to build this list.</w:t></w:r>'
        '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
        "</w:p>"
    )


def inject_front_matter(doc: str) -> tuple[str, int]:
    """Insert Contents / List of Figures / List of Tables before the first heading.
    Returns (new_doc, cut_index) where cut_index marks the title-page boundary."""
    m = re.search(r'<w:p\b(?:(?!</w:p>).)*?<w:pStyle w:val="Heading1"', doc, re.S)
    cut = m.start() if m else doc.rfind("</w:body>")
    page_break = '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
    block = (
        page_break
        + _toc_block("Contents", ' TOC \\o "1-3" \\h \\z \\u ')
        + page_break
        + _toc_block("List of Figures", ' TOC \\h \\z \\c "Figure" ')
        + _toc_block("List of Tables", ' TOC \\h \\z \\c "Table" ')
        + page_break
    )
    return doc[:cut] + block + doc[cut:], cut


def center_title_page(doc: str, cut: int) -> str:
    """Centre every paragraph before `cut` (the title-page content)."""
    head, tail = doc[:cut], doc[cut:]

    def center(m: re.Match) -> str:
        p = m.group(0)
        if "<w:jc " in p:
            return re.sub(r'<w:jc w:val="[^"]*"\s*/>', '<w:jc w:val="center"/>', p, count=1)
        if "<w:pPr>" in p:
            return p.replace("<w:pPr>", '<w:pPr><w:jc w:val="center"/>', 1)
        return re.sub(r"(<w:p\b[^>]*>)", r'\1<w:pPr><w:jc w:val="center"/></w:pPr>', p, count=1)

    head = PARA.sub(center, head)
    head = _borderless_tables(
        head
    )  # the cover's author/supervisor tables are borderless in the PDF
    return head + tail


_NIL_BORDERS = (
    "<w:tblBorders>"
    '<w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/>'
    '<w:right w:val="nil"/><w:insideH w:val="nil"/><w:insideV w:val="nil"/>'
    "</w:tblBorders>"
)


def _borderless_tables(xml: str) -> str:
    """Override table borders to none on every table in the given fragment."""

    def repl(m: re.Match) -> str:
        tbl = m.group(0)
        if "<w:tblBorders>" in tbl:
            return re.sub(
                r"<w:tblBorders>.*?</w:tblBorders>", _NIL_BORDERS, tbl, count=1, flags=re.S
            )
        return tbl.replace("<w:tblPr>", "<w:tblPr>" + _NIL_BORDERS, 1)

    return re.sub(r"<w:tbl>.*?</w:tbl>", repl, xml, flags=re.S)


def rtl_arabic(doc: str) -> str:
    """Mark paragraphs that contain Arabic letters as RTL, and their runs rtl."""

    def repl(m: re.Match) -> str:
        p = m.group(0)
        if not ARABIC.search(p):
            return p
        # paragraph direction
        if "<w:pPr>" in p:
            if "<w:bidi" not in p:
                p = p.replace("<w:pPr>", "<w:pPr><w:bidi/>", 1)
        else:
            p = re.sub(r"(<w:p\b[^>]*>)", r"\1<w:pPr><w:bidi/></w:pPr>", p, count=1)

        # run direction: add <w:rtl/> to every run's rPr (create rPr if missing)
        def run(rm: re.Match) -> str:
            r = rm.group(0)
            if "<w:rtl" in r:
                return r
            if "<w:rPr>" in r:
                return r.replace("<w:rPr>", "<w:rPr><w:rtl/>", 1)
            return re.sub(r"(<w:r\b[^>]*>)", r"\1<w:rPr><w:rtl/></w:rPr>", r, count=1)

        return re.sub(r"<w:r\b.*?</w:r>", run, p, flags=re.S)

    return PARA.sub(repl, doc)


def enable_update_fields(settings: str) -> str:
    if "<w:updateFields" in settings:
        return settings
    # insert as the first child of <w:settings ...> (Word/LibreOffice update the
    # TOC/SEQ fields on open when this flag is present)
    return re.sub(
        r"(<w:settings\b[^>]*>)",
        r'\1<w:updateFields w:val="true"/>',
        settings,
        count=1,
    )


def main() -> None:
    path = sys.argv[1]
    zin = zipfile.ZipFile(path)
    data = {n: zin.read(n) for n in zin.namelist()}
    zin.close()

    doc = data[DOC].decode("utf-8")
    doc = number_captions(doc)
    doc, cut = inject_front_matter(doc)
    doc = center_title_page(doc, cut)
    doc = rtl_arabic(doc)
    data[DOC] = doc.encode("utf-8")

    if SETTINGS in data:
        data[SETTINGS] = enable_update_fields(data[SETTINGS].decode("utf-8")).encode("utf-8")

    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
        for n, d in data.items():
            zo.writestr(n, d)
    import os

    os.replace(tmp, path)
    print("polished", path)


if __name__ == "__main__":
    main()
