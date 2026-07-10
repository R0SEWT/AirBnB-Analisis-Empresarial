from __future__ import annotations

import json
from html import escape
from pathlib import Path

from src.transformations.common import ensure_parent


def build_medallion_html(summary_path: Path, output_path: Path) -> Path:
    summary = {}
    if Path(summary_path).exists():
        summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))

    layers = summary.get("layers", {})
    outputs = summary.get("outputs", {})
    generated_at = escape(summary.get("generated_at_utc", "Not generated yet"))

    def metric(layer: str, key: str) -> str:
        value = layers.get(layer, {}).get(key, 0)
        return f"{value:,}"

    cards = [
        ("Raw", "csv.gz originales", metric("raw", "files"), "data/raw/listings*.csv.gz + reviews*.csv.gz"),
        ("Bronze", "estructura estandarizada", metric("bronze", "rows"), "data/bronze/*.parquet"),
        ("Silver", "entidades limpias", metric("silver", "rows"), "data/silver/listings.parquet + reviews.parquet"),
        ("Gold", "datasets finales separados", metric("gold", "rows"), "data/gold/listings.parquet + reviews.parquet"),
    ]

    card_html = "\n".join(
        f"""
        <section class="stage">
          <p class="eyebrow">{escape(title)}</p>
          <h2>{escape(subtitle)}</h2>
          <strong>{escape(count)}</strong>
          <span>{escape(path)}</span>
        </section>
        """
        for title, subtitle, count, path in cards
    )

    output_items = "\n".join(
        f"<li><code>{escape(name)}</code><span>{escape(str(path))}</span></li>"
        for name, path in outputs.items()
    )

    html = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Airbnb Medallion Pipeline</title>
  <style>
    :root {{
      --ink: #172026;
      --muted: #5c6970;
      --line: #d8dee3;
      --raw: #476c9b;
      --bronze: #9a6b45;
      --silver: #6f7d86;
      --gold: #b48b18;
      --bg: #f7f8f5;
      --panel: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      background: var(--bg);
      color: var(--ink);
    }}
    header {{
      padding: 32px 6vw 18px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(28px, 4vw, 48px);
      letter-spacing: 0;
    }}
    header p {{ margin: 0; color: var(--muted); max-width: 900px; line-height: 1.5; }}
    main {{ padding: 28px 6vw 44px; }}
    .pipeline {{
      display: grid;
      grid-template-columns: repeat(4, minmax(180px, 1fr));
      gap: 14px;
      align-items: stretch;
      margin-bottom: 24px;
    }}
    .stage {{
      min-height: 190px;
      border: 1px solid var(--line);
      border-top: 8px solid var(--raw);
      background: var(--panel);
      border-radius: 8px;
      padding: 18px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .stage:nth-child(2) {{ border-top-color: var(--bronze); }}
    .stage:nth-child(3) {{ border-top-color: var(--silver); }}
    .stage:nth-child(4) {{ border-top-color: var(--gold); }}
    .eyebrow {{
      margin: 0;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    h2 {{ margin: 8px 0 12px; font-size: 20px; letter-spacing: 0; }}
    strong {{ font-size: 36px; line-height: 1; }}
    .stage span {{ color: var(--muted); overflow-wrap: anywhere; }}
    .details {{
      display: grid;
      grid-template-columns: minmax(240px, 1fr) minmax(240px, 1fr);
      gap: 18px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }}
    .panel h2 {{ margin-top: 0; }}
    ol, ul {{ padding-left: 20px; }}
    li {{ margin: 10px 0; line-height: 1.45; }}
    code {{
      background: #edf0f2;
      border-radius: 4px;
      padding: 2px 5px;
    }}
    li span {{ display: block; color: var(--muted); overflow-wrap: anywhere; margin-top: 3px; }}
    footer {{ padding: 0 6vw 28px; color: var(--muted); }}
    @media (max-width: 900px) {{
      .pipeline, .details {{ grid-template-columns: 1fr; }}
      .stage {{ min-height: 160px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Airbnb Medallion Pipeline</h1>
    <p>Arquitectura visual para cargar archivos raw con el mismo formato, transformarlos en capas bronze y silver, y publicar datasets gold separados para listings y reviews.</p>
  </header>
  <main>
    <section class="pipeline" aria-label="Pipeline medallion">
      {card_html}
    </section>
    <section class="details">
      <div class="panel">
        <h2>Flujo operativo</h2>
        <ol>
          <li>Copiar nuevos archivos <code>listings*.csv.gz</code> y <code>reviews*.csv.gz</code> en <code>data/raw</code>.</li>
          <li>Ejecutar <code>python -m src.pipeline.run_medallion</code>.</li>
          <li>Consumir <code>data/gold/listings.parquet</code> y <code>data/gold/reviews.parquet</code>.</li>
        </ol>
      </div>
      <div class="panel">
        <h2>Salidas</h2>
        <ul>{output_items}</ul>
      </div>
    </section>
  </main>
  <footer>Ultima generacion: {generated_at}</footer>
</body>
</html>
"""
    ensure_parent(output_path)
    output_path.write_text(html, encoding="utf-8")
    return output_path
