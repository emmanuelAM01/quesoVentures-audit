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
C_DARK   = colors.HexColor("#FFFFFF")   # card bg (white, ink-friendly)
C_YELLOW = colors.HexColor("#FFD100")   # yellow accent (used sparingly)
C_WHITE  = colors.HexColor("#FFFFFF")
C_GRAY   = colors.HexColor("#666666")   # muted text
C_LGRAY  = colors.HexColor("#D8D8D5")   # borders / dividers
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

def geo_label(score):
    """Convert 1-5 geo score to outcome language for the competitor table."""
    if score is None:  return "N/A"
    if score >= 4:     return "Shows up"
    if score == 3:     return "Sometimes"
    return "Doesn't show up"

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

def lookup_places_gbp(name: str, city: str) -> dict:
    """
    Looks up a business by name+city using Google Places API (New) text search.
    Returns dict with rating, review_count, photo_count or empty dict on failure.
    """
    api_key = os.environ.get("PLACES_API_KEY", "")
    if not api_key:
        return {}
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type":     "application/json",
        "X-Goog-Api-Key":   api_key,
        "X-Goog-FieldMask": "places.displayName,places.rating,places.userRatingCount,places.photos",
    }
    body = {
        "textQuery":      f"{name} {city}",
        "languageCode":   "en",
        "maxResultCount": 1,
    }
    try:
        r = requests.post(url, json=body, headers=headers, timeout=10)
        places = r.json().get("places", [])
        if not places:
            return {}
        p = places[0]
        return {
            "rating":       p.get("rating"),
            "review_count": p.get("userRatingCount", 0),
            "photo_count":  len(p.get("photos", [])),
        }
    except Exception:
        return {}


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

def consolidate_findings(findings, data):
    """
    Always returns exactly 4 findings.
    Slots 1-3: dynamic findings from what we detected, filled with hardcoded
               universal truths if short. Slot 4: AI finding, always, no exceptions.
    """

    # ── The 4 fixed strings ───────────────────────────────────────────────────

    AI_FINDING = (
        "You don't show up when potential clients search for your services using AI — "
        "these tools look for businesses with clear location signals, consistent citations, "
        "and content structured around how people actually search. This is a new and emerging way to search."
    )

    # Universal fillers — true for every local service business.
    # They name a real problem, imply invisible complexity, position you as the solver.
    FILLERS = [
        (
            "Your review profile isn't being leveraged to its full potential — how reviews are "
            "structured, responded to, and distributed across platforms directly affects how "
            "search engines and AI tools rank your business against competitors"
        ),
        (
            "Appearing in the top 3 Google Maps results requires more than just having a listing. "
            "Businesses that consistently show up there have signals working behind the "
            "scenes that most business owners don't know exist"
        ),
        (
            "The way people search for your type of business has shifted — most high-intent "
            "clients now start with a question, not a keyword, and the businesses set up to "
            "answer those questions are the ones getting the call"
        ),
    ]

    # ── Build slots 1-3 from dynamic findings ────────────────────────────────

    # Deduplicate city-related findings into one
    CITY_KEYS = [
        "search engines and ai tools can't confirm",
        "can't confirm your business serves",
        "city name is missing",
        "city name isn't in",
        "city is barely mentioned",
        "not in the conversation",
    ]
    NOISE_KEYS = [
        "loads code it doesn't use",
        "loads unused styling files",
        "text files aren't compressed",
        "slow-loading code is delaying",
        "page briefly freezes",
        "main page content takes too long",
    ]

    city_f  = [f for f in findings if any(k in f.lower() for k in CITY_KEYS)]
    noise_f = [f for f in findings if any(k.lower() in f.lower() for k in NOISE_KEYS)]
    other_f = [f for f in findings if f not in city_f and f not in noise_f]

    slots = []

    # Add city finding (collapsed to one if multiple)
    if city_f:
        slots.append(
            "Search engines and AI tools can't confirm your business serves this area — "
            "when someone nearby searches for what you offer, you're not in the conversation"
        )

    # Add other real findings
    for f in other_f:
        if len(slots) >= 3:
            break
        if not any(f[:35].lower() in s.lower() for s in slots):
            slots.append(f)

    # Fill remaining slots 1-3 with universal fillers
    filler_idx = 0
    while len(slots) < 3 and filler_idx < len(FILLERS):
        candidate = FILLERS[filler_idx]
        if not any(candidate[:35].lower() in s.lower() for s in slots):
            slots.append(candidate)
        filler_idx += 1

    # ── Slot 4: AI finding — always ──────────────────────────────────────────
    slots.append(AI_FINDING)

    return slots[:4]

def _phone_finding(html):
    """
    Distinguish between no phone at all vs phone buried/hard to find.
    Hard to find = phone exists in HTML but not in a prominent location
    (not in header, hero, or nav — only in footer or contact page).
    """
    if not html:
        return "missing"
    from bs4 import BeautifulSoup as _BS
    import re as _re
    soup = _BS(html, "html.parser")
    phone_pattern = _re.compile(r'\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4}')
    # Check prominent zones first
    prominent = ""
    for tag in ["header", "nav"]:
        el = soup.find(tag)
        if el: prominent += el.get_text()
    # Check first 2 headings and hero area (first 3000 chars of body text)
    body_text = soup.get_text()[:3000]
    prominent += body_text
    if phone_pattern.search(prominent):
        return "visible"       # phone easy to find
    # Check rest of page
    if phone_pattern.search(soup.get_text()):
        return "buried"        # phone exists but hard to find
    return "missing"           # no phone at all


def auto_site_score(exists, seo, html=None):
    if not exists: return 1, ["Your business has no website — search engines and AI tools have nothing to find, index, or recommend"]
    issues, score = [], 5
    if not seo.get("city_in_title"):    score-=0.5; issues.append("Search engines and AI tools can't confirm your business serves this area — when someone nearby searches for what you offer, you're not in the conversation")
    if not seo.get("city_in_h1"):       score-=0.5; issues.append("Search engines and AI tools can't confirm your business serves this area — when someone nearby searches for what you offer, you're not in the conversation")
    if not seo.get("city_in_content"):  score-=1;   issues.append("Search engines and AI tools can't confirm your business serves this area — when someone nearby searches for what you offer, you're not in the conversation")
    if not seo.get("service_mentioned"):score-=1;   issues.append("Your website doesn't clearly communicate what you do — Google and AI tools can't recommend a business they can't categorize")
    if not seo.get("is_mobile_ready"):  score-=1;   issues.append("Most of your potential clients are searching on their phone — a slow site means they're gone before they ever see you, and search engines take note")
    phone_status = _phone_finding(html)
    if phone_status == "missing":
        score-=0.5; issues.append("Visitors who are ready to book hit a wall — when the path to contact isn't clear, users leave and search engines can't signal your business as the obvious next step")
    elif phone_status == "buried":
        score-=0.25; issues.append("Visitors who are ready to book hit a wall — when the path to contact isn't clear, users leave and search engines can't signal your business as the obvious next step")
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
    ws_score, ws_issues = auto_site_score(exists, seo, html=html)
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
        if client_ps < 50:   auto_findings.append(f"Your site takes too long to load on phones ({client_ps}/100). Visitors are leaving your site before it even opens.")
        elif client_ps < 70: auto_findings.append(f"Your site is slower than average on phones ({client_ps}/100). This costs you customers because majority of people browse on their phones.")
    if client_seo_pct is not None and client_seo_pct < 80:
        auto_findings.append(f"Google found technical issues on your site that make it harder to rank ({client_seo_pct}/100)")
    # Add top Lighthouse audit failures as findings
    for audit_str in client_audits:
        auto_findings.append(audit_str)

    # Rating + review count via Places API (same free API as the pipeline)
    print("  Fetching GBP data from Places API...", end=" ", flush=True)
    gbp_data = lookup_places_gbp(data["business_name"], data["business_city"])
    if gbp_data.get("rating"):
        rat = str(gbp_data["rating"])
        rev = str(gbp_data["review_count"])
        print(f"rating={rat}  reviews={rev}")
        ov_rat = prompt(f"  Star rating (Enter to keep {rat})", default=rat)
        ov_rev = prompt(f"  Review count (Enter to keep {rev})", default=rev)
        data["review_rating"] = ov_rat
        data["review_count"]  = ov_rev
    else:
        print("not found")
        print("  Enter manually (check Google for this business):")
        data["review_rating"] = prompt("  Star rating (e.g. 4.8)", default="?")
        data["review_count"]  = prompt("  Review count (e.g. 270)", default="0")

    print(f"\n  Client: website={'✓' if exists else '✗'}  perf={client_ps or 'N/A'}  seo={client_seo_pct or 'N/A'}  rating={data['review_rating']}  reviews={data['review_count']}")

    divider("COMPETITOR")
    print(f'  Search Google: "{data["business_type"]} {data["business_city"]}" — pick the top result that is NOT the client.\n')
    data["comp_name"] = prompt("Competitor name", default="N/A")

    # Auto-fetch competitor rating + reviews via Places API
    print("  Fetching competitor GBP data...", end=" ", flush=True)
    comp_gbp = lookup_places_gbp(data["comp_name"], data["business_city"])
    if comp_gbp.get("rating"):
        c_rat = str(comp_gbp["rating"])
        c_rev = str(comp_gbp["review_count"])
        print(f"rating={c_rat}  reviews={c_rev}")
        ov_crat = prompt(f"  Competitor star rating (Enter to keep {c_rat})", default=c_rat)
        ov_crev = prompt(f"  Competitor review count (Enter to keep {c_rev})", default=c_rev)
        data["comp_rating"]  = ov_crat
        data["comp_reviews"] = ov_crev
    else:
        print("not found")
        data["comp_rating"]  = prompt("  Competitor star rating", default="?")
        data["comp_reviews"] = prompt("  Competitor review count", default="?")

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

    print(f'\n  [COMPETITOR] AI Search Visibility')
    print(f'  Ask ChatGPT: "best {data["business_type"]} in {data["business_city"].split(",")[0].strip()}" — does the COMPETITOR appear?')
    _cgeo_opts = ["No — not mentioned at all", "Sometimes — mentioned but not by name", "Yes — recommended by name"]
    _cgeo_ans  = prompt("  Do they show up?", options=_cgeo_opts)
    data["comp_geo_score"] = {1: 1, 2: 3, 3: 5}[_cgeo_ans]

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

    # GBP — 4 options covering the "complete but wrong" case
    print(f"\n  [CLIENT] Business Profile (Google Business)")
    print("  Open their Google listing and check how it looks to a customer.")
    _gbp_opts = [
        "Not set up — profile is bare or missing entirely",
        "Filled out but off — info is there but outdated, inaccurate, or missing key things",
        "Set up but basic — correct info, nothing standing out, blends in with everyone else",
        "Well set up — accurate, has photos, services listed, actively maintained",
    ]
    _gbp_ans  = prompt("  How does their profile look?", options=_gbp_opts)
    data["gbp_score"] = {1: 1, 2: 2, 3: 3, 4: 5}[_gbp_ans]

    # Visibility — plain language
    print(f'\n  [CLIENT] Google Maps Visibility')
    print(f'  Search Google: "{data["business_type"]} {data["business_city"]}" — does the client show up in the map results?')
    _vis_opts = ["No — not in map results at all", "Sometimes — appears but not in top 3", "Yes — shows up in the top 3"]
    _vis_ans  = prompt("  Do they show up?", options=_vis_opts)
    data["visibility_score"] = {1: 1, 2: 3, 3: 5}[_vis_ans]

    # GEO — plain language
    print(f'\n  [CLIENT] AI Search Visibility')
    print(f'  Ask ChatGPT: "best {data["business_type"]} in {data["business_city"].split(",")[0].strip()}" — does the client appear?')
    _geo_opts = ["No — not mentioned at all", "Sometimes — mentioned but not by name", "Yes — recommended by name"]
    _geo_ans  = prompt("  Do they show up?", options=_geo_opts)
    data["geo_score"] = {1: 1, 2: 3, 3: 5}[_geo_ans]

    # Store phone status for findings logic
    data["_phone_status"] = _phone_finding(html) if html else "missing"

    divider("FINDINGS")
    data["findings"] = consolidate_findings(auto_findings, data)
    if data["findings"]:
        print("\n  Auto-detected findings:")
        for f in data["findings"]: print(f"    → {f}")

    # HOW TO FIX IT removed from PDF — that's the in-person conversation
    data["recommendations"] = []
    data["fix_pairs"] = []

    data["audit_date"] = date.today().strftime("%B %d, %Y")
    return data

def auto_fix_pairs(data, findings):
    """
    Generate (problem, fix) pairs for the combined What We're Fixing section.
    Each pair is one row: left = what's wrong in plain English, right = what I'm doing about it.
    Returns list of (problem, fix) tuples, max 4.
    """
    pairs = []
    seo    = data.get("_seo", {})
    exists = data.get("has_website", False)
    ps     = data.get("client_ps")
    seo_pct= data.get("client_seo_pct")
    gbp    = data.get("gbp_score", 3)
    vis    = data.get("visibility_score", 3)
    geo    = data.get("geo_score", 3)
    city   = data.get("business_city", "your city").split(",")[0].strip()
    btype  = data.get("business_type", "your business")

    if not exists:
        pairs.append((
            "You have no website — anyone searching for you online can't find you at all",
            "I'll build you a simple, fast site that tells Google who you are and where you are"
        ))
    else:
        if not seo.get("city_in_title") or not seo.get("city_in_h1") or not seo.get("city_in_content"):
            pairs.append((
                f"Your site doesn't clearly say you're in {city} — Google can't confirm you're a local business",
                f"I'll add {city} to your page title, headline, and content so Google knows exactly where you serve clients"
            ))
        if not seo.get("service_mentioned"):
            pairs.append((
                f"It's not clear on your site that you're a {btype} — Google and new visitors have to guess",
                "I'll make your service obvious on the homepage so Google and customers immediately know what you offer"
            ))
        if ps is not None and ps < 70:
            pairs.append((
                f"Your site loads too slowly on phones ({ps}/100) — most people leave before it opens",
                f"I'll compress assets, defer scripts, and fix the technical bottlenecks slowing your site down. Not a DIY fix — but the right work moves that score from {ps} to 85+ fast"
            ))
        if not seo.get("is_mobile_ready"):
            pairs.append((
                "Your site doesn't display correctly on phones — that's how most of your customers search",
                "I'll make your site fully mobile-friendly so it looks right on every screen"
            ))
        phone_status = data.get("_phone_status", "visible")
        if phone_status == "missing":
            pairs.append((
                "There's no phone number on your site — someone ready to book can't call you",
                "I'll add your number in a visible spot so customers can reach you in one tap"
            ))
        elif phone_status == "buried":
            pairs.append((
                "Your phone number is hard to find — most people won't hunt for it",
                "I'll move your number to the top of every page so it's impossible to miss"
            ))

    if gbp <= 2:
        pairs.append((
            "Your Google Business profile is incomplete — Google ranks complete profiles higher in Maps",
            "I'll fill out your profile with photos, hours, services, and a description to push you up in local results"
        ))
    elif gbp == 3:
        pairs.append((
            "Your Google listing is set up but not fully built out — you're leaving ranking points on the table",
            "I'll add recent photos and optimize your listing so you show up higher when people search nearby"
        ))

    if geo <= 2:
        pairs.append((
            "You don't show up when people ask AI to recommend a " + btype + " in " + city,
            "I'll build the structured data and local citations that AI tools use to decide who to recommend"
        ))
    elif geo == 3:
        pairs.append((
            "You show up inconsistently on AI search — not reliably recommended by name",
            "I'll strengthen your citation signals and content authority so AI tools recommend you every time"
        ))

    try:
        rev_count = int(data.get("review_count", 0))
        comp_rev  = int(data.get("comp_reviews", 0))
        if rev_count < 20 or (comp_rev > 0 and rev_count < comp_rev * 0.5):
            pairs.append((
                f"You have fewer reviews than your competitor — Google shows businesses with more reviews first",
                f"I'll set up a simple system to get your happy customers leaving reviews automatically"
            ))
    except (ValueError, TypeError):
        pass

    # Deduplicate and cap at 4 pairs
    seen, final = set(), []
    for p, f in pairs:
        key = p[:40]
        if key not in seen:
            seen.add(key)
            final.append((p, f))
        if len(final) == 4:
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

    inner_w    = PAGE_W - 2*PAD
    CTA_H      = 58   # matches CTA_H_NEW in drawing section
    CTA_PAD    = 16   # matches BOT_MARGIN
    AUTH_H_RSV = 78
    AUTH_GAP   = 16   # matches BOT_MARGIN
    PAGE_BOT   = CTA_PAD + CTA_H + AUTH_GAP + AUTH_H_RSV + 10
    cursor     = PAGE_H - 24   # tighter top margin
    SEC_GAP    = 10   # uniform gap before every section label
    LBL_GAP    = 6    # uniform gap between section label and first card

    # ── HEADER BLOCK ──────────────────────────────────────────────────────────
    HDR_H = 56
    cursor -= HDR_H
    rounded_rect(c, PAD, cursor, inner_w, HDR_H, r=8, fill_color=C_WHITE, stroke_color=C_LGRAY, stroke_width=0.5)

    # Business name (large, dark)
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(C_BLACK)
    c.drawString(PAD + 16, cursor + HDR_H - 24, data["business_name"])

    # Sub info
    c.setFont("Helvetica", 9)
    c.setFillColor(C_GRAY)
    c.drawString(PAD + 16, cursor + HDR_H - 40, f"{data['business_type']}  ·  {data['business_city']}")

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
    STATS_H = 48
    cursor -= STATS_H
    rounded_rect(c, PAD, cursor, inner_w, STATS_H, r=8, fill_color=C_DARK, stroke_color=C_LGRAY, stroke_width=0.5)

    total = sum(data[k] for k in ["website_score","speed_score","gbp_score","visibility_score","geo_score"])
    total_pct = int((total / 25) * 100)
    ov_col = score_color(total, 25)

    # Overall score left block
    c.setStrokeColor(ov_col)
    c.setLineWidth(2)
    c.roundRect(PAD + 2, cursor + 2, 72, STATS_H - 4, 6, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(ov_col)
    c.drawCentredString(PAD + 38, cursor + STATS_H/2 - 6, f"{total_pct + 10}%")
    c.setFont("Helvetica", 6)
    c.setFillColor(C_GRAY)
    c.drawCentredString(PAD + 38, cursor + 7, "Visibility Score")

    # Stats: rating, reviews, speed, seo
    seo_pct = data.get("client_seo_pct")
    stats = [
        (data["review_rating"] + " ★", "Google Rating"),
        (str(data["review_count"]),     "Reviews"),
        (pct_label(data.get("client_ps")), "Mobile Speed"),
        (pct_label(seo_pct),            "SEO Score"),
    ]
    stat_x = PAD + 86
    stat_w = (inner_w - 92) / 4
    for i, (val, lbl) in enumerate(stats):
        sx = stat_x + i * stat_w
        if lbl == "Mobile Speed":
            sc = pct_color(data.get("client_ps"))
        elif lbl == "SEO Score":
            sc = pct_color(seo_pct)
        else:
            sc = C_BLACK
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(sc)
        c.drawCentredString(sx + stat_w/2, cursor + STATS_H/2 + 2, val)
        c.setFont("Helvetica", 6)
        c.setFillColor(C_GRAY)
        c.drawCentredString(sx + stat_w/2, cursor + STATS_H/2 - 11, lbl)
        if i < 3:
            c.setStrokeColor(C_LGRAY)
            c.setLineWidth(0.5)
            c.line(sx + stat_w, cursor + 8, sx + stat_w, cursor + STATS_H - 8)

    cursor -= 8

    # ── SCORE BREAKDOWN + COMPETITOR (two columns) ─────────────────────────────
    COL1_W = inner_w * 0.50
    COL2_W = inner_w * 0.47
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

    # Competitor section height — 7 rows (header + 6 data) + verdict sentence
    COMP_ROWS   = 7   # header + 6 data rows
    COMP_ROW_H  = 23  # tighter rows to keep column height controlled
    VERDICT_H   = 22  # space for the verdict sentence below caption
    COL2_CONTENT_H = SEC_LBL + BREAK_H + COMP_ROW_H + (COMP_ROWS - 1) * COMP_ROW_H + 24 + VERDICT_H

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
        rounded_rect(c, lx, row_y, COL1_W, ROW_H, r=6, fill_color=C_DARK, stroke_color=C_LGRAY, stroke_width=0.5)

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

    # Header row — rounded top only, square bottom so it joins the rows cleanly
    COMP_HDR_H = 24
    tbl_y = cy + COL_H - SEC_LBL - BREAK_H - COMP_HDR_H
    r = 6
    # Draw rounded-top-only shape manually
    c.setFillColor(C_WHITE)
    c.setStrokeColor(C_BLACK)
    c.setLineWidth(0.8)
    p = c.beginPath()
    p.moveTo(cx + r, tbl_y + COMP_HDR_H)
    p.arcTo(cx, tbl_y + COMP_HDR_H - 2*r, cx + 2*r, tbl_y + COMP_HDR_H, startAng=90, extent=90)
    p.lineTo(cx, tbl_y)
    p.lineTo(cx + COL2_W, tbl_y)
    p.lineTo(cx + COL2_W, tbl_y + COMP_HDR_H - r)
    p.arcTo(cx + COL2_W - 2*r, tbl_y + COMP_HDR_H - 2*r, cx + COL2_W, tbl_y + COMP_HDR_H, startAng=0, extent=90)
    p.close()
    c.drawPath(p, fill=1, stroke=1)

    cw = COL2_W / 3
    for i, lbl in enumerate(["", "You", "Them"]):
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(C_BLACK)
        c.drawCentredString(cx + (i + 0.5) * cw, tbl_y + COMP_HDR_H/2 - 3.5, lbl)

    def ai_label(score):
        if score is None: return "N/A"
        if score >= 4:    return "Shows up"
        if score == 3:    return "Sometimes"
        return "Not showing up"

    def vis_label(score):
        """Search visibility — are they showing up when people search?"""
        if score is None: return "N/A"
        if score >= 4:    return "Visible"
        if score == 3:    return "Inconsistent"
        return "Missing"

    def gbp_label(score):
        """First impression — does the profile make people want to call?"""
        if score is None: return "N/A"
        if score >= 5:    return "Strong"
        if score >= 3:    return "Basic"
        if score >= 2:    return "Needs work"
        return "Incomplete"

    comp_rows_data = [
        ("Google Rating",      str(data["review_rating"]),        str(data["comp_rating"])),
        ("Review Count",       str(data["review_count"]) + " reviews", str(data["comp_reviews"]) + " reviews"),
        ("Phone Experience",   pct_label(data.get("client_ps")), pct_label(data.get("comp_ps"))),
        ("Search Visibility",  vis_label(data.get("visibility_score")), vis_label(5)),
        ("First Impression",   gbp_label(data.get("gbp_score")), gbp_label(5)),
        ("Found on AI Search", ai_label(data.get("geo_score")),  ai_label(data.get("comp_geo_score"))),
    ]

    dr_y = tbl_y - COMP_ROW_H
    for ri, (label, v1, v2) in enumerate(comp_rows_data):
        is_last = ri == len(comp_rows_data) - 1
        r_val = 6 if is_last else 0
        top_r = 0  # rows always square on top

        # White fill, light border, rounded only on bottom of last row
        c.setFillColor(C_WHITE)
        c.setStrokeColor(C_LGRAY)
        c.setLineWidth(0.5)
        if is_last:
            c.roundRect(cx, dr_y, COL2_W, COMP_ROW_H, r_val, fill=1, stroke=1)
            c.setFillColor(C_WHITE)
            c.rect(cx, dr_y + COMP_ROW_H/2, COL2_W, COMP_ROW_H/2, fill=1, stroke=0)
            # redraw border on top half
            c.setStrokeColor(C_LGRAY)
            c.setLineWidth(0.5)
            c.line(cx, dr_y + COMP_ROW_H, cx + COL2_W, dr_y + COMP_ROW_H)
            c.line(cx, dr_y, cx, dr_y + COMP_ROW_H)
            c.line(cx + COL2_W, dr_y, cx + COL2_W, dr_y + COMP_ROW_H)
        else:
            c.rect(cx, dr_y, COL2_W, COMP_ROW_H, fill=1, stroke=1)

        c.setFont("Helvetica", 8)
        c.setFillColor(C_GRAY)
        c.drawString(cx + 8, dr_y + COMP_ROW_H/2 - 3.5, label)

        # Color-code rows by type
        if label == "Phone Experience":
            try: v1_col = pct_color(int(v1.replace("/100","")))
            except: v1_col = C_BLACK
            try: v2_col = pct_color(int(v2.replace("/100","")))
            except: v2_col = C_BLACK
        elif label == "Found on AI Search":
            def _ai_col(v):
                if v == "Shows up":    return C_GREEN
                if v == "Sometimes":   return C_ORANGE
                return C_RED
            v1_col = _ai_col(v1)
            v2_col = _ai_col(v2)
        elif label in ("Search Visibility", "First Impression"):
            def _outcome_col(v):
                if v in ("Visible", "Strong"):       return C_GREEN
                if v in ("Inconsistent", "Basic"):   return C_ORANGE
                return C_RED
            v1_col = _outcome_col(v1)
            v2_col = _outcome_col(v2)
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

    # Verdict sentence — ties the table to a business outcome
    comp_short = data['comp_name'].split()[0:3]
    comp_short = " ".join(comp_short)
    verdict = (
        f"{comp_short} is showing up in places you aren't yet — "
        "every search where they appear and you don't is a client "
        "choosing them by default. That's your room for growth."
    )
    c.setFont("Helvetica", 7)
    c.setFillColor(C_BLACK)
    # Word-wrap verdict into the column width
    words = verdict.split()
    line, vy = "", dr_y - 14
    for w in words:
        test = (line + " " + w).strip()
        if c.stringWidth(test, "Helvetica", 7) <= COL2_W:
            line = test
        else:
            c.drawString(cx, vy, line)
            vy -= 10
            line = w
    if line:
        c.drawString(cx, vy, line)

    # ── WHAT WE FOUND ─────────────────────────────────────────────────────────
    if data.get("findings"):
        cursor -= SEC_GAP
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(C_GRAY)
        c.drawString(PAD, cursor, "WHAT WE FOUND")
        cursor -= LBL_GAP

        # Calculate a shared card height that fits all 4 findings in available space
        available_h = cursor - PAGE_BOT - 10
        card_gap    = 4
        n_findings  = min(4, len(data["findings"]))
        shared_h    = max(34, (available_h - (n_findings - 1) * card_gap) // n_findings)

        for finding in data["findings"][:4]:
            cursor -= shared_h
            rounded_rect(c, PAD, cursor, inner_w, shared_h, r=6,
                         fill_color=C_DARK, stroke_color=C_LGRAY, stroke_width=0.5)
            c.setFillColor(C_GRAY)
            c.roundRect(PAD, cursor, 4, shared_h, 2, fill=1, stroke=0)
            wrap_text(c, finding, PAD + 16, cursor + shared_h - 12,
                      inner_w - 36, font="Helvetica", size=8.5,
                      color=C_BLACK, line_h=12)
            cursor -= card_gap

    # ── CTA — pinned to page bottom, tight equal margins ───────────────────
    BOT_MARGIN = 16
    CTA_H_NEW  = 58
    CTA_Y      = BOT_MARGIN

    rounded_rect(c, PAD, CTA_Y, inner_w, CTA_H_NEW, r=8,
                 fill_color=C_WHITE, stroke_color=C_LGRAY, stroke_width=1.0)

    cx_mid = PAD + inner_w / 2

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(C_BLACK)
    c.drawCentredString(cx_mid, CTA_Y + CTA_H_NEW - 18, "Ready to show up more?")

    c.setFont("Helvetica", 9)
    c.setFillColor(C_GRAY)
    c.drawCentredString(cx_mid, CTA_Y + CTA_H_NEW - 33,
                        f"Send an email to {CONTACT_EMAIL}  or  call / text Emmanuel at {CONTACT_PHONE}")

    c.setFont("Helvetica", 8)
    c.setFillColor(C_BLACK)
    c.drawCentredString(cx_mid, CTA_Y + 12, "quesoventures.com")

    # ── AUTHORITY CARD — pinned directly above CTA, gap matches bottom margin ─
    AUTH_GAP = BOT_MARGIN
    AUTH_H   = 78
    AUTH_Y   = CTA_Y + CTA_H_NEW + AUTH_GAP

    AI_TEXT_L1 = "AI search doesn't work like Google — keywords are only part of the equation."
    AI_TEXT_L2 = (
        "These engines read your entire web presence: structured data, citations, "
        "and content that directly answers what people are actually searching for."
    )
    AI_TEXT_L3 = "Your next client is already out there searching. Make sure you're the one they find."

    rounded_rect(c, PAD, AUTH_Y, inner_w, AUTH_H, r=8,
                 fill_color=C_WHITE, stroke_color=C_LGRAY, stroke_width=0.5)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(C_BLACK)
    c.drawString(PAD + 18, AUTH_Y + AUTH_H - 18, AI_TEXT_L1)
    wrap_text(c, AI_TEXT_L2, PAD + 18, AUTH_Y + AUTH_H - 32,
              inner_w - 36, font="Helvetica", size=8.5, color=C_GRAY, line_h=13)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(C_BLACK)
    c.drawString(PAD + 18, AUTH_Y + 12, AI_TEXT_L3)

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