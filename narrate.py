"""
narrate.py — bridge between insights.json and render.py

Manual workflow:
  1. Run analyze.py  →  data/insights.json is created
  2. Run narrate.py  →  copy the printed prompt + paste insights.json into claude.ai
  3. Copy Claude's response → save as data/narrative.txt
  4. Run render.py   →  output/index.html is produced
"""

import json
import sys
import textwrap

import config


def get_narrative() -> str:
    """Read narrative.txt and return its contents. Called by render.py."""
    if not config.NARRATIVE_PATH.exists():
        print(
            f"\nERROR: {config.NARRATIVE_PATH} not found.\n"
            "Run  python narrate.py  for instructions on creating it."
        )
        sys.exit(1)

    text = config.NARRATIVE_PATH.read_text(encoding="utf-8").strip()
    if not text:
        print(f"\nERROR: {config.NARRATIVE_PATH} is empty. Paste your Claude.ai narrative into it.")
        sys.exit(1)

    return text


def _build_claude_prompt(insights: dict) -> str:
    week = insights.get("week_of", "this week")
    n_weeks = insights.get("weeks_of_data", 1)
    top = insights.get("current_top20", [])
    top3 = ", ".join(f"#{p['rank']} {p['title']}" for p in top[:3] if p.get("rank"))

    new_in = insights.get("new_entrants", [])
    dropped = insights.get("dropouts", [])
    climbers = insights.get("rank_movers", {}).get("climbers", [])
    price_changes = insights.get("price_changes", [])
    anomalies = insights.get("price_anomalies", [])

    bullets = []
    if new_in:
        titles = ", ".join(p["title"] for p in new_in[:3])
        bullets.append(f"- New entrants this week: {titles}")
    if dropped:
        titles = ", ".join(p["title"] for p in dropped[:3])
        bullets.append(f"- Products that dropped off: {titles}")
    if climbers:
        c = climbers[0]
        bullets.append(f"- Biggest climber: {c['title']} (rank {c['rank_prev']} -> {c['rank_now']})")
    if price_changes:
        pc = price_changes[0]
        bullets.append(f"- Largest price move: {pc['title']} ({pc['change_pct']:+.1f}%)")
    if anomalies:
        a = anomalies[0]
        bullets.append(f"- Price outlier: {a['title']} (₹{a['price']}, {a['direction']})")

    highlights = "\n".join(bullets) if bullets else "- (First week of data — no prior-week comparison yet)"

    return textwrap.dedent(f"""
        You are an Amazon business analyst writing an internal Weekly Business Review (WBR).
        Write in Amazon's 6-pager narrative style: full prose paragraphs, no bullet points,
        data-driven, crisp, and direct. One page maximum (~400 words).

        Context:
        - Category: Amazon India Handmade bestsellers
        - Week of: {week}
        - Weeks of historical data: {n_weeks}
        - Current top 3: {top3}

        Key signals this week:
        {highlights}

        Full data (insights.json):
        ---
        [PASTE THE CONTENTS OF data/insights.json HERE]
        ---

        Structure your narrative with these four short sections (use plain ## headers):
        ## Headline
        One sentence that captures the single most important thing that happened this week.

        ## Performance Overview
        2–3 sentences on the overall state of the top 20 — stability, price trends, rating patterns.

        ## Notable Movements
        2–3 sentences on the most significant rank changes, new entrants, or dropouts.

        ## Watch List
        1–2 sentences on what to monitor next week — anomalies, emerging products, risks.
    """).strip()


if __name__ == "__main__":
    if not config.INSIGHTS_PATH.exists():
        print("No insights.json found. Run analyze.py first.")
        sys.exit(1)

    with open(config.INSIGHTS_PATH, encoding="utf-8") as f:
        insights = json.load(f)

    if config.NARRATIVE_PATH.exists():
        text = config.NARRATIVE_PATH.read_text(encoding="utf-8").strip()
        if text:
            print(f"narrative.txt found ({len(text.split())} words). Preview:\n")
            print("-" * 60)
            print(text[:600] + ("..." if len(text) > 600 else ""))
            print("-" * 60)
            print("\nLooks good — run  python render.py  to build the HTML.")
            sys.exit(0)

    print("=" * 60)
    print("STEP: Create data/narrative.txt")
    print("=" * 60)
    print()
    print("1. Open claude.ai in your browser (free account works).")
    print("2. Start a new chat and paste the prompt below.")
    print("3. Replace the placeholder with the actual contents of")
    print(f"   {config.INSIGHTS_PATH}")
    print("4. Copy Claude's full response.")
    print(f"5. Save it as:  {config.NARRATIVE_PATH}")
    print("6. Run:  python render.py")
    print()
    print("=" * 60)
    print("PROMPT TO PASTE INTO CLAUDE.AI:")
    print("=" * 60)
    print()
    print(_build_claude_prompt(insights))
    print()
