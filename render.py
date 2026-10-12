import json
import re
import sys
from datetime import datetime, timezone

from jinja2 import Template

import config
import narrate


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Amazon India Handmade · WBR {{ week_of }}</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                   'Helvetica Neue', Arial, sans-serif;
      font-size: 15px; line-height: 1.65; color: #1a202c; background: #f8fafc;
    }
    a { color: {{ accent }}; }

    header {
      background: {{ accent }}; color: #fff; padding: 2rem 1.5rem 1.5rem;
    }
    header h1 { font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em; }
    header .meta { margin-top: 0.35rem; font-size: 0.85rem; opacity: 0.85; }

    .container { max-width: 860px; margin: 0 auto; padding: 2rem 1.5rem; }

    .narrative {
      background: #fff; border-radius: 8px; padding: 2rem;
      margin-bottom: 2rem; box-shadow: 0 1px 3px rgba(0,0,0,.08);
    }
    .narrative h2 {
      font-size: 0.875rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.07em; color: {{ accent }};
      border-bottom: 2px solid {{ accent }}; padding-bottom: 0.35rem;
      margin: 1.75rem 0 0.65rem;
    }
    .narrative h2:first-child { margin-top: 0; }
    .narrative p { color: #374151; margin-bottom: 0.65rem; }

    .card {
      background: #fff; border-radius: 8px; padding: 1.5rem;
      margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,.08);
    }
    .card h2 {
      font-size: 0.875rem; font-weight: 700; color: {{ accent }};
      text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 1rem;
    }

    table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
    th {
      text-align: left; padding: 0.5rem 0.75rem; font-weight: 600;
      color: #6b7280; border-bottom: 2px solid #e5e7eb; white-space: nowrap;
    }
    td { padding: 0.45rem 0.75rem; border-bottom: 1px solid #f3f4f6; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #f0fdfa; }
    .rank { font-weight: 700; color: {{ accent }}; width: 3rem; }
    .num  { font-variant-numeric: tabular-nums; }
    .up   { color: #16a34a; font-weight: 600; }
    .down { color: #dc2626; font-weight: 600; }
    .badge {
      display: inline-block; background: {{ accent }}; color: #fff;
      font-size: 0.68rem; font-weight: 700; padding: 0.1rem 0.4rem;
      border-radius: 999px; margin-left: 0.4rem; vertical-align: middle;
    }

    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
    @media (max-width: 620px) { .grid-2 { grid-template-columns: 1fr; } }

    .empty { color: #9ca3af; font-style: italic; font-size: 0.875rem; }

    footer {
      text-align: center; padding: 2rem 1rem;
      font-size: 0.78rem; color: #9ca3af;
    }
    footer strong { color: {{ accent }}; }
  </style>
</head>
<body>

<header>
  <div style="max-width:860px;margin:0 auto">
    <h1>Amazon India &middot; Handmade</h1>
    <div class="meta">
      Weekly Business Review &nbsp;&middot;&nbsp; Week of {{ week_of }}
      &nbsp;&middot;&nbsp; {{ weeks_of_data }} week{{ 's' if weeks_of_data != 1 else '' }} of data
    </div>
  </div>
</header>

<div class="container">

  <div class="narrative">
    {% for section in narrative_sections %}
      {% if section.heading %}<h2>{{ section.heading }}</h2>{% endif %}
      {% for para in section.paragraphs %}<p>{{ para }}</p>{% endfor %}
    {% endfor %}
  </div>

  <div class="card">
    <h2>Current Top 20</h2>
    <table>
      <thead>
        <tr><th>#</th><th>Product</th><th>Price (&#8377;)</th><th>Rating</th></tr>
      </thead>
      <tbody>
        {% for p in top20 %}
        <tr>
          <td class="rank">{{ p.rank or '&mdash;' }}</td>
          <td>
            {{ p.title }}
            {% if p.title in new_titles %}<span class="badge">NEW</span>{% endif %}
          </td>
          <td class="num">{{ '%.2f' | format(p.price) if p.price else '&mdash;' }}</td>
          <td>{{ p.rating or '&mdash;' }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <div class="grid-2">

    <div class="card">
      <h2>Climbers</h2>
      {% if climbers %}
      <table>
        <thead><tr><th>Product</th><th>Was</th><th>Now</th><th>&Delta;</th></tr></thead>
        <tbody>
          {% for c in climbers %}
          <tr>
            <td>{{ c.title }}</td>
            <td class="num">{{ c.rank_prev }}</td>
            <td class="num">{{ c.rank_now }}</td>
            <td class="up">&#9650; {{ c.positions_gained }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}<p class="empty">No significant climbers this week.</p>{% endif %}
    </div>

    <div class="card">
      <h2>Fallers</h2>
      {% if fallers %}
      <table>
        <thead><tr><th>Product</th><th>Was</th><th>Now</th><th>&Delta;</th></tr></thead>
        <tbody>
          {% for f in fallers %}
          <tr>
            <td>{{ f.title }}</td>
            <td class="num">{{ f.rank_prev }}</td>
            <td class="num">{{ f.rank_now }}</td>
            <td class="down">&#9660; {{ f.positions_lost }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}<p class="empty">No significant fallers this week.</p>{% endif %}
    </div>

    <div class="card">
      <h2>New Entrants</h2>
      {% if new_entrants %}
      <table>
        <thead><tr><th>Product</th><th>Rank</th></tr></thead>
        <tbody>
          {% for e in new_entrants %}
          <tr><td>{{ e.title }}</td><td class="rank">{{ e.rank }}</td></tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}<p class="empty">No new entrants this week.</p>{% endif %}
    </div>

    <div class="card">
      <h2>Dropouts</h2>
      {% if dropouts %}
      <table>
        <thead><tr><th>Product</th><th>Last rank</th></tr></thead>
        <tbody>
          {% for d in dropouts %}
          <tr><td>{{ d.title }}</td><td class="rank">{{ d.last_rank }}</td></tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}<p class="empty">No dropouts this week.</p>{% endif %}
    </div>

  </div>

  {% if price_changes or price_anomalies %}
  <div class="card">
    <h2>Price Signals</h2>
    <table>
      <thead>
        <tr><th>Product</th><th>Now (&#8377;)</th><th>Prev (&#8377;)</th><th>Change</th><th>Note</th></tr>
      </thead>
      <tbody>
        {% for pc in price_changes %}
        <tr>
          <td>{{ pc.title }}</td>
          <td class="num">{{ '%.2f' | format(pc.price_now) }}</td>
          <td class="num">{{ '%.2f' | format(pc.price_prev) }}</td>
          <td class="{{ 'up' if pc.change_pct > 0 else 'down' }}">
            {{ '%+.1f' | format(pc.change_pct) }}%
          </td>
          <td>WoW move</td>
        </tr>
        {% endfor %}
        {% for a in price_anomalies %}
        <tr>
          <td>{{ a.title }}</td>
          <td class="num">{{ '%.2f' | format(a.price) }}</td>
          <td class="num">&mdash;</td>
          <td>&mdash;</td>
          <td>{{ a.direction }} (z&nbsp;=&nbsp;{{ a.z_score }})</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}

</div>

<footer>
  Generated {{ generated_at }} &nbsp;&middot;&nbsp;
  <strong>Amazon India Handmade WBR</strong> &nbsp;&middot;&nbsp;
  Data scraped from amazon.in &nbsp;&middot;&nbsp; For internal review only
</footer>

</body>
</html>
"""


def parse_narrative(text: str) -> list[dict]:
    """Split '## Heading\\nbody' format into [{heading, paragraphs}] dicts."""
    parts = re.split(r"^##\s+(.+)$", text.strip(), flags=re.MULTILINE)
    sections = []
    if parts[0].strip():
        sections.append({
            "heading": None,
            "paragraphs": [l.strip() for l in parts[0].strip().splitlines() if l.strip()],
        })
    for heading, body in zip(parts[1::2], parts[2::2]):
        sections.append({
            "heading": heading.strip(),
            "paragraphs": [l.strip() for l in body.strip().splitlines() if l.strip()],
        })
    if not sections:
        sections.append({"heading": None, "paragraphs": [text.strip()]})
    return sections


def render(insights: dict, narrative_text: str) -> str:
    new_titles = {e["title"] for e in insights.get("new_entrants", [])}
    return Template(HTML_TEMPLATE).render(
        accent=config.ACCENT_COLOR,
        week_of=insights.get("week_of", "—"),
        weeks_of_data=insights.get("weeks_of_data", 1),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        narrative_sections=parse_narrative(narrative_text),
        top20=insights.get("current_top20", []),
        new_titles=new_titles,
        climbers=insights.get("rank_movers", {}).get("climbers", []),
        fallers=insights.get("rank_movers", {}).get("fallers", []),
        new_entrants=insights.get("new_entrants", []),
        dropouts=insights.get("dropouts", []),
        price_changes=insights.get("price_changes", []),
        price_anomalies=insights.get("price_anomalies", []),
    )


if __name__ == "__main__":
    if not config.INSIGHTS_PATH.exists():
        print("No insights.json found. Run analyze.py first.")
        sys.exit(1)

    with open(config.INSIGHTS_PATH, encoding="utf-8") as f:
        insights = json.load(f)

    narrative_text = narrate.get_narrative()

    config.OUTPUT_DIR.mkdir(exist_ok=True)
    html = render(insights, narrative_text)
    config.OUTPUT_HTML.write_text(html, encoding="utf-8")

    print(f"HTML written to {config.OUTPUT_HTML}")
    print(f"Open in browser: {config.OUTPUT_HTML.resolve()}")
