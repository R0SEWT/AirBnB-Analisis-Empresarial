# Dashboards

Build the BI star schema:

```bash
python -m src.pipeline.build_star_schema
```

Generate the local dashboard:

```bash
python -m src.dashboard.airbnb_dashboard
```

Generate the schema view:

```bash
python -m src.dashboard.star_schema_view
```

Open:

```text
dashboards/airbnb_quality_dashboard.html
dashboards/star_schema_view.html
```

The HTML dashboard is a practical local equivalent of a Power BI/Tableau/Looker report. Its source tables are modeled as facts and dimensions in `data/gold/star/`.

Build trust/risk analytics marts:

```bash
python -m src.pipeline.build_trust_risk_analytics
```

Generate the trust/risk dashboard:

```bash
python -m src.dashboard.trust_risk_dashboard
```

Open:

```text
dashboards/trust_risk_dashboard.html
```
