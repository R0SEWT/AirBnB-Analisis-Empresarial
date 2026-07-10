from __future__ import annotations

from pathlib import Path
import math
import re
import warnings

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


warnings.filterwarnings("ignore", category=FutureWarning)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs" / "tb4_rfm"

TARGET_COUNTRIES = {"United States", "Brazil", "Mexico", "Spain", "Japan"}
HIGH_RISK_SEGMENTS = {"High", "Critical"}


def read_table(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    suffixes = "".join(path.suffixes).lower()
    if suffixes.endswith(".parquet"):
        return pd.read_parquet(path, columns=columns)
    if suffixes.endswith(".csv") or suffixes.endswith(".csv.gz"):
        return pd.read_csv(path, usecols=columns)
    if suffixes.endswith(".xlsx") or suffixes.endswith(".xls"):
        return pd.read_excel(path, usecols=columns)
    raise ValueError(f"Formato no soportado: {path}")


def existing_columns(path: Path) -> list[str]:
    suffixes = "".join(path.suffixes).lower()
    if suffixes.endswith(".parquet"):
        import pyarrow.parquet as pq

        return pq.ParquetFile(path).schema.names
    if suffixes.endswith(".csv") or suffixes.endswith(".csv.gz"):
        return pd.read_csv(path, nrows=5).columns.tolist()
    return read_table(path).columns.tolist()


def selected_columns(path: Path, candidates: list[str]) -> list[str]:
    available = set(existing_columns(path))
    return [column for column in candidates if column in available]


def clean_numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    cleaned = (
        series.astype(str)
        .str.replace(r"[$,%]", "", regex=True)
        .str.replace(",", "", regex=False)
        .replace({"nan": np.nan, "None": np.nan, "<NA>": np.nan})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def source_to_market(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value)
    text = re.sub(r"\.csv(\.gz)?$", "", text)
    return text


def infer_market_country(listings: pd.DataFrame, market_summary_path: Path) -> pd.DataFrame:
    if "country" in listings.columns and listings["country"].notna().any():
        return listings
    if "_source_file" not in listings.columns or not market_summary_path.exists():
        return listings

    market_summary = read_table(market_summary_path)
    if not {"market", "country", "market_label"}.issubset(market_summary.columns):
        return listings

    mapping = market_summary[["market", "country", "market_label"]].drop_duplicates()
    inferred = listings.copy()
    inferred["_market_from_source"] = inferred["_source_file"].map(source_to_market)
    inferred = inferred.merge(mapping, left_on="_market_from_source", right_on="market", how="left")
    return inferred


def score_quantile(series: pd.Series, higher_is_better: bool, force_low_mask: pd.Series | None = None) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    scores = pd.Series(1, index=values.index, dtype="int64")
    valid = values.notna()
    if valid.sum() == 0:
        return scores

    ranked = values[valid].rank(method="first", ascending=True if higher_is_better else False)
    try:
        scored = pd.qcut(ranked, q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    except ValueError:
        pct = values[valid].rank(method="average", pct=True, ascending=True if higher_is_better else False)
        scored = np.ceil(pct * 5).clip(1, 5).astype(int)
    scores.loc[valid] = scored

    if force_low_mask is not None:
        scores.loc[force_low_mask.fillna(False)] = 1
    return scores.astype(int)


def assign_rfm_segment(df: pd.DataFrame) -> pd.Series:
    r = df["R_score"]
    f = df["F_score"]
    m = df["M_score"]
    conditions = [
        (r >= 4) & (f >= 4) & (m >= 4),
        (r <= 2) & (f >= 4) & (m >= 4),
        (f <= 1) & (r >= 4),
        (r >= 4) & (f <= 3) & (m >= 3),
        (r >= 3) & (f >= 4) & (m <= 2),
        (r <= 2) & (f <= 2),
    ]
    labels = [
        "Champions / Alto valor activo",
        "Alto valor en riesgo",
        "Nuevos o poca evidencia",
        "Potenciales en crecimiento",
        "Frecuentes de bajo valor",
        "Dormidos",
    ]
    return pd.Series(np.select(conditions, labels, default="Valor medio operativo"), index=df.index)


def assign_rfm_level(score: pd.Series) -> pd.Series:
    return pd.Series(
        np.select(
            [score >= 12, score >= 8],
            ["Alto", "Medio"],
            default="Bajo",
        ),
        index=score.index,
    )


def assign_priority_segment(df: pd.DataFrame) -> pd.Series:
    high_risk = df["high_critical_flag"].eq(1)
    level = df["rfm_level"]
    conditions = [
        level.eq("Alto") & high_risk,
        level.eq("Alto") & ~high_risk,
        level.eq("Medio") & high_risk,
        level.eq("Bajo") & high_risk,
        level.eq("Bajo") & ~high_risk,
    ]
    labels = [
        "Prioridad critica",
        "Proteger y retener",
        "Corregir antes de escalar",
        "Bajo valor pero riesgoso",
        "Monitoreo bajo",
    ]
    return pd.Series(np.select(conditions, labels, default="Monitoreo bajo"), index=df.index)


def action_for_priority(priority: str) -> str:
    actions = {
        "Prioridad critica": "Revision Trust & Safety inmediata; corregir confianza antes de impulsar demanda.",
        "Proteger y retener": "Mantener visibilidad, monitorear calidad y proteger oferta de alto valor.",
        "Corregir antes de escalar": "Aplicar mejoras de calidad/verificacion antes de campanas o mayor exposicion.",
        "Bajo valor pero riesgoso": "Depurar, corregir datos minimos o mantener monitoreo preventivo.",
        "Monitoreo bajo": "Seguimiento ligero; priorizar solo si cambia actividad o riesgo.",
    }
    return actions.get(priority, "Monitoreo operativo.")


def dominant_segment(series: pd.Series) -> str:
    counts = series.dropna().value_counts()
    if counts.empty:
        return "Sin segmento"
    return str(counts.index[0])


def format_pct(series: pd.Series) -> pd.Series:
    return (series * 100).round(2)


def markdown_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    table = df.copy()
    if max_rows is not None:
        table = table.head(max_rows)
    for column in table.columns:
        if pd.api.types.is_float_dtype(table[column]):
            table[column] = table[column].map(lambda value: "" if pd.isna(value) else f"{value:,.2f}")
        else:
            table[column] = table[column].map(lambda value: "" if pd.isna(value) else str(value))
    headers = list(table.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in table.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in headers) + " |")
    return "\n".join(lines)


def save_plot(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams["figure.figsize"] = (11, 6)

    listings_path = DATA_DIR / "gold" / "listings.parquet"
    reviews_path = DATA_DIR / "gold" / "reviews.parquet"
    risk_path = DATA_DIR / "gold" / "analytics" / "listing_trust_risk.parquet"
    market_summary_path = DATA_DIR / "gold" / "analytics" / "market_trust_risk_summary.parquet"
    risk_segment_summary_path = DATA_DIR / "gold" / "analytics" / "risk_segment_summary.parquet"

    required_paths = [listings_path, reviews_path]
    missing_required = [str(path.relative_to(ROOT)) for path in required_paths if not path.exists()]
    if missing_required:
        raise FileNotFoundError(f"Faltan archivos requeridos: {missing_required}")

    listings_cols = selected_columns(
        listings_path,
        [
            "listing_id",
            "name",
            "host_id",
            "host_name",
            "room_type",
            "property_type",
            "neighbourhood_cleansed",
            "price",
            "reviews_per_month",
            "number_of_reviews",
            "review_scores_rating",
            "availability_365",
            "_source_file",
        ],
    )
    reviews_cols = selected_columns(
        reviews_path,
        ["listing_id", "review_id", "review_date", "comment_length", "has_comment", "_source_file"],
    )
    risk_cols = (
        selected_columns(
            risk_path,
            [
                "listing_id",
                "country",
                "market",
                "market_label",
                "risk_score",
                "trust_score",
                "risk_segment",
                "primary_risk_driver",
                "recommended_action",
            ],
        )
        if risk_path.exists()
        else []
    )

    listings = read_table(listings_path, columns=listings_cols)
    reviews = read_table(reviews_path, columns=reviews_cols)
    risk = read_table(risk_path, columns=risk_cols) if risk_cols else pd.DataFrame({"listing_id": listings["listing_id"]})

    data_validation_rows = [
        {
            "dataset": "listings",
            "path": listings_path.relative_to(ROOT).as_posix(),
            "rows": len(listings),
            "columns": ", ".join(listings.columns),
        },
        {
            "dataset": "reviews",
            "path": reviews_path.relative_to(ROOT).as_posix(),
            "rows": len(reviews),
            "columns": ", ".join(reviews.columns),
        },
        {
            "dataset": "listing_trust_risk",
            "path": risk_path.relative_to(ROOT).as_posix() if risk_path.exists() else "No disponible",
            "rows": len(risk),
            "columns": ", ".join(risk.columns),
        },
    ]
    if market_summary_path.exists():
        market_summary_existing = read_table(market_summary_path)
        data_validation_rows.append(
            {
                "dataset": "market_trust_risk_summary",
                "path": market_summary_path.relative_to(ROOT).as_posix(),
                "rows": len(market_summary_existing),
                "columns": ", ".join(market_summary_existing.columns),
            }
        )
    if risk_segment_summary_path.exists():
        risk_segment_summary_existing = read_table(risk_segment_summary_path)
        data_validation_rows.append(
            {
                "dataset": "risk_segment_summary",
                "path": risk_segment_summary_path.relative_to(ROOT).as_posix(),
                "rows": len(risk_segment_summary_existing),
                "columns": ", ".join(risk_segment_summary_existing.columns),
            }
        )
    tabla_validacion_datos = pd.DataFrame(data_validation_rows)
    tabla_validacion_datos.to_csv(OUTPUT_DIR / "tabla_validacion_datos.csv", index=False)

    reviews["review_date"] = pd.to_datetime(reviews["review_date"], errors="coerce")
    reviews = reviews.dropna(subset=["review_date", "listing_id"]).copy()
    reviews["year_month"] = reviews["review_date"].dt.to_period("M").astype(str)
    reviews_por_mes = (
        reviews.groupby("year_month")
        .agg(reviews=("listing_id", "size"), listings_con_review=("listing_id", "nunique"))
        .reset_index()
        .sort_values("year_month")
    )
    reviews_por_mes.to_csv(OUTPUT_DIR / "reviews_por_mes.csv", index=False)

    aggregation = {
        "observed_reviews": ("review_id", "count") if "review_id" in reviews.columns else ("listing_id", "size"),
        "first_review_date": ("review_date", "min"),
        "last_review_date": ("review_date", "max"),
    }
    if "comment_length" in reviews.columns:
        aggregation["avg_comment_length"] = ("comment_length", "mean")
    if "has_comment" in reviews.columns:
        aggregation["non_empty_review_count"] = ("has_comment", "sum")
    review_agg = reviews.groupby("listing_id").agg(**aggregation).reset_index()

    min_review_date = reviews["review_date"].min()
    max_review_date = reviews["review_date"].max()
    months_available = reviews["review_date"].dt.to_period("M").nunique()
    reference_date = max_review_date + pd.Timedelta(days=1)

    rfm = listings.merge(review_agg, on="listing_id", how="left")
    if "listing_id" in risk.columns:
        rfm = rfm.merge(risk.drop_duplicates("listing_id"), on="listing_id", how="left")

    rfm = infer_market_country(rfm, market_summary_path)
    if "country" in rfm.columns:
        before_country_filter = len(rfm)
        rfm = rfm[rfm["country"].isin(TARGET_COUNTRIES)].copy()
        country_filter_note = (
            f"Se filtro a los 5 paises objetivo: {before_country_filter:,} -> {len(rfm):,} listings."
        )
    else:
        country_filter_note = "No se encontro country; se conservaron todos los listings y se documento la brecha."

    rfm["observed_reviews"] = pd.to_numeric(rfm["observed_reviews"], errors="coerce").fillna(0).astype(int)
    rfm["first_review_date"] = pd.to_datetime(rfm["first_review_date"], errors="coerce")
    rfm["last_review_date"] = pd.to_datetime(rfm["last_review_date"], errors="coerce")
    no_reviews = rfm["observed_reviews"].eq(0) | rfm["last_review_date"].isna()
    recency_for_reviewed = (reference_date - rfm["last_review_date"]).dt.days
    max_recency_reviewed = recency_for_reviewed[~no_reviews].max()
    no_review_recency = int(max_recency_reviewed + 1) if pd.notna(max_recency_reviewed) else 9999
    rfm["recency_days"] = recency_for_reviewed.where(~no_reviews, no_review_recency).clip(lower=0)
    rfm["frequency"] = rfm["observed_reviews"].fillna(0).astype(int)

    rfm["price_clean"] = clean_numeric(rfm["price"]) if "price" in rfm.columns else np.nan
    rfm["price_missing_flag"] = rfm["price_clean"].isna() | rfm["price_clean"].le(0)
    positive_prices = rfm.loc[~rfm["price_missing_flag"], "price_clean"]
    price_p01 = positive_prices.quantile(0.01) if len(positive_prices) else np.nan
    price_p99 = positive_prices.quantile(0.99) if len(positive_prices) else np.nan
    rfm["price_outlier_flag"] = False
    if pd.notna(price_p99):
        rfm["price_outlier_flag"] = rfm["price_clean"].gt(price_p99)
        rfm["price_for_monetary"] = rfm["price_clean"].clip(lower=0, upper=price_p99)
    else:
        rfm["price_for_monetary"] = rfm["price_clean"]
    rfm.loc[rfm["price_missing_flag"], "price_for_monetary"] = 0

    rfm["monetary_proxy"] = (rfm["price_for_monetary"].fillna(0) * rfm["frequency"]).clip(lower=0)
    if "reviews_per_month" in rfm.columns:
        rfm["annual_value_proxy"] = (
            rfm["price_for_monetary"].fillna(0)
            * pd.to_numeric(rfm["reviews_per_month"], errors="coerce").fillna(0).clip(lower=0)
            * 12
        )
    else:
        rfm["annual_value_proxy"] = np.nan

    rfm["R_score"] = score_quantile(rfm["recency_days"], higher_is_better=False, force_low_mask=no_reviews)
    rfm["F_score"] = score_quantile(rfm["frequency"], higher_is_better=True, force_low_mask=rfm["frequency"].eq(0))
    rfm["M_score"] = score_quantile(
        rfm["monetary_proxy"], higher_is_better=True, force_low_mask=rfm["monetary_proxy"].eq(0)
    )
    rfm["rfm_total_score"] = rfm["R_score"] + rfm["F_score"] + rfm["M_score"]
    rfm["rfm_code"] = rfm["R_score"].astype(str) + rfm["F_score"].astype(str) + rfm["M_score"].astype(str)
    rfm["rfm_segment"] = assign_rfm_segment(rfm)
    rfm["rfm_level"] = assign_rfm_level(rfm["rfm_total_score"])

    if "risk_segment" not in rfm.columns:
        rfm["risk_segment"] = "Unknown"
    if "risk_score" not in rfm.columns:
        rfm["risk_score"] = np.nan
    rfm["high_critical_flag"] = rfm["risk_segment"].astype(str).isin(HIGH_RISK_SEGMENTS).astype(int)
    rfm["priority_segment"] = assign_priority_segment(rfm)

    action_map = {
        priority: action_for_priority(priority)
        for priority in [
            "Prioridad critica",
            "Proteger y retener",
            "Corregir antes de escalar",
            "Bajo valor pero riesgoso",
            "Monitoreo bajo",
        ]
    }
    rfm["priority_action"] = rfm["priority_segment"].map(action_map)

    if "country" not in rfm.columns:
        rfm["country"] = "No disponible"
    if "market_label" not in rfm.columns:
        rfm["market_label"] = rfm.get("market", "No disponible")

    output_cols = [
        column
        for column in [
            "listing_id",
            "country",
            "market_label",
            "room_type",
            "property_type",
            "price_clean",
            "price_for_monetary",
            "price_missing_flag",
            "price_outlier_flag",
            "observed_reviews",
            "first_review_date",
            "last_review_date",
            "avg_comment_length",
            "non_empty_review_count",
            "recency_days",
            "frequency",
            "monetary_proxy",
            "annual_value_proxy",
            "R_score",
            "F_score",
            "M_score",
            "rfm_total_score",
            "rfm_code",
            "rfm_segment",
            "rfm_level",
            "risk_score",
            "risk_segment",
            "high_critical_flag",
            "priority_segment",
            "priority_action",
            "primary_risk_driver",
            "recommended_action",
        ]
        if column in rfm.columns
    ]
    rfm_segments = rfm[output_cols].copy()
    rfm_segments.to_parquet(OUTPUT_DIR / "rfm_listing_segments.parquet", index=False)
    rfm_segments.to_csv(OUTPUT_DIR / "rfm_listing_segments.csv", index=False)

    tabla_rfm_general = pd.DataFrame(
        [
            {
                "total_listings": len(rfm),
                "listings_con_reviews": int(rfm["frequency"].gt(0).sum()),
                "reviews_procesadas": len(reviews),
                "min_review_date": min_review_date.date().isoformat(),
                "max_review_date": max_review_date.date().isoformat(),
                "reference_date": reference_date.date().isoformat(),
                "meses_disponibles": int(months_available),
                "promedio_recency": rfm["recency_days"].mean(),
                "promedio_frequency": rfm["frequency"].mean(),
                "promedio_monetary_proxy": rfm["monetary_proxy"].mean(),
                "price_missing_rate": rfm["price_missing_flag"].mean(),
                "price_outlier_rate": rfm["price_outlier_flag"].mean(),
            }
        ]
    )
    tabla_rfm_general.to_csv(OUTPUT_DIR / "tabla_rfm_general.csv", index=False)

    tabla_rfm_segmentos = (
        rfm.groupby("rfm_segment", dropna=False)
        .agg(
            cantidad_listings=("listing_id", "count"),
            recency_promedio=("recency_days", "mean"),
            frequency_promedio=("frequency", "mean"),
            monetary_proxy_promedio=("monetary_proxy", "mean"),
            rfm_promedio=("rfm_total_score", "mean"),
            risk_score_promedio=("risk_score", "mean"),
            high_critical_pct=("high_critical_flag", "mean"),
        )
        .reset_index()
    )
    tabla_rfm_segmentos["porcentaje"] = tabla_rfm_segmentos["cantidad_listings"] / len(rfm)
    tabla_rfm_segmentos["high_critical_pct"] = format_pct(tabla_rfm_segmentos["high_critical_pct"])
    tabla_rfm_segmentos["porcentaje"] = format_pct(tabla_rfm_segmentos["porcentaje"])
    tabla_rfm_segmentos = tabla_rfm_segmentos.sort_values("cantidad_listings", ascending=False)
    tabla_rfm_segmentos.to_csv(OUTPUT_DIR / "tabla_rfm_segmentos.csv", index=False)

    market_group = ["country", "market_label"]
    market_agg = (
        rfm.groupby(market_group, dropna=False)
        .agg(
            listings=("listing_id", "count"),
            segmento_dominante=("rfm_segment", dominant_segment),
            rfm_promedio=("rfm_total_score", "mean"),
            risk_score_promedio=("risk_score", "mean"),
            high_critical_pct=("high_critical_flag", "mean"),
            monetary_proxy_promedio=("monetary_proxy", "mean"),
            prioridad_critica=("priority_segment", lambda s: (s == "Prioridad critica").sum()),
        )
        .reset_index()
    )
    market_agg["high_critical_pct"] = format_pct(market_agg["high_critical_pct"])
    tabla_rfm_mercado = market_agg.sort_values(["rfm_promedio", "listings"], ascending=[False, False])
    tabla_rfm_mercado.to_csv(OUTPUT_DIR / "tabla_rfm_mercado.csv", index=False)

    tabla_prioridad_accion = (
        rfm.groupby("priority_segment", dropna=False)
        .agg(cantidad=("listing_id", "count"))
        .reset_index()
        .sort_values("cantidad", ascending=False)
    )
    all_priorities = pd.DataFrame(
        {
            "priority_segment": [
                "Prioridad critica",
                "Proteger y retener",
                "Corregir antes de escalar",
                "Monitoreo bajo",
                "Bajo valor pero riesgoso",
            ]
        }
    )
    tabla_prioridad_accion = all_priorities.merge(tabla_prioridad_accion, on="priority_segment", how="left")
    tabla_prioridad_accion["cantidad"] = tabla_prioridad_accion["cantidad"].fillna(0).astype(int)
    tabla_prioridad_accion["porcentaje"] = format_pct(tabla_prioridad_accion["cantidad"] / len(rfm))
    tabla_prioridad_accion["accion_recomendada"] = tabla_prioridad_accion["priority_segment"].map(action_map)
    tabla_prioridad_accion = tabla_prioridad_accion.sort_values("cantidad", ascending=False)
    tabla_prioridad_accion.to_csv(OUTPUT_DIR / "tabla_prioridad_accion.csv", index=False)

    plt.figure(figsize=(13, 5))
    monthly_plot = reviews_por_mes.copy()
    monthly_plot["date"] = pd.to_datetime(monthly_plot["year_month"] + "-01")
    sns.lineplot(data=monthly_plot, x="date", y="reviews", color="#2f6f73", linewidth=2)
    plt.title("Reviews por mes - proxy de actividad Airbnb")
    plt.xlabel("Mes")
    plt.ylabel("Cantidad de reviews")
    save_plot(OUTPUT_DIR / "reviews_por_mes.png")

    plt.figure(figsize=(11, 6))
    order = tabla_rfm_segmentos["rfm_segment"].tolist()
    ax = sns.countplot(data=rfm, y="rfm_segment", order=order, color="#3b5b92")
    ax.bar_label(ax.containers[0], fmt="%d")
    plt.title("Distribucion de segmentos RFM")
    plt.xlabel("Listings")
    plt.ylabel("Segmento RFM")
    save_plot(OUTPUT_DIR / "distribucion_segmentos_rfm.png")

    plt.figure(figsize=(11, 6))
    sample = rfm.sample(min(40000, len(rfm)), random_state=42)
    sns.scatterplot(
        data=sample,
        x="rfm_total_score",
        y="risk_score",
        hue="rfm_level",
        alpha=0.35,
        s=18,
        palette={"Alto": "#2f6f73", "Medio": "#d39c3f", "Bajo": "#7b7f87"},
    )
    plt.title("RFM total score vs risk_score")
    plt.xlabel("RFM total score")
    plt.ylabel("Risk score Trust & Safety")
    plt.legend(title="Nivel RFM", bbox_to_anchor=(1.02, 1), loc="upper left")
    save_plot(OUTPUT_DIR / "rfm_vs_risk_score.png")

    top_market_risk = (
        rfm[rfm["priority_segment"].eq("Prioridad critica")]
        .groupby(["country", "market_label"], dropna=False)
        .agg(listings_prioridad_critica=("listing_id", "count"), monetary_proxy_promedio=("monetary_proxy", "mean"))
        .reset_index()
        .sort_values("listings_prioridad_critica", ascending=False)
        .head(10)
    )
    if top_market_risk.empty:
        top_market_risk = (
            rfm[rfm["high_critical_flag"].eq(1)]
            .groupby(["country", "market_label"], dropna=False)
            .agg(listings_prioridad_critica=("listing_id", "count"), monetary_proxy_promedio=("monetary_proxy", "mean"))
            .reset_index()
            .sort_values("listings_prioridad_critica", ascending=False)
            .head(10)
        )
    plt.figure(figsize=(11, 6))
    sns.barplot(data=top_market_risk, x="listings_prioridad_critica", y="market_label", hue="country", dodge=False)
    plt.title("Top mercados con alto valor RFM y riesgo Trust & Safety")
    plt.xlabel("Listings")
    plt.ylabel("Mercado")
    plt.legend(title="Pais", bbox_to_anchor=(1.02, 1), loc="upper left")
    save_plot(OUTPUT_DIR / "top_mercados_high_value_risk.png")

    rfm_high_risk_count = int(rfm["priority_segment"].eq("Prioridad critica").sum())
    rfm_high_count = int(rfm["rfm_level"].eq("Alto").sum())
    high_critical_count = int(rfm["high_critical_flag"].sum())

    table_segment_md = tabla_rfm_segmentos[
        [
            "rfm_segment",
            "cantidad_listings",
            "porcentaje",
            "recency_promedio",
            "frequency_promedio",
            "monetary_proxy_promedio",
            "risk_score_promedio",
            "high_critical_pct",
        ]
    ].copy()
    table_market_md = tabla_rfm_mercado[
        [
            "country",
            "market_label",
            "listings",
            "segmento_dominante",
            "rfm_promedio",
            "risk_score_promedio",
            "high_critical_pct",
        ]
    ].copy()
    table_priority_md = tabla_prioridad_accion.copy()

    summary_lines = [
        "# TB4 - Resultados para pegar: RFM Airbnb Trust & Safety",
        "",
        "## 1. Rango temporal y datos procesados",
        "",
        f"- Rango temporal de reviews: {min_review_date.date().isoformat()} a {max_review_date.date().isoformat()}.",
        f"- Fecha de corte RFM: {reference_date.date().isoformat()} = max(review_date) + 1 dia.",
        f"- Meses disponibles: {months_available}.",
        f"- Reviews procesadas: {len(reviews):,}.",
        f"- Listings procesados en los 5 paises objetivo: {len(rfm):,}.",
        f"- Listings con al menos una review: {int(rfm['frequency'].gt(0).sum()):,}.",
        f"- {country_filter_note}",
        "",
        "## 2. Definicion RFM usada",
        "",
        "- Recency: dias desde la ultima review observada hasta la fecha de corte. Menor recency implica actividad mas reciente.",
        "- Frequency: cantidad de reviews observadas por listing. Se usa como proxy operativo de actividad posterior a reserva.",
        "- Monetary proxy: `price * observed_reviews`. Es un proxy monetario, no ingreso real ni revenue de Airbnb.",
        "- Annual value proxy: `price * reviews_per_month * 12` cuando `reviews_per_month` esta disponible.",
        "- Los scores R, F y M van de 1 a 5. En R, menor recency recibe mayor score. En F y M, mayor valor recibe mayor score.",
        "",
        "## 3. Tabla de segmentos RFM",
        "",
        markdown_table(table_segment_md),
        "",
        "## 4. Tabla de mercados",
        "",
        markdown_table(table_market_md),
        "",
        "## 5. Tabla de prioridad de accion",
        "",
        markdown_table(table_priority_md),
        "",
        "## 6. Interpretacion ejecutiva",
        "",
        f"- Se identificaron {rfm_high_count:,} listings con nivel RFM alto. Estos listings combinan actividad reciente, frecuencia y valor monetario proxy.",
        f"- Se identificaron {high_critical_count:,} listings en segmentos Trust & Safety High/Critical.",
        f"- El cruce RFM x riesgo produce {rfm_high_risk_count:,} listings de `Prioridad critica`: alto valor/actividad proxy y riesgo alto.",
        "- Los listings de `Proteger y retener` son relevantes para crecimiento, pero deben mantenerse monitoreados para evitar deterioro de calidad.",
        "- Los listings de `Corregir antes de escalar` no deberian recibir mayor exposicion comercial hasta resolver senales de confianza o calidad.",
        "",
        "## 7. Limitaciones",
        "",
        "- El repositorio no contiene reservas, pagos, comisiones ni disputas reales.",
        "- Las reviews se usan como proxy de actividad posterior a reserva.",
        "- `monetary_proxy` no debe llamarse ingreso real; solo aproxima valor potencial observable.",
        "- `risk_score` y `risk_segment` son proxies analiticos del proyecto, no evidencia de disputas internas reales de Airbnb.",
        "- Los precios provienen de mercados con monedas distintas; el proxy monetario no esta normalizado por tipo de cambio.",
        "- No se afirma reduccion de disputas porque no existe una tabla de disputas reales.",
        "",
        "## 8. Recomendaciones de negocio",
        "",
        "- Priorizar `Prioridad critica` para revision Trust & Safety antes de acciones de crecimiento.",
        "- Usar `Proteger y retener` para mantener oferta de alto valor proxy con riesgo bajo o moderado.",
        "- Usar `Corregir antes de escalar` para activar acciones de mejora de calidad, verificacion o contenido.",
        "- Usar la tabla de mercado para asignar capacidad operativa por pais y mercado.",
        "- Integrar el RFM como complemento del modelo de riesgo de TB3 en el dashboard de confianza/riesgo.",
    ]
    (OUTPUT_DIR / "resultados_para_pegar_tb4.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print("\n=== TABLA RFM GENERAL ===")
    print(tabla_rfm_general.to_string(index=False))
    print("\n=== TABLA RFM SEGMENTOS ===")
    print(tabla_rfm_segmentos.to_string(index=False))
    print("\n=== TABLA RFM MERCADO ===")
    print(tabla_rfm_mercado.to_string(index=False))
    print("\n=== TABLA PRIORIDAD ACCION ===")
    print(tabla_prioridad_accion.to_string(index=False))
    print("\nArchivos generados en:", OUTPUT_DIR.relative_to(ROOT))


if __name__ == "__main__":
    main()
