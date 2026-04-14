#!/usr/bin/env python3
"""
aiAudit.py  —  Queso Ventures
All copy. Edit here. No PDF logic.

Language rules:
  - No "AI visibility", "AEO", "GEO", "ChatGPT" in client-facing prose
  - Use "new search tools", "new ways customers search", "instead of Google"
  - Always end on the solution or the opportunity — never on the problem alone
"""


def get_competitor_rows(
    comp_name, client_reviews, comp_reviews,
    industry_term="customer",
    client_vis=1, comp_vis=5,
    client_geo=1, comp_geo=5,
):
    """
    Returns list of (question, you_answer, them_answer, you_is_good, them_is_good).
    """
    rows = []

    # Row 1 — reviews
    try:
        c = int(str(client_reviews).replace(",", ""))
        t = int(str(comp_reviews).replace(",", ""))
        you_good  = c >= t
        them_good = t >= c
    except (ValueError, TypeError):
        c, t = "?", "?"
        you_good = them_good = False
    rows.append((
        "Who has more reviews?",
        str(c), str(t),
        you_good, them_good,
    ))

    # Row 2 — Google Maps / local search
    def vis_ans(s):
        if s is None: return "N/A"
        if s >= 4:    return "Yes"
        if s == 3:    return "Sometimes"
        return "No"
    rows.append((
        "Who shows up in Google Maps nearby?",
        vis_ans(client_vis), vis_ans(comp_vis),
        (client_vis or 0) >= 4, (comp_vis or 0) >= 4,
    ))

    # Row 3 — new search tools
    def geo_ans(s):
        if s is None: return "N/A"
        if s >= 4:    return "Yes"
        if s == 3:    return "Sometimes"
        return "No"
    rows.append((
        "Who comes up on new search tools?",
        geo_ans(client_geo), geo_ans(comp_geo),
        (client_geo or 0) >= 4, (comp_geo or 0) >= 4,
    ))

    return rows


def get_competitor_takeaway(featured_query="", industry_term="customer"):
    """
    Two short lines below the comparison table.
    Uses the featured service query to make it specific — no competitor name, no reviews.
    """
    if featured_query:
        line1 = f'When someone searches: "{featured_query}"'
    else:
        line1 = "When someone uses a new search tool to find a business like yours —"
    line2 = "AI tools give one answer, not a list. When it's your competitor, that call goes to them."
    return (line1, line2)


def get_findings(
    industry_term="customer",
    has_website=True,
    client_ps=None,
    geo_score=1,
    vis_score=1,
    comp_name="",
    client_reviews=0,
    comp_reviews=0,
    gbp_score=3,
    featured_service="",
):
    """
    Returns list of (headline, body) tuples — always 3 findings.
    Tailored to the actual prospect data. Ends each finding on the solution.
    """
    findings = []
    service  = featured_service if featured_service else f"{industry_term}s like yours"

    try:
        c_rev = int(str(client_reviews).replace(",", ""))
        t_rev = int(str(comp_reviews).replace(",", ""))
        rev_gap = t_rev - c_rev
    except (ValueError, TypeError):
        rev_gap = 0

    # ── Finding 1 — new search visibility ────────────────────────────────────
    if geo_score <= 2:
        if rev_gap > 50:
            findings.append((
                f"When {industry_term}s search a new way, businesses with more signals show up first.",
                f"Right now that's not you — and the review gap makes it worse. "
                f"New search tools weigh consistency and volume across the whole internet, "
                f"not just one platform. Queso Ventures builds that consistency for you.",
            ))
        else:
            findings.append((
                f"People searching for {service} a new way aren't finding you.",
                f"When {industry_term}s skip Google and ask a new search tool, your business "
                f"doesn't come up. Those are real people, ready to book, going somewhere else. "
                f"Queso Ventures makes sure you're the name they find.",
            ))
    else:
        findings.append((
            f"You show up on new search tools sometimes — not every time.",
            f"The {industry_term}s you miss on the days you don't appear don't come back. "
            f"Queso Ventures turns 'sometimes' into 'every time.'",
        ))

    # ── Finding 2 — website / foundation ─────────────────────────────────────
    if not has_website:
        findings.append((
            "Without a website, new search tools have nothing to say about you.",
            f"Every new search tool needs somewhere to point {industry_term}s. "
            f"Without a site, even the things working in your favor can't do their job. "
            f"Queso Ventures builds that foundation.",
        ))
    elif client_ps is not None and client_ps < 50:
        findings.append((
            f"Your site scores {client_ps}/100 on Google's speed test.",
            f"A slow, outdated site doesn't just lose {industry_term}s who land on it — "
            f"it signals to every search tool that your business isn't keeping up. "
            f"Queso Ventures turns that signal around.",
        ))
    else:
        findings.append((
            "Your Google listing covers about 30% of where new search tools look.",
            f"The other 70% — online directories, citations, how you're described "
            f"across dozens of sites — is where most businesses go invisible. "
            f"Queso Ventures fills those gaps.",
        ))

    # ── Finding 3 — the hook ─────────────────────────────────────────────────
    findings.append((
        "Your current marketing gets you noticed. Queso Ventures gets you found.",
        f"Marketing controls how you look when someone finds you. "
        f"What's different now is that 'finding you' happens on tools your marketing "
        f"doesn't reach. That's the gap Queso Ventures is built to close.",
    ))

    return findings


def get_explainer(industry_term="customer"):
    """
    Returns a structured dict for the WHY THIS IS HAPPENING section.
    Rendered in main.py as: callout box (intro + bold statement) + 3 horizontal cards.
    All copy is hardcoded — same message for every client.
    Cards: number + title on same line in main.py.
    """
    intro = "AI tools read your reviews, listings, and every mention of your business online."
    statement = "The most complete, consistent presence gets recommended. Gaps get passed over."

    cards = [
        (
            "AI Makes the Call",
            "Reviews, listings, citations — AI tools cross-reference all of them to pick one business.",
        ),
        (
            "The Window Is Open",
            "Most businesses in your area haven't built this presence yet.",
        ),
        (
            "We Build It For You",
            "Results compound gradually. You gain ground every week.",
        ),
    ]

    return {"intro": intro, "statement": statement, "cards": cards}


def get_cta_headline():
    return "Let's get you found sooner."


def get_cta_subline(email, phone):
    return f"{email}  ·  Call or text Emmanuel  ·  {phone}"
