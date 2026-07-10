"""Raw → Bronze: type casting and structural standardization."""

from pathlib import Path

import pandas as pd
import yaml

_SCHEMA_PATH = Path(__file__).parents[2] / "configs" / "lima_schema.yaml"


def _load_schema() -> dict:
    with open(_SCHEMA_PATH) as f:
        return yaml.safe_load(f)


def _parse_price(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace(r"[$,]", "", regex=True)
        .str.strip()
        .replace("", float("nan"))
        .astype(float)
    )


def run_bronze(
    df: pd.DataFrame | None = None, out_path: Path | None = None
) -> pd.DataFrame:
    from src.ingestion.load_listings import load_raw

    schema = _load_schema()
    raw = df if df is not None else load_raw()

    bronze = raw.copy()

    bronze["price"] = _parse_price(bronze["price"])

    has_raw = "neighbourhood" in bronze.columns
    has_clean = "neighbourhood_cleansed" in bronze.columns
    if has_raw and not has_clean:
        bronze = bronze.rename(columns={"neighbourhood": "neighbourhood_cleansed"})

    if "last_review" in bronze.columns:
        bronze["last_review"] = pd.to_datetime(bronze["last_review"], errors="coerce")

    for bool_col in ("instant_bookable",):
        if bool_col in bronze.columns:
            bronze[bool_col] = bronze[bool_col].map({"t": True, "f": False})

    out_path = out_path or Path(schema["bronze"]["output"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bronze.to_parquet(out_path, index=False)
    print(f"Bronze written: {out_path} ({len(bronze):,} rows)")
    return bronze


if __name__ == "__main__":
    run_bronze()
