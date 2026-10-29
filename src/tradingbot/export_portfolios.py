"""Exportação das carteiras: roda as metodologias e os exemplos por perfil, cada uma desde a data mais antiga possível, e grava web/public/data/portfolios.json."""
import json
import os
from dataclasses import asdict
from datetime import date
from pathlib import Path

import pandas as pd

from tradingbot.portfolio import (
    ALL_PORTFOLIOS,
    LABELS,
    REBALANCE_COST,
    annual_returns,
    drawdown,
    metrics,
    own_start,
    period_ends,
    simulate,
)
from tradingbot.profiles import PROFILES

SCHEMA = 2
SAMPLE_EVERY = 5  # uma observação por semana de pregão: o gráfico não precisa de mais e o arquivo fica pequeno
RELATED = 2  # quantas metodologias parecidas cada perfil lista
BENCHMARKS = (("cdi", "CDI", "CDI"), ("ibovespa", "Ibovespa (BOVA11)", "BOVA11"), ("sp500", "S&P 500 em reais (IVVB11)", "IVVB11"))
ASSUMPTIONS = (
    "Tudo em reais: os ativos em dólar foram convertidos pelo câmbio de cada dia.",
    f"Cada rebalanceamento ou troca custa {REBALANCE_COST:.1%} do valor negociado. Não há imposto de renda, que reduziria o resultado.",
    "Decisões tomadas no fechamento do último pregão do período, com dados só até aquele dia.",
    "Cada carteira começa na data mais antiga em que todos os seus ativos têm preço. Para comparar de forma justa, a tabela também mostra a janela comum, a mesma para todas.",
    "Antes de o ETF existir, um substituto preenche o passado: o índice Bovespa para o BOVA11, o S&P 500 (SPY) em reais para o IVVB11, o ouro futuro para o GLD, e EFA, AGG e DVY para VXUS, BND e SCHD/VYM. O substituto não tem as taxas do ETF.",
    "Preços do Yahoo Finance; o caixa é o CDI do Banco Central. Os FIIs já vêm com os proventos, mas o Yahoo só tem o histórico da maioria deles a partir de 2014.",
    "O Yahoo não traz os proventos do BOVA11 nem do índice: o Ibovespa e a fatia de ações brasileiras ficam um pouco abaixo do real.",
    "Os FIIs são uma cesta de fundos grandes que existem hoje, o que favorece o resultado (viés de sobrevivência).",
    "Os ativos dos exemplos por perfil (dividendos, crescimento e swing) foram escolhidos hoje, sabendo quais prosperaram: o resultado é otimista e não mostra o que alguém teria conseguido escolhendo na época.",
    "Simulação com dados passados: não é recomendação e não garante resultado futuro.",
)


def _rebased(series: pd.Series, start: pd.Timestamp) -> pd.Series:
    part = series.loc[start:].dropna()
    return 100 * part / part.iloc[0]


def _padded(series: pd.Series, sample: pd.Index, digits: int) -> list[float | None]:
    return [None if pd.isna(v) else round(float(v), digits) for v in series.reindex(sample)]


def _summary(equity: pd.Series, cash: pd.Series) -> dict:
    return {"metrics": metrics(equity, cash), "annual_returns": annual_returns(equity)}


def build_payload(table: pd.DataFrame, start: pd.Timestamp | None) -> dict:
    """Cada carteira começa em `own_start` (ou em `start`, se for mais tarde). A janela comum é o maior desses inícios."""
    starts = {}
    for m in ALL_PORTFOLIOS:
        first = own_start(table, m)
        starts[m.id] = first if start is None else max(first, start)
    earliest, common = min(starts.values()), max(starts.values())
    window = table.loc[earliest:]
    sample = window.index[::SAMPLE_EVERY]
    if sample[-1] != window.index[-1]:
        sample = sample.append(window.index[-1:])
    cash = table["CDI"]

    portfolios = []
    for m in ALL_PORTFOLIOS:
        begin = starts[m.id]
        equity = simulate(table, m.make_target(), period_ends(table.loc[begin:].index, m.rebalance), begin)
        common_equity = _rebased(equity, common)
        references = {}
        for id_, _name, column in BENCHMARKS:
            references[id_] = _summary(_rebased(table[column], begin), cash)
        portfolios.append(
            {
                "id": m.id,
                "name": m.name,
                "kind": m.kind,
                "author": m.author,
                "summary": m.summary,
                "rule": m.rule,
                "rebalance": m.rebalance,
                "components": [{"label": LABELS[k], "weight": w} for k, w in (m.weights or ())],
                "universe": [LABELS[k] for k in m.universe],
                "start": str(begin.date()),
                "equity": _padded(equity, sample, 4),
                "drawdown": _padded(drawdown(equity), sample, 6),
                **_summary(equity, cash),
                "metrics_common": metrics(common_equity, cash),
                "benchmarks": references,
            }
        )

    benchmarks = []
    for id_, name, column in BENCHMARKS:
        full = _rebased(table[column], earliest)
        benchmarks.append(
            {
                "id": id_,
                "name": name,
                "equity": _padded(full, sample, 4),
                "drawdown": _padded(drawdown(full), sample, 6),
                **_summary(full, cash),
                "metrics_common": metrics(_rebased(table[column], common), cash),
            }
        )

    by_id = {p["id"]: p for p in portfolios}
    classic = [p for p in portfolios if p["kind"] == "classic"]
    profiles = []
    for profile in PROFILES:
        related: list[str] = []
        if profile.related_by:
            key, order = profile.related_by
            ranked = sorted(
                (p for p in classic if p["metrics_common"][key] is not None),
                key=lambda p: p["metrics_common"][key],
                reverse=order == "desc",
            )
            related = [p["id"] for p in ranked[:RELATED]]
        item = asdict(profile)
        item.pop("related_by")
        item["related_ids"] = related
        assert profile.portfolio_id in by_id, profile.portfolio_id
        profiles.append(item)

    return {
        "schema": SCHEMA,
        "currency": "BRL",
        "generated_at": date.today().isoformat(),
        "start": str(earliest.date()),
        "common_start": str(common.date()),
        "end": str(window.index[-1].date()),
        "dates": [str(d.date()) for d in sample],
        "assumptions": list(ASSUMPTIONS),
        "portfolios": portfolios,
        "benchmarks": benchmarks,
        "profiles": profiles,
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
