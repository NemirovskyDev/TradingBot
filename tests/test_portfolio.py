import math

import numpy as np
import pandas as pd
import pytest

from tradingbot.portfolio import (
    ALL_PORTFOLIOS,
    METHODOLOGIES,
    PROFILE_PORTFOLIOS,
    breakout_target,
    REBALANCE_COST,
    annual_returns,
    drawdown,
    gem_target,
    ivy_target,
    metrics,
    own_start,
    period_ends,
    simulate,
)


def _frame(**cols):
    idx = pd.bdate_range("2020-01-01", periods=len(next(iter(cols.values()))))
    return pd.DataFrame({k: np.asarray(v, dtype=float) for k, v in cols.items()}, index=idx)


def _fixed(weights):
    return lambda _date, _history: weights


def test_buy_and_hold_when_no_rebalance_date():
    prices = _frame(A=[100, 110, 121], B=[100, 100, 100])
    eq = simulate(prices, _fixed({"A": 0.5, "B": 0.5}), set(), prices.index[0])
    assert eq.iloc[0] == pytest.approx(100.0)
    assert eq.iloc[-1] == pytest.approx(100 * (0.5 * 1.21 + 0.5))


def test_rebalance_restores_weights_and_charges_turnover_cost():
    prices = _frame(A=[100, 200, 200], B=[100, 100, 100])
    eq = simulate(prices, _fixed({"A": 0.5, "B": 0.5}), {prices.index[1]}, prices.index[0], cost=0.001)
    # antes: A=100 e B=50. Alvo 75/75 troca 50 no total, que custa 0,05
    assert eq.iloc[1] == pytest.approx(149.95)
    assert eq.iloc[2] == pytest.approx(149.95)


def test_default_cost_is_ten_basis_points():
    assert REBALANCE_COST == pytest.approx(0.001)


def test_weights_must_sum_to_one():
    prices = _frame(A=[100, 101], B=[100, 100])
    with pytest.raises(ValueError, match="soma"):
        simulate(prices, _fixed({"A": 0.5, "B": 0.4}), set(), prices.index[0])


def test_missing_price_for_a_weighted_asset_is_an_error():
    prices = _frame(A=[100, np.nan, 102], B=[100, 100, 100])
    with pytest.raises(ValueError, match="ausente"):
        simulate(prices, _fixed({"A": 0.5, "B": 0.5}), set(), prices.index[0])


def test_start_after_the_data_is_an_error():
    prices = _frame(A=[100, 101], B=[100, 100])
    with pytest.raises(ValueError, match="início"):
        simulate(prices, _fixed({"A": 1.0}), set(), pd.Timestamp("2030-01-01"))


def test_target_only_sees_history_up_to_the_date():
    prices = _frame(A=[100, 101, 102, 103], B=[100, 100, 100, 100])
    seen = []

    def spy(date, history):
        seen.append((date, history.index[-1]))
        return {"A": 1.0}

    simulate(prices, spy, {prices.index[2]}, prices.index[0])
    assert all(date == last for date, last in seen)


def test_period_ends_picks_last_trading_day_of_each_period():
    idx = pd.bdate_range("2020-11-01", "2021-02-28")
    yearly = period_ends(idx, "yearly")
    assert pd.Timestamp("2020-12-31") in yearly and pd.Timestamp("2021-02-26") in yearly
    monthly = period_ends(idx, "monthly")
    assert pd.Timestamp("2020-11-30") in monthly and pd.Timestamp("2021-01-29") in monthly
    with pytest.raises(ValueError):
        period_ends(idx, "weekly")


def test_drawdown_and_metrics():
    idx = pd.to_datetime(["2020-01-01", "2020-07-01", "2020-12-31", "2021-01-01"])
    eq = pd.Series([100.0, 120.0, 90.0, 135.0], index=idx)
    cash = pd.Series([1.0, 1.02, 1.04, 1.041], index=idx)
    dd = drawdown(eq)
    assert dd.min() == pytest.approx(90 / 120 - 1)
    m = metrics(eq, cash)
    assert m["max_drawdown"] == pytest.approx(-0.25)
    assert m["total_return"] == pytest.approx(0.35)
    years = (idx[-1] - idx[0]).days / 365.25
    assert m["cagr"] == pytest.approx(1.35 ** (1 / years) - 1)
    assert all(v is None or math.isfinite(v) for v in m.values())


def test_metrics_with_flat_equity_have_no_sharpe():
    idx = pd.bdate_range("2020-01-01", periods=10)
    eq = pd.Series(100.0, index=idx)
    m = metrics(eq, pd.Series(1.0, index=idx))
    assert m["volatility"] == 0 and m["sharpe"] is None


def test_sharpe_of_the_cash_series_itself_is_undefined():
    idx = pd.bdate_range("2020-01-01", periods=300)
    cash = pd.Series(np.cumprod(np.full(300, 1.0004)), index=idx)
    assert metrics(100 * cash / cash.iloc[0], cash)["sharpe"] is None


def test_annual_returns_flags_partial_years():
    idx = pd.bdate_range("2020-03-02", "2021-06-30")
    eq = pd.Series(np.linspace(100, 150, len(idx)), index=idx)
    rows = annual_returns(eq)
    assert [r["year"] for r in rows] == [2020, 2021]
    assert rows[0]["partial"] and rows[1]["partial"]
    assert rows[1]["return"] == pytest.approx(eq.iloc[-1] / eq[:"2020-12-31"].iloc[-1] - 1)


def _monthly(values):
    idx = pd.date_range("2018-01-31", periods=len(values), freq="ME")
    return pd.Series(np.asarray(values, dtype=float), index=idx)


def test_ivy_holds_asset_above_its_10_month_average_else_cash():
    up = _monthly(np.linspace(100, 160, 14))
    down = _monthly(np.linspace(160, 100, 14))
    history = pd.DataFrame({"UP": up, "DOWN": down})
    w = ivy_target(("UP", "DOWN"), "CDI")(history.index[-1], history)
    assert w == {"UP": 0.5, "DOWN": 0.0, "CDI": 0.5}


def test_ivy_goes_to_cash_without_enough_history():
    history = pd.DataFrame({"UP": _monthly(np.linspace(100, 110, 5))})
    assert ivy_target(("UP",), "CDI")(history.index[-1], history) == {"UP": 0.0, "CDI": 1.0}


def _gem_history(us, exus, bonds, cash):
    idx = pd.bdate_range("2019-01-01", periods=len(us))
    return pd.DataFrame({"US": us, "EXUS": exus, "BOND": bonds, "CDI": cash}, index=idx)


def test_gem_picks_us_when_it_beats_cash_and_ex_us():
    n = 300
    h = _gem_history(np.linspace(100, 160, n), np.linspace(100, 130, n), np.full(n, 100.0), np.linspace(1, 1.05, n))
    assert gem_target("US", "EXUS", "BOND", "CDI")(h.index[-1], h) == {"US": 1.0}


def test_gem_picks_ex_us_when_it_beats_us():
    n = 300
    h = _gem_history(np.linspace(100, 120, n), np.linspace(100, 170, n), np.full(n, 100.0), np.linspace(1, 1.05, n))
    assert gem_target("US", "EXUS", "BOND", "CDI")(h.index[-1], h) == {"EXUS": 1.0}


def test_gem_goes_to_bonds_when_us_does_not_beat_cash():
    n = 300
    h = _gem_history(np.linspace(100, 101, n), np.linspace(100, 170, n), np.full(n, 100.0), np.linspace(1, 1.10, n))
    assert gem_target("US", "EXUS", "BOND", "CDI")(h.index[-1], h) == {"BOND": 1.0}


def test_gem_without_12_months_of_history_stays_in_cash():
    h = _gem_history(np.linspace(100, 110, 50), np.linspace(100, 110, 50), np.full(50, 100.0), np.linspace(1, 1.01, 50))
    assert gem_target("US", "EXUS", "BOND", "CDI")(h.index[-1], h) == {"CDI": 1.0}


def test_registry_has_the_seven_methodologies_with_valid_weights():
    ids = [m.id for m in METHODOLOGIES]
    assert ids == ["arca", "permanente", "all-weather", "golden-butterfly", "sessenta-quarenta", "faber-ivy", "momentum-dual"]
    assert len(set(ids)) == len(ids)
    for m in METHODOLOGIES:
        assert m.name and m.author and m.summary and m.rule and m.rebalance in ("yearly", "monthly")
        if m.weights is not None:
            assert sum(w for _, w in m.weights) == pytest.approx(1.0)
            assert set(m.universe) == {k for k, _ in m.weights}
        assert "CDI" in m.universe or m.id in ("golden-butterfly", "sessenta-quarenta", "all-weather")


def test_rotation_methodologies_have_no_fixed_weights():
    tactical = {m.id: m for m in METHODOLOGIES}
    assert tactical["faber-ivy"].weights is None and tactical["momentum-dual"].weights is None
    assert tactical["faber-ivy"].rebalance == "monthly"


def test_arca_is_25_percent_in_each_quadrant():
    arca = next(m for m in METHODOLOGIES if m.id == "arca")
    assert dict(arca.weights) == {"BOVA11": 0.25, "FII": 0.25, "CDI": 0.25, "IVVB11": 0.25}
    assert arca.make_target()(pd.Timestamp("2020-01-01"), pd.DataFrame()) == dict(arca.weights)


def test_all_weather_matches_the_published_allocation():
    aw = dict(next(m for m in METHODOLOGIES if m.id == "all-weather").weights)
    assert aw == {"VTI": 0.30, "TLT": 0.40, "IEF": 0.15, "GLD": 0.075, "DBC": 0.075}


def _closes(**series):
    n = len(next(iter(series.values())))
    return pd.DataFrame({k: np.asarray(v, dtype=float) for k, v in series.items()}, index=pd.bdate_range("2020-01-01", periods=n))


def test_period_ends_daily_is_every_day():
    idx = pd.bdate_range("2020-01-01", periods=5)
    assert period_ends(idx, "daily") == set(idx)


def test_breakout_holds_an_asset_only_after_it_breaks_its_recent_high_and_leaves_below_the_low():
    up = np.concatenate([np.full(70, 100.0), np.linspace(100, 140, 20), np.linspace(140, 80, 30)])
    flat = np.full(len(up), 50.0)
    h = _closes(UP=up, FLAT=flat, CDI=np.cumprod(np.full(len(up), 1.0004)))
    target = breakout_target(("UP", "FLAT"), "CDI", entry=55, exit_=20)
    assert target(h.index[40], h.iloc[:41]) == {"UP": 0.0, "FLAT": 0.0, "CDI": 1.0}  # sem 55 dias de histórico
    assert target(h.index[80], h.iloc[:81]) == {"UP": 0.5, "FLAT": 0.0, "CDI": 0.5}  # rompeu a máxima
    assert target(h.index[-1], h) == {"UP": 0.0, "FLAT": 0.0, "CDI": 1.0}  # caiu abaixo da mínima de 20 dias


def test_breakout_is_incremental_and_matches_a_fresh_run_day_by_day():
    rng = np.random.default_rng(3)
    a = 100 * np.cumprod(1 + rng.normal(0.001, 0.02, 300))
    b = 100 * np.cumprod(1 + rng.normal(0.0, 0.02, 300))
    h = _closes(A=a, B=b, CDI=np.cumprod(np.full(300, 1.0004)))
    running = breakout_target(("A", "B"), "CDI")
    for i in range(100, 300, 7):
        fresh = breakout_target(("A", "B"), "CDI")(h.index[i], h.iloc[: i + 1])
        assert running(h.index[i], h.iloc[: i + 1]) == fresh


def test_breakout_ignores_a_missing_price_instead_of_crashing():
    a = np.concatenate([np.full(10, np.nan), np.linspace(100, 200, 120)])
    h = _closes(A=a, CDI=np.cumprod(np.full(130, 1.0004)))
    w = breakout_target(("A",), "CDI")(h.index[-1], h)
    assert sum(w.values()) == pytest.approx(1.0)


def test_profile_portfolios_are_four_with_valid_weights_and_sit_apart_from_the_classics():
    assert [m.id for m in PROFILE_PORTFOLIOS] == ["renda-dividendos", "estabilidade", "crescimento", "swing-alto-risco"]
    assert [m.id for m in ALL_PORTFOLIOS] == [m.id for m in METHODOLOGIES] + [m.id for m in PROFILE_PORTFOLIOS]
    assert all(m.kind == "profile" for m in PROFILE_PORTFOLIOS) and all(m.kind == "classic" for m in METHODOLOGIES)
    for m in PROFILE_PORTFOLIOS:
        if m.weights is not None:
            assert sum(w for _, w in m.weights) == pytest.approx(1.0)


def test_dividend_portfolio_mixes_fiis_brazilian_and_us_payers():
    w = dict(next(m for m in PROFILE_PORTFOLIOS if m.id == "renda-dividendos").weights)
    assert w["FII"] == 0.40 and w["SCHD"] == 0.10 and w["KO"] == 0.05 and w["BBAS3"] == 0.05


def test_stability_portfolio_is_mostly_cash_and_swing_checks_every_day():
    stab = dict(next(m for m in PROFILE_PORTFOLIOS if m.id == "estabilidade").weights)
    assert stab["CDI"] == 0.70
    swing = next(m for m in PROFILE_PORTFOLIOS if m.id == "swing-alto-risco")
    assert swing.rebalance == "daily" and swing.weights is None and "CDI" in swing.universe and len(swing.universe) == 9


def test_swing_waits_for_its_long_lived_assets_but_not_for_the_recent_ones():
    swing = next(m for m in PROFILE_PORTFOLIOS if m.id == "swing-alto-risco")
    assert swing.optional == ("TSLA", "META")
    idx = pd.bdate_range("2004-01-01", periods=400)
    cols = {name: np.full(400, 100.0) for name in swing.universe}
    table = pd.DataFrame(cols, index=idx)
    table["CDI"] = np.cumprod(np.full(400, 1.0004))
    table["NVDA"] = np.concatenate([np.full(50, np.nan), np.full(350, 100.0)])  # obrigatório: o início espera por ele
    table["TSLA"] = np.nan  # opcional: não atrasa
    start = own_start(table, swing)
    assert start == idx[idx >= idx[50] + pd.Timedelta(days=90)][0]


def test_own_start_is_the_latest_first_price_plus_warmup_and_rejects_missing_instruments():
    idx = pd.bdate_range("2020-01-01", periods=400)
    table = pd.DataFrame({"A": np.concatenate([np.full(5, np.nan), np.full(395, 1.0)]), "B": np.full(400, 1.0)}, index=idx)
    static = type(METHODOLOGIES[0])("x", "X", "a", "s", "r", "yearly", ("A", "B"), (("A", 0.5), ("B", 0.5)), lambda: None)
    assert own_start(table, static) == idx[5]
    table["A"] = np.nan
    with pytest.raises(ValueError, match="A"):
        own_start(table, static)
