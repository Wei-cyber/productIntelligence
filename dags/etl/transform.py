"""
etl/transform.py

SILVER layer producer.

Responsibility: take raw bronze JSON (one Amazon search-results page) and
flatten it into a clean, typed list of product-snapshot records — one row
per (asin, query, captured_at). This is where we handle the messiness of
the API response: missing fields, "$6.91" -> 6.91, sponsored flags, etc.

Nothing here writes to the warehouse — it returns plain dicts so it can be
unit-tested without a database, and load.py owns all persistence.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_result_item(item: dict, query: str, captured_at: datetime) -> dict:
    """
    Flatten a single entry from `organic_results` (or `sponsored_results`)
    into our silver schema. Field names below mirror what SerpAPI's
    amazon_search engine actually returns — see extract.py's raw payloads.
    """
    return {
        "asin": item.get("asin"),
        "query": query,
        "captured_at": captured_at,
        "position": _safe_int(item.get("position")),
        "title": item.get("title"),
        "brand": "amazon_brand" if item.get("amazon_brand") else None,
        "sponsored": bool(item.get("sponsored", False)),
        "rating": _safe_float(item.get("rating")),
        "reviews": _safe_int(item.get("reviews")),
        "price": _safe_float(item.get("extracted_price")),
        "price_per_unit": _safe_float(item.get("extracted_price_unit")),
        "old_price": _safe_float(item.get("extracted_old_price")),
        "is_climate_pledge_friendly": bool(item.get("climate_pledge_friendly", False)),
        "is_small_business": bool(item.get("small_business", False)),
        "bought_last_month_raw": item.get("bought_last_month"),
        "link_clean": item.get("link_clean"),
        "thumbnail": item.get("thumbnail"),
    }


def transform_payload(payload: dict, query: str, captured_at: datetime = None) -> list[dict]:
    """
    Turn one raw SerpAPI payload into a list of silver-layer row dicts.
    Handles both `organic_results` and `sponsored_results` if present —
    SerpAPI sometimes splits them, sometimes folds sponsored items into
    `organic_results` with a `sponsored: true` flag (as in the sample data).
    """
    captured_at = captured_at or datetime.now(timezone.utc)
    rows = []

    for key in ("organic_results", "sponsored_results"):
        for item in payload.get(key, []) or []:
            if not item.get("asin"):
                # Can't track price/ranking history without a stable product id.
                continue
            rows.append(parse_result_item(item, query, captured_at))

    logger.info("Transformed %d row(s) for query=%r", len(rows), query)
    return rows


def transform_bronze_row(bronze_row: dict) -> list[dict]:
    """
    Convenience wrapper for load.py: takes a row as read from
    bronze_raw_results (query, captured_at, raw_json already parsed to dict)
    and returns silver rows.
    """
    return transform_payload(
        payload=bronze_row["raw_json"],
        query=bronze_row["query"],
        captured_at=bronze_row["captured_at"],
    )
