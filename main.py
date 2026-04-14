#!/usr/bin/env python3
"""
main.py  —  Queso Ventures Audit  (v9)
Usage:  source .env && python main.py

7 sections: Header → Score Factors → Comparison → Why Losing → AEO Education → Client Snapshot → CTA
No stats bar. Contact info lives in the header. Everything readable — no light gray subtext.
"""

import os
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from NewwebAudit import collect_data, calc_visibility_score
from NewaiAudit  import (
    get_competitor_rows,
    get_competitor_takeaway,
    get_score_factors,
    get_why_losing,
    get_aeo_cards,
    get_client_snapshot,
    get_cta_headline,
)

# ─────────────────────────────────────────────
#  BRAND
# ─────────────────────────────────────────────
C_BLACK  = colors.HexColor("#1A1A1A")
C_WHITE  = colors.HexColor("#FFFFFF")
C_GRAY   = colors.HexColor("#767676")
C_LGRAY  = colors.HexColor("#D8D8D4")
C_DGRAY  = colors.HexColor("#444444")
C_RED    = colors.HexColor("#C4161C")
C_ORANGE = colors.HexColor("#D4720A")
C_GREEN  = colors.HexColor("#1A7A3C")

PAGE_W, PAGE_H = letter
PAD = 40

CONTACT_EMAIL = "hello@quesoventures.com"
CONTACT_PHONE = "(281) 203-4531"
CONTACT_SITE  = "quesoventures.com"

LOGO_URL  = "https://www.quesoventures.com/logo.png"
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".qv_logo.png")


def ensure_logo():
    if os.path.exists(LOGO_PATH):
        return LOGO_PATH
    try:
        import requests
        r = requests.get(LOGO_URL, timeout=10)
        if r.status_code == 200:
            with open(LOGO_PATH, "wb") as f:
                f.write(r.content)
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
    p.moveTo(x+r, y);           p.lineTo(x+w-r, y)
    p.arcTo(x+w-2*r, y,         x+w, y+2*r,        startAng=-90, extent=90)
    p.lineTo(x+w, y+h-r)
    p.arcTo(x+w-2*r, y+h-2*r,  x+w, y+h,           startAng=0,   extent=90)
    p.lineTo(x+r, y+h)
    p.arcTo(x,    y+h-2*r,     x+2*r, y+h,          startAng=90,  extent=90)
    p.lineTo(x, y+r)
    p.arcTo(x,    y,            x+2*r, y+2*r,        startAng=180, extent=90)
    p.close()
    c.drawPath(p, fill=1 if fill else 0, stroke=1 if stroke else 0)


def wraptext(c, txt, x, y, maxw, font="Helvetica", size=9, color=C_BLACK, lh=13):
    """Draw word-wrapped text. Returns y after last line."""
    c.setFont(font, size); c.setFillColor(color)
    words = txt.split(); line = ""; cy = y
    for w in words:
        t = (line + " " + w).strip()
        if c.stringWidth(t, font, size) <= maxw:
            line = t
        else:
            if line: c.drawString(x, cy, line); cy -= lh
            line = w
    if line: c.drawString(x, cy, line); cy -= lh
    return cy


def texth(c, txt, maxw, font="Helvetica", size=9, lh=13):
    """Estimate pixel height of word-wrapped text block."""
    words = txt.split(); lines = 1; line = ""
    for w in words:
        t = (line + " " + w).strip()
        if c.stringWidth(t, font, size) <= maxw: line = t
        else: lines += 1; line = w
    return lines * lh


def sec_label(c, x, y, txt):
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(C_GRAY)
    c.drawString(x, y, txt.upper())


def rule(c, x, y, w, color=C_LGRAY, lw=0.5):
    c.setStrokeColor(color); c.setLineWidth(lw)
    c.line(x, y, x + w, y)


# ─────────────────────────────────────────────
#  GAUGE
# ─────────────────────────────────────────────
def draw_gauge(c, cx, cy, pct, r=22):
    """Semi-arc gauge. Arc stroke + score text are the only colored ink."""
    c.setStrokeColor(C_LGRAY); c.setLineWidth(3.5)
    c.arc(cx - r, cy - r, cx + r, cy + r, startAng=200, extent=-220)
    col = C_RED if pct < 40 else C_ORANGE if pct < 68 else C_GREEN
    c.setStrokeColor(col); c.setLineWidth(3.5)
    c.arc(cx - r, cy - r, cx + r, cy + r, startAng=200, extent=-(pct / 100 * 220))
    c.setFont("Helvetica-Bold", 14); c.setFillColor(col)
    c.drawCentredString(cx, cy - 4, f"{pct}%")
    c.setFont("Helvetica", 6); c.setFillColor(C_GRAY)
    c.drawCentredString(cx, cy - 14, "Visibility Score")


# ─────────────────────────────────────────────
#  CHIP  (comparison table answer)
# ─────────────────────────────────────────────
def draw_chip(c, cx, y, text, good):
    if text in ("N/A", "?"):
        border = C_LGRAY; tcol = C_GRAY
    elif text == "Sometimes":
        border = C_ORANGE; tcol = C_ORANGE
    elif good:
        border = C_GREEN; tcol = C_GREEN
    else:
        border = C_RED; tcol = C_RED
    rrect(c, cx - 46, y + 7, 92, 20, r=4, fill=C_WHITE, stroke=border, sw=1.2)
    c.setFont("Helvetica-Bold", 9.5); c.setFillColor(tcol)
    c.drawCentredString(cx, y + 18, text)


# ─────────────────────────────────────────────
#  BUILD
# ─────────────────────────────────────────────
def build_pdf(data, output_path):
    logo = ensure_logo()
    cv   = canvas.Canvas(output_path, pagesize=letter)
    iw   = PAGE_W - 2 * PAD   # 532pt
    term = data.get("industry_term", "customer")

    cv.setFillColor(C_WHITE); cv.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # ─────────────────────────────────────────
    #  SECTION CONSTANTS
    # ─────────────────────────────────────────
    HDR_H           = 64
    SCORE_FACTORS_H = 68
    COMP_PLATES_H   = 50
    COMP_ROW_H      = 28
    N_COMP_ROWS     = 3
    TAKEAWAY_H      = 42
    WHY_PARA_H      = 44
    AEO_CARD_H      = 46
    SNAP_ROW_H      = 24
    cta_h           = 66

    # ─────────────────────────────────────────
    #  PRE-FETCH CONTENT
    # ─────────────────────────────────────────
    vis_pct   = data.get("visibility_pct", calc_visibility_score(data))
    comp_rows = get_competitor_rows(
        data["comp_name"], data["review_count"], data["comp_reviews"],
        term,
        data.get("visibility_score", 1), data.get("comp_vis_score", 5),
        data.get("geo_score", 1),        data.get("comp_geo_score", 5),
    )
    (tk_line1, tk_line2) = get_competitor_takeaway(data.get("featured_query", ""), term)
    factors  = get_score_factors(data, term)
    why_text = get_why_losing(
        term,
        data.get("business_city", "your area"),
        data.get("featured_service", ""),
    )
    aeo_cards = get_aeo_cards()
    snapshot  = get_client_snapshot(data, term)

    bname = data["business_name"]
    city  = data.get("business_city", "")

    # ─────────────────────────────────────────
    #  DRAW
    # ─────────────────────────────────────────
    cursor = PAGE_H - 16

    # ── 1. HEADER ────────────────────────────────────────────────────────────
    cursor -= HDR_H
    rrect(cv, PAD, cursor, iw, HDR_H, r=8, fill=C_WHITE, stroke=C_LGRAY, sw=0.8)

    r_gauge  = 22
    cy_gauge = cursor + HDR_H - 30
    draw_gauge(cv, PAGE_W / 2, cy_gauge, vis_pct, r=r_gauge)

    name_y     = cy_gauge - 4
    subtitle_y = name_y - 14

    # Left zone: business name + city
    ns = 15
    while cv.stringWidth(bname, "Helvetica-Bold", ns) > iw * 0.38 and ns > 9:
        ns -= 0.5
    cv.setFont("Helvetica-Bold", ns); cv.setFillColor(C_BLACK)
    cv.drawString(PAD + 14, name_y, bname)
    cv.setFont("Helvetica", 8.5); cv.setFillColor(C_DGRAY)
    cv.drawString(PAD + 14, subtitle_y, city)

    # Right zone: logo + brand, phone, email·site
    re = PAD + iw - 14
    cv.setFont("Helvetica-Bold", 9.5)
    qvw = cv.stringWidth("Queso Ventures", "Helvetica-Bold", 9.5)
    if logo:
        LW = LH = 14
        bx = re - LW - 5 - qvw
        cv.drawImage(logo, bx, name_y - 3, width=LW, height=LH,
                     preserveAspectRatio=True, mask="auto")
        cv.setFillColor(C_BLACK); cv.drawString(bx + LW + 5, name_y, "Queso Ventures")
    else:
        cv.setFillColor(C_BLACK); cv.drawRightString(re, name_y, "Queso Ventures")
    cv.setFont("Helvetica-Bold", 8); cv.setFillColor(C_ORANGE)
    cv.drawRightString(re, subtitle_y, CONTACT_PHONE)
    cv.setFont("Helvetica", 7); cv.setFillColor(C_GRAY)
    cv.drawRightString(re, subtitle_y - 12, f"{CONTACT_EMAIL}  ·  {CONTACT_SITE}")

    cursor -= 8

    # ── 2. SCORE FACTORS ─────────────────────────────────────────────────────
    cursor -= SCORE_FACTORS_H
    sec_label(cv, PAD, cursor + SCORE_FACTORS_H - 2, "Your Visibility Score")

    row_start = cursor + SCORE_FACTORS_H - 18
    for i, (lbl, insight) in enumerate(factors):
        ry = row_start - i * 30
        # Orange accent bar
        cv.setFillColor(C_ORANGE)
        cv.rect(PAD, ry - 16, 3, 22, fill=1, stroke=0)
        # Label (bold) + insight (regular) on two lines
        cv.setFont("Helvetica-Bold", 9.5); cv.setFillColor(C_BLACK)
        cv.drawString(PAD + 10, ry, lbl)
        cv.setFont("Helvetica", 8.5); cv.setFillColor(C_DGRAY)
        cv.drawString(PAD + 10, ry - 12, insight)
        if i == 0:
            rule(cv, PAD + 10, ry - 21, iw - 10, color=C_LGRAY, lw=0.3)

    cursor -= 12

    # ── 3. HOW YOU STACK UP ──────────────────────────────────────────────────
    sec_label(cv, PAD, cursor, "How You Stack Up")
    cursor -= 8

    # Name plates
    cursor -= COMP_PLATES_H
    half_w = (iw - 4) / 2
    lx = PAD
    rx = PAD + half_w + 4

    rrect(cv, lx, cursor, half_w, COMP_PLATES_H, r=8, fill=C_WHITE, stroke=C_ORANGE, sw=1.5)
    cv.setFont("Helvetica-Bold", 7); cv.setFillColor(C_ORANGE)
    cv.drawString(lx + 8, cursor + COMP_PLATES_H - 11, "YOU")
    bname_ns = 11
    while cv.stringWidth(bname, "Helvetica-Bold", bname_ns) > half_w - 20 and bname_ns > 7.5:
        bname_ns -= 0.5
    cv.setFont("Helvetica-Bold", bname_ns); cv.setFillColor(C_BLACK)
    cv.drawCentredString(lx + half_w / 2, cursor + COMP_PLATES_H / 2 + 2, bname)
    cv.setFont("Helvetica", 7); cv.setFillColor(C_GRAY)
    cv.drawCentredString(lx + half_w / 2, cursor + COMP_PLATES_H / 2 - 9,
                         f"{data['review_rating']} \u2605  \u00b7  {data['review_count']} reviews")

    rrect(cv, rx, cursor, half_w, COMP_PLATES_H, r=8, fill=C_WHITE, stroke=C_LGRAY, sw=1)
    cv.setFont("Helvetica-Bold", 7); cv.setFillColor(C_GRAY)
    cv.drawString(rx + 8, cursor + COMP_PLATES_H - 11, "THEM")
    cname = data["comp_name"]
    cname_ns = 10
    while cv.stringWidth(cname, "Helvetica-Bold", cname_ns) > half_w - 20 and cname_ns > 7.5:
        cname_ns -= 0.5
    cv.setFont("Helvetica-Bold", cname_ns); cv.setFillColor(C_DGRAY)
    cv.drawCentredString(rx + half_w / 2, cursor + COMP_PLATES_H / 2 + 2, cname)
    cv.setFont("Helvetica", 7); cv.setFillColor(C_GRAY)
    cv.drawCentredString(rx + half_w / 2, cursor + COMP_PLATES_H / 2 - 9,
                         f"{data.get('comp_rating', '?')} \u2605  \u00b7  {data.get('comp_reviews', '?')} reviews")

    cursor -= 10

    # Column headers
    Q_W   = iw * 0.52
    A_W   = iw * 0.24
    MID_X = PAD + Q_W + A_W * 0.5
    THM_X = PAD + Q_W + A_W * 1.5

    cv.setFont("Helvetica-Bold", 7.5); cv.setFillColor(C_DGRAY)
    cv.drawCentredString(MID_X, cursor, "You")
    cv.drawCentredString(THM_X, cursor, "Them")
    cursor -= 4
    rule(cv, PAD, cursor, iw)

    # Rows
    for ri, (question, you_ans, them_ans, you_good, them_good) in enumerate(comp_rows):
        cursor -= COMP_ROW_H
        row_y  = cursor
        text_y = row_y + COMP_ROW_H / 2 - 3
        cv.setFont("Helvetica-Bold", 8.5); cv.setFillColor(C_BLACK)
        cv.drawString(PAD + 8, text_y, question)
        draw_chip(cv, MID_X, row_y, you_ans, you_good)
        draw_chip(cv, THM_X, row_y, them_ans, them_good)
        rule(cv, PAD, row_y, iw, color=C_LGRAY, lw=0.4)

    cursor -= 8

    # Takeaway box
    cursor -= TAKEAWAY_H
    rrect(cv, PAD, cursor, iw, TAKEAWAY_H, r=6,
          fill=C_WHITE, stroke=C_LGRAY, sw=0.8)
    cv.setFont("Helvetica-Oblique", 10); cv.setFillColor(C_DGRAY)
    cv.drawCentredString(PAD + iw / 2, cursor + TAKEAWAY_H - 13, tk_line1)
    cv.setFont("Helvetica-Bold", 10.5); cv.setFillColor(C_BLACK)
    cv.drawCentredString(PAD + iw / 2, cursor + 13, tk_line2)

    cursor -= 12

    # ── 4. WHY THIS HAPPENS ──────────────────────────────────────────────────
    sec_label(cv, PAD, cursor, "Why This Happens")
    cursor -= 10

    cursor -= WHY_PARA_H + 4
    rrect(cv, PAD, cursor, iw, WHY_PARA_H, r=6, fill=C_WHITE, stroke=C_LGRAY, sw=0.8)
    cv.setFillColor(C_ORANGE)
    cv.rect(PAD, cursor, 3, WHY_PARA_H, fill=1, stroke=0)
    wraptext(cv, why_text, PAD + 12, cursor + WHY_PARA_H - 12,
             iw - 20, font="Helvetica", size=8.5, color=C_DGRAY, lh=13)

    cursor -= 12

    # ── 5. WHAT CHANGES THIS (AEO education) ─────────────────────────────────
    sec_label(cv, PAD, cursor, "What Changes This")
    cursor -= 10

    cursor -= AEO_CARD_H
    CARD_GAP = 6
    CARD_W   = (iw - 2 * CARD_GAP) / 3
    for ci, (heading, body) in enumerate(aeo_cards):
        cx = PAD + ci * (CARD_W + CARD_GAP)
        rrect(cv, cx, cursor, CARD_W, AEO_CARD_H, r=6, fill=C_WHITE, stroke=C_LGRAY, sw=0.8)
        head_y  = cursor + AEO_CARD_H - 13
        num_str = f"0{ci + 1}  "
        num_w   = cv.stringWidth(num_str, "Helvetica-Bold", 8.5)
        cv.setFont("Helvetica-Bold", 8.5); cv.setFillColor(C_ORANGE)
        cv.drawString(cx + 8, head_y, num_str)
        cv.setFillColor(C_BLACK)
        cv.drawString(cx + 8 + num_w, head_y, heading)
        wraptext(cv, body, cx + 8, head_y - 13,
                 CARD_W - 16, font="Helvetica", size=7.5, color=C_DGRAY, lh=10)

    cursor -= 12

    # ── 6. YOUR NUMBERS (client snapshot) ────────────────────────────────────
    sec_label(cv, PAD, cursor, "Your Numbers")
    cursor -= 10

    STAT_COL_W = 90
    geo        = data.get("geo_score", 1)
    geo_col    = C_GREEN if geo >= 4 else C_ORANGE if geo == 3 else C_RED

    for si, (val, lbl, insight) in enumerate(snapshot):
        cursor -= SNAP_ROW_H
        mid_stat = cursor + SNAP_ROW_H / 2

        # Stat value — AI visibility row gets color, others stay black
        val_col = geo_col if lbl == "AI Visibility" else C_BLACK
        cv.setFont("Helvetica-Bold", 13); cv.setFillColor(val_col)
        cv.drawCentredString(PAD + STAT_COL_W / 2, mid_stat + 2, val)
        cv.setFont("Helvetica", 6.5); cv.setFillColor(C_GRAY)
        cv.drawCentredString(PAD + STAT_COL_W / 2, mid_stat - 8, lbl)

        # Vertical divider
        cv.setStrokeColor(C_LGRAY); cv.setLineWidth(0.5)
        cv.line(PAD + STAT_COL_W + 4, cursor + 4,
                PAD + STAT_COL_W + 4, cursor + SNAP_ROW_H - 4)

        # Insight — use wraptext to handle long strings safely
        wraptext(cv, insight, PAD + STAT_COL_W + 12, mid_stat + 4,
                 iw - STAT_COL_W - 16, font="Helvetica", size=8.5, color=C_DGRAY, lh=12)

        if si < len(snapshot) - 1:
            cursor -= 4
            rule(cv, PAD, cursor + 2, iw, color=C_LGRAY, lw=0.3)

    cursor -= 10

    # ── 7. CTA ───────────────────────────────────────────────────────────────
    cursor -= cta_h
    rrect(cv, PAD, cursor, iw, cta_h, r=8, fill=C_WHITE, stroke=C_BLACK, sw=1.5)
    mid = PAD + iw / 2
    cv.setFont("Helvetica-Bold", 16); cv.setFillColor(C_BLACK)
    cv.drawCentredString(mid, cursor + cta_h - 22, get_cta_headline())
    cv.setFont("Helvetica-Bold", 11); cv.setFillColor(C_ORANGE)
    cv.drawCentredString(mid, cursor + cta_h - 40,
                         f"{CONTACT_PHONE}  ·  Call or text Emmanuel")
    cv.setFont("Helvetica", 9); cv.setFillColor(C_DGRAY)
    cv.drawCentredString(mid, cursor + cta_h - 55,
                         f"{CONTACT_EMAIL}  ·  {CONTACT_SITE}")

    cv.save()
    print(f"  \u2713  {output_path}  (bottom margin: {cursor - 16:.0f}pt)")


# ─────────────────────────────────────────────
#  ENTRY
# ─────────────────────────────────────────────
def main():
    data = collect_data()
    data["audit_date"] = date.today().strftime("%B %d, %Y")
    safe = (data["business_name"]
            .replace(" ", "_").replace("&", "and").replace("/", "-").lower())
    fn   = f"audit_{safe}_{date.today().strftime('%Y%m%d')}.pdf"
    desk = os.path.expanduser("~/Desktop")
    out  = os.path.join(desk if os.path.exists(desk) else os.getcwd(), fn)
    build_pdf(data, out)


if __name__ == "__main__":
    main()
