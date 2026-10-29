from datetime import date

import numpy as np
import pandas as pd
import pytest

from tradingbot.data import DataError
from tradingbot import portfolio_data
from tradingbot.portfolio_data import FII_BASKET, build_price_table, fetch_cdi, fii_basket


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


def test_fii_basket_averages_available_constituents_and_skips_missing():
    a = _closes(base=10.0, step=0.1)
    b = _closes(start="2020-01-08", base=20.0, step=0.4)  # entra depois

    def get_close(ticker):
        if ticker == FII_BASKET[0]:
            return a
        if ticker == FII_BASKET[1]:
            return b
        if ticker == FII_BASKET[2]:
            return a * 2
        raise DataError("sem dados")

    basket = fii_basket(get_close)
    assert basket.index[0] == a.index[0] and basket.iloc[0] == pytest.approx(1.0)
    first_return = (a.iloc[1] / a.iloc[0] - 1)  # no 2º dia só a e a*2 existem, com o mesmo retorno
    assert basket.iloc[1] == pytest.approx(1 + first_return)


def test_fii_basket_needs_enough_constituents():
    def get_close(ticker):
        if ticker == FII_BASKET[0]:
            return _closes()
        raise DataError("sem dados")

    with pytest.raises(DataError, match="FII"):
        fii_basket(get_close)


def test_build_price_table_converts_usd_to_reais_and_aligns_to_b3_calendar():
    b3 = pd.bdate_range("2020-01-01", periods=10)
    us_days = b3.delete(3)  # feriado americano em um dia útil da B3

    def get_close(ticker):
        if ticker == "BRL=X":
            return pd.Series(5.0, index=b3)
        if ticker in ("BOVA11.SA", "IVVB11.SA"):
            return pd.Series(100.0, index=b3)
        if ticker.endswith(".SA"):
            return pd.Series(10.0 + np.arange(10) * 0.1, index=b3)
        return pd.Series(10.0, index=us_days)

    def get_cdi(start, end):
        return pd.Series(1.0004, index=b3)

    table = build_price_table(date(2020, 1, 1), date(2020, 2, 1), get_close, get_cdi)
    assert table.index.equals(b3)
    assert {"BOVA11", "IVVB11", "FII", "CDI", "VTI", "GLD", "BND"} <= set(table.columns)
    assert (table["VTI"] == 50.0).all()  # US$10 x R$5, com o feriado preenchido pelo dia anterior
    assert table["CDI"].iloc[0] == pytest.approx(1.0004)
    assert table["CDI"].iloc[-1] == pytest.approx(1.0004**10)


def test_build_price_table_reports_the_instrument_that_failed():
    def get_close(ticker):
        if ticker == "GLD":
            raise DataError("sem dados para GLD")
        return pd.Series(10.0, index=pd.bdate_range("2020-01-01", periods=5))

    with pytest.raises(DataError, match="GLD"):
        build_price_table(date(2020, 1, 1), date(2020, 2, 1), get_close, lambda s, e: pd.Series(1.0004, index=pd.bdate_range("2020-01-01", periods=5)))
