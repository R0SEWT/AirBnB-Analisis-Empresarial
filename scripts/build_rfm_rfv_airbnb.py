from pathlib import Path
import textwrap

import nbformat as nbf
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "notebooks" / "RFM_RFV_Airbnb_Quispe_Fernando.ipynb"


def md(text: str):
    return nbf.v4.new_markdown_cell(textwrap.dedent(text).strip())


def code(text: str):
    return nbf.v4.new_code_cell(textwrap.dedent(text).strip())


cells = [
    md(
        """
        # Analisis RFM y RFV - Airbnb

        Este notebook desarrolla una segmentacion RFM y RFV para el proyecto Airbnb. Dado que el repositorio no contiene reservas reales, gasto de huespedes ni transacciones, el analisis se construye como proxy a nivel de `listing_id` usando las senales disponibles:

        - **Recency / Recencia:** dias desde la ultima review observada.
        - **Frequency / Frecuencia:** cantidad de reviews observadas.
        - **Monetary / Monetario:** proxy `precio x reviews observadas`.
        - **Value / Valor:** proxy de valor/confianza combinando `trust_score` y rating.

        La interpretacion debe mantenerse academica y empresarial: los resultados ayudan a priorizar listings para crecimiento, reactivacion o gestion de confianza, pero no sustituyen datos internos de reservas, ingresos o disputas reales.
        """
    ),
    code(
        """
        from pathlib import Path
        import os
        import warnings

        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
        import seaborn as sns

        warnings.filterwarnings("ignore", category=FutureWarning)
        pd.set_option("display.max_columns", 80)

        RANDOM_STATE = 42
        sns.set_theme(style="whitegrid", context="notebook")
        plt.rcParams["figure.figsize"] = (11, 6)
        plt.rcParams["axes.titlesize"] = 13
        plt.rcParams["axes.labelsize"] = 11

        def find_project_root(start=None):
            start = Path.cwd() if start is None else Path(start)
            for candidate in [start, *start.parents]:
                if (candidate / "data").exists() and (candidate / "pyproject.toml").exists():
                    return candidate
            return start

        PROJECT_ROOT = find_project_root()
        os.chdir(PROJECT_ROOT)

        DATA_DIR = PROJECT_ROOT / "data"
        OUTPUT_DIR = PROJECT_ROOT / "outputs"
        FIG_DIR = OUTPUT_DIR / "figures"
        for directory in [OUTPUT_DIR, FIG_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

        print(f"Proyecto: {PROJECT_ROOT}")
        """
    ),
    md(
        """
        ## 1. Comprension del negocio

        En Airbnb, una segmentacion RFM/RFV puede apoyar decisiones de:

        - **Trust & Safety:** identificar listings activos pero con baja confianza para revision preventiva.
        - **Operaciones:** priorizar mercados con alta actividad y alto valor potencial.
        - **Producto:** detectar listings confiables con baja traccion para acciones de mejora o reactivacion.
        - **Revenue/Growth:** ubicar listings con mayor proxy comercial.

        La unidad de analisis sera `listing_id`, no huesped, porque los datos disponibles del proyecto estan modelados principalmente a nivel de anuncio.
        """
    ),
    md(
        """
        ## 2. Comprension de los datos

        Se prioriza el mart `data/gold/analytics/listing_trust_risk.parquet` porque ya integra listings, reviews observadas, riesgo y confianza. Si no existiera, el notebook usa `data/gold/listings.parquet` y agrega `data/gold/reviews.parquet`.
        """
    ),
    code(
        """
        def read_table(path: Path, columns=None):
            suffix = "".join(path.suffixes).lower()
            if suffix.endswith(".parquet"):
                return pd.read_parquet(path, columns=columns)
            if suffix.endswith(".csv") or suffix.endswith(".csv.gz"):
                return pd.read_csv(path, usecols=columns)
            raise ValueError(f"Formato no soportado: {path}")

        risk_path = DATA_DIR / "gold" / "analytics" / "listing_trust_risk.parquet"
        listings_path = DATA_DIR / "gold" / "listings.parquet"
        reviews_path = DATA_DIR / "gold" / "reviews.parquet"

        if risk_path.exists():
            base = read_table(risk_path)
            source_description = risk_path.relative_to(PROJECT_ROOT).as_posix()
        elif listings_path.exists():
            base = read_table(listings_path)
            source_description = listings_path.relative_to(PROJECT_ROOT).as_posix()
        else:
            raise FileNotFoundError("No se encontro data/gold/analytics/listing_trust_risk.parquet ni data/gold/listings.parquet")

        print("Fuente base:", source_description)
        print("Shape base:", base.shape)
        display(base.head(3))
        display(pd.DataFrame({"dtype": base.dtypes.astype(str), "nulos": base.isna().sum(), "nulos_pct": base.isna().mean().round(4)}).sort_values("nulos_pct", ascending=False).head(20))
        """
    ),
    code(
        """
        if "observed_reviews" not in base.columns or "last_observed_review_date" not in base.columns:
            if not reviews_path.exists():
                raise FileNotFoundError("Se requieren reviews para calcular frecuencia/recencia y no se encontro data/gold/reviews.parquet")
            reviews = read_table(reviews_path, columns=["listing_id", "review_date"])
            reviews["review_date"] = pd.to_datetime(reviews["review_date"], errors="coerce")
            review_agg = (
                reviews.dropna(subset=["listing_id"])
                .groupby("listing_id")
                .agg(
                    observed_reviews=("review_date", "size"),
                    last_observed_review_date=("review_date", "max"),
                )
                .reset_index()
            )
            base = base.merge(review_agg, on="listing_id", how="left")

        date_source = pd.to_datetime(base.get("last_observed_review_date"), errors="coerce")
        if date_source.notna().any():
            analysis_date = date_source.max()
        elif "last_scraped" in base.columns:
            analysis_date = pd.to_datetime(base["last_scraped"], errors="coerce").max()
        else:
            analysis_date = pd.Timestamp.today().normalize()

        print("Fecha de corte analitica:", analysis_date.date())
        """
    ),
    md(
        """
        ## 3. Preparacion de datos

        Se limpian precios, se imputan valores faltantes con medianas razonables por mercado/tipo de habitacion y se construyen las variables base de RFM/RFV. La imputacion solo se usa para calcular proxies, no para crear resultados financieros reales.
        """
    ),
    code(
        """
        def numeric_series(series):
            if series is None:
                return pd.Series(np.nan, index=base.index)
            if pd.api.types.is_numeric_dtype(series):
                return pd.to_numeric(series, errors="coerce")
            cleaned = series.astype(str).str.replace(r"[$,%]", "", regex=True).str.replace(",", "", regex=False)
            return pd.to_numeric(cleaned, errors="coerce")

        df = base.copy()
        df["last_review_date_rfm"] = pd.to_datetime(df["last_observed_review_date"], errors="coerce")
        df["recency_days"] = (analysis_date - df["last_review_date_rfm"]).dt.days
        df["recency_days"] = df["recency_days"].where(df["recency_days"].notna(), 9999)
        df["recency_days"] = df["recency_days"].clip(lower=0)

        df["frequency_reviews"] = numeric_series(df.get("observed_reviews")).fillna(0).clip(lower=0)

        df["price_clean"] = numeric_series(df.get("price"))
        group_cols = [c for c in ["market_label", "room_type"] if c in df.columns]
        if group_cols and df["price_clean"].notna().any():
            df["price_imputed"] = df["price_clean"]
            df["price_imputed"] = df["price_imputed"].fillna(df.groupby(group_cols)["price_clean"].transform("median"))
            if "room_type" in df.columns:
                df["price_imputed"] = df["price_imputed"].fillna(df.groupby("room_type")["price_clean"].transform("median"))
            df["price_imputed"] = df["price_imputed"].fillna(df["price_clean"].median())
        else:
            df["price_imputed"] = df["price_clean"].fillna(df["price_clean"].median())

        df["monetary_proxy"] = (df["price_imputed"].fillna(0) * df["frequency_reviews"]).clip(lower=0)

        rating = numeric_series(df.get("review_scores_rating"))
        df["rating_100"] = np.where(rating <= 5, rating * 20, rating)
        df["rating_100"] = pd.Series(df["rating_100"], index=df.index).clip(lower=0, upper=100)

        trust = numeric_series(df.get("trust_score"))
        if trust.notna().any():
            df["value_proxy"] = 0.6 * trust + 0.4 * df["rating_100"]
            df["value_proxy"] = df["value_proxy"].fillna(trust).fillna(df["rating_100"])
        else:
            df["value_proxy"] = df["rating_100"]
        df["value_proxy"] = df["value_proxy"].fillna(df["value_proxy"].median()).clip(lower=0, upper=100)

        if "risk_segment" in df.columns:
            df["is_high_risk_proxy"] = df["risk_segment"].astype(str).isin(["High", "Critical"]).astype(int)
        else:
            df["is_high_risk_proxy"] = np.nan

        selected_cols = [
            c for c in [
                "listing_id", "country", "market_label", "room_type", "property_type", "risk_segment",
                "recency_days", "frequency_reviews", "price_imputed", "monetary_proxy",
                "review_scores_rating", "trust_score", "value_proxy", "is_high_risk_proxy",
            ]
            if c in df.columns
        ]
        display(df[selected_cols].head(5))
        display(df[["recency_days", "frequency_reviews", "price_imputed", "monetary_proxy", "value_proxy"]].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9, 0.99]).T)
        """
    ),
    md(
        """
        ## 4. Scoring RFM y RFV

        Cada componente se puntua de 1 a 5 por percentiles:

        - Recency: menor cantidad de dias desde la ultima review recibe mayor score.
        - Frequency: mayor cantidad de reviews recibe mayor score.
        - Monetary: mayor proxy `precio x reviews` recibe mayor score.
        - Value: mayor proxy de confianza/calidad recibe mayor score.
        """
    ),
    code(
        """
        def percentile_score(series, higher_is_better=True):
            s = pd.to_numeric(series, errors="coerce")
            score = pd.Series(1, index=s.index, dtype="int64")
            valid = s.notna()
            if valid.sum() == 0:
                return score
            pct = s[valid].rank(method="average", pct=True, ascending=higher_is_better)
            score.loc[valid] = np.ceil(pct * 5).clip(1, 5).astype(int)
            return score

        def classify_total(score, kind):
            if kind == "rfm":
                labels = {
                    "champions": "Champions comerciales",
                    "high": "Activos de alto potencial",
                    "mid": "Intermedios",
                    "low": "Baja traccion",
                    "critical": "Inactivos o sin evidencia",
                }
            else:
                labels = {
                    "champions": "Confiables y activos",
                    "high": "Valiosos a potenciar",
                    "mid": "Monitoreo selectivo",
                    "low": "Riesgo operativo medio",
                    "critical": "Baja confianza o baja actividad",
                }
            return np.select(
                [score >= 13, score >= 10, score >= 7, score >= 4],
                [labels["champions"], labels["high"], labels["mid"], labels["low"]],
                default=labels["critical"],
            )

        df["r_score"] = percentile_score(df["recency_days"], higher_is_better=False)
        df["f_score"] = percentile_score(df["frequency_reviews"], higher_is_better=True)
        df["m_score"] = percentile_score(df["monetary_proxy"], higher_is_better=True)
        df["v_score"] = percentile_score(df["value_proxy"], higher_is_better=True)

        df["rfm_score"] = df["r_score"] + df["f_score"] + df["m_score"]
        df["rfv_score"] = df["r_score"] + df["f_score"] + df["v_score"]
        df["rfm_code"] = df["r_score"].astype(str) + df["f_score"].astype(str) + df["m_score"].astype(str)
        df["rfv_code"] = df["r_score"].astype(str) + df["f_score"].astype(str) + df["v_score"].astype(str)

        df["rfm_segment"] = classify_total(df["rfm_score"], "rfm")
        df["rfv_segment"] = classify_total(df["rfv_score"], "rfv")

        conditions = [
            (df["rfm_score"] >= 10) & (df["rfv_score"] >= 10),
            (df["rfm_score"] >= 10) & (df["rfv_score"] < 10),
            (df["rfm_score"] < 10) & (df["rfv_score"] >= 10),
        ]
        choices = [
            "Mantener y proteger",
            "Alto potencial comercial con riesgo de confianza",
            "Reactivar demanda de listings confiables",
        ]
        df["rfm_rfv_action"] = np.select(conditions, choices, default="Depurar, corregir o monitorear")

        score_cols = [
            "listing_id", "country", "market_label", "room_type", "property_type", "risk_segment",
            "recency_days", "frequency_reviews", "price_imputed", "monetary_proxy", "value_proxy",
            "r_score", "f_score", "m_score", "v_score", "rfm_score", "rfv_score",
            "rfm_code", "rfv_code", "rfm_segment", "rfv_segment", "rfm_rfv_action",
        ]
        score_cols = [c for c in score_cols if c in df.columns]
        display(df[score_cols].head(10))
        """
    ),
    md(
        """
        ## 5. Resultados

        Se generan tablas de resumen por segmento y mercado. Estas tablas son las principales salidas para incorporar al documento o dashboard del proyecto.
        """
    ),
    code(
        """
        def segment_summary(segment_col):
            summary = (
                df.groupby(segment_col, dropna=False)
                .agg(
                    listings=("listing_id", "count"),
                    avg_recency_days=("recency_days", "mean"),
                    avg_frequency_reviews=("frequency_reviews", "mean"),
                    avg_price=("price_imputed", "mean"),
                    avg_monetary_proxy=("monetary_proxy", "mean"),
                    avg_value_proxy=("value_proxy", "mean"),
                    high_risk_rate=("is_high_risk_proxy", "mean"),
                )
                .reset_index()
            )
            summary["listings_pct"] = summary["listings"] / summary["listings"].sum()
            return summary.sort_values("listings", ascending=False)

        rfm_summary = segment_summary("rfm_segment")
        rfv_summary = segment_summary("rfv_segment")

        market_group_cols = [c for c in ["country", "market_label"] if c in df.columns]
        market_summary = (
            df.groupby(market_group_cols, dropna=False)
            .agg(
                listings=("listing_id", "count"),
                avg_rfm_score=("rfm_score", "mean"),
                avg_rfv_score=("rfv_score", "mean"),
                avg_recency_days=("recency_days", "mean"),
                avg_frequency_reviews=("frequency_reviews", "mean"),
                avg_monetary_proxy=("monetary_proxy", "mean"),
                avg_value_proxy=("value_proxy", "mean"),
                high_risk_rate=("is_high_risk_proxy", "mean"),
                maintain_and_protect=("rfm_rfv_action", lambda s: (s == "Mantener y proteger").sum()),
                commercial_risk=("rfm_rfv_action", lambda s: (s == "Alto potencial comercial con riesgo de confianza").sum()),
                reliable_reactivation=("rfm_rfv_action", lambda s: (s == "Reactivar demanda de listings confiables").sum()),
            )
            .reset_index()
            .sort_values("avg_rfv_score", ascending=False)
        )

        scores_path = OUTPUT_DIR / "rfm_rfv_listing_scores.csv"
        rfm_summary_path = OUTPUT_DIR / "rfm_segment_summary.csv"
        rfv_summary_path = OUTPUT_DIR / "rfv_segment_summary.csv"
        market_summary_path = OUTPUT_DIR / "rfm_rfv_market_summary.csv"

        df[score_cols].to_csv(scores_path, index=False)
        rfm_summary.to_csv(rfm_summary_path, index=False)
        rfv_summary.to_csv(rfv_summary_path, index=False)
        market_summary.to_csv(market_summary_path, index=False)

        print("Archivos guardados:")
        for path in [scores_path, rfm_summary_path, rfv_summary_path, market_summary_path]:
            print("-", path.relative_to(PROJECT_ROOT))

        display(rfm_summary)
        display(rfv_summary)
        display(market_summary)
        """
    ),
    md(
        """
        ## 6. Visualizaciones

        Los graficos se exportan a `outputs/figures/` para reutilizarlos en el informe o dashboard.
        """
    ),
    code(
        """
        def save_fig(filename):
            path = FIG_DIR / filename
            plt.tight_layout()
            plt.savefig(path, dpi=160, bbox_inches="tight")
            print(f"Figura guardada: {path.relative_to(PROJECT_ROOT)}")

        plt.figure(figsize=(10, 5))
        order = rfm_summary["rfm_segment"].tolist()
        ax = sns.countplot(data=df, y="rfm_segment", order=order, color="#2f6f73")
        ax.bar_label(ax.containers[0], fmt="%d")
        plt.title("Distribucion de segmentos RFM")
        plt.xlabel("Listings")
        plt.ylabel("Segmento RFM")
        save_fig("rfm_segment_distribution.png")
        plt.show()

        plt.figure(figsize=(10, 5))
        order = rfv_summary["rfv_segment"].tolist()
        ax = sns.countplot(data=df, y="rfv_segment", order=order, color="#3b5b92")
        ax.bar_label(ax.containers[0], fmt="%d")
        plt.title("Distribucion de segmentos RFV")
        plt.xlabel("Listings")
        plt.ylabel("Segmento RFV")
        save_fig("rfv_segment_distribution.png")
        plt.show()

        matrix = pd.crosstab(df["rfm_segment"], df["rfv_segment"])
        plt.figure(figsize=(12, 7))
        sns.heatmap(matrix, annot=True, fmt="d", cmap="YlGnBu")
        plt.title("Matriz de segmentos RFM vs RFV")
        plt.xlabel("Segmento RFV")
        plt.ylabel("Segmento RFM")
        save_fig("rfm_rfv_matrix.png")
        plt.show()

        sample = df.sample(min(len(df), 25000), random_state=RANDOM_STATE)
        plt.figure(figsize=(11, 6))
        sns.scatterplot(
            data=sample,
            x=np.log1p(sample["frequency_reviews"]),
            y=np.log1p(sample["monetary_proxy"]),
            hue="rfv_segment",
            alpha=0.35,
            s=18,
        )
        plt.title("Frecuencia vs proxy monetario por segmento RFV")
        plt.xlabel("log(1 + reviews)")
        plt.ylabel("log(1 + precio x reviews)")
        plt.legend(title="RFV", bbox_to_anchor=(1.02, 1), loc="upper left")
        save_fig("rfm_rfv_frequency_monetary_scatter.png")
        plt.show()

        top_market = market_summary.sort_values("commercial_risk", ascending=False).head(10)
        label_col = "market_label" if "market_label" in top_market.columns else market_group_cols[0]
        plt.figure(figsize=(11, 5))
        sns.barplot(data=top_market, x="commercial_risk", y=label_col, color="#b84a4a")
        plt.title("Mercados con mas listings de alto potencial comercial y riesgo de confianza")
        plt.xlabel("Listings")
        plt.ylabel("Mercado")
        save_fig("rfm_rfv_market_commercial_risk.png")
        plt.show()
        """
    ),
    md(
        """
        ## 7. Interpretacion e implementacion

        La combinacion RFM/RFV permite separar decisiones comerciales de decisiones de confianza. Un listing puede tener alta traccion comercial, pero baja confianza operacional; ese caso es prioritario para corregir antes de escalar demanda. Tambien puede ocurrir lo contrario: listings confiables con poca actividad, buenos candidatos para reactivacion o mejora de visibilidad.
        """
    ),
    code(
        """
        total_listings = len(df)
        action_summary = (
            df["rfm_rfv_action"]
            .value_counts()
            .rename_axis("accion")
            .reset_index(name="listings")
        )
        action_summary["listings_pct"] = action_summary["listings"] / total_listings
        display(action_summary)

        top_rfm = rfm_summary.iloc[0]
        top_rfv = rfv_summary.iloc[0]
        top_action = action_summary.iloc[0]

        best_market = market_summary.sort_values("avg_rfv_score", ascending=False).iloc[0]
        risk_market = market_summary.sort_values("commercial_risk", ascending=False).iloc[0]

        summary_lines = [
            "# Resumen RFM/RFV - Airbnb",
            "",
            "## Alcance",
            "",
            f"- Unidad de analisis: `listing_id`.",
            f"- Fuente principal: `{source_description}`.",
            f"- Fecha de corte analitica: {analysis_date.date().isoformat()}.",
            "- RFM usa recencia, frecuencia y un proxy monetario `precio x reviews`.",
            "- RFV usa recencia, frecuencia y un proxy de valor/confianza basado en `trust_score` y rating.",
            "- No existen reservas ni gasto real en el repositorio; por tanto, RFM/RFV se presentan como proxies academicos y operativos.",
            "",
            "## Hallazgos principales",
            "",
            f"- Total de listings segmentados: {total_listings:,}.",
            f"- Segmento RFM mas numeroso: {top_rfm['rfm_segment']} ({int(top_rfm['listings']):,} listings; {top_rfm['listings_pct']:.2%}).",
            f"- Segmento RFV mas numeroso: {top_rfv['rfv_segment']} ({int(top_rfv['listings']):,} listings; {top_rfv['listings_pct']:.2%}).",
            f"- Accion operativa mas frecuente: {top_action['accion']} ({int(top_action['listings']):,} listings; {top_action['listings_pct']:.2%}).",
            f"- Mercado con mayor RFV promedio: {best_market.get('market_label', 'N/D')} ({best_market.get('country', 'N/D')}) con RFV promedio {best_market['avg_rfv_score']:.2f}.",
            f"- Mercado con mas listings de alto potencial comercial y riesgo de confianza: {risk_market.get('market_label', 'N/D')} ({risk_market.get('country', 'N/D')}) con {int(risk_market['commercial_risk']):,} listings.",
            "",
            "## Uso recomendado",
            "",
            "- `Mantener y proteger`: listings con buena traccion y buen valor/confianza; monitoreo y retencion.",
            "- `Alto potencial comercial con riesgo de confianza`: prioridad para Trust & Safety y mejora de calidad antes de impulsar demanda.",
            "- `Reactivar demanda de listings confiables`: candidatos para campanas, visibilidad, soporte a hosts o revision de precio.",
            "- `Depurar, corregir o monitorear`: baja traccion y bajo valor/confianza; evaluar completitud, disponibilidad y calidad minima.",
            "",
            "## Limitaciones",
            "",
            "- Reviews se usan como proxy de reservas/actividad.",
            "- Precio por noche se usa como proxy monetario; no representa ingreso real ni comisiones.",
            "- `trust_score` y `risk_segment` son proxies del proyecto, no disputas internas reales.",
        ]
        summary = "\\n".join(summary_lines) + "\\n"
        summary_path = OUTPUT_DIR / "rfm_rfv_resumen_resultados.md"
        summary_path.write_text(summary, encoding="utf-8")
        print(f"Resumen guardado: {summary_path.relative_to(PROJECT_ROOT)}")
        print(summary)
        """
    ),
]


def main():
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    nb = nbf.v4.new_notebook()
    nb["cells"] = cells
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    }
    nbf.write(nb, NOTEBOOK_PATH)

    client = NotebookClient(
        nb,
        timeout=1800,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
    )
    client.execute()
    nbf.write(nb, NOTEBOOK_PATH)
    print(f"Notebook ejecutado: {NOTEBOOK_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
