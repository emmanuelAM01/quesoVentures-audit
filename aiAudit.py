#!/usr/bin/env python3
"""
Queso Ventures — GEO/AEO Opportunity Document
Usage: edit the config block below, then run: python aiAudit.py
"""
from datetime import date

# ─────────────────────────────────────────────
#  CONFIG — edit this per client
# ─────────────────────────────────────────────
BUSINESS_NAME = "Health is Wealth"
BUSINESS_CITY = "Humble, TX"
AUDIT_DATE    = date.today().strftime("%B %d, %Y")

# Each finding is a tuple: ("orange" or "red", "finding text")
# Always 4 entries
FINDINGS = [
    ("orange",
     "You show up for some searches but not others — the patients who need you most "
     "are searching in ways your online presence isn't set up to catch yet."),
    ("orange",
     "The platforms AI tools pull from when deciding who to recommend "
     "don't have a complete or consistent picture of your business."),
    ("orange",
     "Your services cover multiple specialties — but new patients searching "
     "for any one of them aren't finding you as the obvious answer for them."),
    ("orange",
     "There are gaps between how patients try to reach you and how easy it actually is — "
     "every gap is a potential new patient who went with someone else."),
]

# ─────────────────────────────────────────────
#  HARDCODED CONTENT — same for every client
# ─────────────────────────────────────────────
PATIENT_TEXT = (
    "Your next patient isn't opening Google and typing keywords anymore. "
    "They're asking questions to AI like 'where can I get a weight loss shot near me' "
    "or 'best clinic for IV therapy in my area.' These tools give one answer, not a list of links. "
    "The clinics in that answer are getting calls, but "
    "the ones that aren't don't exist to that patient."
)

OPT_A_TITLE = "AI Visibility Only"
OPT_A_DESC  = (
    "Work on the layer that determines whether AI tools "
    "recommend you. Without touching your current site."
)

OPT_B_TITLE = "New Site + AI Visibility"
OPT_B_DESC  = (
    "A restructured site designed for 2026. Fast, clear, and "
    "optimized for AI search from day one."
)

AI_VIS_TEXT = (
    "AI Visibility means showing up when it matters most. "
    "When someone asks an AI tool to recommend a business like yours, it decides based on "
    "three things: how consistently your business information appears across the internet, "
    "how clearly your services are described in places AI tools actually read, and how much "
    "trust your online presence has built up over time. This isn't something that happens "
    "automatically, it's built intentionally. Businesses that optimize for this now, will have a strong headstart."
)

AUTH_L1 = "AI search doesn't work like Google — keywords are only part of the equation."
AUTH_L2 = (
    "These engines read your entire web presence: structured data, citations, "
    "and content that directly answers what people are actually searching for. "
    "Your next client is already out there searching. Make sure you're the one they find."
)

CONTACT_PHONE = "(281) 203-4531"
CONTACT_EMAIL = "hello@quesoventures.com"
CONTACT_SITE  = "quesoventures.com"

# ─────────────────────────────────────────────
#  BUILD
# ─────────────────────────────────────────────
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
import os

C_BLACK  = colors.HexColor("#1A1A1A")
C_WHITE  = colors.HexColor("#FFFFFF")
C_GRAY   = colors.HexColor("#666666")
C_LGRAY  = colors.HexColor("#D8D8D5")
C_RED    = colors.HexColor("#C4161C")
C_ORANGE = colors.HexColor("#D4720A")

PAGE_W, PAGE_H = letter
PAD = 40

LOGO_URL  = "https://www.quesoventures.com/logo.png"
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".qv_logo.png")

def ensure_logo():
    import requests
    if os.path.exists(LOGO_PATH):
        return LOGO_PATH
    try:
        print("  Downloading logo...", end=" ", flush=True)
        r = requests.get(LOGO_URL, timeout=10)
        if r.status_code == 200:
            with open(LOGO_PATH, "wb") as f:
                f.write(r.content)
            print("done")
            return LOGO_PATH
        print(f"failed (HTTP {r.status_code})")
    except Exception as e:
        print(f"failed ({e})")
    return None

def rounded_rect(c, x, y, w, h, r=6, fill_color=None, stroke_color=None, stroke_width=0.5):
    if fill_color:   c.setFillColor(fill_color)
    if stroke_color: c.setStrokeColor(stroke_color); c.setLineWidth(stroke_width)
    else:            c.setLineWidth(0)
    p = c.beginPath()
    p.moveTo(x+r, y)
    p.lineTo(x+w-r, y)
    p.arcTo(x+w-2*r, y, x+w, y+2*r, startAng=-90, extent=90)
    p.lineTo(x+w, y+h-r)
    p.arcTo(x+w-2*r, y+h-2*r, x+w, y+h, startAng=0, extent=90)
    p.lineTo(x+r, y+h)
    p.arcTo(x, y+h-2*r, x+2*r, y+h, startAng=90, extent=90)
    p.lineTo(x, y+r)
    p.arcTo(x, y, x+2*r, y+2*r, startAng=180, extent=90)
    p.close()
    c.drawPath(p, fill=1 if fill_color else 0, stroke=1 if stroke_color else 0)

def wrap_text(c, txt, x, y, max_w, font="Helvetica", size=9, color=C_BLACK, line_h=13):
    c.setFont(font, size)
    c.setFillColor(color)
    words = txt.split()
    line, cy = "", y
    for w in words:
        test = (line + " " + w).strip()
        if c.stringWidth(test, font, size) <= max_w:
            line = test
        else:
            c.drawString(x, cy, line)
            cy -= line_h
            line = w
    if line:
        c.drawString(x, cy, line)
    return cy

def estimate_h(c, txt, max_w, font="Helvetica", size=9, line_h=13, pad=18):
    words = txt.split()
    lines, line = 1, ""
    for w in words:
        test = (line + " " + w).strip()
        if c.stringWidth(test, font, size) <= max_w:
            line = test
        else:
            lines += 1
            line = w
    return max(34, lines * line_h + pad)

def build(output_path):
    logo_path = ensure_logo()
    c = canvas.Canvas(output_path, pagesize=letter)
    inner_w = PAGE_W - 2*PAD
    cursor  = PAGE_H - 24

    c.setFillColor(C_WHITE)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # ── HEADER ────────────────────────────────────────────────────────────────
    HDR_H = 56
    cursor -= HDR_H
    rounded_rect(c, PAD, cursor, inner_w, HDR_H, r=8,
                 fill_color=C_WHITE, stroke_color=C_LGRAY)
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(C_BLACK)
    c.drawString(PAD+16, cursor+HDR_H-24, BUSINESS_NAME)
    c.setFont("Helvetica", 9)
    c.setFillColor(C_GRAY)
    c.drawString(PAD+16, cursor+HDR_H-40,
                 f"AI & Local Search Opportunity  ·  {BUSINESS_CITY}")
    right_edge = PAD + inner_w - 16
    row1_y     = cursor + HDR_H - 26
    row2_y     = cursor + HDR_H - 42
    qv_label   = "Queso Ventures"
    c.setFont("Helvetica-Bold", 10)
    qv_w = c.stringWidth(qv_label, "Helvetica-Bold", 10)
    if logo_path:
        LOGO_H = 14; LOGO_W = 14
        total_w = LOGO_W + 5 + qv_w
        brand_x = right_edge - total_w
        c.drawImage(logo_path, brand_x, row1_y - 3, width=LOGO_W, height=LOGO_H,
                    preserveAspectRatio=True, mask="auto")
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(C_BLACK)
        c.drawString(brand_x + LOGO_W + 5, row1_y, qv_label)
    else:
        c.setFillColor(C_BLACK)
        c.drawRightString(right_edge, row1_y, qv_label)
    c.setFont("Helvetica", 8)
    c.setFillColor(C_GRAY)
    c.drawRightString(right_edge, row2_y,
                      f"{AUDIT_DATE}")
    cursor -= 12

    # ── HOW YOUR NEXT PATIENT IS FINDING YOU ──────────────────────────────────
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(C_GRAY)
    c.drawString(PAD, cursor, "HOW YOUR NEXT PATIENT IS FINDING YOU")
    cursor -= 8

    p_h = estimate_h(c, PATIENT_TEXT, inner_w-36, size=9, line_h=13, pad=24)
    cursor -= p_h
    rounded_rect(c, PAD, cursor, inner_w, p_h, r=6,
                 fill_color=C_WHITE, stroke_color=C_LGRAY)
    c.setFillColor(C_GRAY)
    c.roundRect(PAD, cursor, 4, p_h, 2, fill=1, stroke=0)
    wrap_text(c, PATIENT_TEXT, PAD+16, cursor+p_h-13,
              inner_w-36, font="Helvetica", size=9, color=C_BLACK, line_h=13)
    cursor -= 14

    # ── WHERE YOU STAND RIGHT NOW ─────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(C_GRAY)
    c.drawString(PAD, cursor, "WHERE YOU STAND RIGHT NOW")
    cursor -= 8

    color_map = {"orange": C_ORANGE, "red": C_RED}
    for col_key, txt in FINDINGS:
        col   = color_map.get(col_key, C_ORANGE)
        fnd_h = estimate_h(c, txt, inner_w-50, size=8.5, line_h=13, pad=18)
        cursor -= fnd_h
        rounded_rect(c, PAD, cursor, inner_w, fnd_h, r=6,
                     fill_color=C_WHITE, stroke_color=C_LGRAY)
        c.setFillColor(col)
        c.roundRect(PAD, cursor, 4, fnd_h, 2, fill=1, stroke=0)
        wrap_text(c, txt, PAD+16, cursor+fnd_h-12,
                  inner_w-36, font="Helvetica", size=8.5, color=C_BLACK, line_h=13)
        cursor -= 4

    cursor -= 14

    # ── TWO WAYS FORWARD ──────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(C_GRAY)
    c.drawString(PAD, cursor, "TWO WAYS FORWARD")
    cursor -= 8

    half_w = (inner_w - 8) / 2

    # measure option card heights — equal, desc only
    a_desc_h = estimate_h(c, OPT_A_DESC, half_w-28, size=8, line_h=12, pad=0)
    b_desc_h = estimate_h(c, OPT_B_DESC, half_w-28, size=8, line_h=12, pad=0)
    OPT_H    = max(16 + 14 + a_desc_h + 8, 16 + 14 + b_desc_h + 8) + 12

    cursor -= OPT_H

    # Option A card
    rounded_rect(c, PAD, cursor, half_w, OPT_H, r=8,
                 fill_color=C_WHITE, stroke_color=C_LGRAY)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(C_BLACK)
    c.drawString(PAD+14, cursor+OPT_H-16, OPT_A_TITLE)
    wrap_text(c, OPT_A_DESC, PAD+14, cursor+OPT_H-30,
              half_w-28, font="Helvetica", size=8, color=C_GRAY, line_h=12)

    # Option B card
    rounded_rect(c, PAD+half_w+8, cursor, half_w, OPT_H, r=8,
                 fill_color=C_WHITE, stroke_color=C_LGRAY)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(C_BLACK)
    c.drawString(PAD+half_w+22, cursor+OPT_H-16, OPT_B_TITLE)
    wrap_text(c, OPT_B_DESC, PAD+half_w+22, cursor+OPT_H-30,
              half_w-28, font="Helvetica", size=8, color=C_GRAY, line_h=12)

    cursor -= 8

    # AI Visibility explanation — full width card below both options
    ai_vis_h = estimate_h(c, AI_VIS_TEXT, inner_w-36, size=8.5, line_h=13, pad=28)
    cursor -= ai_vis_h
    rounded_rect(c, PAD, cursor, inner_w, ai_vis_h, r=6,
                 fill_color=C_WHITE, stroke_color=C_LGRAY)
    c.setFillColor(C_GRAY)
    c.roundRect(PAD, cursor, 4, ai_vis_h, 2, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(C_BLACK)
    c.drawString(PAD+16, cursor+ai_vis_h-13, "What is AI Visibility?")
    wrap_text(c, AI_VIS_TEXT, PAD+16, cursor+ai_vis_h-27,
              inner_w-36, font="Helvetica", size=8.5, color=C_BLACK, line_h=13)

    # ── AUTHORITY CARD + CTA ──────────────────────────────────────────────────
    BOT_MARGIN = 16
    CTA_H      = 58
    CTA_Y      = BOT_MARGIN
    AUTH_H     = 66
    AUTH_Y     = CTA_Y + CTA_H + BOT_MARGIN

    rounded_rect(c, PAD, AUTH_Y, inner_w, AUTH_H, r=8,
                 fill_color=C_WHITE, stroke_color=C_LGRAY)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(C_BLACK)
    c.drawString(PAD+18, AUTH_Y+AUTH_H-16, AUTH_L1)
    wrap_text(c, AUTH_L2, PAD+18, AUTH_Y+AUTH_H-30,
              inner_w-36, font="Helvetica", size=8.5, color=C_GRAY, line_h=13)

    rounded_rect(c, PAD, CTA_Y, inner_w, CTA_H, r=8,
                 fill_color=C_WHITE, stroke_color=C_LGRAY, stroke_width=1.0)
    cx_mid = PAD + inner_w / 2
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(C_BLACK)
    c.drawCentredString(cx_mid, CTA_Y+CTA_H-18, "Ready to show up more?")
    c.setFont("Helvetica", 9)
    c.setFillColor(C_GRAY)
    c.drawCentredString(cx_mid, CTA_Y+CTA_H-33,
                        f"Email {CONTACT_EMAIL}  or  call / text Emmanuel at {CONTACT_PHONE}")
    c.setFont("Helvetica", 8)
    c.setFillColor(C_BLACK)
    c.drawCentredString(cx_mid, CTA_Y+12, CONTACT_SITE)

    c.save()
    print(f"✓ saved: {output_path}")

if __name__ == "__main__":
    safe = BUSINESS_NAME.replace(" ", "_").replace("&", "and").lower()
    out  = os.path.join(os.path.expanduser("~"), "Desktop", f"geo_{safe}.pdf")
    if not os.path.exists(os.path.expanduser("~/Desktop")):
        out = f"geo_{safe}.pdf"
    build(out)