#!/usr/bin/env python3
"""
main.py  —  Queso Ventures Audit  (v13)
Usage:  source .env && python main.py

Spacing model:
  - Every section height is measured before drawing.
  - Total content height is summed.
  - Remaining vertical space is divided evenly between all inter-section gaps.
  - Result: content fills the page naturally with uniform breathing room.
  - Minimum gap enforced at 8pt so nothing ever crams together.
"""

import os
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from NewaiAudit import (
    get_competitor_rows,
    get_competitor_takeaway,
    get_findings,
    get_outcome,
    get_differentiator,
    get_cta_headline,
)

# ─────────────────────────────────────────────
#  BRAND
# ─────────────────────────────────────────────
C_BLACK  = colors.HexColor("#1A1A1A")
C_WHITE  = colors.HexColor("#FFFFFF")
C_GRAY   = colors.HexColor("#767676")
C_LGRAY  = colors.HexColor("#D8D8D4")
C_DGRAY  = colors.HexColor("#3A3A3A")
C_RED    = colors.HexColor("#C4161C")
C_ORANGE = colors.HexColor("#D4720A")
C_GREEN  = colors.HexColor("#1A7A3C")

PAGE_W, PAGE_H = letter
PAD = 38

CONTACT_EMAIL = "hello@quesoventures.com"
CONTACT_PHONE = "(281) 203-4531"
CONTACT_SITE  = "quesoventures.com"

LOGO_URL  = "https://www.quesoventures.com/logo.png"
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".qv_logo.png")

# CTA footer: light rule + 3 text lines, pinned near bottom
CTA_RULE_Y  = 48    # y of the rule from page bottom
CTA_LINES   = 3     # headline + phone + email
CTA_LINE_H  = 14

# Section label height
SEC_LABEL_H = 8     # label text + gap below it

# Minimum and maximum inter-section gaps
GAP_MIN = 10
GAP_MAX = 22


def ensure_logo():
    if os.path.exists(LOGO_PATH):
        return LOGO_PATH
    try:
        import requests
        r = requests.get(LOGO_URL, timeout=10)
        if r.status_code == 200:
            with open(LOGO_PATH, "wb") as f: f.write(r.content)
            return LOGO_PATH
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────
#  PRIMITIVES
# ─────────────────────────────────────────────
def rrect(c, x, y, w, h, r=6, fill=None, stroke=None, sw=0.5):
    if fill:   c.setFillColor(fill)
    if stroke: c.setStrokeColor(stroke); c.setLineWidth(sw)
    else:      c.setLineWidth(0)
    p = c.beginPath()
    p.moveTo(x+r, y);          p.lineTo(x+w-r, y)
    p.arcTo(x+w-2*r, y,        x+w,    y+2*r,    startAng=-90, extent=90)
    p.lineTo(x+w, y+h-r)
    p.arcTo(x+w-2*r, y+h-2*r, x+w,    y+h,      startAng=0,   extent=90)
    p.lineTo(x+r, y+h)
    p.arcTo(x,    y+h-2*r,    x+2*r,  y+h,      startAng=90,  extent=90)
    p.lineTo(x, y+r)
    p.arcTo(x,    y,           x+2*r,  y+2*r,   startAng=180, extent=90)
    p.close()
    c.drawPath(p, fill=1 if fill else 0, stroke=1 if stroke else 0)


def wraptext(c, txt, x, y, maxw, font="Helvetica", size=9, color=C_DGRAY, lh=13):
    c.setFont(font, size); c.setFillColor(color)
    words = txt.split(); line = ""; cy = y
    for w in words:
        t = (line + " " + w).strip()
        if c.stringWidth(t, font, size) <= maxw: line = t
        else:
            if line: c.drawString(x, cy, line); cy -= lh
            line = w
    if line: c.drawString(x, cy, line); cy -= lh
    return cy


def texth(c, txt, maxw, font="Helvetica", size=9, lh=13):
    words = txt.split(); lines = 1; line = ""
    for w in words:
        t = (line + " " + w).strip()
        if c.stringWidth(t, font, size) <= maxw: line = t
        else: lines += 1; line = w
    return lines * lh


def sec_label(c, x, y, txt):
    c.setFont("Helvetica-Bold", 7.5); c.setFillColor(C_DGRAY)
    c.drawString(x, y, txt.upper())


def hrule(c, x, y, w, color=C_LGRAY, lw=0.4):
    c.setStrokeColor(color); c.setLineWidth(lw); c.line(x, y, x + w, y)


def draw_gauge(c, cx, cy, pct, r=22):
    c.setStrokeColor(C_LGRAY); c.setLineWidth(4)
    c.arc(cx-r, cy-r, cx+r, cy+r, startAng=200, extent=-220)
    col = C_RED if pct < 40 else C_ORANGE if pct < 68 else C_GREEN
    c.setStrokeColor(col); c.setLineWidth(4)
    c.arc(cx-r, cy-r, cx+r, cy+r, startAng=200, extent=-(pct/100*220))
    c.setFont("Helvetica-Bold", 15); c.setFillColor(col)
    c.drawCentredString(cx, cy - 4, f"{pct}%")
    c.setFont("Helvetica", 6.5); c.setFillColor(C_GRAY)
    c.drawCentredString(cx, cy - 14, "Visibility Score")


CHIP_W = 86; CHIP_H = 22; CHIP_R = 4

def draw_chip(c, cx, cell_y, cell_h, text, good):
    if text in ("N/A", "?"):  border = C_LGRAY; tcol = C_GRAY
    elif text == "Sometimes": border = C_ORANGE; tcol = C_ORANGE
    elif good:                border = C_GREEN;  tcol = C_GREEN
    else:                     border = C_RED;    tcol = C_RED
    chip_x = cx - CHIP_W / 2
    chip_y = cell_y + (cell_h - CHIP_H) / 2
    rrect(c, chip_x, chip_y, CHIP_W, CHIP_H, r=CHIP_R, fill=C_WHITE, stroke=border, sw=1.2)
    c.setFont("Helvetica-Bold", 9); c.setFillColor(tcol)
    c.drawCentredString(cx, chip_y + CHIP_H/2 - 3.5, text)


# ─────────────────────────────────────────────
#  MEASURE all section heights before drawing
# ─────────────────────────────────────────────
def measure_sections(cv, iw, data, comp_rows, findings, out_head, out_buls, diff_head, diff_buls):
    """
    Returns dict of section_name -> pixel height.
    All heights measured from content only — gaps not included.
    """
    heights = {}

    # 1. Header — fixed
    heights["header"] = 64

    # 2. Stack up = plates + col headers + 3 rows + takeaway
    PLATE_H    = 42
    COL_HDR_H  = 18
    COMP_ROW_H = 34
    TK_H       = 48
    heights["stackup"] = (
        SEC_LABEL_H + PLATE_H + COL_HDR_H +
        len(comp_rows) * COMP_ROW_H + 8 + TK_H
    )

    # 3. Findings
    finding_total = SEC_LABEL_H
    for f in findings:
        fh = texth(cv, f, iw - 26, font="Helvetica", size=8.5, lh=13) + 22
        finding_total += fh + 6
    heights["findings"] = finding_total

    # 4. How Searching Works Now
    LINE_H = 16
    heights["outcome"] = SEC_LABEL_H + 16 + len(out_buls) * LINE_H + 14

    # 5. Differentiator — base only; slack absorbed at draw time
    DIFF_LINE_H = 16
    heights["diff"] = 18 + 10 + len(diff_buls) * DIFF_LINE_H + 14

    return heights


# ─────────────────────────────────────────────
#  BUILD PDF
# ─────────────────────────────────────────────
def build_pdf(data, output_path):
    logo = ensure_logo()
    cv   = canvas.Canvas(output_path, pagesize=letter)
    iw   = PAGE_W - 2 * PAD
    term = data.get("industry_term", "customer")

    cv.setFillColor(C_WHITE); cv.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    from NewwebAudit import calc_visibility_score
    vis_pct = data.get("visibility_pct", calc_visibility_score(data))

    comp_rows            = get_competitor_rows(
        data["comp_name"], data["review_count"], data["comp_reviews"], term,
        data.get("visibility_score", 1), data.get("comp_vis_score", 5),
        data.get("geo_score", 1),        data.get("comp_geo_score", 5),
    )
    tk_line1, tk_line2   = get_competitor_takeaway(data.get("featured_query", ""), term)
    findings             = data.get("_findings", get_findings(data))
    out_head, out_buls   = get_outcome(data)
    diff_head, diff_buls = get_differentiator(term)
    bname                = data["business_name"]
    city                 = data.get("business_city", "")

    # ── measure ──────────────────────────────────────────────────────────────
    hts = measure_sections(cv, iw, data, comp_rows, findings,
                           out_head, out_buls, diff_head, diff_buls)

    # Available vertical space: from top margin to CTA rule, minus header
    TOP_MARGIN    = 14
    usable_h      = PAGE_H - TOP_MARGIN - hts["header"] - (PAGE_H - CTA_RULE_Y) - 4
    content_h     = hts["stackup"] + hts["findings"] + hts["outcome"] + hts["diff"]
    n_gaps        = 4   # gaps: after header, after stackup, after findings, after outcome
    gap           = max(GAP_MIN, min(GAP_MAX, (usable_h - content_h) / n_gaps))

    # ── draw ─────────────────────────────────────────────────────────────────
    cursor = PAGE_H - TOP_MARGIN

    # ═══════════════════════════════════════════════════════
    #  1. HEADER
    # ═══════════════════════════════════════════════════════
    HDR_H    = hts["header"]
    GAUGE_R  = 22
    GAUGE_CX = PAGE_W / 2
    LEFT_MAX_W = GAUGE_CX - GAUGE_R - 12 - (PAD + 14)

    cursor -= HDR_H
    rrect(cv, PAD, cursor, iw, HDR_H, r=8, fill=C_WHITE, stroke=C_LGRAY, sw=0.8)
    draw_gauge(cv, GAUGE_CX, cursor + HDR_H - 30, vis_pct, r=GAUGE_R)

    # Left — name
    name_y = cursor + HDR_H - 19
    sub_y  = cursor + HDR_H - 33
    ns = 15
    while cv.stringWidth(bname, "Helvetica-Bold", ns) > LEFT_MAX_W and ns > 9:
        ns -= 0.5
    dn = bname
    if cv.stringWidth(dn, "Helvetica-Bold", ns) > LEFT_MAX_W:
        while cv.stringWidth(dn + "\u2026", "Helvetica-Bold", ns) > LEFT_MAX_W and len(dn) > 4:
            dn = dn[:-1]
        dn += "\u2026"
    cv.setFont("Helvetica-Bold", ns); cv.setFillColor(C_BLACK)
    cv.drawString(PAD + 14, name_y, dn)
    cv.setFont("Helvetica", 8); cv.setFillColor(C_GRAY)
    cv.drawString(PAD + 14, sub_y, city)
    cv.setFont("Helvetica", 7.5); cv.setFillColor(C_GRAY)
    cv.drawString(PAD + 14, sub_y - 13,
                  data.get("audit_date", date.today().strftime("%B %d, %Y")))

    # Right — QV brand
    re  = PAD + iw - 14
    qvw = cv.stringWidth("Queso Ventures", "Helvetica-Bold", 9.5)
    RIGHT_ZONE_X = GAUGE_CX + GAUGE_R + 12
    if logo:
        LW = LH = 14
        bx = re - LW - 5 - qvw
        if bx >= RIGHT_ZONE_X:
            cv.drawImage(logo, bx, name_y - 2, width=LW, height=LH,
                         preserveAspectRatio=True, mask="auto")
            cv.setFont("Helvetica-Bold", 9.5); cv.setFillColor(C_BLACK)
            cv.drawString(bx + LW + 5, name_y, "Queso Ventures")
        else:
            cv.setFont("Helvetica-Bold", 9.5); cv.setFillColor(C_BLACK)
            cv.drawRightString(re, name_y, "Queso Ventures")
    else:
        cv.setFont("Helvetica-Bold", 9.5); cv.setFillColor(C_BLACK)
        cv.drawRightString(re, name_y, "Queso Ventures")
    cv.setFont("Helvetica-Bold", 8); cv.setFillColor(C_ORANGE)
    cv.drawRightString(re, sub_y, CONTACT_PHONE)
    cv.setFont("Helvetica", 7.5); cv.setFillColor(C_GRAY)
    cv.drawRightString(re, sub_y - 13, f"{CONTACT_EMAIL}  .  {CONTACT_SITE}")

    cursor -= gap + 8
    # ═══════════════════════════════════════════════════════
    sec_label(cv, PAD, cursor, "How You Stack Up")
    cursor -= SEC_LABEL_H

    # Name plates
    PLATE_H = 42
    cursor -= PLATE_H
    half_w = (iw - 4) / 2
    lx = PAD; rx = PAD + half_w + 4

    rrect(cv, lx, cursor, half_w, PLATE_H, r=8, fill=C_WHITE, stroke=C_ORANGE, sw=1.5)
    cv.setFont("Helvetica-Bold", 7); cv.setFillColor(C_ORANGE)
    cv.drawString(lx + 10, cursor + PLATE_H - 12, "YOU")
    ns2 = 10
    while cv.stringWidth(bname, "Helvetica-Bold", ns2) > half_w - 20 and ns2 > 7.5:
        ns2 -= 0.5
    cv.setFont("Helvetica-Bold", ns2); cv.setFillColor(C_BLACK)
    cv.drawCentredString(lx + half_w/2, cursor + PLATE_H/2 + 2, bname)
    cv.setFont("Helvetica", 7.5); cv.setFillColor(C_GRAY)
    cv.drawCentredString(lx + half_w/2, cursor + PLATE_H/2 - 9,
                         f"{data['review_rating']} \u2605  .  {data['review_count']} reviews")

    cname = data["comp_name"]
    rrect(cv, rx, cursor, half_w, PLATE_H, r=8, fill=C_WHITE, stroke=C_LGRAY, sw=1)
    cv.setFont("Helvetica-Bold", 7); cv.setFillColor(C_GRAY)
    cv.drawString(rx + 10, cursor + PLATE_H - 12, "THEM")
    ns3 = 10
    while cv.stringWidth(cname, "Helvetica-Bold", ns3) > half_w - 20 and ns3 > 7.5:
        ns3 -= 0.5
    cv.setFont("Helvetica-Bold", ns3); cv.setFillColor(C_DGRAY)
    cv.drawCentredString(rx + half_w/2, cursor + PLATE_H/2 + 2, cname)
    cv.setFont("Helvetica", 7.5); cv.setFillColor(C_GRAY)
    cv.drawCentredString(rx + half_w/2, cursor + PLATE_H/2 - 9,
                         f"{data.get('comp_rating','?')} \u2605  .  {data.get('comp_reviews','?')} reviews")

    # Column headers — generous space above them
    cursor -= 10
    Q_W   = iw * 0.52
    A_W   = iw * 0.24
    MID_X = PAD + Q_W + A_W * 0.5
    THM_X = PAD + Q_W + A_W * 1.5
    cv.setFont("Helvetica-Bold", 8); cv.setFillColor(C_DGRAY)
    cv.drawCentredString(MID_X, cursor, "You")
    cv.drawCentredString(THM_X, cursor, "Them")
    cursor -= 6
    hrule(cv, PAD, cursor, iw)

    # Chip rows
    COMP_ROW_H = 34
    for question, you_ans, them_ans, you_good, them_good in comp_rows:
        cursor -= COMP_ROW_H
        cv.setFont("Helvetica-Bold", 8.5); cv.setFillColor(C_BLACK)
        cv.drawString(PAD + 8, cursor + COMP_ROW_H/2 - 3, question)
        draw_chip(cv, MID_X, cursor, COMP_ROW_H, you_ans,  you_good)
        draw_chip(cv, THM_X, cursor, COMP_ROW_H, them_ans, them_good)
        hrule(cv, PAD, cursor, iw, color=C_LGRAY, lw=0.35)

    # Takeaway
    cursor -= 8
    TK_H = 48
    cursor -= TK_H
    rrect(cv, PAD, cursor, iw, TK_H, r=6, fill=C_WHITE, stroke=C_LGRAY, sw=0.8)
    cv.setFont("Helvetica-BoldOblique", 9); cv.setFillColor(C_DGRAY)
    cv.drawCentredString(PAD + iw/2, cursor + TK_H - 15, tk_line1)
    l2_size = 10
    while cv.stringWidth(tk_line2, "Helvetica-Bold", l2_size) > iw - 20 and l2_size > 8:
        l2_size -= 0.5
    cv.setFont("Helvetica-Bold", l2_size); cv.setFillColor(C_BLACK)
    cv.drawCentredString(PAD + iw/2, cursor + 14, tk_line2)

    cursor -= gap

    # ═══════════════════════════════════════════════════════
    #  3. WHAT WE FOUND
    # ═══════════════════════════════════════════════════════
    sec_label(cv, PAD, cursor, "What We Found")
    cursor -= SEC_LABEL_H

    for finding in findings:
        fh = texth(cv, finding, iw - 26, font="Helvetica", size=8.5, lh=13) + 22
        cursor -= fh
        rrect(cv, PAD, cursor, iw, fh, r=6, fill=C_WHITE, stroke=C_LGRAY, sw=0.8)
        cv.setFillColor(C_ORANGE)
        cv.rect(PAD, cursor, 3, fh, fill=1, stroke=0)
        wraptext(cv, finding, PAD + 12, cursor + fh - 13,
                 iw - 22, font="Helvetica", size=8.5, color=C_BLACK, lh=13)
        cursor -= 6

    cursor -= gap

    # ═══════════════════════════════════════════════════════
    #  4. HOW SEARCHING WORKS NOW
    # ═══════════════════════════════════════════════════════
    sec_label(cv, PAD, cursor, "How Searching Works Now")
    cursor -= SEC_LABEL_H

    LINE_H    = 16
    OUTCOME_H = 16 + len(out_buls) * LINE_H + 14
    cursor -= OUTCOME_H
    rrect(cv, PAD, cursor, iw, OUTCOME_H, r=6, fill=C_WHITE, stroke=C_LGRAY, sw=0.8)
    cv.setFillColor(C_ORANGE)
    cv.rect(PAD, cursor, 3, OUTCOME_H, fill=1, stroke=0)
    cv.setFont("Helvetica-Bold", 9.5); cv.setFillColor(C_BLACK)
    cv.drawString(PAD + 12, cursor + OUTCOME_H - 13, out_head)
    for bi, bullet in enumerate(out_buls):
        by = cursor + OUTCOME_H - 13 - LINE_H - bi * LINE_H
        cv.setFont("Helvetica", 8.5); cv.setFillColor(C_ORANGE)
        cv.drawString(PAD + 12, by, "\u25cf")
        cv.setFont("Helvetica", 8.5); cv.setFillColor(C_BLACK)
        cv.drawString(PAD + 22, by, bullet)

    cursor -= gap

    # ═══════════════════════════════════════════════════════
    #  5. DIFFERENTIATOR
    # ═══════════════════════════════════════════════════════
    # Absorb any remaining slack into the differentiator card so nothing floats below it
    DIFF_LINE_H  = 16
    DIFF_H_BASE  = 18 + 10 + len(diff_buls) * DIFF_LINE_H + 14
    slack        = max(0, cursor - (CTA_RULE_Y + 8) - DIFF_H_BASE)
    DIFF_H       = DIFF_H_BASE + slack
    cursor -= DIFF_H
    rrect(cv, PAD, cursor, iw, DIFF_H, r=6, fill=C_WHITE, stroke=C_LGRAY, sw=0.8)

    # Headline — centered
    cv.setFont("Helvetica-Bold", 10); cv.setFillColor(C_BLACK)
    cv.drawCentredString(PAD + iw/2, cursor + DIFF_H - 14, diff_head)
    hrule(cv, PAD + 14, cursor + DIFF_H - 20, iw - 28, color=C_LGRAY, lw=0.4)

    # Bullets — 9pt, left-aligned, more defined as statements
    buls_start_y = cursor + DIFF_H - 14 - 22 - (slack / 2)
    for di, bul in enumerate(diff_buls):
        dy = buls_start_y - di * DIFF_LINE_H
        cv.setFont("Helvetica", 9); cv.setFillColor(C_DGRAY)
        cv.drawString(PAD + 14, dy, bul)

    # ═══════════════════════════════════════════════════════
    #  6. CTA FOOTER — light rule + 3 centered lines
    # ═══════════════════════════════════════════════════════
    hrule(cv, PAD, CTA_RULE_Y, iw, color=C_LGRAY, lw=0.6)
    mid = PAD + iw / 2
    cv.setFont("Helvetica-Bold", 13); cv.setFillColor(C_BLACK)
    cv.drawCentredString(mid, CTA_RULE_Y - 14, get_cta_headline())
    cv.setFont("Helvetica-Bold", 9); cv.setFillColor(C_ORANGE)
    cv.drawCentredString(mid, CTA_RULE_Y - 27,
                         f"{CONTACT_PHONE}  .  Call or text Emmanuel")
    cv.setFont("Helvetica", 8); cv.setFillColor(C_DGRAY)
    cv.drawCentredString(mid, CTA_RULE_Y - 39,
                         f"{CONTACT_EMAIL}  .  {CONTACT_SITE}")

    cv.save()
    slack = cursor - (CTA_RULE_Y + 4)
    print(f"  \u2713  Saved: {output_path}")
    print(f"  \u2022  Gap computed: {gap:.1f}pt   Slack above CTA: {slack:.0f}pt"
          f"  ({'OK' if slack >= 0 else 'OVERFLOW — reduce content or font sizes'})")


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
def main():
    from NewwebAudit import collect_data
    data = collect_data()
    data["audit_date"]  = date.today().strftime("%B %d, %Y")
    data["_findings"]   = get_findings(data)   # score-mapped, no LLM

    safe = (data["business_name"]
            .replace(" ", "_").replace("&", "and").replace("/", "-").lower())
    fn   = f"audit_{safe}_{date.today().strftime('%Y%m%d')}.pdf"
    desk = os.path.expanduser("~/Desktop")
    out  = os.path.join(desk if os.path.exists(desk) else os.getcwd(), fn)
    build_pdf(data, out)


if __name__ == "__main__":
    main()