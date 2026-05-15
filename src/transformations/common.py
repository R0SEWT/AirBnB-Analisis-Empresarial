from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


def ensure_parent(path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def read_csv_gz(path: Path, **kwargs) -> pd.DataFrame:
    return pd.read_csv(path, compression="gzip", dtype=str, low_memory=False, **kwargs)


def parse_money(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype("string")
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce")


def parse_percent(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.replace("%", "", regex=False).str.strip()
    return pd.to_numeric(cleaned, errors="coerce") / 100


def parse_bool(series: pd.Series) -> pd.Series:
    normalized = series.astype("string").str.lower().str.strip()
    return normalized.map({"t": True, "true": True, "1": True, "f": False, "false": False, "0": False})


def text_length(series: pd.Series) -> pd.Series:
    return series.fillna("").astype("string").str.strip().str.len()


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.mask(denominator == 0)
    return numerator / denominator


def normalize_column_name(name: str) -> str:
    clean = re.sub(r"[^0-9a-zA-Z]+", "_", name.strip().lower())
    return clean.strip("_")

