# Dashboards

Build the BI star schema:

```bash
python -m src.pipeline.build_star_schema
```

Generate the local dashboard:

```bash
python -m src.dashboard.airbnb_dashboard
```

Open:

```text
dashboards/airbnb_quality_dashboard.html
```

The HTML dashboard is a practical local equivalent of a Power BI/Tableau/Looker report. Its source tables are modeled as facts and dimensions in `data/gold/star/`.

