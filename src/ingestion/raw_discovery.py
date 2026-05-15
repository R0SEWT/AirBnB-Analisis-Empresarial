from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RawDatasetFiles:
    listings: list[Path]
    reviews: list[Path]

    def ensure_required(self) -> None:
        missing = []
        if not self.listings:
            missing.append("listings*.csv.gz")
        if not self.reviews:
            missing.append("reviews*.csv.gz")
        if missing:
            expected = ", ".join(missing)
            raise FileNotFoundError(f"No raw files found for: {expected}")


def discover_raw_files(raw_dir: Path) -> RawDatasetFiles:
    """Find raw Airbnb files using the naming convention in data/raw."""
    raw_dir = Path(raw_dir)
    listings = sorted(raw_dir.glob("listings*.csv.gz"))
    reviews = sorted(raw_dir.glob("reviews*.csv.gz"))
    return RawDatasetFiles(listings=listings, reviews=reviews)

