import numpy as np
import pandas as pd
import pytest


def _synthetic(n: int = 300, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.01, n)))
    open_ = np.concatenate([[100.0], close[:-1]])
    spread = np.abs(rng.normal(0, 0.004, n)) * close
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - spread
    index = pd.bdate_range("2020-01-01", periods=n)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": 1_000_000.0},
        index=index,
    )


@pytest.fixture
def synthetic_prices():
    """Fábrica de preços diários sintéticos e determinísticos: synthetic_prices(n, seed)."""
    return _synthetic
