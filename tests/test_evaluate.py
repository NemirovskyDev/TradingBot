import pandas as pd

from tradingbot.backtest import BacktestResult
from tradingbot.config import CostConfig, RiskConfig
from tradingbot.evaluate import PromotionCriteria, Verdict, evaluate_strategy, judge
from tradingbot.strategies import sma_cross

CRIT = PromotionCriteria(min_trades=30, max_drawdown=0.25)


def _res(sharpe=1.0, dd=0.10, n=40, ret=0.20):
    eq = pd.Series([1.0, 1.0 + ret], name="equity")
    return BacktestResult(eq, pd.DataFrame(), {"total_return": ret, "max_drawdown": dd, "sharpe": sharpe, "n_trades": float(n)}, [])


def test_passes_when_all_criteria_met():
    v = judge(_res(), _res(sharpe=0.5), _res(ret=0.05), CRIT)
    assert v.passed and v.reasons == []


def test_fails_with_too_few_trades():
    v = judge(_res(n=5), _res(sharpe=0.5), _res(), CRIT)
    assert not v.passed and any("operações" in r for r in v.reasons)


def test_fails_when_drawdown_exceeds_limit():
    v = judge(_res(dd=0.40), _res(sharpe=0.5), _res(), CRIT)
    assert not v.passed and any("queda" in r for r in v.reasons)


def test_fails_when_not_better_than_buy_and_hold():
    v = judge(_res(sharpe=0.3), _res(sharpe=0.5), _res(), CRIT)
    assert not v.passed and any("comprar e segurar" in r for r in v.reasons)


def test_fails_when_negative_under_double_costs():
    v = judge(_res(), _res(sharpe=0.5), _res(ret=-0.02), CRIT)
    assert not v.passed and any("custo" in r for r in v.reasons)


def test_reason_numbers_use_decimal_comma():
    v = judge(_res(sharpe=0.3, dd=0.4), _res(sharpe=0.5), _res(), CRIT)
    text = " ".join(v.reasons)
    assert "0,30 contra 0,50" in text and "40,0%" in text and "25%" in text


def test_reports_every_failed_criterion():
    v = judge(_res(sharpe=0.1, dd=0.9, n=1), _res(sharpe=0.5), _res(ret=-0.1), CRIT)
    assert len(v.reasons) == 4


def test_evaluate_strategy_returns_verdict_on_synthetic_data(synthetic_prices):
    prices = synthetic_prices(500, 4)
    v = evaluate_strategy(prices, lambda p: sma_cross(p, 5, 20), CRIT, RiskConfig(), CostConfig())
    assert isinstance(v, Verdict) and isinstance(v.passed, bool)
    assert v.reasons or v.passed


def test_evaluate_strategy_short_history_returns_failed_verdict(synthetic_prices):
    v = evaluate_strategy(synthetic_prices(2, 1), sma_cross, CRIT, RiskConfig(), CostConfig())
    assert not v.passed and v.reasons
