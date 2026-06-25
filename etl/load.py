"""
etl/load.py

Responsible for:
  1. Persisting silver rows (idempotent insert, dedup on UNIQUE constraint).
  2. Merging silver -> gold (product_dim upsert + price_history append).
"""

import logging
import os
from datetime import datetime, timezone

from sqlalchemy import create_engine, text

import config
from etl.transform import transform_bronze_row

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_SQL_DIR = os.path.join(os.path.dirname(__file__), "..", "warehouse")


def _load_merge_statements() -> dict:
    """
    merge_queries.sql contains multiple statements separated by numbered
    comment headers.
    """
    with open(os.path.join(_SQL_DIR, "merge_queries.sql")) as f:
        content = f.read()

    parts = content.split("-- ------------------------------------------------------------")
    statements = []
    for part in parts:
        stripped_lines = [
            line for line in part.splitlines()
            if line.strip() and not line.strip().startswith("--")
        ]
        sql = "\n".join(stripped_lines).strip()
        if sql.upper().startswith(("INSERT", "UPDATE", "DELETE")):
            statements.append(sql)
    return {
        "upsert_dim": statements[0],
        "insert_history": statements[1],
    }


def insert_silver_rows(rows: list[dict], engine) -> int:
    if not rows:
        return 0
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                INSERT INTO silver_product_snapshot (
                    asin, query, captured_at, position, title, brand, sponsored,
                    rating, reviews, price, price_per_unit, old_price,
                    is_climate_pledge_friendly, is_small_business,
                    bought_last_month_raw, link_clean, thumbnail
                )
                VALUES (
                    :asin, :query, :captured_at, :position, :title, :brand, :sponsored,
                    :rating, :reviews, :price, :price_per_unit, :old_price,
                    :is_climate_pledge_friendly, :is_small_business,
                    :bought_last_month_raw, :link_clean, :thumbnail
                )
                ON CONFLICT (asin, query, captured_at) DO NOTHING
                """
            ),
            rows,
        )
        return result.rowcount


def merge_to_gold(rows: list[dict], engine, merge_sql: dict) -> None:
    if not rows:
        return
    with engine.begin() as conn:
        for row in rows:
            conn.execute(text(merge_sql["upsert_dim"]), row)
            conn.execute(text(merge_sql["insert_history"]), row)


def fetch_unprocessed_bronze(engine, since: datetime = None) -> list[dict]:
    """
    Pull bronze rows to process. In this simple version we just process
    everything newer than `since`
    """
    since = since or datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                SELECT query, captured_at, raw_json
                FROM bronze_raw_results
                WHERE captured_at >= :since
                ORDER BY captured_at
                """
            ),
            {"since": since},
        )
        return [dict(r._mapping) for r in result]


def run_load(since: datetime = None):
    engine = create_engine(config.SQLALCHEMY_URL)
    merge_sql = _load_merge_statements()

    bronze_rows = fetch_unprocessed_bronze(engine, since=since)
    logger.info("Loaded %d bronze row(s) to process", len(bronze_rows))

    total_silver, total_gold = 0, 0
    for bronze_row in bronze_rows:
        silver_rows = transform_bronze_row(bronze_row)
        inserted = insert_silver_rows(silver_rows, engine)
        merge_to_gold(silver_rows, engine, merge_sql)
        total_silver += inserted
        total_gold += len(silver_rows)

    logger.info(
        "Load complete. %d new silver row(s), %d row(s) merged to gold.",
        total_silver, total_gold,
    )


if __name__ == "__main__":
    run_load()
