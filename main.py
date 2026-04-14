#!/usr/bin/env python3
"""
main.py  —  Queso Ventures Audit  (v8)
Usage:  source .env && python main.py

Printer-friendly: no solid color fills — only borders and text carry color.
Color budget: score gauge, logo, AI Search text, orange accent bars,
              YOU plate border, Queso Ventures name — everything else black/gray.
"""

import os
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from webAudit import collect_data, calc_visibility_score
from aiAudit  import (
    get_competitor_rows,
    get_competitor_takeaway,
    get_findings,
    get_explainer,
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
#  GAUGE  (only colored element besides logo)
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
#  CHIP  (comparison table answer — border + text only, no fill)
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
    logo  = ensure_logo()
    cv    = canvas.Canvas(output_path, pagesize=letter)
    iw    = PAGE_W - 2 * PAD   # 532pt
    term  = data.get("industry_term", "customer")
    btype = data.get("business_type", "")

    cv.setFillColor(C_WHITE); cv.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # ─────────────────────────────────────────────
    #  PRE-MEASURE
    # ─────────────────────────────────────────────
    HDR_H         = 64
    STATS_H       = 44
    COMP_PLATES_H = 50   # reduced — give more room to the statement below
    COMP_ROW_H    = 28   # compact rows
    N_COMP_ROWS   = 3
    TAKEAWAY_H    = 46   # prominent centered statement in a shaded box

    comp_rows = get_competitor_rows(
        data["comp_name"], data["review_count"], data["comp_reviews"],
        term,
        data.get("visibility_score", 1), data.get("comp_vis_score", 5),
        data.get("geo_score", 1),        data.get("comp_geo_score", 5),
    )
    (tk_line1, tk_line2) = get_competitor_takeaway(
        data.get("featured_query", ""), term
    )

    findings = get_findings(
        term, data.get("has_website", True),
        data.get("client_ps"), data.get("geo_score", 1),
        data.get("visibility_score", 1),
        comp_name=data.get("comp_name", ""),
        client_reviews=data.get("review_count", 0),
        comp_reviews=data.get("comp_reviews", 0),
        gbp_score=data.get("gbp_score", 3),
        featured_service=data.get("featured_service", ""),
    )
    expl = get_explainer(term)

    # WHY section heights  (now drawn BEFORE findings)
    CALLOUT_PAD  = 6    # top + bottom padding inside callout box
    CALLOUT_LH1  = 12   # intro line height (8.5pt text)
    CALLOUT_GAP  = 5    # between intro and query
    CALLOUT_LH2  = 14   # query line height (11pt text)
    callout_h    = CALLOUT_PAD + CALLOUT_LH1 + CALLOUT_GAP + CALLOUT_LH2 + CALLOUT_PAD

    WHY_CARD_H   = 46   # height of each of the 3 horizontal insight cards (number+title same line)
    why_sec_h    = 10 + callout_h + 8 + WHY_CARD_H  # label_gap + box + gap + cards

    # Competitor section:
    #   label_gap(8) + plates(50) + gap(10) + col_hdr+gap(4+4) + rows(3×28)
    #   + gap(8) + TAKEAWAY_H(46)
    comp_sec_h = 8 + COMP_PLATES_H + 10 + 8 + N_COMP_ROWS * COMP_ROW_H + 8 + TAKEAWAY_H

    # Per-finding budget  (order: comp → WHY → finds → CTA)
    FIND_HEADLINE_SIZE = 11
    FIND_BODY_SIZE     = 8.5
    FIND_GAP           = 12
    cta_h              = 68
    BOTTOM_RESERVE     = 14  # guaranteed bottom margin beyond the 16pt pad
    GAPS = 8 + 20 + 14 + 14 + 10  # hdr-stats, stats-comp, comp-why, why-finds, finds-cta

    fixed_used   = 16 + HDR_H + GAPS + STATS_H + comp_sec_h + why_sec_h + cta_h + 16
    finds_budget = PAGE_H - fixed_used
    n_finds      = len(findings)
    per_find_h   = (finds_budget - (n_finds - 1) * FIND_GAP - 14 - BOTTOM_RESERVE) / n_finds
    per_find_h   = max(per_find_h, 42)

    # ─────────────────────────────────────────────
    #  DRAW
    # ─────────────────────────────────────────────
    cursor = PAGE_H - 16

    # ── HEADER ───────────────────────────────────────────────────────────────
    cursor -= HDR_H
    rrect(cv, PAD, cursor, iw, HDR_H, r=8, fill=C_WHITE, stroke=C_LGRAY, sw=0.8)

    bname = data["business_name"]

    # Gauge center — fits inside card with 8pt clearance top/bottom
    r_gauge  = 22
    cy_gauge = cursor + HDR_H - 30   # arc top at cursor+52 (12pt from card top)
    vis_pct  = data.get("visibility_pct", calc_visibility_score(data))
    draw_gauge(cv, PAGE_W / 2, cy_gauge, vis_pct, r=r_gauge)

    # Left/right text anchored to gauge % baseline
    name_y     = cy_gauge - 4    # % renders at cy-4; name shares that baseline
    subtitle_y = name_y - 14

    # Left zone: business name + type/city
    ns = 15
    while cv.stringWidth(bname, "Helvetica-Bold", ns) > iw * 0.38 and ns > 9:
        ns -= 0.5
    cv.setFont("Helvetica-Bold", ns); cv.setFillColor(C_BLACK)
    cv.drawString(PAD + 14, name_y, bname)
    cv.setFont("Helvetica", 8.5); cv.setFillColor(C_GRAY)
    cv.drawString(PAD + 14, subtitle_y,
                  f"{data['business_type']}  ·  {data['business_city']}")

    # Right zone: logo + brand
    re  = PAD + iw - 14
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
    cv.setFont("Helvetica", 8); cv.setFillColor(C_GRAY)
    cv.drawRightString(re, subtitle_y, f"Visibility Report  ·  {data['audit_date']}")

    cursor -= 8

    # ── STATS BAR ─────────────────────────────────────────────────────────────
    cursor -= STATS_H
    rrect(cv, PAD, cursor, iw, STATS_H, r=8, fill=C_WHITE, stroke=C_LGRAY, sw=0.8)

    geo = data.get("geo_score", 1)
    ai_label = "Showing Up" if geo >= 4 else "Partial" if geo == 3 else "Not Visible"
    ai_col   = C_GREEN   if geo >= 4 else C_ORANGE  if geo == 3 else C_RED

    client_ps = data.get("client_ps")
    if client_ps is not None:
        tech_val = f"{client_ps}/100"
        tech_lbl = "Site Speed · Google"
        tech_col = C_GREEN if client_ps >= 70 else C_ORANGE if client_ps >= 50 else C_RED
    else:
        photos   = data.get("gbp_photo_count", 0)
        tech_val = str(photos)
        tech_lbl = "Profile Photos · GBP"
        tech_col = C_GREEN if photos >= 10 else C_ORANGE if photos >= 3 else C_RED

    # Slot 1: Rating + Reviews combined (3 lines)
    # Slot 2: AI Search (2 lines)
    # Slot 3: Technical metric (2 lines)
    STATS_ZONE_W = 375
    sw3  = STATS_ZONE_W / 3
    mid_y = cursor + STATS_H / 2

    # Slot 1
    cx1 = PAD + sw3 / 2
    cv.setFont("Helvetica-Bold", 11); cv.setFillColor(C_BLACK)
    cv.drawCentredString(cx1, mid_y + 5, f"{data['review_rating']} ★")
    cv.setFont("Helvetica", 7); cv.setFillColor(C_DGRAY)
    cv.drawCentredString(cx1, mid_y - 5, f"{data['review_count']} Reviews")
    cv.setFont("Helvetica", 6.5); cv.setFillColor(C_GRAY)
    cv.drawCentredString(cx1, mid_y - 14, "Google Rating")

    cv.setStrokeColor(C_LGRAY); cv.setLineWidth(0.5)
    cv.line(PAD + sw3, cursor + 8, PAD + sw3, cursor + STATS_H - 8)

    # Slot 2
    cx2 = PAD + sw3 * 1.5
    cv.setFont("Helvetica-Bold", 12); cv.setFillColor(ai_col)
    cv.drawCentredString(cx2, mid_y + 3, ai_label)
    cv.setFont("Helvetica", 6.5); cv.setFillColor(C_GRAY)
    cv.drawCentredString(cx2, mid_y - 9, "Beyond Google")

    cv.setStrokeColor(C_LGRAY); cv.setLineWidth(0.5)
    cv.line(PAD + sw3 * 2, cursor + 8, PAD + sw3 * 2, cursor + STATS_H - 8)

    # Slot 3
    cx3 = PAD + sw3 * 2.5
    cv.setFont("Helvetica-Bold", 12); cv.setFillColor(tech_col)
    cv.drawCentredString(cx3, mid_y + 3, tech_val)
    cv.setFont("Helvetica", 6.5); cv.setFillColor(C_GRAY)
    cv.drawCentredString(cx3, mid_y - 9, tech_lbl)

    # Divider + contact zone
    div_x = PAD + STATS_ZONE_W
    cv.setStrokeColor(C_LGRAY); cv.setLineWidth(0.5)
    cv.line(div_x, cursor + 8, div_x, cursor + STATS_H - 8)
    ccx = div_x + (iw - STATS_ZONE_W) / 2
    cv.setFont("Helvetica-Bold", 7.5); cv.setFillColor(C_ORANGE)
    cv.drawCentredString(ccx, mid_y + 4, "Emmanuel · Queso Ventures")
    cv.setFont("Helvetica", 7); cv.setFillColor(C_GRAY)
    cv.drawCentredString(ccx, mid_y - 8, f"{CONTACT_PHONE}  ·  {CONTACT_SITE}")

    cursor -= 20

    # ── HOW YOU STACK UP ─────────────────────────────────────────────────────
    sec_label(cv, PAD, cursor, "How You Stack Up")
    cursor -= 8

    # Name plates
    cursor -= COMP_PLATES_H
    half_w = (iw - 4) / 2
    lx = PAD
    rx = PAD + half_w + 4

    # YOU — orange border
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
                         f"{data['review_rating']} ★  ·  {data['review_count']} reviews")

    # THEM — gray border
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
                         f"{data.get('comp_rating', '?')} ★  ·  {data.get('comp_reviews', '?')} reviews")

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

    # Takeaway — prominent centered statement in a shaded box
    cursor -= TAKEAWAY_H
    rrect(cv, PAD, cursor, iw, TAKEAWAY_H, r=6,
          fill=C_WHITE, stroke=C_LGRAY, sw=0.8)
    cv.setFont("Helvetica-Oblique", 11); cv.setFillColor(C_DGRAY)
    cv.drawCentredString(PAD + iw / 2, cursor + TAKEAWAY_H - 14, tk_line1)
    cv.setFont("Helvetica-Bold", 11); cv.setFillColor(C_BLACK)
    cv.drawCentredString(PAD + iw / 2, cursor + 12, tk_line2)

    cursor -= 14  # comp → WHY gap

    # ── WHY THIS IS HAPPENING — callout box + 3 insight cards ────────────────
    sec_label(cv, PAD, cursor, "Why This Is Happening")
    cursor -= 10

    # Callout box — business outcome framing, no search query
    box_y = cursor - callout_h
    rrect(cv, PAD, box_y, iw, callout_h, r=6, fill=C_WHITE, stroke=C_LGRAY, sw=0.8)
    cv.setFillColor(C_ORANGE)
    cv.rect(PAD, box_y, 3, callout_h, fill=1, stroke=0)   # left accent bar

    intro_y = cursor - CALLOUT_PAD - CALLOUT_LH1 + 3
    cv.setFont("Helvetica", 8.5); cv.setFillColor(C_DGRAY)
    cv.drawString(PAD + 12, intro_y, expl["intro"])

    stmt_y = intro_y - CALLOUT_GAP - CALLOUT_LH2 + 2
    cv.setFont("Helvetica-Bold", 11); cv.setFillColor(C_BLACK)
    cv.drawCentredString(PAD + iw / 2, stmt_y, expl["statement"])

    cursor -= callout_h + 8

    # 3 horizontal insight cards — number + title on same line
    CARD_GAP = 6
    CARD_W   = (iw - 2 * CARD_GAP) / 3
    cursor -= WHY_CARD_H
    for ci, (heading, body) in enumerate(expl["cards"]):
        cx = PAD + ci * (CARD_W + CARD_GAP)
        rrect(cv, cx, cursor, CARD_W, WHY_CARD_H, r=6, fill=C_WHITE, stroke=C_LGRAY, sw=0.8)
        head_y = cursor + WHY_CARD_H - 13
        # Number "01" in orange, then heading in black — same baseline
        num_str = f"0{ci + 1}  "
        num_w = cv.stringWidth(num_str, "Helvetica-Bold", 8.5)
        cv.setFont("Helvetica-Bold", 8.5); cv.setFillColor(C_ORANGE)
        cv.drawString(cx + 8, head_y, num_str)
        cv.setFillColor(C_BLACK)
        cv.drawString(cx + 8 + num_w, head_y, heading)
        wraptext(cv, body, cx + 8, head_y - 13,
                 CARD_W - 16, font="Helvetica", size=7.5, color=C_DGRAY, lh=10)

    cursor -= 14  # WHY → finds gap

    # ── WHAT THIS IS COSTING YOU ─────────────────────────────────────────────
    sec_label(cv, PAD, cursor, "What This Is Costing You")
    cursor -= 14

    for fi, (headline, body) in enumerate(findings):
        # Orange accent bar spans the full slot height
        bar_h = per_find_h - 6
        cv.setFillColor(C_ORANGE)
        cv.rect(PAD, cursor - bar_h, 3, bar_h, fill=1, stroke=0)

        # Headline centered vertically in the slot
        headline_y = cursor - (per_find_h - FIND_HEADLINE_SIZE) / 2
        cv.setFont("Helvetica-Bold", FIND_HEADLINE_SIZE); cv.setFillColor(C_BLACK)
        cv.drawString(PAD + 14, headline_y, headline)

        cursor -= per_find_h

        if fi < len(findings) - 1:
            cursor -= FIND_GAP
            rule(cv, PAD + 14, cursor + FIND_GAP / 2, iw - 14, color=C_LGRAY, lw=0.3)

    cursor -= 10  # finds → CTA gap

    # ── CTA BLOCK — border only ───────────────────────────────────────────────
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
    print(f"  ✓  {output_path}  (bottom margin: {cursor - 16:.0f}pt)")


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
