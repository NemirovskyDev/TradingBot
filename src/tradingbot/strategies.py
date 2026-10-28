"""Estratégias de swing determinísticas. Cada uma devolve 1 (comprado) ou 0 (fora) por dia,
calculada só com dados até aquele dia; o backtest executa o sinal na abertura do dia seguinte."""
from collections.abc import Callable

import numpy as np
import pandas as pd


def sma_cross(prices: pd.DataFrame, fast: int = 20, slow: int = 50) -> pd.Series:
    close = prices["close"]
    fast_ma = close.rolling(fast, min_periods=fast).mean()
    slow_ma = close.rolling(slow, min_periods=slow).mean()
    return (fast_ma > slow_ma).astype(int).rename("signal")


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).where(loss != 0, 100.0)


def rsi_reversion(
    prices: pd.DataFrame, period: int = 14, buy_below: float = 30, exit_above: float = 50
) -> pd.Series:
    rsi = _rsi(prices["close"], period)
    held = 0
    out = []
    for value in rsi:
        if np.isnan(value):
            held = 0
        elif held == 0 and value < buy_below:
            held = 1
        elif held == 1 and value > exit_above:
            held = 0
        out.append(held)
    return pd.Series(out, index=prices.index, name="signal", dtype=int)


def momentum(prices: pd.DataFrame, lookback: int = 60) -> pd.Series:
    close = prices["close"]
    ret = close / close.shift(lookback) - 1
    return (ret > 0).astype(int).rename("signal")


STRATEGIES: dict[str, Callable[..., pd.Series]] = {
    "sma_cross": sma_cross,
    "rsi_reversion": rsi_reversion,
    "momentum": momentum,
}

# Frases mostradas ao usuário (front) para cada compra e saída por sinal.
REASONS: dict[str, dict[str, str]] = {
    "sma_cross": {
        "entry": "A média curta cruzou a longa para cima.",
        "exit": "A média curta cruzou a longa para baixo.",
    },
    "rsi_reversion": {
        "entry": "O ativo caiu demais (RSI abaixo de 30) e o bot apostou na recuperação.",
        "exit": "O RSI voltou acima de 50, então o bot realizou o ganho.",
    },
    "momentum": {
        "entry": "O preço está acima do de 60 dias atrás: tendência de alta.",
        "exit": "O preço caiu abaixo do de 60 dias atrás: a tendência de alta acabou.",
    },
}
