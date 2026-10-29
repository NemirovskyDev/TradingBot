import json

import numpy as np
import pandas as pd
import pytest

from tradingbot.export_portfolios import SCHEMA, build_payload, export_portfolios
from tradingbot.portfolio import ALL_PORTFOLIOS


INSTRUMENTS = (
    "BOVA11", "IVVB11", "FII", "VTI", "VBR", "VXUS", "EFA", "VNQ", "TLT", "IEF", "SHY", "BND", "GLD", "DBC",
    "QQQ", "SCHD", "VYM", "KO", "PG", "JNJ", "PEP", "BBAS3", "ITUB4", "TAEE11", "VIVT3",
    "NVDA", "TSLA", "AMD", "NFLX", "META", "AMZN", "PETR4", "VALE3",
)


def _table(years=6):
    """Tabela sintética com todos os instrumentos: sobem devagar, o caixa cresce sempre."""
    idx = pd.bdate_range("2010-01-04", periods=252 * years)
    rng = np.random.default_rng(7)
    cols = {}
    for name in INSTRUMENTS:
        cols[name] = 100 * np.cumprod(1 + rng.normal(0.0003, 0.01, len(idx)))
    cols["CDI"] = np.cumprod(np.full(len(idx), 1.0004))
    return pd.DataFrame(cols, index=idx)


def test_payload_has_every_methodology_and_the_benchmarks_on_one_calendar():
    table = _table()
    payload = build_payload(table, table.index[252 * 2])
    assert payload["schema"] == SCHEMA and payload["currency"] == "BRL"
    assert [p["id"] for p in payload["portfolios"]] == [m.id for m in ALL_PORTFOLIOS]
    assert [p["kind"] for p in payload["portfolios"]] == ["classic"] * 7 + ["profile"] * 4
    assert [b["id"] for b in payload["benchmarks"]] == ["cdi", "ibovespa", "sp500"]
    n = len(payload["dates"])
    for series in payload["portfolios"] + payload["benchmarks"]:
        assert len(series["equity"]) == n and len(series["drawdown"]) == n
        assert next(v for v in series["equity"] if v is not None) == pytest.approx(100.0)
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


def test_each_portfolio_starts_when_its_own_assets_exist_and_the_common_window_is_the_latest_start():
    table = _table()
    table.loc[table.index[:300], "QQQ"] = np.nan  # só a carteira de crescimento depende do QQQ
    payload = build_payload(table, None)
    by_id = {p["id"]: p for p in payload["portfolios"]}
    assert by_id["crescimento"]["start"] == str(table.index[300].date())
    assert by_id["arca"]["start"] == str(table.index[0].date())
    starts = [p["start"] for p in payload["portfolios"]]
    assert payload["start"] == min(starts) and payload["common_start"] == max(starts)
    equity = by_id["crescimento"]["equity"]
    first_valid = next(i for i, v in enumerate(equity) if v is not None)
    assert first_valid > 0 and all(v is None for v in equity[:first_valid])  # antes do início a curva fica vazia
    assert equity[first_valid] == pytest.approx(100.0)


def test_references_are_summarised_over_each_portfolios_own_period_and_over_the_common_window():
    table = _table()
    payload = build_payload(table, None)
    for p in payload["portfolios"]:
        assert set(p["benchmarks"]) == {"cdi", "ibovespa", "sp500"}
        assert p["benchmarks"]["cdi"]["metrics"]["total_return"] > 0 and p["benchmarks"]["cdi"]["annual_returns"]
        assert p["metrics_common"]["total_return"] is not None
    assert all("metrics_common" in b for b in payload["benchmarks"])


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


def test_payload_has_the_four_profiles_pointing_at_real_portfolios_and_related_ones():
    table = _table()
    payload = build_payload(table, table.index[252 * 2])
    ids = {p["id"] for p in payload["portfolios"]}
    classic = {p["id"] for p in payload["portfolios"] if p["kind"] == "classic"}
    profiles = {p["id"]: p for p in payload["profiles"]}
    assert list(profiles) == ["renda-dividendos", "estabilidade", "crescimento", "swing-alto-risco"]
    for p in profiles.values():
        assert p["portfolio_id"] in ids and set(p["related_ids"]) <= classic
        assert p["name"] and p["tagline"] and p["expect"] and p["warning"]
    assert profiles["renda-dividendos"]["related_ids"] == []
    assert profiles["swing-alto-risco"]["runs_link"] is True and profiles["crescimento"]["runs_link"] is False
    # estabilidade ordena pela menor queda máxima; crescimento pelo maior retorno ao ano
    by_id = {p["id"]: p["metrics_common"] for p in payload["portfolios"]}
    stab = profiles["estabilidade"]["related_ids"]
    assert len(stab) == 2 and by_id[stab[0]]["max_drawdown"] >= by_id[stab[1]]["max_drawdown"]
    growth = profiles["crescimento"]["related_ids"]
    assert len(growth) == 2 and by_id[growth[0]]["cagr"] >= by_id[growth[1]]["cagr"]


def test_the_swing_portfolio_holds_cash_when_nothing_has_broken_out():
    table = _table()
    for name in ("NVDA", "TSLA", "AMD", "NFLX", "META", "AMZN", "PETR4", "VALE3"):
        table[name] = 100.0  # preço parado: nenhum rompimento
    payload = build_payload(table, table.index[252 * 2])
    swing = next(p for p in payload["portfolios"] if p["id"] == "swing-alto-risco")
    assert swing["metrics"]["total_return"] == pytest.approx(swing["benchmarks"]["cdi"]["metrics"]["total_return"], rel=1e-3)
