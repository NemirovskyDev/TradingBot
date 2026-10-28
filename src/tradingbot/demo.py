"""Dados de exemplo (sintéticos) para a demo pública: não representam nenhum ativo real."""
import numpy as np
import pandas as pd


def make_synthetic_prices(n: int = 1500, seed: int = 7) -> pd.DataFrame:
    """Passeio aleatório com tendência e um ciclo de ~80 dias, para as estratégias terem o que operar."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    log_returns = rng.normal(0.0003, 0.011, n) + 0.010 * np.cos(2 * np.pi * t / 80)
    close = 100 * np.exp(np.cumsum(log_returns))
    open_ = np.concatenate([[100.0], close[:-1]])
    spread = np.abs(rng.normal(0, 0.004, n)) * close
    return pd.DataFrame(
        {
            "open": open_,
            "high": np.maximum(open_, close) + spread,
            "low": np.minimum(open_, close) - spread,
            "close": close,
            "volume": rng.integers(800_000, 1_200_000, n).astype(float),
        },
        index=pd.bdate_range("2018-01-01", periods=n),
    )


