# Product Intelligence Pipeline

Tracks Amazon product listings (price, search rank, reviews) over time using
SerpAPI's `amazon` search engine, following a medallion (bronze/silver/gold)
pattern in Postgres, orchestrated by Airflow, visualized in Dash.

## Architecture

```
SerpAPI ──▶ extract.py ──▶ bronze_raw_results      (raw JSON, untouched)
                              │
                              ▼
                         transform.py               (pure functions, no DB)
                              │
                              ▼
                          load.py ──▶ silver_product_snapshot  (typed, deduped)
                              │
                              ▼
                       gold.product_dim   (latest attributes per ASIN)
                       gold.price_history (append-only time series)
                              │
                              ▼
                       dashboard/app.py (Dash) — price & rank trend charts
```

**Why split bronze/silver/gold here, specifically:**
- *Bronze* exists so a parsing bug or a SerpAPI field rename never costs you
  re-querying (and re-paying for) the API — you just re-run `transform.py`
  and `load.py` against history.
- *Silver* is one clean row per snapshot, with a `UNIQUE(asin, query,
  captured_at)` constraint so re-running load is always safe (idempotent).
- *Gold* splits into two tables for two different access patterns: a small
  dimension table (`product_dim`) for "what is this product, right now",
  and a long, append-only history table (`price_history`) for trend charts.
  Keeping these separate means the dashboard's time-series queries don't
  have to scan or repeat descriptive text columns on every row.
  
## Running on Airflow

Drop `product_pipeline_dag.py` into the DAGs folder. It expects
`etl/`, `warehouse/`, and `config.py` to be importable and the same env vars as above set on the Airflow
workers/connections.

**Why `etl/`, `warehouse/`, and `config.py` are duplicated inside `dags/`:**

Airflow only automatically adds the `dags/` folder itself to `sys.path` —
not its parent directory. Since `docker-compose.yml` mounts `./dags` as a
volume at runtime, the actual code Airflow imports has to physically live
inside `dags/`.

## Environment variables

| Var              | Purpose                                  | Default        |
|-------------------|------------------------------------------|----------------|
| `SERPAPI_KEY`     | SerpAPI auth                             | *(required)*   |
| `TRACKED_QUERIES` | Comma-separated search terms to monitor  | `Coffee, wireless earbuds`       |
| `AMAZON_DOMAIN`   | Amazon marketplace                       | `amazon.com`   |
| `PG_HOST/PORT/DB/USER/PASSWORD` | Postgres connection         | see `config.py`|
