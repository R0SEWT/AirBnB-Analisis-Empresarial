from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.ingestion.raw_discovery import RawDatasetFiles
from src.transformations.common import ensure_parent, read_csv_gz

BRONZE_METADATA_COLUMNS = ["_source_file", "_loaded_at_utc"]
REVIEW_RAW_COLUMNS = ["listing_id", "id", "date", "reviewer_id", "reviewer_name", "comments"]


def build_bronze_listings(raw_files: RawDatasetFiles, output_path: Path) -> int:
    """Load all raw listings files and persist a structurally standardized bronze table."""
    frames = []
    loaded_at = datetime.now(UTC).isoformat()

    for path in raw_files.listings:
        frame = read_csv_gz(path)
        frame["_source_file"] = path.name
        frame["_loaded_at_utc"] = loaded_at
        frames.append(frame)

    bronze = pd.concat(frames, ignore_index=True, sort=False)
    ensure_parent(output_path)
    bronze.to_parquet(output_path, index=False)
    return len(bronze)


def build_bronze_reviews(
    raw_files: RawDatasetFiles,
    output_path: Path,
    chunk_size: int = 100_000,
) -> int:
    """Load raw reviews in chunks and persist a bronze parquet file."""
    ensure_parent(output_path)
    loaded_at = datetime.now(UTC).isoformat()
    schema = pa.schema([(column, pa.string()) for column in REVIEW_RAW_COLUMNS + BRONZE_METADATA_COLUMNS])
    writer: pq.ParquetWriter | None = None
    rows = 0

    try:
        for path in raw_files.reviews:
            for chunk in pd.read_csv(
                path,
                compression="gzip",
                dtype=str,
                chunksize=chunk_size,
                low_memory=False,
            ):
                chunk = chunk.reindex(columns=REVIEW_RAW_COLUMNS)
                chunk["_source_file"] = path.name
                chunk["_loaded_at_utc"] = loaded_at
                table = pa.Table.from_pandas(chunk, schema=schema, preserve_index=False)
                if writer is None:
                    writer = pq.ParquetWriter(output_path, schema=schema, compression="snappy")
                writer.write_table(table)
                rows += len(chunk)
    finally:
        if writer is not None:
            writer.close()

    return rows

