import numpy as np
from scipy.sparse import csr_matrix

from src.experiments.lima.review_segments import auto_label_clusters, clean_text


def test_clean_text_strips_html():
    assert "<br/>" not in clean_text("great place<br/>loved it")
    assert "<b>" not in clean_text("<b>nice</b> host")


def test_clean_text_lowercase():
    result = clean_text("AMAZING Location")
    assert result == result.lower()


def test_clean_text_removes_numbers():
    result = clean_text("great stay 10/10")
    assert "10" not in result


def test_auto_label_returns_nonempty_string():
    vocab = np.array(["clean", "great", "noise", "location", "host"])
    X = csr_matrix(
        np.array(
            [
                [0.8, 0.7, 0.1, 0.2, 0.3],
                [0.9, 0.6, 0.1, 0.1, 0.4],
                [0.1, 0.1, 0.9, 0.8, 0.2],
            ]
        )
    )
    labels = np.array([0, 0, 1])
    result = auto_label_clusters(X, labels, vocab, n_terms=2)
    assert isinstance(result[0], str) and len(result[0]) > 0
    assert isinstance(result[1], str) and len(result[1]) > 0
    assert " / " in result[0]
