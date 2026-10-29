import json
from pathlib import Path

import pytest

from tradingbot import cli, export_real
from tradingbot.catalog import Asset, write_catalog
from tradingbot.data import DataError
from tradingbot.demo import make_synthetic_prices
from tradingbot.evaluate import Evaluation, Verdict
from tradingbot.strategies import STRATEGIES

CONFIG = str(Path(__file__).resolve().parents[1] / "config.toml")
CATALOG = [
    Asset("AAA", "Alfa Corp", "Ações EUA"),
    Asset("BBB.SA", "Beta ON", "Ações B3"),
    Asset("BAD", "Sem dados", "Ações EUA"),
    Asset("SHORT", "Histórico curto", "Cripto"),
]


def _fake_prices(ticker, start, end, *a, **k):
    if ticker == "BAD":
        raise DataError("Sem dados para BAD.")
    if ticker == "SHORT":
        return make_synthetic_prices(120, 3)
    return make_synthetic_prices(1500, 7 if ticker == "AAA" else 9)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    catalog = write_catalog(CATALOG, tmp_path / "assets.json")
    monkeypatch.setattr(export_real, "get_prices", _fake_prices)
    monkeypatch.setattr(export_real.time, "sleep", lambda s: None)  # as novas tentativas não precisam esperar nos testes
    monkeypatch.setattr(cli, "MAX_SKIPPED_FRACTION", 0.9)  # o catálogo de teste tem metade dos ativos quebrados de propósito
    return tmp_path, catalog


def _run(tmp_path, catalog, *extra):
    out = tmp_path / "data"
    code = cli.main(["export", "--real", "--catalog", str(catalog), "--out", str(out), "--config", CONFIG, *extra])
    return code, out


def _index(out):
    return json.loads((out / "index.json").read_text(encoding="utf-8"))


def test_real_export_writes_three_runs_per_asset_and_skips_failures(setup, capsys):
    tmp_path, catalog = setup
    code, out = _run(tmp_path, catalog)
    assert code == 0
    ids = sorted(r["id"] for r in _index(out)["runs"])
    assert ids == sorted(f"{s}-{strat}" for s in ("aaa", "bbb_sa") for strat in ("momentum", "rsi_reversion", "sma_cross"))
    text = capsys.readouterr().out
    assert "BAD" in text and "SHORT" in text  # os ignorados são listados, com o motivo


def test_real_export_index_carries_name_category_and_real_data_flag(setup):
    tmp_path, catalog = setup
    _, out = _run(tmp_path, catalog)
    run = next(r for r in _index(out)["runs"] if r["id"] == "bbb_sa-sma_cross")
    assert run["ticker"] == "BBB.SA" and run["name"] == "Beta ON" and run["category"] == "Ações B3"
    data = json.loads((out / "runs" / "bbb_sa-sma_cross.json").read_text(encoding="utf-8"))
    assert data["meta"]["synthetic"] is False and data["meta"]["ticker"] == "BBB.SA"


def test_real_export_requires_exactly_one_data_mode(setup):
    tmp_path, catalog = setup
    with pytest.raises(SystemExit):
        cli.main(["export", "--out", str(tmp_path / "d")])
    with pytest.raises(SystemExit):
        cli.main(["export", "--out", str(tmp_path / "d"), "--real", "--synthetic"])


def test_real_export_removes_only_stale_runs_and_leaves_other_files_alone(setup):
    tmp_path, catalog = setup
    out = tmp_path / "data"
    (out / "runs").mkdir(parents=True)
    (out / "runs" / "velho-sma_cross.json").write_text("{}", encoding="utf-8")
    (out / "LEIAME.txt").write_text("não mexa", encoding="utf-8")
    _run(tmp_path, catalog)
    assert not (out / "runs" / "velho-sma_cross.json").exists()
    assert (out / "LEIAME.txt").read_text(encoding="utf-8") == "não mexa"
    assert (out / "runs" / "aaa-sma_cross.json").exists()


def test_real_export_with_empty_result_returns_error(setup, monkeypatch, capsys):
    tmp_path, catalog = setup
    monkeypatch.setattr(export_real, "get_prices", lambda *a, **k: (_ for _ in ()).throw(DataError("fora do ar")))
    code, out = _run(tmp_path, catalog)
    assert code == 2
    assert not (out / "index.json").exists()  # nada é gravado se nenhum ativo funcionou
    assert "nenhum ativo" in capsys.readouterr().err.lower()


def test_real_export_retries_a_transient_download_failure(setup, monkeypatch):
    tmp_path, catalog = setup
    attempts = {"AAA": 0, "BAD": 0}

    def flaky(ticker, start, end, *a, **k):
        if ticker in attempts:
            attempts[ticker] += 1
        if ticker == "AAA" and attempts["AAA"] == 1:
            raise DataError("falha de rede")  # só na primeira tentativa
        return _fake_prices(ticker, start, end)

    monkeypatch.setattr(export_real, "get_prices", flaky)
    _, out = _run(tmp_path, catalog)
    assert "AAA" in {r["ticker"] for r in _index(out)["runs"]} and attempts["AAA"] == 2
    assert attempts["BAD"] == 2  # sem dados de verdade: tenta duas vezes e desiste


def test_limit_mode_never_deletes_published_files_and_warns(setup, capsys):
    tmp_path, catalog = setup
    out = tmp_path / "data"
    (out / "runs").mkdir(parents=True)
    published = out / "runs" / "publicado-sma_cross.json"
    published.write_text("{}", encoding="utf-8")
    code, _ = _run(tmp_path, catalog, "--limit", "1")
    assert code == 0 and published.exists()
    assert {r["ticker"] for r in _index(out)["runs"]} == {"AAA"}
    assert "modo de teste" in capsys.readouterr().out


def test_mass_failure_keeps_what_is_published(setup, monkeypatch, capsys):
    tmp_path, catalog = setup
    out = tmp_path / "data"
    (out / "runs").mkdir(parents=True)
    (out / "index.json").write_text('{"schema": 1, "runs": ["antigo"]}', encoding="utf-8")
    (out / "runs" / "antigo-sma_cross.json").write_text("{}", encoding="utf-8")
    # só AAA funciona: 3 de 4 ativos falham (75% > 25%), como acontece quando a fonte limita as requisições
    monkeypatch.setattr(cli, "MAX_SKIPPED_FRACTION", 0.25)
    monkeypatch.setattr(export_real, "get_prices", lambda t, s, e, *a, **k: _fake_prices(t, s, e) if t == "AAA" else (_ for _ in ()).throw(DataError("limite")))
    code, _ = _run(tmp_path, catalog)
    assert code == 2
    assert "antigo" in (out / "index.json").read_text(encoding="utf-8")  # índice e arquivos antigos intactos
    assert (out / "runs" / "antigo-sma_cross.json").exists()
    assert "falharam" in capsys.readouterr().err


def test_an_asset_is_all_or_nothing_across_strategies(setup, monkeypatch):
    tmp_path, catalog = setup
    real = export_real.evaluate_detailed

    def fail_last_strategy(prices, strategy, *a, **k):
        if strategy is STRATEGIES["sma_cross"]:  # a última na ordem alfabética
            return Evaluation(Verdict(False, ["x"]))
        return real(prices, strategy, *a, **k)

    monkeypatch.setattr(export_real, "evaluate_detailed", fail_last_strategy)
    monkeypatch.setattr(export_real, "get_prices", lambda t, s, e, *a, **k: _fake_prices("AAA", s, e))
    code, out = _run(tmp_path, catalog, "--limit", "2")
    assert code == 2  # nenhum ativo ficou completo
    assert not (out / "index.json").exists()
