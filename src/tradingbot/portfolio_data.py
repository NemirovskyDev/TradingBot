"""Preços das carteiras em reais: ETFs em dólar convertidos pelo câmbio, cesta de FIIs e CDI do Banco Central."""
import time
from collections.abc import Callable
from datetime import date, timedelta

import pandas as pd
import requests

from tradingbot.data import DataError, get_prices

BRL_PAIR = "BRL=X"
BRL_TICKERS = {"BOVA11": "BOVA11.SA", "IVVB11": "IVVB11.SA"}
USD_TICKERS = ("VTI", "VBR", "VXUS", "EFA", "VNQ", "TLT", "IEF", "SHY", "BND", "GLD", "DBC")
# FIIs grandes e antigos (todos com histórico desde antes de 2014); quem falhar é pulado
FII_BASKET = ("HGLG11.SA", "KNRI11.SA", "MXRF11.SA", "HGRE11.SA", "BRCR11.SA", "VISC11.SA")
MIN_FII = 3
BCB_CDI = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json&dataInicial={}&dataFinal={}"
BCB_WINDOW_DAYS = 3000  # a API recusa janelas de mais de 10 anos


def _fetch_window(url: str, http_get: Callable, attempts: int = 4, wait: float = 3.0) -> list:
    """A API do Banco Central responde 502 de vez em quando: tenta de novo antes de desistir."""
    for attempt in range(attempts):
        try:
            response = http_get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001 - rede, HTTP ou JSON
            if attempt == attempts - 1:
                raise DataError(f"Falha ao baixar o CDI do Banco Central: {exc}") from exc
            time.sleep(wait * (attempt + 1))
    return []


def fetch_cdi(start: date, end: date, http_get: Callable = requests.get) -> pd.Series:
    """Fator diário do CDI (1 + taxa do dia) por data. Busca em janelas de menos de 10 anos."""
    frames = []
    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=BCB_WINDOW_DAYS), end)
        url = BCB_CDI.format(cursor.strftime("%d/%m/%Y"), window_end.strftime("%d/%m/%Y"))
        frame = pd.DataFrame(_fetch_window(url, http_get))
        if not frame.empty:
            try:
                frames.append(
                    pd.Series(
                        1 + frame["valor"].astype(float).to_numpy() / 100,
                        index=pd.to_datetime(frame["data"], format="%d/%m/%Y"),
                    )
                )
            except (KeyError, ValueError) as exc:
                raise DataError(f"Resposta inesperada do CDI do Banco Central: {exc}") from exc
        cursor = window_end + timedelta(days=1)
    if not frames:
        raise DataError("O Banco Central não devolveu dados do CDI.")
    series = pd.concat(frames).sort_index()
    return series[~series.index.duplicated(keep="first")]


def fii_basket(get_close: Callable[[str], pd.Series]) -> pd.Series:
    """Índice (começa em 1) da média dos retornos diários dos FIIs que têm dado em cada dia."""
    closes = []
    for ticker in FII_BASKET:
        try:
            closes.append(get_close(ticker))
        except DataError:
            continue
    if len(closes) < MIN_FII:
        raise DataError(f"A cesta de FIIs precisa de pelo menos {MIN_FII} fundos com dados (vieram {len(closes)}).")
    returns = pd.concat(closes, axis=1).sort_index().pct_change(fill_method=None)
    daily = returns.mean(axis=1, skipna=True).dropna()  # o 1º dia não tem retorno
    start = min(c.index[0] for c in closes)
    return pd.concat([pd.Series([1.0], index=[start]), (1 + daily).cumprod()])


def _default_close(start: date, end: date) -> Callable[[str], pd.Series]:
    def get_close(ticker: str) -> pd.Series:
        return get_prices(ticker, start.isoformat(), end.isoformat())["close"]

    return get_close


def build_price_table(
    start: date,
    end: date,
    get_close: Callable[[str], pd.Series] | None = None,
    get_cdi: Callable[[date, date], pd.Series] | None = None,
) -> pd.DataFrame:
    """Tabela diária em reais, no calendário da B3, com uma coluna por instrumento. Antes do primeiro dado de um instrumento a coluna fica vazia."""
    get_close = get_close or _default_close(start, end)
    get_cdi = get_cdi or fetch_cdi
    calendar = get_close(BRL_TICKERS["BOVA11"]).index
    fx = get_close(BRL_PAIR)
    columns: dict[str, pd.Series] = {}
    for name, ticker in BRL_TICKERS.items():
        columns[name] = get_close(ticker).reindex(calendar)
    basket = fii_basket(get_close)
    columns["FII"] = basket.reindex(calendar.union(basket.index)).ffill().reindex(calendar)
    for name in USD_TICKERS:
        usd = get_close(name)
        union = calendar.union(usd.index).union(fx.index)
        converted = usd.reindex(union).ffill() * fx.reindex(union).ffill()
        columns[name] = converted.reindex(calendar)
    cdi = get_cdi(start, end)
    cdi_index = cdi.cumprod()
    columns["CDI"] = cdi_index.reindex(calendar.union(cdi_index.index)).ffill().reindex(calendar)
    return pd.DataFrame(columns, index=calendar)
