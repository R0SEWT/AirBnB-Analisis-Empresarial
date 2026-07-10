from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.transformations.common import ensure_parent

GOLD_LISTING_COLUMNS = [
    "listing_id",
    "listing_url",
    "last_scraped",
    "source",
    "name",
    "description",
    "host_id",
    "host_name",
    "host_since",
    "host_is_superhost",
    "host_identity_verified",
    "host_response_rate",
    "host_acceptance_rate",
    "neighbourhood",
    "neighbourhood_cleansed",
    "neighbourhood_group_cleansed",
    "latitude",
    "longitude",
    "property_type",
    "room_type",
    "accommodates",
    "bathrooms",
    "bathrooms_text",
    "bedrooms",
    "beds",
    "price",
    "price_per_accommodates",
    "minimum_nights",
    "maximum_nights",
    "availability_365",
    "number_of_reviews",
    "review_scores_rating",
    "reviews_per_month",
    "_source_file",
    "_loaded_at_utc",
]

GOLD_REVIEW_COLUMNS = [
    "listing_id",
    "review_id",
    "review_date",
    "review_year",
    "review_month",
    "reviewer_id",
    "reviewer_name",
    "comments",
    "comment_length",
    "has_comment",
    "_source_file",
    "_loaded_at_utc",
]


def build_gold_listings(
    silver_listings_path: Path,
    output_path: Path,
    csv_output_path: Path | None = None,
) -> int:
    """Publish the business-ready listings dataset without joining reviews."""
    listings = pd.read_parquet(silver_listings_path)
    columns = [column for column in GOLD_LISTING_COLUMNS if column in listings.columns]
    listings = listings[columns]

    ensure_parent(output_path)
    listings.to_parquet(output_path, index=False)
    if csv_output_path is not None:
        ensure_parent(csv_output_path)
        listings.to_csv(csv_output_path, index=False)
    return len(listings)


def build_gold_reviews(
    silver_reviews_path: Path,
    output_path: Path,
    batch_size: int = 100_000,
) -> int:
    """Publish the business-ready reviews dataset as a separate gold table."""
    ensure_parent(output_path)
    parquet_file = pq.ParquetFile(silver_reviews_path)
    writer: pq.ParquetWriter | None = None
    rows = 0

    try:
        for batch in parquet_file.iter_batches(batch_size=batch_size):
            reviews = batch.to_pandas()
            reviews["review_year"] = reviews["review_date"].dt.year.astype("Int64")
            reviews["review_month"] = reviews["review_date"].dt.month.astype("Int64")
            reviews["has_comment"] = reviews["comment_length"].fillna(0) > 0
            reviews = reviews[GOLD_REVIEW_COLUMNS]

            table = pa.Table.from_pandas(reviews, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(output_path, table.schema, compression="snappy")
            writer.write_table(table)
            rows += len(reviews)
    finally:
        if writer is not None:
            writer.close()

    return rows

