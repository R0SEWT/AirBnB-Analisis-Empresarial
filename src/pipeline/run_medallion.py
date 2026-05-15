from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from src.ingestion.raw_discovery import discover_raw_files
from src.transformations.bronze import build_bronze_listings, build_bronze_reviews
from src.transformations.gold import build_gold_listings, build_gold_reviews
from src.transformations.silver import build_silver_listings, build_silver_reviews
from src.visualization.medallion_view import build_medallion_html


def run_pipeline(
    raw_dir: Path = Path("data/raw"),
    data_dir: Path = Path("data"),
    chunk_size: int = 100_000,
    write_csv: bool = True,
    build_view: bool = True,
) -> dict:
    raw_files = discover_raw_files(raw_dir)
    raw_files.ensure_required()

    bronze_listings_path = data_dir / "bronze" / "listings_bronze.parquet"
    bronze_reviews_path = data_dir / "bronze" / "reviews_bronze.parquet"
    silver_listings_path = data_dir / "silver" / "listings.parquet"
    silver_reviews_path = data_dir / "silver" / "reviews.parquet"
    gold_listings_path = data_dir / "gold" / "listings.parquet"
    gold_reviews_path = data_dir / "gold" / "reviews.parquet"
    gold_listings_csv_path = data_dir / "gold" / "listings.csv"
    summary_path = data_dir / "gold" / "medallion_summary.json"
    html_path = Path("app") / "medallion_viewer.html"

    bronze_listing_rows = build_bronze_listings(raw_files, bronze_listings_path)
    bronze_review_rows = build_bronze_reviews(raw_files, bronze_reviews_path, chunk_size=chunk_size)
    silver_listing_rows = build_silver_listings(bronze_listings_path, silver_listings_path)
    silver_review_rows = build_silver_reviews(bronze_reviews_path, silver_reviews_path, batch_size=chunk_size)
    gold_listing_rows = build_gold_listings(
        silver_listings_path,
        gold_listings_path,
        csv_output_path=gold_listings_csv_path if write_csv else None,
    )
    gold_review_rows = build_gold_reviews(silver_reviews_path, gold_reviews_path, batch_size=chunk_size)

    summary = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "layers": {
            "raw": {
                "files": len(raw_files.listings) + len(raw_files.reviews),
                "listing_files": len(raw_files.listings),
                "review_files": len(raw_files.reviews),
            },
            "bronze": {
                "rows": bronze_listing_rows + bronze_review_rows,
                "listing_rows": bronze_listing_rows,
                "review_rows": bronze_review_rows,
            },
            "silver": {
                "rows": silver_listing_rows + silver_review_rows,
                "listing_rows": silver_listing_rows,
                "review_rows": silver_review_rows,
            },
            "gold": {
                "rows": gold_listing_rows + gold_review_rows,
                "listing_rows": gold_listing_rows,
                "review_rows": gold_review_rows,
            },
        },
        "outputs": {
            "bronze_listings": str(bronze_listings_path),
            "bronze_reviews": str(bronze_reviews_path),
            "silver_listings": str(silver_listings_path),
            "silver_reviews": str(silver_reviews_path),
            "gold_listings_parquet": str(gold_listings_path),
            "gold_reviews_parquet": str(gold_reviews_path),
            "gold_listings_csv": str(gold_listings_csv_path) if write_csv else "disabled",
            "visual_interface": str(html_path) if build_view else "disabled",
        },
    }

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if build_view:
        build_medallion_html(summary_path, html_path)

    return summary


def print_summary(summary: dict) -> None:
    layers = summary["layers"]
    rows = [
        ("raw_files", layers["raw"]["files"]),
        ("bronze_rows", layers["bronze"]["rows"]),
        ("silver_rows", layers["silver"]["rows"]),
        ("gold_rows", layers["gold"]["rows"]),
    ]
    width = max(len(name) for name, _ in rows)
    for name, value in rows:
        print(f"{name:<{width}} {value:,}")
    print("\nOutputs:")
    for name, path in summary["outputs"].items():
        print(f"- {name}: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Airbnb medallion data layers.")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--chunk-size", type=int, default=100_000)
    parser.add_argument("--no-csv", action="store_true", help="Skip gold listings CSV export.")
    parser.add_argument("--no-view", action="store_true", help="Skip static HTML interface generation.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_pipeline(
        raw_dir=args.raw_dir,
        data_dir=args.data_dir,
        chunk_size=args.chunk_size,
        write_csv=not args.no_csv,
        build_view=not args.no_view,
    )
    print_summary(summary)


if __name__ == "__main__":
    main()
