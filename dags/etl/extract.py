"""
etl/extract.py

BRONZE layer producer.

Responsibility: hit SerpAPI, get the raw response back, and persist it
*unmodified* (as JSON files + a row in bronze_raw_results).
"""

import json
import logging
import os
import time
from datetime import datetime, timezone

import requests
from sqlalchemy import create_engine, text

import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_search_results(query: str, page: int = 1) -> dict:
    """Call SerpAPI's amazon engine for a single query/page."""
    params = {
        "engine": "amazon",
        "amazon_domain": config.AMAZON_DOMAIN,
        "k": query,
        "page": page,
        "api_key": config.SERPAPI_KEY,
    }
    resp = requests.get(config.SERPAPI_BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def dump_raw_to_disk(query: str, payload: dict, captured_at: datetime) -> str:
    """Write the raw payload to disk. Returns the file path."""
    os.makedirs(config.RAW_DUMP_DIR, exist_ok=True)
    safe_query = query.strip().replace(" ", "_").lower()
    fname = f"{safe_query}_{captured_at.strftime('%Y%m%dT%H%M%S')}.json"
    path = os.path.join(config.RAW_DUMP_DIR, fname)
    with open(path, "w") as f:
        json.dump(payload, f)
    return path


def persist_raw_to_bronze(query: str, payload: dict, captured_at: datetime, engine=None):
    """Insert one row per raw API call into bronze_raw_results."""
    engine = engine or create_engine(config.SQLALCHEMY_URL)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO bronze_raw_results (query, captured_at, raw_json)
                VALUES (:query, :captured_at, :raw_json)
                """
            ),
            {
                "query": query,
                "captured_at": captured_at,
                "raw_json": json.dumps(payload),
            },
        )


def run_extract(queries=None):
    """Entry point used by the Airflow task / CLI."""
    queries = queries or config.TRACKED_QUERIES
    engine = create_engine(config.SQLALCHEMY_URL)
    captured_paths = []

    for q in queries:
        q = q.strip()
        if not q:
            continue
        logger.info("Fetching SerpAPI results for query=%r", q)
        captured_at = datetime.now(timezone.utc)
        try:
            payload = fetch_search_results(q)
        except requests.RequestException as exc:
            logger.error("SerpAPI request failed for %r: %s", q, exc)
            continue

        path = dump_raw_to_disk(q, payload, captured_at)
        persist_raw_to_bronze(q, payload, captured_at, engine=engine)
        captured_paths.append(path)
        time.sleep(1)

    logger.info("Extract complete. %d payload(s) captured.", len(captured_paths))
    return captured_paths


if __name__ == "__main__":
    run_extract()
