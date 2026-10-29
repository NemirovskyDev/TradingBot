import pytest

from tradingbot import cli
from tradingbot.catalog import Asset, load_catalog, write_catalog
from tradingbot.catalog_build import (
    build_catalog,
    check_expanded,
    merge,
    parse_brapi_funds,
    parse_brapi_stocks,
    parse_sp500,
    pretty_name,
    rank_by_market_cap,
)
from tradingbot.catalog_seed import SEED

SP_HTML = """
<table><thead><tr><th>Symbol</th><th>Security</th><th>GICS Sector</th></tr></thead><tbody>
<tr><td>AAPL</td><td>Apple Inc.</td><td>Information Technology</td></tr>
<tr><td>BRK.B</td><td>Berkshire Hathaway</td><td>Financials</td></tr>
<tr><td>LLY</td><td>Eli Lilly and Company</td><td>Health Care</td></tr>
</tbody></table>
"""

STOCKS = {
    "stocks": [
        {"stock": "PETR4", "name": "PETROBRAS PN", "close": 52.5, "volume": 5e7, "market_cap": 7.2e11},
        {"stock": "ITUB4", "name": "ITAU UNIBANCO PN", "close": 33.0, "volume": 3e7, "market_cap": 3.1e11},
        {"stock": "SEMCAP3", "name": "Sem valor de mercado", "close": 1.0, "volume": 10, "market_cap": None},
        {"stock": "PETR4F", "name": "PETROBRAS PN (FRACIONARIO)", "close": 52.5, "volume": 1e5, "market_cap": 7.2e11},
        {"stock": "IBOV11", "name": "ISHARES IBOVESPA FUNDO DE INDICE", "close": 120.0, "volume": 1e6, "market_cap": 5e9},
        {"stock": "TAEE11", "name": "TAESA UNIT", "close": 36.0, "volume": 1e6, "market_cap": 1.2e10},
        {"stock": "AAPL34", "name": "APPLE INC BDR", "close": 60.0, "volume": 1e6, "market_cap": 9e9},  # BDR: não é ação da B3
        {"stock": "ECOR3", "name": "ECORODOVIAS INFRAESTRUTURA E LOGISTICA S.A.", "close": 8.0, "volume": 1e6, "market_cap": 8e9},
    ]
}

FUNDS = {
    "stocks": [
        {"stock": "HGLG11", "name": "CSHG LOGISTICA", "close": 160.0, "volume": 90000},
        {"stock": "FNAM11", "name": "FNAM11", "close": 0.49, "volume": 16238000},  # preço de centavos: não é um FII negociável
        {"stock": "ABCD34", "name": "BDR qualquer", "close": 80.0, "volume": 50000},
        {"stock": "MXRF11", "name": "MAXI RENDA", "close": 9.6, "volume": 80000},
        {"stock": "ZERO11", "name": "Sem volume", "close": 50.0, "volume": 0},
        {"stock": "SPXU11", "name": "SPXU11", "close": 100.0, "volume": 9e5},  # nome igual ao ticker: a brapi não sabe o que é
        {"stock": "VGIA11", "name": "VALORA CRA FIAGRO", "close": 9.5, "volume": 1e5},
        {"stock": "BOVB11", "name": "ETF BRADESCO IBOVESPA FUNDO DE INDICE", "close": 100.0, "volume": 9e5},
        {"stock": "BISE11", "name": "CLASSE A DE COTAS DO BRADESCO ISENTO 2031 FIC DE FIF EM INFRAESTRUTURA RENDA FIXA", "close": 90.0, "volume": 1e5},
        {"stock": "UTLI11", "name": "IT NOW UTILIDADE PUBLICA FUNDO DE ÍNDICE", "close": 80.0, "volume": 1e5},
    ]
}

US = "Ações EUA"


def test_parse_sp500_converts_dots_to_dashes_for_yfinance():
    assets = parse_sp500(SP_HTML)
    assert [a.ticker for a in assets] == ["AAPL", "BRK-B", "LLY"]
    assert assets[1] == Asset("BRK-B", "Berkshire Hathaway", US)


def test_parse_brapi_stocks_adds_sa_suffix_and_drops_fractional_lots_etfs_and_no_market_cap():
    assets = parse_brapi_stocks(STOCKS)
    # sem PETR4F (lote fracionário), IBOV11 (ETF) nem AAPL34 (BDR); ECOR3 fica: "infraestrutura" no nome só barra fundos (final 11)
    assert [a.ticker for a in assets] == ["PETR4.SA", "ITUB4.SA", "TAEE11.SA", "ECOR3.SA"]
    assert all(a.category == "Ações B3" for a in assets)


def test_parse_brapi_funds_keeps_only_tradable_reit_tickers():
    assets = parse_brapi_funds(FUNDS)
    assert [a.ticker for a in assets] == ["HGLG11.SA", "MXRF11.SA"]
    assert all(a.category == "FIIs" for a in assets)


def test_parse_brapi_handles_empty_or_malformed_payloads():
    assert parse_brapi_stocks({}) == []
    assert parse_brapi_funds({"stocks": None}) == []
    assert parse_brapi_stocks({"stocks": [{"stock": None}, "texto", {"name": "x"}]}) == []


def test_rank_by_market_cap_sorts_desc_with_missing_and_failing_last():
    caps = {"A": 1.0, "B": 9.0, "C": None}

    def cap(ticker):
        if ticker == "D":
            raise RuntimeError("sem dados")
        return caps[ticker]

    assets = [Asset(t, t, US) for t in "ABCD"]
    assert [a.ticker for a in rank_by_market_cap(assets, cap)] == ["B", "A", "C", "D"]


def test_merge_keeps_seed_first_dedupes_case_insensitively_and_caps_per_category():
    seed = [Asset("AAPL", "Apple", US)]
    extras = {US: [Asset("aapl", "Apple dup", US), Asset("MSFT", "Microsoft", US), Asset("NVDA", "NVIDIA", US)]}
    merged = merge(seed, extras, {US: 1})
    assert [a.ticker for a in merged] == ["AAPL", "MSFT"]
    assert merged[0].name == "Apple"


def test_build_catalog_with_fakes_never_duplicates_and_respects_limits():
    seed = [Asset("AAPL", "Apple", US), Asset("PETR4.SA", "Petrobras PN", "Ações B3")]
    calls = {"html": 0, "json": []}

    def fetch_html(url):
        calls["html"] += 1
        return SP_HTML

    def fetch_json(url):
        calls["json"].append(url)
        return FUNDS if "fund" in url else STOCKS

    caps = {"BRK-B": 9e11, "LLY": 8e11}
    assets = build_catalog(seed, fetch_html=fetch_html, fetch_json=fetch_json, cap_fn=lambda t: caps.get(t), sp_n=1, b3_n=5, fii_n=1)
    tickers = [a.ticker for a in assets]
    assert tickers == ["AAPL", "PETR4.SA", "BRK-B", "ITUB4.SA", "TAEE11.SA", "ECOR3.SA", "HGLG11.SA"]
    assert len(tickers) == len({t.upper() for t in tickers})
    assert calls["html"] == 1 and len(calls["json"]) == 2


def _expanded():
    return [*SEED, Asset("ZZZ", "Zed", US), Asset("ZZZZ3.SA", "Zed ON", "Ações B3"), Asset("ZZZZ11.SA", "Zed FII", "FIIs")]


def test_cli_catalog_writes_a_valid_catalog_file(monkeypatch, tmp_path):
    fake = _expanded()
    monkeypatch.setattr(cli, "build_from_network", lambda sp, b3, fii: fake)
    out = tmp_path / "assets.json"
    assert cli.main(["catalog", "--out", str(out)]) == 0
    assert load_catalog(out) == fake
    assert not list(tmp_path.glob("*.tmp"))  # a gravação atômica não deixa arquivo temporário


def test_cli_catalog_with_an_empty_source_keeps_the_existing_file(monkeypatch, tmp_path, capsys):
    out = tmp_path / "assets.json"
    out.write_text('[{"ticker": "KEEP", "name": "Antigo", "category": "Ações EUA"}]', encoding="utf-8")
    monkeypatch.setattr(cli, "build_from_network", lambda sp, b3, fii: list(SEED))  # brapi devolveu nada: só o seed
    assert cli.main(["catalog", "--out", str(out)]) == 2
    assert "KEEP" in out.read_text(encoding="utf-8")
    assert "nada foi gravado" in capsys.readouterr().err


def test_cli_catalog_network_error_is_a_message_not_a_traceback(monkeypatch, tmp_path, capsys):
    def boom(sp, b3, fii):
        raise ConnectionError("sem rede")

    monkeypatch.setattr(cli, "build_from_network", boom)
    assert cli.main(["catalog", "--out", str(tmp_path / "a.json")]) == 2
    err = capsys.readouterr().err
    assert "sem rede" in err and "Traceback" not in err


def test_write_catalog_validates_before_touching_the_file(tmp_path):
    out = tmp_path / "assets.json"
    out.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        write_catalog([Asset("A", "a", US), Asset("a", "dup", US)], out)
    assert out.read_text(encoding="utf-8") == "[]"


def test_check_expanded_requires_new_assets_from_every_requested_source():
    check_expanded(_expanded(), {US: 5, "Ações B3": 5, "FIIs": 5})
    with pytest.raises(ValueError, match="FIIs"):
        check_expanded([*SEED, Asset("ZZZ", "Zed", US), Asset("ZZZZ3.SA", "Zed ON", "Ações B3")], {US: 5, "Ações B3": 5, "FIIs": 5})
    check_expanded(list(SEED), {US: 0, "Ações B3": 0, "FIIs": 0})  # nada pedido, nada exigido


def test_merge_keeps_one_share_class_per_b3_company_and_skips_us_second_classes():
    seed = [Asset("PETR4.SA", "Petrobras PN", "Ações B3")]
    extras = {
        "Ações B3": [Asset("PETR3.SA", "Petrobras ON", "Ações B3"), Asset("ITUB4.SA", "Itaú", "Ações B3"), Asset("ITUB3.SA", "Itaú ON", "Ações B3")],
        US: [Asset("GOOG", "Alphabet C", US), Asset("MSFT", "Microsoft", US)],
    }
    merged = merge(seed, extras, {"Ações B3": 5, US: 5})
    assert [a.ticker for a in merged] == ["PETR4.SA", "ITUB4.SA", "MSFT"]


def test_pretty_name_removes_legal_suffixes_fixes_case_and_limits_length():
    assert pretty_name("PETROLEO BRASILEIRO S.A. PETROBRAS", "PETR4") == "Petroleo Brasileiro Petrobras"
    assert pretty_name("CSHG LOGISTICA FUNDO DE INVESTIMENTO IMOBILIARIO", "HGLG11") == "Cshg Logistica"
    assert pretty_name("BANCO DO BRASIL S/A", "BBAS3") == "Banco do Brasil"
    long = pretty_name("FUNDO " + "MUITO LONGO " * 12 + "RESPONSABILIDADE LIMITADA", "XXXX11")
    assert len(long) <= 43 and long.endswith("…")
    assert pretty_name("ABCD11", "ABCD11") == "ABCD11"  # nome igual ao ticker: usa o ticker


def test_rank_by_market_cap_treats_nan_as_missing():
    caps = {"A": float("nan"), "B": 5.0, "C": 9.0}
    assets = [Asset(t, t, US) for t in "ABC"]
    assert [a.ticker for a in rank_by_market_cap(assets, caps.get)] == ["C", "B", "A"]
