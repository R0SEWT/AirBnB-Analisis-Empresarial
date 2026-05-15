from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.dashboard.airbnb_dashboard import build_dashboard
from src.modeling.star_schema import build_star_schema


def test_star_schema_and_dashboard_are_generated_from_gold_tables(tmp_path: Path) -> None:
    data_dir = tmp_path / "data" / "gold"
    data_dir.mkdir(parents=True)

    listings = pd.DataFrame(
        [
            {
                "listing_id": 101,
                "listing_url": "https://example.test/rooms/101",
                "last_scraped": pd.Timestamp("2026-05-14"),
                "source": "city scrape",
                "name": "Centro apartment",
                "description": "Small apartment",
                "host_id": 501,
                "host_name": "Ana",
                "host_since": pd.Timestamp("2020-01-01"),
                "host_is_superhost": True,
                "host_identity_verified": True,
                "host_response_rate": 0.95,
                "host_acceptance_rate": 0.88,
                "neighbourhood": "Centro",
                "neighbourhood_cleansed": "Miraflores",
                "neighbourhood_group_cleansed": "Lima",
                "latitude": -12.12,
                "longitude": -77.03,
                "property_type": "Entire rental unit",
                "room_type": "Entire home/apt",
                "accommodates": 2,
                "bathrooms": 1.0,
                "bathrooms_text": "1 bath",
                "bedrooms": 1.0,
                "beds": 1.0,
                "price": 100.0,
                "price_per_accommodates": 50.0,
                "minimum_nights": 2,
                "maximum_nights": 30,
                "availability_365": 250,
                "number_of_reviews": 2,
                "review_scores_rating": 4.8,
                "reviews_per_month": 1.2,
                "_source_file": "listings.csv.gz",
                "_loaded_at_utc": "2026-05-15T00:00:00+00:00",
            }
        ]
    )
    reviews = pd.DataFrame(
        [
            {
                "listing_id": 101,
                "review_id": 9001,
                "review_date": pd.Timestamp("2026-05-01"),
                "review_year": 2026,
                "review_month": 5,
                "reviewer_id": 7001,
                "reviewer_name": "Luis",
                "comments": "Great place.",
                "comment_length": 12,
                "has_comment": True,
                "_source_file": "reviews.csv.gz",
                "_loaded_at_utc": "2026-05-15T00:00:00+00:00",
            }
        ]
    )

    listings_path = data_dir / "listings.parquet"
    reviews_path = data_dir / "reviews.parquet"
    star_dir = data_dir / "star"
    output_path = tmp_path / "dashboards" / "airbnb_quality_dashboard.html"
    listings.to_parquet(listings_path, index=False)
    reviews.to_parquet(reviews_path, index=False)

    summary = build_star_schema(listings_path, reviews_path, star_dir, review_batch_size=1)
    result = build_dashboard(listings_path, star_dir, output_path)

    assert summary["dim_listing_rows"] == 1
    assert summary["fact_reviews_rows"] == 1
    assert (star_dir / "dim_date.parquet").exists()
    assert output_path.exists()
    assert result["output"] == str(output_path)
    assert "Airbnb Marketplace Quality Dashboard" in output_path.read_text(encoding="utf-8")

