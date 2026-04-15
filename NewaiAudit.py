#!/usr/bin/env python3
"""
NewaiAudit.py  —  Queso Ventures
Copy layer only. No PDF logic lives here.

Rules:
  - No LLM anywhere in this file. All copy is hardcoded.
  - No "AEO", "GEO", "ChatGPT", "algorithm", "structured data" in client prose.
  - No platform names that give them DIY ideas (no "Google Business Profile" etc).
  - No raw scores exposed anywhere.
  - Periods not dashes. Short punchy sentences.
  - Industry term swaps throughout: patient / client / guest / customer / member.
  - Every finding ends on the business impact, not the technical problem.
  - Every outcome line ends on the growth moment or the cost of inaction.
"""

import os


# ─────────────────────────────────────────────
#  INDUSTRY CONTEXT MAP
# ─────────────────────────────────────────────

INDUSTRY_MAP = {
    "clinic":      "patient",
    "health":      "patient",
    "wellness":    "patient",
    "medical":     "patient",
    "dental":      "patient",
    "dentist":     "patient",
    "chiro":       "patient",
    "therapy":     "patient",
    "therapist":   "patient",
    "rehab":       "patient",
    "med spa":     "client",
    "spa":         "client",
    "salon":       "client",
    "barbershop":  "client",
    "barber":      "client",
    "law":         "client",
    "attorney":    "client",
    "legal":       "client",
    "accountant":  "client",
    "cpa":         "client",
    "financial":   "client",
    "real estate": "client",
    "realty":      "client",
    "realtor":     "client",
    "restaurant":  "guest",
    "cafe":        "guest",
    "coffee":      "guest",
    "bakery":      "guest",
    "food truck":  "guest",
    "hotel":       "guest",
    "gym":         "member",
    "fitness":     "member",
    "crossfit":    "member",
    "yoga":        "member",
    "auto":        "customer",
    "mechanic":    "customer",
    "plumb":       "customer",
    "electric":    "customer",
    "hvac":        "customer",
    "roofing":     "customer",
    "landscap":    "customer",
    "cleaning":    "customer",
    "pest":        "customer",
}

def get_industry_term(business_type: str) -> str:
    bt = business_type.lower()
    for fragment, term in INDUSTRY_MAP.items():
        if fragment in bt:
            return term
    return "customer"


# ─────────────────────────────────────────────
#  FINDINGS  (score-mapped, no LLM)
#
#  Three findings always generated from these signals:
#    geo_score       1=not showing up  3=sometimes  5=yes
#    visibility_score (Maps)  same scale
#    gbp_score       1=bare  2=off  3=basic  5=well maintained
#    has_website     True/False
#    client_ps       0-100 or None
#
#  Each finding: 1-2 short sentences. Impact first, not cause.
#  No platform names. No scores or numbers mentioned.
# ─────────────────────────────────────────────

def get_findings(data: dict) -> list:
    term     = data.get("industry_term", "customer")
    city     = data.get("business_city", "your area").split(",")[0].strip()
    btype    = data.get("business_type", "your business")
    geo      = data.get("geo_score", 1)
    vis      = data.get("visibility_score", 1)
    gbp      = data.get("gbp_score", 3)
    has_site = data.get("has_website", False)
    ps       = data.get("client_ps")
    seo      = data.get("_seo", {})
    city_on_site = seo.get("city_in_content", False)
    phone_on_site = seo.get("has_phone", False)

    findings = []

    # ── FINDING 1: New search tool visibility (geo_score) ──────────────────
    # This is always finding 1 — it is the core of the pitch.
    if geo == 1:
        findings.append(
            f"When someone in {city} uses a new search tool to find a {btype}, "
            f"your business is not in the answer. "
            f"Those {term}s are going somewhere else before they ever know you exist."
        )
    elif geo == 3:
        findings.append(
            f"You show up on new search tools sometimes — not consistently. "
            f"The {term}s you miss on the days you don't appear "
            f"are booking with whoever does show up."
        )
    else:
        findings.append(
            f"You're showing up on new search tools — that puts you ahead of most. "
            f"Staying consistent is what keeps that advantage compounding in your favor."
        )

    # ── FINDING 2: Maps + online presence completeness ─────────────────────
    # Combo of visibility_score + gbp_score
    if vis == 1 and gbp <= 2:
        findings.append(
            f"Your local presence is incomplete in the places new {term}s look first. "
            f"When your information is missing or inconsistent across the web, "
            f"search tools pass you over — even if someone is searching for exactly what you offer."
        )
    elif vis == 1 and gbp == 3:
        findings.append(
            f"You have a basic local presence, but it is not enough to get surfaced "
            f"when {term}s search nearby. "
            f"The gap between showing up sometimes and showing up every time "
            f"is a more complete, consistent presence across the web."
        )
    elif vis == 3:
        findings.append(
            f"You appear locally on some searches but not others. "
            f"Every search you miss is a {term} who finds someone else, "
            f"leaves them a review, and sends friends their way instead of yours."
        )
    else:
        findings.append(
            f"Your local presence is working in your favor. "
            f"The opportunity now is in the layer beyond local search — "
            f"the places new search tools read that most businesses in {city} haven't addressed yet."
        )

    # ── FINDING 3: Website + site signals ──────────────────────────────────
    # Keyed on has_website, ps, city_on_site, phone_on_site
    if not has_site:
        findings.append(
            f"You don't have a website, which means new search tools have almost nothing "
            f"to read about your business. "
            f"That single gap limits everything else — no site means no signal."
        )
    elif ps is not None and ps < 50:
        findings.append(
            f"Your website loads slowly on phones, which is how most {term}s are searching. "
            f"A slow site signals to every tool that reads it "
            f"that your business is not keeping up — and they respond accordingly."
        )
    elif not city_on_site and not phone_on_site:
        findings.append(
            f"Your website doesn't clearly tell new search tools where you are "
            f"or how to reach you. "
            f"That missing context is one of the main reasons you get passed over "
            f"when someone nearby is looking."
        )
    elif not city_on_site:
        findings.append(
            f"Your website doesn't clearly signal that you serve {city}. "
            f"New search tools use that context to decide who to recommend locally — "
            f"without it, you're invisible to {term}s searching right in your area."
        )
    elif ps is not None and ps < 70:
        findings.append(
            f"Your site covers the basics but has room to work harder. "
            f"The businesses earning the most new {term}s from search "
            f"have sites that actively reinforce their presence — not just describe their services."
        )
    else:
        findings.append(
            f"Your website is a solid foundation. "
            f"The next layer is making sure everything it says about you "
            f"is echoed consistently across every place new search tools look."
        )

    return findings[:3]


# ─────────────────────────────────────────────
#  COMPETITOR TABLE
# ─────────────────────────────────────────────

def get_competitor_rows(
    comp_name, client_reviews, comp_reviews,
    industry_term="customer",
    client_vis=1, comp_vis=5,
    client_geo=1, comp_geo=5,
):
    rows = []

    try:
        c = int(str(client_reviews).replace(",", ""))
        t = int(str(comp_reviews).replace(",", ""))
        you_good  = c >= t
        them_good = t >= c
    except (ValueError, TypeError):
        c, t = "?", "?"
        you_good = them_good = False
    rows.append(("Who has more reviews?", str(c), str(t), you_good, them_good))

    def vis_ans(s):
        if s is None: return "N/A"
        if s >= 4:    return "Yes"
        if s == 3:    return "Sometimes"
        return "Not Yet"

    rows.append((
        "Showing up in Google Maps?",
        vis_ans(client_vis), vis_ans(comp_vis),
        (client_vis or 0) >= 4, (comp_vis or 0) >= 4,
    ))
    rows.append((
        "Found by new search tools?",
        vis_ans(client_geo), vis_ans(comp_geo),
        (client_geo or 0) >= 4, (comp_geo or 0) >= 4,
    ))
    return rows


def get_competitor_takeaway(featured_query="", industry_term="customer"):
    if featured_query:
        line1 = f'Someone searches: "{featured_query}"'
    else:
        line1 = f"A {industry_term} uses a new search tool to find a business like yours."
    line2 = "A curated recommendation is built. One business is featured. If it is not you, that search never happened."
    return (line1, line2)


# ─────────────────────────────────────────────
#  HOW SEARCHING WORKS NOW  (score-mapped, no LLM)
# ─────────────────────────────────────────────

_OUTCOME_MAP = {
    "not_visible": {
        "patient": (
            "Every search that does not find you finds someone else.",
            "That patient books with them. Leaves a review for them. Refers friends to them.",
            "Their presence grows. Yours stays the same. The gap widens every day.",
        ),
        "client": (
            "Every search that does not find you finds someone else.",
            "That client books with them. Leaves a review for them. Tells their friends.",
            "Their presence grows. Yours stays the same. The gap widens every day.",
        ),
        "guest": (
            "Every search that does not find you finds someone else.",
            "That guest goes to them. Posts about them. Comes back to them.",
            "Their presence grows. Yours stays the same. The gap widens every day.",
        ),
        "member": (
            "Every search that does not find you finds someone else.",
            "That person joins them. Refers friends to them. Stays with them.",
            "Their presence grows. Yours stays the same. The gap widens every day.",
        ),
        "customer": (
            "Every search that does not find you finds someone else.",
            "That customer calls them. Leaves a review for them. Calls them again next time.",
            "Their presence grows. Yours stays the same. The gap widens every day.",
        ),
    },
    "sometimes": {
        "patient": (
            "You show up. Just not every time.",
            "The patients searching on the days you do not appear book with whoever does.",
            "Inconsistency compounds. Every missed search is a relationship started elsewhere.",
        ),
        "client": (
            "You show up. Just not every time.",
            "The clients searching on the days you do not appear book with whoever does.",
            "Inconsistency compounds. Every missed search is a relationship started elsewhere.",
        ),
        "guest": (
            "You show up. Just not every time.",
            "The guests searching on the days you do not appear go somewhere else.",
            "Inconsistency compounds. Every missed search is a habit formed elsewhere.",
        ),
        "member": (
            "You show up. Just not every time.",
            "The people searching on the days you do not appear join somewhere else.",
            "Inconsistency compounds. Every missed search is a membership that goes elsewhere.",
        ),
        "customer": (
            "You show up. Just not every time.",
            "The customers searching on the days you do not appear call someone else.",
            "Inconsistency compounds. Every missed search is a job that goes elsewhere.",
        ),
    },
    "visible": {
        "patient": (
            "You are showing up. Keep earning it.",
            "Every consistent appearance is another patient who found you first.",
            "Staying consistent is what turns visibility into a full schedule.",
        ),
        "client": (
            "You are showing up. Keep earning it.",
            "Every consistent appearance is another client who found you first.",
            "Staying consistent is what turns visibility into a fully booked calendar.",
        ),
        "guest": (
            "You are showing up. Keep earning it.",
            "Every consistent appearance is another guest who chose you first.",
            "Staying consistent is what turns visibility into a full house.",
        ),
        "member": (
            "You are showing up. Keep earning it.",
            "Every consistent appearance is another person who found you first.",
            "Staying consistent is what turns visibility into steady membership growth.",
        ),
        "customer": (
            "You are showing up. Keep earning it.",
            "Every consistent appearance is another customer who called you first.",
            "Staying consistent is what turns visibility into steady inbound work.",
        ),
    },
}


def get_outcome(data: dict) -> tuple:
    geo  = data.get("geo_score", 1)
    term = data.get("industry_term", "customer")
    tier = "not_visible" if geo <= 2 else "sometimes" if geo == 3 else "visible"
    t    = term if term in _OUTCOME_MAP[tier] else "customer"
    vals = _OUTCOME_MAP[tier][t]
    return (vals[0], list(vals[1:]))


# ─────────────────────────────────────────────
#  DIFFERENTIATOR  (keyword-mapped, no LLM)
# ─────────────────────────────────────────────

_DIFF = {
    "patient": (
        "The layer that makes everything else work.",
        [
            "SEO and marketing are valuable. Without visibility, neither one gets the chance to matter.",
            "New search tools decide who gets recommended before a patient ever sees your website.",
            "Building the right presence means knowing exactly what these models look for and how they are trained to surface it.",
            "Queso Ventures does this exclusively. New patients start finding you. That is the whole point.",
        ],
    ),
    "client": (
        "The layer that makes everything else work.",
        [
            "SEO and marketing are valuable. Without visibility, neither one gets the chance to matter.",
            "New search tools decide who gets recommended before a client ever sees your website.",
            "Building the right presence means knowing exactly what these models look for and how they are trained to surface it.",
            "Queso Ventures does this exclusively. New clients start finding you. That is the whole point.",
        ],
    ),
    "guest": (
        "The layer that makes everything else work.",
        [
            "SEO and marketing are valuable. Without visibility, neither one gets the chance to matter.",
            "New search tools decide who gets recommended before a guest ever finds your page.",
            "Building the right presence means knowing exactly what these models look for and how they are trained to surface it.",
            "Queso Ventures does this exclusively. New guests start finding you. That is the whole point.",
        ],
    ),
    "member": (
        "The layer that makes everything else work.",
        [
            "SEO and marketing are valuable. Without visibility, neither one gets the chance to matter.",
            "New search tools decide who gets recommended before a potential member ever sees your site.",
            "Building the right presence means knowing exactly what these models look for and how they are trained to surface it.",
            "Queso Ventures does this exclusively. New members start finding you. That is the whole point.",
        ],
    ),
    "customer": (
        "The layer that makes everything else work.",
        [
            "SEO and marketing are valuable. Without visibility, neither one gets the chance to matter.",
            "New search tools decide who gets recommended before a customer ever reaches your site.",
            "Building the right presence means knowing exactly what these models look for and how they are trained to surface it.",
            "Queso Ventures does this exclusively. New customers start finding you. That is the whole point.",
        ],
    ),
}


def get_differentiator(industry_term="customer"):
    t = industry_term if industry_term in _DIFF else "customer"
    return _DIFF[t]


# ─────────────────────────────────────────────
#  CTA
# ─────────────────────────────────────────────

def get_cta_headline():
    return "Let's get you found."