from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from src.modeling.star_schema import build_star_schema


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build BI-ready star schema from gold Airbnb datasets.")
    parser.add_argument("--gold-listings", type=Path, default=Path("data/gold/listings.parquet"))
    parser.add_argument("--gold-reviews", type=Path, default=Path("data/gold/reviews.parquet"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/gold/star"))
    parser.add_argument("--review-batch-size", type=int, default=250_000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build_star_schema(
        gold_listings_path=args.gold_listings,
        gold_reviews_path=args.gold_reviews,
        output_dir=args.output_dir,
        review_batch_size=args.review_batch_size,
    )
    summary["generated_at_utc"] = datetime.now(UTC).isoformat()
    summary_path = args.output_dir / "star_schema_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

