import numpy as np
import pandas as pd
import pytest

from tradingbot.backtest import buy_and_hold, run_backtest, split_train_test, walk_forward_windows
from tradingbot.config import CostConfig, RiskConfig
from tradingbot.strategies import sma_cross

RISK = RiskConfig()
FREE = CostConfig(commission=0.0, slippage_bps=0.0)


def _flat(n=20, price=100.0):
    idx = pd.bdate_range("2022-01-03", periods=n)
    return pd.DataFrame(
        {"open": price, "high": price + 1, "low": price - 1, "close": price, "volume": 1e6}, index=idx
    )


def _signals(prices, start):
    s = pd.Series(0, index=prices.index)
    s.iloc[start:] = 1
    return s


def test_signal_executes_next_open():
    prices = _flat()
    prices.iloc[6, prices.columns.get_loc("open")] = 103.0
    res = run_backtest(prices, _signals(prices, 5), RISK, FREE)
    trade = res.trades.iloc[0]
    assert trade["entry_date"] == prices.index[6]
    assert trade["entry_price"] == pytest.approx(103.0)


def test_slippage_worsens_entry_price():
    prices = _flat()
    res = run_backtest(prices, _signals(prices, 5), RISK, CostConfig(commission=0.0, slippage_bps=100.0))
    assert res.trades.iloc[0]["entry_price"] == pytest.approx(101.0)  # 1% acima da abertura de 100


def test_no_signals_equals_flat_equity():
    prices = _flat()
    res = run_backtest(prices, pd.Series(0, index=prices.index), RISK, FREE, initial_capital=10_000)
    assert (res.equity == 10_000).all()
    assert res.metrics["n_trades"] == 0 and len(res.trades) == 0


def test_stop_triggers_exit_at_stop_price():
    prices = _flat()
    prices.iloc[8, prices.columns.get_loc("low")] = 90.0
    res = run_backtest(prices, _signals(prices, 5), RISK, FREE)
    trade = res.trades.iloc[0]
    assert trade["exit_kind"] == "stop"
    assert trade["exit_price"] == pytest.approx(96.0)  # fechamento 100 menos 2 x ATR 2
    assert trade["pnl_pct"] < 0


def test_no_reentry_right_after_stop_while_signal_stays_on():
    prices = _flat(30)
    prices.iloc[8, prices.columns.get_loc("low")] = 90.0
    res = run_backtest(prices, _signals(prices, 5), RISK, FREE)
    assert len(res.trades) == 1


def test_signal_off_exits_at_next_open():
    prices = _flat()
    sig = pd.Series(0, index=prices.index)
    sig.iloc[5:10] = 1
    res = run_backtest(prices, sig, RISK, FREE)
    trade = res.trades.iloc[0]
    # primeiro sinal 0 no dia 10: a saída acontece na abertura do dia seguinte
    assert trade["exit_kind"] == "signal" and trade["exit_date"] == prices.index[11]


def test_position_open_at_end_is_closed_with_end_kind():
    prices = _flat()
    res = run_backtest(prices, _signals(prices, 5), RISK, FREE)
    assert res.trades.iloc[-1]["exit_kind"] == "end"


def test_trades_have_exit_kind_and_columns():
    prices = _flat()
    res = run_backtest(prices, _signals(prices, 5), RISK, FREE)
    assert list(res.trades.columns) == [
        "entry_date", "entry_price", "exit_date", "exit_price", "qty", "stop", "pnl_pct", "exit_kind",
    ]
    assert set(res.trades["exit_kind"]) <= {"stop", "signal", "end"}


def test_zero_size_entry_is_recorded_as_blocked():
    prices = _flat()
    res = run_backtest(prices, _signals(prices, 5), RISK, FREE, initial_capital=50)
    assert len(res.trades) == 0
    assert res.blocked and set(res.blocked[0]) == {"date", "reason"}


def test_costs_reduce_return(synthetic_prices):
    prices = synthetic_prices(400, 5)
    sig = sma_cross(prices, fast=5, slow=20)
    cheap = run_backtest(prices, sig, RISK, FREE)
    dear = run_backtest(prices, sig, RISK, CostConfig(commission=5.0, slippage_bps=50.0))
    assert cheap.metrics["n_trades"] > 0
    assert dear.metrics["total_return"] < cheap.metrics["total_return"]


def test_mismatched_signal_index_raises():
    prices = _flat()
    with pytest.raises(ValueError):
        run_backtest(prices, pd.Series(1, index=prices.index[:-1]), RISK, FREE)


def test_metrics_drawdown_is_positive_fraction(synthetic_prices):
    prices = synthetic_prices(400, 5)
    res = run_backtest(prices, sma_cross(prices, 5, 20), RISK, FREE)
    assert 0 <= res.metrics["max_drawdown"] < 1
    assert np.isfinite(res.metrics["sharpe"])


def test_buy_and_hold_matches_price_ratio(synthetic_prices):
    prices = synthetic_prices(100, 1)
    res = buy_and_hold(prices, 10_000)
    assert res.metrics["total_return"] == pytest.approx(prices["close"].iloc[-1] / prices["close"].iloc[0] - 1)


def test_split_train_test_is_chronological(synthetic_prices):
    prices = synthetic_prices(100, 1)
    train, test = split_train_test(prices, 0.3)
    assert len(train) == 70 and len(test) == 30
    assert train.index.max() < test.index.min()


def test_split_train_test_rejects_bad_fraction(synthetic_prices):
    with pytest.raises(ValueError):
        split_train_test(synthetic_prices(100, 1), 1.5)


def test_walk_forward_windows_do_not_overlap_in_test(synthetic_prices):
    windows = walk_forward_windows(synthetic_prices(1000, 1), train_days=504, test_days=126)
    assert len(windows) == 3
    for train, test in windows:
        assert train.index.max() < test.index.min()
    tests = [set(t.index) for _, t in windows]
    assert all(a.isdisjoint(b) for i, a in enumerate(tests) for b in tests[i + 1 :])


def test_walk_forward_short_history_returns_empty_list(synthetic_prices):
    assert walk_forward_windows(synthetic_prices(100, 1)) == []
