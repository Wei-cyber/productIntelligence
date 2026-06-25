-- warehouse/merge_queries.sql
--
-- These are templates executed by etl/load.py (via SQLAlchemy `text()`),
-- not run standalone. Kept here so the merge logic is reviewable/testable
-- independent of Python.

-- ------------------------------------------------------------
-- 1. Upsert into gold.product_dim
-- ------------------------------------------------------------
-- :asin :title :brand :is_climate_pledge_friendly :is_small_business
-- :thumbnail :link_clean :captured_at

INSERT INTO gold.product_dim (
    asin, title, brand, is_climate_pledge_friendly, is_small_business,
    thumbnail, link_clean, first_seen_at, last_seen_at
)
VALUES (
    :asin, :title, :brand, :is_climate_pledge_friendly, :is_small_business,
    :thumbnail, :link_clean, :captured_at, :captured_at
)
ON CONFLICT (asin) DO UPDATE SET
    title                       = EXCLUDED.title,
    brand                       = EXCLUDED.brand,
    is_climate_pledge_friendly  = EXCLUDED.is_climate_pledge_friendly,
    is_small_business           = EXCLUDED.is_small_business,
    thumbnail                   = EXCLUDED.thumbnail,
    link_clean                  = EXCLUDED.link_clean,
    last_seen_at                = EXCLUDED.last_seen_at
WHERE gold.product_dim.last_seen_at < EXCLUDED.last_seen_at;

-- ------------------------------------------------------------
-- 2. Insert into gold.price_history.
-- ------------------------------------------------------------
-- :asin :query :captured_at :position :price :price_per_unit
-- :rating :reviews :sponsored

INSERT INTO gold.price_history (
    asin, query, captured_at, position, price, price_per_unit,
    rating, reviews, sponsored
)
VALUES (
    :asin, :query, :captured_at, :position, :price, :price_per_unit,
    :rating, :reviews, :sponsored
)
ON CONFLICT (asin, query, captured_at) DO NOTHING;

