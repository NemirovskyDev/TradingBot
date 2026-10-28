import numpy as np
import pandas as pd
import pytest

from tradingbot.data import DataError, get_prices


def _raw(n=10, caps=True):
    idx = pd.bdate_range("2024-01-01", periods=n)
    cols = ["Open", "High", "Low", "Close", "Volume"] if caps else ["open", "high", "low", "close", "volume"]
    df = pd.DataFrame(np.arange(n * 5, dtype=float).reshape(n, 5) + 1, index=idx, columns=cols)
    return df


def test_get_prices_normalizes_columns(tmp_path):
    df = get_prices("spy", "2024-01-01", "2024-02-01", cache_dir=tmp_path, fetch=lambda t, s, e: _raw())
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.index.is_monotonic_increasing


def test_get_prices_handles_multiindex_columns(tmp_path):
    raw = _raw()
    raw.columns = pd.MultiIndex.from_product([raw.columns, ["SPY"]])
    df = get_prices("SPY", "2024-01-01", "2024-02-01", cache_dir=tmp_path, fetch=lambda t, s, e: raw)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]


def test_get_prices_uses_cache_second_call(tmp_path):
    calls = []

    def fetch(t, s, e):
        calls.append(t)
        return _raw()

    first = get_prices("SPY", "2024-01-01", "2024-02-01", cache_dir=tmp_path, fetch=fetch)
    second = get_prices("SPY", "2024-01-01", "2024-02-01", cache_dir=tmp_path, fetch=fetch)
    assert len(calls) == 1
    pd.testing.assert_frame_equal(first, second, check_freq=False)


def test_get_prices_empty_raises_data_error(tmp_path):
    with pytest.raises(DataError):
        get_prices("ZZZZ", "2024-01-01", "2024-02-01", cache_dir=tmp_path, fetch=lambda t, s, e: pd.DataFrame())


def test_get_prices_drops_nan_close(tmp_path):
    raw = _raw()
    raw.iloc[3, raw.columns.get_loc("Close")] = np.nan
    df = get_prices("SPY", "2024-01-01", "2024-02-01", cache_dir=tmp_path, fetch=lambda t, s, e: raw)
    assert len(df) == 9 and df["close"].notna().all()


@pytest.mark.parametrize("bad", ["", "../x", "A B", "A" * 30])
def test_get_prices_rejects_unsafe_ticker(tmp_path, bad):
    with pytest.raises(DataError):
        get_prices(bad, "2024-01-01", "2024-02-01", cache_dir=tmp_path, fetch=lambda t, s, e: _raw())


def test_get_prices_fetch_failure_becomes_data_error(tmp_path):
    def boom(t, s, e):
        raise ConnectionError("sem rede")

    with pytest.raises(DataError):
        get_prices("SPY", "2024-01-01", "2024-02-01", cache_dir=tmp_path, fetch=boom)


def test_get_prices_drops_rows_with_nan_ohlc(tmp_path):
    raw = _raw()
    raw.iloc[2, raw.columns.get_loc("Open")] = np.nan
    raw.iloc[4, raw.columns.get_loc("Low")] = np.nan
    df = get_prices("SPY", "2024-01-01", "2024-02-01", cache_dir=tmp_path, fetch=lambda t, s, e: raw)
    assert len(df) == 8 and df[["open", "high", "low", "close"]].notna().all().all()


@pytest.mark.parametrize("bad", ["x/../../evil", "2024-13-01", "", "2024-01-01\n"])
def test_get_prices_rejects_bad_dates(tmp_path, bad):
    with pytest.raises(DataError):
        get_prices("SPY", bad, "2024-02-01", cache_dir=tmp_path, fetch=lambda t, s, e: _raw())
    with pytest.raises(DataError):
        get_prices("SPY", "2024-01-01", bad, cache_dir=tmp_path, fetch=lambda t, s, e: _raw())


def test_get_prices_rejects_ticker_with_trailing_newline(tmp_path):
    with pytest.raises(DataError):
        get_prices("AAPL\n", "2024-01-01", "2024-02-01", cache_dir=tmp_path, fetch=lambda t, s, e: _raw())
