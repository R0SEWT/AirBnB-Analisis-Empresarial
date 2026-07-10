"""Silver reviews → Gold: NLP clustering with auto-generated segment labels."""

import re
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import Normalizer

_SCHEMA_PATH = Path(__file__).parents[3] / "configs" / "lima_schema.yaml"

_HTML_TAG = re.compile(r"<[^>]+>")
_NON_ALPHA = re.compile(r"[^a-zA-ZáéíóúñüÁÉÍÓÚÑÜ\s]")


def _load_schema() -> dict:
    with open(_SCHEMA_PATH) as f:
        return yaml.safe_load(f)


def clean_text(text: str) -> str:
    text = _HTML_TAG.sub(" ", text)
    text = _NON_ALPHA.sub(" ", text)
    return " ".join(text.lower().split())


def build_listing_corpus(reviews_path: Path) -> pd.DataFrame:
    reviews = pd.read_csv(
        reviews_path,
        usecols=["listing_id", "comments"],
        dtype={"comments": "str"},
    )
    reviews["comments"] = reviews["comments"].fillna("").apply(clean_text)
    corpus = (
        reviews.groupby("listing_id")["comments"]
        .apply(" ".join)
        .reset_index()
    )
    corpus.columns = ["listing_id", "text"]
    return corpus


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


def auto_label_clusters(
    X_tfidf,
    labels: np.ndarray,
    vocab: np.ndarray,
    n_terms: int,
) -> dict:
    label_map = {}
    for seg in np.unique(labels):
        mask = labels == seg
        mean_vec = np.asarray(X_tfidf[mask].mean(axis=0)).ravel()
        top_idx = mean_vec.argsort()[::-1][:n_terms]
        label_map[int(seg)] = " / ".join(vocab[top_idx])
    return label_map


def run_review_segmentation() -> pd.DataFrame:
    schema = _load_schema()
    cfg = schema["review_segmentation"]
    tfidf_cfg = cfg["tfidf"]

    reviews_path = Path(cfg["raw_reviews"])
    print("Building listing corpus…")
    corpus = build_listing_corpus(reviews_path)
    print(f"Corpus: {len(corpus):,} listings with reviews")

    print("Fitting TF-IDF…")
    tfidf = TfidfVectorizer(
        max_features=tfidf_cfg["max_features"],
        min_df=tfidf_cfg["min_df"],
        max_df=tfidf_cfg["max_df"],
        ngram_range=tuple(tfidf_cfg["ngram_range"]),
        stop_words=tfidf_cfg["stop_words"],
    )
    X_tfidf = tfidf.fit_transform(corpus["text"])
    vocab = tfidf.get_feature_names_out()

    print("LSA (TruncatedSVD)…")
    svd = TruncatedSVD(
        n_components=cfg["svd_components"], random_state=cfg["random_state"]
    )
    X = Normalizer().fit_transform(svd.fit_transform(X_tfidf))

    k = _best_k(X, cfg["k_min"], cfg["k_max"], cfg["random_state"])

    km = KMeans(n_clusters=k, random_state=cfg["random_state"], n_init="auto")
    labels = km.fit_predict(X)
    corpus["review_segment"] = labels

    label_map = auto_label_clusters(X_tfidf, labels, vocab, cfg["top_label_terms"])
    corpus["review_segment_label"] = corpus["review_segment"].map(label_map)

    print("\nSegment summary:")
    summary = corpus.groupby(["review_segment", "review_segment_label"]).size()
    summary.name = "count"
    print(summary.to_string())

    result = corpus[["listing_id", "review_segment", "review_segment_label"]].copy()

    out_segments = Path(cfg["output_segments"])
    out_segments.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(out_segments, index=False)
    print(f"\nSegments written: {out_segments} ({len(result):,} rows)")

    label_df = pd.DataFrame(
        [(k, v) for k, v in label_map.items()],
        columns=["segment", "label"],
    )
    out_labels = Path(cfg["output_labels"])
    label_df.to_csv(out_labels, index=False)
    print(f"Labels written: {out_labels}")

    return result


if __name__ == "__main__":
    run_review_segmentation()
