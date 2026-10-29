"""Gera o catálogo ampliado: os ativos validados (seed) mais uma fatia do S&P 500, do Ibovespa e dos FIIs.

Fontes: Wikipedia (lista do S&P 500, lida com lxml), brapi.dev (ações da B3 por valor de mercado e fundos por volume,
sem chave) e yfinance (valor de mercado dos candidatos do S&P 500). Todas as fontes de rede são injetáveis."""
import math
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from io import StringIO

import pandas as pd

from tradingbot.catalog import Asset
from tradingbot.catalog_seed import B3, FII, SEED, US

SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
BRAPI_STOCKS_URL = "https://brapi.dev/api/quote/list?type=stock&sortBy=market_cap_basic&sortOrder=desc&limit=200"
BRAPI_FUNDS_URL = "https://brapi.dev/api/quote/list?type=fund&sortBy=volume&sortOrder=desc&limit=200"
# 4 letras + classe 3 a 8 ou unit (11). Fora: lotes fracionários (PETR4F) e BDRs (XXXX34, XXXX35)
_B3_STOCK = re.compile(r"[A-Z]{4}(?:[3-8]|11)")
_FII = re.compile(r"[A-Z]{4}11")
MIN_FII_PRICE = 5.0  # abaixo disso o "fundo" da lista da brapi costuma ser um papel de centavos, não um FII negociável
# a lista de "fundos" da brapi também traz ETFs, fundos de índice, de renda fixa/infraestrutura e Fiagros; não são FIIs
_NOT_A_REIT = re.compile(
    r"\bETF\b|ÍNDICE|INDICE|RENDA FIXA|\bFIC\b|\bFIF\b|INFRAESTRUTURA|FIAGRO|\bAGRO|CRIPTO|BITCOIN|\bOURO\b", re.IGNORECASE
)
_SECOND_CLASS = {"GOOG", "FOX", "NWS"}  # a outra classe da mesma empresa (GOOGL, FOXA, NWSA) já está no S&P 500
_LEGAL = re.compile(
    r"(?<!\w)S\.?\s?/?A\.?(?!\w)|\bFUNDO DE INVESTIMENTO IMOBILI[AÁ]RIO\b|\bRESPONSABILIDADE LIMITADA\b|\bRESP\.? LIMITADA\b|\bFII\b|\s-\s*$",
    re.IGNORECASE,
)
_SMALL_WORDS = {"de", "da", "do", "dos", "das", "e", "em"}
MAX_NAME = 42


def pretty_name(raw: str, ticker: str) -> str:
    """Nome legível: tira sufixos jurídicos (S.A., Fundo de Investimento Imobiliário...), acerta a caixa e limita o tamanho."""
    name = re.sub(r"\s+", " ", _LEGAL.sub(" ", raw)).strip(" -.")
    words = [w.lower() if w.lower() in _SMALL_WORDS and i else w.capitalize() for i, w in enumerate(name.split())]
    name = " ".join(words)
    if not name or name.upper() == ticker.upper():
        return ticker
    if len(name) > MAX_NAME:
        name = name[:MAX_NAME].rsplit(" ", 1)[0].rstrip(" ,-") + "…"
    return name


def parse_sp500(html: str) -> list[Asset]:
    table = pd.read_html(StringIO(html), match="Symbol")[0]
    return [
        Asset(str(sym).strip().replace(".", "-"), str(name).strip(), US)  # a Wikipedia usa BRK.B; o yfinance, BRK-B
        for sym, name in zip(table["Symbol"], table["Security"])
    ]


def _items(payload: object) -> list[dict]:
    stocks = payload.get("stocks") if isinstance(payload, dict) else None
    return [i for i in stocks if isinstance(i, dict)] if isinstance(stocks, list) else []


def parse_brapi_stocks(payload: object) -> list[Asset]:
    """Ações da B3 na ordem da API (valor de mercado decrescente); descarta as sem valor de mercado e os ETFs."""
    out = []
    for item in _items(payload):
        code = item.get("stock")
        if not (isinstance(code, str) and _B3_STOCK.fullmatch(code) and item.get("market_cap")):
            continue
        raw = str(item.get("name") or code)
        if code.endswith("11") and _NOT_A_REIT.search(raw):  # ETFs e fundos de índice vêm misturados, sempre com final 11
            continue
        out.append(Asset(f"{code}.SA", pretty_name(raw, code), B3))
    return out


def parse_brapi_funds(payload: object) -> list[Asset]:
    """FIIs negociáveis: ticker XXXX11, preço de pelo menos R$ 5, com volume e nome de fundo imobiliário."""
    out = []
    for item in _items(payload):
        code = item.get("stock")
        raw = str(item.get("name") or "").strip()
        if not (isinstance(code, str) and _FII.fullmatch(code)):
            continue
        if not raw or raw.upper() == code or _NOT_A_REIT.search(raw):  # nome igual ao ticker: a brapi não sabe o que é (ETF, por exemplo)
            continue
        if (item.get("close") or 0) >= MIN_FII_PRICE and (item.get("volume") or 0) > 0:
            out.append(Asset(f"{code}.SA", pretty_name(raw, code), FII))
    return out


def rank_by_market_cap(assets: list[Asset], cap_fn: Callable[[str], float | None], workers: int = 8) -> list[Asset]:
    """Ordena por valor de mercado decrescente; quem não tem valor (ou falhou ao consultar) vai para o fim."""

    def safe(ticker: str) -> float | None:
        try:
            cap = cap_fn(ticker)
        except Exception:  # noqa: BLE001 - uma consulta que falha só tira o ativo do topo
            return None
        return None if cap is None or math.isnan(cap) else cap

    with ThreadPoolExecutor(max_workers=workers) as pool:
        caps = list(pool.map(safe, [a.ticker for a in assets]))
    order = sorted(range(len(assets)), key=lambda i: (caps[i] is None, -(caps[i] or 0.0)))
    return [assets[i] for i in order]


def _company_key(asset: Asset) -> str:
    """Mesma empresa, mesma chave: na B3 as classes ON/PN (PETR3, PETR4) compartilham as 4 letras."""
    return f"B3:{asset.ticker[:4].upper()}" if asset.category == B3 else asset.ticker.upper()


def merge(seed: list[Asset], extras: dict[str, list[Asset]], limits: dict[str, int]) -> list[Asset]:
    """Seed primeiro (com os nomes dele); depois, por categoria, até `limits[categoria]` ativos novos de empresas ainda ausentes."""
    out = list(seed)
    seen = {_company_key(a) for a in out}
    for category, candidates in extras.items():
        added = 0
        for asset in candidates:
            if added >= limits.get(category, 0):
                break
            if asset.ticker.upper() in _SECOND_CLASS and category == US:
                continue
            if _company_key(asset) in seen:
                continue
            out.append(asset)
            seen.add(_company_key(asset))
            added += 1
    return out


def check_expanded(assets: list[Asset], wanted: dict[str, int]) -> None:
    """Falha se uma fonte devolveu nada (brapi fora do ar, por exemplo): sem isso o catálogo seria regravado só com o seed."""
    seed_tickers = {a.ticker for a in SEED}
    for category, n in wanted.items():
        added = sum(1 for a in assets if a.category == category and a.ticker not in seed_tickers)
        if n > 0 and added == 0:
            raise ValueError(f"a fonte de '{category}' não devolveu nenhum ativo novo")


def build_catalog(
    seed: list[Asset],
    *,
    fetch_html: Callable[[str], str],
    fetch_json: Callable[[str], object],
    cap_fn: Callable[[str], float | None],
    sp_n: int,
    b3_n: int,
    fii_n: int,
) -> list[Asset]:
    known = {a.ticker.upper() for a in seed}
    sp_candidates = [a for a in parse_sp500(fetch_html(SP500_URL)) if a.ticker.upper() not in known]
    extras = {
        US: rank_by_market_cap(sp_candidates, cap_fn),
        B3: parse_brapi_stocks(fetch_json(BRAPI_STOCKS_URL)),
        FII: parse_brapi_funds(fetch_json(BRAPI_FUNDS_URL)),
    }
    return merge(seed, extras, {US: sp_n, B3: b3_n, FII: fii_n})


# ---- fontes reais de rede (usadas só pelo comando `catalog`) ----

def _http_get(url: str):
    import requests

    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (TradingBot, uso educacional)"}, timeout=30)
    response.raise_for_status()
    return response


def _market_cap(ticker: str) -> float | None:
    import yfinance as yf

    return float(yf.Ticker(ticker).fast_info["market_cap"])


def build_from_network(sp_n: int, b3_n: int, fii_n: int) -> list[Asset]:
    return build_catalog(
        SEED,
        fetch_html=lambda url: _http_get(url).text,
        fetch_json=lambda url: _http_get(url).json(),
        cap_fn=_market_cap,
        sp_n=sp_n,
        b3_n=b3_n,
        fii_n=fii_n,
    )
