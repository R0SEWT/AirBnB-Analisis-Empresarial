from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from src.transformations.common import ensure_parent


def market_series(listings: pd.DataFrame) -> pd.Series:
    return listings["_source_file"].astype("string").str.replace(".csv.gz", "", regex=False).fillna("Unknown")


def normalize_bool(series: pd.Series) -> pd.Series:
    return series.map(lambda value: bool(value) if pd.notna(value) else False)


def money(value: float | int | None) -> float:
    if pd.isna(value):
        return 0.0
    return round(float(value), 2)


def pct(value: float | int | None) -> float:
    if pd.isna(value):
        return 0.0
    return round(float(value) * 100, 2)


def average(series: pd.Series) -> float:
    return money(series.dropna().mean())


def build_summary_rows(listings: pd.DataFrame) -> list[dict]:
    rows = []
    markets = ["All"] + sorted(listings["market"].dropna().unique().tolist())
    room_types = ["All"] + sorted(listings["room_type"].dropna().unique().tolist())

    for market in markets:
        for room_type in room_types:
            frame = listings
            if market != "All":
                frame = frame[frame["market"] == market]
            if room_type != "All":
                frame = frame[frame["room_type"] == room_type]
            if frame.empty:
                continue
            rows.append(
                {
                    "market": market,
                    "room_type": room_type,
                    "listings": int(len(frame)),
                    "hosts": int(frame["host_id"].nunique()),
                    "avg_price": average(frame["price"]),
                    "avg_rating": average(frame["review_scores_rating"]),
                    "avg_availability": average(frame["availability_365"]),
                    "superhost_rate": pct(frame["host_is_superhost"].fillna(False).astype(bool).mean()),
                    "identity_verified_rate": pct(frame["host_identity_verified"].fillna(False).astype(bool).mean()),
                    "reviewed_listing_rate": pct((frame["number_of_reviews"].fillna(0) > 0).mean()),
                    "reviews_declared": int(frame["number_of_reviews"].fillna(0).sum()),
                }
            )
    return rows


def grouped_chart(listings: pd.DataFrame, group_column: str, value_column: str = "listing_id", top: int = 12) -> list[dict]:
    grouped = (
        listings.groupby(group_column, dropna=False)
        .agg(listings=(value_column, "count"), avg_price=("price", "mean"), avg_rating=("review_scores_rating", "mean"))
        .reset_index()
        .sort_values("listings", ascending=False)
        .head(top)
    )
    return [
        {
            "label": str(row[group_column] if pd.notna(row[group_column]) else "Unknown"),
            "listings": int(row["listings"]),
            "avg_price": money(row["avg_price"]),
            "avg_rating": money(row["avg_rating"]),
        }
        for _, row in grouped.iterrows()
    ]


def availability_buckets(listings: pd.DataFrame) -> list[dict]:
    buckets = pd.cut(
        listings["availability_365"],
        bins=[-1, 0, 90, 180, 270, 365],
        labels=["0", "1-90", "91-180", "181-270", "271-365"],
    )
    counts = buckets.value_counts(sort=False)
    return [{"label": str(index), "listings": int(value)} for index, value in counts.items()]


def price_buckets(listings: pd.DataFrame) -> list[dict]:
    prices = listings["price"].dropna()
    if prices.empty:
        return []
    capped = prices.clip(upper=prices.quantile(0.98))
    buckets = pd.cut(capped, bins=8)
    counts = buckets.value_counts(sort=False)
    return [{"label": f"{interval.left:.0f}-{interval.right:.0f}", "listings": int(value)} for interval, value in counts.items()]


def build_filter_breakdowns(listings: pd.DataFrame) -> dict:
    breakdowns = {"room_type": [], "neighbourhood": [], "availability": [], "price": []}
    markets = ["All"] + sorted(listings["market"].dropna().unique().tolist())
    room_types = ["All"] + sorted(listings["room_type"].dropna().unique().tolist())

    for market in markets:
        market_frame = listings if market == "All" else listings[listings["market"] == market]
        for row in grouped_chart(market_frame, "room_type", top=8):
            breakdowns["room_type"].append({"market": market, "room_type": "All", **row})

        for room_type in room_types:
            frame = market_frame if room_type == "All" else market_frame[market_frame["room_type"] == room_type]
            if frame.empty:
                continue
            for row in grouped_chart(frame, "neighbourhood_cleansed", top=14):
                breakdowns["neighbourhood"].append({"market": market, "room_type": room_type, **row})
            for row in availability_buckets(frame):
                breakdowns["availability"].append({"market": market, "room_type": room_type, **row})
            for row in price_buckets(frame):
                breakdowns["price"].append({"market": market, "room_type": room_type, **row})

    return breakdowns


def review_trend(star_dir: Path, listings: pd.DataFrame, batch_size: int = 250_000) -> list[dict]:
    fact_path = star_dir / "fact_reviews.parquet"
    if not fact_path.exists():
        return []

    listing_market = listings[["listing_id", "market"]].dropna(subset=["listing_id"])
    partials = []
    parquet_file = pq.ParquetFile(fact_path)
    for batch in parquet_file.iter_batches(columns=["listing_id", "review_date_key", "comment_length"], batch_size=batch_size):
        reviews = batch.to_pandas()
        reviews = reviews.merge(listing_market, on="listing_id", how="left")
        reviews["date"] = pd.to_datetime(reviews["review_date_key"].astype("string"), format="%Y%m%d", errors="coerce")
        reviews["year_month"] = reviews["date"].dt.strftime("%Y-%m")
        grouped = (
            reviews.groupby(["market", "year_month"], dropna=False)
            .agg(reviews=("listing_id", "count"), avg_comment_length=("comment_length", "mean"))
            .reset_index()
        )
        partials.append(grouped)

    if not partials:
        return []

    trend = pd.concat(partials, ignore_index=True)
    trend = (
        trend.groupby(["market", "year_month"], dropna=False)
        .agg(reviews=("reviews", "sum"), avg_comment_length=("avg_comment_length", "mean"))
        .reset_index()
        .sort_values("year_month")
    )
    recent_months = trend["year_month"].dropna().drop_duplicates().sort_values().tail(36)
    trend = trend[trend["year_month"].isin(recent_months)]
    all_market = (
        trend.groupby("year_month", dropna=False)
        .agg(reviews=("reviews", "sum"), avg_comment_length=("avg_comment_length", "mean"))
        .reset_index()
    )
    all_market["market"] = "All"
    trend = pd.concat([trend, all_market], ignore_index=True).sort_values(["market", "year_month"])

    return [
        {
            "market": str(row["market"] if pd.notna(row["market"]) else "Unknown"),
            "year_month": str(row["year_month"]),
            "reviews": int(row["reviews"]),
            "avg_comment_length": money(row["avg_comment_length"]),
        }
        for _, row in trend.iterrows()
    ]


def build_dashboard_payload(
    gold_listings_path: Path = Path("data/gold/listings.parquet"),
    star_dir: Path = Path("data/gold/star"),
) -> dict:
    listings = pd.read_parquet(gold_listings_path)
    listings["market"] = market_series(listings)
    listings["host_is_superhost"] = normalize_bool(listings["host_is_superhost"])
    listings["host_identity_verified"] = normalize_bool(listings["host_identity_verified"])

    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "sources": {
            "gold_listings": str(gold_listings_path),
            "star_schema": str(star_dir),
        },
        "filters": {
            "markets": ["All"] + sorted(listings["market"].dropna().unique().tolist()),
            "room_types": ["All"] + sorted(listings["room_type"].dropna().unique().tolist()),
        },
        "summary": build_summary_rows(listings),
        "charts": {
            "breakdowns": build_filter_breakdowns(listings),
            "reviews_trend": review_trend(star_dir, listings),
            "top_reviewed_listings": [
                {
                    "name": str(row["name"])[:80],
                    "market": str(row["market"]),
                    "room_type": str(row["room_type"]),
                    "reviews": int(row["number_of_reviews"]),
                    "rating": money(row["review_scores_rating"]),
                }
                for _, row in listings.sort_values("number_of_reviews", ascending=False).head(12).iterrows()
            ],
        },
    }


def render_dashboard_html(payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=True)
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Airbnb Marketplace Quality Dashboard</title>
  <style>
    :root {{
      --bg: #f5f6f2;
      --panel: #ffffff;
      --ink: #172026;
      --muted: #64717a;
      --line: #d9dfd8;
      --accent: #d9485f;
      --blue: #2f6f9f;
      --green: #3d7c59;
      --gold: #b4891d;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, Segoe UI, Arial, sans-serif;
    }}
    header {{
      background: #fff;
      border-bottom: 1px solid var(--line);
      padding: 20px 28px 16px;
      display: grid;
      gap: 14px;
    }}
    h1 {{ margin: 0; font-size: 28px; letter-spacing: 0; }}
    .subtitle {{ margin: 0; color: var(--muted); max-width: 920px; line-height: 1.45; }}
    .filters {{
      display: grid;
      grid-template-columns: repeat(2, minmax(180px, 280px));
      gap: 12px;
    }}
    label {{ display: grid; gap: 6px; color: var(--muted); font-size: 13px; font-weight: 700; }}
    select {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      padding: 10px 12px;
      font-size: 14px;
    }}
    main {{ padding: 22px 28px 34px; display: grid; gap: 18px; }}
    .kpis {{ display: grid; grid-template-columns: repeat(6, minmax(140px, 1fr)); gap: 12px; }}
    .card, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .card span {{ display: block; color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }}
    .card strong {{ display: block; margin-top: 8px; font-size: 28px; line-height: 1; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(280px, 1fr)); gap: 18px; }}
    h2 {{ margin: 0 0 14px; font-size: 18px; letter-spacing: 0; }}
    .bar-row {{ display: grid; grid-template-columns: minmax(110px, 190px) 1fr 80px; gap: 10px; align-items: center; margin: 9px 0; }}
    .label {{ overflow: hidden; white-space: nowrap; text-overflow: ellipsis; color: var(--ink); }}
    .track {{ height: 12px; background: #ecf0ed; border-radius: 999px; overflow: hidden; }}
    .bar {{ height: 100%; background: var(--blue); border-radius: 999px; }}
    .value {{ text-align: right; color: var(--muted); font-variant-numeric: tabular-nums; }}
    .trend {{ width: 100%; height: 260px; }}
    .table {{ width: 100%; border-collapse: collapse; }}
    .table th, .table td {{ border-bottom: 1px solid var(--line); padding: 9px 6px; text-align: left; font-size: 14px; }}
    .table th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    footer {{ color: var(--muted); padding: 0 28px 24px; font-size: 13px; }}
    @media (max-width: 1100px) {{
      .kpis {{ grid-template-columns: repeat(3, 1fr); }}
      .grid {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 680px) {{
      header, main, footer {{ padding-left: 16px; padding-right: 16px; }}
      .kpis, .filters {{ grid-template-columns: 1fr; }}
      .bar-row {{ grid-template-columns: 1fr; gap: 5px; }}
      .value {{ text-align: left; }}
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Airbnb Marketplace Quality Dashboard</h1>
      <p class="subtitle">Vista operacional basada en modelo estrella: dimensiones de listing, host, ubicacion y fecha; hechos de snapshots de listings y reviews.</p>
    </div>
    <div class="filters">
      <label>Mercado<select id="marketFilter"></select></label>
      <label>Tipo de habitacion<select id="roomFilter"></select></label>
    </div>
  </header>
  <main>
    <section class="kpis" id="kpis"></section>
    <section class="grid">
      <div class="panel"><h2>Listings por tipo</h2><div id="roomChart"></div></div>
      <div class="panel"><h2>Zonas con mayor oferta</h2><div id="neighbourhoodChart"></div></div>
      <div class="panel"><h2>Disponibilidad anual</h2><div id="availabilityChart"></div></div>
      <div class="panel"><h2>Distribucion de precios</h2><div id="priceChart"></div></div>
    </section>
    <section class="panel">
      <h2>Tendencia mensual de reviews</h2>
      <svg class="trend" id="trendChart" role="img" aria-label="Reviews por mes"></svg>
    </section>
    <section class="panel">
      <h2>Listings con mayor volumen de reviews</h2>
      <table class="table" id="topListings"></table>
    </section>
  </main>
  <footer id="footer"></footer>
  <script id="dashboard-data" type="application/json">{data}</script>
  <script>
    const payload = JSON.parse(document.getElementById('dashboard-data').textContent);
    const marketFilter = document.getElementById('marketFilter');
    const roomFilter = document.getElementById('roomFilter');

    function optionList(select, values) {{
      select.innerHTML = values.map(value => `<option value="${{value}}">${{value}}</option>`).join('');
    }}

    function number(value) {{
      return new Intl.NumberFormat('en-US').format(Math.round(value || 0));
    }}

    function decimal(value) {{
      return Number(value || 0).toFixed(2);
    }}

    function activeSummary() {{
      const market = marketFilter.value || 'All';
      const room = roomFilter.value || 'All';
      return payload.summary.find(row => row.market === market && row.room_type === room)
        || payload.summary.find(row => row.market === market && row.room_type === 'All')
        || payload.summary.find(row => row.market === 'All' && row.room_type === room)
        || payload.summary.find(row => row.market === 'All' && row.room_type === 'All');
    }}

    function renderKpis(row) {{
      const kpis = [
        ['Listings', number(row.listings)],
        ['Hosts', number(row.hosts)],
        ['Precio promedio', `$${{decimal(row.avg_price)}}`],
        ['Rating promedio', decimal(row.avg_rating)],
        ['Superhost', `${{decimal(row.superhost_rate)}}%`],
        ['Identidad verificada', `${{decimal(row.identity_verified_rate)}}%`],
      ];
      document.getElementById('kpis').innerHTML = kpis.map(([label, value]) => `<div class="card"><span>${{label}}</span><strong>${{value}}</strong></div>`).join('');
    }}

    function breakdownRows(name) {{
      const market = marketFilter.value || 'All';
      const room = roomFilter.value || 'All';
      const rows = payload.charts.breakdowns[name] || [];
      let filtered = rows.filter(row => row.market === market && row.room_type === room);
      if (!filtered.length) filtered = rows.filter(row => row.market === market && row.room_type === 'All');
      if (!filtered.length) filtered = rows.filter(row => row.market === 'All' && row.room_type === room);
      if (!filtered.length) filtered = rows.filter(row => row.market === 'All' && row.room_type === 'All');
      return filtered;
    }}

    function renderBars(id, rows, valueKey = 'listings') {{
      const max = Math.max(...rows.map(row => row[valueKey] || 0), 1);
      document.getElementById(id).innerHTML = rows.map(row => {{
        const value = row[valueKey] || 0;
        const width = Math.max(2, (value / max) * 100);
        return `<div class="bar-row"><div class="label" title="${{row.label}}">${{row.label}}</div><div class="track"><div class="bar" style="width:${{width}}%"></div></div><div class="value">${{number(value)}}</div></div>`;
      }}).join('');
    }}

    function renderTrend() {{
      const market = marketFilter.value || 'All';
      const rows = payload.charts.reviews_trend.filter(row => row.market === market);
      const svg = document.getElementById('trendChart');
      const width = svg.clientWidth || 900;
      const height = 260;
      svg.setAttribute('viewBox', `0 0 ${{width}} ${{height}}`);
      if (!rows.length) {{
        svg.innerHTML = '<text x="16" y="36" fill="#64717a">Sin reviews para el filtro seleccionado.</text>';
        return;
      }}
      const max = Math.max(...rows.map(row => row.reviews), 1);
      const points = rows.map((row, index) => {{
        const x = 36 + (index / Math.max(rows.length - 1, 1)) * (width - 72);
        const y = height - 34 - (row.reviews / max) * (height - 70);
        return [x, y, row];
      }});
      const line = points.map(point => `${{point[0]}},${{point[1]}}`).join(' ');
      const circles = points.map(([x, y, row]) => `<circle cx="${{x}}" cy="${{y}}" r="3" fill="#d9485f"><title>${{row.year_month}}: ${{number(row.reviews)}} reviews</title></circle>`).join('');
      svg.innerHTML = `<polyline fill="none" stroke="#d9485f" stroke-width="3" points="${{line}}"></polyline>${{circles}}<text x="36" y="20" fill="#64717a">Ultimos 36 meses</text>`;
    }}

    function renderTopListings() {{
      const market = marketFilter.value || 'All';
      const room = roomFilter.value || 'All';
      let rows = payload.charts.top_reviewed_listings.filter(row => (market === 'All' || row.market === market) && (room === 'All' || row.room_type === room));
      if (!rows.length) rows = payload.charts.top_reviewed_listings;
      document.getElementById('topListings').innerHTML = `<thead><tr><th>Listing</th><th>Mercado</th><th>Tipo</th><th>Reviews</th><th>Rating</th></tr></thead><tbody>${{rows.map(row => `<tr><td>${{row.name}}</td><td>${{row.market}}</td><td>${{row.room_type}}</td><td>${{number(row.reviews)}}</td><td>${{decimal(row.rating)}}</td></tr>`).join('')}}</tbody>`;
    }}

    function render() {{
      renderKpis(activeSummary());
      renderBars('roomChart', breakdownRows('room_type'));
      renderBars('neighbourhoodChart', breakdownRows('neighbourhood'));
      renderBars('availabilityChart', breakdownRows('availability'));
      renderBars('priceChart', breakdownRows('price'));
      renderTrend();
      renderTopListings();
      document.getElementById('footer').textContent = `Generado: ${{payload.generated_at_utc}} | Fuente: ${{payload.sources.star_schema}}`;
    }}

    optionList(marketFilter, payload.filters.markets);
    optionList(roomFilter, payload.filters.room_types);
    marketFilter.addEventListener('change', render);
    roomFilter.addEventListener('change', render);
    window.addEventListener('resize', renderTrend);
    render();
  </script>
</body>
</html>
"""


def build_dashboard(
    gold_listings_path: Path = Path("data/gold/listings.parquet"),
    star_dir: Path = Path("data/gold/star"),
    output_path: Path = Path("dashboards/airbnb_quality_dashboard.html"),
) -> dict:
    payload = build_dashboard_payload(gold_listings_path=gold_listings_path, star_dir=star_dir)
    ensure_parent(output_path)
    output_path.write_text(render_dashboard_html(payload), encoding="utf-8")
    return {"output": str(output_path), "generated_at_utc": payload["generated_at_utc"]}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a static Airbnb dashboard from the star schema.")
    parser.add_argument("--gold-listings", type=Path, default=Path("data/gold/listings.parquet"))
    parser.add_argument("--star-dir", type=Path, default=Path("data/gold/star"))
    parser.add_argument("--output", type=Path, default=Path("dashboards/airbnb_quality_dashboard.html"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_dashboard(gold_listings_path=args.gold_listings, star_dir=args.star_dir, output_path=args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
