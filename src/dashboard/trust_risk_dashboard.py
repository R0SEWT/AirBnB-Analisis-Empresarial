from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from src.transformations.common import ensure_parent


def number(value: float | int | None) -> float:
    if pd.isna(value):
        return 0.0
    return round(float(value), 2)


def percent_from_ratio(value: float | int | None) -> float:
    if pd.isna(value):
        return 0.0
    return round(float(value) * 100, 2)


def percent_from_count(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def records(frame: pd.DataFrame) -> list[dict]:
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def build_funnel(scores: pd.DataFrame) -> list[dict]:
    total = len(scores)
    high = int(scores["risk_segment"].isin(["High", "Critical"]).sum())
    critical = int((scores["risk_segment"] == "Critical").sum())
    return [
        {"stage": "Listings nuevos / activos", "listings": total},
        {"stage": "Listings evaluados", "listings": total},
        {"stage": "Alto riesgo", "listings": high},
        {"stage": "Revision manual sugerida", "listings": high},
        {"stage": "Bloqueo o hold preventivo", "listings": critical},
    ]


def build_driver_matrix(scores: pd.DataFrame) -> list[dict]:
    matrix = (
        scores.groupby(["dispute_cause_proxy", "primary_risk_driver"], dropna=False)
        .agg(
            listings=("listing_id", "count"),
            avg_risk_score=("risk_score", "mean"),
            high_risk_listings=("risk_segment", lambda values: values.isin(["High", "Critical"]).sum()),
        )
        .reset_index()
    )
    matrix["high_risk_rate"] = matrix["high_risk_listings"] / matrix["listings"]
    matrix = matrix.sort_values(["high_risk_listings", "avg_risk_score"], ascending=False)
    return [
        {
            "cause": str(row["dispute_cause_proxy"]),
            "driver": str(row["primary_risk_driver"]),
            "listings": int(row["listings"]),
            "high_risk_listings": int(row["high_risk_listings"]),
            "high_risk_rate": percent_from_ratio(row["high_risk_rate"]),
            "avg_risk_score": number(row["avg_risk_score"]),
        }
        for _, row in matrix.iterrows()
    ]


def build_temporal_proxy(scores: pd.DataFrame) -> list[dict]:
    dated = scores.dropna(subset=["last_observed_review_date"]).copy()
    if dated.empty:
        return []
    dated["year_month"] = pd.to_datetime(dated["last_observed_review_date"]).dt.strftime("%Y-%m")
    trend = (
        dated.groupby("year_month", dropna=False)
        .agg(
            reviewed_listings=("listing_id", "count"),
            high_risk_listings=("risk_segment", lambda values: values.isin(["High", "Critical"]).sum()),
            avg_risk_score=("risk_score", "mean"),
        )
        .reset_index()
        .sort_values("year_month")
        .tail(36)
    )
    return [
        {
            "year_month": str(row["year_month"]),
            "reviewed_listings": int(row["reviewed_listings"]),
            "high_risk_listings": int(row["high_risk_listings"]),
            "avg_risk_score": number(row["avg_risk_score"]),
        }
        for _, row in trend.iterrows()
    ]


def build_segment_ranking(scores: pd.DataFrame) -> list[dict]:
    frame = (
        scores.groupby(["country", "market_label", "room_type", "listing_lifecycle_stage"], dropna=False)
        .agg(
            listings=("listing_id", "count"),
            avg_risk_score=("risk_score", "mean"),
            high_risk_listings=("risk_segment", lambda values: values.isin(["High", "Critical"]).sum()),
            avg_price=("price", "mean"),
        )
        .reset_index()
    )
    frame = frame[frame["listings"] >= 20].copy()
    frame["high_risk_rate"] = frame["high_risk_listings"] / frame["listings"]
    frame = frame.sort_values(["high_risk_rate", "avg_risk_score"], ascending=False).head(15)
    return [
        {
            "segment": f"{row['country']} | {row['market_label']} | {row['room_type']} | {row['listing_lifecycle_stage']}",
            "listings": int(row["listings"]),
            "avg_risk_score": number(row["avg_risk_score"]),
            "high_risk_rate": percent_from_ratio(row["high_risk_rate"]),
            "avg_price": number(row["avg_price"]),
        }
        for _, row in frame.iterrows()
    ]


def build_payload(analytics_dir: Path = Path("data/gold/analytics")) -> dict:
    scores = pd.read_parquet(analytics_dir / "listing_trust_risk.parquet")
    market_summary = pd.read_parquet(analytics_dir / "market_trust_risk_summary.parquet")
    segment_summary = pd.read_parquet(analytics_dir / "risk_segment_summary.parquet")

    high_risk = scores[scores["risk_segment"].isin(["High", "Critical"])]
    critical = scores[scores["risk_segment"] == "Critical"]
    market_summary = market_summary.sort_values(["high_risk_rate", "avg_risk_score"], ascending=False)

    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "sources": {"analytics_dir": str(analytics_dir)},
        "objective": (
            "Monitorear la calidad y el riesgo de listings antes y despues de su primera reserva, "
            "identificar mercados y tipos de propiedades con mayor probabilidad de disputas graves, "
            "y apoyar decisiones de Trust & Safety, soporte, compliance y experiencia."
        ),
        "users": [
            "Lider de Ciencia de Datos",
            "Equipo de Trust & Safety",
            "Operaciones por mercado",
            "Equipo de Producto",
            "Legal / Compliance",
        ],
        "kpis": {
            "listings": int(len(scores)),
            "high_risk_listings": int(len(high_risk)),
            "high_risk_rate": percent_from_count(len(high_risk), len(scores)),
            "critical_risk_listings": int(len(critical)),
            "avg_risk_score": number(scores["risk_score"].mean()),
            "avg_trust_score": number(scores["trust_score"].mean()),
        },
        "model_kpis": [
            {"indicator": "Precision del modelo", "value": "Pendiente", "target": ">= 85%", "source": "Requiere etiquetas de disputa grave"},
            {"indicator": "Tasa de disputas graves", "value": "Pendiente", "target": "-20% vs linea base 2S-2025", "source": "Requiere reservas y disputas"},
            {"indicator": "Tiempo de resolucion", "value": "Pendiente", "target": "Reducir horas/dias promedio", "source": "Requiere sistema de soporte"},
            {"indicator": "Escalamiento humano", "value": "Pendiente", "target": "Control operativo", "source": "Requiere logs IA + soporte"},
            {"indicator": "Falsos positivos", "value": "Pendiente", "target": "Minimizar impacto injusto", "source": "Requiere outcomes posteriores"},
        ],
        "funnel": build_funnel(scores),
        "markets": [
            {
                "country": str(row["country"]),
                "market": str(row["market_label"]),
                "source": str(row["market"]),
                "listings": int(row["listings"]),
                "high_risk_rate": percent_from_ratio(row["high_risk_rate"]),
                "critical_risk_rate": percent_from_ratio(row["critical_risk_rate"]),
                "avg_risk_score": number(row["avg_risk_score"]),
            }
            for _, row in market_summary.iterrows()
        ],
        "segments": records(segment_summary),
        "driver_matrix": build_driver_matrix(scores),
        "temporal_proxy": build_temporal_proxy(scores),
        "segment_ranking": build_segment_ranking(scores),
        "top_risk_listings": [
            {
                "listing_id": int(row["listing_id"]),
                "name": str(row["name"])[:80],
                "market": f"{row['country']} / {row['market_label']}",
                "risk_score": number(row["risk_score"]),
                "trust_score": number(row["trust_score"]),
                "risk_segment": str(row["risk_segment"]),
                "cause": str(row["dispute_cause_proxy"]),
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
  <title>Airbnb Trust & Safety Risk Dashboard</title>
  <style>
    :root {{
      --bg: #f6f7f3;
      --panel: #fff;
      --ink: #172026;
      --muted: #607078;
      --line: #d8ded6;
      --risk: #d9485f;
      --trust: #2f6f9f;
      --warn: #b4891d;
      --green: #3d7c59;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--bg); color: var(--ink); font-family: Inter, Segoe UI, Arial, sans-serif; }}
    header {{ padding: 24px 30px 18px; background: #fff; border-bottom: 1px solid var(--line); display: grid; gap: 12px; }}
    h1 {{ margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }}
    p {{ line-height: 1.45; }}
    header p, .muted {{ color: var(--muted); margin: 0; }}
    main {{ padding: 22px 30px 36px; display: grid; gap: 18px; }}
    .kpis {{ display: grid; grid-template-columns: repeat(6, minmax(140px, 1fr)); gap: 12px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(280px, 1fr)); gap: 18px; }}
    .card, .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; }}
    .card span {{ display: block; color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }}
    .card strong {{ display: block; margin-top: 8px; font-size: 28px; line-height: 1; }}
    h2 {{ margin: 0 0 14px; font-size: 18px; letter-spacing: 0; }}
    h3 {{ margin: 0 0 8px; font-size: 15px; }}
    .users {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .pill {{ border: 1px solid var(--line); border-radius: 999px; padding: 7px 10px; background: #f8faf8; color: var(--ink); font-size: 13px; }}
    .bar-row {{ display: grid; grid-template-columns: minmax(130px, 230px) 1fr 92px; gap: 10px; align-items: center; margin: 9px 0; }}
    .label {{ overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }}
    .track {{ height: 12px; background: #edf0ed; border-radius: 999px; overflow: hidden; }}
    .bar {{ height: 100%; background: var(--trust); border-radius: 999px; }}
    .bar.risk {{ background: var(--risk); }}
    .value {{ text-align: right; color: var(--muted); font-variant-numeric: tabular-nums; }}
    .market-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; }}
    .market {{ border: 1px solid var(--line); border-left: 6px solid var(--risk); border-radius: 8px; padding: 12px; background: #fff; }}
    .market strong {{ display: block; margin-bottom: 4px; }}
    .funnel {{ display: grid; gap: 8px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 9px 7px; text-align: left; font-size: 14px; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .trend {{ width: 100%; height: 230px; }}
    footer {{ color: var(--muted); padding: 0 30px 24px; font-size: 13px; }}
    @media (max-width: 1100px) {{ .kpis {{ grid-template-columns: repeat(3, 1fr); }} .grid {{ grid-template-columns: 1fr; }} }}
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
    <div>
      <h1>Airbnb Trust & Safety Risk Dashboard</h1>
      <p id="objective"></p>
    </div>
    <div class="users" id="users"></div>
  </header>
  <main>
    <section class="kpis" id="kpis"></section>
    <section class="panel">
      <h2>KPIs del modelo y operacion</h2>
      <table id="modelKpis"></table>
    </section>
    <section class="grid">
      <div class="panel"><h2>Mapa geografico de riesgo</h2><div class="market-grid" id="markets"></div></div>
      <div class="panel"><h2>Embudo de riesgo</h2><div class="funnel" id="funnel"></div></div>
      <div class="panel"><h2>Matriz causa-impacto</h2><div id="driverMatrix"></div></div>
      <div class="panel"><h2>Ranking de segmentos</h2><div id="segmentRanking"></div></div>
    </section>
    <section class="panel">
      <h2>Serie temporal proxy</h2>
      <p class="muted">Usa ultima review observada por listing como proxy hasta incorporar reservas y disputas graves reales.</p>
      <svg class="trend" id="trend"></svg>
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
    const num = value => fmt.format(Math.round(value || 0));
    const dec = value => Number(value || 0).toFixed(2);
    const pct = value => `${{Number(value || 0).toFixed(2)}}%`;

    function renderKpis() {{
      const k = payload.kpis;
      const rows = [
        ['Listings evaluados', num(k.listings)],
        ['Alto riesgo', num(k.high_risk_listings)],
        ['% alto riesgo', pct(k.high_risk_rate)],
        ['Critical', num(k.critical_risk_listings)],
        ['Risk score prom.', dec(k.avg_risk_score)],
        ['Trust score prom.', dec(k.avg_trust_score)],
      ];
      document.getElementById('kpis').innerHTML = rows.map(([label, value]) => `<div class="card"><span>${{label}}</span><strong>${{value}}</strong></div>`).join('');
    }}

    function bars(id, rows, labelKey, valueKey, cls = 'risk') {{
      const max = Math.max(...rows.map(row => row[valueKey] || 0), 1);
      document.getElementById(id).innerHTML = rows.map(row => {{
        const value = row[valueKey] || 0;
        const width = Math.max(2, value / max * 100);
        return `<div class="bar-row"><div class="label" title="${{row[labelKey]}}">${{row[labelKey]}}</div><div class="track"><div class="bar ${{cls}}" style="width:${{width}}%"></div></div><div class="value">${{num(value)}}</div></div>`;
      }}).join('');
    }}

    function renderModelKpis() {{
      const header = '<thead><tr><th>Indicador</th><th>Valor actual</th><th>Meta</th><th>Fuente requerida</th></tr></thead>';
      const body = payload.model_kpis.map(row => `<tr><td>${{row.indicator}}</td><td>${{row.value}}</td><td>${{row.target}}</td><td>${{row.source}}</td></tr>`).join('');
      document.getElementById('modelKpis').innerHTML = `${{header}}<tbody>${{body}}</tbody>`;
    }}

    function renderMarkets() {{
      document.getElementById('markets').innerHTML = payload.markets.map(row => `<div class="market"><strong>${{row.country}}</strong><span>${{row.market}}</span><p class="muted">${{num(row.listings)}} listings | ${{pct(row.high_risk_rate)}} alto riesgo | score ${{dec(row.avg_risk_score)}}</p></div>`).join('');
    }}

    function renderTrend() {{
      const rows = payload.temporal_proxy;
      const svg = document.getElementById('trend');
      const width = svg.clientWidth || 900;
      const height = 230;
      svg.setAttribute('viewBox', `0 0 ${{width}} ${{height}}`);
      if (!rows.length) {{
        svg.innerHTML = '<text x="16" y="36" fill="#607078">Sin datos temporales disponibles.</text>';
        return;
      }}
      const max = Math.max(...rows.map(row => row.high_risk_listings), 1);
      const points = rows.map((row, index) => {{
        const x = 34 + (index / Math.max(rows.length - 1, 1)) * (width - 68);
        const y = height - 30 - (row.high_risk_listings / max) * (height - 64);
        return [x, y, row];
      }});
      const line = points.map(point => `${{point[0]}},${{point[1]}}`).join(' ');
      const dots = points.map(([x, y, row]) => `<circle cx="${{x}}" cy="${{y}}" r="3" fill="#d9485f"><title>${{row.year_month}}: ${{num(row.high_risk_listings)}} high risk</title></circle>`).join('');
      svg.innerHTML = `<polyline fill="none" stroke="#d9485f" stroke-width="3" points="${{line}}"></polyline>${{dots}}<text x="34" y="20" fill="#607078">High-risk listings por mes observado</text>`;
    }}

    function renderTopRisk() {{
      const header = '<thead><tr><th>Listing</th><th>Mercado</th><th>Riesgo</th><th>Confianza</th><th>Causa proxy</th><th>Accion</th></tr></thead>';
      const body = payload.top_risk_listings.map(row => `<tr><td>${{row.name}}<br><span class="muted">#${{row.listing_id}}</span></td><td>${{row.market}}</td><td>${{dec(row.risk_score)}}<br>${{row.risk_segment}}</td><td>${{dec(row.trust_score)}}</td><td>${{row.cause}}</td><td>${{row.action}}</td></tr>`).join('');
      document.getElementById('topRisk').innerHTML = `${{header}}<tbody>${{body}}</tbody>`;
    }}

    document.getElementById('objective').textContent = payload.objective;
    document.getElementById('users').innerHTML = payload.users.map(user => `<span class="pill">${{user}}</span>`).join('');
    renderKpis();
    renderModelKpis();
    renderMarkets();
    bars('funnel', payload.funnel, 'stage', 'listings');
    bars('driverMatrix', payload.driver_matrix, 'cause', 'high_risk_listings');
    bars('segmentRanking', payload.segment_ranking, 'segment', 'high_risk_rate');
    renderTrend();
    renderTopRisk();
    document.getElementById('footer').textContent = `Generado: ${{payload.generated_at_utc}} | Fuente: ${{payload.sources.analytics_dir}}`;
    window.addEventListener('resize', renderTrend);
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

