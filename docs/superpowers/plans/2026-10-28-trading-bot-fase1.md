# TradingBot Fase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Assistente de linha de comando que analisa ativos e testa estratégias de swing no histórico, com portão de risco determinístico, sem enviar nenhuma ordem.

**Architecture:** Pacote Python `tradingbot` com módulos pequenos (`config`, `data`, `strategies`, `risk`, `backtest`, `evaluate`, `analyst`, `broker`, `cli`). Estratégias e risco são código determinístico; o Claude só escreve o relatório do `analyst`. O backtest executa o sinal do dia t na abertura do dia t+1.

**Tech Stack:** Python 3.11+, pandas, numpy, yfinance, anthropic (SDK), pytest.

**Spec:** `docs/superpowers/specs/2026-10-28-trading-bot-design.md`

## Global Constraints
- Fase 1 não envia ordens: `broker` é só interface; nenhuma implementação real.
- Horizonte swing, dados diários; universo inicial ações e ETFs dos EUA (yfinance também cobre B3, só para o assistente).
- Portão de risco sem LLM, vence o `analyst`. Valores iniciais em `config.toml`: risco por trade 1%, stop obrigatório, teto de posições abertas, teto por ativo, teto por setor, perda máxima semanal que pausa o bot.
- Backtest: custos e slippage incluídos, sem look-ahead, treino e teste separados, poucos parâmetros.
- Critério de promoção ao paper (fora da amostra): bate o buy and hold ajustado ao risco, drawdown máximo aceitável, trades suficientes, positiva com custo dobrado. Os números são pontos de partida a calibrar com o Bernardo.
- `analyst` cita a fonte de cada afirmação e nunca decide ordens. Modelo: `claude-sonnet-5-5`.
- Nunca gravar chaves no repositório (`ANTHROPIC_API_KEY` só por variável de ambiente).
- Commits só com OK do Bernardo; a pasta fica dentro do repositório git de `Projetos`.

## Review Focus
- Ticker inexistente ou sem dados: erro claro (`DataError`), não DataFrame vazio.
- Histórico menor que a janela da estratégia: sem sinais e sem crash.
- Preços com NaN, buracos ou splits: usar preço ajustado e descartar linhas sem `close`.
- Capital pequeno ou stop inválido (stop ≥ entrada): quantidade 0 ou `RiskRejected`, nunca ordem negativa.
- `analyst` sem chave de API ou com resposta malformada: relatório marcado como indisponível, backtest segue funcionando.

---

## File Structure
```
pyproject.toml
config.toml
src/tradingbot/{__init__,__main__,config,data,strategies,risk,backtest,evaluate,analyst,broker,cli}.py
tests/test_{config,data,strategies,risk,backtest,evaluate,analyst,cli}.py
tests/conftest.py        # fixture synthetic_prices(n, seed) -> DataFrame
```

### Task 1: Scaffold e configuração

**Files:** Create `pyproject.toml`, `config.toml`, `src/tradingbot/__init__.py`, `src/tradingbot/config.py`, `tests/conftest.py`, `tests/test_config.py`

**Interfaces:**
- Produces: `RiskConfig(risk_per_trade=0.01, max_open_positions=5, max_position_pct=0.20, max_sector_pct=0.40, weekly_loss_limit=0.05)`, `CostConfig(commission=0.0, slippage_bps=5.0)`, `AppConfig(risk: RiskConfig, costs: CostConfig, initial_capital: float)` (todas `@dataclass(frozen=True)`), `load_config(path: Path) -> AppConfig` (usa `tomllib`).
- Produces (conftest): fixture `synthetic_prices` retornando função `(n: int = 300, seed: int = 0) -> pd.DataFrame` com colunas `open, high, low, close, volume` e `DatetimeIndex` diário crescente.

- [ ] **Step 1: Write failing test** `test_load_config_reads_risk_values`: grava um TOML temporário com `risk_per_trade = 0.02` e afirma `load_config(p).risk.risk_per_trade == 0.02`. Segundo teste `test_load_config_rejects_nonpositive_risk`: `risk_per_trade = 0` levanta `ValueError`.
- [ ] **Step 2:** Run `pytest tests/test_config.py -v`. Expected: FAIL (módulo inexistente).
- [ ] **Step 3:** Criar `pyproject.toml` (layout `src`, dependências acima, `pytest` em extras `dev`), `config.toml` com os valores padrão e implementar `config.py`; validar `0 < risk_per_trade <= 0.05`.
- [ ] **Step 4:** Run `pip install -e ".[dev]" && pytest tests/test_config.py -v`. Expected: PASS.
- [ ] **Step 5:** Commit (com OK do Bernardo): `feat: scaffold e configuração`.

### Task 2: Dados

**Files:** Create `src/tradingbot/data.py`, `tests/test_data.py`

**Interfaces:**
- Consumes: nada.
- Produces: `class DataError(Exception)`; `get_prices(ticker: str, start: str, end: str, cache_dir: Path = Path(".cache"), fetch: Callable[[str, str, str], pd.DataFrame] | None = None) -> pd.DataFrame` com colunas minúsculas `open, high, low, close, volume` (preço ajustado), índice crescente, sem NaN em `close`. `fetch=None` usa yfinance (`auto_adjust=True`). Cache em CSV `{cache_dir}/{ticker}_{start}_{end}.csv`.

- [ ] **Step 1: Write failing tests** (com `fetch` falso): `test_get_prices_normalizes_columns` (colunas e ordem), `test_get_prices_uses_cache_second_call` (contador do fetch == 1), `test_get_prices_empty_raises_data_error`, `test_get_prices_drops_nan_close`.
- [ ] **Step 2:** Run `pytest tests/test_data.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implementar `get_prices`; ticker normalizado com `.upper()`, vazio vira `DataError`.
- [ ] **Step 4:** Run tests. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: data com cache`.

### Task 3: Estratégias

**Files:** Create `src/tradingbot/strategies.py`, `tests/test_strategies.py`

**Interfaces:**
- Consumes: DataFrame de `get_prices`.
- Produces: cada função devolve `pd.Series[int]` com o mesmo índice, valores `1` (comprado) ou `0` (fora), calculada só com dados até o dia t: `sma_cross(prices, fast: int = 20, slow: int = 50)`, `rsi_reversion(prices, period: int = 14, buy_below: float = 30, exit_above: float = 50)`, `momentum(prices, lookback: int = 60)`. Registro `STRATEGIES: dict[str, Callable]`.

- [ ] **Step 1: Write failing tests:** `test_sma_cross_long_when_fast_above_slow` (série crescente → último sinal 1), `test_sma_cross_flat_during_warmup` (primeiros `slow-1` valores 0), `test_strategies_short_history_all_zero` (30 linhas, sem exceção), `test_signal_has_no_lookahead` (alterar o último `close` não muda sinais anteriores).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implementar com pandas; RSI de Wilder; `momentum` = 1 se retorno de `lookback` dias > 0.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: estratégias de swing`.

### Task 4: Portão de risco

**Files:** Create `src/tradingbot/risk.py`, `tests/test_risk.py`

**Interfaces:**
- Consumes: `RiskConfig`.
- Produces: `class RiskRejected(Exception)`; `@dataclass Order(ticker: str, side: Literal["buy","sell"], qty: int, entry: float, stop: float | None, sector: str = "unknown")`; `@dataclass Position(ticker: str, qty: int, entry: float, sector: str)`; `@dataclass PortfolioState(equity: float, positions: dict[str, Position], week_start_equity: float)`; `position_size(capital: float, entry: float, stop: float, cfg: RiskConfig) -> int` (`floor(capital*risk_per_trade/(entry-stop))`, limitado a `max_position_pct*capital/entry`; levanta `RiskRejected` se `stop >= entry`); `atr_stop(prices: pd.DataFrame, i: int, period: int = 14, mult: float = 2.0) -> float`; `check_order(order: Order, state: PortfolioState, cfg: RiskConfig) -> None` (levanta `RiskRejected` com motivo).

- [ ] **Step 1: Write failing tests:** `test_position_size_one_percent_risk` (capital 10_000, entry 100, stop 95 → 20), `test_position_size_capped_by_max_position_pct` (stop muito próximo → qty ≤ 20% do capital/entry), `test_position_size_rejects_stop_above_entry`, `test_check_order_rejects_missing_stop`, `test_check_order_rejects_when_max_positions_reached`, `test_check_order_rejects_sector_over_limit`, `test_check_order_rejects_after_weekly_loss_limit` (equity 94% do início da semana com limite 5%), `test_small_capital_gives_zero_qty` (capital 50, entry 100 → 0).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implementar; `check_order` só valida compras (vendas sempre passam). Sem import de `anthropic` neste módulo.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: portão de risco`.

### Task 5: Backtest

**Files:** Create `src/tradingbot/backtest.py`, `tests/test_backtest.py`

**Interfaces:**
- Consumes: `risk.position_size`, `risk.atr_stop`, `CostConfig`, `RiskConfig`.
- Produces: `@dataclass BacktestResult(equity: pd.Series, trades: pd.DataFrame, metrics: dict[str, float])` com métricas `total_return`, `max_drawdown` (positivo, fração), `sharpe` (anualizado, 252), `n_trades`; `run_backtest(prices, signals, risk_cfg, cost_cfg, initial_capital=10_000.0) -> BacktestResult`; `buy_and_hold(prices, initial_capital=10_000.0) -> BacktestResult`; `split_train_test(prices, test_fraction: float = 0.3) -> tuple[pd.DataFrame, pd.DataFrame]` (corte temporal, sem embaralhar); `walk_forward_windows(prices, train_days: int = 504, test_days: int = 126) -> list[tuple[pd.DataFrame, pd.DataFrame]]` (janelas deslizantes, cada teste começa onde o treino termina, sem sobreposição entre testes).

Regras: sinal do dia t executa na abertura de t+1, com slippage `slippage_bps` contra o preço e comissão por trade; stop via `atr_stop` na entrada, saída ao stop se `low <= stop` (preço do stop), ou na abertura seguinte a um sinal 0; sem alavancagem.

- [ ] **Step 1: Write failing tests:** `test_signal_executes_next_open` (entrada igual ao `open` do dia seguinte mais slippage), `test_no_signals_equals_flat_equity` (equity constante, 0 trades), `test_stop_triggers_exit_at_stop_price`, `test_costs_reduce_return` (custo maior → `total_return` menor), `test_split_train_test_is_chronological`, `test_buy_and_hold_matches_price_ratio`, `test_walk_forward_windows_do_not_overlap_in_test` e `test_walk_forward_short_history_returns_empty_list`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implementar laço diário sobre as barras; uma posição por vez (fase 1, um ativo por backtest).
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: motor de backtest`.

### Task 6: Critério de promoção

**Files:** Create `src/tradingbot/evaluate.py`, `tests/test_evaluate.py`

**Interfaces:**
- Consumes: `BacktestResult`, `run_backtest`, `split_train_test`.
- Produces: `@dataclass(frozen=True) PromotionCriteria(min_trades: int = 30, max_drawdown: float = 0.25)`; `@dataclass Verdict(passed: bool, reasons: list[str])`; `evaluate_strategy(prices, strategy: Callable, criteria: PromotionCriteria, risk_cfg, cost_cfg) -> Verdict` (roda no trecho de teste; também roda com `slippage_bps` e `commission` dobrados).

Passa se: `sharpe` da estratégia > `sharpe` do buy and hold, `max_drawdown <= criteria.max_drawdown`, `n_trades >= criteria.min_trades`, `total_return > 0` com custo dobrado. `reasons` lista cada falha.

- [ ] **Step 1: Write failing tests:** `test_fails_with_too_few_trades` (reasons cita trades), `test_fails_when_drawdown_exceeds_limit`, `test_fails_when_negative_under_double_costs`, `test_passes_when_all_criteria_met` (resultados montados à mão via função auxiliar do teste).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implementar; separar a regra pura `judge(strategy_res, benchmark_res, doubled_res, criteria) -> Verdict` para testar sem backtest.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: critério de promoção`.

### Task 7: Analyst

**Files:** Create `src/tradingbot/analyst.py`, `tests/test_analyst.py`

**Interfaces:**
- Consumes: `get_prices`.
- Produces: `@dataclass Finding(claim: str, source: str)`; `@dataclass AnalystReport(ticker: str, sections: dict[str, list[Finding]], available: bool)` com seções `tecnica, fundamentos, sentimento, risco_noticias`; `validate_findings(raw: list[dict]) -> list[Finding]` (descarta item sem `claim` ou com `source` vazio); `analyze(ticker: str, prices: pd.DataFrame, ask: Callable[[str, str], str] | None = None) -> AnalystReport`. `ask(role_prompt, context) -> str` devolve JSON; `None` usa o SDK `anthropic` com `claude-sonnet-5-5`. Contexto de notícias e fundamentos vem de `yfinance.Ticker` (fonte a revisar, ponto em aberto da spec).

- [ ] **Step 1: Write failing tests (com `ask` falso):** `test_validate_findings_drops_unsourced_claims`, `test_analyze_returns_four_sections`, `test_analyze_malformed_json_marks_section_empty_not_crash`, `test_analyze_without_api_key_is_unavailable` (sem `ask` e sem `ANTHROPIC_API_KEY`: `available=False`, sem exceção).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implementar quatro prompts curtos (um por seção) pedindo JSON `[{"claim","source"}]` e a instrução de não recomendar compra ou venda.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: analyst com subagentes`.

### Task 8: Interface do broker

**Files:** Create `src/tradingbot/broker.py`, `tests/test_cli.py` (teste de contrato)

**Interfaces:**
- Consumes: `Order`, `Position`.
- Produces: `class Broker(Protocol)` com `submit_order(self, order: Order) -> str` e `get_positions(self) -> list[Position]`; `class NullBroker` cujos métodos levantam `NotImplementedError("Fase 2: ordens ainda não implementadas")`.

- [ ] **Step 1: Write failing test** `test_null_broker_never_places_orders` (`submit_order` levanta `NotImplementedError`).
- [ ] **Step 2:** Run `pytest tests/test_cli.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit: `feat: interface do broker (vazia)`.

### Task 9: CLI e relatório

**Files:** Create `src/tradingbot/cli.py`, `src/tradingbot/__main__.py`; Modify `tests/test_cli.py`

**Interfaces:**
- Consumes: tudo acima.
- Produces: `main(argv: list[str] | None = None) -> int` com subcomandos `backtest TICKER --strategy {sma_cross,rsi_reversion,momentum} --start YYYY-MM-DD --end YYYY-MM-DD` e `analyze TICKER`. `backtest` imprime métricas da estratégia e do buy and hold e o `Verdict`; `analyze` imprime as seções com fontes. Grava `reports/{ticker}_{data}.md`. Retorna 0 em sucesso, 2 em `DataError` (mensagem em português, sem traceback).

- [ ] **Step 1: Write failing tests:** `test_backtest_command_prints_verdict` (com `get_prices` substituído por série sintética), `test_unknown_ticker_returns_2` (`DataError` vira código 2 e mensagem), `test_analyze_without_key_still_exits_0` (relatório "indisponível").
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implementar com `argparse`; dividir `--start/--end` do treino e do teste via `split_train_test`.
- [ ] **Step 4:** Run `pytest -v`. Expected: todos PASS.
- [ ] **Step 5:** Verificação manual: `python -m tradingbot backtest SPY --strategy sma_cross --start 2015-01-01 --end 2025-12-31`. Expected: métricas, veredito e `reports/SPY_*.md`. Commit: `feat: cli e relatório`.
