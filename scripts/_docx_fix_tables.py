#!/usr/bin/env python3
"""Rewrite LaTeX longtables (in place, on the given .tex files) into a
pandoc-friendly shape for the Word build.

pandoc's longtable reader mishandles these tables two ways:
  * \multicolumn group rows make it bail out and emit literal '&' separators;
  * the \endfirsthead/\endhead machinery duplicates the header row.

This collapses each longtable to: optional caption, one header row, then body
rows, with \multicolumn group rows flattened into a normal first-column label.
Regular table/tabular environments are left untouched.
"""
import re, sys


def extract_braced(s, i):
    """s[i] must be '{'. Return (inner_text, index_after_matching_brace)."""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == '{':
            depth += 1
        elif s[j] == '}':
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
    return s[i + 1:], len(s)


MACH = re.compile(r'\\(toprule|midrule|bottomrule|addlinespace|'
                  r'endfirsthead|endhead|endfoot|endlastfoot)\b')


def count_cols(colspec):
    return len(re.findall(r'p\{[^}]*\}|m\{[^}]*\}|b\{[^}]*\}|[lrc]', colspec)) or 1


def flatten_multicolumn(row, ncol):
    """\\multicolumn{N}{align}{content} -> content followed by blank cells."""
    i = len(r'\multicolumn')
    _, i = extract_braced(row, row.index('{', i))   # {N}
    _, i = extract_braced(row, row.index('{', i))   # {align}
    content, _ = extract_braced(row, row.index('{', i))  # {content}
    return content.strip() + ' &' * (ncol - 1)


def fix_longtable(block):
    m = re.match(r'\\begin\{longtable\}(\[[^\]]*\])?\s*', block)
    colspec, after = extract_braced(block, block.index('{', m.end() - 1))
    ncol = count_cols(colspec)
    body = block[after:block.rindex(r'\end{longtable}')]

    caption, rows = None, []
    for raw in re.split(r'\\\\', body):
        r = MACH.sub('', raw).strip()
        if not r:
            continue
        if r.startswith(r'\caption'):
            caption = r
            continue
        if r'\multicolumn' in r and 'continued' in r:
            continue
        if r.startswith(r'\multicolumn'):
            r = flatten_multicolumn(r, ncol)
        if rows and rows[-1] == r:        # drop duplicated header
            continue
        rows.append(r)

    if not rows:
        return block
    out = [r'\begin{longtable}{' + colspec + '}']
    if caption:
        out.append(caption + r' \\')
    out += [r'\toprule', rows[0] + r' \\', r'\midrule', r'\endhead']
    out += [r + r' \\' for r in rows[1:]]
    out += [r'\bottomrule', r'\end{longtable}']
    return '\n'.join(out)


def main(paths):
    for p in paths:
        s = open(p, encoding='utf-8').read()
        s2 = re.sub(r'\\begin\{longtable\}.*?\\end\{longtable\}',
                    lambda mm: fix_longtable(mm.group(0)), s, flags=re.S)
        if s2 != s:
            open(p, 'w', encoding='utf-8').write(s2)


if __name__ == '__main__':
    main(sys.argv[1:])
