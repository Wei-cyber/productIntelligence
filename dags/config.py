"""
config.py

Single source of truth for connection info and constants.
Everything pulls from environment variables so the same code runs
locally (docker-compose), in Airflow, and in CI without edits.
"""

import os

from dotenv import load_dotenv

load_dotenv()  # reads .env in the current working directory, if present

# --- SerpAPI ---
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")
SERPAPI_BASE_URL = "https://serpapi.com/search.json"
AMAZON_DOMAIN = os.environ.get("AMAZON_DOMAIN", "amazon.com")

# Queries to track over time. Each one becomes a recurring "watch".
TRACKED_QUERIES = os.environ.get("TRACKED_QUERIES", "Coffee").split(",")

# --- Postgres (the "warehouse") ---
PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_PORT = os.environ.get("PG_PORT", "5432")
PG_DB = os.environ.get("PG_DB", "product_intel")
PG_USER = os.environ.get("PG_USER", "postgres")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "postgres")

SQLALCHEMY_URL = (
    f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
)

# --- Misc ---
# Where extract.py drops raw JSON payloads before they're loaded into bronze.
RAW_DUMP_DIR = os.environ.get("RAW_DUMP_DIR", "/tmp/product_pipeline_raw")
