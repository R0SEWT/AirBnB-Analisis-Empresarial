# Architecture Grounding

## Purpose

This file contains the stable technical grounding for the Airbnb analytics project.

Beads tracks live work. This document defines the project architecture and analytical conventions that should remain relatively stable across sessions.

## Repository Layers

Expected repository structure:

```text
.
├── app/
├── configs/
├── data/
│   ├── raw/
│   ├── bronze/
│   ├── silver/
│   └── gold/
├── dashboards/
├── docs/
├── notebooks/
├── reports/
├── src/
├── tests/
├── README.md
└── CLAUDE.md
```

## Medallion Architecture

Use a medallion architecture:

```text
raw → bronze → silver → gold
```

Layer meanings:

| Layer | Meaning |
|---|---|
| `raw` | Original files, exports, downloaded datasets. Never manually edited. |
| `bronze` | Structurally standardized data: stable format, basic typing, minimal cleaning. |
| `silver` | Clean analytical entities: normalized listings, hosts, bookings, reviews, markets. |
| `gold` | Business-ready analytical tables for dashboards, models, and reports. |

Do not commit large data files. Keep only `.gitkeep`, documentation, schemas, and small samples when needed.

Suggested `.gitignore` rules:

```gitignore
data/raw/*
data/bronze/*
data/silver/*
data/gold/*

!data/raw/.gitkeep
!data/bronze/.gitkeep
!data/silver/.gitkeep
!data/gold/.gitkeep
!data/README.md

models/*.pkl
models/*.joblib
models/*.pt
mlruns/
wandb/
__pycache__/
.ipynb_checkpoints/
```

## Analytical Pipeline

The project pipeline should follow:

```text
ingest → transform → features → model → dashboard → report
```

Suggested mapping:

| Stage | Folder | Purpose |
|---|---|---|
| ingest | `src/ingestion/` | Acquire or load raw data. |
| transform | `src/transformations/` | Build bronze and silver layers. |
| features | `src/features/` | Build model/dashboard features. |
| model | `src/models/` | Train tentative predictive models. |
| evaluation | `src/evaluation/` | Evaluate models, risks, and assumptions. |
| dashboard | `src/visualization/` and `dashboards/` | Prepare dashboard-ready outputs. |
| report | `reports/` | Academic deliverables and figures. |

## Tentative Gold Schema

A business-ready star schema may include:

```text
fact_bookings
fact_disputes
fact_reviews
fact_revenue
dim_listing
dim_host
dim_location
dim_date
```

Possible analytical marts:

```text
mart_listing_quality
mart_marketplace_health
mart_host_performance
mart_trust_and_safety
features_listing_risk
```

## Analytical Maturity

Classify initiatives using this sequence:

```text
descriptive → diagnostic → predictive → prescriptive
```

| Level | Question | Airbnb Use |
|---|---|---|
| Descriptive | What is happening? | Monitor listings, bookings, disputes, reviews, cancellations, revenue. |
| Diagnostic | Why is it happening? | Identify drivers of bad reviews, disputes, cancellations, host churn, or demand drops. |
| Predictive | What will likely happen? | Predict risky listings, dispute probability, low-quality hosts, churn, or booking probability. |
| Prescriptive | What should be done? | Recommend verification, host coaching, ranking adjustment, pricing action, or support escalation. |

## Business Anchors

Analytical work should support at least one of these business needs:

- trust and safety,
- listing quality,
- host alignment,
- guest experience,
- regulatory readiness,
- marketplace liquidity,
- revenue optimization,
- international expansion.

## Modeling Principles

Prefer strong baselines before complex models.

Model ladder:

```text
logistic regression → random forest → gradient boosting → tabular + text embeddings → ensemble
```

Evaluation should match the task:

| Task | Metrics |
|---|---|
| Classification | precision, recall, F1, ROC-AUC, PR-AUC |
| Risk ranking | lift@k, precision@k, recall@k |
| Forecasting | MAE, RMSE, MAPE |
| Dashboard | clarity, actionability, business relevance |
| Prescriptive action | uplift, cost-benefit, A/B test impact |

For risk and trust models, prioritize:

```text
precision@k
recall@k
false_positive_rate
segment_fairness
model_drift
calibration
```

Do not claim model performance without actual evaluation.

## Visualization Case

Preferred dashboard theme:

> Marketplace Trust & Listing Quality Dashboard

Core sections:

1. Executive KPIs.
2. Dispute and cancellation trends.
3. Listing quality by market.
4. Host risk segmentation.
5. Geographic concentration.
6. Recommended interventions.

Potential KPIs:

```text
total_bookings
active_listings
average_rating
dispute_rate
severe_dispute_rate
cancellation_rate
host_response_rate
avg_resolution_time
high_risk_listing_count
revenue_at_risk
```

A dashboard must end with business recommendations, not only visualizations.

## Report Alignment

Reports should connect strategy and analytics.

For TB2, the mandatory sections are:

1. Business model.
2. Business Model Canvas.
3. Enterprise architecture.
4. Data repository and analytical initiative classification.
5. Visualization use case and business recommendations.

Use formal academic Spanish in reports.

Avoid vague claims such as:

```text
usar IA para mejorar la empresa
implementar big data
el modelo será muy eficiente
```

Prefer concrete claims such as:

```text
se propone un modelo de clasificación binaria para estimar la probabilidad de disputa grave a nivel de listing
la capa gold consolida tablas de hechos y dimensiones orientadas a consumo analítico
la analítica prescriptiva traduce el score de riesgo en acciones operativas
```
