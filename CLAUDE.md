# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A CLI tool that generates a single-page PDF visibility audit report for local business prospects. Emmanuel (Queso Ventures) runs it before a sales call to produce a printed one-pager that compares the prospect against a competitor across reviews, Google Maps presence, and AI search visibility.

## Running the Tool

```bash
# Activate the venv and load API keys, then run
source venv/bin/activate
source .env && python main.py
```

The tool prompts interactively for all inputs and saves the PDF to `~/Desktop/audit_<business>_<date>.pdf` (or CWD if no Desktop).

## Architecture

Three files, strict separation of concerns:

**`webAudit.py`** — data collection only, no PDF logic
- `collect_data()`: interactive CLI wizard; fetches website HTML, runs PageSpeed API, queries Google Places API, asks scoring questions. Returns a `data` dict consumed by `main.py`.
- `calc_visibility_score(data)`: computes the 0–100 visibility score from five weighted sub-scores (website 20%, speed 10%, GBP 20%, maps 20%, AI 30%).
- `build_findings(data, auto_findings)`: generates 3 business-outcome-focused finding strings.
- Requires env vars: `PAGESPEED_KEY`, `PLACES_API_KEY`

**`aiAudit.py`** — copy/content only, no PDF logic and no data fetching
- Functions return plain strings or lists of tuples used verbatim in the PDF.
- `get_competitor_rows()` / `get_competitor_takeaway()`: the competitor table content.
- `get_findings()`: 3 `(headline, body)` tuples for the "What This Means" section.
- `get_explainer()`: the "So What's Going On?" paragraph.
- Edit all PDF copy here.

**`main.py`** — PDF layout engine only
- `build_pdf(data, output_path)`: draws the entire single-page PDF using ReportLab's canvas API (no high-level abstractions).
- Layout is cursor-based (starts at top of page, moves down). Pre-measures all dynamic text heights before drawing so everything fits on one page.
- Brand colors are defined as constants at the top (`C_RED`, `C_ORANGE`, `C_GREEN`, etc.).
- `ensure_logo()`: downloads and caches `.qv_logo.png` from quesoventures.com on first run.

## Key Design Constraints

- **One page only** — the layout pre-measures every section and divides remaining space proportionally among findings. Do not add sections without accounting for the budget.
- **No AI jargon in copy** — use "the new search" not "AI search" or "AEO/GEO" in customer-facing text. `aiAudit.py` enforces this.
- **Industry-specific language** — `INDUSTRY_TERMS` in `webAudit.py` maps business types to the right word for "customer" (patient, guest, member, client). All copy functions accept `industry_term` and use it.
- **Orange vs Blue clients** — Orange = AI visibility pitch (client has a working site, needs presence everywhere AI looks). Blue = fundamentals pitch (no site or broken site). The audit is built for Orange clients; Blue clients get a different in-person approach.

## Dependencies

```bash
pip install -r requirements.txt
```

Main packages: `reportlab` (PDF), `requests` (HTTP), `beautifulsoup4` (HTML parsing), `pillow` (image handling for logo).
