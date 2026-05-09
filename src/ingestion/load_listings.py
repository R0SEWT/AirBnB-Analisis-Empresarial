"""Load raw listings CSV and validate required columns."""

from pathlib import Path

import pandas as pd
import yaml

_SCHEMA_PATH = Path(__file__).parents[2] / "configs" / "lima_schema.yaml"


def _load_schema() -> dict:
    with open(_SCHEMA_PATH) as f:
        return yaml.safe_load(f)


def load_raw(path: str | Path | None = None) -> pd.DataFrame:
    schema = _load_schema()
    raw_path = Path(path) if path else Path(schema["raw_file"])

    if not raw_path.exists():
        raise FileNotFoundError(
            f"Raw file not found: {raw_path}\n"
            "Download listings.csv from https://insideairbnb.com/get-the-data/ "
            "(Mexico City) and place it at data/raw/mexico_listings.csv"
        )

    df = pd.read_csv(raw_path, low_memory=False)

    missing = [c for c in schema["required_columns"] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    return df
