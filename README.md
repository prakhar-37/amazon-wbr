# Amazon India Handmade WBR Auto-Generator

A pipeline that scrapes Amazon India's Handmade bestsellers, detects
anomalies with statistical analysis, and produces a one-page Weekly
Business Review (WBR) in Amazon's 6-pager narrative style — published
as a live HTML page.

**Live report:** https://prakhar-37.github.io/amazon-wbr

---

## What it does

| Step | Script | Output |
|------|--------|--------|
| 1. Snapshot bestsellers | `scraper.py` | `data/wbr.db` (DuckDB) |
| 2. Detect anomalies | `analyze.py` | `data/insights.json` |
| 3. Write narrative | Manual via claude.ai | `data/narrative.txt` |
| 4. Render report | `render.py` | `output/index.html` |

## Weekly workflow

```bash
# Activate virtual environment (Windows)
.\.venv\Scripts\Activate.ps1

# 1. Take this week's snapshot
python scraper.py --mock        # or without --mock if live scraping works

# 2. Analyse
python analyze.py

# 3. Get the Claude.ai prompt, paste insights.json, save response as data/narrative.txt
python narrate.py

# 4. Build the HTML report
python render.py

# 5. Publish
git add output/index.html
git commit -m "WBR update: week of YYYY-MM-DD"
git push
```

## Setup

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install playwright pandas duckdb scipy anthropic jinja2 python-dotenv beautifulsoup4
playwright install chromium
```

No API keys required. Narrative is generated manually via the free
[claude.ai](https://claude.ai) chat interface.

## Stack

- **Playwright** — headless browser scraping
- **DuckDB** — lightweight local database for weekly snapshots
- **pandas + scipy** — week-over-week analysis and Z-score anomaly detection
- **Jinja2** — HTML templating
- **Claude.ai** — free AI narrative generation (manual step)
- **GitHub Pages** — report hosting
