import type { PortfolioData, Run, RunIndex } from "../data/types";

function isoDay(offset: number): string {
  const d = new Date(Date.UTC(2024, 0, 1 + offset));
  return d.toISOString().slice(0, 10);
}

/** Execução mínima e válida: 60 dias de preço, 3 operações (ganho, perda por stop, ganho) e 1 sinal bloqueado. */
export function makeRun(overrides: Partial<Run> = {}): Run {
  const prices = Array.from({ length: 60 }, (_, i) => {
    const close = 100 + i * 0.5 + (i % 7);
    return { date: isoDay(i), open: close - 0.3, high: close + 1, low: close - 1, close, volume: 1_000_000 };
  });
  const equity = prices.map((p, i) => ({
    date: p.date,
    strategy: 10_000 + i * 12,
    buy_hold: 10_000 + i * 20,
  }));
  return {
    meta: {
      ticker: "DEMO",
      strategy: "sma_cross",
      params: {
        estrategia: { fast: 20, slow: 50 },
        risco: {
          risk_per_trade: 0.01,
          max_open_positions: 5,
          max_position_pct: 0.2,
          max_sector_pct: 0.4,
          weekly_loss_limit: 0.05,
        },
        custos: { commission: 0, slippage_bps: 5 },
      },
      start: prices[0]!.date,
      end: prices[prices.length - 1]!.date,
      initial_capital: 10_000,
      generated_at: "2026-10-28T12:00:00+00:00",
      synthetic: true,
    },
    prices,
    equity,
    trades: [
      {
        id: "t1", entry_date: isoDay(5), entry_price: 102.5, exit_date: isoDay(15), exit_price: 108.1, qty: 30,
        stop: 98.2, pnl_pct: 0.054, reason_entry: "A média curta cruzou a longa para cima.",
        reason_exit: "A média curta cruzou a longa para baixo.",
      },
      {
        id: "t2", entry_date: isoDay(20), entry_price: 110, exit_date: isoDay(24), exit_price: 105.4, qty: 28,
        stop: 105.4, pnl_pct: -0.042, reason_entry: "A média curta cruzou a longa para cima.",
        reason_exit: "O preço tocou o stop de proteção.",
      },
      {
        id: "t3", entry_date: isoDay(35), entry_price: 118, exit_date: isoDay(55), exit_price: 126.5, qty: 25,
        stop: 112, pnl_pct: 0.072, reason_entry: "A média curta cruzou a longa para cima.",
        reason_exit: "O período do teste terminou com a posição aberta.",
      },
    ],
    blocked: [{ date: isoDay(30), ticker: "DEMO", reason: "Limite de 5 posições abertas atingido." }],
    metrics: { total_return: 0.124, benchmark_return: 0.091, max_drawdown: 0.082, sharpe: 1.23, n_trades: 3 },
    verdict: { passed: false, reasons: ["Poucas operações para concluir algo: 3 de pelo menos 30."] },
    ...overrides,
  };
}

/** Índice como o da exportação real: 3 ativos em 2 categorias, 3 estratégias (o último ativo só tem 2). */
export function makeCatalogIndex(): RunIndex {
  const run = (id: string, ticker: string, name: string, category: string, strategy: string) => ({
    id,
    ticker,
    strategy,
    label: `${name} · ${strategy}`,
    name,
    category,
  });
  return {
    schema: 1,
    runs: [
      run("aapl-momentum", "AAPL", "Apple", "Ações EUA", "momentum"),
      run("aapl-sma_cross", "AAPL", "Apple", "Ações EUA", "sma_cross"),
      run("petr4_sa-momentum", "PETR4.SA", "Petrobras PN", "Ações B3", "momentum"),
      run("petr4_sa-sma_cross", "PETR4.SA", "Petrobras PN", "Ações B3", "sma_cross"),
      run("btc_usd-sma_cross", "BTC-USD", "Bitcoin", "Cripto", "sma_cross"),
    ],
  };
}

export function makeIndex(): RunIndex {
  return {
    schema: 1,
    runs: [
      { id: "demo-sma_cross", ticker: "DEMO", strategy: "sma_cross", label: "Exemplo · sma_cross" },
      { id: "demo-momentum", ticker: "DEMO", strategy: "momentum", label: "Exemplo · momentum" },
    ],
  };
}

/** Carteiras de exemplo: 4 datas, duas carteiras (uma de pesos fixos, uma de rotação) e as três referências. */
export function makePortfolios(): PortfolioData {
  const series = (id: string, name: string, equity: number[], cagr: number) => ({
    id,
    name,
    equity,
    drawdown: equity.map((v) => Math.min(0, v / Math.max(...equity) - 1)),
    metrics: { total_return: equity[equity.length - 1]! / 100 - 1, cagr, volatility: 0.09, max_drawdown: -0.24, sharpe: 0.3 },
    annual_returns: [
      { year: 2020, return: 0.05, partial: true },
      { year: 2021, return: 0.12, partial: false },
    ],
  });
  return {
    schema: 1,
    currency: "BRL",
    generated_at: "2026-10-28",
    start: "2020-06-01",
    end: "2021-06-01",
    dates: ["2020-06-01", "2020-12-01", "2021-03-01", "2021-06-01"],
    assumptions: ["Tudo em reais.", "Não há imposto de renda."],
    portfolios: [
      {
        ...series("arca", "ARCA", [100, 110, 120, 130], 0.125),
        author: "Thiago Nigro (Primo Rico)",
        summary: "Quatro quadrantes de 25%.",
        rule: "Rebalanceia uma vez por ano.",
        rebalance: "yearly",
        components: [
          { label: "Ações brasileiras (BOVA11)", weight: 0.25 },
          { label: "Caixa (CDI)", weight: 0.25 },
        ],
        universe: ["Ações brasileiras (BOVA11)", "Caixa (CDI)"],
      },
      {
        ...series("momentum-dual", "Momentum dual (GEM)", [100, 105, 95, 140], 0.158),
        author: "Gary Antonacci",
        summary: "Um ativo por vez.",
        rule: "Decide no fechamento de cada mês.",
        rebalance: "monthly",
        components: [],
        universe: ["Ações dos EUA (VTI)", "Títulos dos EUA (BND)"],
      },
    ],
    benchmarks: [
      series("cdi", "CDI", [100, 105, 108, 110], 0.101),
      series("ibovespa", "Ibovespa (BOVA11)", [100, 90, 110, 120], 0.104),
      series("sp500", "S&P 500 em reais (IVVB11)", [100, 120, 140, 160], 0.212),
    ],
  };
}
