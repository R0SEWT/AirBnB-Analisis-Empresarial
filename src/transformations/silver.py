"""Bronze → Silver: deduplication, outlier removal, imputation."""

from pathlib import Path

import pandas as pd
import yaml

_SCHEMA_PATH = Path(__file__).parents[2] / "configs" / "lima_schema.yaml"


def _load_schema() -> dict:
    with open(_SCHEMA_PATH) as f:
        return yaml.safe_load(f)


def run_silver(df: pd.DataFrame | None = None) -> pd.DataFrame:
    schema = _load_schema()
    pct = schema["silver"]["price_outlier_percentile"]

    if df is None:
        bronze_path = Path(schema["bronze"]["output"])
        if not bronze_path.exists():
            raise FileNotFoundError(
                f"Bronze file not found: {bronze_path}. Run bronze first."
            )
        df = pd.read_parquet(bronze_path)

    silver = df.drop_duplicates(subset="id").copy()

    price_ceil = silver["price"].quantile(pct / 100)
    silver = silver[(silver["price"] > 0) & (silver["price"] <= price_ceil)]

    if "neighbourhood_cleansed" in silver.columns:
        silver["neighbourhood_cleansed"] = (
            silver["neighbourhood_cleansed"].str.strip().str.lower()
        )

    if "review_scores_rating" in silver.columns:
        median_by_neighbourhood = silver.groupby("neighbourhood_cleansed")[
            "review_scores_rating"
        ].transform("median")
        silver["review_scores_rating"] = silver["review_scores_rating"].fillna(
            median_by_neighbourhood
        )
        global_median = silver["review_scores_rating"].median()
        silver["review_scores_rating"] = silver["review_scores_rating"].fillna(
            global_median
        )

    out_path = Path(schema["silver"]["output"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    silver.to_parquet(out_path, index=False)
    print(f"Silver written: {out_path} ({len(silver):,} rows)")
    return silver


if __name__ == "__main__":
    run_silver()
