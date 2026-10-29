"""Preços das carteiras em reais: ETFs em dólar convertidos pelo câmbio, cesta de FIIs e CDI do Banco Central."""
import time
from collections.abc import Callable, Sequence
from datetime import date, timedelta

import pandas as pd
import requests

from tradingbot.catalog import Asset
from tradingbot.data import DataError, get_prices
from tradingbot.portfolio import POOL_PREFIX

BRL_PAIR = "BRL=X"
CALENDAR_TICKER = "^BVSP"  # os pregões da B3 desde 1993 definem o calendário
BRL_TICKERS = {
    "BOVA11": "BOVA11.SA", "IVVB11": "IVVB11.SA", "BBAS3": "BBAS3.SA", "ITUB4": "ITUB4.SA",
    "TAEE11": "TAEE11.SA", "VIVT3": "VIVT3.SA",
}
USD_TICKERS = (
    "VTI", "VBR", "VXUS", "EFA", "VNQ", "TLT", "IEF", "SHY", "BND", "GLD", "DBC",
    "QQQ", "SCHD", "VYM", "KO", "PG", "JNJ", "PEP",
)
STOCK_CATEGORIES = ("Ações EUA", "Ações B3")  # de onde o swing escolhe
# Antes de o instrumento existir, um substituto parecido preenche o passado (escalado para coincidir no primeiro dia real).
# O substituto não tem as taxas do ETF e, no caso do índice, nem os proventos: é uma aproximação, avisada no painel.
PROXIES: dict[str, tuple[str, bool]] = {  # instrumento -> (ticker do substituto, está em dólar)
    "BOVA11": (CALENDAR_TICKER, False),
    "IVVB11": ("SPY", True),
    "VXUS": ("EFA", True),
    "BND": ("AGG", True),
    "GLD": ("GC=F", True),
    "SCHD": ("DVY", True),
    "VYM": ("DVY", True),
}
# FIIs grandes e antigos; o Yahoo só tem histórico da maioria a partir de 2014. Quem falhar é pulado.
FII_BASKET = ("HGLG11.SA", "KNRI11.SA", "MXRF11.SA", "HGRE11.SA", "BRCR11.SA", "VISC11.SA", "RNGO11.SA", "BTLG11.SA", "KNCR11.SA")
GAP_DAYS = 5  # buracos de até uma semana nos dados do Yahoo (um dia sem cotação) são preenchidos com o dia anterior
MIN_FII = 3  # a cesta só começa no primeiro dia em que há pelo menos este número de fundos
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
    """Índice (começa em 1) da média dos retornos diários dos FIIs que têm dado em cada dia, a partir do primeiro dia com MIN_FII fundos."""
    closes = []
    for ticker in FII_BASKET:
        try:
            closes.append(get_close(ticker))
        except DataError:
            continue
    if len(closes) < MIN_FII:
        raise DataError(f"A cesta de FIIs precisa de pelo menos {MIN_FII} fundos com dados (vieram {len(closes)}).")
    prices = pd.concat(closes, axis=1).sort_index()
    enough = prices.notna().sum(axis=1) >= MIN_FII
    start = enough.idxmax()
    prices = prices.loc[start:]
    daily = prices.pct_change(fill_method=None).mean(axis=1, skipna=True).iloc[1:]
    return pd.concat([pd.Series([1.0], index=[start]), (1 + daily.fillna(0)).cumprod()])


def splice(real: pd.Series, proxy: pd.Series) -> pd.Series:
    """Série real com o passado preenchido pelo substituto, escalado para igualar a real no primeiro dia dela. Sem sobreposição, devolve a real."""
    valid = real.dropna()
    if valid.empty:
        return real
    first = valid.index[0]
    at_first = proxy.loc[:first].dropna()
    if at_first.empty or at_first.iloc[-1] == 0:
        return real
    ratio = valid.iloc[0] / at_first.iloc[-1]
    head = (proxy.loc[proxy.index < first].dropna() * ratio).reindex(real.index[real.index < first])
    return pd.concat([head.dropna(), real.loc[first:]]).reindex(real.index)


def stock_pool(assets: Sequence[Asset]) -> list[tuple[str, str, bool]]:
    """Universo de ações do swing a partir do catálogo: (nome, ticker no Yahoo, está em dólar)."""
    return [(a.ticker.removesuffix(".SA"), a.ticker, not a.ticker.endswith(".SA")) for a in assets if a.category in STOCK_CATEGORIES]


def _default_close(start: date, end: date) -> Callable[[str], pd.Series]:
    def get_close(ticker: str) -> pd.Series:
        return get_prices(ticker, start.isoformat(), end.isoformat())["close"]

    return get_close


def build_price_table(
    start: date,
    end: date,
    get_close: Callable[[str], pd.Series] | None = None,
    get_cdi: Callable[[date, date], pd.Series] | None = None,
    pool: Sequence[tuple[str, str, bool]] = (),
) -> pd.DataFrame:
    """Tabela diária em reais, no calendário da B3, com uma coluna por instrumento. Antes do primeiro dado de um instrumento (e do substituto) a coluna fica vazia.
    `pool` (nome, ticker, em dólar) vira colunas com prefixo P: (o universo do swing); quem não tem dados é pulado."""
    get_close = get_close or _default_close(start, end)
    get_cdi = get_cdi or fetch_cdi
    calendar = get_close(CALENDAR_TICKER).index
    fx = get_close(BRL_PAIR)

    def to_calendar(series: pd.Series, usd: bool) -> pd.Series:
        union = calendar.union(series.index).union(fx.index)
        values = series.reindex(union).ffill()
        if usd:
            values = values * fx.reindex(union).ffill()
        return values.reindex(calendar)

    columns: dict[str, pd.Series] = {}
    wanted = [(name, ticker, False) for name, ticker in BRL_TICKERS.items()] + [(name, name, True) for name in USD_TICKERS]
    for name, ticker, usd in wanted:
        real = get_close(ticker).reindex(calendar).ffill(limit=GAP_DAYS) if not usd else to_calendar(get_close(ticker), True)
        if name in PROXIES:
            proxy_ticker, proxy_usd = PROXIES[name]
            real = splice(real, to_calendar(get_close(proxy_ticker), proxy_usd))
        columns[name] = real
    for name, ticker, usd in pool:
        try:
            close = get_close(ticker)
        except DataError:
            continue
        columns[POOL_PREFIX + name] = to_calendar(close, True) if usd else close.reindex(calendar).ffill(limit=GAP_DAYS)
    basket = fii_basket(get_close)
    columns["FII"] = basket.reindex(calendar.union(basket.index)).ffill().reindex(calendar)
    cdi_index = get_cdi(start, end).cumprod()
    columns["CDI"] = cdi_index.reindex(calendar.union(cdi_index.index)).ffill().reindex(calendar)
    return pd.DataFrame(columns, index=calendar)
