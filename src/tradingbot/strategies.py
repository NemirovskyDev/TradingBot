"""Estratégias de swing determinísticas. Cada uma devolve 1 (comprado) ou 0 (fora) por dia,
calculada só com dados até aquele dia; o backtest executa o sinal na abertura do dia seguinte."""
from collections.abc import Callable

import numpy as np
import pandas as pd


def sma_cross(prices: pd.DataFrame, fast: int = 50, slow: int = 200) -> pd.Series:
    close = prices["close"]
    fast_ma = close.rolling(fast, min_periods=fast).mean()
    slow_ma = close.rolling(slow, min_periods=slow).mean()
    return (fast_ma > slow_ma).astype(int).rename("signal")


def _rsi(close: pd.Series, period: int) -> pd.Series:
    """RSI de Wilder. Fica aqui porque o analyst usa o indicador, mesmo sem estratégia de RSI."""
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).where(loss != 0, 100.0)


def donchian(prices: pd.DataFrame, entry: int = 55, exit_: int = 20) -> pd.Series:
    """Rompimento de Donchian (turtles): compra acima da máxima de `entry` dias, sai abaixo da mínima de `exit_` dias."""
    upper = prices["high"].rolling(entry, min_periods=entry).max().shift(1)
    lower = prices["low"].rolling(exit_, min_periods=exit_).min().shift(1)
    held = 0
    out = []
    for close, up, low in zip(prices["close"], upper, lower):
        if np.isnan(up) or np.isnan(low):
            held = 0
        elif held == 0 and close > up:
            held = 1
        elif held == 1 and close < low:
            held = 0
        out.append(held)
    return pd.Series(out, index=prices.index, name="signal", dtype=int)


def momentum(prices: pd.DataFrame, lookback: int = 252) -> pd.Series:
    """Momentum absoluto (Antonacci): comprado enquanto o retorno dos últimos 12 meses é positivo."""
    close = prices["close"]
    ret = close / close.shift(lookback) - 1
    return (ret > 0).astype(int).rename("signal")


STRATEGIES: dict[str, Callable[..., pd.Series]] = {
    "sma_cross": sma_cross,
    "donchian": donchian,
    "momentum": momentum,
}

# Frases mostradas ao usuário (front) para cada compra e saída por sinal.
REASONS: dict[str, dict[str, str]] = {
    "sma_cross": {
        "entry": "A média de 50 dias cruzou a de 200 para cima (o chamado golden cross).",
        "exit": "A média de 50 dias cruzou a de 200 para baixo.",
    },
    "donchian": {
        "entry": "O preço passou da máxima dos últimos 55 dias: um rompimento de alta.",
        "exit": "O preço caiu abaixo da mínima dos últimos 20 dias, e o bot saiu.",
    },
    "momentum": {
        "entry": "O preço está acima do de 12 meses atrás: tendência de alta.",
        "exit": "O preço caiu abaixo do de 12 meses atrás: a tendência de alta acabou.",
    },
}
