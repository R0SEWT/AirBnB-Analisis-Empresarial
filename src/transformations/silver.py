from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.transformations.common import (
    ensure_parent,
    parse_bool,
    parse_money,
    parse_percent,
    safe_divide,
    text_length,
)

LISTING_COLUMNS = [
    "id",
    "listing_url",
    "scrape_id",
    "last_scraped",
    "source",
    "name",
    "description",
    "host_id",
    "host_name",
    "host_since",
    "host_response_rate",
    "host_acceptance_rate",
    "host_is_superhost",
    "host_identity_verified",
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
    "minimum_nights",
    "maximum_nights",
    "availability_365",
    "number_of_reviews",
    "review_scores_rating",
    "reviews_per_month",
    "_source_file",
    "_loaded_at_utc",
]

NUMERIC_COLUMNS = [
    "listing_id",
    "host_id",
    "latitude",
    "longitude",
    "accommodates",
    "bathrooms",
    "bedrooms",
    "beds",
    "price",
    "minimum_nights",
    "maximum_nights",
    "availability_365",
    "number_of_reviews",
    "review_scores_rating",
    "reviews_per_month",
    "host_response_rate",
    "host_acceptance_rate",
]


def build_silver_listings(bronze_path: Path, output_path: Path) -> int:
    """Create the clean listing entity at one row per listing_id."""
    listings = pd.read_parquet(bronze_path)
    listings = listings.reindex(columns=LISTING_COLUMNS)
    listings = listings.rename(columns={"id": "listing_id"})

    listings["listing_id"] = pd.to_numeric(listings["listing_id"], errors="coerce").astype("Int64")
    listings["host_id"] = pd.to_numeric(listings["host_id"], errors="coerce").astype("Int64")
    listings["last_scraped"] = pd.to_datetime(listings["last_scraped"], errors="coerce")
    listings["host_since"] = pd.to_datetime(listings["host_since"], errors="coerce")
    listings["price"] = parse_money(listings["price"])
    listings["host_response_rate"] = parse_percent(listings["host_response_rate"])
    listings["host_acceptance_rate"] = parse_percent(listings["host_acceptance_rate"])
    listings["host_is_superhost"] = parse_bool(listings["host_is_superhost"])
    listings["host_identity_verified"] = parse_bool(listings["host_identity_verified"])

    for column in NUMERIC_COLUMNS:
        if column in {"listing_id", "host_id", "price", "host_response_rate", "host_acceptance_rate"}:
            continue
        listings[column] = pd.to_numeric(listings[column], errors="coerce")

    listings = listings.dropna(subset=["listing_id"])
    listings = listings.sort_values(["listing_id", "last_scraped"], ascending=[True, False])
    listings = listings.drop_duplicates(subset=["listing_id"], keep="first")
    listings["price_per_accommodates"] = safe_divide(listings["price"], listings["accommodates"])

    ensure_parent(output_path)
    listings.to_parquet(output_path, index=False)
    return len(listings)


def build_silver_reviews(
    bronze_path: Path,
    output_path: Path,
    batch_size: int = 100_000,
) -> int:
    """Create the clean review entity while keeping chunked processing."""
    ensure_parent(output_path)
    parquet_file = pq.ParquetFile(bronze_path)
    schema = pa.schema(
        [
            ("listing_id", pa.int64()),
            ("review_id", pa.int64()),
            ("review_date", pa.timestamp("ns")),
            ("reviewer_id", pa.int64()),
            ("reviewer_name", pa.string()),
            ("comments", pa.string()),
            ("comment_length", pa.int32()),
            ("_source_file", pa.string()),
            ("_loaded_at_utc", pa.string()),
        ]
    )
    writer: pq.ParquetWriter | None = None
    rows = 0

    try:
        for batch in parquet_file.iter_batches(batch_size=batch_size):
            reviews = batch.to_pandas()
            reviews = reviews.rename(columns={"id": "review_id", "date": "review_date"})
            reviews["listing_id"] = pd.to_numeric(reviews["listing_id"], errors="coerce").astype("Int64")
            reviews["review_id"] = pd.to_numeric(reviews["review_id"], errors="coerce").astype("Int64")
            reviews["reviewer_id"] = pd.to_numeric(reviews["reviewer_id"], errors="coerce").astype("Int64")
            reviews["review_date"] = pd.to_datetime(reviews["review_date"], errors="coerce")
            reviews["comments"] = reviews["comments"].astype("string")
            reviews["comment_length"] = text_length(reviews["comments"]).astype("Int32")
            reviews = reviews.dropna(subset=["listing_id", "review_id"])
            reviews = reviews.drop_duplicates(subset=["review_id"], keep="first")
            reviews = reviews[
                [
                    "listing_id",
                    "review_id",
                    "review_date",
                    "reviewer_id",
                    "reviewer_name",
                    "comments",
                    "comment_length",
                    "_source_file",
                    "_loaded_at_utc",
                ]
            ]
            table = pa.Table.from_pandas(reviews, schema=schema, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(output_path, schema=schema, compression="snappy")
            writer.write_table(table)
            rows += len(reviews)
    finally:
        if writer is not None:
            writer.close()

    return rows

