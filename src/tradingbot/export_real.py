"""Exportação dos ativos do catálogo (dados reais): baixa, roda as 3 estratégias e grava um JSON por execução."""
import inspect
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from tradingbot.catalog import Asset, slug
from tradingbot.data import DataError, get_prices
from tradingbot.evaluate import PromotionCriteria, evaluate_detailed
from tradingbot.export import export_run
from tradingbot.strategies import STRATEGIES

MIN_BARS = 600  # menos que isso deixa o trecho de teste (30%) curto demais para um veredito
MAX_SKIPPED_FRACTION = 0.25  # acima disso a fonte provavelmente falhou: melhor não trocar o que já está publicado


@dataclass
class ExportResult:
    runs: list[dict] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def strategy_params(name: str, cfg) -> dict:
    defaults = {k: v.default for k, v in inspect.signature(STRATEGIES[name]).parameters.items() if k != "prices"}
    return {"estrategia": defaults, "risco": asdict(cfg.risk), "custos": asdict(cfg.costs)}


def _fetch_with_retry(ticker: str, start: str, end: str, attempts: int = 2, wait: float = 2.0):
    """Falhas de rede são comuns em uma exportação longa: tenta de novo antes de desistir do ativo."""
    for attempt in range(attempts):
        try:
            return get_prices(ticker, start, end)
        except DataError:
            if attempt == attempts - 1:
                raise
            time.sleep(wait)


def export_real(assets: list[Asset], cfg, out: Path, start: str, end: str) -> ExportResult:
    """Grava as execuções de cada ativo. Um ativo só entra com as 3 estratégias; sem dados ou histórico curto, é listado e ignorado."""
    result = ExportResult()
    for asset in assets:
        try:
            prices = _fetch_with_retry(asset.ticker, start, end)
        except DataError as exc:
            result.skipped.append(f"{asset.ticker} ({exc})")
            continue
        if len(prices) < MIN_BARS:
            result.skipped.append(f"{asset.ticker} (histórico curto: {len(prices)} barras)")
            continue
        asset_runs: list[dict] = []
        for name in sorted(STRATEGIES):
            ev = evaluate_detailed(prices, STRATEGIES[name], PromotionCriteria(), cfg.risk, cfg.costs, cfg.initial_capital)
            if ev.strategy is None or ev.benchmark is None or ev.test is None:
                asset_runs = []
                result.skipped.append(f"{asset.ticker} (trecho de teste curto demais)")
                break
            run_id = f"{slug(asset.ticker)}-{name}"
            export_run(run_id, asset.ticker, name, strategy_params(name, cfg), ev.test, ev.strategy, ev.benchmark, ev.verdict, out)
            asset_runs.append(
                {"id": run_id, "ticker": asset.ticker, "strategy": name, "label": f"{asset.name} · {name}",
                 "name": asset.name, "category": asset.category}
            )
        result.runs.extend(asset_runs)  # tudo ou nada por ativo
    return result
