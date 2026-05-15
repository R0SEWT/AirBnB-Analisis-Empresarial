from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from src.transformations.common import ensure_parent


@dataclass(frozen=True)
class TrustRiskOutputs:
    listing_scores: Path
    market_summary: Path
    segment_summary: Path
    summary_json: Path


def default_outputs(output_dir: Path) -> TrustRiskOutputs:
    return TrustRiskOutputs(
        listing_scores=output_dir / "listing_trust_risk.parquet",
        market_summary=output_dir / "market_trust_risk_summary.parquet",
        segment_summary=output_dir / "risk_segment_summary.parquet",
        summary_json=output_dir / "trust_risk_summary.json",
    )


def normalize_bool(series: pd.Series) -> pd.Series:
    normalized = series.astype("string").str.lower().str.strip()
    return normalized.map({"true": True, "t": True, "1": True, "false": False, "f": False, "0": False}).astype("boolean").fillna(False)


def market_name(listings: pd.DataFrame) -> pd.Series:
    return listings["_source_file"].astype("string").str.replace(".csv.gz", "", regex=False).fillna("unknown")


def clip_score(series: pd.Series, maximum: float) -> pd.Series:
    return series.clip(lower=0, upper=maximum).fillna(0)


def build_review_features(
    reviews_path: Path,
    batch_size: int = 250_000,
) -> pd.DataFrame:
    """Aggregate review signals by listing without loading all review text into memory."""
    parquet_file = pq.ParquetFile(reviews_path)
    partials = []
    max_review_date = None

    for batch in parquet_file.iter_batches(
        columns=["listing_id", "review_id", "review_date", "comment_length", "has_comment"],
        batch_size=batch_size,
    ):
        reviews = batch.to_pandas()
        if reviews.empty:
            continue
        current_max = reviews["review_date"].max()
        max_review_date = current_max if max_review_date is None else max(max_review_date, current_max)
        grouped = reviews.groupby("listing_id", dropna=True).agg(
            observed_reviews=("review_id", "count"),
            first_observed_review_date=("review_date", "min"),
            last_observed_review_date=("review_date", "max"),
            avg_comment_length=("comment_length", "mean"),
            non_empty_review_count=("has_comment", "sum"),
        )
        partials.append(grouped.reset_index())

    if not partials:
        return pd.DataFrame(
            columns=[
                "listing_id",
                "observed_reviews",
                "first_observed_review_date",
                "last_observed_review_date",
                "avg_comment_length",
                "non_empty_review_count",
                "review_recency_days",
            ]
        )

    review_features = pd.concat(partials, ignore_index=True)
    review_features = review_features.groupby("listing_id", dropna=True).agg(
        observed_reviews=("observed_reviews", "sum"),
        first_observed_review_date=("first_observed_review_date", "min"),
        last_observed_review_date=("last_observed_review_date", "max"),
        avg_comment_length=("avg_comment_length", "mean"),
        non_empty_review_count=("non_empty_review_count", "sum"),
    )
    review_features["review_recency_days"] = (
        pd.to_datetime(max_review_date) - pd.to_datetime(review_features["last_observed_review_date"])
    ).dt.days
    return review_features.reset_index()


def price_outlier_flag(listings: pd.DataFrame) -> pd.Series:
    group_columns = ["market", "room_type"]
    prices = pd.to_numeric(listings["price"], errors="coerce").astype("float64")
    quantiles = prices.groupby([listings[column] for column in group_columns]).transform(lambda values: values.quantile(0.95))
    return ((prices.notna()) & (prices > quantiles.astype("float64"))).fillna(False)


def risk_segment(score: pd.Series) -> pd.Series:
    return pd.cut(
        score,
        bins=[-1, 24, 49, 74, 100],
        labels=["Low", "Moderate", "High", "Critical"],
    ).astype("string")


def primary_driver(frame: pd.DataFrame) -> pd.Series:
    driver_columns = {
        "quality_risk": "Listing quality",
        "host_trust_risk": "Host trust",
        "review_confidence_risk": "Review confidence",
        "listing_completeness_risk": "Listing completeness",
        "price_market_risk": "Price and market anomaly",
    }
    highest = frame[list(driver_columns)].idxmax(axis=1)
    return highest.map(driver_columns)


def recommended_action(frame: pd.DataFrame) -> pd.Series:
    mapping = {
        "Listing quality": "Prioritize listing quality review and guest-experience follow-up",
        "Host trust": "Request host verification or host support intervention",
        "Review confidence": "Monitor low-confidence listing until more recent guest signals appear",
        "Listing completeness": "Ask host to complete listing content and operational details",
        "Price and market anomaly": "Audit pricing and availability against comparable listings",
    }
    return frame["primary_risk_driver"].map(mapping).fillna("Monitor listing")


def build_listing_scores(listings: pd.DataFrame, review_features: pd.DataFrame) -> pd.DataFrame:
    scored = listings.merge(review_features, on="listing_id", how="left")
    scored["market"] = market_name(scored)
    scored["host_is_superhost_bool"] = normalize_bool(scored["host_is_superhost"])
    scored["host_identity_verified_bool"] = normalize_bool(scored["host_identity_verified"])
    scored["observed_reviews"] = scored["observed_reviews"].fillna(0)
    scored["avg_comment_length"] = scored["avg_comment_length"].fillna(0)
    scored["non_empty_review_count"] = scored["non_empty_review_count"].fillna(0)
    scored["review_recency_days"] = scored["review_recency_days"].fillna(9999)
    scored["description_length"] = scored["description"].fillna("").astype("string").str.len()
    scored["is_price_outlier"] = price_outlier_flag(scored)

    rating = scored["review_scores_rating"]
    scored["quality_risk"] = clip_score((4.8 - rating.fillna(4.2)) * 18, 25)
    scored.loc[rating.isna(), "quality_risk"] = 18

    response_gap = (0.85 - scored["host_response_rate"].fillna(0.85)) * 10
    acceptance_gap = (0.75 - scored["host_acceptance_rate"].fillna(0.75)) * 8
    scored["host_trust_risk"] = 0
    scored.loc[~scored["host_identity_verified_bool"], "host_trust_risk"] += 9
    scored.loc[~scored["host_is_superhost_bool"], "host_trust_risk"] += 4
    scored["host_trust_risk"] += clip_score(response_gap, 4)
    scored["host_trust_risk"] += clip_score(acceptance_gap, 3)

    scored["review_confidence_risk"] = 0
    scored.loc[scored["observed_reviews"] == 0, "review_confidence_risk"] += 14
    scored.loc[(scored["observed_reviews"] > 0) & (scored["observed_reviews"] < 5), "review_confidence_risk"] += 7
    scored.loc[scored["review_recency_days"] > 365, "review_confidence_risk"] += 5
    scored.loc[(scored["observed_reviews"] > 0) & (scored["avg_comment_length"] < 40), "review_confidence_risk"] += 3

    scored["listing_completeness_risk"] = 0
    scored.loc[scored["description_length"] < 120, "listing_completeness_risk"] += 4
    scored.loc[scored["price"].isna(), "listing_completeness_risk"] += 4
    scored.loc[scored["bathrooms"].isna(), "listing_completeness_risk"] += 2
    scored.loc[scored["bedrooms"].isna(), "listing_completeness_risk"] += 2
    scored.loc[scored["latitude"].isna() | scored["longitude"].isna(), "listing_completeness_risk"] += 2

    scored["price_market_risk"] = 0
    scored.loc[scored["is_price_outlier"], "price_market_risk"] += 8
    scored.loc[(scored["availability_365"] > 300) & (scored["observed_reviews"] < 5), "price_market_risk"] += 5
    scored.loc[scored["minimum_nights"].fillna(0) > 30, "price_market_risk"] += 2

    risk_columns = [
        "quality_risk",
        "host_trust_risk",
        "review_confidence_risk",
        "listing_completeness_risk",
        "price_market_risk",
    ]
    scored["risk_score"] = scored[risk_columns].sum(axis=1).clip(0, 100).round(2)
    scored["trust_score"] = (100 - scored["risk_score"]).clip(0, 100).round(2)
    scored["risk_segment"] = risk_segment(scored["risk_score"])
    scored["primary_risk_driver"] = primary_driver(scored)
    scored["recommended_action"] = recommended_action(scored)

    output_columns = [
        "listing_id",
        "market",
        "name",
        "host_id",
        "host_name",
        "room_type",
        "property_type",
        "neighbourhood_cleansed",
        "price",
        "availability_365",
        "review_scores_rating",
        "observed_reviews",
        "last_observed_review_date",
        "review_recency_days",
        "host_is_superhost_bool",
        "host_identity_verified_bool",
        "host_response_rate",
        "host_acceptance_rate",
        "quality_risk",
        "host_trust_risk",
        "review_confidence_risk",
        "listing_completeness_risk",
        "price_market_risk",
        "risk_score",
        "trust_score",
        "risk_segment",
        "primary_risk_driver",
        "recommended_action",
    ]
    return scored[output_columns].sort_values(["risk_score", "observed_reviews"], ascending=[False, True])


def build_market_summary(scores: pd.DataFrame) -> pd.DataFrame:
    return (
        scores.groupby("market", dropna=False)
        .agg(
            listings=("listing_id", "count"),
            avg_risk_score=("risk_score", "mean"),
            avg_trust_score=("trust_score", "mean"),
            high_risk_listings=("risk_segment", lambda values: values.isin(["High", "Critical"]).sum()),
            critical_risk_listings=("risk_segment", lambda values: (values == "Critical").sum()),
            avg_rating=("review_scores_rating", "mean"),
            avg_observed_reviews=("observed_reviews", "mean"),
        )
        .reset_index()
        .assign(
            high_risk_rate=lambda frame: frame["high_risk_listings"] / frame["listings"],
            critical_risk_rate=lambda frame: frame["critical_risk_listings"] / frame["listings"],
        )
        .sort_values("avg_risk_score", ascending=False)
    )


def build_segment_summary(scores: pd.DataFrame) -> pd.DataFrame:
    order = ["Low", "Moderate", "High", "Critical"]
    summary = (
        scores.groupby("risk_segment", dropna=False)
        .agg(
            listings=("listing_id", "count"),
            avg_risk_score=("risk_score", "mean"),
            avg_trust_score=("trust_score", "mean"),
            avg_rating=("review_scores_rating", "mean"),
            avg_observed_reviews=("observed_reviews", "mean"),
        )
        .reset_index()
    )
    summary["risk_segment"] = pd.Categorical(summary["risk_segment"], categories=order, ordered=True)
    return summary.sort_values("risk_segment")


def build_trust_risk_analytics(
    gold_listings_path: Path = Path("data/gold/listings.parquet"),
    gold_reviews_path: Path = Path("data/gold/reviews.parquet"),
    output_dir: Path = Path("data/gold/analytics"),
    batch_size: int = 250_000,
    write_csv: bool = True,
) -> dict:
    listings = pd.read_parquet(gold_listings_path)
    review_features = build_review_features(gold_reviews_path, batch_size=batch_size)
    scores = build_listing_scores(listings, review_features)
    market_summary = build_market_summary(scores)
    segment_summary = build_segment_summary(scores)
    outputs = default_outputs(output_dir)

    ensure_parent(outputs.listing_scores)
    scores.to_parquet(outputs.listing_scores, index=False)
    market_summary.to_parquet(outputs.market_summary, index=False)
    segment_summary.to_parquet(outputs.segment_summary, index=False)

    csv_outputs = {}
    if write_csv:
        csv_outputs = {
            "listing_scores_csv": str(output_dir / "listing_trust_risk.csv"),
            "market_summary_csv": str(output_dir / "market_trust_risk_summary.csv"),
            "segment_summary_csv": str(output_dir / "risk_segment_summary.csv"),
        }
        scores.to_csv(csv_outputs["listing_scores_csv"], index=False)
        market_summary.to_csv(csv_outputs["market_summary_csv"], index=False)
        segment_summary.to_csv(csv_outputs["segment_summary_csv"], index=False)

    summary = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "method": "interpretable_rule_based_score_v1",
        "rows": {
            "listing_scores": int(len(scores)),
            "market_summary": int(len(market_summary)),
            "segment_summary": int(len(segment_summary)),
        },
        "outputs": {
            "listing_scores": str(outputs.listing_scores),
            "market_summary": str(outputs.market_summary),
            "segment_summary": str(outputs.segment_summary),
            **csv_outputs,
        },
        "risk_segments": segment_summary.assign(risk_segment=segment_summary["risk_segment"].astype("string")).to_dict(
            orient="records"
        ),
    }
    ensure_parent(outputs.summary_json)
    outputs.summary_json.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return summary
