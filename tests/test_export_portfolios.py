import json

import numpy as np
import pandas as pd
import pytest

from tradingbot.export_portfolios import SCHEMA, build_payload, export_portfolios
from tradingbot.portfolio import METHODOLOGIES


def _table(years=6):
    """Tabela sintética com todos os instrumentos: sobem devagar, o caixa cresce sempre."""
    idx = pd.bdate_range("2010-01-04", periods=252 * years)
    rng = np.random.default_rng(7)
    cols = {}
    for name in ("BOVA11", "IVVB11", "FII", "VTI", "VBR", "VXUS", "EFA", "VNQ", "TLT", "IEF", "SHY", "BND", "GLD", "DBC"):
        cols[name] = 100 * np.cumprod(1 + rng.normal(0.0003, 0.01, len(idx)))
    cols["CDI"] = np.cumprod(np.full(len(idx), 1.0004))
    return pd.DataFrame(cols, index=idx)


def test_payload_has_every_methodology_and_the_benchmarks_on_one_calendar():
    table = _table()
    payload = build_payload(table, table.index[252 * 2])
    assert payload["schema"] == SCHEMA and payload["currency"] == "BRL"
    assert [p["id"] for p in payload["portfolios"]] == [m.id for m in METHODOLOGIES]
    assert [b["id"] for b in payload["benchmarks"]] == ["cdi", "ibovespa", "sp500"]
    n = len(payload["dates"])
    for series in payload["portfolios"] + payload["benchmarks"]:
        assert len(series["equity"]) == n and len(series["drawdown"]) == n
        assert series["equity"][0] == pytest.approx(100.0)
        assert series["metrics"]["max_drawdown"] <= 0
        assert series["annual_returns"]
    assert payload["dates"][-1] == str(table.index[-1].date())  # a última data nunca é cortada pela amostragem


def test_payload_describes_each_portfolio_for_the_ui():
    table = _table()
    payload = build_payload(table, table.index[252 * 2])
    arca = payload["portfolios"][0]
    assert arca["name"] == "ARCA" and arca["rebalance"] == "yearly"
    assert {c["label"]: c["weight"] for c in arca["components"]}["Caixa (CDI)"] == 0.25
    ivy = next(p for p in payload["portfolios"] if p["id"] == "faber-ivy")
    assert ivy["components"] == [] and ivy["rule"]
    assert payload["assumptions"] and any("imposto" in a.lower() for a in payload["assumptions"])


def test_start_is_the_first_day_with_every_price():
    table = _table()
    table.loc[table.index[:100], "IVVB11"] = np.nan
    payload = build_payload(table, None)
    assert payload["dates"][0] == str(table.index[100].date())


def test_no_common_window_is_an_error():
    table = _table(1)
    table["IVVB11"] = np.nan
    with pytest.raises(ValueError, match="IVVB11"):
        build_payload(table, None)


def test_export_writes_a_valid_json_atomically(tmp_path):
    table = _table()
    path = export_portfolios(table, tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert path.name == "portfolios.json" and data["schema"] == SCHEMA
    assert not list(tmp_path.glob("*.tmp"))
    assert "NaN" not in path.read_text(encoding="utf-8")  # JSON válido: sem NaN


def test_a_failed_build_keeps_the_previous_file(tmp_path):
    (tmp_path / "portfolios.json").write_text('{"old": true}', encoding="utf-8")
    table = _table(1)
    table["IVVB11"] = np.nan
    with pytest.raises(ValueError):
        export_portfolios(table, tmp_path)
    assert json.loads((tmp_path / "portfolios.json").read_text(encoding="utf-8")) == {"old": True}
