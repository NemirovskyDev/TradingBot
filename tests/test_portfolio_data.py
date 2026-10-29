from datetime import date

import numpy as np
import pandas as pd
import pytest

from tradingbot.data import DataError
from tradingbot import portfolio_data
from tradingbot.portfolio_data import FII_BASKET, build_price_table, fetch_cdi, fii_basket, splice, stock_pool


class _Resp:
    def __init__(self, rows, status=200):
        self._rows, self.status_code = rows, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._rows


def _bcb_fake(calls):
    """Devolve 0,04% ao dia nos dias úteis da janela pedida e registra cada pedido."""

    def get(url, timeout=0):
        query = dict(p.split("=") for p in url.split("?")[1].split("&"))
        start = pd.to_datetime(query["dataInicial"], format="%d/%m/%Y")
        end = pd.to_datetime(query["dataFinal"], format="%d/%m/%Y")
        calls.append((start, end))
        days = pd.bdate_range(start, end)
        return _Resp([{"data": d.strftime("%d/%m/%Y"), "valor": "0.04"} for d in days])

    return get


def test_cdi_is_fetched_in_windows_under_ten_years_and_deduplicated():
    calls = []
    series = fetch_cdi(date(2004, 1, 1), date(2026, 1, 1), http_get=_bcb_fake(calls))
    assert len(calls) >= 3
    assert all((end - start).days < 3650 for start, end in calls)  # a API recusa janelas maiores
    assert series.index.is_monotonic_increasing and not series.index.has_duplicates
    assert series.iloc[0] == pytest.approx(1.0004)  # fator diário: 0,04% ao dia


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(portfolio_data.time, "sleep", lambda _s: None)


def test_cdi_retries_a_transient_failure():
    ok = _bcb_fake([])
    state = {"n": 0}

    def flaky(url, timeout=0):
        state["n"] += 1
        return _Resp([], status=502) if state["n"] == 1 else ok(url, timeout)

    series = fetch_cdi(date(2020, 1, 1), date(2020, 3, 1), http_get=flaky)
    assert state["n"] >= 2 and len(series) > 0


def test_cdi_malformed_rows_become_a_data_error():
    with pytest.raises(DataError, match="CDI"):
        fetch_cdi(date(2020, 1, 1), date(2020, 3, 1), http_get=lambda url, timeout=0: _Resp([{"x": 1}]))


def test_cdi_failure_becomes_a_data_error():
    def boom(url, timeout=0):
        return _Resp([], status=500)

    with pytest.raises(DataError, match="CDI"):
        fetch_cdi(date(2020, 1, 1), date(2021, 1, 1), http_get=boom)


def test_cdi_with_no_rows_is_an_error():
    with pytest.raises(DataError, match="CDI"):
        fetch_cdi(date(2020, 1, 1), date(2021, 1, 1), http_get=lambda url, timeout=0: _Resp([]))


def _closes(start="2020-01-01", n=30, base=10.0, step=0.1):
    return pd.Series(base + step * np.arange(n), index=pd.bdate_range(start, periods=n))


def test_fii_basket_starts_only_when_enough_constituents_have_data():
    a = _closes(base=10.0, step=0.1)
    b = _closes(start="2020-01-08", base=20.0, step=0.4)  # entra depois
    c = _closes(start="2020-01-15", base=30.0, step=0.3)  # a cesta só começa aqui: antes só há 2 fundos

    def get_close(ticker):
        return {FII_BASKET[0]: a, FII_BASKET[1]: b, FII_BASKET[2]: c}[ticker] if ticker in FII_BASKET[:3] else (_ for _ in ()).throw(DataError("sem dados"))

    basket = fii_basket(get_close)
    assert basket.index[0] == c.index[0] and basket.iloc[0] == pytest.approx(1.0)
    expected = 1 + (a.iloc[11] / a.iloc[10] - 1 + b.iloc[6] / b.iloc[5] - 1 + c.iloc[1] / c.iloc[0] - 1) / 3
    assert basket.iloc[1] == pytest.approx(expected)


def test_splice_fills_the_past_with_the_scaled_proxy_and_keeps_the_real_series():
    idx = pd.bdate_range("2020-01-01", periods=10)
    real = pd.Series([np.nan] * 5 + [200.0, 210.0, 220.0, 230.0, 240.0], index=idx)
    proxy = pd.Series(np.arange(10, dtype=float) + 100.0, index=idx)  # 100..109; no dia 5 vale 105
    out = splice(real, proxy)
    assert out.iloc[5:].tolist() == real.iloc[5:].tolist()
    assert out.iloc[5] == pytest.approx(200.0)
    assert out.iloc[4] == pytest.approx(104.0 * 200.0 / 105.0)  # mesma variação do substituto, escalada
    assert out.notna().all()


def test_splice_without_overlap_keeps_the_real_series_untouched():
    idx = pd.bdate_range("2020-01-01", periods=6)
    real = pd.Series([np.nan, np.nan, np.nan, 10.0, 11.0, 12.0], index=idx)
    proxy = pd.Series([np.nan] * 6, index=idx)
    assert splice(real, proxy).equals(real)


def test_fii_basket_needs_enough_constituents():
    def get_close(ticker):
        if ticker == FII_BASKET[0]:
            return _closes()
        raise DataError("sem dados")

    with pytest.raises(DataError, match="FII"):
        fii_basket(get_close)


def test_build_price_table_converts_usd_to_reais_aligns_to_b3_and_splices_proxies():
    b3 = pd.bdate_range("2020-01-01", periods=10)
    us_days = b3.delete(3)  # feriado americano em um dia útil da B3
    late = b3[4:]  # o ETF só existe a partir do 5º dia

    def get_close(ticker):
        if ticker == "^BVSP":
            return pd.Series(1000.0 + np.arange(10), index=b3)
        if ticker == "BRL=X":
            return pd.Series(5.0, index=b3)
        if ticker in ("BOVA11.SA", "IVVB11.SA"):
            return pd.Series(100.0, index=late)
        if ticker.endswith(".SA"):
            return pd.Series(10.0 + np.arange(10) * 0.1, index=b3)
        return pd.Series(10.0, index=us_days)

    def get_cdi(start, end):
        return pd.Series(1.0004, index=b3)

    table = build_price_table(date(2020, 1, 1), date(2020, 2, 1), get_close, get_cdi)
    assert table.index.equals(b3)
    assert {"BOVA11", "IVVB11", "FII", "CDI", "VTI", "GLD", "BND", "QQQ", "BBAS3", "PG"} <= set(table.columns)
    assert (table["VTI"] == 50.0).all()  # US$10 x R$5, com o feriado preenchido pelo dia anterior
    assert table["BOVA11"].notna().all() and table["BOVA11"].iloc[4] == pytest.approx(100.0)  # o passado vem do índice
    assert table["BOVA11"].iloc[3] == pytest.approx(100.0 * 1003 / 1004)
    assert table["IVVB11"].notna().all()  # o passado vem do S&P 500 (SPY) em reais
    assert table["CDI"].iloc[0] == pytest.approx(1.0004)
    assert table["CDI"].iloc[-1] == pytest.approx(1.0004**10)


def test_build_price_table_reports_the_instrument_that_failed():
    def get_close(ticker):
        if ticker == "GLD":
            raise DataError("sem dados para GLD")
        return pd.Series(10.0, index=pd.bdate_range("2020-01-01", periods=5))

    with pytest.raises(DataError, match="GLD"):
        build_price_table(date(2020, 1, 1), date(2020, 2, 1), get_close, lambda s, e: pd.Series(1.0004, index=pd.bdate_range("2020-01-01", periods=5)))


def test_a_one_day_hole_in_a_brazilian_series_is_filled_but_a_long_gap_is_not():
    b3 = pd.bdate_range("2020-01-01", periods=30)

    def get_close(ticker):
        if ticker in ("^BVSP", "BRL=X"):
            return pd.Series(5.0, index=b3)
        if ticker == "ITUB4.SA":
            return pd.Series(10.0, index=b3.delete([10, 20, 21, 22, 23, 24, 25, 26]))  # 1 dia e depois 7 dias sem dado
        if ticker.endswith(".SA"):
            return pd.Series(10.0 + np.arange(30) * 0.1, index=b3)
        return pd.Series(10.0, index=b3)

    table = build_price_table(date(2020, 1, 1), date(2020, 3, 1), get_close, lambda s, e: pd.Series(1.0004, index=b3))
    assert table["ITUB4"].iloc[10] == 10.0  # buraco de um dia: preenchido
    assert pd.isna(table["ITUB4"].iloc[26])  # buraco longo: depois de 5 dias preenchidos, volta a faltar


def test_the_stock_pool_becomes_prefixed_columns_in_reais_and_skips_tickers_without_data():
    b3 = pd.bdate_range("2020-01-01", periods=10)

    def get_close(ticker):
        if ticker == "SEMDADO":
            raise DataError("sem dados")
        if ticker in ("^BVSP", "BRL=X"):
            return pd.Series(5.0 if ticker == "BRL=X" else 1000.0, index=b3)
        if ticker == "PETR4.SA":
            return pd.Series(30.0, index=b3)
        if ticker == "AAPL":
            return pd.Series(10.0, index=b3)
        return pd.Series(10.0, index=b3)

    pool = [("PETR4", "PETR4.SA", False), ("AAPL", "AAPL", True), ("SEMDADO", "SEMDADO", True)]
    table = build_price_table(date(2020, 1, 1), date(2020, 2, 1), get_close, lambda s, e: pd.Series(1.0004, index=b3), pool=pool)
    assert (table["P:AAPL"] == 50.0).all()  # US$10 x R$5
    assert (table["P:PETR4"] == 30.0).all()
    assert "P:SEMDADO" not in table.columns


def test_stock_pool_takes_only_us_and_b3_stocks_from_the_catalog():
    from tradingbot.catalog import Asset

    catalog = [
        Asset("AAPL", "Apple", "Ações EUA"), Asset("PETR4.SA", "Petrobras", "Ações B3"),
        Asset("MXRF11.SA", "Maxi", "FIIs"), Asset("SPY", "S&P", "ETFs EUA"), Asset("BTC-USD", "Bitcoin", "Cripto"),
    ]
    assert stock_pool(catalog) == [("AAPL", "AAPL", True), ("PETR4", "PETR4.SA", False)]
