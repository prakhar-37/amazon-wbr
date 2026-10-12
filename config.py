from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "docs"

DB_PATH = DATA_DIR / "wbr.db"
INSIGHTS_PATH = DATA_DIR / "insights.json"
NARRATIVE_PATH = DATA_DIR / "narrative.txt"
OUTPUT_HTML = OUTPUT_DIR / "index.html"

SCRAPE_URL = "https://www.amazon.in/gp/bestsellers/handmade"
TOP_N = 20  # how many bestsellers to track

ACCENT_COLOR = "#0d9488"
