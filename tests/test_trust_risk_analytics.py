from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.analytics.trust_risk import build_trust_risk_analytics
from src.dashboard.trust_risk_dashboard import build_dashboard


def test_trust_risk_analytics_builds_scores_and_dashboard(tmp_path: Path) -> None:
    gold_dir = tmp_path / "data" / "gold"
    analytics_dir = gold_dir / "analytics"
    dashboard_path = tmp_path / "dashboards" / "trust_risk_dashboard.html"
    gold_dir.mkdir(parents=True)

    listings = pd.DataFrame(
        [
            {
                "listing_id": 101,
                "listing_url": "https://example.test/rooms/101",
                "last_scraped": pd.Timestamp("2026-05-14"),
                "source": "city scrape",
                "name": "Risky room",
                "description": "Short",
                "host_id": 501,
                "host_name": "Ana",
                "host_since": pd.Timestamp("2020-01-01"),
                "host_is_superhost": False,
                "host_identity_verified": False,
                "host_response_rate": 0.2,
                "host_acceptance_rate": 0.3,
                "neighbourhood": "Centro",
                "neighbourhood_cleansed": "Miraflores",
                "neighbourhood_group_cleansed": "Lima",
                "latitude": -12.12,
                "longitude": -77.03,
                "property_type": "Private room",
                "room_type": "Private room",
                "accommodates": 2,
                "bathrooms": 1.0,
                "bathrooms_text": "1 bath",
                "bedrooms": 1.0,
                "beds": 1.0,
                "price": 999.0,
                "price_per_accommodates": 499.5,
                "minimum_nights": 40,
                "maximum_nights": 365,
                "availability_365": 350,
                "number_of_reviews": 1,
                "review_scores_rating": 3.9,
                "reviews_per_month": 0.1,
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
                "review_date": pd.Timestamp("2024-01-01"),
                "review_year": 2024,
                "review_month": 1,
                "reviewer_id": 7001,
                "reviewer_name": "Luis",
                "comments": "Bad",
                "comment_length": 3,
                "has_comment": True,
                "_source_file": "reviews.csv.gz",
                "_loaded_at_utc": "2026-05-15T00:00:00+00:00",
            }
        ]
    )

    listings_path = gold_dir / "listings.parquet"
    reviews_path = gold_dir / "reviews.parquet"
    listings.to_parquet(listings_path, index=False)
    reviews.to_parquet(reviews_path, index=False)

    summary = build_trust_risk_analytics(
        gold_listings_path=listings_path,
        gold_reviews_path=reviews_path,
        output_dir=analytics_dir,
        batch_size=1,
    )
    result = build_dashboard(analytics_dir=analytics_dir, output_path=dashboard_path)
    scores = pd.read_parquet(analytics_dir / "listing_trust_risk.parquet")

    assert summary["rows"]["listing_scores"] == 1
    assert scores.loc[0, "risk_score"] > 0
    assert scores.loc[0, "trust_score"] < 100
    assert scores.loc[0, "primary_risk_driver"] in {
        "Listing quality",
        "Host trust",
        "Review confidence",
        "Listing completeness",
        "Price and market anomaly",
    }
    assert dashboard_path.exists()
    assert result["output"] == str(dashboard_path)
    assert "Airbnb Trust & Safety Risk Dashboard" in dashboard_path.read_text(encoding="utf-8")
