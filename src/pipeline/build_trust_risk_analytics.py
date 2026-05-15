from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.analytics.trust_risk import build_trust_risk_analytics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build trust and risk analytics marts from gold Airbnb data.")
    parser.add_argument("--gold-listings", type=Path, default=Path("data/gold/listings.parquet"))
    parser.add_argument("--gold-reviews", type=Path, default=Path("data/gold/reviews.parquet"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/gold/analytics"))
    parser.add_argument("--batch-size", type=int, default=250_000)
    parser.add_argument("--no-csv", action="store_true", help="Skip CSV exports.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build_trust_risk_analytics(
        gold_listings_path=args.gold_listings,
        gold_reviews_path=args.gold_reviews,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        write_csv=not args.no_csv,
    )
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

