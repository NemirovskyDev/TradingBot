from pathlib import Path

import pytest

from tradingbot.config import load_config


def _write(tmp_path: Path, risk_per_trade: float) -> Path:
    p = tmp_path / "config.toml"
    p.write_text(
        f"initial_capital = 5000.0\n[risk]\nrisk_per_trade = {risk_per_trade}\n[costs]\nslippage_bps = 7.5\n",
        encoding="utf-8",
    )
    return p


def test_load_config_reads_risk_values(tmp_path):
    cfg = load_config(_write(tmp_path, 0.02))
    assert cfg.risk.risk_per_trade == 0.02
    assert cfg.costs.slippage_bps == 7.5
    assert cfg.initial_capital == 5000.0


def test_load_config_uses_defaults_for_missing_keys(tmp_path):
    cfg = load_config(_write(tmp_path, 0.02))
    assert cfg.risk.max_open_positions == 5


@pytest.mark.parametrize("value", [0, -0.01, 0.06])
def test_load_config_rejects_out_of_range_risk(tmp_path, value):
    with pytest.raises(ValueError):
        load_config(_write(tmp_path, value))


def test_default_config_file_loads():
    cfg = load_config(Path(__file__).resolve().parents[1] / "config.toml")
    assert cfg.risk.risk_per_trade == 0.01


def test_load_config_rejects_unknown_key_as_value_error(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text("[risk]\nfoo = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="foo"):
        load_config(p)
