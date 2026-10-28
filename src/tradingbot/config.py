"""Configuração do bot: limites de risco, custos e capital inicial, lidos de um TOML."""
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RiskConfig:
    risk_per_trade: float = 0.01
    max_open_positions: int = 5
    max_position_pct: float = 0.20
    max_sector_pct: float = 0.40
    weekly_loss_limit: float = 0.05


@dataclass(frozen=True)
class CostConfig:
    commission: float = 0.0
    slippage_bps: float = 5.0


@dataclass(frozen=True)
class AppConfig:
    risk: RiskConfig = field(default_factory=RiskConfig)
    costs: CostConfig = field(default_factory=CostConfig)
    initial_capital: float = 10_000.0


def _validate(risk: RiskConfig, costs: CostConfig, capital: float) -> None:
    if not 0 < risk.risk_per_trade <= 0.05:
        raise ValueError("risk_per_trade deve estar entre 0 (exclusivo) e 0,05")
    for name in ("max_position_pct", "max_sector_pct", "weekly_loss_limit"):
        if not 0 < getattr(risk, name) <= 1:
            raise ValueError(f"{name} deve estar entre 0 (exclusivo) e 1")
    if risk.max_open_positions < 1:
        raise ValueError("max_open_positions deve ser pelo menos 1")
    if costs.commission < 0 or costs.slippage_bps < 0:
        raise ValueError("custos não podem ser negativos")
    if capital <= 0:
        raise ValueError("initial_capital deve ser positivo")


def load_config(path: Path) -> AppConfig:
    """Lê o TOML; chaves ausentes usam os padrões e valores fora da faixa levantam ValueError."""
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    try:
        risk = RiskConfig(**raw.get("risk", {}))
        costs = CostConfig(**raw.get("costs", {}))
    except TypeError as exc:  # chave desconhecida ou mal escrita no TOML
        raise ValueError(f"Chave desconhecida na configuração: {exc}") from exc
    capital = float(raw.get("initial_capital", 10_000.0))
    _validate(risk, costs, capital)
    return AppConfig(risk=risk, costs=costs, initial_capital=capital)
