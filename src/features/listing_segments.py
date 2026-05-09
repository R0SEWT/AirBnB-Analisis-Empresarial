"""Silver → Gold: build feature matrix and run K-means segmentation."""

from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import OneHotEncoder, StandardScaler

_SCHEMA_PATH = Path(__file__).parents[2] / "configs" / "lima_schema.yaml"


def _load_schema() -> dict:
    with open(_SCHEMA_PATH) as f:
        return yaml.safe_load(f)


def _best_k(X: np.ndarray, k_min: int, k_max: int, random_state: int) -> int:
    scores = {}
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, random_state=random_state, n_init="auto")
        labels = km.fit_predict(X)
        scores[k] = silhouette_score(X, labels, sample_size=min(5000, len(X)))
    best = max(scores, key=scores.__getitem__)
    print(f"Silhouette scores: { {k: round(v, 4) for k, v in scores.items()} }")
    print(f"Selected k={best}")
    return best


def run_segmentation(df: pd.DataFrame | None = None) -> pd.DataFrame:
    schema = _load_schema()
    seg_cfg = schema["segmentation"]

    if df is None:
        silver_path = Path(schema["silver"]["output"])
        if not silver_path.exists():
            raise FileNotFoundError(
                f"Silver file not found: {silver_path}. Run silver transform first."
            )
        df = pd.read_parquet(silver_path)

    log1p_cols = seg_cfg["features"]["log1p_scaled"]
    scale_cols = seg_cfg["features"]["scaled"]
    onehot_cols = seg_cfg["features"]["onehot"]

    all_feat_cols = log1p_cols + scale_cols + onehot_cols
    working = df[all_feat_cols].dropna()
    idx = working.index

    log1p_scaled = StandardScaler().fit_transform(np.log1p(working[log1p_cols].values))
    scaled = StandardScaler().fit_transform(working[scale_cols].values)
    enc = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    ohe = enc.fit_transform(working[onehot_cols].values)

    X = np.hstack([log1p_scaled, scaled, ohe])

    k = _best_k(
        X,
        k_min=seg_cfg["k_min"],
        k_max=seg_cfg["k_max"],
        random_state=seg_cfg["random_state"],
    )

    labels = KMeans(
        n_clusters=k, random_state=seg_cfg["random_state"], n_init="auto"
    ).fit_predict(X)

    result = df.copy()
    result["segment"] = np.nan
    result.loc[idx, "segment"] = labels
    result["segment"] = result["segment"].astype("Int64")

    segments_path = Path(schema["gold"]["segments_output"])
    segments_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(segments_path, index=False)
    print(f"Segments written: {segments_path} ({len(result):,} rows)")

    profiles = (
        result.groupby("segment")[log1p_cols + scale_cols]
        .median()
        .round(2)
    )
    profiles_path = Path(schema["gold"]["profiles_output"])
    profiles.to_csv(profiles_path)
    print(f"Profiles written: {profiles_path}")

    return result


if __name__ == "__main__":
    run_segmentation()
