"""Backtest diário de um ativo: o sinal do dia t é executado na abertura de t+1, com slippage e comissão,
stop por ATR e o portão de risco. Uma posição por vez, sem alavancagem."""
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from tradingbot.config import CostConfig, RiskConfig
from tradingbot.risk import Order, PortfolioState, RiskRejected, atr_stop, check_order, position_size

TRADE_COLUMNS = ["entry_date", "entry_price", "exit_date", "exit_price", "qty", "stop", "pnl_pct", "exit_kind"]
_TICKER = "ASSET"


@dataclass
class BacktestResult:
    equity: pd.Series
    trades: pd.DataFrame
    metrics: dict[str, float]
    blocked: list[dict[str, str]]


def _metrics(equity: pd.Series, initial_capital: float, n_trades: int) -> dict[str, float]:
    returns = equity.pct_change().dropna()
    std = returns.std()
    sharpe = 0.0 if len(returns) < 2 or not std or np.isnan(std) else float(returns.mean() / std * math.sqrt(252))
    return {
        "total_return": float(equity.iloc[-1] / initial_capital - 1),
        "max_drawdown": float((1 - equity / equity.cummax()).max()),
        "sharpe": sharpe,
        "n_trades": float(n_trades),
    }


def run_backtest(
    prices: pd.DataFrame,
    signals: pd.Series,
    risk_cfg: RiskConfig,
    cost_cfg: CostConfig,
    initial_capital: float = 10_000.0,
) -> BacktestResult:
    if prices.empty:
        raise ValueError("prices está vazio")
    if not signals.index.equals(prices.index):
        raise ValueError("signals precisa ter o mesmo índice de prices")

    slip = cost_cfg.slippage_bps / 10_000
    cash = initial_capital
    pos: dict | None = None
    pending: str | None = None  # "buy" | "sell", decidido no fechamento anterior
    pending_stop = 0.0
    wait_reset = False  # após stop ou bloqueio, só volta a comprar depois de um sinal 0
    trades: list[dict] = []
    blocked: list[dict[str, str]] = []
    equity: list[float] = []
    week_key = None
    week_start_equity = initial_capital

    def close_position(date, price: float, kind: str) -> None:
        nonlocal cash, pos
        proceeds = pos["qty"] * price - cost_cfg.commission
        cost = pos["qty"] * pos["entry_price"] + pos["entry_commission"]
        cash += proceeds
        trades.append(
            {
                "entry_date": pos["entry_date"], "entry_price": pos["entry_price"], "exit_date": date,
                "exit_price": price, "qty": pos["qty"], "stop": pos["stop"],
                "pnl_pct": (proceeds - cost) / cost, "exit_kind": kind,
            }
        )
        pos = None

    for t, date in enumerate(prices.index):
        row = prices.iloc[t]
        mark = cash + (pos["qty"] * row["open"] if pos else 0.0)
        key = date.isocalendar()[:2]
        if key != week_key:
            week_key, week_start_equity = key, mark

        if pending == "buy" and pos is None:
            entry = float(row["open"]) * (1 + slip)
            qty = 0
            reason = None
            try:
                qty = position_size(cash, entry, pending_stop, risk_cfg)
                qty = min(qty, math.floor(max(cash - cost_cfg.commission, 0) / entry))
                if qty == 0:
                    reason = "Capital insuficiente para respeitar o risco por trade."
                else:
                    check_order(
                        Order(_TICKER, "buy", qty, entry, pending_stop),
                        PortfolioState(equity=cash, positions={}, week_start_equity=week_start_equity),
                        risk_cfg,
                    )
            except RiskRejected as exc:
                reason = str(exc)
            if reason:
                blocked.append({"date": date.date().isoformat(), "reason": reason})
                wait_reset = True
            else:
                cash -= qty * entry + cost_cfg.commission
                pos = {
                    "qty": qty, "entry_price": entry, "entry_date": date, "stop": pending_stop,
                    "entry_commission": cost_cfg.commission,
                }
        elif pending == "sell" and pos is not None:
            close_position(date, float(row["open"]) * (1 - slip), "signal")
        pending = None

        if pos is not None and row["low"] <= pos["stop"]:
            fill = min(float(row["open"]), pos["stop"]) * (1 - slip)  # abertura abaixo do stop = gap
            close_position(date, fill, "stop")
            wait_reset = True

        if t == len(prices) - 1 and pos is not None:
            close_position(date, float(row["close"]) * (1 - slip), "end")

        equity.append(cash + (pos["qty"] * float(row["close"]) if pos else 0.0))

        sig = int(signals.iloc[t])
        if sig == 0:
            wait_reset = False
            if pos is not None:
                pending = "sell"
        elif pos is None and not wait_reset:
            pending = "buy"
            pending_stop = atr_stop(prices, t)

    equity_s = pd.Series(equity, index=prices.index, name="equity")
    trades_df = pd.DataFrame(trades, columns=TRADE_COLUMNS)
    return BacktestResult(equity_s, trades_df, _metrics(equity_s, initial_capital, len(trades_df)), blocked)


def buy_and_hold(prices: pd.DataFrame, initial_capital: float = 10_000.0) -> BacktestResult:
    """Compra tudo no primeiro fechamento e segura; sem custos (referência de comparação)."""
    if prices.empty:
        raise ValueError("prices está vazio")
    close = prices["close"].astype(float)
    equity = (initial_capital / close.iloc[0] * close).rename("equity")
    trades = pd.DataFrame(
        [{
            "entry_date": prices.index[0], "entry_price": close.iloc[0], "exit_date": prices.index[-1],
            "exit_price": close.iloc[-1], "qty": initial_capital / close.iloc[0], "stop": np.nan,
            "pnl_pct": close.iloc[-1] / close.iloc[0] - 1, "exit_kind": "end",
        }],
        columns=TRADE_COLUMNS,
    )
    return BacktestResult(equity, trades, _metrics(equity, initial_capital, 1), [])


def split_train_test(prices: pd.DataFrame, test_fraction: float = 0.3) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Corte temporal (o teste é o trecho mais recente), sem embaralhar."""
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction deve estar entre 0 e 1 (exclusivo)")
    cut = int(round(len(prices) * (1 - test_fraction)))
    if cut < 1 or cut >= len(prices):
        raise ValueError("histórico curto demais para dividir em treino e teste")
    return prices.iloc[:cut], prices.iloc[cut:]


def walk_forward_windows(
    prices: pd.DataFrame, train_days: int = 504, test_days: int = 126
) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    """Janelas deslizantes: cada teste começa onde o treino termina e os testes não se sobrepõem."""
    windows = []
    start = 0
    while start + train_days + test_days <= len(prices):
        train = prices.iloc[start : start + train_days]
        test = prices.iloc[start + train_days : start + train_days + test_days]
        windows.append((train, test))
        start += test_days
    return windows
