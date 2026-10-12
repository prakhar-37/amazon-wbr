import json
from datetime import datetime, timezone

import duckdb
import pandas as pd
from scipy import stats

import config


def load_snapshots() -> pd.DataFrame:
    con = duckdb.connect(str(config.DB_PATH), read_only=True)
    df = con.execute("SELECT * FROM snapshots ORDER BY scraped_at").fetchdf()
    con.close()
    return df


def split_weeks(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Return (current_week, prior_week). Prior is None if only one scrape exists."""
    dates = sorted(df["scraped_at"].dt.date.unique())
    current = df[df["scraped_at"].dt.date == dates[-1]].copy()
    prior = df[df["scraped_at"].dt.date == dates[-2]].copy() if len(dates) >= 2 else None
    return current, prior


def price_anomalies(current: pd.DataFrame) -> list[dict]:
    """Flag products whose price is 2+ standard deviations from the category mean."""
    prices = current["price"].dropna()
    if len(prices) < 4:
        return []
    z_scores = stats.zscore(prices)
    results = []
    for idx, z in zip(prices.index, z_scores):
        if abs(z) >= 2.0:
            row = current.loc[idx]
            results.append({
                "title": row["title"],
                "rank": _int(row["rank"]),
                "price": _float(row["price"]),
                "z_score": round(float(z), 2),
                "direction": "unusually high" if z > 0 else "unusually low",
            })
    return results


def build_insights(current: pd.DataFrame, prior: pd.DataFrame | None, n_snapshots: int) -> dict:
    top20 = [
        {
            "rank": _int(row["rank"]),
            "title": row["title"],
            "price": _float(row["price"]),
            "rating": _float(row["rating"]),
        }
        for _, row in current.sort_values("rank").iterrows()
    ]

    insights: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "week_of": str(current["scraped_at"].dt.date.iloc[0]),
        "weeks_of_data": n_snapshots,
        "current_top20": top20,
        "new_entrants": [],
        "dropouts": [],
        "rank_movers": {"climbers": [], "fallers": []},
        "price_changes": [],
        "price_anomalies": price_anomalies(current),
    }

    if prior is None:
        return insights

    current_titles = set(current["title"])
    prior_titles = set(prior["title"])

    # New entrants: on the list this week, not last week
    insights["new_entrants"] = sorted(
        [
            {"title": t, "rank": _int(current.loc[current["title"] == t, "rank"].iloc[0])}
            for t in current_titles - prior_titles
        ],
        key=lambda x: x["rank"] or 99,
    )

    # Dropouts: on the list last week, gone this week
    insights["dropouts"] = sorted(
        [
            {"title": t, "last_rank": _int(prior.loc[prior["title"] == t, "rank"].iloc[0])}
            for t in prior_titles - current_titles
        ],
        key=lambda x: x["last_rank"] or 99,
    )

    # Rank movers: products that appear in both weeks
    merged = current.merge(prior, on="title", suffixes=("_now", "_prev"))
    # positive rank_change = climbed (e.g. was rank 10, now rank 3 → change = +7)
    merged["rank_change"] = merged["rank_prev"] - merged["rank_now"]

    climbers = merged[merged["rank_change"] > 3].sort_values("rank_change", ascending=False)
    fallers = merged[merged["rank_change"] < -3].sort_values("rank_change")

    insights["rank_movers"]["climbers"] = [
        {
            "title": r["title"],
            "rank_now": _int(r["rank_now"]),
            "rank_prev": _int(r["rank_prev"]),
            "positions_gained": _int(r["rank_change"]),
        }
        for _, r in climbers.iterrows()
    ]
    insights["rank_movers"]["fallers"] = [
        {
            "title": r["title"],
            "rank_now": _int(r["rank_now"]),
            "rank_prev": _int(r["rank_prev"]),
            "positions_lost": _int(abs(r["rank_change"])),
        }
        for _, r in fallers.iterrows()
    ]

    # Price changes > 10% week-over-week
    pm = merged[merged["price_now"].notna() & merged["price_prev"].notna()].copy()
    pm["pct"] = ((pm["price_now"] - pm["price_prev"]) / pm["price_prev"] * 100).round(1)
    significant = pm[pm["pct"].abs() > 10].sort_values("pct", key=abs, ascending=False)

    insights["price_changes"] = [
        {
            "title": r["title"],
            "price_now": _float(r["price_now"]),
            "price_prev": _float(r["price_prev"]),
            "change_pct": float(r["pct"]),
        }
        for _, r in significant.iterrows()
    ]

    return insights


def _int(val) -> int | None:
    try:
        return int(val) if pd.notna(val) else None
    except (TypeError, ValueError):
        return None


def _float(val) -> float | None:
    try:
        return round(float(val), 2) if pd.notna(val) else None
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    if not config.DB_PATH.exists():
        print("No database found. Run scraper.py first.")
        raise SystemExit(1)

    df = load_snapshots()
    n_snapshots = df["scraped_at"].dt.date.nunique()
    current, prior = split_weeks(df)
    insights = build_insights(current, prior, n_snapshots)

    if prior is None:
        print("Only one week of data — comparisons will be empty until next week's scrape.")

    config.DATA_DIR.mkdir(exist_ok=True)
    with open(config.INSIGHTS_PATH, "w", encoding="utf-8") as f:
        json.dump(insights, f, indent=2, ensure_ascii=False)

    print(f"insights.json written to {config.INSIGHTS_PATH}")
    print(f"  Weeks of data : {n_snapshots}")
    print(f"  Top product   : {insights['current_top20'][0]['title'] if insights['current_top20'] else 'none'}")
    print(f"  New entrants  : {len(insights['new_entrants'])}")
    print(f"  Dropouts      : {len(insights['dropouts'])}")
    print(f"  Climbers      : {len(insights['rank_movers']['climbers'])}")
    print(f"  Fallers       : {len(insights['rank_movers']['fallers'])}")
    print(f"  Price changes : {len(insights['price_changes'])}")
    print(f"  Price anomalies: {len(insights['price_anomalies'])}")
