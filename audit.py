#!/usr/bin/env python3
"""
source .env && python audit.py

"""

import os, re, sys, requests
from bs4 import BeautifulSoup
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ─────────────────────────────────────────────
#  BRAND — light / print-friendly
# ─────────────────────────────────────────────
C_BLACK  = colors.HexColor("#1A1A1A")   # primary text
C_DARK   = colors.HexColor("#F5F5F3")   # card bg (very light gray)
C_YELLOW = colors.HexColor("#FFD100")   # yellow accent (used sparingly)
C_WHITE  = colors.HexColor("#FFFFFF")
C_GRAY   = colors.HexColor("#666666")   # muted text
C_LGRAY  = colors.HexColor("#E8E8E5")   # subtle card / dividers
C_RED    = colors.HexColor("#C4161C")   # primary accent (Queso red)
C_ORANGE = colors.HexColor("#D4720A")
C_GREEN  = colors.HexColor("#1E7D3E")
C_PAGE   = colors.HexColor("#FFFFFF")   # page background

PAGE_W, PAGE_H = letter   # 612 x 792
PAD = 40                  # outer padding

AUDITOR      = "Queso Ventures"
SITE_URL     = "quesoventures.com"
CONTACT_EMAIL= "hello@quesoventures.com"
CONTACT_PHONE= "(281) 203-4531"
LOGO_URL     = "https://www.quesoventures.com/logo.png"
LOGO_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".qv_logo.png")

def ensure_logo():
    """Download logo once and cache it next to the script."""
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

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def score_color(s, mx=5):
    p = s / mx
    return C_RED if p < 0.4 else (C_ORANGE if p < 0.7 else C_GREEN)

def score_label(s, mx=5):
    p = s / mx
    return "Needs Work" if p < 0.4 else ("Fair" if p < 0.7 else "Good")

def pct_color(p):
    if p is None: return C_GRAY
    return C_RED if p < 50 else (C_ORANGE if p < 70 else C_GREEN)

def pct_label(p):
    if p is None: return "N/A"
    return f"{p}/100"

def rr(v, dec=1):
    """Right-round a rect: draw filled rect."""
    return v

def prompt(label, options=None, default=None):
    if options:
        print(f"\n  {label}")
        for i, o in enumerate(options, 1):
            print(f"    {i}. {o}")
        while True:
            try:
                val = int(input("    Enter number: ").strip())
                if 1 <= val <= len(options): return val
            except ValueError: pass
            print("    Invalid. Try again.")
    else:
        suffix = f" [{default}]" if default else ""
        val = input(f"  {label}{suffix}: ").strip()
        return val if val else default

def divider(title=""):
    w = 60
    if title:
        pad = (w - len(title) - 2) // 2
        print(f"\n{'─'*pad} {title} {'─'*pad}")
    else:
        print(f"\n{'─'*w}")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}
PAGESPEED_KEY = os.environ.get("PAGESPEED_KEY", "")

def check_website(url):
    if not url or url.lower() in ("none","n",""): return False, None, None
    if not url.startswith("http"): url = "https://" + url
    try:
        r = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
        return (r.status_code < 400), url, r.text if r.status_code < 400 else None
    except: return False, url, None

def get_pagespeed(url, label="", full=False):
    """
    Fetch PageSpeed data with retry. full=True returns rich dict; full=False returns perf int.
    """
    if not url: return (None if not full else {})
    tag = f" [{label}]" if label else ""
    params = {
        "url":      url,
        "strategy": "mobile",
        "category": ["performance", "seo"],
    }
    if PAGESPEED_KEY: params["key"] = PAGESPEED_KEY

    for attempt in range(1, 3):
        retry_tag = "  (retry)" if attempt > 1 else ""
        print(f"  Fetching PageSpeed{tag}{retry_tag}...", end=" ", flush=True)
        try:
            r    = requests.get(
                "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
                params=params, timeout=50
            )
            data = r.json()
            lhr  = data.get("lighthouseResult", {})
            cats = lhr.get("categories", {})

            perf_score = cats.get("performance", {}).get("score")
            seo_score  = cats.get("seo", {}).get("score")
            perf_pct   = int(perf_score * 100) if perf_score is not None else None
            seo_pct    = int(seo_score  * 100) if seo_score  is not None else None
            print(f"perf={perf_pct}/100  seo={seo_pct}/100" if seo_pct else f"{perf_pct}/100")

            if not full:
                return perf_pct

            # ── Core Web Vitals (real user data from Chrome) ──
            le   = data.get("loadingExperience", {})
            mets = le.get("metrics", {})
            def cwv_metric(key):
                m = mets.get(key, {})
                return {"rating": m.get("category", "N/A"), "value": m.get("percentile")}
            cwv = {
                "lcp": cwv_metric("LARGEST_CONTENTFUL_PAINT_MS"),
                "fid": cwv_metric("FIRST_INPUT_DELAY_MS"),
                "cls": cwv_metric("CUMULATIVE_LAYOUT_SHIFT_SCORE"),
            }

            # ── Top failing audits → plain English ──
            audits = lhr.get("audits", {})
            AUDIT_PLAIN = {
                "render-blocking-resources":       "Slow-loading code is delaying your page from appearing",
                "unused-javascript":               "Your site loads code it doesn't use, slowing it down",
                "unused-css-rules":                "Your site loads unused styling files, wasting load time",
                "uses-optimized-images":           "Images on your site are too large and slowing it down",
                "uses-responsive-images":          "Images aren't sized for phones, making mobile visitors wait",
                "uses-text-compression":           "Text files aren't compressed, making your site slower to load",
                "server-response-time":            "Your hosting server is responding slowly to visitors",
                "largest-contentful-paint-element":"Your main page content takes too long to appear on screen",
                "total-blocking-time":             "Your page briefly freezes while loading, frustrating visitors",
            }
            failures = []
            for key, plain in AUDIT_PLAIN.items():
                audit = audits.get(key, {})
                sc    = audit.get("score")
                disp  = audit.get("displayValue", "")
                if sc is not None and sc < 0.9 and disp:
                    savings = re.search(r"[\d\.]+\s*s", disp)
                    suffix  = f" ({savings.group(0)} savings)" if savings else ""
                    failures.append(f"{plain}{suffix}")

            return {
                "perf_score": perf_pct,
                "seo_score":  seo_pct,
                "cwv":        cwv,
                "top_audits": failures[:3],
            }

        except Exception as e:
            is_timeout = any(w in str(e).lower() for w in ("timed out", "timeout", "read timeout"))
            print("timed out" if is_timeout else f"failed ({e})")
            if attempt == 2:
                return None if not full else {}
            import time; time.sleep(2)

def ps_to_score(p):
    if p is None: return None
    if p >= 90: return 5
    if p >= 70: return 4
    if p >= 50: return 3
    if p >= 30: return 2
    return 1

def scrape_gbp(name, city):
    print("  Fetching GBP...", end=" ", flush=True)
    q = f"{name} {city}"
    try:
        r = requests.get(f"https://www.google.com/search?q={requests.utils.quote(q)}",
                         headers=HEADERS, timeout=10)
        txt = BeautifulSoup(r.text,"html.parser").get_text(" ", strip=True)
        rat = re.search(r'\b([1-5]\.[0-9])\b', txt[:3000])
        rev = re.search(r'[\(\s](\d{1,5})\s*(?:Google\s+)?reviews?\b', txt[:3000], re.I)
        print(f"rating={rat.group(1) if rat else '?'}")
        return (rat.group(1) if rat else None), (rev.group(1) if rev else None)
    except Exception as e:
        print(f"failed ({e})"); return None, None

def seo_check(html, city, btype):
    if not html: return {}
    soup = BeautifulSoup(html,"html.parser")
    tl   = soup.find("title")
    city_l = city.lower().split(",")[0].strip()
    type_l = btype.lower().split()[0]
    txt    = soup.get_text(" ").lower()
    h1s    = [h.get_text().lower() for h in soup.find_all("h1")]
    return {
        "city_in_title":     city_l in (tl.get_text().lower() if tl else ""),
        "city_in_h1":        any(city_l in h for h in h1s),
        "city_in_content":   city_l in txt,
        "service_mentioned": type_l in txt,
        "is_mobile_ready":   bool(soup.find("meta", attrs={"name":"viewport"})),
        "has_phone":         bool(re.search(r'\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4}', soup.get_text())),
    }

def auto_site_score(exists, seo):
    if not exists: return 1, ["No website found — you're invisible to anyone searching online"]
    issues, score = [], 5
    if not seo.get("city_in_title"):    score-=0.5; issues.append("Your city name is missing from your page title — Google can't tell where you are")
    if not seo.get("city_in_h1"):       score-=0.5; issues.append("Your city name isn't in your main headline — customers searching locally won't find you")
    if not seo.get("city_in_content"):  score-=1;   issues.append("Your city is barely mentioned on your website — Google doesn't know you're local")
    if not seo.get("service_mentioned"):score-=1;   issues.append("What you do isn't clearly stated on your website — visitors and Google have to guess")
    if not seo.get("is_mobile_ready"):  score-=1;   issues.append("Your site may not display properly on phones — most of your customers search on mobile")
    if not seo.get("has_phone"):        score-=0.5; issues.append("No phone number found on your website — customers can't easily call you")
    return max(1, round(score)), issues

# ─────────────────────────────────────────────
#  DATA COLLECTION
# ─────────────────────────────────────────────
def collect_data():
    print("\n" + "="*60)
    print("  QUESO VENTURES — AUDIT GENERATOR")
    print("="*60)
    data, auto_findings = {}, []
    score_opts = ["1 - Very Poor","2 - Poor","3 - Fair","4 - Good","5 - Excellent"]

    divider("CLIENT")
    data["business_name"] = prompt("Business name")
    data["business_type"] = prompt("Business type (e.g. Auto Repair, Event Venue)")
    data["business_city"] = prompt("City / Area (e.g. Humble, TX)")
    url_in = prompt("Website URL (blank if none)", default="")
    data["has_website"] = bool(url_in and url_in.lower() not in ("none","n",""))
    data["website_url"]  = url_in if data["has_website"] else ""

    divider("AUTO-FETCHING CLIENT")
    exists, site_url, html = check_website(data["website_url"])
    if data["has_website"] and not exists:
        confirm = prompt("Could not reach site — mark as existing anyway? (y/n)", default="n").lower()
        if confirm == "y": exists = True; html = None
    data["has_website"] = exists
    seo = seo_check(html, data["business_city"], data["business_type"]) if html else {}
    data["_seo"] = seo  # stash for recommendation engine
    ws_score, ws_issues = auto_site_score(exists, seo)
    auto_findings.extend(ws_issues)

    client_ps_data = get_pagespeed(site_url, "client", full=True) if exists else {}
    client_ps      = client_ps_data.get("perf_score") if client_ps_data else None
    client_seo_pct = client_ps_data.get("seo_score")  if client_ps_data else None
    client_cwv     = client_ps_data.get("cwv", {})    if client_ps_data else {}
    client_audits  = client_ps_data.get("top_audits", []) if client_ps_data else []

    # Manual fallback if API failed
    if exists and client_ps is None:
        print("  PageSpeed fetch failed — enter manually at pagespeed.web.dev\n")
        _ps_in = prompt("  Client phone speed score (0-100, or blank to skip)", default="")
        client_ps = int(_ps_in) if _ps_in and _ps_in.isdigit() else None
        _seo_in = prompt("  Client SEO score (0-100, or blank to skip)", default="")
        client_seo_pct = int(_seo_in) if _seo_in and _seo_in.isdigit() else None

    data["client_ps"]      = client_ps
    data["client_seo_pct"] = client_seo_pct
    data["client_cwv"]     = client_cwv
    ps_score = ps_to_score(client_ps)

    if client_ps is not None:
        if client_ps < 50:   auto_findings.append(f"Your site takes too long to load on phones ({client_ps}/100) — visitors leave before it opens")
        elif client_ps < 70: auto_findings.append(f"Your site is slower than average on phones ({client_ps}/100) — this costs you customers")
    if client_seo_pct is not None and client_seo_pct < 80:
        auto_findings.append(f"Google found technical issues on your site that make it harder to rank ({client_seo_pct}/100)")
    # Add top Lighthouse audit failures as findings
    for audit_str in client_audits:
        auto_findings.append(audit_str)

    rat, rev = scrape_gbp(data["business_name"], data["business_city"])
    if not rat:
        print("  GBP scrape failed — enter manually (check Google)\n")
        rat = prompt("  Google star rating (e.g. 4.2)", default="?")
        rev = prompt("  Google review count", default="0")
    data["review_rating"] = rat or "?"
    data["review_count"]  = rev or "0"

    print(f"\n  Client: website={'✓' if exists else '✗'}  perf={client_ps or 'N/A'}  seo={client_seo_pct or 'N/A'}  rating={data['review_rating']}  reviews={data['review_count']}")

    divider("COMPETITOR")
    print(f'  Search Google: "{data["business_type"]} {data["business_city"]}" — pick the top result that is NOT the client.\n')
    data["comp_name"]    = prompt("Competitor name", default="N/A")
    data["comp_rating"]  = prompt("Competitor star rating", default="?")
    data["comp_reviews"] = prompt("Competitor review count", default="?")
    comp_url_in = prompt("Competitor website URL (blank if none)", default="")
    data["comp_has_site"] = bool(comp_url_in and comp_url_in.lower() not in ("none","n",""))
    data["comp_website"]  = comp_url_in

    data["comp_ps"]      = None
    data["comp_seo_pct"] = None
    if data["comp_has_site"]:
        print()
        comp_exists, comp_url, _ = check_website(comp_url_in)
        if comp_exists:
            comp_ps_data         = get_pagespeed(comp_url, "competitor", full=True)
            data["comp_ps"]      = comp_ps_data.get("perf_score") if comp_ps_data else None
            data["comp_seo_pct"] = comp_ps_data.get("seo_score")  if comp_ps_data else None
            if data["comp_ps"] is None:
                print("  PageSpeed fetch failed — enter manually at pagespeed.web.dev\n")
                _cp = prompt("  Competitor phone speed score (0-100, or blank to skip)", default="")
                data["comp_ps"] = int(_cp) if _cp and _cp.isdigit() else None
                _cs = prompt("  Competitor SEO score (0-100, or blank to skip)", default="")
                data["comp_seo_pct"] = int(_cs) if _cs and _cs.isdigit() else None

    divider("SCORING — CLIENT")

    # Website
    if exists:
        print(f"\n  [CLIENT] Website Quality — auto-score: {ws_score}/5")
        ov = prompt("  Override? (blank = accept)", default="")
        data["website_score"] = int(ov) if ov and ov.isdigit() else ws_score
    else:
        data["website_score"] = 1; print("\n  [CLIENT] Website Quality — 1 (no site)")

    # Speed
    if ps_score:
        print(f"\n  [CLIENT] Mobile Page Speed — auto-score: {ps_score}/5 ({client_ps}/100)")
        ov = prompt("  Override? (blank = accept)", default="")
        data["speed_score"] = int(ov) if ov and ov.isdigit() else ps_score
    elif not exists:
        data["speed_score"] = 1
    else:
        if not PAGESPEED_KEY: print("  Tip: set PAGESPEED_KEY env var for auto-scoring")
        data["speed_score"] = prompt("[CLIENT] Mobile Page Speed (score manually)", options=score_opts)

    # GBP
    print(f"\n  [CLIENT] Google Business Profile")
    print("  Check: complete photos, hours, description, services, recent posts?")
    data["gbp_score"] = prompt("  Score", options=score_opts)

    # Visibility
    print(f'\n  [CLIENT] Local Search Visibility')
    print(f'  Search: "{data["business_type"]} {data["business_city"]}" — is the CLIENT in the top 3 map results?')
    data["visibility_score"] = prompt("  Score", options=score_opts)

    # GEO
    print(f'\n  [CLIENT] GEO / AI Readiness')
    print(f'  Ask ChatGPT: "best {data["business_type"]} in {data["business_city"]}" — does CLIENT appear?')
    data["geo_score"] = prompt("  Score", options=score_opts)

    divider("FINDINGS")
    if auto_findings:
        print("\n  Auto-detected (included automatically):")
        for f in auto_findings: print(f"    → {f}")
    print("\n  Add your own (press Enter twice when done):")
    manual = []
    while True:
        line = input("  > ").strip()
        if line == "" and (not manual or manual[-1] == ""): break
        if line: manual.append(line)
    data["findings"] = (auto_findings + manual)[:4]

    # Auto-generate recommendations
    auto_recs = auto_recommendations(data, auto_findings + manual)
    divider("RECOMMENDATIONS")
    print("\n  Auto-generated recommendations (based on findings):")
    for i, r in enumerate(auto_recs, 1):
        print(f"    {i}. {r}")
    print("\n  Override any? (press Enter to keep, or type replacement)")
    final_recs = list(auto_recs)
    for i in range(len(final_recs)):
        override = input(f"  [{i+1}] override (Enter to keep): ").strip()
        if override:
            final_recs[i] = override
    print("\n  Add an extra recommendation? (Enter to skip)")
    extra = input("  > ").strip()
    if extra:
        final_recs.append(extra)
    data["recommendations"] = final_recs[:3]

    data["audit_date"] = date.today().strftime("%B %d, %Y")
    return data

def auto_recommendations(data, findings):
    """Generate tailored recommendations based on what was found."""
    recs = []

    seo = data.get("_seo", {})
    exists = data.get("has_website", False)
    ps = data.get("client_ps")
    seo_pct = data.get("client_seo_pct")
    gbp = data.get("gbp_score", 3)
    vis = data.get("visibility_score", 3)
    geo = data.get("geo_score", 3)

    if not exists:
        recs.append("Get a simple website up — even a one-page site puts you on the map for customers searching online. Right now you're invisible to anyone who doesn't already know you.")
    else:
        if not seo.get("city_in_title") or not seo.get("city_in_h1"):
            recs.append(f"Add '{data['business_city'].split(',')[0].strip()}' to your page title and main headline so Google knows exactly where you serve customers.")
        if not seo.get("service_mentioned"):
            recs.append(f"Make it obvious on your homepage what you do — Google and customers shouldn't have to guess you're a {data['business_type']}.")
        if ps is not None and ps < 70:
            recs.append(f"Speed up your site on mobile — it scores {ps}/100 right now. Most of your customers search on their phone, and a slow site means they leave before they even see you.")
        if seo_pct is not None and seo_pct < 80:
            recs.append("Fix the technical issues Google flagged on your site — these are invisible to visitors but they quietly hurt where you rank in search results.")
        if not seo.get("has_phone"):
            recs.append("Put your phone number on your website where people can see it. If someone has to search for how to call you, most of them won't bother.")

    if gbp <= 2:
        recs.append("Fill out your Google Business listing completely — add photos, your hours, a description of what you do, and the services you offer. It's free and it's one of the fastest ways to show up higher on Google Maps.")
    elif gbp == 3:
        recs.append("Your Google listing is set up but not fully optimized. Adding recent photos and responding to reviews can bump you up in local search results quickly.")

    if vis <= 2:
        recs.append(f"Right now you're not showing up when someone searches for '{data['business_type']} in {data['business_city'].split(',')[0].strip()}' on Google Maps. That's your highest-intent customer — they're ready to call someone. Let's make sure that someone is you.")

    if geo <= 2:
        recs.append("AI tools like ChatGPT are starting to recommend local businesses by name. You're not showing up yet — getting your online presence in order now puts you ahead of competitors who haven't figured this out.")

    # Always include a review nudge if reviews are low
    try:
        rev_count = int(data.get("review_count", 0))
        comp_rev  = int(data.get("comp_reviews", 0))
        if rev_count < 20 or (comp_rev > 0 and rev_count < comp_rev * 0.5):
            recs.append(f"Ask your happy customers to leave a Google review. {data['comp_name']} has {data.get('comp_reviews', '?')} reviews — more reviews means Google shows you first more often.")
    except (ValueError, TypeError):
        pass

    # Deduplicate and cap at 3
    seen, final = set(), []
    for r in recs:
        key = r[:40]
        if key not in seen:
            seen.add(key)
            final.append(r)
        if len(final) == 3:
            break

    return final

# ─────────────────────────────────────────────
#  LOW-LEVEL DRAWING HELPERS
# ─────────────────────────────────────────────
def rounded_rect(c, x, y, w, h, r=6, fill_color=None, stroke_color=None, stroke_width=0):
    if fill_color:   c.setFillColor(fill_color)
    if stroke_color: c.setStrokeColor(stroke_color); c.setLineWidth(stroke_width)
    else:            c.setLineWidth(0)
    p = c.beginPath()
    p.moveTo(x + r, y)
    p.lineTo(x + w - r, y)
    p.arcTo(x + w - 2*r, y, x + w, y + 2*r, startAng=-90, extent=90)
    p.lineTo(x + w, y + h - r)
    p.arcTo(x + w - 2*r, y + h - 2*r, x + w, y + h, startAng=0, extent=90)
    p.lineTo(x + r, y + h)
    p.arcTo(x, y + h - 2*r, x + 2*r, y + h, startAng=90, extent=90)
    p.lineTo(x, y + r)
    p.arcTo(x, y, x + 2*r, y + 2*r, startAng=180, extent=90)
    p.close()
    c.drawPath(p, fill=1 if fill_color else 0, stroke=1 if stroke_color else 0)

def text(c, txt, x, y, font="Helvetica", size=10, color=C_WHITE, align="left"):
    c.setFont(font, size)
    c.setFillColor(color)
    if align == "center": c.drawCentredString(x, y, txt)
    elif align == "right": c.drawRightString(x, y, txt)
    else: c.drawString(x, y, txt)

def wrap_text(c, txt, x, y, max_w, font="Helvetica", size=9, color=C_GRAY, line_h=14):
    """Simple word-wrap text block. Returns final y."""
    c.setFont(font, size)
    c.setFillColor(color)
    words = txt.split()
    line  = ""
    cy    = y
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
        cy -= line_h
    return cy

def pill(c, x, y, w, h, label, bg, text_color=C_BLACK, font="Helvetica-Bold", size=8):
    rounded_rect(c, x, y, w, h, r=h//2, fill_color=bg)
    text(c, label, x + w/2, y + h/2 - size*0.35, font=font, size=size, color=text_color, align="center")

def score_pill(c, x, y, score, mx=5):
    col = score_color(score, mx)
    lbl = score_label(score, mx)
    pill(c, x, y, 72, 18, lbl, bg=col, text_color=C_WHITE)

def score_dots(c, x, y, score, mx=5, dot_r=5, gap=14):
    """Draw filled/empty dots for score."""
    for i in range(mx):
        cx = x + i * gap
        cy = y
        filled = i < score
        col = score_color(score, mx) if filled else C_LGRAY
        c.setFillColor(col)
        c.circle(cx, cy, dot_r, fill=1, stroke=0)

# ─────────────────────────────────────────────
#  PDF BUILD
# ─────────────────────────────────────────────
def build_pdf(data, output_path):
    logo_path = ensure_logo()
    c = canvas.Canvas(output_path, pagesize=letter)

    # ── White page background ──────────────────────────────────────────────────
    c.setFillColor(C_PAGE)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Thin top bar — just a single clean line in dark gray
    c.setFillColor(C_BLACK)
    c.rect(0, PAGE_H - 3, PAGE_W, 3, fill=1, stroke=0)

    inner_w = PAGE_W - 2*PAD
    cursor  = PAGE_H - 3  # start just below top bar

    # ── HEADER BLOCK ──────────────────────────────────────────────────────────
    HDR_H = 68
    cursor -= HDR_H
    rounded_rect(c, PAD, cursor, inner_w, HDR_H, r=8, fill_color=C_DARK)

    # Business name (large, dark)
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(C_BLACK)
    c.drawString(PAD + 16, cursor + HDR_H - 30, data["business_name"])

    # Sub info
    c.setFont("Helvetica", 10)
    c.setFillColor(C_GRAY)
    c.drawString(PAD + 16, cursor + HDR_H - 48, f"{data['business_type']}  ·  {data['business_city']}")

    # Right side: "QUESO VENTURES" + doc type + date
    right_edge = PAD + inner_w - 16
    row1_y     = cursor + HDR_H - 26
    row2_y     = cursor + HDR_H - 42

    c.setFont("Helvetica-Bold", 10)
    qv_label = "Queso Ventures"
    qv_w = c.stringWidth(qv_label, "Helvetica-Bold", 10)

    if logo_path:
        LOGO_H = 14; LOGO_W = 14
        # Total width of logo + gap + text
        total_brand_w = LOGO_W + 5 + qv_w
        brand_x = right_edge - total_brand_w
        logo_y  = row1_y - 3
        c.drawImage(logo_path, brand_x, logo_y, width=LOGO_W, height=LOGO_H,
                    preserveAspectRatio=True, mask="auto")
        c.setFillColor(C_BLACK)
        c.drawString(brand_x + LOGO_W + 5, row1_y, qv_label)
    else:
        c.setFillColor(C_BLACK)
        c.drawRightString(right_edge, row1_y, qv_label)

    c.setFont("Helvetica", 8)
    c.setFillColor(C_GRAY)
    c.drawRightString(right_edge, row2_y, f"Visibility Report  ·  {data['audit_date']}")

    cursor -= 10

    # ── OVERALL SCORE + QUICK STATS ────────────────────────────────────────────
    STATS_H = 62
    cursor -= STATS_H
    rounded_rect(c, PAD, cursor, inner_w, STATS_H, r=8, fill_color=C_DARK)

    total = sum(data[k] for k in ["website_score","speed_score","gbp_score","visibility_score","geo_score"])
    total_pct = int((total / 25) * 100)
    ov_col = score_color(total, 25)

    # Overall score left block — outlined, no fill, saves ink
    c.setStrokeColor(ov_col)
    c.setLineWidth(2)
    c.roundRect(PAD + 2, cursor + 2, 86, STATS_H - 4, 6, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 26)
    c.setFillColor(ov_col)
    c.drawCentredString(PAD + 45, cursor + STATS_H/2 - 9, f"{total_pct}%")
    c.setFont("Helvetica", 7)
    c.setFillColor(C_GRAY)
    c.drawCentredString(PAD + 45, cursor + 9, "Visibility Score")

    # Stats: rating, reviews, website, speed, seo
    seo_pct = data.get("client_seo_pct")
    stats = [
        (data["review_rating"] + " ★",              "Google Rating"),
        (str(data["review_count"]),                  "Reviews"),
        ("✓ Yes" if data["has_website"] else "✗ No", "Has Website"),
        (pct_label(data.get("client_ps")),           "Phone Speed"),
        (pct_label(seo_pct),                         "SEO Score"),
    ]
    stat_x = PAD + 100
    stat_w = (inner_w - 106) / 5
    for i, (val, lbl) in enumerate(stats):
        sx = stat_x + i * stat_w
        if lbl == "Phone Speed":
            sc = pct_color(data.get("client_ps"))
        elif lbl == "SEO Score":
            sc = pct_color(seo_pct)
        elif "✓" in val:
            sc = C_GREEN
        elif "✗" in val:
            sc = C_RED
        else:
            sc = C_BLACK   # rating and reviews — dark, readable on light card
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(sc)
        c.drawCentredString(sx + stat_w/2, cursor + STATS_H/2 + 2, val)
        c.setFont("Helvetica", 7)
        c.setFillColor(C_GRAY)
        c.drawCentredString(sx + stat_w/2, cursor + STATS_H/2 - 14, lbl)
        if i < 4:
            c.setStrokeColor(C_LGRAY)
            c.setLineWidth(0.5)
            c.line(sx + stat_w, cursor + 12, sx + stat_w, cursor + STATS_H - 12)

    cursor -= 10

    # ── SCORE BREAKDOWN + COMPETITOR (two columns) ─────────────────────────────
    COL1_W = inner_w * 0.54
    COL2_W = inner_w * 0.43
    COL_GAP = inner_w * 0.03

    categories = [
        ("website_score",    "Website",                 "Does it load? Does it say what you do & where?"),
        ("speed_score",      "Mobile Speed",            "How fast your site loads on a phone"),
        ("gbp_score",        "Google Listing",          "Is your Google Business profile complete?"),
        ("visibility_score", "Google Maps",             "Do customers find you when they search locally?"),
        ("geo_score",        "AI Search",               "Do AI tools like ChatGPT recommend you?"),
    ]

    ROW_H   = 38
    SEC_LBL = 16
    BREAK_H = 8
    COL1_CONTENT_H = SEC_LBL + BREAK_H + len(categories) * (ROW_H + 3) - 3

    # Competitor section height
    COMP_ROWS   = 6   # header + 5 data rows
    COMP_ROW_H  = 24
    COL2_CONTENT_H = SEC_LBL + BREAK_H + COMP_ROW_H + (COMP_ROWS - 1) * COMP_ROW_H + 24  # +24 for name caption below

    COL_H = max(COL1_CONTENT_H, COL2_CONTENT_H) + 16

    cursor -= COL_H

    # ── Left column: Score breakdown ──
    lx = PAD
    ly = cursor
    # Section label
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(C_GRAY)
    c.drawString(lx, ly + COL_H - SEC_LBL, "VISIBILITY BREAKDOWN")

    row_y = ly + COL_H - SEC_LBL - BREAK_H - ROW_H
    for key, name, note in categories:
        sc = data[key]

        # Row card
        rounded_rect(c, lx, row_y, COL1_W, ROW_H, r=6, fill_color=C_DARK)

        # Score dot cluster (left side of card)
        score_dots(c, lx + 14, row_y + ROW_H/2, sc, dot_r=4, gap=11)

        # Name + note — shifted right to avoid dot overlap
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(C_BLACK)
        c.drawString(lx + 75, row_y + ROW_H/2 + 3, name)
        c.setFont("Helvetica", 7)
        c.setFillColor(C_GRAY)
        c.drawString(lx + 75, row_y + ROW_H/2 - 9, note)

        row_y -= (ROW_H + 3)

    # ── Right column: Competitor ──
    cx = PAD + COL1_W + COL_GAP
    cy = cursor

    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(C_GRAY)
    c.drawString(cx, cy + COL_H - SEC_LBL, "VS. COMPETITOR")

    # Header row — light gray fill, dark text (ink-friendly, readable)
    COMP_HDR_H = 24
    tbl_y = cy + COL_H - SEC_LBL - BREAK_H - COMP_HDR_H
    rounded_rect(c, cx, tbl_y, COL2_W, COMP_HDR_H, r=6, fill_color=C_LGRAY)

    cw = COL2_W / 3
    for i, lbl in enumerate(["", "You", "Them"]):
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(C_BLACK)
        c.drawCentredString(cx + (i + 0.5) * cw, tbl_y + COMP_HDR_H/2 - 3.5, lbl)

    comp_rows_data = [
        ("Rating",      str(data["review_rating"]),               str(data["comp_rating"])),
        ("Reviews",     str(data["review_count"]),                str(data["comp_reviews"])),
        ("Website",     "Yes" if data["has_website"] else "No",   "Yes" if data["comp_has_site"] else "No"),
        ("Phone Speed", pct_label(data.get("client_ps")),         pct_label(data.get("comp_ps"))),
        ("SEO Score",   pct_label(data.get("client_seo_pct")),    pct_label(data.get("comp_seo_pct"))),
    ]

    dr_y = tbl_y - COMP_ROW_H
    for ri, (label, v1, v2) in enumerate(comp_rows_data):
        is_last = ri == len(comp_rows_data) - 1
        bg = C_DARK if ri % 2 == 0 else C_LGRAY

        if is_last:
            # Use roundRect for the last row to get rounded bottom corners
            c.setFillColor(bg)
            c.roundRect(cx, dr_y, COL2_W, COMP_ROW_H, 6, fill=1, stroke=0)
            # Square off the top of this rounded rect
            c.rect(cx, dr_y + COMP_ROW_H/2, COL2_W, COMP_ROW_H/2, fill=1, stroke=0)
        else:
            rounded_rect(c, cx, dr_y, COL2_W, COMP_ROW_H, r=0, fill_color=bg)

        c.setFont("Helvetica", 8)
        c.setFillColor(C_GRAY)
        c.drawString(cx + 8, dr_y + COMP_ROW_H/2 - 3.5, label)

        # Color-code percentage rows
        if label in ("Phone Speed", "SEO Score"):
            try: v1_col = pct_color(int(v1.replace("/100","")))
            except: v1_col = C_BLACK
            try: v2_col = pct_color(int(v2.replace("/100","")))
            except: v2_col = C_BLACK
        else:
            v1_col = v2_col = C_BLACK

        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(v1_col)
        c.drawCentredString(cx + cw * 1.5, dr_y + COMP_ROW_H/2 - 3.5, v1)
        c.setFillColor(v2_col)
        c.drawCentredString(cx + cw * 2.5, dr_y + COMP_ROW_H/2 - 3.5, v2)

        dr_y -= COMP_ROW_H

    # Competitor name caption below table — left aligned, truncated to fit
    caption = f"* Them = {data['comp_name']}"
    c.setFont("Helvetica", 7)
    while c.stringWidth(caption, "Helvetica", 7) > COL2_W and len(caption) > 12:
        caption = caption[:-2]
    if not caption.endswith(data['comp_name']):
        caption = caption.rstrip() + "…"
    c.setFillColor(C_GRAY)
    c.drawString(cx, dr_y - 2, caption)

    cursor -= 10

    # ── FINDINGS ──────────────────────────────────────────────────────────────
    if data["findings"]:
        cursor -= 8
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(C_GRAY)
        c.drawString(PAD, cursor, "WHAT WE FOUND")
        cursor -= 6

        # Core Web Vitals pills
        cwv = data.get("client_cwv", {})
        has_cwv_data = cwv and any(
            m.get("rating", "N/A") != "N/A"
            for m in cwv.values()
        )
        if has_cwv_data:
            CWV_LABELS     = {"lcp": "Page Load", "fid": "Response Time", "cls": "Visual Stability"}
            RATING_DISPLAY = {"FAST": "Good", "AVERAGE": "Fair", "SLOW": "Slow", "N/A": "N/A"}
            RATING_COL     = {"FAST": C_GREEN, "AVERAGE": C_ORANGE, "SLOW": C_RED, "N/A": C_GRAY}
            PILL_H   = 20
            PILL_PAD = 8
            GAP      = 8
            cursor  -= PILL_H + 6

            px = PAD
            for key, lbl_text in CWV_LABELS.items():
                metric      = cwv.get(key, {})
                rating      = metric.get("rating", "N/A")
                rating_disp = RATING_DISPLAY.get(rating, rating)
                col         = RATING_COL.get(rating, C_GRAY)

                lbl_w    = c.stringWidth(lbl_text,    "Helvetica-Bold", 7)
                rating_w = c.stringWidth(rating_disp, "Helvetica-Bold", 7)
                pill_w   = PILL_PAD + lbl_w + GAP + rating_w + PILL_PAD

                rounded_rect(c, px, cursor, pill_w, PILL_H, r=PILL_H//2, fill_color=C_DARK)

                c.setFont("Helvetica-Bold", 7)
                c.setFillColor(C_BLACK)
                c.drawString(px + PILL_PAD, cursor + PILL_H/2 - 3.5, lbl_text)

                badge_x = px + PILL_PAD + lbl_w + GAP
                badge_w = rating_w + PILL_PAD
                rounded_rect(c, badge_x - 4, cursor + 3, badge_w + 4, PILL_H - 6, r=5, fill_color=col)
                c.setFont("Helvetica-Bold", 7)
                c.setFillColor(C_WHITE)
                c.drawString(badge_x, cursor + PILL_H/2 - 3.5, rating_disp)

                px += pill_w + 8

        for finding in data["findings"][:4]:
            words   = finding.split()
            chars   = sum(len(w)+1 for w in words)
            lines   = max(1, int(chars * 7.5 / (inner_w - 50)) + 1)
            fnd_h   = max(28, lines * 13 + 10)

            cursor -= fnd_h
            rounded_rect(c, PAD, cursor, inner_w, fnd_h, r=6, fill_color=C_DARK)

            # Gray left accent
            c.setFillColor(C_GRAY)
            c.roundRect(PAD, cursor, 4, fnd_h, 2, fill=1, stroke=0)

            # Text — starts further right, no icon
            wrap_text(c, finding, PAD + 16, cursor + fnd_h - 11,
                      inner_w - 30, font="Helvetica", size=8.5,
                      color=C_BLACK, line_h=13)
            cursor -= 4

    # ── RECOMMENDATIONS ────────────────────────────────────────────────────────
    if data["recommendations"]:
        cursor -= 10
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(C_GRAY)
        c.drawString(PAD, cursor, "HOW TO FIX IT")
        cursor -= 8

        n     = len(data["recommendations"])
        rec_w = (inner_w - (n-1)*6) / n

        words_all = [r.split() for r in data["recommendations"]]
        max_lines = max(max(1, int(sum(len(w)+1 for w in ws) * 7.5 / (rec_w - 24)) + 1)
                        for ws in words_all)
        rec_h = max(70, max_lines * 13 + 48)
        cursor -= rec_h

        for i, rec in enumerate(data["recommendations"]):
            rx = PAD + i * (rec_w + 6)
            rounded_rect(c, rx, cursor, rec_w, rec_h, r=8, fill_color=C_DARK)

            # Number badge — dark top
            badge_h = 28
            rounded_rect(c, rx, cursor + rec_h - badge_h, rec_w, badge_h, r=8, fill_color=C_BLACK)
            c.setFillColor(C_BLACK)
            c.rect(rx, cursor + rec_h - badge_h, rec_w, badge_h/2, fill=1, stroke=0)

            c.setFont("Helvetica-Bold", 14)
            c.setFillColor(C_WHITE)
            c.drawCentredString(rx + rec_w/2, cursor + rec_h - 19, str(i+1))

            text_top = cursor + rec_h - badge_h - 14
            wrap_text(c, rec, rx + 12, text_top,
                      rec_w - 24, font="Helvetica", size=8.5,
                      color=C_BLACK, line_h=13)

        cursor -= 8

    # ── FOOTER ────────────────────────────────────────────────────────────────
    c.setStrokeColor(C_LGRAY)
    c.setLineWidth(0.5)
    c.line(PAD, 28, PAGE_W - PAD, 28)
    c.setFont("Helvetica", 7)
    c.setFillColor(C_GRAY)
    c.drawCentredString(PAGE_W / 2, 18, f"{CONTACT_EMAIL}  ·  {CONTACT_PHONE}")

    c.save()

# ─────────────────────────────────────────────
#  COLLECT + BUILD
# ─────────────────────────────────────────────
def main():
    data = collect_data()
    safe = data["business_name"].replace(" ","_").replace("/","-").lower()
    fn   = f"audit_{safe}_{date.today().strftime('%Y%m%d')}.pdf"
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    out = os.path.join(desktop if os.path.exists(desktop) else os.getcwd(), fn)
    print(f"\n  Building PDF...", end=" ", flush=True)
    build_pdf(data, out)
    print("done.")
    print(f"\n  ✓ Saved: {out}\n")

if __name__ == "__main__":
    main()