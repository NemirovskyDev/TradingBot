"""Catálogo de ativos do painel: ticker (formato yfinance), nome e categoria, lido de assets.json."""
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

CATEGORIES = ("Ações EUA", "ETFs EUA", "Ações B3", "FIIs", "ETFs B3", "Cripto")
DEFAULT_PATH = Path(__file__).with_name("assets.json")
_TICKER = re.compile(r"[A-Za-z0-9.\-^=]{1,15}")  # mesma regra do data.py: o ticker vira parte de nome de arquivo


@dataclass(frozen=True)
class Asset:
    ticker: str
    name: str
    category: str


def slug(ticker: str) -> str:
    """Id seguro para nome de arquivo e URL: 'PETR4.SA' vira 'petr4_sa', 'BTC-USD' vira 'btc_usd'."""
    return re.sub(r"[^a-z0-9]+", "_", ticker.lower()).strip("_")


def _parse(item: object, index: int) -> Asset:
    if not isinstance(item, dict):
        raise ValueError(f"item {index}: esperado um objeto com ticker, name e category")
    ticker, name, category = item.get("ticker"), item.get("name"), item.get("category")
    if not isinstance(ticker, str) or not _TICKER.fullmatch(ticker):
        raise ValueError(f"item {index}: ticker inválido: {ticker!r}")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"item {index} ({ticker}): nome vazio")
    if category not in CATEGORIES:
        raise ValueError(f"item {index} ({ticker}): categoria desconhecida: {category!r}")
    return Asset(ticker, name.strip(), category)


def validate_assets(assets: list[Asset]) -> list[Asset]:
    """Tickers seguros, nomes preenchidos, categorias conhecidas, sem duplicados (sem diferenciar maiúsculas) e com ids únicos."""
    seen_tickers, seen_slugs = set(), {}
    for i, a in enumerate(assets):
        _parse({"ticker": a.ticker, "name": a.name, "category": a.category}, i)
        if a.ticker.upper() in seen_tickers:
            raise ValueError(f"ticker duplicado: {a.ticker}")
        seen_tickers.add(a.ticker.upper())
        s = slug(a.ticker)
        if s in seen_slugs:
            raise ValueError(f"id repetido ({s}) entre {seen_slugs[s]} e {a.ticker}")
        seen_slugs[s] = a.ticker
    return assets


def load_catalog(path: Path = DEFAULT_PATH) -> list[Asset]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("o catálogo deve ser uma lista de ativos")
    return validate_assets([_parse(item, i) for i, item in enumerate(raw)])


def write_catalog(assets: list[Asset], path: Path = DEFAULT_PATH) -> Path:
    """Valida e grava de forma atômica: um erro no meio nunca deixa o arquivo pela metade."""
    validate_assets(assets)
    target = Path(path)
    items = [{"ticker": a.ticker, "name": a.name, "category": a.category} for a in assets]
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, target)
    return target
