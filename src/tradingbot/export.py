"""Exporta o resultado do backtest em JSON versionado para o front (contrato: seção 5 da spec do front)."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from tradingbot.backtest import BacktestResult
from tradingbot.evaluate import Verdict
from tradingbot.strategies import REASONS

SCHEMA = 1
STOP_REASON = "O preço tocou o stop de proteção."
END_REASON = "O período do teste terminou com a posição aberta."
_RUN_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")  # vira nome de arquivo (use fullmatch: nada de caminhos nem "\n")


def _day(ts) -> str:
    return pd.Timestamp(ts).date().isoformat()


def _write(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return path


def export_run(
    run_id: str,
    ticker: str,
    strategy: str,
    params: dict,
    prices: pd.DataFrame,
    result: BacktestResult,
    benchmark: BacktestResult,
    verdict: Verdict,
    out_dir: Path,
    synthetic: bool = False,
) -> Path:
    """Grava `out_dir/runs/{run_id}.json`. Datas AAAA-MM-DD; retornos e queda como frações (0,124 = 12,4%)."""
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError(f"run_id inválido: {run_id!r}")
    if strategy not in REASONS:
        raise ValueError(f"estratégia desconhecida: {strategy!r}")
    reasons = REASONS[strategy]
    exit_reason = {"stop": STOP_REASON, "signal": reasons["exit"], "end": END_REASON}

    trades = [
        {
            "id": f"t{i}",
            "entry_date": _day(t.entry_date), "entry_price": round(float(t.entry_price), 4),
            "exit_date": _day(t.exit_date), "exit_price": round(float(t.exit_price), 4),
            "qty": int(t.qty), "stop": round(float(t.stop), 4), "pnl_pct": round(float(t.pnl_pct), 6),
            "reason_entry": reasons["entry"], "reason_exit": exit_reason[t.exit_kind],
        }
        for i, t in enumerate(result.trades.itertuples(index=False), start=1)
    ]
    m = result.metrics
    payload = {
        "meta": {
            "ticker": ticker, "strategy": strategy, "params": params,
            "start": _day(prices.index[0]), "end": _day(prices.index[-1]),
            "initial_capital": round(float(benchmark.equity.iloc[0]), 2),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "synthetic": synthetic,
        },
        "prices": [
            {"date": _day(ts), "open": round(float(r.open), 4), "high": round(float(r.high), 4),
             "low": round(float(r.low), 4), "close": round(float(r.close), 4), "volume": int(r.volume)}
            for ts, r in zip(prices.index, prices.itertuples(index=False))
        ],
        "equity": [
            {"date": _day(ts), "strategy": round(float(s), 2), "buy_hold": round(float(b), 2)}
            for ts, s, b in zip(result.equity.index, result.equity, benchmark.equity)
        ],
        "trades": trades,
        "blocked": [{"date": b["date"], "ticker": ticker, "reason": b["reason"]} for b in result.blocked],
        "metrics": {
            "total_return": round(m["total_return"], 6),
            "benchmark_return": round(benchmark.metrics["total_return"], 6),
            "max_drawdown": round(m["max_drawdown"], 6),
            "sharpe": round(m["sharpe"], 4),
            "n_trades": int(m["n_trades"]),
        },
        "verdict": {"passed": verdict.passed, "reasons": list(verdict.reasons)},
    }
    return _write(Path(out_dir) / "runs" / f"{run_id}.json", payload)


def write_index(out_dir: Path, runs: list[dict]) -> Path:
    return _write(Path(out_dir) / "index.json", {"schema": SCHEMA, "runs": runs})


def publish(out_dir: Path, runs: list[dict], prune: bool = True) -> Path:
    """Grava o índice e, se `prune`, apaga de runs/ só os arquivos de execuções que não estão no índice novo."""
    out = Path(out_dir)
    if prune:
        keep = {f"{r['id']}.json" for r in runs}
        for stale in (out / "runs").glob("*.json"):
            if stale.name not in keep:
                stale.unlink()
    return write_index(out, runs)
