from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from src.transformations.common import ensure_parent


def money(value: float | int | None) -> float:
    if pd.isna(value):
        return 0.0
    return round(float(value), 2)


def pct(value: float | int | None) -> float:
    if pd.isna(value):
        return 0.0
    return round(float(value) * 100, 2)


def build_payload(analytics_dir: Path = Path("data/gold/analytics")) -> dict:
    scores = pd.read_parquet(analytics_dir / "listing_trust_risk.parquet")
    market_summary = pd.read_parquet(analytics_dir / "market_trust_risk_summary.parquet")
    segment_summary = pd.read_parquet(analytics_dir / "risk_segment_summary.parquet")

    high_risk = scores[scores["risk_segment"].isin(["High", "Critical"])]
    driver_summary = (
        scores.groupby("primary_risk_driver", dropna=False)
        .agg(listings=("listing_id", "count"), avg_risk_score=("risk_score", "mean"))
        .reset_index()
        .sort_values("listings", ascending=False)
    )

    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "sources": {"analytics_dir": str(analytics_dir)},
        "kpis": {
            "listings": int(len(scores)),
            "avg_risk_score": money(scores["risk_score"].mean()),
            "avg_trust_score": money(scores["trust_score"].mean()),
            "high_risk_listings": int(len(high_risk)),
            "high_risk_rate": pct(len(high_risk) / len(scores) if len(scores) else 0),
            "critical_risk_listings": int((scores["risk_segment"] == "Critical").sum()),
        },
        "segments": [
            {
                "risk_segment": str(row["risk_segment"]),
                "listings": int(row["listings"]),
                "avg_risk_score": money(row["avg_risk_score"]),
                "avg_trust_score": money(row["avg_trust_score"]),
            }
            for _, row in segment_summary.iterrows()
        ],
        "markets": [
            {
                "market": str(row["market"]),
                "listings": int(row["listings"]),
                "avg_risk_score": money(row["avg_risk_score"]),
                "avg_trust_score": money(row["avg_trust_score"]),
                "high_risk_rate": pct(row["high_risk_rate"]),
                "critical_risk_rate": pct(row["critical_risk_rate"]),
            }
            for _, row in market_summary.head(12).iterrows()
        ],
        "drivers": [
            {
                "driver": str(row["primary_risk_driver"]),
                "listings": int(row["listings"]),
                "avg_risk_score": money(row["avg_risk_score"]),
            }
            for _, row in driver_summary.iterrows()
        ],
        "top_risk_listings": [
            {
                "listing_id": int(row["listing_id"]),
                "name": str(row["name"])[:80],
                "market": str(row["market"]),
                "risk_score": money(row["risk_score"]),
                "trust_score": money(row["trust_score"]),
                "risk_segment": str(row["risk_segment"]),
                "driver": str(row["primary_risk_driver"]),
                "action": str(row["recommended_action"]),
            }
            for _, row in scores.head(20).iterrows()
        ],
    }


def render_dashboard(payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=True)
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Airbnb Trust & Risk Dashboard</title>
  <style>
    :root {{
      --bg: #f6f7f3;
      --panel: #fff;
      --ink: #172026;
      --muted: #5f6d75;
      --line: #d8ded6;
      --risk: #d9485f;
      --trust: #2f6f9f;
      --warn: #b4891d;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, Segoe UI, Arial, sans-serif;
    }}
    header {{
      padding: 24px 30px 18px;
      background: #fff;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{ margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }}
    header p {{ margin: 0; color: var(--muted); max-width: 980px; line-height: 1.45; }}
    main {{ padding: 22px 30px 36px; display: grid; gap: 18px; }}
    .kpis {{ display: grid; grid-template-columns: repeat(6, minmax(140px, 1fr)); gap: 12px; }}
    .card, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .card span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .card strong {{ display: block; margin-top: 8px; font-size: 28px; line-height: 1; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(280px, 1fr)); gap: 18px; }}
    h2 {{ margin: 0 0 14px; font-size: 18px; letter-spacing: 0; }}
    .bar-row {{ display: grid; grid-template-columns: minmax(120px, 220px) 1fr 86px; gap: 10px; align-items: center; margin: 9px 0; }}
    .label {{ overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }}
    .track {{ height: 12px; background: #edf0ed; border-radius: 999px; overflow: hidden; }}
    .bar {{ height: 100%; background: var(--trust); border-radius: 999px; }}
    .bar.risk {{ background: var(--risk); }}
    .value {{ text-align: right; color: var(--muted); font-variant-numeric: tabular-nums; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 9px 7px; text-align: left; font-size: 14px; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    footer {{ color: var(--muted); padding: 0 30px 24px; font-size: 13px; }}
    @media (max-width: 1100px) {{
      .kpis {{ grid-template-columns: repeat(3, 1fr); }}
      .grid {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 700px) {{
      header, main, footer {{ padding-left: 16px; padding-right: 16px; }}
      .kpis {{ grid-template-columns: 1fr; }}
      .bar-row {{ grid-template-columns: 1fr; gap: 5px; }}
      .value {{ text-align: left; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Airbnb Trust & Risk Dashboard</h1>
    <p>Vista dashboard-ready basada en un score explicable de confianza y riesgo. El objetivo es priorizar intervenciones operativas; no representa un modelo predictivo validado.</p>
  </header>
  <main>
    <section class="kpis" id="kpis"></section>
    <section class="grid">
      <div class="panel"><h2>Distribucion por segmento</h2><div id="segments"></div></div>
      <div class="panel"><h2>Principales drivers de riesgo</h2><div id="drivers"></div></div>
      <div class="panel"><h2>Mercados con mayor riesgo promedio</h2><div id="markets"></div></div>
      <div class="panel"><h2>Acciones recomendadas</h2><p id="actions"></p></div>
    </section>
    <section class="panel">
      <h2>Listings priorizados por riesgo</h2>
      <table id="topRisk"></table>
    </section>
  </main>
  <footer id="footer"></footer>
  <script id="dashboard-data" type="application/json">{data}</script>
  <script>
    const payload = JSON.parse(document.getElementById('dashboard-data').textContent);
    const fmt = new Intl.NumberFormat('en-US');
    const pct = value => `${{Number(value || 0).toFixed(2)}}%`;
    const num = value => fmt.format(Math.round(value || 0));
    const dec = value => Number(value || 0).toFixed(2);

    function renderKpis() {{
      const k = payload.kpis;
      const rows = [
        ['Listings', num(k.listings)],
        ['Risk score prom.', dec(k.avg_risk_score)],
        ['Trust score prom.', dec(k.avg_trust_score)],
        ['High + Critical', num(k.high_risk_listings)],
        ['Tasa alto riesgo', pct(k.high_risk_rate)],
        ['Critical', num(k.critical_risk_listings)],
      ];
      document.getElementById('kpis').innerHTML = rows.map(([label, value]) => `<div class="card"><span>${{label}}</span><strong>${{value}}</strong></div>`).join('');
    }}

    function bars(id, rows, labelKey, valueKey, cls = '') {{
      const max = Math.max(...rows.map(row => row[valueKey] || 0), 1);
      document.getElementById(id).innerHTML = rows.map(row => {{
        const value = row[valueKey] || 0;
        const width = Math.max(2, value / max * 100);
        return `<div class="bar-row"><div class="label" title="${{row[labelKey]}}">${{row[labelKey]}}</div><div class="track"><div class="bar ${{cls}}" style="width:${{width}}%"></div></div><div class="value">${{num(value)}}</div></div>`;
      }}).join('');
    }}

    function renderTable() {{
      const header = '<thead><tr><th>Listing</th><th>Mercado</th><th>Riesgo</th><th>Confianza</th><th>Driver</th><th>Accion</th></tr></thead>';
      const body = payload.top_risk_listings.map(row => `<tr><td>${{row.name}}<br><span>#${{row.listing_id}}</span></td><td>${{row.market}}</td><td>${{dec(row.risk_score)}}<br>${{row.risk_segment}}</td><td>${{dec(row.trust_score)}}</td><td>${{row.driver}}</td><td>${{row.action}}</td></tr>`).join('');
      document.getElementById('topRisk').innerHTML = `${{header}}<tbody>${{body}}</tbody>`;
    }}

    function renderActions() {{
      const actions = payload.top_risk_listings.slice(0, 5).map(row => row.action);
      const unique = [...new Set(actions)];
      document.getElementById('actions').textContent = unique.join(' | ');
    }}

    renderKpis();
    bars('segments', payload.segments, 'risk_segment', 'listings', 'risk');
    bars('drivers', payload.drivers, 'driver', 'listings', 'risk');
    bars('markets', payload.markets, 'market', 'avg_risk_score', 'risk');
    renderActions();
    renderTable();
    document.getElementById('footer').textContent = `Generado: ${{payload.generated_at_utc}} | Fuente: ${{payload.sources.analytics_dir}}`;
  </script>
</body>
</html>
"""


def build_dashboard(
    analytics_dir: Path = Path("data/gold/analytics"),
    output_path: Path = Path("dashboards/trust_risk_dashboard.html"),
) -> dict:
    payload = build_payload(analytics_dir=analytics_dir)
    ensure_parent(output_path)
    output_path.write_text(render_dashboard(payload), encoding="utf-8")
    return {"output": str(output_path), "generated_at_utc": payload["generated_at_utc"]}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a trust and risk dashboard from analytics marts.")
    parser.add_argument("--analytics-dir", type=Path, default=Path("data/gold/analytics"))
    parser.add_argument("--output", type=Path, default=Path("dashboards/trust_risk_dashboard.html"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_dashboard(analytics_dir=args.analytics_dir, output_path=args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

