import pandas as pd

from src.transformations.silver import run_silver


def _make_bronze(prices, ratings=None, neighbourhoods=None):
    n = len(prices)
    return pd.DataFrame(
        {
            "id": range(n),
            "name": [f"listing_{i}" for i in range(n)],
            "host_id": range(n),
            "neighbourhood_cleansed": neighbourhoods or (["miraflores"] * n),
            "room_type": ["Entire home/apt"] * n,
            "price": prices,
            "minimum_nights": [1] * n,
            "number_of_reviews": [10] * n,
            "review_scores_rating": ratings or ([4.5] * n),
            "availability_365": [200] * n,
            "calculated_host_listings_count": [1] * n,
        }
    )


def test_silver_removes_zero_price():
    df = _make_bronze([0.0, 50.0, 100.0])
    result = run_silver(df)
    assert (result["price"] > 0).all()


def test_silver_removes_duplicates():
    df = _make_bronze([50.0, 50.0, 50.0])
    df["id"] = [1, 1, 2]
    result = run_silver(df)
    assert len(result) == 2


def test_silver_imputes_rating():
    ratings = [4.5, None, 4.0]
    df = _make_bronze([50.0, 60.0, 70.0], ratings=ratings)
    result = run_silver(df)
    assert result["review_scores_rating"].isna().sum() == 0
