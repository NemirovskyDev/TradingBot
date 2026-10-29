import type { Portfolio, PortfolioData, Run, RunIndex } from "../data/types";

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

/** Carteiras de exemplo (schema 2): 4 datas, 2 metodologias clássicas (a segunda começa depois), os 4 exemplos por perfil e as 3 referências. */
export function makePortfolios(): PortfolioData {
  const metrics = (cagr: number, drawdown = -0.24) => ({ total_return: 0.3, cagr, volatility: 0.09, max_drawdown: drawdown, sharpe: 0.3 });
  const annual = [
    { year: 2020, return: 0.05, partial: true },
    { year: 2021, return: 0.12, partial: false },
  ];
  const benchmarksOf = (): Portfolio["benchmarks"] => ({
    cdi: { metrics: metrics(0.101, 0), annual_returns: annual },
    ibovespa: { metrics: metrics(0.104, -0.4), annual_returns: annual },
    sp500: { metrics: metrics(0.212, -0.3), annual_returns: annual },
  });
  const portfolio = (
    id: string,
    name: string,
    kind: Portfolio["kind"],
    equity: (number | null)[],
    cagr: number,
    extra: Partial<Portfolio> = {},
  ): Portfolio => ({
    id,
    name,
    kind,
    equity,
    drawdown: equity.map(() => -0.01),
    metrics: metrics(cagr),
    metrics_common: metrics(cagr - 0.014, -0.2),
    annual_returns: annual,
    author: kind === "classic" ? "Autor da metodologia" : "Exemplo montado pelo projeto",
    summary: `Resumo de ${name}.`,
    rule: "Rebalanceia uma vez por ano.",
    rebalance: "yearly",
    components: [{ label: "Caixa (CDI)", weight: 0.25 }],
    universe: ["Caixa (CDI)"],
    start: "2020-06-01",
    benchmarks: benchmarksOf(),
    ...extra,
  });
  const profile = (id: string, related: string[] = [], runs = false) => ({
    id,
    name: `Perfil ${id}`,
    tagline: `Objetivo de ${id}.`,
    expect: `O que esperar de ${id}.`,
    warning: `Aviso de ${id}.`,
    portfolio_id: id,
    related_ids: related,
    runs_link: runs,
  });
  return {
    schema: 2,
    currency: "BRL",
    generated_at: "2026-10-28",
    start: "2020-06-01",
    common_start: "2020-12-01",
    end: "2021-06-01",
    dates: ["2020-06-01", "2020-12-01", "2021-03-01", "2021-06-01"],
    assumptions: ["Tudo em reais.", "Não há imposto de renda."],
    portfolios: [
      portfolio("arca", "ARCA", "classic", [100, 110, 120, 130], 0.125, { author: "Thiago Nigro (Primo Rico)", summary: "Quatro quadrantes de 25%." }),
      portfolio("momentum-dual", "Momentum dual (GEM)", "classic", [null, 100, 95, 140], 0.158, {
        rule: "Decide no fechamento de cada mês.",
        rebalance: "monthly",
        components: [],
        universe: ["Ações dos EUA (VTI)", "Títulos dos EUA (BND)"],
        start: "2020-12-01",
      }),
      portfolio("renda-dividendos", "Renda de dividendos", "profile", [100, 104, 108, 112], 0.131),
      portfolio("estabilidade", "Estabilidade", "profile", [100, 102, 104, 106], 0.109, { metrics: metrics(0.109, -0.05) }),
      portfolio("crescimento", "Crescimento", "profile", [100, 115, 130, 150], 0.151),
      portfolio("swing-alto-risco", "Swing em ativos voláteis", "profile", [100, 120, 90, 160], 0.24, { rebalance: "daily", components: [] }),
    ],
    benchmarks: [
      { id: "cdi", name: "CDI", equity: [100, 105, 108, 110], drawdown: [0, 0, 0, 0], metrics: metrics(0.101, 0), metrics_common: metrics(0.1, 0), annual_returns: annual },
      { id: "ibovespa", name: "Ibovespa (BOVA11)", equity: [100, 90, 110, 120], drawdown: [0, -0.1, 0, 0], metrics: metrics(0.104, -0.4), metrics_common: metrics(0.098, -0.4), annual_returns: annual },
      { id: "sp500", name: "S&P 500 em reais (IVVB11)", equity: [100, 120, 140, 160], drawdown: [0, 0, 0, 0], metrics: metrics(0.212, -0.3), metrics_common: metrics(0.213, -0.3), annual_returns: annual },
    ],
    profiles: [
      profile("renda-dividendos"),
      profile("estabilidade", ["arca", "momentum-dual"]),
      profile("crescimento", ["momentum-dual"]),
      profile("swing-alto-risco", [], true),
    ],
  };
}
