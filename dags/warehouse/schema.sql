-- warehouse/schema.sql
--
-- Three layers, same Postgres database
--
--   bronze_raw_results   -> exact API responses, never mutated
--   silver_product_snapshot -> one cleaned row per (asin, query, captured_at)
--   gold.product_dim / gold.price_history -> the "current truth" + time series

-- ============================================================
-- BRONZE
-- ============================================================
CREATE TABLE IF NOT EXISTS bronze_raw_results (
    id              BIGSERIAL PRIMARY KEY,
    query           TEXT        NOT NULL,
    captured_at     TIMESTAMPTZ NOT NULL,
    raw_json        JSONB       NOT NULL,
    inserted_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bronze_captured_at ON bronze_raw_results (captured_at);
CREATE INDEX IF NOT EXISTS idx_bronze_query ON bronze_raw_results (query);

-- ============================================================
-- SILVER
-- ============================================================
CREATE TABLE IF NOT EXISTS silver_product_snapshot (
    id                          BIGSERIAL PRIMARY KEY,
    asin                        TEXT        NOT NULL,
    query                       TEXT        NOT NULL,
    captured_at                 TIMESTAMPTZ NOT NULL,
    position                    INTEGER,
    title                       TEXT,
    brand                       TEXT,
    sponsored                   BOOLEAN     DEFAULT FALSE,
    rating                      NUMERIC(3,2),
    reviews                     INTEGER,
    price                       NUMERIC(10,2),
    price_per_unit              NUMERIC(10,2),
    old_price                   NUMERIC(10,2),
    is_climate_pledge_friendly  BOOLEAN     DEFAULT FALSE,
    is_small_business           BOOLEAN     DEFAULT FALSE,
    bought_last_month_raw       TEXT,
    link_clean                  TEXT,
    thumbnail                   TEXT,
    inserted_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- One snapshot per product per query per capture run.
    UNIQUE (asin, query, captured_at)
);

CREATE INDEX IF NOT EXISTS idx_silver_asin ON silver_product_snapshot (asin);
CREATE INDEX IF NOT EXISTS idx_silver_captured_at ON silver_product_snapshot (captured_at);

-- ============================================================
-- GOLD
-- ============================================================
CREATE SCHEMA IF NOT EXISTS gold;

-- product_dim: latest known attributes per product. Slowly-changing,
CREATE TABLE IF NOT EXISTS gold.product_dim (
    asin                        TEXT PRIMARY KEY,
    title                       TEXT,
    brand                       TEXT,
    is_climate_pledge_friendly  BOOLEAN,
    is_small_business           BOOLEAN,
    thumbnail                   TEXT,
    link_clean                  TEXT,
    first_seen_at               TIMESTAMPTZ NOT NULL,
    last_seen_at                TIMESTAMPTZ NOT NULL
);

-- price_history: the actual time series we analyze trends from.
-- Append-only, deduped on (asin, query, captured_at).
CREATE TABLE IF NOT EXISTS gold.price_history (
    asin            TEXT        NOT NULL,
    query           TEXT        NOT NULL,
    captured_at     TIMESTAMPTZ NOT NULL,
    position        INTEGER,
    price           NUMERIC(10,2),
    price_per_unit  NUMERIC(10,2),
    rating          NUMERIC(3,2),
    reviews         INTEGER,
    sponsored       BOOLEAN,
    PRIMARY KEY (asin, query, captured_at)
);

CREATE INDEX IF NOT EXISTS idx_gold_price_history_asin ON gold.price_history (asin);
CREATE INDEX IF NOT EXISTS idx_gold_price_history_query ON gold.price_history (query);
