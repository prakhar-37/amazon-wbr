import asyncio
import random
import sys
from datetime import date, datetime, timezone

import duckdb
from playwright.async_api import async_playwright

import config

# ── Mock data ────────────────────────────────────────────────────────────────
# A pool of 25 realistic Amazon India Handmade products.
# --mock draws 20 of them each week (different selection per ISO week),
# with slight rank shuffling and ±10% price noise — so week-over-week
# comparisons in analyze.py have real movement to report.

_MOCK_POOL = [
    {"title": "Handcrafted Brass Diya Set (Set of 5)",          "price": 499.0,  "rating": 4.3},
    {"title": "Hand-Painted Madhubani Art Frame",               "price": 849.0,  "rating": 4.5},
    {"title": "Jute Tote Bag with Embroidery",                  "price": 349.0,  "rating": 4.2},
    {"title": "Terracotta Planter Set (3 pcs)",                 "price": 599.0,  "rating": 4.4},
    {"title": "Handwoven Silk Stole - Banarasi",                "price": 1299.0, "rating": 4.6},
    {"title": "Wooden Elephant Figurine - Rajasthani",          "price": 449.0,  "rating": 4.1},
    {"title": "Hand-Block Printed Kurta Fabric (2.5 m)",        "price": 699.0,  "rating": 4.3},
    {"title": "Bamboo Incense Holder with Drawers",             "price": 299.0,  "rating": 4.5},
    {"title": "Kalamkari Cushion Cover Set (2 pcs)",            "price": 549.0,  "rating": 4.2},
    {"title": "Handmade Silver Oxidised Earrings",              "price": 799.0,  "rating": 4.7},
    {"title": "Warli Art Ceramic Mug",                          "price": 399.0,  "rating": 4.4},
    {"title": "Natural Beeswax Candle Set (6 pcs)",             "price": 649.0,  "rating": 4.6},
    {"title": "Handloom Cotton Dhurrie Rug (4×6 ft)",           "price": 2499.0, "rating": 4.3},
    {"title": "Pattachitra Wooden Jewellery Box",               "price": 999.0,  "rating": 4.5},
    {"title": "Hand-Stitched Leather Journal",                  "price": 749.0,  "rating": 4.4},
    {"title": "Dokra Brass Tribal Wall Hanging",                "price": 1199.0, "rating": 4.2},
    {"title": "Handmade Macramé Plant Hanger",                  "price": 449.0,  "rating": 4.5},
    {"title": "Block Print Indigo Bedsheet (King)",             "price": 1499.0, "rating": 4.3},
    {"title": "Coconut Shell Bowl Set (4 pcs)",                 "price": 379.0,  "rating": 4.1},
    {"title": "Handwoven Bamboo Storage Basket",                "price": 529.0,  "rating": 4.4},
    {"title": "Tanjore Painting - Ganesh (12×16 in)",           "price": 3499.0, "rating": 4.7},
    {"title": "Hand-Dyed Shibori Silk Scarf",                   "price": 899.0,  "rating": 4.5},
    {"title": "Ceramic Chai Set with Wooden Tray",              "price": 849.0,  "rating": 4.6},
    {"title": "Handmade Cane Rocking Chair",                    "price": 8999.0, "rating": 4.3},
    {"title": "Natural Henna Powder (Premium, 200 g)",          "price": 199.0,  "rating": 4.2},
]


def generate_mock_items() -> list[dict]:
    """Return 20 products with week-seeded variation — deterministic per ISO week."""
    today = date.today()
    seed = today.year * 100 + today.isocalendar()[1]
    rng = random.Random(seed)

    pool = _MOCK_POOL[:]
    rng.shuffle(pool)
    selected = pool[: config.TOP_N]

    items = []
    for rank, product in enumerate(selected, start=1):
        price = round(product["price"] * (1 + rng.uniform(-0.10, 0.10)), 2)
        rating = round(min(5.0, max(3.5, product["rating"] + rng.uniform(-0.1, 0.1))), 1)
        items.append({"rank": rank, "title": product["title"], "price": price, "rating": rating})
    return items


async def scrape() -> list[dict]:
    items = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-IN",
            viewport={"width": 1280, "height": 900},
        )
        # Remove the navigator.webdriver flag that flags us as a bot
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await context.new_page()

        print(f"Opening {config.SCRAPE_URL} ...")
        await page.goto(config.SCRAPE_URL, wait_until="networkidle", timeout=90_000)
        await page.wait_for_timeout(5_000)  # let JS-rendered cards populate

        # Amazon uses either div or li for each bestseller card
        cards = await page.query_selector_all("div.zg-item-immersion")
        if not cards:
            cards = await page.query_selector_all("li.zg-item-immersion")

        if not cards:
            print("WARNING: No product cards found. Amazon may have changed layout or shown a CAPTCHA.")
            await browser.close()
            return []

        print(f"Found {len(cards)} cards, extracting top {config.TOP_N} ...")

        for card in cards[: config.TOP_N]:
            rank = await _extract_rank(card)
            title = await _extract_text(card, [
                "._cDEzb_p13n-sc-css-line-clamp-1_1Fn1y",
                ".p13n-sc-truncate-desktop-type2",
                ".p13n-sc-truncate",
                "a.a-link-normal span",
            ])
            price = await _extract_price(card)
            rating = await _extract_rating(card)

            if title:
                items.append({"rank": rank, "title": title, "price": price, "rating": rating})

        await browser.close()
    return items


async def _extract_rank(card) -> int | None:
    el = await card.query_selector(".zg-bdg-text")
    if not el:
        return None
    text = (await el.inner_text()).strip().lstrip("#")
    return int(text) if text.isdigit() else None


async def _extract_text(card, selectors: list[str]) -> str | None:
    for sel in selectors:
        el = await card.query_selector(sel)
        if el:
            return (await el.inner_text()).strip()
    return None


async def _extract_price(card) -> float | None:
    for sel in ["._cDEzb_p13n-sc-price_3mJ9Z", ".p13n-sc-price"]:
        el = await card.query_selector(sel)
        if el:
            raw = (await el.inner_text()).replace("₹", "").replace(",", "").strip()
            try:
                return float(raw)
            except ValueError:
                return None
    return None


async def _extract_rating(card) -> float | None:
    el = await card.query_selector(".a-icon-alt")
    if el:
        try:
            return float((await el.inner_text()).split()[0])
        except (ValueError, IndexError):
            pass
    return None


def save_to_db(items: list[dict]) -> None:
    config.DATA_DIR.mkdir(exist_ok=True)
    con = duckdb.connect(str(config.DB_PATH))
    con.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            scraped_at  TIMESTAMPTZ,
            rank        INTEGER,
            title       VARCHAR,
            price       DOUBLE,
            rating      DOUBLE
        )
    """)
    now = datetime.now(timezone.utc)
    con.executemany(
        "INSERT INTO snapshots VALUES (?, ?, ?, ?, ?)",
        [(now, r["rank"], r["title"], r["price"], r["rating"]) for r in items],
    )
    con.close()
    print(f"Saved {len(items)} products at {now.strftime('%Y-%m-%d %H:%M UTC')}")


if __name__ == "__main__":
    if "--mock" in sys.argv:
        print("Mock mode: generating synthetic bestseller data ...")
        items = generate_mock_items()
        print(f"Generated {len(items)} mock products (week-seed: {date.today().isocalendar()[1]})")
    else:
        items = asyncio.run(scrape())

    if items:
        save_to_db(items)
    else:
        print("Nothing saved — check your internet connection or try again later.")
        print("Tip: run  python scraper.py --mock  to use synthetic data instead.")
