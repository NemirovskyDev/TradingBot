import json

import pytest

from tradingbot.catalog import CATEGORIES, DEFAULT_PATH, Asset, load_catalog, slug


def _write(tmp_path, items):
    p = tmp_path / "assets.json"
    p.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    return p


def _item(ticker="AAPL", name="Apple", category="Ações EUA"):
    return {"ticker": ticker, "name": name, "category": category}


@pytest.mark.parametrize(
    "ticker,expected",
    [("PETR4.SA", "petr4_sa"), ("BTC-USD", "btc_usd"), ("BRK-B", "brk_b"), ("^BVSP", "bvsp"), ("AAPL", "aapl")],
)
def test_slug_is_a_safe_lowercase_id(ticker, expected):
    assert slug(ticker) == expected


def test_load_catalog_reads_assets(tmp_path):
    assets = load_catalog(_write(tmp_path, [_item(), _item("PETR4.SA", "Petrobras PN", "Ações B3")]))
    assert assets == [Asset("AAPL", "Apple", "Ações EUA"), Asset("PETR4.SA", "Petrobras PN", "Ações B3")]


def test_load_catalog_rejects_duplicate_tickers_case_insensitively(tmp_path):
    with pytest.raises(ValueError, match="duplicado"):
        load_catalog(_write(tmp_path, [_item("AAPL"), _item("aapl")]))


def test_load_catalog_rejects_unknown_category(tmp_path):
    with pytest.raises(ValueError, match="categoria"):
        load_catalog(_write(tmp_path, [_item(category="Outra")]))


@pytest.mark.parametrize("bad", ["", "../x", "A B", "A" * 30])
def test_load_catalog_rejects_unsafe_tickers(tmp_path, bad):
    with pytest.raises(ValueError, match="ticker"):
        load_catalog(_write(tmp_path, [_item(ticker=bad)]))


def test_load_catalog_rejects_empty_name(tmp_path):
    with pytest.raises(ValueError, match="nome"):
        load_catalog(_write(tmp_path, [_item(name="  ")]))


def test_load_catalog_rejects_slug_collisions(tmp_path):
    with pytest.raises(ValueError, match="id"):
        load_catalog(_write(tmp_path, [_item("A.B"), _item("A-B")]))


def test_load_catalog_rejects_non_list_json(tmp_path):
    p = tmp_path / "assets.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_catalog(p)


def test_packaged_catalog_is_valid_and_covers_every_category():
    assets = load_catalog(DEFAULT_PATH)
    assert len(assets) >= 78
    assert {a.category for a in assets} == set(CATEGORIES)
    tickers = {a.ticker for a in assets}
    assert {"SPY", "PETR4.SA", "HGLG11.SA", "BTC-USD", "BOVA11.SA"} <= tickers
