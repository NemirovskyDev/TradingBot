"""Critério para uma estratégia passar do backtest ao paper trading. Julga só o trecho fora da amostra.
Os limites são pontos de partida a calibrar, não recomendação de investimento."""
from collections.abc import Callable
from dataclasses import dataclass, field, replace

import pandas as pd

from tradingbot.backtest import BacktestResult, buy_and_hold, run_backtest, split_train_test
from tradingbot.config import CostConfig, RiskConfig


@dataclass(frozen=True)
class PromotionCriteria:
    min_trades: int = 10  # tendência opera pouco (2 a 5 vezes em 2 anos); abaixo de 10 o resultado é estatisticamente fraco
    max_drawdown: float = 0.25


@dataclass
class Verdict:
    passed: bool
    reasons: list[str] = field(default_factory=list)


def _br(x: float, digits: int = 2) -> str:
    """Número no formato pt-BR (vírgula decimal), pois as frases vão direto para a tela."""
    return f"{x:.{digits}f}".replace(".", ",")


def judge(
    strategy: BacktestResult, benchmark: BacktestResult, doubled_costs: BacktestResult, criteria: PromotionCriteria
) -> Verdict:
    """Regra pura: cada critério que falha vira uma frase simples em `reasons`."""
    reasons = []
    s, b = strategy.metrics, benchmark.metrics
    if s["sharpe"] <= b["sharpe"]:
        reasons.append(
            f"Não superou o comprar e segurar ajustado ao risco (Sharpe {_br(s['sharpe'])} contra {_br(b['sharpe'])})."
        )
    if s["max_drawdown"] > criteria.max_drawdown:
        reasons.append(
            f"A maior queda foi de {_br(s['max_drawdown'] * 100, 1)}%, "
            f"acima do limite de {_br(criteria.max_drawdown * 100, 0)}%."
        )
    if s["n_trades"] < criteria.min_trades:
        reasons.append(
            f"Poucas operações para concluir algo: {int(s['n_trades'])} de pelo menos {criteria.min_trades}."
        )
    if doubled_costs.metrics["total_return"] <= 0:
        reasons.append("Com o custo dobrado a estratégia deixa de dar lucro.")
    return Verdict(passed=not reasons, reasons=reasons)


@dataclass
class Evaluation:
    """Veredito mais os resultados que o geraram (None quando o histórico é curto demais)."""

    verdict: Verdict
    strategy: BacktestResult | None = None
    benchmark: BacktestResult | None = None
    test: pd.DataFrame | None = None


def evaluate_detailed(
    prices: pd.DataFrame,
    strategy: Callable[[pd.DataFrame], pd.Series],
    criteria: PromotionCriteria,
    risk_cfg: RiskConfig,
    cost_cfg: CostConfig,
    initial_capital: float = 10_000.0,
) -> Evaluation:
    """Roda no trecho de teste (os 30% mais recentes); os sinais usam o histórico todo para o aquecimento."""
    try:
        _, test = split_train_test(prices)
    except ValueError:
        return Evaluation(Verdict(False, ["Histórico curto demais para separar treino e teste."]))
    if len(test) < 2:
        return Evaluation(Verdict(False, ["O trecho de teste tem menos de 2 dias."]))
    signals = strategy(prices).loc[test.index]
    doubled = replace(cost_cfg, commission=cost_cfg.commission * 2, slippage_bps=cost_cfg.slippage_bps * 2)
    result = run_backtest(test, signals, risk_cfg, cost_cfg, initial_capital)
    bench = buy_and_hold(test, initial_capital)
    verdict = judge(result, bench, run_backtest(test, signals, risk_cfg, doubled, initial_capital), criteria)
    return Evaluation(verdict, result, bench, test)


def evaluate_strategy(
    prices: pd.DataFrame,
    strategy: Callable[[pd.DataFrame], pd.Series],
    criteria: PromotionCriteria,
    risk_cfg: RiskConfig,
    cost_cfg: CostConfig,
    initial_capital: float = 10_000.0,
) -> Verdict:
    return evaluate_detailed(prices, strategy, criteria, risk_cfg, cost_cfg, initial_capital).verdict
