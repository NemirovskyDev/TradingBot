"""Portão de risco determinístico entre sinal e ordem. Sem LLM: vence qualquer opinião do analyst."""
import math
from dataclasses import dataclass
from numbers import Integral
from typing import Literal

import pandas as pd

from tradingbot.config import RiskConfig


class RiskRejected(Exception):
    """Ordem ou tamanho de posição recusado; a mensagem diz o motivo (em português)."""


@dataclass
class Order:
    ticker: str
    side: Literal["buy", "sell"]
    qty: int
    entry: float
    stop: float | None
    sector: str = "unknown"


@dataclass
class Position:
    ticker: str
    qty: int
    entry: float
    sector: str


@dataclass
class PortfolioState:
    equity: float
    positions: dict[str, Position]
    week_start_equity: float


def position_size(capital: float, entry: float, stop: float, cfg: RiskConfig) -> int:
    """qtd = (capital * risco_por_trade) / (entrada - stop), limitada ao teto de posição; 0 se não couber."""
    if not all(math.isfinite(x) for x in (capital, entry, stop)) or entry <= 0 or stop <= 0:
        raise RiskRejected("Capital, entrada e stop precisam ser números válidos e positivos.")
    if stop >= entry:
        raise RiskRejected("O stop precisa ficar abaixo do preço de entrada.")
    by_risk = math.floor(capital * cfg.risk_per_trade / (entry - stop))
    by_cap = math.floor(capital * cfg.max_position_pct / entry)
    return max(0, min(by_risk, by_cap))


def atr_stop(prices: pd.DataFrame, i: int, period: int = 14, mult: float = 2.0) -> float:
    """Stop = fechamento do dia i menos mult * ATR (média da amplitude real das últimas `period` barras)."""
    window = prices.iloc[max(0, i - period + 1) : i + 1]
    prev_close = prices["close"].shift(1).loc[window.index]
    true_range = pd.concat(
        [window["high"] - window["low"], (window["high"] - prev_close).abs(), (window["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    atr = float(true_range.mean())
    return float(prices["close"].iloc[i]) - mult * atr


def check_order(order: Order, state: PortfolioState, cfg: RiskConfig) -> None:
    """Levanta RiskRejected se a compra violar algum limite. Vendas sempre passam."""
    if order.side == "sell":
        return
    # NaN passa em qualquer comparação (nan >= x é False), então valores não finitos são barrados à parte.
    if not isinstance(order.qty, Integral) or order.qty <= 0:
        raise RiskRejected("Quantidade precisa ser um número inteiro maior que zero.")
    if not math.isfinite(order.entry) or order.entry <= 0:
        raise RiskRejected("O preço de entrada precisa ser um número válido e positivo.")
    if order.stop is None:
        raise RiskRejected("Toda compra precisa de stop.")
    if not math.isfinite(order.stop) or not 0 < order.stop < order.entry:
        raise RiskRejected("O stop precisa ser um número positivo abaixo do preço de entrada.")
    if state.equity <= state.week_start_equity * (1 - cfg.weekly_loss_limit):
        raise RiskRejected("Limite de perda da semana atingido: o bot está pausado.")
    if len(state.positions) >= cfg.max_open_positions:
        raise RiskRejected(f"Limite de {cfg.max_open_positions} posições abertas atingido.")
    value = order.qty * order.entry
    existing = state.positions.get(order.ticker)
    asset_value = value + (existing.qty * existing.entry if existing else 0.0)
    if asset_value > cfg.max_position_pct * state.equity:
        raise RiskRejected("A posição passaria do limite por ativo.")
    if order.sector != "unknown":
        sector_value = value + sum(p.qty * p.entry for p in state.positions.values() if p.sector == order.sector)
        if sector_value > cfg.max_sector_pct * state.equity:
            raise RiskRejected("A compra passaria do limite por setor.")
