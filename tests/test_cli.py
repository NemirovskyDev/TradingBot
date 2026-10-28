from pathlib import Path

import pytest

from tradingbot import cli
from tradingbot.broker import NullBroker
from tradingbot.data import DataError
from tradingbot.risk import Order

CONFIG = str(Path(__file__).resolve().parents[1] / "config.toml")


def _args(tmp_path, ticker="SPY", strategy="sma_cross"):
    return ["backtest", ticker, "--strategy", strategy, "--start", "2020-01-01", "--end", "2022-01-01",
            "--config", CONFIG, "--out", str(tmp_path)]


def test_null_broker_never_places_orders():
    with pytest.raises(NotImplementedError):
        NullBroker().submit_order(Order("SPY", "buy", 1, 100.0, 95.0))
    with pytest.raises(NotImplementedError):
        NullBroker().get_positions()


def test_backtest_command_prints_verdict_and_writes_report(monkeypatch, capsys, tmp_path, synthetic_prices):
    monkeypatch.setattr(cli, "get_prices", lambda *a, **k: synthetic_prices(500, 4))
    assert cli.main(_args(tmp_path)) == 0
    out = capsys.readouterr().out
    assert "Veredito" in out and "Comprar e segurar" in out
    assert list(tmp_path.glob("SPY_*.md"))


def test_backtest_short_history_still_exits_0(monkeypatch, capsys, tmp_path, synthetic_prices):
    monkeypatch.setattr(cli, "get_prices", lambda *a, **k: synthetic_prices(6, 1))
    assert cli.main(_args(tmp_path)) == 0
    assert "Ainda não passou" in capsys.readouterr().out


def test_unknown_ticker_returns_2_with_message(monkeypatch, capsys, tmp_path):
    def boom(*a, **k):
        raise DataError("Sem dados para ZZZZ.")

    monkeypatch.setattr(cli, "get_prices", boom)
    assert cli.main(_args(tmp_path, "ZZZZ")) == 2
    err = capsys.readouterr().err
    assert "Sem dados para ZZZZ" in err and "Traceback" not in err


def test_path_like_ticker_is_rejected_without_network(tmp_path):
    assert cli.main(_args(tmp_path, "../x")) == 2


def test_missing_config_returns_2(monkeypatch, capsys, tmp_path, synthetic_prices):
    monkeypatch.setattr(cli, "get_prices", lambda *a, **k: synthetic_prices(100, 1))
    args = _args(tmp_path)
    args[args.index("--config") + 1] = str(tmp_path / "nao-existe.toml")
    assert cli.main(args) == 2
    assert "configuração" in capsys.readouterr().err.lower()


def test_unknown_strategy_is_rejected_by_argparse(tmp_path):
    with pytest.raises(SystemExit) as exc:
        cli.main(_args(tmp_path, strategy="inexistente"))
    assert exc.value.code == 2


def test_analyze_without_key_still_exits_0(monkeypatch, capsys, synthetic_prices):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(cli, "get_prices", lambda *a, **k: synthetic_prices(200, 1))
    assert cli.main(["analyze", "SPY"]) == 0
    assert "indisponível" in capsys.readouterr().out


def test_analysis_text_distinguishes_failed_sections_from_no_data():
    from tradingbot.analyst import AnalystReport, Finding

    rep = AnalystReport("SPY", {"tecnica": [Finding("ok", "src")], "fundamentos": [], "sentimento": [], "risco_noticias": []},
                        available=True, failed=["sentimento"])
    text = cli._analysis_text(rep)
    assert "falha na consulta" in text and text.count("sem dados nesta seção") == 2
