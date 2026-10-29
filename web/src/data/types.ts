// Contrato de dados exportado pelo backtest (spec do front, seção 5). Retornos e quedas são frações (0,124 = 12,4%).

export interface RunRef {
  id: string;
  ticker: string;
  strategy: string;
  label: string;
  /** Nome do ativo e categoria (Ações EUA, FIIs, Cripto...); ausentes nos dados de exemplo. */
  name?: string;
  category?: string;
}

export interface RunIndex {
  schema: 1;
  runs: RunRef[];
}

export interface Price {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface EquityPoint {
  date: string;
  strategy: number;
  buy_hold: number;
}

export interface Trade {
  id: string;
  entry_date: string;
  entry_price: number;
  exit_date: string;
  exit_price: number;
  qty: number;
  stop: number;
  pnl_pct: number;
  reason_entry: string;
  reason_exit: string;
}

export interface BlockedSignal {
  date: string;
  ticker: string;
  reason: string;
}

export interface Metrics {
  total_return: number;
  benchmark_return: number;
  max_drawdown: number;
  sharpe: number;
  n_trades: number;
}

export interface Verdict {
  passed: boolean;
  reasons: string[];
}

export interface RiskParams {
  risk_per_trade: number;
  max_open_positions: number;
  max_position_pct: number;
  max_sector_pct: number;
  weekly_loss_limit: number;
}

export interface CostParams {
  commission: number;
  slippage_bps: number;
}

export interface RunMeta {
  ticker: string;
  strategy: string;
  params: {
    estrategia: Record<string, number>;
    risco: Partial<RiskParams>;
    custos: Partial<CostParams>;
  };
  start: string;
  end: string;
  initial_capital: number;
  generated_at: string;
  synthetic: boolean;
}

export interface Run {
  meta: RunMeta;
  prices: Price[];
  equity: EquityPoint[];
  trades: Trade[];
  blocked: BlockedSignal[];
  metrics: Metrics;
  verdict: Verdict;
}

/** Carteiras (portfolios.json, versão 2). Cada carteira começa na sua data mais antiga: as séries compartilham `dates` e ficam `null` antes do início. Retornos são frações. */
export interface PortfolioMetrics {
  total_return: number | null;
  cagr: number | null;
  volatility: number | null;
  max_drawdown: number | null;
  sharpe: number | null;
}

export interface AnnualReturn {
  year: number;
  return: number | null;
  /** Primeiro ou último ano incompleto: o retorno não cobre o ano inteiro. */
  partial: boolean;
}

export interface ReferenceSummary {
  metrics: PortfolioMetrics;
  annual_returns: AnnualReturn[];
}

export interface PortfolioSeries {
  id: string;
  name: string;
  /** Valor de R$ 100 por data; null antes do início da série. */
  equity: (number | null)[];
  drawdown: (number | null)[];
  /** No período próprio (do início da série até o fim). */
  metrics: PortfolioMetrics;
  /** Na janela comum, a mesma para todas as carteiras. */
  metrics_common: PortfolioMetrics;
  annual_returns: AnnualReturn[];
}

export interface PortfolioComponent {
  label: string;
  weight: number;
}

export interface Portfolio extends PortfolioSeries {
  /** "classic" é uma metodologia publicada; "profile" é um exemplo montado pelo projeto para um perfil. */
  kind: "classic" | "profile";
  author: string;
  summary: string;
  rule: string;
  rebalance: "yearly" | "monthly" | "daily";
  /** Vazio nas metodologias em que os pesos mudam com o sinal (Ivy, momentum dual, swing). */
  components: PortfolioComponent[];
  universe: string[];
  start: string;
  /** As referências (cdi, ibovespa, sp500) medidas no mesmo período desta carteira. */
  benchmarks: Record<string, ReferenceSummary>;
}

export interface Profile {
  id: string;
  name: string;
  tagline: string;
  expect: string;
  warning: string;
  portfolio_id: string;
  related_ids: string[];
  runs_link: boolean;
}

export interface PortfolioData {
  schema: 2;
  currency: "BRL";
  generated_at: string;
  start: string;
  common_start: string;
  end: string;
  dates: string[];
  assumptions: string[];
  portfolios: Portfolio[];
  benchmarks: PortfolioSeries[];
  profiles: Profile[];
}
