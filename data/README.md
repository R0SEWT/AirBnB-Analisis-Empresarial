# Data Directory

This project follows a medallion architecture:

```text
raw → bronze → silver → gold
```

Large data files should not be committed. Keep only `.gitkeep`, schemas, dictionaries, and small samples when necessary.

## Raw input convention

Place Airbnb files in `data/raw` using these names:

```text
listings*.csv.gz
reviews*.csv.gz
```

Then run:

```bash
python -m src.pipeline.run_medallion
```

The gold datasets are generated in:

```text
data/gold/listings.parquet
data/gold/reviews.parquet
```
