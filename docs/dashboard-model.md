# Dashboard y modelo estrella

El dashboard consume los datasets gold separados:

```text
data/gold/listings.parquet
data/gold/reviews.parquet
```

Antes de visualizar, se construye un modelo estrella BI-ready en:

```text
data/gold/star/
```

## Modelo estrella

```mermaid
erDiagram
    dim_listing ||--o{ fact_listing_snapshot : listing_id
    dim_listing ||--o{ fact_reviews : listing_id
    dim_host ||--o{ fact_listing_snapshot : host_id
    dim_location ||--o{ fact_listing_snapshot : location_key
    dim_date ||--o{ fact_listing_snapshot : last_scraped_date_key
    dim_date ||--o{ fact_reviews : review_date_key

    dim_listing {
        int listing_id PK
        string name
        string property_type
        string room_type
    }

    dim_host {
        int host_id PK
        string host_name
        boolean host_is_superhost
        boolean host_identity_verified
    }

    dim_location {
        int location_key PK
        string neighbourhood
        string neighbourhood_cleansed
        string neighbourhood_group_cleansed
    }

    dim_date {
        int date_key PK
        date date
        int year
        int quarter
        int month
        string year_month
    }

    fact_listing_snapshot {
        int listing_id FK
        int host_id FK
        int location_key FK
        int last_scraped_date_key FK
        float price
        int availability_365
        float review_scores_rating
    }

    fact_reviews {
        int review_id PK
        int listing_id FK
        int review_date_key FK
        int reviewer_id
        int comment_length
        boolean has_comment
    }
```

## Construccion

```bash
python -m src.pipeline.build_star_schema
```

Luego generar el dashboard:

```bash
python -m src.dashboard.airbnb_dashboard
```

Generar la vista visual del modelo estrella:

```bash
python -m src.dashboard.star_schema_view
```

Salida:

```text
dashboards/airbnb_quality_dashboard.html
dashboards/star_schema_view.html
```

## Escalabilidad a BI

Las tablas en `data/gold/star/` pueden importarse directamente a Power BI, Tableau o Looker Studio:

- `dim_listing.parquet`
- `dim_host.parquet`
- `dim_location.parquet`
- `dim_date.parquet`
- `fact_listing_snapshot.parquet`
- `fact_reviews.parquet`

Para herramientas que no lean Parquet directamente, se puede agregar export CSV sin cambiar el contrato conceptual del modelo.
