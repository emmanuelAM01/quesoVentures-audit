#!/usr/bin/env python3
"""
webAudit.py  —  Queso Ventures
Handles: website check, PageSpeed, GBP lookup, competitor data, scoring.
Called by main.py — does not build any PDF.
"""

import os, re, requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36"
    )
}
PAGESPEED_KEY = os.environ.get("PAGESPEED_KEY", "")
PLACES_KEY    = os.environ.get("PLACES_API_KEY", "")
OPENAI_KEY    = os.environ.get("OPENAI_API_KEY", "")

# ─────────────────────────────────────────────
#  INDUSTRY LANGUAGE MAP
#  Key: lowercase fragment that appears in business_type
#  Value: singular word for "customer"
# ─────────────────────────────────────────────
INDUSTRY_TERMS = {
    "clinic":       "patient",
    "health":       "patient",
    "wellness":     "patient",
    "medical":      "patient",
    "dental":       "patient",
    "dentist":      "patient",
    "chiro":        "patient",
    "therapy":      "patient",
    "therapist":    "patient",
    "med spa":      "client",
    "spa":          "client",
    "salon":        "client",
    "barbershop":   "client",
    "barber":       "client",
    "law":          "client",
    "attorney":     "client",
    "legal":        "client",
    "accountant":   "client",
    "cpa":          "client",
    "financial":    "client",
    "restaurant":   "guest",
    "cafe":         "guest",
    "coffee":       "guest",
    "bakery":       "guest",
    "hotel":        "guest",
    "gym":          "member",
    "fitness":      "member",
    "crossfit":     "member",
    "yoga":         "member",
    "real estate":  "client",
    "realty":       "client",
    "realtor":      "client",
    "auto":         "customer",
    "mechanic":     "customer",
    "plumb":        "customer",
    "electric":     "customer",
    "hvac":         "customer",
    "roofing":      "customer",
    "landscap":     "customer",
    "cleaning":     "customer",
    "pest":         "customer",
}

def get_featured_service(html: str, business_type: str, city: str) -> tuple:
    """
    Extract a specific service from the website HTML, confirm with admin via CLI,
    then generate a realistic customer search query for that service.

    Returns: (featured_service, featured_query)
      featured_service — e.g. "weight loss injections"
      featured_query   — e.g. "where can I get weight loss injections near Humble"
    """
    city_short = city.split(",")[0].strip()
    services   = []

    # Step 1 — try to extract services from HTML using OpenAI
    if OPENAI_KEY and html:
        try:
            import openai
            client = openai.OpenAI(api_key=OPENAI_KEY)
            snippet = html[:4000]
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": (
                        "From this website HTML, list 2-3 of the most specific "
                        "customer-facing services offered. Be specific "
                        "(e.g. 'weight loss injections' not 'wellness'). "
                        "Output as a comma-separated list. Nothing else.\n\n"
                        f"HTML:\n{snippet}"
                    ),
                }],
                max_tokens=40,
                temperature=0.2,
            )
            raw = resp.choices[0].message.content.strip()
            services = [s.strip().strip('"\'') for s in raw.split(",") if s.strip()]
        except Exception as e:
            print(f"  (OpenAI extraction: {e})")

    # Step 2 — admin confirms or overrides
    if services:
        print(f"\n  Found services on their site:")
        for i, s in enumerate(services, 1):
            print(f"    {i}. {s}")
        val = input("  Which to highlight? (1-3 or type your own): ").strip()
        if val.isdigit() and 1 <= int(val) <= len(services):
            featured_service = services[int(val) - 1]
        elif val:
            featured_service = val
        else:
            featured_service = services[0]
    else:
        # No HTML or extraction failed — ask admin directly
        featured_service = input(
            f"  Key service to highlight (e.g. 'weight loss shots', or blank to skip): "
        ).strip()

    if not featured_service:
        return "", ""

    # Step 3 — generate the example customer query
    featured_query = f"where can I get {featured_service} near {city_short}"
    print(f"  → Featured query: \"{featured_query}\"")
    return featured_service, featured_query


def get_industry_term(business_type: str) -> str:
    """Return the right word for 'customer' based on business type."""
    bt = business_type.lower()
    for fragment, term in INDUSTRY_TERMS.items():
        if fragment in bt:
            return term
    return "customer"

# ─────────────────────────────────────────────
#  CLI HELPERS
# ─────────────────────────────────────────────
def prompt(label, options=None, default=None):
    if options:
        print(f"\n  {label}")
        for i, o in enumerate(options, 1):
            print(f"    {i}. {o}")
        while True:
            try:
                val = int(input("    Enter number: ").strip())
                if 1 <= val <= len(options):
                    return val
            except ValueError:
                pass
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

# ─────────────────────────────────────────────
#  WEBSITE CHECK
# ─────────────────────────────────────────────
def check_website(url):
    if not url or url.lower() in ("none", "n", ""):
        return False, None, None
    if not url.startswith("http"):
        url = "https://" + url
    try:
        r = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
        return (r.status_code < 400), url, (r.text if r.status_code < 400 else None)
    except:
        return False, url, None

def seo_check(html, city, btype):
    if not html:
        return {}
    soup    = BeautifulSoup(html, "html.parser")
    tl      = soup.find("title")
    city_l  = city.lower().split(",")[0].strip()
    type_l  = btype.lower().split()[0]
    txt     = soup.get_text(" ").lower()
    h1s     = [h.get_text().lower() for h in soup.find_all("h1")]
    return {
        "city_in_title":     city_l in (tl.get_text().lower() if tl else ""),
        "city_in_h1":        any(city_l in h for h in h1s),
        "city_in_content":   city_l in txt,
        "service_mentioned": type_l in txt,
        "is_mobile_ready":   bool(soup.find("meta", attrs={"name": "viewport"})),
        "has_phone":         bool(re.search(r'\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4}', soup.get_text())),
    }

def _phone_finding(html):
    if not html:
        return "missing"
    soup = BeautifulSoup(html, "html.parser")
    body = soup.get_text(" ")
    if not re.search(r'\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4}', body):
        return "missing"
    header = soup.find(["header", "nav"])
    if header and re.search(r'\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4}', header.get_text()):
        return "visible"
    return "buried"

def auto_site_score(exists, seo, html=None):
    """Score website 1-5 and collect auto-findings."""
    if not exists:
        return 1, []
    score = 3
    issues = []
    if seo.get("city_in_content") or seo.get("city_in_title"):
        score += 0.5
    else:
        issues.append("location_missing")
    if seo.get("service_mentioned"):
        score += 0.5
    if seo.get("is_mobile_ready"):
        score += 0.5
    if seo.get("has_phone"):
        score += 0.5
    # check for agency footer
    agency_link = False
    if html:
        soup = BeautifulSoup(html, "html.parser")
        footer = soup.find("footer")
        if footer:
            links = footer.find_all("a", href=True)
            for lnk in links:
                href = lnk.get("href", "").lower()
                txt  = lnk.get_text().lower()
                if any(w in href + txt for w in ["agency", "design", "studio", "creative", "web", "built by", "powered by"]):
                    agency_link = True
                    break
    return min(5, max(1, int(score))), issues

# ─────────────────────────────────────────────
#  PAGESPEED
# ─────────────────────────────────────────────
def get_pagespeed(url, label="", full=False):
    if not url:
        return None if not full else {}
    tag = f" [{label}]" if label else ""
    params = {"url": url, "strategy": "mobile", "category": ["performance", "seo"]}
    if PAGESPEED_KEY:
        params["key"] = PAGESPEED_KEY

    for attempt in range(1, 3):
        retry = "  (retry)" if attempt > 1 else ""
        print(f"  Fetching PageSpeed{tag}{retry}...", end=" ", flush=True)
        try:
            r    = requests.get(
                "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
                params=params, timeout=50
            )
            data = r.json()
            lhr  = data.get("lighthouseResult", {})
            cats = lhr.get("categories", {})
            perf = cats.get("performance", {}).get("score")
            seo  = cats.get("seo", {}).get("score")
            pp   = int(perf * 100) if perf is not None else None
            sp   = int(seo  * 100) if seo  is not None else None
            print(f"perf={pp}/100  seo={sp}/100" if sp else f"{pp}/100")
            if not full:
                return pp

            AUDIT_PLAIN = {
                "render-blocking-resources": "Slow-loading code is delaying your page from appearing",
                "unused-javascript":          "Your site loads code it doesn't use, slowing it down",
                "uses-optimized-images":      "Images are too large and slowing your site down",
                "server-response-time":       "Your hosting server is responding slowly to visitors",
                "largest-contentful-paint-element": "Your main page content takes too long to appear",
            }
            audits   = lhr.get("audits", {})
            failures = []
            for key, plain in AUDIT_PLAIN.items():
                audit = audits.get(key, {})
                sc    = audit.get("score")
                disp  = audit.get("displayValue", "")
                if sc is not None and sc < 0.9 and disp:
                    savings = re.search(r"[\d\.]+\s*s", disp)
                    suffix  = f" ({savings.group(0)} savings)" if savings else ""
                    failures.append(f"{plain}{suffix}")

            return {"perf_score": pp, "seo_score": sp, "top_audits": failures[:3]}

        except Exception as e:
            is_timeout = any(w in str(e).lower() for w in ("timed out", "timeout"))
            print("timed out" if is_timeout else f"failed ({e})")
            if attempt == 2:
                return None if not full else {}
            import time; time.sleep(2)

def ps_to_score(p):
    if p is None: return None
    if p >= 90:   return 5
    if p >= 70:   return 4
    if p >= 50:   return 3
    if p >= 30:   return 2
    return 1

# ─────────────────────────────────────────────
#  GOOGLE PLACES API
# ─────────────────────────────────────────────
def lookup_places_gbp(name, city):
    if not PLACES_KEY:
        return {}
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type":     "application/json",
        "X-Goog-Api-Key":   PLACES_KEY,
        "X-Goog-FieldMask": "places.displayName,places.rating,places.userRatingCount,places.photos",
    }
    body = {"textQuery": f"{name} {city}", "languageCode": "en", "maxResultCount": 1}
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
    except:
        return {}

# ─────────────────────────────────────────────
#  SCORING HELPERS
# ─────────────────────────────────────────────
def pct_color_str(p):
    """Return 'red' / 'orange' / 'green' string for use in main."""
    if p is None: return "gray"
    if p < 50:    return "red"
    if p < 70:    return "orange"
    return "green"

def calc_visibility_score(data):
    """
    Auto-calculate overall visibility score (0-100) from:
      website  20%  (1-5 → 4-20)
      gbp      25%  (1-5 → 5-25)
      maps     20%  (1-5 → 4-20)
      ai       35%  (1-5 → 7-35)

    Speed score is still collected (drives which finding variant appears)
    but removed from the formula — it's not part of the AI visibility pitch.
    """
    w  = data.get("website_score",    3)
    g  = data.get("gbp_score",        3)
    v  = data.get("visibility_score", 3)
    ai = data.get("geo_score",        1)

    score = (
        (w  / 5) * 20 +
        (g  / 5) * 25 +
        (v  / 5) * 20 +
        (ai / 5) * 35
    )
    # Small baseline boost so scores don't feel demoralizing to the owner —
    # AI visibility is genuinely new and most businesses score low on it.
    boosted = int(round(score)) + 14
    return min(boosted, 85)   # cap at 85 — always room to grow

# ─────────────────────────────────────────────
#  FINDINGS ENGINE
# ─────────────────────────────────────────────
def build_findings(data, auto_findings):
    """
    Always returns exactly 3 finding strings (AI/GEO-focused, plain business English).
    auto_findings are website-level issues kept as supporting context but abstracted.
    """
    term    = data.get("industry_term", "customer")
    city    = data.get("business_city", "your area").split(",")[0].strip()
    btype   = data.get("business_type", "your business")
    geo     = data.get("geo_score",        1)
    vis     = data.get("visibility_score", 1)
    gbp     = data.get("gbp_score",        3)
    ps      = data.get("client_ps")
    exists  = data.get("has_website", False)

    findings = []

    # ── FINDING 1: AI search visibility ──────────────────────────────────────
    if geo <= 2:
        findings.append(
            f"When someone asks an AI tool to recommend a {btype} near {city}, "
            f"your business doesn't come up — which means those {term}s are going "
            f"somewhere else before they ever find you."
        )
    else:
        findings.append(
            f"You're showing up on some AI searches but not all of them — "
            f"the {term}s you're missing are the ones actively searching right now "
            f"and landing with whoever shows up first."
        )

    # ── FINDING 2: Online presence consistency ───────────────────────────────
    if vis <= 2:
        findings.append(
            f"Your business information isn't consistent across the internet — "
            f"AI tools cross-reference dozens of sources to decide who to trust and recommend. "
            f"Gaps and mismatches are the #1 reason a business gets skipped."
        )
    else:
        findings.append(
            f"Your listing shows up locally, but the layer underneath — the one "
            f"that tells AI tools who you are and what you do — still has gaps "
            f"that are costing you new {term}s every week."
        )

    # ── FINDING 3: Website as part of AI visibility ──────────────────────────
    if not exists:
        findings.append(
            f"You don't have a website — which isn't just about looking professional. "
            f"Your site is 30% of your total AI visibility score. Without it, "
            f"AI tools have almost nothing to read about your business, "
            f"and that holds back everything else."
        )
    elif ps is not None and ps < 50:
        findings.append(
            f"Your website is part of the picture — but right now it's working against you. "
            f"A slow, hard-to-use site is worse than no site at all for AI visibility "
            f"because it tells every tool that reads it: this business isn't keeping up."
        )
    elif gbp <= 2:
        findings.append(
            f"Your Google Business profile is incomplete — and that's one of the first "
            f"places AI tools look when someone asks for a recommendation near {city}. "
            f"An incomplete profile is a missed opportunity on every single search."
        )
    else:
        findings.append(
            f"Your site and Google listing cover about 30% of AI visibility — "
            f"but the other 70% lives everywhere else online: citations, directories, "
            f"structured data, and signals most business owners don't know exist yet."
        )

    return findings[:3]

# ─────────────────────────────────────────────
#  MAIN DATA COLLECTION
# ─────────────────────────────────────────────
def collect_data():
    score_opts = [1, 2, 3, 4, 5]
    data         = {}
    auto_findings = []

    divider("BUSINESS INFO")
    data["business_name"] = prompt("Business name")
    data["business_type"] = prompt("Business type (e.g. med spa, wellness clinic, dentist)")
    data["business_city"] = prompt("City, State (e.g. Humble, TX)", default="Humble, TX")
    data["industry_term"] = get_industry_term(data["business_type"])
    print(f"  → Industry term: \"{data['industry_term']}\" (edit INDUSTRY_TERMS in webAudit.py to change)")

    divider("WEBSITE")
    url_in = prompt("Client website URL (blank if none)", default="")
    data["has_website"]  = bool(url_in and url_in.lower() not in ("none", "n", ""))
    data["website_url"]  = url_in if data["has_website"] else ""

    divider("AUTO-FETCHING CLIENT")
    exists, site_url, html = check_website(data["website_url"])
    if data["has_website"] and not exists:
        confirm = prompt("Could not reach site — mark as existing anyway? (y/n)", default="n").lower()
        if confirm == "y":
            exists = True; html = None
    data["has_website"] = exists
    seo = seo_check(html, data["business_city"], data["business_type"]) if html else {}
    data["_seo"] = seo

    ws_score, ws_issues = auto_site_score(exists, seo, html=html)
    auto_findings.extend(ws_issues)

    client_ps_data = get_pagespeed(site_url, "client", full=True) if exists else {}
    client_ps      = client_ps_data.get("perf_score") if client_ps_data else None
    client_seo_pct = client_ps_data.get("seo_score")  if client_ps_data else None

    if exists and client_ps is None:
        print("  PageSpeed fetch failed — enter manually at pagespeed.web.dev\n")
        _ps  = prompt("  Client phone speed score (0-100, or blank to skip)", default="")
        _seo = prompt("  Client SEO score (0-100, or blank to skip)", default="")
        client_ps      = int(_ps)  if _ps  and _ps.isdigit()  else None
        client_seo_pct = int(_seo) if _seo and _seo.isdigit() else None

    data["client_ps"]      = client_ps
    data["client_seo_pct"] = client_seo_pct
    ps_score = ps_to_score(client_ps)

    # Featured service — extracted from website, confirmed by admin
    divider("FEATURED SERVICE")
    print("  We'll pull a specific service to use as the example search query in the report.")
    feat_svc, feat_qry = get_featured_service(
        html or "", data["business_type"], data["business_city"]
    )
    data["featured_service"] = feat_svc
    data["featured_query"]   = feat_qry

    if client_ps is not None:
        if client_ps < 50:
            auto_findings.append(f"site_speed_critical:{client_ps}")
        elif client_ps < 70:
            auto_findings.append(f"site_speed_slow:{client_ps}")

    # ── GBP via Places API ──
    print("  Fetching GBP data from Places API...", end=" ", flush=True)
    gbp_data = lookup_places_gbp(data["business_name"], data["business_city"])
    if gbp_data.get("rating"):
        rat = str(gbp_data["rating"])
        rev = str(gbp_data["review_count"])
        print(f"rating={rat}  reviews={rev}  photos={gbp_data.get('photo_count', 0)}")
        ov_rat = prompt(f"  Star rating (Enter to keep {rat})", default=rat)
        ov_rev = prompt(f"  Review count (Enter to keep {rev})", default=rev)
        data["review_rating"]    = ov_rat
        data["review_count"]     = ov_rev
        data["gbp_photo_count"]  = gbp_data.get("photo_count", 0)
    else:
        print("not found")
        data["review_rating"]   = prompt("  Star rating (e.g. 4.8)", default="?")
        data["review_count"]    = prompt("  Review count (e.g. 270)", default="0")
        data["gbp_photo_count"] = 0

    print(f"\n  Client: website={'✓' if exists else '✗'}  "
          f"perf={client_ps or 'N/A'}  seo={client_seo_pct or 'N/A'}  "
          f"rating={data['review_rating']}  reviews={data['review_count']}")

    # ── COMPETITOR ──
    divider("COMPETITOR")
    print(f'  Search Google: "{data["business_type"]} {data["business_city"]}" '
          f'— pick the top result that is NOT the client.\n')
    data["comp_name"] = prompt("Competitor name", default="N/A")

    print("  Fetching competitor GBP data...", end=" ", flush=True)
    comp_gbp = lookup_places_gbp(data["comp_name"], data["business_city"])
    if comp_gbp.get("rating"):
        cr  = str(comp_gbp["rating"])
        crv = str(comp_gbp["review_count"])
        print(f"rating={cr}  reviews={crv}")
        data["comp_rating"]  = prompt(f"  Competitor star rating (Enter to keep {cr})", default=cr)
        data["comp_reviews"] = prompt(f"  Competitor review count (Enter to keep {crv})", default=crv)
    else:
        print("not found")
        data["comp_rating"]  = prompt("  Competitor star rating", default="?")
        data["comp_reviews"] = prompt("  Competitor review count", default="?")

    comp_url_in = prompt("Competitor website URL (blank if none)", default="")
    data["comp_has_site"] = bool(comp_url_in and comp_url_in.lower() not in ("none", "n", ""))
    data["comp_website"]  = comp_url_in
    data["comp_ps"]       = None
    data["comp_seo_pct"]  = None
    if data["comp_has_site"]:
        comp_exists, comp_url, _ = check_website(comp_url_in)
        if comp_exists:
            comp_ps_data         = get_pagespeed(comp_url, "competitor", full=True)
            data["comp_ps"]      = comp_ps_data.get("perf_score") if comp_ps_data else None
            data["comp_seo_pct"] = comp_ps_data.get("seo_score")  if comp_ps_data else None

    # ── SCORING ──
    divider("SCORING — CLIENT")

    if exists:
        print(f"\n  [CLIENT] Website Quality — auto-score: {ws_score}/5")
        ov = prompt("  Override? (blank = accept)", default="")
        data["website_score"] = int(ov) if ov and ov.isdigit() else ws_score
    else:
        data["website_score"] = 1
        print("\n  [CLIENT] Website Quality — 1 (no site)")

    if ps_score:
        print(f"\n  [CLIENT] Mobile Page Speed — auto-score: {ps_score}/5 ({client_ps}/100)")
        ov = prompt("  Override? (blank = accept)", default="")
        data["speed_score"] = int(ov) if ov and ov.isdigit() else ps_score
    elif not exists:
        data["speed_score"] = 1
    else:
        data["speed_score"] = int(prompt("[CLIENT] Mobile Page Speed (1-5)", default="3"))

    print(f"\n  [CLIENT] Google Business Profile")
    _gbp_opts = [
        "Not set up — profile is bare or missing",
        "Filled out but off — info there but outdated or inaccurate",
        "Set up but basic — correct info, nothing standing out",
        "Well set up — accurate, photos, services listed, maintained",
    ]
    _gbp_ans = prompt("  How does their profile look?", options=_gbp_opts)
    data["gbp_score"] = {1: 1, 2: 2, 3: 3, 4: 5}[_gbp_ans]

    print(f'\n  [CLIENT] Google Maps Visibility')
    print(f'  Search: "{data["business_type"]} {data["business_city"]}" — do they show in map results?')
    _vis_opts = ["No — not in map results at all", "Sometimes — appears but not in top 3", "Yes — top 3"]
    _vis_ans  = prompt("  Do they show up?", options=_vis_opts)
    data["visibility_score"] = {1: 1, 2: 3, 3: 5}[_vis_ans]

    print(f'\n  [CLIENT] AI Search Visibility')
    print(f'  Ask ChatGPT: "best {data["business_type"]} in {data["business_city"].split(",")[0].strip()}"')
    _geo_opts = ["No — not mentioned at all", "Sometimes — mentioned but not by name", "Yes — recommended by name"]
    _geo_ans  = prompt("  Do they show up?", options=_geo_opts)
    data["geo_score"] = {1: 1, 2: 3, 3: 5}[_geo_ans]

    print(f'\n  [COMPETITOR] AI Search Visibility')
    print(f'  Same ChatGPT query — does the COMPETITOR appear?')
    _cgeo_opts = ["No — not mentioned at all", "Sometimes — mentioned but not by name", "Yes — recommended by name"]
    _cgeo_ans  = prompt("  Do they show up?", options=_cgeo_opts)
    data["comp_geo_score"] = {1: 1, 2: 3, 3: 5}[_cgeo_ans]

    print(f'\n  [COMPETITOR] Google Maps Visibility')
    print(f'  Same Google Maps search — does the competitor show in top 3?')
    _cvis_opts = ["No — not in map results", "Sometimes — not in top 3", "Yes — top 3"]
    _cvis_ans  = prompt("  Do they show up?", options=_cvis_opts)
    data["comp_vis_score"] = {1: 1, 2: 3, 3: 5}[_cvis_ans]

    data["_phone_status"] = _phone_finding(html) if html else "missing"
    data["visibility_pct"] = calc_visibility_score(data)
    data["findings"]       = build_findings(data, auto_findings)

    return data