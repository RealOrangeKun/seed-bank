#!/usr/bin/env python3
"""Build the full 39-slide Seed Bank graduation deck as an editable .pptx.

Mirrors the Slidev deck and the `presentation.md` content guide: one consistent
environmental palette (soft greens on warm-white), Inter, Lucide icon chips (no
emoji), watermark + slide-number chrome, speaker notes, and an auto-fade entrance
animation on each slide's hero element (injected as PowerPoint timing XML).

Run:  ./.venv/bin/python build_pptx.py   ->  seed-bank.pptx
"""

from __future__ import annotations

import os

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml import parse_xml
from pptx.util import Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
FONT = "Inter"

# ---- ONE environmental palette ----
LEAF = RGBColor(0x1E, 0x7A, 0x40)
LEAF_DEEP = RGBColor(0x14, 0x53, 0x2D)
LEAF_SOFT = RGBColor(0xEA, 0xF3, 0xEC)
INFO = RGBColor(0x15, 0x7A, 0xAC)
AMBER = RGBColor(0xE0, 0x8A, 0x1E)
AMBER_SOFT = RGBColor(0xFB, 0xF1, 0xDE)
RED = RGBColor(0xC0, 0x39, 0x2B)
BG = RGBColor(0xFA, 0xFB, 0xF8)
CARDBG = RGBColor(0xFF, 0xFF, 0xFF)
TEXT = RGBColor(0x16, 0x26, 0x1E)
MUTED = RGBColor(0x5C, 0x6B, 0x62)
BORDER = RGBColor(0xE6, 0xEB, 0xE4)
CHROME = RGBColor(0x9A, 0xA7, 0x9F)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
DETECT_BG = RGBColor(0xE7, 0xF0, 0xF7)
DETECT_FG = RGBColor(0x12, 0x55, 0x7A)

SW, SH = 13.333, 7.5
TOTAL = 39

prs = Presentation()
prs.slide_width = Inches(SW)
prs.slide_height = Inches(SH)
BLANK = prs.slide_layouts[6]


def _a(*p):
    return os.path.join(ASSETS, *p)


def new_slide(bg=BG):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = bg
    return s


def text(
    s,
    x,
    y,
    w,
    h,
    runs,
    *,
    align=PP_ALIGN.LEFT,
    anchor=MSO_ANCHOR.TOP,
    space_after=2.0,
    line=1.08,
    wrap=True,
):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        p.space_before = Pt(0)
        p.line_spacing = line
        for t, size, color, bold in para:
            r = p.add_run()
            r.text = t
            r.font.name = FONT
            r.font.size = Pt(size)
            r.font.bold = bold
            r.font.color.rgb = color
    return tb


def rrect(s, x, y, w, h, fill, line_color=None, line_w=1.0, radius=0.09):
    sp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sp.adjustments[0] = radius
    sp.fill.solid()
    sp.fill.fore_color.rgb = fill
    if line_color is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line_color
        sp.line.width = Pt(line_w)
    sp.shadow.inherit = False
    return sp


def rect(s, x, y, w, h, fill):
    sp = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sp.fill.solid()
    sp.fill.fore_color.rgb = fill
    sp.line.fill.background()
    sp.shadow.inherit = False
    return sp


def picture_fit(s, path, x, y, max_w, max_h, align="center", valign="middle"):
    with Image.open(path) as im:
        iw, ih = im.size
    ar = iw / ih
    w, h = max_w, max_w / ar
    if h > max_h:
        h, w = max_h, max_h * ar
    px = x + (max_w - w) / 2 if align == "center" else x
    py = y + (max_h - h) / 2 if valign == "middle" else y
    return s.shapes.add_picture(path, Inches(px), Inches(py), Inches(w), Inches(h))


def notes(s, txt):
    s.notes_slide.notes_text_frame.text = txt.strip()


# ---- chrome ----
def footer(s, n):
    picture_fit(s, _a("logos", "seed.png"), 0.55, SH - 0.5, 0.22, 0.22, valign="top")
    text(s, 0.83, SH - 0.5, 2.0, 0.3, [[("Seed Bank", 9, CHROME, True)]], anchor=MSO_ANCHOR.MIDDLE)
    text(
        s,
        SW - 2.05,
        SH - 0.5,
        1.5,
        0.3,
        [[(f"{n} / {TOTAL}", 9, CHROME, False)]],
        align=PP_ALIGN.RIGHT,
        anchor=MSO_ANCHOR.MIDDLE,
    )


def act_tag(s, txt):
    w = 0.16 * len(txt) + 0.4
    chip = rrect(s, 0.9, 0.42, w, 0.28, LEAF_SOFT, radius=0.3)
    tf = chip.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = txt.upper()
    r.font.name = FONT
    r.font.size = Pt(8)
    r.font.bold = True
    r.font.color.rgb = LEAF


def head(s, main, sub=None, amber_suffix=None):
    runs = [(main, 26, LEAF_DEEP, True)]
    if amber_suffix:
        runs.append((" " + amber_suffix, 26, AMBER, True))
    text(s, 0.9, 0.78, 11.5, 0.7, [runs])
    if sub:
        text(s, 0.9, 1.5, 11.5, 0.45, [[(sub, 16, LEAF, True)]])
        return 2.15
    return 1.7


def icon_chip(s, x, y, size, icon, bg=LEAF_SOFT):
    if bg is not None:
        rrect(s, x, y, size, size, bg, radius=0.22)
    pad = size * 0.24
    picture_fit(s, _a("icons", icon + ".png"), x + pad, y + pad, size - 2 * pad, size - 2 * pad)


def card(s, x, y, w, h, accent=None, fill=CARDBG):
    sp = rrect(s, x, y, w, h, fill, line_color=BORDER, line_w=1.0, radius=0.09)
    if accent == "leaf":
        rect(s, x, y, 0.06, h, LEAF)
    elif accent == "amber":
        rect(s, x, y, 0.06, h, AMBER)
    return sp


def bullets(s, x, y, w, h, items, size=11, color=MUTED, anchor=MSO_ANCHOR.TOP, gap=2.0):
    paras = []
    for it in items:
        if isinstance(it, str):
            paras.append([("•  ", size, LEAF, True), (it, size, color, False)])
        else:  # list of runs already
            paras.append([("•  ", size, LEAF, True)] + it)
    return text(s, x, y, w, h, paras, anchor=anchor, space_after=gap, line=1.2)


def badge(s, x, y, num, lab, amber=False, w=2.4):
    col = AMBER if amber else LEAF_DEEP
    rrect(s, x, y, w, 1.0, CARDBG, line_color=BORDER, radius=0.1)
    rect(s, x, y, 0.06, 1.0, AMBER if amber else LEAF)
    text(s, x + 0.22, y + 0.12, w - 0.35, 0.5, [[(num, 22, col, True)]])
    text(s, x + 0.22, y + 0.6, w - 0.35, 0.35, [[(lab, 9, MUTED, False)]])


def pill(s, x, y, label, icon=None, border=BORDER):
    w = 0.098 * len(label) + (0.42 if icon else 0.2) + 0.35
    rrect(s, x, y, w, 0.42, CARDBG, line_color=border, radius=0.5)
    tx = x + 0.2
    if icon:
        icon_chip(s, x + 0.13, y + 0.08, 0.26, icon, bg=None)
        tx = x + 0.48
    text(s, tx, y, w - (tx - x) - 0.1, 0.42, [[(label, 10, TEXT, True)]], anchor=MSO_ANCHOR.MIDDLE)
    return w


def pill_row(s, x, y, items, gap=0.2):
    cx = x
    for it in items:
        if isinstance(it, tuple):
            label = it[0]
            icon = it[1] if len(it) > 1 else None
        else:
            label, icon = it, None
        cx += pill(s, cx, y, label, icon) + gap


# ---- animation: auto-fade entrance (start with previous, staggered) ----
_TID = [100]


def _nid():
    _TID[0] += 1
    return _TID[0]


def animate_fade(s, shapes, dur=500, stagger=250):
    """Inject a PowerPoint timing tree: each shape fades in automatically (with
    previous), staggered. Verified structurally; confirm playback in PowerPoint."""
    if not shapes:
        return
    pars = []
    for i, sp in enumerate(shapes):
        spid = sp.shape_id
        delay = i * stagger
        i1, i2, i3, i4, i5 = _nid(), _nid(), _nid(), _nid(), _nid()
        pars.append(f"""
        <p:par>
          <p:cTn id="{i1}" fill="hold">
            <p:stCondLst><p:cond delay="{delay}"/></p:stCondLst>
            <p:childTnLst>
              <p:par>
                <p:cTn id="{i2}" fill="hold">
                  <p:stCondLst><p:cond delay="0"/></p:stCondLst>
                  <p:childTnLst>
                    <p:par>
                      <p:cTn id="{i3}" presetID="10" presetClass="entr" presetSubtype="0" fill="hold" grpId="0" nodeType="withEffect">
                        <p:stCondLst><p:cond delay="0"/></p:stCondLst>
                        <p:childTnLst>
                          <p:set>
                            <p:cBhvr>
                              <p:cTn id="{i4}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>
                              <p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>
                              <p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst>
                            </p:cBhvr>
                            <p:to><p:strVal val="visible"/></p:to>
                          </p:set>
                          <p:animEffect transition="in" filter="fade">
                            <p:cBhvr>
                              <p:cTn id="{i5}" dur="{dur}"/>
                              <p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>
                            </p:cBhvr>
                          </p:animEffect>
                        </p:childTnLst>
                      </p:cTn>
                    </p:par>
                  </p:childTnLst>
                </p:cTn>
              </p:par>
            </p:childTnLst>
          </p:cTn>
        </p:par>""")
    root = _nid()
    seq = _nid()
    xml = f"""<p:timing xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
        xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
      <p:tnLst><p:par><p:cTn id="{root}" dur="indefinite" restart="never" nodeType="tmRoot">
        <p:childTnLst>
          <p:seq concurrent="1" nextAc="seek">
            <p:cTn id="{seq}" dur="indefinite" nodeType="mainSeq">
              <p:childTnLst>{"".join(pars)}</p:childTnLst>
            </p:cTn>
            <p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>
            <p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>
          </p:seq>
        </p:childTnLst>
      </p:cTn></p:par></p:tnLst>
    </p:timing>"""
    s._element.append(parse_xml(xml))


def diagram_card(s, path, x, y, w, h, caption=None):
    rrect(s, x, y, w, h, CARDBG, line_color=BORDER, radius=0.05)
    cap_h = 0.28 if caption else 0
    pic = picture_fit(s, path, x + 0.15, y + 0.15, w - 0.3, h - 0.3 - cap_h)
    if caption:
        text(s, x, y + h - 0.26, w, 0.24, [[(caption, 8, MUTED, False)]], align=PP_ALIGN.CENTER)
    return pic


def stage(s, x, y, w, h, label, sub=None, kind="io"):
    fill, fg = {
        "io": (CARDBG, TEXT),
        "detect": (DETECT_BG, DETECT_FG),
        "classify": (LEAF_SOFT, LEAF_DEEP),
    }[kind]
    line = (
        BORDER
        if kind == "io"
        else (RGBColor(0xCF, 0xE0, 0xEC) if kind == "detect" else RGBColor(0xD5, 0xE6, 0xDA))
    )
    rrect(s, x, y, w, h, fill, line_color=line, radius=0.12)
    runs = [[(label, 10.5, fg, True)]]
    if sub:
        runs.append([(sub, 8, fg, False)])
    text(
        s,
        x + 0.1,
        y + 0.1,
        w - 0.2,
        h - 0.2,
        runs,
        align=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE,
        space_after=1.0,
    )


def arrow(s, x, y, w=0.35):
    text(
        s, x, y, w, 0.4, [[("→", 16, MUTED, True)]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE
    )


# =====================================================================================
#  SLIDES
# =====================================================================================

# ---- SLIDE 1 — Title ----
s = new_slide()
t1 = text(
    s,
    0,
    2.15,
    SW,
    1.1,
    [[("Seed Bank", 54, LEAF_DEEP, True)]],
    align=PP_ALIGN.CENTER,
    anchor=MSO_ANCHOR.MIDDLE,
)
text(
    s,
    0,
    3.28,
    SW,
    0.6,
    [[("AI-Powered Seed Quality Intelligence", 24, LEAF, False)]],
    align=PP_ALIGN.CENTER,
)
text(
    s,
    0,
    4.08,
    SW,
    0.4,
    [[("Faculty of Computers and Artificial Intelligence · Cairo University", 13, TEXT, True)]],
    align=PP_ALIGN.CENTER,
)
text(
    s,
    0,
    4.48,
    SW,
    0.4,
    [
        [
            (
                "Supervisors: Dr. Ali Zidane · Dr. Ghada Dahy · Dr. Heba Sherif · Dr. Eman Ahmed",
                11,
                MUTED,
                False,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
)


def team_chip(cx, nw, label, names):
    chip = rrect(s, cx, 5.15, 0.42, 0.3, LEAF, radius=0.3)
    tf = chip.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.name = FONT
    r.font.size = Pt(10)
    r.font.bold = True
    r.font.color.rgb = WHITE
    text(s, cx + 0.5, 5.13, nw, 0.35, [[(names, 11, TEXT, False)]], anchor=MSO_ANCHOR.MIDDLE)


team_chip(1.35, 4.6, "AI", "Omar Ez-Eldin Abdullah · Yussuf Ahmed Awad")
team_chip(6.85, 5.6, "IS", "Ali Abdelrahman · Mohamed Amr · Youssef Tarek Ali")
lg1 = picture_fit(
    s, _a("logos", "Cairo_University_new_logo.png"), 5.55, 5.8, 0.95, 0.95, valign="top"
)
picture_fit(s, _a("logos", "FCAI.jpg"), 6.75, 5.8, 1.1, 0.95, valign="top")
footer(s, 1)
animate_fade(s, [t1])
notes(
    s,
    'Open warm and confident — "We built an AI platform that grades seed quality from a single '
    'photo — usable by a farmer in a field or a QA lab." Name the two sub-teams (AI + IS).',
)

# ---- SLIDE 2 — A Seed Bank in Computer Science? ----
s = new_slide()
act_tag(s, "Act I · The Problem")
head(s, "A Seed Bank… in Computer Science?")
c1 = card(s, 1.4, 2.2, 4.8, 2.3, accent="leaf")
icon_chip(s, 3.5, 2.5, 0.7, "warehouse")
text(s, 1.5, 3.3, 4.6, 0.5, [[("A storage vault?", 15, LEAF_DEEP, True)]], align=PP_ALIGN.CENTER)
text(
    s,
    1.5,
    3.8,
    4.6,
    0.4,
    [[("Preserving seeds for the future", 11, MUTED, False)]],
    align=PP_ALIGN.CENTER,
)
c2 = card(s, 7.1, 2.2, 4.8, 2.3, accent="leaf")
icon_chip(s, 9.2, 2.5, 0.7, "brain-circuit")
text(
    s,
    7.2,
    3.3,
    4.6,
    0.5,
    [[("…or seed intelligence?", 15, LEAF_DEEP, True)]],
    align=PP_ALIGN.CENTER,
)
text(
    s,
    7.2,
    3.8,
    4.6,
    0.4,
    [[("AI that grades seed quality", 11, MUTED, False)]],
    align=PP_ALIGN.CENTER,
)
q = text(s, 0, 4.7, SW, 1.0, [[("?", 44, AMBER, True)]], align=PP_ALIGN.CENTER)
footer(s, 2)
animate_fade(s, [c1, c2, q])
notes(
    s,
    "Let the visual do the work — pause on the '?'. Reveal we mean seed-quality intelligence, "
    "not a storage vault. → Next: the 30-second version of what it does.",
)

# ---- SLIDE 3 — The 30-Second Pitch ----
s = new_slide()
act_tag(s, "Act I · The Problem")
head(s, "The 30-Second Pitch")
stage(s, 2.2, 1.9, 2.6, 0.8, "Photograph seeds", kind="io")
arrow(s, 4.9, 2.1)
stage(s, 5.4, 1.9, 2.6, 0.8, "AI analyzes", kind="classify")
arrow(s, 8.1, 2.1)
stage(s, 8.6, 1.9, 2.6, 0.8, "Quality report", kind="io")
d1 = diagram_card(s, _a("screenshots", "Dashboard.png"), 1.4, 3.0, 5.2, 2.9)
diagram_card(s, _a("screenshots", "MobileView.png"), 6.9, 3.0, 5.0, 2.9)
text(
    s,
    0,
    6.0,
    SW,
    0.4,
    [
        [
            (
                "A platform for farmers and QA labs to instantly grade seed quality using computer vision.",
                12,
                MUTED,
                False,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
)
footer(s, 3)
animate_fade(s, [d1])
notes(s, "The whole product in one breath — photograph → analyze → report, on web and mobile.")

# ---- SLIDE 4 — Who Is This For? ----
s = new_slide()
act_tag(s, "Act I · The Problem")
head(s, "Who Is This For?")
p1 = card(s, 0.9, 2.1, 5.6, 2.4, accent="leaf")
icon_chip(s, 1.15, 2.35, 0.7, "tractor")
text(s, 2.05, 2.4, 4.2, 0.4, [[("The Farmer", 15, LEAF_DEEP, True)]])
text(s, 2.05, 2.82, 4.2, 0.3, [[("Checking quality in the field", 10, MUTED, False)]])
pill_row(s, 1.15, 3.5, [("Slow counting", "clock"), ("Subjective", "help-circle")])
pill_row(s, 1.15, 4.0, [("No digital tools", "smartphone")])
p2 = card(s, 6.8, 2.1, 5.6, 2.4, accent="leaf")
icon_chip(s, 7.05, 2.35, 0.7, "flask-conical")
text(s, 7.95, 2.4, 4.2, 0.4, [[("The QA Laboratory", 15, LEAF_DEEP, True)]])
text(s, 7.95, 2.82, 4.2, 0.3, [[("Grading at throughput", 10, MUTED, False)]])
pill_row(s, 7.05, 3.5, [("Needs throughput", "bar-chart-3"), ("Needs objectivity", "target")])
pill_row(s, 7.05, 4.0, [("Machines too costly", "dollar-sign")])
text(
    s,
    0,
    4.8,
    SW,
    0.4,
    [[("Two audiences, two pains — and one backend serves both.", 13, MUTED, False)]],
    align=PP_ALIGN.CENTER,
)
footer(s, 4)
animate_fade(s, [p1, p2])
notes(
    s,
    "Two audiences, two different pains. Stress that one backend serves both (paid off in the platform act).",
)

# ---- SLIDE 5 — The Problem: Manual Grading ----
s = new_slide()
act_tag(s, "Act I · The Problem")
head(s, "The Problem: Manual Grading")
ch = icon_chip(s, 6.17, 2.3, 1.0, "hand")
text(
    s,
    0,
    3.45,
    SW,
    0.4,
    [[("Sorting seeds by hand, one tray at a time", 12, MUTED, False)]],
    align=PP_ALIGN.CENTER,
)
pr_y = 4.3
labels = [
    ("Slow", "clock"),
    ("Subjective", "help-circle"),
    ("Inconsistent", "x-red"),
    ("Can't scale", "trending-down-red"),
]
# centre the pill row
totw = sum(0.098 * len(l) + 0.42 + 0.35 for l, _ in labels) + 0.2 * (len(labels) - 1)
pill_row(s, (SW - totw) / 2, pr_y, labels)
footer(s, 5)
notes(
    s,
    "Manual grading is slow, subjective, inconsistent, and doesn't scale — the core pain in four words.",
)

# ---- SLIDE 6 — The Technology Gap ----
s = new_slide()
act_tag(s, "Act I · The Problem")
head(s, "The Technology Gap")
c1 = card(s, 0.9, 2.3, 3.6, 2.6)
icon_chip(s, 2.35, 2.6, 0.7, "factory")
text(
    s,
    1.0,
    3.5,
    3.4,
    0.6,
    [[("Industrial Optical Sorters", 13, LEAF_DEEP, True)]],
    align=PP_ALIGN.CENTER,
)
text(s, 1.0, 4.2, 3.4, 0.4, [[("$$$$$", 16, RED, True)]], align=PP_ALIGN.CENTER)
c2 = card(s, 4.85, 2.15, 3.65, 2.9, accent="amber", fill=AMBER_SOFT)
icon_chip(s, 6.35, 2.5, 0.7, "leaf", bg=None)
text(
    s,
    4.95,
    3.4,
    3.45,
    0.6,
    [[("Nothing affordable here", 14, LEAF_DEEP, True)]],
    align=PP_ALIGN.CENTER,
)
text(
    s,
    4.95,
    4.15,
    3.45,
    0.5,
    [[("Seed Bank fills this gap", 14, LEAF, True)]],
    align=PP_ALIGN.CENTER,
)
c3 = card(s, 8.85, 2.3, 3.6, 2.6)
icon_chip(s, 10.3, 2.6, 0.7, "hand")
text(s, 8.95, 3.5, 3.4, 0.6, [[("Manual Counting", 13, LEAF_DEEP, True)]], align=PP_ALIGN.CENTER)
text(
    s,
    8.95,
    4.2,
    3.4,
    0.4,
    [[("Cheap, but slow & subjective", 10, MUTED, False)]],
    align=PP_ALIGN.CENTER,
)
footer(s, 6)
animate_fade(s, [c1, c2, c3])
notes(
    s,
    "Nothing affordable between hand-counting and industrial optical sorters — that empty middle is our wedge.",
)

# ---- SLIDE 7 — Why Seeds Are Hard for AI ----
s = new_slide()
act_tag(s, "Act I · The Problem")
head(s, "Why Seeds Are Hard for AI")
cells = [
    ("Overlap & Clutter", "layers"),
    ("Lighting Variation", "sun"),
    ("Subtle Defects", "zoom-in"),
    ("Natural ≈ Damaged", "help-circle"),
]
cw, gap = 2.75, 0.25
x0 = (SW - (cw * 4 + gap * 3)) / 2
shapes = []
for i, (lab, ic) in enumerate(cells):
    x = x0 + i * (cw + gap)
    c = card(s, x, 2.3, cw, 2.0)
    icon_chip(s, x + cw / 2 - 0.35, 2.55, 0.7, ic)
    text(s, x + 0.1, 3.45, cw - 0.2, 0.6, [[(lab, 12, LEAF_DEEP, True)]], align=PP_ALIGN.CENTER)
    shapes.append(c)
text(
    s,
    0,
    4.7,
    SW,
    0.4,
    [[("Seeds aren't manufactured parts — they're organic and irregular.", 13, MUTED, False)]],
    align=PP_ALIGN.CENTER,
)
footer(s, 7)
animate_fade(s, shapes, stagger=180)
notes(
    s, "Seeds are organic — overlap, lighting, subtle defects, and healthy-looks-damaged ambiguity."
)

# ---- SLIDE 8 — The Data Problem ----
s = new_slide()
act_tag(s, "Act I · The Problem")
head(s, "The Data Problem")
items = [
    ("bar-chart-3", "Volume Gap", "Need ~100K images; best public sets have <20K"),
    (
        "tags",
        "Annotation Mismatch",
        "Detection sets have boxes but no quality; classification sets have labels but no boxes. None has both.",
    ),
    ("microscope", "Lab ≠ Real World", "Lab-trained models fail on real-world phone photos"),
]
cw, gap = 3.7, 0.3
x0 = (SW - (cw * 3 + gap * 2)) / 2
shapes = []
for i, (ic, ti, de) in enumerate(items):
    x = x0 + i * (cw + gap)
    c = card(s, x, 2.2, cw, 2.5, accent="leaf")
    icon_chip(s, x + 0.25, 2.45, 0.6, ic)
    text(s, x + 0.95, 2.5, cw - 1.1, 0.4, [[(ti, 13, LEAF_DEEP, True)]])
    text(s, x + 0.25, 3.25, cw - 0.5, 1.3, [[(de, 10, MUTED, False)]], line=1.25)
    shapes.append(c)
text(
    s,
    0,
    5.0,
    SW,
    0.4,
    [[("These three problems set up the entire AI journey that follows.", 12, MUTED, False)]],
    align=PP_ALIGN.CENTER,
)
footer(s, 8)
animate_fade(s, shapes, stagger=180)
notes(
    s,
    "Three data problems — volume, annotation mismatch, lab≠real-world — are the seeds of the whole journey.",
)

# ---- SLIDE 9 — Can Machine Learning Solve This? ----
s = new_slide()
act_tag(s, "Act II · From ML to Computer Vision")
head(s, "Can Machine Learning Solve This?")
text(
    s,
    0.9,
    2.0,
    6.0,
    1.0,
    [
        [
            (
                "We began by asking: can we hand-craft features — size, shape, colour, texture ratios — and classify quality with traditional ML?",
                12,
                MUTED,
                False,
            )
        ]
    ],
    line=1.3,
)
stage(s, 0.9, 3.3, 1.7, 0.8, "Seed image", kind="io")
arrow(s, 2.65, 3.5)
stage(s, 3.05, 3.3, 1.9, 0.8, "Measure features", kind="io")
arrow(s, 5.0, 3.5)
stage(s, 5.4, 3.3, 1.6, 0.8, "ML classifier", kind="classify")
w = card(s, 7.4, 2.6, 5.0, 2.2, accent="amber", fill=AMBER_SOFT)
icon_chip(s, 7.65, 2.85, 0.55, "alert-amber", bg=None)
text(
    s,
    8.3,
    2.9,
    3.9,
    1.7,
    [
        [
            ("The discovery: ", 12, LEAF_DEEP, True),
            (
                "seeds are morphologically complex — hand-crafted features can't generalize across species, defects, and environments.",
                12,
                TEXT,
                False,
            ),
        ]
    ],
    line=1.3,
)
footer(s, 9)
animate_fade(s, [w])
notes(
    s,
    "We started honestly with hand-crafted features and classic ML. The discovery: those features don't generalize.",
)

# ---- SLIDE 10 — The Proposed Solution ----
s = new_slide()
act_tag(s, "Act II · From ML to Computer Vision")
head(s, "The Proposed Solution")
text(
    s,
    0.9,
    1.55,
    11.5,
    0.5,
    [
        [
            (
                '"Grade seed quality from an ordinary photo — and manufacture the training data that makes it possible."',
                14,
                LEAF_DEEP,
                True,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
)
c1 = card(s, 0.9, 2.2, 5.6, 2.7, accent="leaf")
icon_chip(s, 1.15, 2.45, 0.6, "sprout")
text(s, 1.85, 2.5, 4.5, 0.4, [[("Seed Bank — the platform", 13, LEAF_DEEP, True)]])
bullets(
    s,
    1.15,
    3.2,
    5.1,
    1.6,
    [
        [
            ("Photo → ", 11, MUTED, False),
            ("find every seed → grade each", 11, LEAF_DEEP, True),
            (" → report", 11, MUTED, False),
        ],
        [
            ("Every verdict ", 11, MUTED, False),
            ("traceable", 11, LEAF_DEEP, True),
            (" to its model", 11, MUTED, False),
        ],
        "Model management + offline evaluation",
        [
            ("A ", 11, MUTED, False),
            ("web + mobile", 11, LEAF_DEEP, True),
            (" app a farmer can use", 11, MUTED, False),
        ],
    ],
)
c2 = card(s, 6.8, 2.2, 5.6, 2.7, accent="leaf")
icon_chip(s, 7.05, 2.45, 0.6, "dna")
text(s, 7.75, 2.5, 4.5, 0.4, [[("MultiSeedGen — the data factory", 13, LEAF_DEEP, True)]])
bullets(
    s,
    7.05,
    3.2,
    5.1,
    1.6,
    [
        "Cut real seeds from single-seed photos",
        [
            ("Composite", 11, LEAF_DEEP, True),
            (" onto realistic backgrounds + camera noise", 11, MUTED, False),
        ],
        [
            ("Export ", 11, MUTED, False),
            ("fully-labelled", 11, LEAF_DEEP, True),
            (" detection datasets", 11, MUTED, False),
        ],
        [("The tool places every seed — labels come for free", 11, INFO, False)],
    ],
)
pill_row(
    s,
    1.9,
    5.15,
    [
        ("No expensive rig — ordinary single-view photos", "dollar-sign"),
        ("Closes the ~100K-image data gap", "database"),
    ],
)
footer(s, 10)
animate_fade(s, [c1, c2], stagger=200)
notes(
    s,
    "The entire solution on one slide — a platform that grades from a normal photo, and a data factory that "
    "generates labelled images. Two problems from earlier — cost and data — one deliverable each.",
)

# ---- SLIDE 11 — Pivoting to Computer Vision ----
s = new_slide()
act_tag(s, "Act II · From ML to Computer Vision")
head(s, "Pivoting to Computer Vision")
st = stage(s, 0.9, 1.95, 4.2, 0.8, "Hand-crafted features → classifier", kind="io")
arrow(s, 5.2, 2.15)
stage(s, 5.7, 1.85, 6.6, 1.0, "Raw image → CNN → learned features → classifier", kind="classify")
text(
    s,
    0,
    3.15,
    SW,
    0.5,
    [
        [
            (
                "Deep learning extracts generalized features automatically — we reframed this as a Computer Vision problem, with two distinct tasks:",
                12,
                MUTED,
                False,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
)
c1 = card(s, 1.6, 3.9, 4.6, 1.3, accent="leaf")
icon_chip(s, 1.85, 4.15, 0.55, "scan")
text(s, 2.55, 4.15, 3.5, 0.4, [[("Task 1 — Where is each seed?", 12, LEAF_DEEP, True)]])
text(s, 2.55, 4.55, 3.5, 0.3, [[("Object Detection", 10, MUTED, False)]])
c2 = card(s, 6.5, 3.9, 4.6, 1.3, accent="leaf")
icon_chip(s, 6.75, 4.15, 0.55, "badge-check")
text(s, 7.45, 4.15, 3.5, 0.4, [[("Task 2 — What's wrong with it?", 12, LEAF_DEEP, True)]])
text(s, 7.45, 4.55, 3.5, 0.3, [[("Quality Classification", 10, MUTED, False)]])
text(
    s,
    0,
    5.4,
    SW,
    0.35,
    [[("▸ This led us to the proposed system architecture — Slides 12–13", 11, INFO, True)]],
    align=PP_ALIGN.CENTER,
)
footer(s, 11)
animate_fade(s, [c1, c2], stagger=200)
notes(
    s,
    "The pivot to deep learning, plus the key reframe: two distinct tasks — where is each seed, and what's wrong with it.",
)

# ---- SLIDE 12 — Proposed System Architecture (1/2) ----
s = new_slide()
act_tag(s, "Act II · From ML to Computer Vision")
head(s, "Proposed System Architecture", "The System at a Glance", amber_suffix="(1/2)")
pieces = [
    ("Clients", "A React web app + an Expo mobile app (English / Arabic)", "clients"),
    (
        "FastAPI backend",
        "Accepts a batch, records it, responds fast — async & cleanly layered",
        "backend",
    ),
    ("Background workers", "The heavy detect → classify work runs off the request path", "workers"),
    ("Datastores", "PostgreSQL · ClickHouse · MinIO · Redis", "datastores"),
]
cx, cw = 0.9, 5.7
cy, ch, gp = 2.35, 0.82, 0.16
for ti, de, ic in pieces:
    card(s, cx, cy, cw, ch, accent="leaf")
    icon_chip(s, cx + 0.2, cy + (ch - 0.52) / 2, 0.52, ic)
    text(
        s,
        cx + 0.95,
        cy + 0.1,
        cw - 1.1,
        ch - 0.2,
        [[(ti, 14, LEAF_DEEP, True)], [(de, 10.5, MUTED, False)]],
        anchor=MSO_ANCHOR.MIDDLE,
        space_after=1.0,
    )
    cy += ch + gp
coy = cy + 0.05
card(s, cx, coy, cw, 0.72, accent="amber", fill=AMBER_SOFT)
text(
    s,
    cx + 0.28,
    coy,
    cw - 0.5,
    0.72,
    [
        [
            (
                "Inference is heavy, so it never runs inside the request the user is waiting on — the API stays responsive.",
                11.5,
                LEAF_DEEP,
                True,
            )
        ]
    ],
    anchor=MSO_ANCHOR.MIDDLE,
)
text(
    s,
    cx,
    coy + 0.82,
    cw,
    0.35,
    [
        [
            (
                "▸ Full container topology at Slide 32 · a live request traced end-to-end at Slide 33",
                10,
                INFO,
                True,
            )
        ]
    ],
)
hero = diagram_card(s, _a("diagrams", "01-system-context.png"), 6.95, 2.35, 5.5, 3.6)
footer(s, 12)
animate_fade(s, [hero])
notes(
    s,
    "The system in one picture. The one idea to land: inference never blocks the user's request. Deep dive in the platform act.",
)

# ---- SLIDE 13 — Proposed System Architecture (2/2) ----
s = new_slide()
act_tag(s, "Act II · From ML to Computer Vision")
head(
    s,
    "Proposed System Architecture",
    "The Two-Stage Detect → Classify Pipeline",
    amber_suffix="(2/2)",
)
py = 2.5
stage(s, 0.6, py, 1.7, 1.0, "Input image", kind="io")
arrow(s, 2.35, py + 0.3)
stage(s, 2.75, py, 2.3, 1.0, "Stage 1 · Detection", "Find every seed + type", kind="detect")
arrow(s, 5.1, py + 0.3)
stage(s, 5.5, py, 1.9, 1.0, "Crop + group", "by seed type", kind="io")
arrow(s, 7.45, py + 0.3)
stage(s, 7.85, py, 2.3, 1.0, "Stage 2 · Classification", "Grade good / bad", kind="classify")
arrow(s, 10.2, py + 0.3)
stage(s, 10.6, py, 2.1, 1.0, "Quality report", kind="io")
text(
    s,
    0.9,
    4.1,
    6.5,
    1.0,
    [
        [
            (
                "One detector for all seeds. One classifier per crop type. Each stage ",
                13,
                TEXT,
                False,
            ),
            ("versioned & optimized independently.", 13, LEAF_DEEP, True),
        ]
    ],
    line=1.3,
)
fan = card(s, 7.9, 4.1, 4.5, 1.2, accent="leaf")
text(
    s,
    8.0,
    4.25,
    4.3,
    0.6,
    [[("1 image → N detections → N labels", 15, LEAF_DEEP, True)]],
    align=PP_ALIGN.CENTER,
)
text(s, 8.0, 4.85, 4.3, 0.3, [[("the data fan-out", 10, MUTED, False)]], align=PP_ALIGN.CENTER)
text(
    s,
    0,
    5.6,
    SW,
    0.35,
    [
        [
            (
                "▸ The engineering behind it — concurrency-safe batching, per-type routing — is at Slide 33",
                11,
                INFO,
                True,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
)
footer(s, 13)
animate_fade(s, [fan])
notes(
    s,
    "The architectural spine of the entire project — detect, then classify — referenced back to repeatedly.",
)

# ---- SLIDE 14 — Phase 1 Detection: Faster R-CNN ----
s = new_slide()
act_tag(s, "Act III · Phase 1 — First Pipeline")
head(s, "Phase 1 Detection: Faster R-CNN")
hero = diagram_card(s, _a("diagrams", "17-fasterRCNN-architecture.png"), 0.9, 2.0, 5.7, 3.6)
text(
    s,
    6.9,
    2.05,
    5.5,
    1.0,
    [
        [
            (
                "ResNet-50 backbone + FPN → region proposals → 3 classes [background, coffee, maize]. YOLOv8 tested alongside — comparable at this stage.",
                12,
                MUTED,
                False,
            )
        ]
    ],
    line=1.3,
)
badge(s, 6.9, 3.2, "0.98", "Faster R-CNN mAP@50", w=2.7)
badge(s, 9.75, 3.2, "0.975", "YOLOv8 mAP@50 · ~30ms", w=2.7)
w = card(s, 6.9, 4.45, 5.55, 1.1, accent="amber", fill=AMBER_SOFT)
text(
    s,
    7.05,
    4.55,
    5.3,
    0.9,
    [
        [
            ("The problem: ", 12, LEAF_DEEP, True),
            (
                "high test metrics, but the model overfitted — it learned the training images, not the concept of 'seed'.",
                12,
                TEXT,
                False,
            ),
        ]
    ],
    line=1.25,
)
footer(s, 14)
animate_fade(s, [hero])
notes(
    s,
    "Phase 1 detection with Faster R-CNN (YOLOv8 alongside). Strong test metrics but overfitting — foreshadow the data problem.",
)

# ---- SLIDE 15 — Phase 1 Classification: ResNet-18 + 4 mods ----
s = new_slide()
act_tag(s, "Act III · Phase 1 — First Pipeline")
head(s, "Phase 1 Classification: ResNet-18 + 4 Custom Modifications")
mods = [
    (
        "zoom-in",
        "1 · Stride → (1,1)",
        "Less downsampling — sees hairline cracks & tiny discolorations",
    ),
    ("eye", "2 · CBAM attention", "Forces focus on defect-relevant regions, not background"),
    ("shuffle", "3 · Hybrid pooling", "GMP + GAP — general patterns AND sharp anomalies"),
    ("binary", "4 · Binary head", "good vs. bad with BCEWithLogitsLoss"),
]
cw, gap = 2.85, 0.22
x0 = (SW - (cw * 4 + gap * 3)) / 2
shapes = []
for i, (ic, ti, de) in enumerate(mods):
    x = x0 + i * (cw + gap)
    c = card(s, x, 2.0, cw, 2.4)
    icon_chip(s, x + 0.2, 2.2, 0.55, ic)
    text(s, x + 0.2, 2.85, cw - 0.4, 0.4, [[(ti, 12, LEAF_DEEP, True)]])
    text(s, x + 0.2, 3.3, cw - 0.4, 1.0, [[(de, 9.5, MUTED, False)]], line=1.2)
    shapes.append(c)
badge(s, 3.0, 4.7, "83.18%", "Maize accuracy · F1 0.769 · Recall 0.889", w=3.6)
badge(s, 6.9, 4.7, "0.910", "Coffee V3 F1 · Recall 0.934", w=3.4)
footer(s, 15)
animate_fade(s, shapes, stagger=160)
notes(
    s,
    "The core AI contribution of Phase 1 — four deliberate modifications to ResNet-18 so it can catch tiny defects.",
)

# ---- SLIDE 16 — Phase 1 Results ----
s = new_slide()
act_tag(s, "Act III · Phase 1 — First Pipeline")
head(s, "Phase 1 Results: What Worked, What Didn't")
c1 = card(s, 0.9, 2.1, 5.6, 3.1, accent="leaf")
icon_chip(s, 1.15, 2.3, 0.5, "check-green", bg=None)
text(s, 1.75, 2.35, 4.5, 0.4, [[("What worked", 14, LEAF, True)]])
bullets(
    s,
    1.15,
    3.0,
    5.1,
    2.0,
    [
        "Detection localized seeds accurately in controlled conditions",
        "ResNet-18 modifications improved classification meaningfully",
        "Two-stage decoupling proved correct — each stage diagnosable alone",
        "Maize performed best — it had the highest-quality dataset",
    ],
    gap=4.0,
)
c2 = card(s, 6.8, 2.1, 5.6, 3.1, accent="amber")
icon_chip(s, 7.05, 2.3, 0.5, "alert-amber", bg=None)
text(s, 7.65, 2.35, 4.5, 0.4, [[("What didn't", 14, AMBER, True)]])
bullets(
    s,
    7.05,
    3.0,
    5.1,
    2.0,
    [
        "Detection overfitted — poor generalization to new images",
        "YOLO performed comparably (same data limitation)",
        "Accuracy decent, but not production-grade",
        [("The dataset was the bottleneck, not the architecture", 11, LEAF_DEEP, True)],
    ],
    gap=4.0,
)
footer(s, 16)
animate_fade(s, [c1, c2], stagger=200)
notes(
    s,
    "Honest scorecard — decoupling worked, maize was best. The punchline: the bottleneck was data, not architecture.",
)

# ---- SLIDE 17 — We Hit a Wall ----
s = new_slide()
act_tag(s, "Act III · Phase 1 — First Pipeline")
head(s, "We Hit a Wall — The Data Insight")
big = text(s, 0, 1.9, SW, 1.0, [[("~100,000", 46, LEAF_DEEP, True)]], align=PP_ALIGN.CENTER)
text(
    s,
    0,
    2.95,
    SW,
    0.5,
    [
        [
            (
                "images per seed type needed to generalize — best public sets have <20,000",
                13,
                MUTED,
                False,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
)
c1 = card(s, 1.6, 3.7, 4.7, 1.6)
text(s, 1.8, 3.85, 4.3, 0.4, [[("The dual problem", 13, LEAF_DEEP, True)]])
text(
    s,
    1.8,
    4.3,
    4.3,
    0.9,
    [
        [
            (
                "Detection sets have boxes but no quality; classification sets have quality but no boxes. No dataset has both.",
                10.5,
                MUTED,
                False,
            )
        ]
    ],
    line=1.25,
)
c2 = card(s, 6.9, 3.7, 4.7, 1.6, accent="leaf")
text(s, 7.1, 3.85, 4.3, 0.4, [[("The decision", 13, LEAF_DEEP, True)]])
text(
    s,
    7.1,
    4.3,
    4.3,
    0.9,
    [
        [
            (
                "Upgrade the classifier → EfficientNet-B2\nBuild our own data → MultiSeedGen",
                11,
                TEXT,
                False,
            )
        ]
    ],
    line=1.3,
)
footer(s, 17)
animate_fade(s, [big])
notes(
    s,
    "The turning point — we need ~100K images per type, and no public set has both boxes and quality labels.",
)

# ---- SLIDE 18 — Phase 2: EfficientNet-B2 ----
s = new_slide()
act_tag(s, "Act IV · Phase 2 — Deeper Models + MultiSeedGen")
head(s, "Phase 2: Upgrading to EfficientNet-B2")
hero = diagram_card(s, _a("diagrams", "18-Efficient-net-B2.png"), 0.9, 2.0, 5.7, 3.6)
text(
    s,
    6.9,
    2.05,
    5.5,
    1.0,
    [
        [
            (
                "Same Faster R-CNN detector; swapped ResNet-18 → EfficientNet-B2. CBAM + hybrid pooling retained (→ 1024 features).",
                12,
                MUTED,
                False,
            )
        ]
    ],
    line=1.3,
)
text(
    s,
    6.9,
    3.15,
    5.5,
    0.7,
    [
        [
            ("Now 7-class multi-label: ", 11, LEAF_DEEP, True),
            (
                "Broken · Damage · Fungus · Healthy · Immature · Shriveled · Weeveled",
                10.5,
                MUTED,
                False,
            ),
        ]
    ],
    line=1.25,
)
badge(s, 6.9, 4.0, "0.769", "ResNet-18 Maize F1", amber=True, w=2.7)
badge(s, 9.75, 4.0, "0.974", "EfficientNet-B2 Macro-F1", w=2.7)
footer(s, 18)
animate_fade(s, [hero])
notes(
    s,
    "EfficientNet-B2 replaces ResNet-18, keeps CBAM + hybrid pooling, and goes from binary to 7-class multi-label. Land 0.769 → 0.974.",
)

# ---- SLIDE 19 — Grad-CAM heatmaps ----
s = new_slide()
act_tag(s, "Act IV · Phase 2 — Deeper Models + MultiSeedGen")
text(
    s,
    0.9,
    0.9,
    11.6,
    0.6,
    [
        [
            ("EfficientNet-B2 + CBAM learns a ", 19, LEAF_DEEP, True),
            ("different attention pattern", 19, AMBER, True),
            (" for each defect class", 19, LEAF_DEEP, True),
        ]
    ],
)
rows = [
    ("Damage", "focuses on the dark lesion", "damage.png"),
    ("Healthy", "uniform activation across the clean surface", "healthy.png"),
    ("Shriveled", "focus on the wrinkled deformation", "shriveled.png"),
    ("Weeveled", "concentrated hotspot on the bore-hole", "weeveled.png"),
]
ry, rh, rgap, rw, rx = 1.75, 1.2, 0.1, 12.0, 0.66
shapes = []
for name, blurb, fn in rows:
    c = rrect(s, rx, ry, rw, rh, CARDBG, line_color=BORDER, radius=0.06)
    text(
        s,
        rx + 0.25,
        ry + 0.06,
        rw - 0.5,
        0.3,
        [
            [
                (name + "  ", 11, LEAF_DEEP, True),
                ("1.00", 11, AMBER, True),
                ("  — " + blurb, 11, MUTED, False),
            ]
        ],
    )
    picture_fit(s, _a("heatmaps", fn), rx + 0.25, ry + 0.38, rw - 0.5, rh - 0.48, valign="top")
    shapes.append(c)
    ry += rh + rgap
text(
    s,
    0,
    ry + 0.02,
    SW,
    0.35,
    [
        [
            (
                "The attention mechanism isn't guessing — it's looking at the right features.",
                10.5,
                MUTED,
                False,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
)
footer(s, 19)
animate_fade(s, shapes, stagger=200)
notes(
    s,
    "The show-stopper — Grad-CAM proves the attention mechanism focuses on the actual defect for each class, not the background.",
)

# ---- SLIDE 20 — Detection Still Overfits ----
s = new_slide()
act_tag(s, "Act IV · Phase 2 — Deeper Models + MultiSeedGen")
head(s, "Detection Still Overfits — We Need Our Own Data")
text(
    s,
    0.9,
    1.9,
    11.5,
    0.6,
    [
        [
            (
                "EfficientNet-B2 solved classification. But object detection still overfitted — the models memorized training images instead of learning 'what a seed looks like.'",
                12,
                MUTED,
                False,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
    line=1.3,
)
notesx = [
    ("Need ~100K annotated images per type",),
    ("Manual bounding-box annotation is prohibitively slow & error-prone",),
    ("Public datasets are lab-only — don't match the real world",),
]
cw, gap = 3.7, 0.3
x0 = (SW - (cw * 3 + gap * 2)) / 2
for i, (de,) in enumerate(notesx):
    x = x0 + i * (cw + gap)
    card(s, x, 2.9, cw, 1.1)
    text(
        s,
        x + 0.25,
        3.05,
        cw - 0.5,
        0.8,
        [[(de, 10.5, MUTED, False)]],
        anchor=MSO_ANCHOR.MIDDLE,
        line=1.25,
    )
w = card(s, 1.9, 4.25, 9.5, 1.2, accent="amber", fill=AMBER_SOFT)
icon_chip(s, 2.2, 4.55, 0.6, "dna", bg=None)
text(
    s,
    2.95,
    4.35,
    8.3,
    1.0,
    [
        [
            (
                "We built MultiSeedGen — a synthetic data factory generating unlimited, perfectly-labelled detection data",
                14,
                LEAF_DEEP,
                True,
            )
        ]
    ],
    anchor=MSO_ANCHOR.MIDDLE,
    line=1.25,
)
footer(s, 20)
animate_fade(s, [w])
notes(
    s,
    "Classification is solved; detection still overfits, and manual annotation can't scale. That's why we built MultiSeedGen.",
)

# ---- SLIDE 21 — MultiSeedGen ----
s = new_slide()
act_tag(s, "Act IV · Phase 2 — Deeper Models + MultiSeedGen")
head(s, "MultiSeedGen: Building Our Own Training Data")
py = 1.9
stages21 = [
    ("Single-seed photos", None, "io", 2.0),
    ("Segment", None, "classify", 1.3),
    ("Composite", "collision physics", "classify", 1.6),
    ("Degrade", "camera sim", "detect", 1.4),
    ("Export", "YOLO / COCO", "io", 1.5),
]
cx = 0.7
for i, (lab, sub, kind, w) in enumerate(stages21):
    stage(s, cx, py, w, 0.85, lab, sub, kind=kind)
    cx += w
    if i < len(stages21) - 1:
        arrow(s, cx, py + 0.22)
        cx += 0.35
hero = diagram_card(
    s, _a("screenshots", "MultiseedGen-seeds_annotatedWithBB.jpg"), 0.9, 3.0, 5.8, 2.9
)
w = card(s, 7.0, 3.0, 5.4, 1.1, accent="amber", fill=AMBER_SOFT)
text(
    s,
    7.2,
    3.15,
    5.0,
    0.85,
    [
        [
            ("Labels come for free", 12, LEAF_DEEP, True),
            (
                " — the engine placed each seed, so it knows exactly where every one is.",
                12,
                TEXT,
                False,
            ),
        ]
    ],
    anchor=MSO_ANCHOR.MIDDLE,
    line=1.25,
)
pill_row(s, 7.0, 4.35, [("6 segmentation backends",), ("15+ augmentation params",)])
pill_row(s, 7.0, 4.9, [("byte-reproducible",), ("~20 species",)])
footer(s, 21)
animate_fade(s, [hero])
notes(
    s,
    "MultiSeedGen is a synthetic data factory — the killer property is that labels are free, because the engine placed each seed.",
)

# ---- SLIDE 22 — Segmentation ----
s = new_slide()
act_tag(s, "Act IV · Phase 2 — Deeper Models + MultiSeedGen")
head(s, "Segmentation: 6 Ways to Cut a Seed")
methods = [
    "auto — classical cascade + confidence gate + rembg fallback",
    "threshold — border-colour distance (clean backgrounds)",
    "otsu — grayscale Otsu (high-contrast)",
    "grabcut — OpenCV GrabCut (textured backgrounds)",
    "rembg (U²-Net) — learned ONNX, GPU-capable",
    "SAM — prompt-driven: auto, box, or point",
]
my = 2.0
for i, m in enumerate(methods):
    card(s, 0.9, my, 5.7, 0.6)
    n = rrect(s, 1.05, my + 0.13, 0.34, 0.34, LEAF, radius=0.5)
    tf = n.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = str(i + 1)
    r.font.name = FONT
    r.font.size = Pt(10)
    r.font.bold = True
    r.font.color.rgb = WHITE
    text(s, 1.55, my, 5.0, 0.6, [[(m, 10, TEXT, False)]], anchor=MSO_ANCHOR.MIDDLE)
    my += 0.68
hero = diagram_card(s, _a("screenshots", "seg-tuner.png"), 6.9, 2.0, 5.5, 3.4)
text(
    s,
    0,
    6.15,
    SW,
    0.35,
    [
        [
            (
                "Content-hash cached — the first pass is the only cost. Per-source override via segment-map.",
                11,
                MUTED,
                False,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
)
footer(s, 22)
animate_fade(s, [hero])
notes(
    s,
    "Six segmentation backends, from thresholding to Segment Anything, chosen per image with a tuner UI. Group as classical → learned → promptable.",
)

# ---- SLIDE 23 — Augmentation & Domain Bridging ----
s = new_slide()
act_tag(s, "Act IV · Phase 2 — Deeper Models + MultiSeedGen")
head(s, "Augmentation & Domain Bridging")
cols = [
    (
        "rotate-cw",
        "Geometric",
        [
            "Scale jitter · rotation · flip",
            "Shear · perspective warp",
            "Collision-aware placement (IoU reject)",
        ],
        None,
    ),
    (
        "camera",
        "Photometric",
        [
            "Sensor noise (Gaussian + Poisson)",
            "JPEG artifacts · motion blur",
            "Gamma + directional drop shadows",
        ],
        None,
    ),
    (
        "mountain",
        "Domain matching",
        [
            "bg_from_sources — real inpainted trays (biggest lever)",
            "neg_frac — 10% negatives",
            "val_seed_holdout · determinism",
        ],
        "amber",
    ),
]
cw, gap = 3.8, 0.28
x0 = (SW - (cw * 3 + gap * 2)) / 2
shapes = []
for i, (ic, ti, its, acc) in enumerate(cols):
    x = x0 + i * (cw + gap)
    c = card(s, x, 2.0, cw, 2.9, accent=acc, fill=AMBER_SOFT if acc else CARDBG)
    icon_chip(s, x + 0.2, 2.2, 0.5, ic, bg=None if acc else LEAF_SOFT)
    text(s, x + 0.8, 2.25, cw - 0.9, 0.4, [[(ti, 13, LEAF_DEEP, True)]])
    bullets(s, x + 0.25, 3.0, cw - 0.5, 1.7, its, size=10, gap=3.0)
    shapes.append(c)
text(
    s,
    0,
    5.15,
    SW,
    0.4,
    [
        [
            (
                "Compositing onto real tray backgrounds was the single biggest quality lever.",
                12,
                MUTED,
                False,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
)
footer(s, 23)
animate_fade(s, shapes, stagger=180)
notes(
    s,
    "Augmentation plus domain bridging — the single biggest lever was compositing onto real tray backgrounds.",
)

# ---- SLIDE 24 — Web UI + Data Loop ----
s = new_slide()
act_tag(s, "Act IV · Phase 2 — Deeper Models + MultiSeedGen")
head(s, "MultiSeedGen Web UI + Data Loop")
c1 = card(s, 0.9, 2.0, 5.6, 3.0, accent="leaf")
icon_chip(s, 1.15, 2.25, 0.55, "monitor")
text(s, 1.85, 2.3, 4.5, 0.4, [[("Its own Web UI", 13, LEAF_DEEP, True)]])
text(
    s,
    1.85,
    2.72,
    4.5,
    0.3,
    [[("React + TypeScript + Tailwind, served by FastAPI", 9.5, MUTED, False)]],
)
bullets(
    s,
    1.15,
    3.4,
    5.1,
    1.5,
    [
        "Run tab — config form + live WebSocket logs",
        "Seg-tuner — per-method preview + quality scoring",
        "Dataset browser · config presets (YAML)",
    ],
    size=10.5,
    gap=3.0,
)
loop = [
    "Generate training data",
    "Models train on it",
    "Real-world edge cases found",
    "Fed back into augmentation",
]
kinds = ["classify", "detect", "io", "io"]
ly = 2.0
for i, (lab, k) in enumerate(zip(loop, kinds)):
    stage(s, 7.6, ly, 4.2, 0.62, lab, kind=k)
    ly += 0.62
    if i < 3:
        text(s, 7.6, ly - 0.02, 4.2, 0.28, [[("↓", 13, MUTED, True)]], align=PP_ALIGN.CENTER)
        ly += 0.24
text(
    s,
    0,
    5.25,
    SW,
    0.4,
    [
        [
            (
                "Each turn of this loop targets the generator at the system's measured weaknesses.",
                12,
                MUTED,
                False,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
)
footer(s, 24)
animate_fade(s, [c1])
notes(
    s,
    "MultiSeedGen is a full tool with its own web UI, and the data feedback loop aims the generator at measured weaknesses.",
)

# ---- SLIDE 25 — Detection Journey ----
s = new_slide()
act_tag(s, "Act V · Final Results & Evidence")
head(s, "Detection Experiments: The Full Journey")
steps = [
    (
        "1",
        "Swin Transformer + FPN",
        "overfitted (too powerful for small data)",
        "0.949",
        "alert-amber",
    ),
    ("2", "+ CIoU loss", "better box regression, still overfitting", "0.981", None),
    (
        "3",
        "ResNet-50 + Faster R-CNN",
        "lower metric, better real-world generalization",
        "0.870",
        "check-green",
    ),
    ("4", "+ PANet", "improved localization at stricter IoU", "0.852", None),
    ("5", "YOLOv8", "fast + accurate, best all-round", "0.975", "star-amber"),
]
my = 2.0
shapes = []
for num, ti, de, m, ic in steps:
    c = card(s, 0.9, my, 11.5, 0.66)
    n = rrect(s, 1.05, my + 0.16, 0.34, 0.34, LEAF, radius=0.5)
    tf = n.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = num
    r.font.name = FONT
    r.font.size = Pt(10)
    r.font.bold = True
    r.font.color.rgb = WHITE
    text(s, 1.6, my, 4.0, 0.66, [[(ti, 11, LEAF_DEEP, True)]], anchor=MSO_ANCHOR.MIDDLE)
    if ic:
        icon_chip(s, 5.5, my + 0.13, 0.4, ic, bg=None)
    text(s, 6.05, my, 5.0, 0.66, [[(de, 10, MUTED, False)]], anchor=MSO_ANCHOR.MIDDLE)
    text(
        s,
        11.0,
        my,
        1.2,
        0.66,
        [[("mAP " + m, 12, LEAF_DEEP, True)]],
        anchor=MSO_ANCHOR.MIDDLE,
        align=PP_ALIGN.RIGHT,
    )
    shapes.append(c)
    my += 0.74
text(
    s,
    0,
    my + 0.05,
    SW,
    0.4,
    [
        [
            ("Lower test metrics ≠ worse model.", 12, LEAF_DEEP, True),
            (
                " After MultiSeedGen, detection trained on 40 seed types with great performance.",
                12,
                MUTED,
                False,
            ),
        ]
    ],
    align=PP_ALIGN.CENTER,
)
footer(s, 25)
animate_fade(s, shapes, stagger=140)
notes(
    s,
    "The full detection experiment journey — the counter-intuitive lesson: lower test metrics can mean better real-world generalization.",
)

# ---- SLIDE 26 — Data Quality > Architecture ----
s = new_slide()
act_tag(s, "Act V · Final Results & Evidence")
head(s, "Classification: Data Quality > Model Architecture")
c1 = card(s, 0.9, 2.1, 5.6, 2.0, accent="amber")
icon_chip(s, 1.15, 2.3, 0.5, "x-red", bg=None)
text(s, 1.75, 2.35, 4.5, 0.4, [[("Soybean — Lab Data", 13, AMBER, True)]])
text(
    s,
    1.15,
    3.0,
    5.1,
    0.5,
    [[("Sterile backgrounds → ", 11, MUTED, False), ("0.9936 F1", 12, RED, True)]],
)
text(s, 1.15, 3.5, 5.1, 0.4, [[("Overfitted — fails on real images", 10.5, MUTED, False)]])
c2 = card(s, 6.8, 2.1, 5.6, 2.0, accent="leaf")
icon_chip(s, 7.05, 2.3, 0.5, "check-green", bg=None)
text(s, 7.65, 2.35, 4.5, 0.4, [[("Maize — Real-World Data", 13, LEAF, True)]])
text(
    s,
    7.05,
    3.0,
    5.1,
    0.5,
    [[("Natural sunlight, phone captures → ", 11, MUTED, False), ("0.974 F1", 12, LEAF, True)]],
)
text(s, 7.05, 3.5, 5.1, 0.4, [[("Generalizes to the real world", 10.5, MUTED, False)]])
pill_row(
    s,
    2.3,
    4.5,
    [("Epoch 1 · 0.808",), ("Epoch 3 · 0.925",), ("Epoch 5 · 0.964",), ("Epoch 7 · 0.974",)],
)
text(
    s,
    0,
    5.3,
    SW,
    0.4,
    [
        [
            (
                "The model that scored lower on the test set performed better in the real world.",
                12,
                MUTED,
                False,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
)
footer(s, 26)
animate_fade(s, [c1, c2], stagger=200)
notes(
    s,
    "Data quality beats architecture — the real-world maize model generalizes; the sterile-lab soybean model overfits.",
)

# ---- SLIDE 27 — Speed vs Precision ----
s = new_slide()
act_tag(s, "Act V · Final Results & Evidence")
head(s, "Speed vs. Precision: Two Deployment Modes")
c1 = card(s, 0.9, 1.9, 5.6, 1.5, accent="leaf")
icon_chip(s, 1.15, 2.1, 0.55, "target")
text(s, 1.85, 2.15, 4.5, 0.4, [[("Precision Mode", 13, LEAF_DEEP, True)]])
text(s, 1.85, 2.55, 4.5, 0.3, [[("Faster R-CNN + EfficientNet-B2", 10, MUTED, False)]])
pill_row(s, 1.15, 2.95, [("~230ms · 4.3 FPS",), ("QA labs",)])
c2 = card(s, 6.8, 1.9, 5.6, 1.5, accent="leaf")
icon_chip(s, 7.05, 2.1, 0.55, "zap")
text(s, 7.75, 2.15, 4.5, 0.4, [[("Speed Mode", 13, LEAF_DEEP, True)]])
text(s, 7.75, 2.55, 4.5, 0.3, [[("YOLOv8", 10, MUTED, False)]])
pill_row(s, 7.05, 2.95, [("~80ms · 12.5 FPS",), ("Conveyor belts",)])
hero = diagram_card(s, _a("screenshots", "YOLO-realtime.png"), 2.6, 3.6, 8.1, 2.2)
text(
    s,
    0,
    5.9,
    SW,
    0.35,
    [
        [
            (
                "876 seeds detected in one dense frame — a detection-model demo of speed-mode throughput (both run on an RTX 3060).",
                10.5,
                MUTED,
                False,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
)
footer(s, 27)
animate_fade(s, [hero])
notes(
    s,
    "Two deployment modes — precision vs speed. The 876-seed image is a model demo; the product realtime experience is the mobile mode.",
)

# ---- SLIDE 28 — Competitor Landscape ----
s = new_slide()
act_tag(s, "Act V · Final Results & Evidence")
head(s, "Competitor Landscape")
cols = ["Feature", "Seed Bank", "LemnaTec", "PCS Agri Track", "Seedy", "GerminationPrediction"]
rows28 = [
    (
        "Cost",
        [
            ("Low", LEAF),
            ("Very high", RED),
            ("Medium", AMBER),
            ("Subscription", AMBER),
            ("Free", LEAF),
        ],
    ),
    (
        "Accessibility",
        [
            ("Web + Mobile", LEAF),
            ("Custom HW", RED),
            ("Needs internet", AMBER),
            ("iOS only", AMBER),
            ("CLI only", RED),
        ],
    ),
    (
        "Multi-crop",
        [
            ("~20 species", LEAF),
            ("Many", LEAF),
            ("Limited", AMBER),
            ("Good DB", LEAF),
            ("Germination only", RED),
        ],
    ),
    (
        "Defect granularity",
        [
            ("7-class multi", LEAF),
            ("Industrial", LEAF),
            ("Basic", AMBER),
            ("Visual ID", RED),
            ("No quality", RED),
        ],
    ),
    ("Mobile", [("Native app", LEAF), ("No", RED), ("Web", AMBER), ("iOS", LEAF), ("No", RED)]),
    (
        "Open / extensible",
        [
            ("Pluggable", LEAF),
            ("Proprietary", RED),
            ("Proprietary", RED),
            ("Proprietary", RED),
            ("OSS", LEAF),
        ],
    ),
]
tx, ty = 0.9, 2.0
colw = [2.6, 1.9, 1.7, 2.0, 1.5, 2.0]
rh = 0.52
# header
rrect(s, tx, ty, sum(colw), rh, LEAF_SOFT, radius=0.04)
cxx = tx
for i, cn in enumerate(cols):
    text(
        s,
        cxx + 0.12,
        ty,
        colw[i] - 0.15,
        rh,
        [[(cn, 9.5, LEAF_DEEP, True)]],
        anchor=MSO_ANCHOR.MIDDLE,
    )
    cxx += colw[i]
ry = ty + rh
# highlight Seed Bank column
rect(s, tx + colw[0], ry, colw[1], rh * len(rows28), LEAF_SOFT)
for feat, cells in rows28:
    cxx = tx
    text(
        s, cxx + 0.12, ry, colw[0] - 0.15, rh, [[(feat, 9.5, TEXT, True)]], anchor=MSO_ANCHOR.MIDDLE
    )
    cxx += colw[0]
    for j, (val, col) in enumerate(cells):
        text(
            s,
            cxx + 0.12,
            ry,
            colw[j + 1] - 0.15,
            rh,
            [[(val, 9, col, True)]],
            anchor=MSO_ANCHOR.MIDDLE,
        )
        cxx += colw[j + 1]
    ry += rh
text(
    s,
    0,
    ry + 0.1,
    SW,
    0.35,
    [
        [
            (
                "Affordable, accessible, multi-crop, fine-grained, and extensible — the all-green column is Seed Bank.",
                11,
                MUTED,
                False,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
)
footer(s, 28)
notes(
    s,
    "Where we sit — affordable, accessible, multi-crop, fine-grained, and extensible. Highlight the all-green column (us).",
)

# ---- SLIDE 29 — Models to Product ----
s = new_slide()
act_tag(s, "Act VI · The Platform & Engineering")
head(s, "A Model in a Notebook Helps No One")
c1 = card(s, 1.6, 2.4, 3.6, 2.0)
icon_chip(s, 3.1, 2.7, 0.6, "file-text")
text(s, 1.7, 3.5, 3.4, 0.4, [[("Trained model", 13, LEAF_DEEP, True)]], align=PP_ALIGN.CENTER)
text(s, 1.7, 3.95, 3.4, 0.3, [[("a lone .pth file", 10, MUTED, False)]], align=PP_ALIGN.CENTER)
text(s, 5.3, 3.1, 0.7, 0.6, [[("→", 26, MUTED, True)]], align=PP_ALIGN.CENTER)
c2 = card(s, 6.2, 2.4, 5.6, 2.0, accent="leaf")
icon_chip(s, 7.9, 2.7, 0.6, "monitor-smartphone")
icon_chip(s, 8.7, 2.7, 0.6, "users")
text(
    s,
    6.3,
    3.6,
    5.4,
    0.6,
    [[("A platform two audiences use every day", 14, LEAF_DEEP, True)]],
    align=PP_ALIGN.CENTER,
)
pill_row(s, 4.2, 4.9, [("Usable", "hand"), ("Traceable", "link"), ("Secure", "shield")])
footer(s, 29)
animate_fade(s, [c1, c2], stagger=250)
notes(
    s,
    "This is the seam. Everything so far was research; now we turn it into something a farmer and a QA lab actually use.",
)

# ---- SLIDE 30 — App Showcase ----
s = new_slide()
act_tag(s, "Act VI · The Platform & Engineering")
head(s, "Live App Showcase")
shots = [
    ("MobileView.png", "Capture on mobile"),
    ("Dashboard.png", "Review on web"),
    ("web-batch-detail.png", "AI insights + boxes"),
    ("Models_managment.png", "ML platform behind it"),
]
cw, gap = 2.85, 0.22
x0 = (SW - (cw * 4 + gap * 3)) / 2
shapes = []
for i, (fn, cap) in enumerate(shots):
    x = x0 + i * (cw + gap)
    p = diagram_card(s, _a("screenshots", fn), x, 2.0, cw, 3.0, caption=cap)
    shapes.append(p)
text(
    s,
    0,
    5.3,
    SW,
    0.4,
    [
        [
            (
                "Capture → analyze → review the insights — with a whole ML platform behind it.",
                12,
                MUTED,
                False,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
)
footer(s, 30)
animate_fade(s, shapes, stagger=180)
notes(
    s,
    "Walk the real farmer journey — capture, analyze, review the insights — then reveal there's a whole ML platform behind it.",
)

# ---- SLIDE 31 — Two Audiences, Two Languages ----
s = new_slide()
act_tag(s, "Act VI · The Platform & Engineering")
head(s, "One Platform, Two Audiences — in Two Languages")
c1 = card(s, 0.9, 2.0, 5.6, 1.4, accent="leaf")
icon_chip(s, 1.15, 2.25, 0.6, "tractor")
text(s, 1.85, 2.3, 4.5, 0.4, [[("Farmer (end user)", 13, LEAF_DEEP, True)]])
text(
    s,
    1.85,
    2.75,
    4.5,
    0.4,
    [[("Capture · analyze · history · share a read-only report", 10, MUTED, False)]],
)
c2 = card(s, 6.8, 2.0, 5.6, 1.4, accent="leaf")
icon_chip(s, 7.05, 2.25, 0.6, "flask-conical")
text(s, 7.75, 2.3, 4.5, 0.4, [[("AI developer / admin", 13, LEAF_DEEP, True)]])
text(
    s,
    7.75,
    2.75,
    4.5,
    0.4,
    [[("Models · datasets · experiments · user management", 10, MUTED, False)]],
)
w = card(s, 0.9, 3.65, 11.5, 1.5, accent="amber", fill=AMBER_SOFT)
icon_chip(s, 1.2, 4.05, 0.6, "languages", bg=None)
text(
    s,
    1.95,
    3.85,
    10.2,
    0.4,
    [[("Fully bilingual — English + Arabic with complete RTL mirroring", 14, LEAF_DEEP, True)]],
)
text(
    s,
    1.95,
    4.35,
    10.2,
    0.7,
    [
        [
            (
                "Every user-facing string translated; the whole layout flips for Arabic — on web AND mobile, not an afterthought.",
                11,
                MUTED,
                False,
            )
        ]
    ],
    line=1.25,
)
footer(s, 31)
animate_fade(s, [c1, c2, w], stagger=180)
notes(
    s,
    "One platform, two role-gated audiences, fully bilingual EN/AR with mirrored RTL on both web and mobile.",
)

# ---- SLIDE 32 — System Architecture ----
s = new_slide()
act_tag(s, "Act VI · The Platform & Engineering")
head(s, "System Architecture")
d1 = diagram_card(s, _a("diagrams", "02-containers-app.png"), 0.9, 2.0, 3.4, 3.4)
d2 = diagram_card(s, _a("diagrams", "02-containers-datastores.png"), 4.4, 2.0, 3.4, 3.4)
bullets(
    s,
    8.1,
    2.2,
    4.4,
    3.0,
    [
        [
            ("Clients", 11, LEAF_DEEP, True),
            (" — React 18 web + Expo mobile (EN/AR)", 11, MUTED, False),
        ],
        [
            ("Backend", 11, LEAF_DEEP, True),
            (" — FastAPI, async, layered, JWT + RBAC", 11, MUTED, False),
        ],
        [
            ("Datastores", 11, LEAF_DEEP, True),
            (" — PostgreSQL · Redis · MinIO · ClickHouse", 11, MUTED, False),
        ],
        [
            ("Workers", 11, LEAF_DEEP, True),
            (" — worker-inference (torch) · worker-cpu", 11, MUTED, False),
        ],
    ],
    gap=6.0,
)
pill(s, 8.1, 4.7, "7 core services · docker compose up")
text(
    s,
    0,
    5.7,
    SW,
    0.35,
    [
        [
            (
                "The deep dive on the high-level view from Slide 12 — clean layering is why each piece is swappable and testable.",
                10.5,
                MUTED,
                False,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
)
footer(s, 32)
animate_fade(s, [d1, d2], stagger=200)
notes(
    s,
    "The payoff of the high-level architecture from Slide 12 — clean layered design, async end-to-end, seven services with one command.",
)

# ---- SLIDE 33 — Analyze Pipeline ----
s = new_slide()
act_tag(s, "Act VI · The Platform & Engineering")
head(s, "The Analyze Pipeline, End-to-End")
steps33 = [
    "1. POST /analyze — photos + optional metadata",
    "2. Validate → upload to MinIO → create batch → commit",
    "3. Dispatch one background job per image",
    "4. DETECT → CROP → GROUP by type → CLASSIFY each group",
    "5. State machine: pending → running → succeeded / partial / failed",
    "6. Client polls until a terminal status",
]
text(
    s,
    0.9,
    1.75,
    5.7,
    1.7,
    [[(s33, 10.5, TEXT, False)] for s33 in steps33],
    line=1.35,
    space_after=3.0,
)
text(s, 7.0, 1.75, 5.5, 1.7, [[("", 10.5, TEXT, False)]])  # spacer
d1 = diagram_card(
    s, _a("diagrams", "06-analyze-sequence.png"), 0.9, 3.5, 5.7, 2.4, caption="Analyze sequence"
)
d2 = diagram_card(
    s,
    _a("diagrams", "07-batch-state-machine.png"),
    6.8,
    1.75,
    5.6,
    4.15,
    caption="Batch state machine",
)
text(
    s,
    0,
    6.0,
    SW,
    0.35,
    [
        [
            (
                "Concurrency-safe state machine · per-seed-type routing · graceful partial results",
                10.5,
                INFO,
                True,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
)
footer(s, 33)
animate_fade(s, [d1, d2], stagger=200)
notes(
    s,
    "Trace a single analyze request end-to-end — the two-stage pipeline in motion: fan-out, per-type routing, concurrency-safe state machine.",
)

# ---- SLIDE 34 — Traceability & Lifecycle ----
s = new_slide()
act_tag(s, "Act VI · The Platform & Engineering")
head(s, "Model Traceability & Lifecycle")
py = 1.9
stage(s, 2.3, py, 2.6, 0.75, "Seed Detection", kind="io")
text(
    s,
    4.9,
    py + 0.15,
    1.0,
    0.45,
    [[("→ FK →", 11, MUTED, True)]],
    align=PP_ALIGN.CENTER,
    anchor=MSO_ANCHOR.MIDDLE,
)
stage(s, 5.9, py, 2.0, 0.75, "Inference", kind="detect")
text(
    s,
    7.9,
    py + 0.15,
    1.0,
    0.45,
    [[("→ FK →", 11, MUTED, True)]],
    align=PP_ALIGN.CENTER,
    anchor=MSO_ANCHOR.MIDDLE,
)
stage(s, 8.9, py, 2.4, 0.75, "Model Artifact", kind="classify")
text(
    s,
    0,
    2.75,
    SW,
    0.35,
    [
        [
            (
                "Every single verdict traces back to the exact model version that produced it.",
                12,
                INFO,
                False,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
)
life = [
    ("package", "Register", "Upload weights, assign builder, set config"),
    ("flask-conical", "Evaluate", "Offline experiments vs labelled datasets"),
    ("rocket", "Promote", "registered → staging → production → archived"),
]
cw, gap = 3.7, 0.3
x0 = (SW - (cw * 3 + gap * 2)) / 2
shapes = []
for i, (ic, ti, de) in enumerate(life):
    x = x0 + i * (cw + gap)
    c = card(s, x, 3.3, cw, 1.5, accent="leaf")
    icon_chip(s, x + 0.25, 3.55, 0.55, ic)
    text(s, x + 0.9, 3.6, cw - 1.05, 0.4, [[(ti, 13, LEAF_DEEP, True)]])
    text(s, x + 0.25, 4.15, cw - 0.5, 0.6, [[(de, 9.5, MUTED, False)]], line=1.2)
    shapes.append(c)
text(
    s,
    0,
    5.15,
    SW,
    0.4,
    [
        [
            (
                "ModelResolver serves the production model per (kind, seed_type) — swapping the live model is a ",
                10.5,
                MUTED,
                False,
            ),
            ("promotion, not a code change.", 10.5, LEAF_DEEP, True),
        ]
    ],
    align=PP_ALIGN.CENTER,
)
footer(s, 34)
animate_fade(s, shapes, stagger=180)
notes(
    s,
    "The seam back to the AI story — every detection links by FK to the exact model version. Swapping models is a promotion, not a redeploy.",
)

# ---- SLIDE 35 — Secure by Design ----
s = new_slide()
act_tag(s, "Act VI · The Platform & Engineering")
head(s, "Secure by Design")
tiles = [
    (
        "key",
        "JWT + refresh rotation",
        "Short-lived tokens; a reused refresh token invalidates the chain",
    ),
    ("link", "Google OAuth", "Social sign-in alongside email / password"),
    ("users", "Role-based access", "end_user · ai_developer · admin — on every route"),
    (
        "scroll-text",
        "Audit log + one error shape",
        "Append-only trail; consistent typed errors (RFC 9457)",
    ),
]
cw, gap = 2.85, 0.22
x0 = (SW - (cw * 4 + gap * 3)) / 2
shapes = []
for i, (ic, ti, de) in enumerate(tiles):
    x = x0 + i * (cw + gap)
    c = card(s, x, 2.3, cw, 2.6)
    icon_chip(s, x + 0.2, 2.5, 0.6, ic)
    text(s, x + 0.2, 3.25, cw - 0.4, 0.7, [[(ti, 12, LEAF_DEEP, True)]], line=1.1)
    text(s, x + 0.2, 3.95, cw - 0.4, 0.9, [[(de, 9.5, MUTED, False)]], line=1.2)
    shapes.append(c)
footer(s, 35)
animate_fade(s, shapes, stagger=160)
notes(
    s,
    "Security done properly — rotating refresh tokens with replay detection, OAuth, real RBAC, an audit trail, one error contract.",
)

# ---- SLIDE 36 — Tech Stack ----
s = new_slide()
act_tag(s, "Act VI · The Platform & Engineering")
head(s, "Tech Stack at a Glance")
groups = [
    (
        "cpu",
        "AI / ML",
        "PyTorch · torchvision (Faster R-CNN) · EfficientNet-B2 · Ultralytics YOLOv8 · OpenCV · rembg · Pillow · NumPy",
    ),
    ("dna", "MultiSeedGen", "classical-CV + rembg + SAM segmentation · React + FastAPI web UI"),
    (
        "monitor",
        "Web",
        "React 18 · TypeScript · Vite · Tailwind · shadcn/ui · TanStack Query · Zod · openapi-fetch · lucide-react",
    ),
    ("smartphone", "Mobile", "Expo SDK 56 · React Native 0.85 · expo-camera · React Navigation"),
    (
        "server",
        "Backend",
        "FastAPI · Python 3.12 · Celery · SQLAlchemy 2 (async) · Pydantic v2 · Alembic",
    ),
    ("database", "Data", "PostgreSQL 16 · ClickHouse · Redis 7 · MinIO"),
    ("box", "Infra", "Docker · multi-stage Dockerfile (CPU / GPU) · nginx"),
    ("lock", "Security", "JWT + refresh rotation · OAuth (Google) · RBAC"),
]
gy = 1.95
for ic, grp, items in groups:
    icon_chip(s, 0.9, gy, 0.5, ic)
    text(s, 1.6, gy, 1.9, 0.5, [[(grp, 11, LEAF_DEEP, True)]], anchor=MSO_ANCHOR.MIDDLE)
    text(s, 3.5, gy, 8.9, 0.5, [[(items, 10, MUTED, False)]], anchor=MSO_ANCHOR.MIDDLE)
    gy += 0.62
footer(s, 36)
notes(
    s,
    "A quick grouped inventory — let it convey breadth and coherence. SAM lives in MultiSeedGen, our data tool, not the runtime backend.",
)

# ---- SLIDE 37 — Key Takeaways ----
s = new_slide()
act_tag(s, "Act VII · Closing")
head(s, "Key Takeaways")
tk = [
    (
        "bar-chart-3",
        "Data quality > architecture",
        "The maize model won because its training data matched the real world.",
    ),
    (
        "git-branch",
        "Decouple detection from classification",
        "Independent stages let us diagnose and swap each without disturbing the other.",
    ),
    (
        "factory",
        "Synthetic data narrows the gap",
        "MultiSeedGen removed the annotation bottleneck — but always test on real photos.",
    ),
]
cw, gap = 3.7, 0.3
x0 = (SW - (cw * 3 + gap * 2)) / 2
shapes = []
for i, (ic, ti, de) in enumerate(tk):
    x = x0 + i * (cw + gap)
    c = card(s, x, 2.3, cw, 2.6, accent="leaf")
    icon_chip(s, x + 0.25, 2.55, 0.6, ic)
    text(s, x + 0.25, 3.3, cw - 0.5, 0.8, [[(ti, 12.5, LEAF_DEEP, True)]], line=1.1)
    text(s, x + 0.25, 4.05, cw - 0.5, 0.9, [[(de, 10, MUTED, False)]], line=1.25)
    shapes.append(c)
footer(s, 37)
animate_fade(s, shapes, stagger=180)
notes(
    s,
    "Three durable lessons — data > architecture, decouple the two stages, synthetic data narrows the gap but real evaluation is the only fair test.",
)

# ---- SLIDE 38 — Future Roadmap ----
s = new_slide()
act_tag(s, "Act VII · Closing")
head(s, "Future Roadmap")
road = [
    ("sprout", "More Crops", "expand real-world datasets for all 20+ species"),
    ("cpu", "Edge AI", "on-device quantized inference, no internet needed"),
    ("refresh-cw", "Active Learning", "low-confidence scans feed back into MultiSeedGen"),
    (
        "factory",
        "Hardware-Integrated Conveyor",
        "realtime already ships on mobile; next is fixed-camera lines + instance segmentation",
    ),
]
my = 2.1
shapes = []
for ic, ti, de in road:
    c = card(s, 1.6, my, 10.1, 0.8, accent="leaf")
    icon_chip(s, 1.8, my + 0.15, 0.5, ic)
    text(s, 2.5, my, 3.3, 0.8, [[(ti, 12.5, LEAF_DEEP, True)]], anchor=MSO_ANCHOR.MIDDLE)
    text(s, 5.9, my, 5.6, 0.8, [[(de, 10.5, MUTED, False)]], anchor=MSO_ANCHOR.MIDDLE, line=1.2)
    shapes.append(c)
    my += 0.95
footer(s, 38)
animate_fade(s, shapes, stagger=160)
notes(
    s,
    "Future work — more crops, edge AI, active learning; realtime already ships, so the frontier is conveyor lines + instance segmentation.",
)

# ---- SLIDE 39 — Thank You ----
s = new_slide()
t = text(
    s,
    0,
    2.2,
    SW,
    1.0,
    [[("Thank You", 52, LEAF_DEEP, True)]],
    align=PP_ALIGN.CENTER,
    anchor=MSO_ANCHOR.MIDDLE,
)
text(s, 0, 3.3, SW, 0.5, [[("Questions?", 22, LEAF, True)]], align=PP_ALIGN.CENTER)
team_chip = None  # (redefine locally below)


def _tc(cx, nw, label, names):
    chip = rrect(s, cx, 4.2, 0.42, 0.3, LEAF, radius=0.3)
    tf = chip.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.name = FONT
    r.font.size = Pt(10)
    r.font.bold = True
    r.font.color.rgb = WHITE
    text(s, cx + 0.5, 4.18, nw, 0.35, [[(names, 11, TEXT, False)]], anchor=MSO_ANCHOR.MIDDLE)


_tc(1.35, 4.6, "AI", "Omar Ez-Eldin Abdullah · Yussuf Ahmed Awad")
_tc(6.85, 5.6, "IS", "Ali Abdelrahman · Mohamed Amr · Youssef Tarek Ali")
text(
    s,
    0,
    4.95,
    SW,
    0.4,
    [
        [
            (
                "Special thanks to Dr. Ali Zidane · Dr. Ghada Dahy · Dr. Heba Sherif · Dr. Eman Ahmed",
                11,
                MUTED,
                False,
            )
        ]
    ],
    align=PP_ALIGN.CENTER,
)
picture_fit(s, _a("logos", "Cairo_University_new_logo.png"), 5.55, 5.6, 0.9, 0.9, valign="top")
picture_fit(s, _a("logos", "FCAI.jpg"), 6.75, 5.6, 1.05, 0.9, valign="top")
footer(s, 39)
animate_fade(s, [t])
notes(
    s,
    "Thank the supervisors, credit both sub-teams explicitly (research and engineering), and open the floor warmly.",
)

out = os.path.join(HERE, "seed-bank.pptx")
prs.save(out)
print("saved", out, "|", len(prs.slides._sldIdLst), "slides")
