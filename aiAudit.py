#!/usr/bin/env python3
"""
aiAudit.py  —  Queso Ventures
All copy. Edit here. No PDF logic.

Language rules:
  - No "AEO", "GEO", "ChatGPT" in client-facing prose
  - Use "new search tools", "AI tools" — plain language only
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
        "Who gets recommended by AI tools?",
        geo_ans(client_geo), geo_ans(comp_geo),
        (client_geo or 0) >= 4, (comp_geo or 0) >= 4,
    ))

    return rows


def get_competitor_takeaway(featured_query="", industry_term="customer"):
    """
    Two short lines below the comparison table.
    """
    if featured_query:
        line1 = f'When someone searches: "{featured_query}"'
    else:
        line1 = "When someone uses an AI tool to find a business like yours —"
    line2 = "AI tools give one answer, not a list. When it's your competitor, that call goes to them."
    return (line1, line2)


def get_score_factors(data, industry_term="customer"):
    """
    Returns list of 2 (label, insight) tuples explaining the biggest score drivers.
    Used in the "Your Visibility Score" section.
    """
    factors = []
    geo     = data.get("geo_score", 1)
    rating  = data.get("review_rating", 0)
    reviews = data.get("review_count", 0)
    city    = data.get("business_city", "your area")
    service = data.get("featured_service", f"{industry_term} services")

    # Factor 1 — AI/geo visibility (35% of score — biggest single weight)
    if geo <= 2:
        factors.append((
            "Not showing up on AI tools.",
            f"When {industry_term}s in {city} search for {service}, your business isn't "
            f"in the results. That's the biggest gap in your score.",
        ))
    elif geo == 3:
        factors.append((
            "Showing up sometimes — not consistently.",
            f"You appear on AI tools occasionally, but not reliably. Consistency is what "
            f"separates businesses that get recommended from ones that get skipped.",
        ))
    else:
        factors.append((
            "AI tools are finding you.",
            f"You're showing up when {industry_term}s search in {city}. "
            f"Keeping this consistent is what keeps you ahead.",
        ))

    # Factor 2 — reviews
    try:
        r   = float(str(rating))
        cnt = int(str(reviews).replace(",", ""))
    except (ValueError, TypeError):
        r, cnt = 0, 0

    if r >= 4.5 and cnt >= 50:
        factors.append((
            "Strong review profile.",
            f"A {rating}\u2605 rating with {reviews} reviews is a genuine asset — AI tools "
            f"factor both into who they recommend.",
        ))
    elif cnt < 25:
        factors.append((
            "Review volume is a gap.",
            f"Fewer reviews means less signal for AI tools to work with. "
            f"Volume and recency both affect whether you show up.",
        ))
    else:
        factors.append((
            f"Solid rating at {rating}\u2605.",
            f"Your reviews are working in your favor. The opportunity is in the places "
            f"AI tools look that Google doesn't cover.",
        ))

    return factors


def get_why_losing(industry_term="customer", city="your area", featured_service=""):
    """
    Single paragraph explaining the mechanism — cookie-cutter with keyword substitution.
    """
    service = featured_service if featured_service else f"{industry_term} services"
    return (
        f"When a {industry_term} in {city} asks an AI tool for {service}, it picks one business — "
        f"not a list. It looks at reviews, listings, and how complete your presence is across the web. "
        f"The most consistent presence gets recommended. Gaps mean you get skipped."
    )


def get_aeo_cards():
    """
    Returns list of 3 (title, body) tuples for the "What Changes This" education section.
    Explains AEO/GEO principles in plain business-owner language.
    """
    return [
        (
            "One Answer, Not a List",
            "AI tools return one recommendation. Getting there means your presence has to be "
            "complete — reviews, listings, and citations all pointing at you.",
        ),
        (
            "Consistency Over Spend",
            "AI tools don't rank by ad budget. They rank by how consistent and complete your "
            "information is across every platform they read from.",
        ),
        (
            "The Window Is Open",
            "Most businesses in your area haven't built this yet. First to build it becomes "
            "the default answer — until someone catches up.",
        ),
    ]


def get_client_snapshot(data, industry_term="customer"):
    """
    Returns list of 3 (value, label, insight) tuples using the client's actual data.
    Used in the "Your Numbers" section.
    """
    rows      = []
    comp_name = data.get("comp_name", "your competitor")
    city      = data.get("business_city", "your area")

    # Row 1 — reviews vs competitor
    try:
        mine   = int(str(data.get("review_count", 0)).replace(",", ""))
        theirs = int(str(data.get("comp_reviews", 0)).replace(",", ""))
        gap    = theirs - mine
    except (ValueError, TypeError):
        mine, theirs, gap = 0, 0, 0

    if gap > 50:
        insight = (f"{comp_name} has {gap} more reviews. AI tools weight volume and recency "
                   f"— that gap is showing up in your score.")
    elif gap > 0:
        insight = (f"{comp_name} has a slight review lead. Closing that gap moves the needle "
                   f"on AI recommendations.")
    else:
        insight = ("You're holding your own on reviews. Keeping the volume growing is what "
                   "sustains the advantage.")
    rows.append((str(mine), "Your Reviews", insight))

    # Row 2 — AI visibility status
    geo       = data.get("geo_score", 1)
    geo_label = "Showing Up" if geo >= 4 else "Partial" if geo == 3 else "Not Visible"
    if geo <= 2:
        ai_insight = (f"AI tools aren't surfacing your business when {industry_term}s search "
                      f"in {city}. This is the single biggest lever in your score.")
    elif geo == 3:
        ai_insight = ("You show up some of the time. The gap between 'sometimes' and 'every "
                      "time' is a more complete presence.")
    else:
        ai_insight = ("You're showing up on AI tools. Maintaining this means keeping your "
                      "presence fresh and consistent.")
    rows.append((geo_label, "AI Visibility", ai_insight))

    # Row 3 — website speed or GBP photos
    ps = data.get("client_ps")
    if ps is not None:
        ps_val   = f"{ps}/100"
        ps_label = "Site Speed"
        if ps >= 70:
            ps_insight = ("Your site loads fast — that's a positive signal. AI tools factor "
                          "site quality into their reads.")
        elif ps >= 50:
            ps_insight = ("Your site is middling on speed. A slow site signals to AI tools "
                          "that your business isn't keeping up.")
        else:
            ps_insight = (f"A {ps}/100 speed score is holding you back. AI tools read site "
                          f"quality as a proxy for business quality.")
        rows.append((ps_val, ps_label, ps_insight))
    else:
        photos    = data.get("gbp_photo_count", 0)
        ph_insight = (
            "Strong photo count — your listing looks active, which AI tools favor."
            if photos >= 10 else
            "Thin photo count signals an incomplete listing. AI tools weight listing completeness."
        )
        rows.append((str(photos), "Profile Photos", ph_insight))

    return rows


def get_cta_headline():
    return "Let's get you found sooner."


def get_cta_subline(email, phone):
    return f"{email}  ·  Call or text Emmanuel  ·  {phone}"
