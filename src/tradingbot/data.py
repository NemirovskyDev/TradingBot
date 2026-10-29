"""Preços diários: baixa (yfinance), normaliza e guarda em cache CSV. Única parte que conhece a fonte."""
import re
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pandas as pd

COLUMNS = ["open", "high", "low", "close", "volume"]
_TICKER = re.compile(r"[A-Za-z0-9.\-^=]{1,15}")  # com fullmatch: bloqueia caminhos, espaços e "\n" no nome do arquivo
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class DataError(Exception):
    """Ticker inválido, sem dados ou falha ao baixar."""


MIN_EXPECTED_BARS = 300  # menos que isso num pedido de muitos anos indica que o Yahoo recusou a data inicial


def _yfinance_fetch(ticker: str, start: str, end: str, download=None) -> pd.DataFrame:
    if download is None:
        import yfinance as yf  # import tardio: os testes não precisam da rede

        download = yf.download
    raw = download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    years = (date.fromisoformat(end) - date.fromisoformat(start)).days / 365
    if years > 3 and (raw is None or len(raw) < MIN_EXPECTED_BARS):
        # com um início muito antigo o Yahoo devolve só uns dias de alguns ativos (criptos): pede o histórico máximo e recorta
        full = download(ticker, period="max", auto_adjust=True, progress=False)
        if full is not None and len(full) > (0 if raw is None else len(raw)):
            raw = full.loc[(full.index >= pd.Timestamp(start)) & (full.index < pd.Timestamp(end))]
    return raw


def _normalize(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if raw is None or raw.empty:
        raise DataError(f"Sem dados para {ticker}.")
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise DataError(f"Dados de {ticker} sem as colunas {missing}.")
    # NaN em open/high/low quebraria o dimensionamento e faria o backtest pular o stop daquele dia
    df = df[COLUMNS].dropna(subset=["open", "high", "low", "close"]).sort_index()
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    if df.empty:
        raise DataError(f"Sem dados válidos para {ticker}.")
    return df


def get_prices(
    ticker: str,
    start: str,
    end: str,
    cache_dir: Path = Path(".cache"),
    fetch: Callable[[str, str, str], pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """Preços ajustados com colunas open/high/low/close/volume e índice de datas crescente."""
    if not _TICKER.fullmatch(ticker or ""):
        raise DataError(f"Ticker inválido: {ticker!r}.")
    for label, value in (("início", start), ("fim", end)):  # as datas entram no nome do cache
        if not _DATE.fullmatch(value or ""):
            raise DataError(f"Data de {label} inválida: {value!r} (use AAAA-MM-DD).")
        try:
            date.fromisoformat(value)
        except ValueError:
            raise DataError(f"Data de {label} inexistente: {value!r}.") from None
    ticker = ticker.upper()
    cache = Path(cache_dir) / f"{ticker.replace('^', '_')}_{start}_{end}.csv"
    if cache.exists():
        return pd.read_csv(cache, index_col=0, parse_dates=True)
    try:
        raw = (fetch or _yfinance_fetch)(ticker, start, end)
    except DataError:
        raise
    except Exception as exc:  # rede, limite de requisições, etc.
        raise DataError(f"Falha ao baixar {ticker}: {exc}") from exc
    df = _normalize(raw, ticker)
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache)
    return df
