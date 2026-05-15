from __future__ import annotations

import gzip
from pathlib import Path

import pandas as pd

from src.pipeline.run_medallion import run_pipeline


def write_gzip_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as file:
        frame.to_csv(file, index=False)


def test_medallion_pipeline_builds_separate_listing_and_review_gold_datasets(tmp_path: Path) -> None:
    raw_dir = tmp_path / "data" / "raw"
    data_dir = tmp_path / "data"

    listings = pd.DataFrame(
        [
            {
                "id": "101",
                "listing_url": "https://example.test/rooms/101",
                "scrape_id": "20260514000000",
                "last_scraped": "2026-05-14",
                "source": "city scrape",
                "name": "Centro apartment",
                "description": "Small apartment",
                "host_id": "501",
                "host_name": "Ana",
                "host_since": "2020-01-01",
                "host_response_rate": "95%",
                "host_acceptance_rate": "88%",
                "host_is_superhost": "t",
                "host_identity_verified": "t",
                "neighbourhood": "Centro",
                "neighbourhood_cleansed": "Miraflores",
                "neighbourhood_group_cleansed": "Lima",
                "latitude": "-12.12",
                "longitude": "-77.03",
                "property_type": "Entire rental unit",
                "room_type": "Entire home/apt",
                "accommodates": "2",
                "bathrooms": "1",
                "bathrooms_text": "1 bath",
                "bedrooms": "1",
                "beds": "1",
                "price": "$100.00",
                "minimum_nights": "2",
                "maximum_nights": "30",
                "availability_365": "250",
                "number_of_reviews": "2",
                "review_scores_rating": "4.8",
                "reviews_per_month": "1.2",
            }
        ]
    )
    reviews = pd.DataFrame(
        [
            {
                "listing_id": "101",
                "id": "9001",
                "date": "2026-05-01",
                "reviewer_id": "7001",
                "reviewer_name": "Luis",
                "comments": "Great place.",
            },
            {
                "listing_id": "101",
                "id": "9002",
                "date": "2026-05-03",
                "reviewer_id": "7002",
                "reviewer_name": "Mia",
                "comments": "Clean and central.",
            },
        ]
    )

    write_gzip_csv(raw_dir / "listings.csv.gz", listings)
    write_gzip_csv(raw_dir / "reviews.csv.gz", reviews)

    summary = run_pipeline(raw_dir=raw_dir, data_dir=data_dir, chunk_size=1, write_csv=True, build_view=False)

    gold_listings_path = data_dir / "gold" / "listings.parquet"
    gold_reviews_path = data_dir / "gold" / "reviews.parquet"
    gold_listings = pd.read_parquet(gold_listings_path)
    gold_reviews = pd.read_parquet(gold_reviews_path)

    assert summary["layers"]["gold"]["listing_rows"] == 1
    assert summary["layers"]["gold"]["review_rows"] == 2
    assert gold_listings.loc[0, "listing_id"] == 101
    assert gold_listings.loc[0, "price"] == 100.0
    assert "review_count_raw" not in gold_listings.columns
    assert len(gold_reviews) == 2
    assert set(gold_reviews["review_id"]) == {9001, 9002}
    assert gold_reviews.loc[0, "review_year"] == 2026
    assert bool(gold_reviews.loc[0, "has_comment"]) is True
