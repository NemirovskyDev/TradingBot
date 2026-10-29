"""Carteiras: motor de simulação em reais e as 7 metodologias de alocação do painel.

Tudo é determinístico e usa só dados até a data de cada decisão. As decisões (rebalanceamento ou sinal de
tendência) são tomadas no fechamento do último pregão do período e valem a partir do dia seguinte."""
import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

REBALANCE_COST = 0.001  # 0,1% do valor negociado em cada rebalanceamento (corretagem e spread); sem imposto
TRADING_DAYS = 252

Target = Callable[[pd.Timestamp, pd.DataFrame], dict[str, float]]

LABELS: dict[str, str] = {
    "BOVA11": "Ações brasileiras (BOVA11)",
    "FII": "Fundos imobiliários (cesta de FIIs)",
    "IVVB11": "Ações dos EUA em reais (IVVB11)",
    "CDI": "Caixa (CDI)",
    "VTI": "Ações dos EUA (VTI)",
    "VBR": "Small caps value dos EUA (VBR)",
    "VXUS": "Ações fora dos EUA (VXUS)",
    "EFA": "Ações de países desenvolvidos (EFA)",
    "VNQ": "Imóveis dos EUA (VNQ)",
    "TLT": "Títulos do Tesouro longos (TLT)",
    "IEF": "Títulos do Tesouro intermediários (IEF)",
    "SHY": "Títulos do Tesouro curtos (SHY)",
    "BND": "Títulos dos EUA (BND)",
    "GLD": "Ouro (GLD)",
    "DBC": "Commodities (DBC)",
}


def period_ends(index: pd.DatetimeIndex, freq: str) -> set[pd.Timestamp]:
    """Último pregão de cada ano ('yearly') ou mês ('monthly') do índice."""
    if freq == "yearly":
        key = np.asarray(index.year)
    elif freq == "monthly":
        key = np.asarray(index.year * 100 + index.month)
    else:
        raise ValueError(f"Frequência desconhecida: {freq!r} (use 'yearly' ou 'monthly').")
    return set(pd.Series(index, index=index).groupby(key).last())


def _checked(weights: dict[str, float]) -> dict[str, float]:
    if any(w < 0 for w in weights.values()) or abs(sum(weights.values()) - 1) > 1e-9:
        raise ValueError(f"Os pesos precisam somar 100% e não podem ser negativos (soma = {sum(weights.values()):.4f}).")
    return weights


def simulate(
    prices: pd.DataFrame,
    target: Target,
    rebalance_dates: set[pd.Timestamp],
    start: pd.Timestamp,
    cost: float = REBALANCE_COST,
    initial: float = 100.0,
) -> pd.Series:
    """Valor da carteira por dia a partir de `start`. A alocação inicial não paga custo; cada rebalanceamento paga `cost` sobre o valor negociado."""
    window = prices.loc[start:]
    if window.empty:
        raise ValueError(f"Sem dados a partir do início {start.date()}.")
    units: dict[str, float] = {}
    values = []
    for date, row in window.iterrows():
        first = not units
        if first or date in rebalance_dates:
            weights = _checked(target(date, prices.loc[:date]))
            held = {k: v for k, v in weights.items() if v > 0}
            missing = [k for k in held if pd.isna(row.get(k))]
            if missing:
                raise ValueError(f"Preço ausente em {date.date()} para {missing}.")
            value = initial if first else sum(units[k] * row[k] for k in units)
            if not first:
                traded = sum(abs(value * held.get(k, 0.0) - units.get(k, 0.0) * row[k]) for k in set(held) | set(units))
                value -= traded * cost
            units = {k: value * w / row[k] for k, w in held.items()}
        missing = [k for k in units if pd.isna(row[k])]
        if missing:
            raise ValueError(f"Preço ausente em {date.date()} para {missing}.")
        values.append(sum(units[k] * row[k] for k in units))
    return pd.Series(values, index=window.index, name="equity")


def drawdown(equity: pd.Series) -> pd.Series:
    return equity / equity.cummax() - 1


def _clean(value: float) -> float | None:
    return round(float(value), 8) if value is not None and math.isfinite(value) else None


def metrics(equity: pd.Series, cash: pd.Series) -> dict[str, float | None]:
    """Retorno total, CAGR, volatilidade anual, queda máxima e Sharpe (excesso sobre o caixa)."""
    ret = equity.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    total = equity.iloc[-1] / equity.iloc[0] - 1
    cagr = (1 + total) ** (1 / years) - 1 if years > 0 and total > -1 else None
    excess = ret - cash.reindex(equity.index).pct_change().dropna()
    std = excess.std(ddof=1)
    sharpe = excess.mean() / std * math.sqrt(TRADING_DAYS) if std and std > 1e-9 else None  # ~0: a série é o próprio caixa
    return {
        "total_return": _clean(total),
        "cagr": _clean(cagr) if cagr is not None else None,
        "volatility": _clean(ret.std(ddof=1) * math.sqrt(TRADING_DAYS)) if len(ret) > 1 else 0,
        "max_drawdown": _clean(drawdown(equity).min()),
        "sharpe": _clean(sharpe) if sharpe is not None else None,
    }


def annual_returns(equity: pd.Series) -> list[dict]:
    """Retorno de cada ano civil; o primeiro e o último anos podem ser parciais (marcados)."""
    last_of_year = equity.groupby(equity.index.year).last()
    rows = []
    previous = equity.iloc[0]
    for year, end in last_of_year.items():
        in_year = equity[equity.index.year == year]
        partial = (year == equity.index[0].year and in_year.index[0] > pd.Timestamp(year=year, month=1, day=10)) or (
            year == equity.index[-1].year and in_year.index[-1] < pd.Timestamp(year=year, month=12, day=20)
        )
        rows.append({"year": int(year), "return": _clean(end / previous - 1), "partial": bool(partial)})
        previous = end
    return rows


def static_target(weights: dict[str, float]) -> Callable[[], Target]:
    return lambda: (lambda _date, _history: dict(weights))


def ivy_target(assets: tuple[str, ...], cash: str) -> Target:
    """Faber/Ivy: peso igual; um ativo só entra se fechou o mês acima da média de 10 meses, senão a fatia vai para o caixa."""

    def target(_date: pd.Timestamp, history: pd.DataFrame) -> dict[str, float]:
        share = 1 / len(assets)
        weights = {cash: 0.0}
        for asset in assets:
            monthly = history[asset].dropna().resample("MS").last().dropna()
            above = len(monthly) >= 10 and monthly.iloc[-1] > monthly.tail(10).mean()
            weights[asset] = share if above else 0.0
            if not above:
                weights[cash] += share
        return weights

    return target


def gem_target(us: str, ex_us: str, bonds: str, cash: str) -> Target:
    """Momentum dual (Antonacci), com o caixa (CDI) como referência: ações dos EUA só se renderam mais que o caixa em 12 meses; entre EUA e fora, o de maior retorno; senão, títulos."""

    def target(_date: pd.Timestamp, history: pd.DataFrame) -> dict[str, float]:
        window = history[[us, ex_us, bonds, cash]].iloc[-(TRADING_DAYS + 1) :]
        if len(window) <= TRADING_DAYS or window.isna().any().any():
            return {cash: 1.0}
        r12 = window.iloc[-1] / window.iloc[0] - 1
        if r12[us] > r12[cash]:
            return {us: 1.0} if r12[us] > r12[ex_us] else {ex_us: 1.0}
        return {bonds: 1.0}

    return target


@dataclass(frozen=True)
class Methodology:
    id: str
    name: str
    author: str
    summary: str
    rule: str
    rebalance: str  # "yearly" | "monthly"
    universe: tuple[str, ...]
    weights: tuple[tuple[str, float], ...] | None  # None quando os pesos mudam com o sinal
    make_target: Callable[[], Target]


def _fixed(
    id_: str, name: str, author: str, summary: str, rule: str, weights: dict[str, float], rebalance: str = "yearly"
) -> Methodology:
    return Methodology(id_, name, author, summary, rule, rebalance, tuple(weights), tuple(weights.items()), static_target(weights))


_IVY = ("VTI", "EFA", "IEF", "DBC", "VNQ")

METHODOLOGIES: tuple[Methodology, ...] = (
    _fixed(
        "arca", "ARCA", "Thiago Nigro (Primo Rico)",
        "Quatro quadrantes de 25%: ações brasileiras, fundos imobiliários, caixa e investimentos no exterior.",
        "Rebalanceia uma vez por ano, voltando cada quadrante a 25%.",
        {"BOVA11": 0.25, "FII": 0.25, "CDI": 0.25, "IVVB11": 0.25},
    ),
    _fixed(
        "permanente", "Carteira Permanente", "Harry Browne",
        "Um quarto em ações, um em títulos longos, um em ouro e um em caixa: uma fatia para cada cenário econômico.",
        "Rebalanceia uma vez por ano, voltando cada fatia a 25%.",
        {"VTI": 0.25, "TLT": 0.25, "GLD": 0.25, "CDI": 0.25},
    ),
    _fixed(
        "all-weather", "All Weather", "Ray Dalio",
        "Muito peso em títulos para equilibrar o risco entre ações, juros, ouro e commodities.",
        "Rebalanceia uma vez por ano: 30% ações, 40% títulos longos, 15% intermediários, 7,5% ouro e 7,5% commodities.",
        {"VTI": 0.30, "TLT": 0.40, "IEF": 0.15, "GLD": 0.075, "DBC": 0.075},
    ),
    _fixed(
        "golden-butterfly", "Golden Butterfly", "Tyler (Portfolio Charts)",
        "Cinco fatias de 20%: ações, small caps value, títulos longos, títulos curtos e ouro.",
        "Rebalanceia uma vez por ano, voltando cada fatia a 20%.",
        {"VTI": 0.20, "VBR": 0.20, "TLT": 0.20, "SHY": 0.20, "GLD": 0.20},
    ),
    _fixed(
        "sessenta-quarenta", "60/40 (três fundos)", "Bogleheads",
        "A referência clássica: 60% em ações (40% EUA e 20% fora) e 40% em títulos.",
        "Rebalanceia uma vez por ano para 40% VTI, 20% VXUS e 40% BND.",
        {"VTI": 0.40, "VXUS": 0.20, "BND": 0.40},
    ),
    Methodology(
        "faber-ivy", "Tendência de 10 meses (Ivy)", "Mebane Faber",
        "Cinco classes de 20%; cada uma só fica na carteira enquanto estiver em tendência de alta.",
        "No fechamento de cada mês, mantém a classe se ela fechou acima da média de 10 meses; senão, a fatia vai para o caixa.",
        "monthly", _IVY + ("CDI",), None, lambda: ivy_target(_IVY, "CDI"),
    ),
    Methodology(
        "momentum-dual", "Momentum dual (GEM)", "Gary Antonacci",
        "Fica 100% em um ativo por vez: ações dos EUA, ações de fora ou títulos, conforme o momentum de 12 meses.",
        "No fechamento de cada mês: se as ações dos EUA renderam mais que o caixa em 12 meses, fica com o melhor entre EUA e fora; senão, vai para títulos.",
        "monthly", ("VTI", "VXUS", "BND", "CDI"), None, lambda: gem_target("VTI", "VXUS", "BND", "CDI"),
    ),
)
