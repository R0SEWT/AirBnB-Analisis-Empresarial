import pandas as pd
import pytest

from src.experiments.lima.bronze import _parse_price


def test_parse_price_strips_symbol():
    s = pd.Series(["$100.00", "$1,250.50", "$0.00", ""])
    result = _parse_price(s)
    assert result[0] == pytest.approx(100.0)
    assert result[1] == pytest.approx(1250.50)
    assert result[2] == pytest.approx(0.0)
    assert pd.isna(result[3])


def test_parse_price_already_numeric():
    s = pd.Series(["75", "200"])
    result = _parse_price(s)
    assert result[0] == pytest.approx(75.0)
    assert result[1] == pytest.approx(200.0)
