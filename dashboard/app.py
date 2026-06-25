"""
dashboard/app.py

Dash app reading directly from the gold layer:
  - gold.product_dim    -> product picker (title, asin)
  - gold.price_history  -> time series for price, rank position, reviews
"""

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dcc, html
from sqlalchemy import create_engine, text

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

engine = create_engine(config.SQLALCHEMY_URL)


def get_product_options():
    query = """
        SELECT asin, title
        FROM gold.product_dim
        ORDER BY title
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    return [
        {"label": f"{row.title[:60]}..." if row.title and len(row.title) > 60 else (row.title or row.asin),
         "value": row.asin}
        for row in df.itertuples()
    ]


def get_history(asin: str) -> pd.DataFrame:
    query = """
        SELECT captured_at, price, position, reviews, rating, sponsored, query
        FROM gold.price_history
        WHERE asin = :asin
        ORDER BY captured_at
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params={"asin": asin})


app = Dash(__name__)
app.title = "Product Intelligence Dashboard"

app.layout = html.Div(
    style={"fontFamily": "Arial, sans-serif", "margin": "24px"},
    children=[
        html.H2("Amazon Product Price & Ranking Trends"),
        html.P("Pick a tracked product to see how its price and search position have moved over time."),
        dcc.Dropdown(id="product-dropdown", options=get_product_options(), placeholder="Select a product..."),
        html.Div(id="summary-stats", style={"margin": "16px 0", "fontSize": "16px"}),
        dcc.Graph(id="price-chart"),
        dcc.Graph(id="position-chart"),
        dcc.Interval(id="refresh-interval", interval=60 * 1000, n_intervals=0),  # refresh dropdown hourly-ish
    ],
)


@app.callback(Output("product-dropdown", "options"), Input("refresh-interval", "n_intervals"))
def refresh_options(_):
    return get_product_options()


@app.callback(
    Output("price-chart", "figure"),
    Output("position-chart", "figure"),
    Output("summary-stats", "children"),
    Input("product-dropdown", "value"),
)
def update_charts(asin):
    empty_fig = px.scatter(title="Select a product to see its trend")
    if not asin:
        return empty_fig, empty_fig, ""

    df = get_history(asin)
    if df.empty:
        return empty_fig, empty_fig, "No history yet for this product."

    price_fig = px.line(
        df, x="captured_at", y="price", color="query", markers=True,
        title="Price over time",
    )
    position_fig = px.line(
        df, x="captured_at", y="position", color="query", markers=True,
        title="Search rank position over time (lower = better)",
    )
    position_fig.update_yaxes(autorange="reversed")  # rank 1 at top

    latest = df.iloc[-1]
    first = df.iloc[0]
    pct_change = (
        round(100 * (latest.price - first.price) / first.price, 1)
        if first.price else None
    )
    stats = (
        f"Latest price: ${latest.price:.2f} | "
        f"Change since first tracked: {pct_change}% | "
        f"Latest rank: #{int(latest.position) if pd.notna(latest.position) else 'N/A'} | "
        f"Reviews: {int(latest.reviews) if pd.notna(latest.reviews) else 'N/A'}"
    )
    return price_fig, position_fig, stats


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=True)
