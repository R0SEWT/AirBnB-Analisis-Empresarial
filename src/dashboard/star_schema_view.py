from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from html import escape
from pathlib import Path

import pyarrow.parquet as pq

from src.transformations.common import ensure_parent


TABLES = [
    {
        "name": "dim_listing",
        "role": "Dimension",
        "key": "listing_id",
        "description": "Atributos descriptivos del alojamiento.",
    },
    {
        "name": "dim_host",
        "role": "Dimension",
        "key": "host_id",
        "description": "Perfil del host y banderas de confianza.",
    },
    {
        "name": "dim_location",
        "role": "Dimension",
        "key": "location_key",
        "description": "Jerarquia geografica normalizada.",
    },
    {
        "name": "dim_date",
        "role": "Dimension",
        "key": "date_key",
        "description": "Calendario comun para snapshots y reviews.",
    },
    {
        "name": "fact_listing_snapshot",
        "role": "Fact",
        "key": "listing_id",
        "description": "Medidas actuales por listing: precio, disponibilidad y rating.",
    },
    {
        "name": "fact_reviews",
        "role": "Fact",
        "key": "review_id",
        "description": "Eventos de reviews con fecha, listing y longitud de comentario.",
    },
]

RELATIONSHIPS = [
    ("dim_listing", "listing_id", "fact_listing_snapshot", "listing_id"),
    ("dim_listing", "listing_id", "fact_reviews", "listing_id"),
    ("dim_host", "host_id", "fact_listing_snapshot", "host_id"),
    ("dim_location", "location_key", "fact_listing_snapshot", "location_key"),
    ("dim_date", "date_key", "fact_listing_snapshot", "last_scraped_date_key"),
    ("dim_date", "date_key", "fact_reviews", "review_date_key"),
]


def parquet_columns(path: Path) -> list[dict]:
    schema = pq.ParquetFile(path).schema_arrow
    return [{"name": field.name, "type": str(field.type)} for field in schema]


def parquet_rows(path: Path) -> int:
    return pq.ParquetFile(path).metadata.num_rows


def build_schema_payload(star_dir: Path = Path("data/gold/star")) -> dict:
    summary_path = star_dir / "star_schema_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    outputs = summary.get("outputs", {})
    tables = []

    for table in TABLES:
        path = Path(outputs.get(table["name"], star_dir / f"{table['name']}.parquet"))
        rows_key = f"{table['name']}_rows"
        tables.append(
            {
                **table,
                "path": str(path),
                "rows": int(summary.get(rows_key, parquet_rows(path) if path.exists() else 0)),
                "columns": parquet_columns(path) if path.exists() else [],
            }
        )

    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "star_dir": str(star_dir),
        "source_summary": str(summary_path),
        "tables": tables,
        "relationships": [
            {
                "from_table": source_table,
                "from_key": source_key,
                "to_table": target_table,
                "to_key": target_key,
            }
            for source_table, source_key, target_table, target_key in RELATIONSHIPS
        ],
    }


def render_table_card(table: dict) -> str:
    columns = "\n".join(
        f"""<tr>
          <td><code>{escape(column["name"])}</code></td>
          <td>{escape(column["type"])}</td>
        </tr>"""
        for column in table["columns"]
    )
    badge_class = "fact" if table["role"] == "Fact" else "dimension"
    return f"""
    <article class="table-card {badge_class}" id="{escape(table["name"])}">
      <div class="table-header">
        <span>{escape(table["role"])}</span>
        <strong>{escape(table["name"])}</strong>
      </div>
      <p>{escape(table["description"])}</p>
      <dl>
        <div><dt>Clave</dt><dd><code>{escape(table["key"])}</code></dd></div>
        <div><dt>Filas</dt><dd>{table["rows"]:,}</dd></div>
      </dl>
      <details>
        <summary>Columnas ({len(table["columns"])})</summary>
        <table>
          <thead><tr><th>Campo</th><th>Tipo</th></tr></thead>
          <tbody>{columns}</tbody>
        </table>
      </details>
    </article>
    """


def render_relationships(payload: dict) -> str:
    return "\n".join(
        f"""<li>
          <a href="#{escape(relation["from_table"])}">{escape(relation["from_table"])}</a>
          <code>{escape(relation["from_key"])}</code>
          <span>-></span>
          <a href="#{escape(relation["to_table"])}">{escape(relation["to_table"])}</a>
          <code>{escape(relation["to_key"])}</code>
        </li>"""
        for relation in payload["relationships"]
    )


def render_schema_html(payload: dict) -> str:
    dimensions = [table for table in payload["tables"] if table["role"] == "Dimension"]
    facts = [table for table in payload["tables"] if table["role"] == "Fact"]
    dimension_cards = "\n".join(render_table_card(table) for table in dimensions)
    fact_cards = "\n".join(render_table_card(table) for table in facts)
    relationships = render_relationships(payload)

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Airbnb Star Schema View</title>
  <style>
    :root {{
      --bg: #f6f7f3;
      --panel: #ffffff;
      --ink: #172026;
      --muted: #5f6d75;
      --line: #d8ded6;
      --fact: #2f6f9f;
      --dim: #3d7c59;
      --accent: #d9485f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      color: var(--ink);
      background: var(--bg);
    }}
    header {{
      padding: 26px 32px 18px;
      background: #fff;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{ margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }}
    header p {{ margin: 0; color: var(--muted); line-height: 1.5; max-width: 980px; }}
    main {{ padding: 24px 32px 36px; display: grid; gap: 20px; }}
    .schema {{
      display: grid;
      grid-template-columns: minmax(260px, 1fr) minmax(320px, 1.05fr);
      gap: 18px;
      align-items: start;
    }}
    .lane {{
      display: grid;
      gap: 14px;
    }}
    .lane-title {{
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0;
    }}
    .table-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-left: 8px solid var(--dim);
      border-radius: 8px;
      padding: 16px;
      scroll-margin-top: 16px;
    }}
    .table-card.fact {{ border-left-color: var(--fact); }}
    .table-header {{
      display: grid;
      gap: 5px;
      margin-bottom: 8px;
    }}
    .table-header span {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .table-header strong {{ font-size: 20px; }}
    .table-card p {{ color: var(--muted); margin: 0 0 12px; line-height: 1.4; }}
    dl {{
      display: grid;
      grid-template-columns: repeat(2, minmax(120px, 1fr));
      gap: 10px;
      margin: 0 0 12px;
    }}
    dt {{ color: var(--muted); font-size: 12px; text-transform: uppercase; font-weight: 700; }}
    dd {{ margin: 4px 0 0; font-weight: 700; }}
    code {{
      background: #edf0ed;
      border-radius: 4px;
      padding: 2px 5px;
      font-size: 12px;
    }}
    summary {{ cursor: pointer; color: var(--ink); font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
    th, td {{ border-bottom: 1px solid var(--line); text-align: left; padding: 7px 4px; font-size: 13px; }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .relationships {{
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .relationships h2 {{ margin: 0 0 12px; font-size: 19px; }}
    .relationships ul {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 9px;
    }}
    .relationships li {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      padding: 9px 10px;
      background: #f8faf8;
      border: 1px solid var(--line);
      border-radius: 6px;
    }}
    a {{ color: var(--fact); text-decoration: none; font-weight: 700; }}
    footer {{ color: var(--muted); padding: 0 32px 24px; font-size: 13px; }}
    @media (max-width: 900px) {{
      header, main, footer {{ padding-left: 16px; padding-right: 16px; }}
      .schema {{ grid-template-columns: 1fr; }}
      dl {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Airbnb Star Schema View</h1>
    <p>Vista del modelo ubicado en <code>{escape(payload["star_dir"])}</code>. Las dimensiones describen entidades de negocio y las tablas fact concentran medidas para dashboard, Power BI, Tableau o Looker.</p>
  </header>
  <main>
    <section class="schema" aria-label="Modelo estrella">
      <div class="lane">
        <h2 class="lane-title">Dimensiones</h2>
        {dimension_cards}
      </div>
      <div class="lane">
        <h2 class="lane-title">Hechos</h2>
        {fact_cards}
      </div>
    </section>
    <section class="relationships">
      <h2>Relaciones</h2>
      <ul>{relationships}</ul>
    </section>
  </main>
  <footer>Generado: {escape(payload["generated_at_utc"])} | Resumen: {escape(payload["source_summary"])}</footer>
</body>
</html>
"""


def build_schema_view(
    star_dir: Path = Path("data/gold/star"),
    output_path: Path = Path("dashboards/star_schema_view.html"),
) -> dict:
    payload = build_schema_payload(star_dir=star_dir)
    ensure_parent(output_path)
    output_path.write_text(render_schema_html(payload), encoding="utf-8")
    return {"output": str(output_path), "generated_at_utc": payload["generated_at_utc"]}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a static visual view of the BI star schema.")
    parser.add_argument("--star-dir", type=Path, default=Path("data/gold/star"))
    parser.add_argument("--output", type=Path, default=Path("dashboards/star_schema_view.html"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_schema_view(star_dir=args.star_dir, output_path=args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

