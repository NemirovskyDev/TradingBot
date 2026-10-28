import pytest

from tradingbot.config import RiskConfig
from tradingbot.risk import Order, PortfolioState, Position, RiskRejected, atr_stop, check_order, position_size

CFG = RiskConfig()


def _state(positions=None, equity=10_000.0, week_start=10_000.0):
    return PortfolioState(equity=equity, positions=positions or {}, week_start_equity=week_start)


def _buy(**kw):
    base = dict(ticker="SPY", side="buy", qty=10, entry=100.0, stop=95.0, sector="etf")
    base.update(kw)
    return Order(**base)


def test_position_size_one_percent_risk():
    assert position_size(10_000, 100, 95, CFG) == 20  # 100 de risco / 5 por ação


def test_position_size_capped_by_max_position_pct():
    assert position_size(10_000, 100, 99.5, CFG) == 20  # risco pediria 200; teto de 20% = 20 ações


def test_position_size_rejects_stop_at_or_above_entry():
    for stop in (100, 101):
        with pytest.raises(RiskRejected):
            position_size(10_000, 100, stop, CFG)


def test_small_capital_gives_zero_qty():
    assert position_size(50, 100, 95, CFG) == 0


def test_check_order_accepts_valid_buy():
    check_order(_buy(), _state(), CFG)


def test_check_order_rejects_missing_stop():
    with pytest.raises(RiskRejected, match="stop"):
        check_order(_buy(stop=None), _state(), CFG)


def test_check_order_rejects_nonpositive_qty():
    with pytest.raises(RiskRejected):
        check_order(_buy(qty=0), _state(), CFG)


def test_check_order_rejects_when_max_positions_reached():
    pos = {f"T{i}": Position(f"T{i}", 1, 10.0, "x") for i in range(CFG.max_open_positions)}
    with pytest.raises(RiskRejected, match="posições"):
        check_order(_buy(), _state(pos), CFG)


def test_check_order_rejects_position_over_asset_limit():
    with pytest.raises(RiskRejected, match="ativo"):
        check_order(_buy(qty=30), _state(), CFG)  # 3000 > 20% de 10000


def test_check_order_rejects_sector_over_limit():
    pos = {"QQQ": Position("QQQ", 19, 100.0, "tech"), "XLK": Position("XLK", 19, 100.0, "tech")}
    with pytest.raises(RiskRejected, match="setor"):
        check_order(_buy(sector="tech", qty=10), _state(pos), CFG)


def test_check_order_rejects_after_weekly_loss_limit():
    with pytest.raises(RiskRejected, match="semana"):
        check_order(_buy(), _state(equity=9_400.0), CFG)


def test_sell_always_passes():
    check_order(_buy(side="sell", stop=None), _state(equity=1_000.0), CFG)


def test_atr_stop_is_below_close(synthetic_prices):
    prices = synthetic_prices(100, 2)
    stop = atr_stop(prices, 50)
    assert 0 < stop < prices["close"].iloc[50]


def test_atr_stop_handles_first_bar(synthetic_prices):
    prices = synthetic_prices(10, 2)
    assert atr_stop(prices, 0) < prices["close"].iloc[0]


@pytest.mark.parametrize("stop", [float("nan"), -5.0, 0.0])
def test_check_order_rejects_nan_or_nonpositive_stop(stop):
    with pytest.raises(RiskRejected):
        check_order(_buy(stop=stop), _state(), CFG)


@pytest.mark.parametrize("kw", [{"entry": float("nan")}, {"entry": 0.0}, {"qty": float("nan")}, {"qty": 2.5}])
def test_check_order_rejects_invalid_entry_or_qty(kw):
    with pytest.raises(RiskRejected):
        check_order(_buy(**kw), _state(), CFG)


def test_position_size_rejects_nan_inputs():
    with pytest.raises(RiskRejected):
        position_size(10_000, float("nan"), 95, CFG)
    with pytest.raises(RiskRejected):
        position_size(10_000, 100, float("nan"), CFG)
