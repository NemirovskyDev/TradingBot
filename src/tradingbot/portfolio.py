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
    "QQQ": "Nasdaq dos EUA (QQQ)",
    "SCHD": "ETF de dividendos dos EUA (SCHD)",
    "VYM": "ETF de dividendos dos EUA (VYM)",
    "KO": "Coca-Cola (KO)",
    "PG": "Procter & Gamble (PG)",
    "JNJ": "Johnson & Johnson (JNJ)",
    "PEP": "PepsiCo (PEP)",
    "BBAS3": "Banco do Brasil (BBAS3)",
    "ITUB4": "Itaú (ITUB4)",
    "TAEE11": "Taesa (TAEE11)",
    "VIVT3": "Vivo (VIVT3)",
    "NVDA": "Nvidia (NVDA)",
    "TSLA": "Tesla (TSLA)",
    "AMD": "AMD (AMD)",
    "NFLX": "Netflix (NFLX)",
    "META": "Meta (META)",
    "AMZN": "Amazon (AMZN)",
    "PETR4": "Petrobras (PETR4)",
    "VALE3": "Vale (VALE3)",
}


def period_ends(index: pd.DatetimeIndex, freq: str) -> set[pd.Timestamp]:
    """Último pregão de cada ano ('yearly') ou mês ('monthly') do índice; 'daily' é todo pregão."""
    if freq == "daily":
        return set(index)
    if freq == "yearly":
        key = np.asarray(index.year)
    elif freq == "monthly":
        key = np.asarray(index.year * 100 + index.month)
    else:
        raise ValueError(f"Frequência desconhecida: {freq!r} (use 'yearly', 'monthly' ou 'daily').")
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


def breakout_target(assets: tuple[str, ...], cash: str, entry: int = 55, exit_: int = 20) -> Target:
    """Donchian sobre fechamentos: cada ativo entra ao passar da máxima de `entry` dias e sai abaixo da mínima de `exit_` dias; a fatia dos que estão fora vai para o caixa.
    Guarda o estado entre chamadas (o simulador chama dia a dia), então cada dia novo custa só a janela, não o histórico todo."""
    state = {"pos": 0, "held": dict.fromkeys(assets, False)}

    def target(_date: pd.Timestamp, history: pd.DataFrame) -> dict[str, float]:
        n = len(history)
        if n < state["pos"]:  # outra simulação com a mesma função: recomeça
            state["pos"], state["held"] = 0, dict.fromkeys(assets, False)
        pos = state["pos"]
        base = max(0, pos - entry)
        for asset in assets:
            col = history[asset].iloc[base:n].to_numpy(dtype=float)
            held = state["held"][asset]
            for i in range(pos - base, n - base):
                close = col[i]
                high = col[max(0, i - entry) : i]
                low = col[max(0, i - exit_) : i]
                if np.isnan(close) or len(high) < entry or np.isnan(high).any() or np.isnan(low).any():
                    held = False
                elif not held and close > high.max():
                    held = True
                elif held and close < low.min():
                    held = False
            state["held"][asset] = held
        state["pos"] = n
        share = 1 / len(assets)
        weights = {a: (share if state["held"][a] else 0.0) for a in assets}
        weights[cash] = 1.0 - sum(weights.values())
        return weights

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
    kind: str = "classic"  # "classic" (metodologia publicada) ou "profile" (exemplo montado pelo projeto para um perfil)
    warmup_days: int = 0  # dias de histórico que as regras de sinal precisam antes do início (o sinal não existe antes disso)
    optional: tuple[str, ...] = ()  # instrumentos que podem faltar no começo: sem preço, ficam fora em vez de adiar o início


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
        "monthly", _IVY + ("CDI",), None, lambda: ivy_target(_IVY, "CDI"), warmup_days=320,
    ),
    Methodology(
        "momentum-dual", "Momentum dual (GEM)", "Gary Antonacci",
        "Fica 100% em um ativo por vez: ações dos EUA, ações de fora ou títulos, conforme o momentum de 12 meses.",
        "No fechamento de cada mês: se as ações dos EUA renderam mais que o caixa em 12 meses, fica com o melhor entre EUA e fora; senão, vai para títulos.",
        "monthly", ("VTI", "VXUS", "BND", "CDI"), None, lambda: gem_target("VTI", "VXUS", "BND", "CDI"), warmup_days=380,
    ),
)


def _profile(id_: str, name: str, summary: str, rule: str, weights: dict[str, float]) -> Methodology:
    return Methodology(id_, name, "Exemplo montado pelo projeto", summary, rule, "yearly", tuple(weights), tuple(weights.items()), static_target(weights), "profile")


_SWING = ("NVDA", "TSLA", "AMD", "NFLX", "META", "AMZN", "PETR4", "VALE3")

PROFILE_PORTFOLIOS: tuple[Methodology, ...] = (
    _profile(
        "renda-dividendos", "Renda de dividendos",
        "Fundos imobiliários, ações pagadoras do Brasil e dos EUA e ETFs de dividendos, para viver de proventos.",
        "Rebalanceia uma vez por ano: 40% FIIs, 20% ações pagadoras da B3, 20% ETFs de dividendos dos EUA e 20% ações pagadoras dos EUA. Os proventos já entram reinvestidos nos números.",
        {"FII": 0.40, "BBAS3": 0.05, "ITUB4": 0.05, "TAEE11": 0.05, "VIVT3": 0.05, "SCHD": 0.10, "VYM": 0.10, "KO": 0.05, "PG": 0.05, "JNJ": 0.05, "PEP": 0.05},
    ),
    _profile(
        "estabilidade", "Estabilidade",
        "Quase tudo em caixa, com fatias pequenas de FIIs, ouro e bolsa para render um pouco acima do CDI.",
        "Rebalanceia uma vez por ano: 70% CDI, 15% FIIs, 10% ouro e 5% ações dos EUA em reais.",
        {"CDI": 0.70, "FII": 0.15, "GLD": 0.10, "IVVB11": 0.05},
    ),
    _profile(
        "crescimento", "Crescimento",
        "Foco em bolsa: S&P 500, Nasdaq e Ibovespa, para fazer o dinheiro crescer aceitando as quedas.",
        "Rebalanceia uma vez por ano: 50% S&P 500 em reais, 25% Nasdaq e 25% Ibovespa.",
        {"IVVB11": 0.50, "QQQ": 0.25, "BOVA11": 0.25},
    ),
    Methodology(
        "swing-alto-risco", "Swing em ativos voláteis", "Exemplo montado pelo projeto",
        "Compra e venda de ativos voláteis em ciclos de dias a semanas, seguindo o rompimento de máximas.",
        "Confere todo dia: cada um dos 8 ativos fica com 12,5% da carteira enquanto passar da máxima de 55 dias, e sai abaixo da mínima de 20 dias; o que está fora fica em CDI. Cada troca custa 0,1%.",
        "daily", _SWING + ("CDI",), None, lambda: breakout_target(_SWING, "CDI"), "profile",
        warmup_days=90, optional=("TSLA", "META"),  # os outros 6 existem desde antes de 2004; sem eles a carteira seria só CDI
    ),
)

ALL_PORTFOLIOS: tuple[Methodology, ...] = METHODOLOGIES + PROFILE_PORTFOLIOS


def own_start(table: pd.DataFrame, method: Methodology) -> pd.Timestamp:
    """Primeiro dia em que a carteira pode começar: todos os instrumentos obrigatórios têm preço, mais o aquecimento do sinal."""
    firsts = []
    for name in method.universe:
        if name in method.optional:
            continue
        valid = table[name].dropna()
        if valid.empty:
            raise ValueError(f"Sem preços para {name}: a carteira {method.name} não tem janela para simular.")
        firsts.append(valid.index[0])
    first = max(firsts)
    if method.warmup_days:
        later = table.index[table.index >= first + pd.Timedelta(days=method.warmup_days)]
        if later.empty:
            raise ValueError(f"Histórico curto demais para o aquecimento de {method.name}.")
        return later[0]
    return first
