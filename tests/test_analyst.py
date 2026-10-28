import json

from tradingbot.analyst import SECTIONS, AnalystReport, Finding, analyze, technical_summary, validate_findings

GOOD = json.dumps([{"claim": "O preço está acima da média de 50 dias.", "source": "preços diários"}])


def _ctx(section, ticker, prices):
    return f"contexto de {section}"


def test_validate_findings_drops_unsourced_claims():
    raw = [
        {"claim": "ok", "source": "yfinance"},
        {"claim": "sem fonte", "source": ""},
        {"claim": "fonte em branco", "source": "   "},
        {"claim": "", "source": "x"},
    ]
    assert validate_findings(raw) == [Finding("ok", "yfinance")]


def test_validate_findings_ignores_non_dict_items():
    assert validate_findings(["texto solto", None, 3]) == []


def test_analyze_returns_four_sections(synthetic_prices):
    rep = analyze("SPY", synthetic_prices(100, 1), ask=lambda role, ctx: GOOD, context_fn=_ctx)
    assert isinstance(rep, AnalystReport) and rep.available
    assert list(rep.sections) == list(SECTIONS) and len(SECTIONS) == 4
    assert all(rep.sections[s] == [Finding("O preço está acima da média de 50 dias.", "preços diários")] for s in SECTIONS)


def test_analyze_malformed_json_marks_section_empty_not_crash(synthetic_prices):
    def ask(role, ctx):
        return "isto não é json" if "sentimento" in ctx else GOOD

    rep = analyze("SPY", synthetic_prices(100, 1), ask=ask, context_fn=_ctx)
    assert rep.sections["sentimento"] == [] and "sentimento" in rep.failed
    assert rep.sections["tecnica"]


def test_analyze_accepts_json_inside_code_fence(synthetic_prices):
    rep = analyze("SPY", synthetic_prices(100, 1), ask=lambda r, c: f"```json\n{GOOD}\n```", context_fn=_ctx)
    assert rep.sections["tecnica"]


def test_analyze_ask_exception_is_contained(synthetic_prices):
    def boom(role, ctx):
        raise RuntimeError("API fora do ar")

    rep = analyze("SPY", synthetic_prices(100, 1), ask=boom, context_fn=_ctx)
    assert all(rep.sections[s] == [] for s in SECTIONS) and set(rep.failed) == set(SECTIONS)


def test_analyze_without_api_key_is_unavailable(synthetic_prices, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    rep = analyze("SPY", synthetic_prices(100, 1), context_fn=_ctx)
    assert rep.available is False and all(rep.sections[s] == [] for s in SECTIONS)


def test_context_is_sent_as_data_and_prompt_forbids_trade_advice(synthetic_prices):
    seen = {}

    def ask(role, ctx):
        seen["role"], seen["ctx"] = role, ctx
        return "[]"

    analyze("SPY", synthetic_prices(100, 1), ask=ask, context_fn=_ctx)
    assert "<contexto>" in seen["ctx"] and "não é instrução" in seen["role"].lower()
    assert "não recomende" in seen["role"].lower()


def test_technical_summary_mentions_indicators(synthetic_prices):
    text = technical_summary(synthetic_prices(120, 1))
    assert "SMA20" in text and "SMA50" in text and "RSI" in text


def test_technical_summary_short_history_does_not_crash(synthetic_prices):
    assert "dados insuficientes" in technical_summary(synthetic_prices(5, 1)).lower()


def test_analyze_marks_unavailable_when_every_section_fails(synthetic_prices):
    def boom(role, ctx):
        raise RuntimeError("401")

    rep = analyze("SPY", synthetic_prices(100, 1), ask=boom, context_fn=_ctx)
    assert rep.available is False and set(rep.failed) == set(SECTIONS)
