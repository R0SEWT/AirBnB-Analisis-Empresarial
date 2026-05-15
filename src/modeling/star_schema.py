from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.transformations.common import ensure_parent


@dataclass(frozen=True)
class StarSchemaPaths:
    dim_listing: Path
    dim_host: Path
    dim_location: Path
    dim_date: Path
    fact_listing_snapshot: Path
    fact_reviews: Path


def default_star_paths(output_dir: Path) -> StarSchemaPaths:
    return StarSchemaPaths(
        dim_listing=output_dir / "dim_listing.parquet",
        dim_host=output_dir / "dim_host.parquet",
        dim_location=output_dir / "dim_location.parquet",
        dim_date=output_dir / "dim_date.parquet",
        fact_listing_snapshot=output_dir / "fact_listing_snapshot.parquet",
        fact_reviews=output_dir / "fact_reviews.parquet",
    )


def date_key(series: pd.Series) -> pd.Series:
    dates = pd.to_datetime(series, errors="coerce")
    return (dates.dt.strftime("%Y%m%d")).astype("Int64")


def build_dim_date(dates: pd.Series) -> pd.DataFrame:
    clean_dates = pd.to_datetime(dates, errors="coerce").dropna().drop_duplicates().sort_values()
    dim = pd.DataFrame({"date": clean_dates})
    dim["date_key"] = date_key(dim["date"])
    dim["year"] = dim["date"].dt.year
    dim["quarter"] = dim["date"].dt.quarter
    dim["month"] = dim["date"].dt.month
    dim["month_name"] = dim["date"].dt.month_name()
    dim["year_month"] = dim["date"].dt.strftime("%Y-%m")
    dim["day"] = dim["date"].dt.day
    dim["day_of_week"] = dim["date"].dt.day_name()
    return dim[["date_key", "date", "year", "quarter", "month", "month_name", "year_month", "day", "day_of_week"]]


def build_star_schema(
    gold_listings_path: Path = Path("data/gold/listings.parquet"),
    gold_reviews_path: Path = Path("data/gold/reviews.parquet"),
    output_dir: Path = Path("data/gold/star"),
    review_batch_size: int = 250_000,
) -> dict:
    """Build a BI-ready star schema from separate gold listings and reviews datasets."""
    listings = pd.read_parquet(gold_listings_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = default_star_paths(output_dir)

    location_columns = ["neighbourhood", "neighbourhood_cleansed", "neighbourhood_group_cleansed"]
    locations = listings[location_columns].fillna("Unknown").drop_duplicates().reset_index(drop=True)
    locations.insert(0, "location_key", range(1, len(locations) + 1))
    listings_with_location = listings.merge(locations, on=location_columns, how="left")

    dim_listing_columns = [
        "listing_id",
        "listing_url",
        "name",
        "description",
        "property_type",
        "room_type",
        "accommodates",
        "bathrooms",
        "bathrooms_text",
        "bedrooms",
        "beds",
    ]
    dim_listing = listings_with_location[dim_listing_columns].drop_duplicates("listing_id")

    dim_host_columns = [
        "host_id",
        "host_name",
        "host_since",
        "host_is_superhost",
        "host_identity_verified",
        "host_response_rate",
        "host_acceptance_rate",
    ]
    dim_host = listings_with_location[dim_host_columns].dropna(subset=["host_id"]).drop_duplicates("host_id")

    fact_listing_snapshot = listings_with_location[
        [
            "listing_id",
            "host_id",
            "location_key",
            "last_scraped",
            "price",
            "price_per_accommodates",
            "minimum_nights",
            "maximum_nights",
            "availability_365",
            "number_of_reviews",
            "review_scores_rating",
            "reviews_per_month",
        ]
    ].copy()
    fact_listing_snapshot["last_scraped_date_key"] = date_key(fact_listing_snapshot["last_scraped"])
    fact_listing_snapshot = fact_listing_snapshot.drop(columns=["last_scraped"])

    reviews_file = pq.ParquetFile(gold_reviews_path)
    review_dates = []
    fact_rows = 0
    writer: pq.ParquetWriter | None = None
    fact_schema = pa.schema(
        [
            ("review_id", pa.int64()),
            ("listing_id", pa.int64()),
            ("review_date_key", pa.int64()),
            ("reviewer_id", pa.int64()),
            ("comment_length", pa.int32()),
            ("has_comment", pa.bool_()),
        ]
    )

    ensure_parent(paths.fact_reviews)
    try:
        for batch in reviews_file.iter_batches(batch_size=review_batch_size):
            reviews = batch.to_pandas()
            review_dates.append(reviews["review_date"])
            fact_reviews = pd.DataFrame(
                {
                    "review_id": reviews["review_id"],
                    "listing_id": reviews["listing_id"],
                    "review_date_key": date_key(reviews["review_date"]),
                    "reviewer_id": reviews["reviewer_id"],
                    "comment_length": reviews["comment_length"],
                    "has_comment": reviews["has_comment"],
                }
            ).dropna(subset=["review_id", "listing_id", "review_date_key"])
            fact_reviews["review_id"] = fact_reviews["review_id"].astype("int64")
            fact_reviews["listing_id"] = fact_reviews["listing_id"].astype("int64")
            fact_reviews["review_date_key"] = fact_reviews["review_date_key"].astype("int64")
            fact_reviews["reviewer_id"] = fact_reviews["reviewer_id"].astype("int64")
            fact_reviews["comment_length"] = fact_reviews["comment_length"].astype("int32")
            fact_reviews["has_comment"] = fact_reviews["has_comment"].astype("bool")
            table = pa.Table.from_pandas(fact_reviews, schema=fact_schema, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(paths.fact_reviews, fact_schema, compression="snappy")
            writer.write_table(table)
            fact_rows += len(fact_reviews)
    finally:
        if writer is not None:
            writer.close()

    listing_dates = pd.to_datetime(
        fact_listing_snapshot["last_scraped_date_key"].astype("string"),
        format="%Y%m%d",
        errors="coerce",
    )
    review_date_values = pd.concat(review_dates, ignore_index=True) if review_dates else pd.Series(dtype="datetime64[ns]")
    dim_date = build_dim_date(pd.concat([listing_dates, review_date_values], ignore_index=True))

    dim_listing.to_parquet(paths.dim_listing, index=False)
    dim_host.to_parquet(paths.dim_host, index=False)
    locations.to_parquet(paths.dim_location, index=False)
    dim_date.to_parquet(paths.dim_date, index=False)
    fact_listing_snapshot.to_parquet(paths.fact_listing_snapshot, index=False)

    return {
        "dim_listing_rows": len(dim_listing),
        "dim_host_rows": len(dim_host),
        "dim_location_rows": len(locations),
        "dim_date_rows": len(dim_date),
        "fact_listing_snapshot_rows": len(fact_listing_snapshot),
        "fact_reviews_rows": fact_rows,
        "outputs": {name: str(path) for name, path in paths.__dict__.items()},
    }
