import json
import re
from pathlib import Path

import pandas as pd
import pytest

from tradingbot import cli
from tradingbot.backtest import buy_and_hold, run_backtest
from tradingbot.config import CostConfig, RiskConfig
from tradingbot.demo import make_synthetic_prices
from tradingbot.evaluate import Verdict
from tradingbot.export import export_run, write_index
from tradingbot.strategies import REASONS, sma_cross

FREE = CostConfig(commission=0.0, slippage_bps=0.0)
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _export(tmp_path, prices, result, synthetic=False, strategy="sma_cross"):
    bench = buy_and_hold(prices)
    path = export_run("run1", "DEMO", strategy, {"fast": 5}, prices, result, bench, Verdict(False, ["x"]), tmp_path, synthetic)
    return json.loads(path.read_text(encoding="utf-8"))


def _real_run(tmp_path):
    prices = make_synthetic_prices(500, 7)
    res = run_backtest(prices, sma_cross(prices, 5, 20), RiskConfig(), FREE)
    assert res.metrics["n_trades"] > 0
    return prices, res


def test_export_run_matches_contract_keys(tmp_path):
    prices, res = _real_run(tmp_path)
    data = _export(tmp_path, prices, res)
    assert set(data) == {"meta", "prices", "equity", "trades", "blocked", "metrics", "verdict"}
    assert set(data["meta"]) >= {"ticker", "strategy", "params", "start", "end", "initial_capital", "generated_at", "synthetic"}
    assert set(data["metrics"]) == {"total_return", "benchmark_return", "max_drawdown", "sharpe", "n_trades"}
    assert set(data["trades"][0]) == {
        "id", "entry_date", "entry_price", "exit_date", "exit_price", "qty", "stop",
        "pnl_pct", "reason_entry", "reason_exit",
    }
    assert set(data["prices"][0]) == {"date", "open", "high", "low", "close", "volume"}
    assert set(data["equity"][0]) == {"date", "strategy", "buy_hold"}
    assert data["verdict"] == {"passed": False, "reasons": ["x"]}


def test_export_dates_are_iso_and_returns_are_fractions(tmp_path):
    prices, res = _real_run(tmp_path)
    data = _export(tmp_path, prices, res)
    assert all(ISO.match(p["date"]) for p in data["prices"])
    assert all(ISO.match(t["entry_date"]) and ISO.match(t["exit_date"]) for t in data["trades"])
    assert data["metrics"]["total_return"] == pytest.approx(res.metrics["total_return"], abs=1e-6)
    assert -1 < data["metrics"]["total_return"] < 10
    assert data["meta"]["initial_capital"] == pytest.approx(10_000.0)


def test_export_trade_ids_are_unique_and_reasons_come_from_strategy(tmp_path):
    prices, res = _real_run(tmp_path)
    data = _export(tmp_path, prices, res)
    ids = [t["id"] for t in data["trades"]]
    assert len(ids) == len(set(ids))
    assert data["trades"][0]["reason_entry"] == REASONS["sma_cross"]["entry"]


def test_export_stop_exit_uses_stop_reason(tmp_path):
    idx = pd.bdate_range("2022-01-03", periods=20)
    prices = pd.DataFrame({"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1e6}, index=idx)
    prices.iloc[8, prices.columns.get_loc("low")] = 90.0
    sig = pd.Series(0, index=idx)
    sig.iloc[5:] = 1
    res = run_backtest(prices, sig, RiskConfig(), FREE)
    data = _export(tmp_path, prices, res)
    assert data["trades"][0]["reason_exit"] == "O preço tocou o stop de proteção."


def test_export_marks_synthetic_flag(tmp_path):
    prices, res = _real_run(tmp_path)
    assert _export(tmp_path, prices, res, synthetic=True)["meta"]["synthetic"] is True
    assert _export(tmp_path, prices, res, synthetic=False)["meta"]["synthetic"] is False


def test_export_json_has_no_nan(tmp_path):
    prices, res = _real_run(tmp_path)
    export_run("r", "DEMO", "sma_cross", {}, prices, res, buy_and_hold(prices), Verdict(True), tmp_path, True)
    text = (tmp_path / "runs" / "r.json").read_text(encoding="utf-8")
    json.loads(text, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))


def test_export_rejects_unsafe_run_id(tmp_path):
    prices, res = _real_run(tmp_path)
    with pytest.raises(ValueError):
        export_run("../x", "DEMO", "sma_cross", {}, prices, res, buy_and_hold(prices), Verdict(True), tmp_path)


def test_write_index_has_schema_1(tmp_path):
    path = write_index(tmp_path, [{"id": "a", "ticker": "DEMO", "strategy": "sma_cross", "label": "A"}])
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "schema": 1, "runs": [{"id": "a", "ticker": "DEMO", "strategy": "sma_cross", "label": "A"}],
    }


def test_synthetic_prices_are_deterministic_for_same_seed():
    pd.testing.assert_frame_equal(make_synthetic_prices(200, 3), make_synthetic_prices(200, 3))
    assert not make_synthetic_prices(200, 3).equals(make_synthetic_prices(200, 4))


def test_synthetic_prices_shape():
    df = make_synthetic_prices(100, 1)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"] and len(df) == 100
    assert (df["high"] >= df["low"]).all() and df.index.is_monotonic_increasing


def test_cli_export_writes_index_and_three_runs(tmp_path):
    config = Path(__file__).resolve().parents[1] / "config.toml"
    assert cli.main(["export", "--out", str(tmp_path), "--synthetic", "--config", str(config)]) == 0
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert index["schema"] == 1 and len(index["runs"]) == 3
    for run in index["runs"]:
        data = json.loads((tmp_path / "runs" / f"{run['id']}.json").read_text(encoding="utf-8"))
        assert data["meta"]["synthetic"] is True


def test_cli_export_requires_synthetic_flag(tmp_path):
    with pytest.raises(SystemExit):
        cli.main(["export", "--out", str(tmp_path)])


@pytest.mark.parametrize("bad", ["demo\n", "a b", "", "x" * 65])
def test_export_rejects_run_ids_that_fullmatch_would_refuse(tmp_path, bad):
    prices, res = _real_run(tmp_path)
    with pytest.raises(ValueError):
        export_run(bad, "DEMO", "sma_cross", {}, prices, res, buy_and_hold(prices), Verdict(True), tmp_path)
