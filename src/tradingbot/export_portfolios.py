"""Exportação das carteiras: roda as 7 metodologias numa janela comum e grava web/public/data/portfolios.json."""
import json
import os
from datetime import date
from pathlib import Path

import pandas as pd

from tradingbot.portfolio import (
    LABELS,
    METHODOLOGIES,
    REBALANCE_COST,
    annual_returns,
    drawdown,
    metrics,
    period_ends,
    simulate,
)

SCHEMA = 1
SAMPLE_EVERY = 5  # uma observação por semana de pregão: o gráfico não precisa de mais e o arquivo fica pequeno
# Colunas que toda metodologia usa; a janela comum começa onde todas existem.
BENCHMARKS = (("cdi", "CDI", "CDI"), ("ibovespa", "Ibovespa (BOVA11)", "BOVA11"), ("sp500", "S&P 500 em reais (IVVB11)", "IVVB11"))
ASSUMPTIONS = (
    "Tudo em reais: os ativos em dólar foram convertidos pelo câmbio de cada dia.",
    f"Cada rebalanceamento custa {REBALANCE_COST:.1%} do valor negociado. Não há imposto de renda, que reduziria o resultado.",
    "Decisões tomadas no fechamento do último pregão do período, com dados só até aquele dia.",
    "Preços do Yahoo Finance; o caixa é o CDI do Banco Central. Os FIIs já vêm com os proventos.",
    "O Yahoo não traz os proventos do BOVA11: o Ibovespa e a fatia de ações brasileiras ficam um pouco abaixo do real.",
    "Os FIIs são uma cesta de fundos grandes que existem hoje, o que favorece o resultado (viés de sobrevivência).",
    "Simulação com dados passados: não é recomendação e não garante resultado futuro.",
)


def _common_start(table: pd.DataFrame) -> pd.Timestamp:
    """Primeiro dia em que todos os instrumentos usados pelas metodologias têm preço."""
    needed = sorted({k for m in METHODOLOGIES for k in m.universe})
    firsts = {}
    for name in needed:
        valid = table[name].dropna()
        if valid.empty:
            raise ValueError(f"Sem preços para {name}: não há janela comum para comparar as carteiras.")
        firsts[name] = valid.index[0]
    return max(firsts.values())


def _series(id_: str, name: str, equity: pd.Series, cash: pd.Series, sample: pd.Index) -> dict:
    return {
        "id": id_,
        "name": name,
        "equity": [round(float(v), 4) for v in equity.loc[sample]],
        "drawdown": [round(float(v), 6) for v in drawdown(equity).loc[sample]],
        "metrics": metrics(equity, cash),
        "annual_returns": annual_returns(equity),
    }


def build_payload(table: pd.DataFrame, start: pd.Timestamp | None) -> dict:
    """`start` None usa a janela comum; um início anterior a ela seria impossível e levanta erro."""
    common = _common_start(table)
    start = common if start is None else max(start, common)
    window = table.loc[start:]
    sample = window.index[::SAMPLE_EVERY]
    if sample[-1] != window.index[-1]:
        sample = sample.append(window.index[-1:])
    cash = table["CDI"]
    portfolios = []
    for m in METHODOLOGIES:
        dates = period_ends(window.index, m.rebalance)
        equity = simulate(table, m.make_target(), dates, start)
        item = _series(m.id, m.name, equity, cash, sample)
        item.update(
            author=m.author,
            summary=m.summary,
            rule=m.rule,
            rebalance=m.rebalance,
            components=[{"label": LABELS[k], "weight": w} for k, w in (m.weights or ())],
            universe=[LABELS[k] for k in m.universe],
        )
        portfolios.append(item)
    benchmarks = []
    for id_, name, column in BENCHMARKS:
        equity = 100 * window[column] / window[column].iloc[0]
        benchmarks.append(_series(id_, name, equity, cash, sample))
    return {
        "schema": SCHEMA,
        "currency": "BRL",
        "generated_at": date.today().isoformat(),
        "start": str(window.index[0].date()),
        "end": str(window.index[-1].date()),
        "dates": [str(d.date()) for d in sample],
        "assumptions": list(ASSUMPTIONS),
        "portfolios": portfolios,
        "benchmarks": benchmarks,
    }


def export_portfolios(table: pd.DataFrame, out: Path, start: pd.Timestamp | None = None) -> Path:
    """Grava portfolios.json de forma atômica: se algo falhar, o arquivo publicado não muda."""
    payload = build_payload(table, start)
    out.mkdir(parents=True, exist_ok=True)
    final = out / "portfolios.json"
    tmp = out / "portfolios.json.tmp"
    tmp.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=None, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, final)
    return final
