import numpy as np
import pandas as pd
import pytest

from tradingbot.strategies import REASONS, STRATEGIES, donchian, momentum, sma_cross


def _trend(n=120, slope=1.0):
    idx = pd.bdate_range("2021-01-01", periods=n)
    close = 100 + slope * np.arange(n, dtype=float)
    return pd.DataFrame({"open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 1e6}, index=idx)


def test_every_strategy_has_entry_and_exit_reason():
    assert set(STRATEGIES) == {"sma_cross", "donchian", "momentum"}
    for name in STRATEGIES:
        assert REASONS[name]["entry"] and REASONS[name]["exit"]


def test_sma_cross_long_when_fast_above_slow():
    sig = sma_cross(_trend(120, 1.0), fast=5, slow=20)
    assert sig.iloc[-1] == 1


def test_sma_cross_flat_during_warmup():
    sig = sma_cross(_trend(120, 1.0), fast=5, slow=20)
    assert (sig.iloc[:19] == 0).all()


def test_sma_cross_flat_in_downtrend():
    assert sma_cross(_trend(120, -0.5), fast=5, slow=20).iloc[-1] == 0


def test_donchian_buys_breakout_then_exits_on_low():
    close = np.concatenate([np.full(70, 100.0), np.linspace(100, 130, 20), np.linspace(130, 80, 30)])
    idx = pd.bdate_range("2021-01-01", periods=len(close))
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1e6}, index=idx)
    sig = donchian(df, entry=55, exit_=20)
    assert sig.iloc[:60].eq(0).all()  # sem histórico para a janela de 55 dias
    assert sig.iloc[75] == 1  # rompeu a máxima de 55 dias
    assert sig.iloc[-1] == 0  # caiu abaixo da mínima de 20 dias


def test_momentum_long_when_return_positive():
    assert momentum(_trend(120, 1.0), lookback=20).iloc[-1] == 1
    assert momentum(_trend(120, -0.5), lookback=20).iloc[-1] == 0


@pytest.mark.parametrize("name", ["sma_cross", "donchian", "momentum"])
def test_strategies_short_history_all_zero(name):
    sig = STRATEGIES[name](_trend(30, 1.0))
    assert len(sig) == 30 and (sig == 0).all()


@pytest.mark.parametrize("name", ["sma_cross", "donchian", "momentum"])
def test_signal_has_no_lookahead(name, synthetic_prices):
    prices = synthetic_prices(200, 3)
    base = STRATEGIES[name](prices)
    changed = prices.copy()
    changed.iloc[-1, changed.columns.get_loc("close")] *= 3
    after = STRATEGIES[name](changed)
    pd.testing.assert_series_equal(base.iloc[:-1], after.iloc[:-1])


@pytest.mark.parametrize("name", ["sma_cross", "donchian", "momentum"])
def test_signals_are_int_zero_or_one(name, synthetic_prices):
    sig = STRATEGIES[name](synthetic_prices(200, 1))
    assert set(sig.unique()) <= {0, 1}
