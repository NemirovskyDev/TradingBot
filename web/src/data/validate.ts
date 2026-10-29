import type {
  BlockedSignal,
  EquityPoint,
  Metrics,
  AnnualReturn,
  Portfolio,
  PortfolioData,
  PortfolioMetrics,
  PortfolioSeries,
  Profile,
  ReferenceSummary,
  Price,
  Run,
  RunIndex,
  RunMeta,
  RunRef,
  Trade,
  Verdict,
} from "./types";

/** Arquivo de dados ausente, malformado ou de versão incompatível; a mensagem diz o campo e fica pronta para a tela. */
export class DataError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DataError";
  }
}

const SUPPORTED_SCHEMA = 1;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
/** Ids viram nome de arquivo (execuções) e parte de ids de marcador (operações, separados por ":"). */
export const SAFE_ID = /^[A-Za-z0-9_-]{1,64}$/;

type Rec = Record<string, unknown>;

function fail(path: string, expected: string): never {
  throw new DataError(`Campo "${path}" inválido: esperado ${expected}.`);
}

function rec(v: unknown, path: string): Rec {
  if (typeof v !== "object" || v === null || Array.isArray(v)) fail(path, "um objeto");
  return v as Rec;
}

function str(v: unknown, path: string): string {
  if (typeof v !== "string") fail(path, "texto");
  return v;
}

function num(v: unknown, path: string): number {
  if (typeof v !== "number" || !Number.isFinite(v)) fail(path, "um número");
  return v;
}

function bool(v: unknown, path: string): boolean {
  if (typeof v !== "boolean") fail(path, "verdadeiro ou falso");
  return v;
}

function isoDate(v: unknown, path: string): string {
  const s = str(v, path);
  if (!ISO_DATE.test(s)) fail(path, "uma data AAAA-MM-DD");
  const [y, m, d] = s.split("-").map(Number) as [number, number, number];
  const date = new Date(Date.UTC(y, m - 1, d));
  if (date.getUTCFullYear() !== y || date.getUTCMonth() !== m - 1 || date.getUTCDate() !== d) {
    fail(path, "uma data existente");
  }
  return s;
}

function list<T>(v: unknown, path: string, item: (x: unknown, p: string) => T): T[] {
  if (!Array.isArray(v)) fail(path, "uma lista");
  return v.map((x, i) => item(x, `${path}[${i}]`));
}

/** O gráfico exige datas crescentes e sem repetição; dados fora disso quebrariam o desenho ou sairiam embaralhados. */
function ascendingDates(items: { date: string }[], path: string): void {
  for (let i = 1; i < items.length; i++) {
    if (items[i]!.date <= items[i - 1]!.date) fail(`${path}[${i}].date`, "datas em ordem crescente e sem repetição");
  }
}

function uniqueSafeIds(ids: string[], path: string): void {
  const seen = new Set<string>();
  ids.forEach((id, i) => {
    if (!SAFE_ID.test(id)) fail(`${path}[${i}].id`, "um identificador com letras, números, _ ou -");
    if (seen.has(id)) fail(`${path}[${i}].id`, "um identificador único");
    seen.add(id);
  });
}

function numberMap(v: unknown, path: string): Record<string, number> {
  const r = rec(v, path);
  return Object.fromEntries(Object.entries(r).map(([k, x]) => [k, num(x, `${path}.${k}`)]));
}

function optionalNumbers<K extends string>(v: unknown, path: string, keys: readonly K[]): Partial<Record<K, number>> {
  const r = rec(v, path);
  const out: Partial<Record<K, number>> = {};
  for (const k of keys) if (r[k] !== undefined) out[k] = num(r[k], `${path}.${k}`);
  return out;
}

function parsePrice(v: unknown, p: string): Price {
  const r = rec(v, p);
  return {
    date: isoDate(r.date, `${p}.date`),
    open: num(r.open, `${p}.open`),
    high: num(r.high, `${p}.high`),
    low: num(r.low, `${p}.low`),
    close: num(r.close, `${p}.close`),
    volume: num(r.volume, `${p}.volume`),
  };
}

function parseEquity(v: unknown, p: string): EquityPoint {
  const r = rec(v, p);
  return {
    date: isoDate(r.date, `${p}.date`),
    strategy: num(r.strategy, `${p}.strategy`),
    buy_hold: num(r.buy_hold, `${p}.buy_hold`),
  };
}

function parseTrade(v: unknown, p: string): Trade {
  const r = rec(v, p);
  return {
    id: str(r.id, `${p}.id`),
    entry_date: isoDate(r.entry_date, `${p}.entry_date`),
    entry_price: num(r.entry_price, `${p}.entry_price`),
    exit_date: isoDate(r.exit_date, `${p}.exit_date`),
    exit_price: num(r.exit_price, `${p}.exit_price`),
    qty: num(r.qty, `${p}.qty`),
    stop: num(r.stop, `${p}.stop`),
    pnl_pct: num(r.pnl_pct, `${p}.pnl_pct`),
    reason_entry: str(r.reason_entry, `${p}.reason_entry`),
    reason_exit: str(r.reason_exit, `${p}.reason_exit`),
  };
}

function parseBlocked(v: unknown, p: string): BlockedSignal {
  const r = rec(v, p);
  return {
    date: isoDate(r.date, `${p}.date`),
    ticker: str(r.ticker, `${p}.ticker`),
    reason: str(r.reason, `${p}.reason`),
  };
}

function parseMeta(v: unknown, p: string): RunMeta {
  const r = rec(v, p);
  const params = rec(r.params, `${p}.params`);
  return {
    ticker: str(r.ticker, `${p}.ticker`),
    strategy: str(r.strategy, `${p}.strategy`),
    params: {
      estrategia: numberMap(params.estrategia ?? {}, `${p}.params.estrategia`),
      risco: optionalNumbers(params.risco ?? {}, `${p}.params.risco`, [
        "risk_per_trade",
        "max_open_positions",
        "max_position_pct",
        "max_sector_pct",
        "weekly_loss_limit",
      ] as const),
      custos: optionalNumbers(params.custos ?? {}, `${p}.params.custos`, ["commission", "slippage_bps"] as const),
    },
    start: isoDate(r.start, `${p}.start`),
    end: isoDate(r.end, `${p}.end`),
    initial_capital: num(r.initial_capital, `${p}.initial_capital`),
    generated_at: str(r.generated_at, `${p}.generated_at`),
    synthetic: bool(r.synthetic, `${p}.synthetic`),
  };
}

function parseMetrics(v: unknown, p: string): Metrics {
  const r = rec(v, p);
  return {
    total_return: num(r.total_return, `${p}.total_return`),
    benchmark_return: num(r.benchmark_return, `${p}.benchmark_return`),
    max_drawdown: num(r.max_drawdown, `${p}.max_drawdown`),
    sharpe: num(r.sharpe, `${p}.sharpe`),
    n_trades: num(r.n_trades, `${p}.n_trades`),
  };
}

function parseVerdict(v: unknown, p: string): Verdict {
  const r = rec(v, p);
  return { passed: bool(r.passed, `${p}.passed`), reasons: list(r.reasons, `${p}.reasons`, str) };
}

export function parseRun(json: unknown): Run {
  const r = rec(json, "execução");
  const run: Run = {
    meta: parseMeta(r.meta, "meta"),
    prices: list(r.prices, "prices", parsePrice),
    equity: list(r.equity, "equity", parseEquity),
    trades: list(r.trades, "trades", parseTrade),
    blocked: list(r.blocked, "blocked", parseBlocked),
    metrics: parseMetrics(r.metrics, "metrics"),
    verdict: parseVerdict(r.verdict, "verdict"),
  };
  ascendingDates(run.prices, "prices");
  ascendingDates(run.equity, "equity");
  uniqueSafeIds(run.trades.map((t) => t.id), "trades");
  return run;
}

function parseRunRef(v: unknown, p: string): RunRef {
  const r = rec(v, p);
  const ref: RunRef = {
    id: str(r.id, `${p}.id`),
    ticker: str(r.ticker, `${p}.ticker`),
    strategy: str(r.strategy, `${p}.strategy`),
    label: str(r.label, `${p}.label`),
  };
  if (r.name !== undefined) ref.name = str(r.name, `${p}.name`);
  if (r.category !== undefined) ref.category = str(r.category, `${p}.category`);
  return ref;
}

export function parseIndex(json: unknown): RunIndex {
  const r = rec(json, "índice");
  if (r.schema !== SUPPORTED_SCHEMA) {
    throw new DataError(`Versão dos dados incompatível: o painel espera a versão ${SUPPORTED_SCHEMA}, recebeu ${String(r.schema)}.`);
  }
  const runs = list(r.runs, "runs", parseRunRef);
  uniqueSafeIds(runs.map((x) => x.id), "runs");
  return { schema: SUPPORTED_SCHEMA, runs };
}

function nullableNum(v: unknown, path: string): number | null {
  return v === null ? null : num(v, path);
}

function parsePortfolioMetrics(v: unknown, p: string): PortfolioMetrics {
  const r = rec(v, p);
  return {
    total_return: nullableNum(r.total_return, `${p}.total_return`),
    cagr: nullableNum(r.cagr, `${p}.cagr`),
    volatility: nullableNum(r.volatility, `${p}.volatility`),
    max_drawdown: nullableNum(r.max_drawdown, `${p}.max_drawdown`),
    sharpe: nullableNum(r.sharpe, `${p}.sharpe`),
  };
}

function parseAnnual(v: unknown, p: string): AnnualReturn {
  const r = rec(v, p);
  return { year: num(r.year, `${p}.year`), return: nullableNum(r.return, `${p}.return`), partial: bool(r.partial, `${p}.partial`) };
}

function parseReference(v: unknown, p: string): ReferenceSummary {
  const r = rec(v, p);
  return {
    metrics: parsePortfolioMetrics(r.metrics, `${p}.metrics`),
    annual_returns: list(r.annual_returns, `${p}.annual_returns`, parseAnnual),
  };
}

function parsePortfolioSeries(v: unknown, p: string, points: number): PortfolioSeries {
  const r = rec(v, p);
  const series = (key: "equity" | "drawdown") => {
    const values = list(r[key], `${p}.${key}`, nullableNum);
    // o gráfico pareia cada valor com a data de mesmo índice: tamanhos diferentes embaralhariam a curva
    if (values.length !== points) fail(`${p}.${key}`, `${points} valores, um por data`);
    return values;
  };
  const equity = series("equity");
  if (!equity.some((x) => x !== null)) fail(`${p}.equity`, "pelo menos um valor");
  return {
    id: str(r.id, `${p}.id`),
    name: str(r.name, `${p}.name`),
    equity,
    drawdown: series("drawdown"),
    metrics: parsePortfolioMetrics(r.metrics, `${p}.metrics`),
    metrics_common: parsePortfolioMetrics(r.metrics_common, `${p}.metrics_common`),
    annual_returns: list(r.annual_returns, `${p}.annual_returns`, parseAnnual),
  };
}

function parsePortfolio(v: unknown, p: string, points: number): Portfolio {
  const r = rec(v, p);
  const rebalance = r.rebalance;
  if (rebalance !== "yearly" && rebalance !== "monthly" && rebalance !== "daily") fail(`${p}.rebalance`, "yearly, monthly ou daily");
  const kind = r.kind;
  if (kind !== "classic" && kind !== "profile") fail(`${p}.kind`, "classic ou profile");
  const benchmarks = rec(r.benchmarks, `${p}.benchmarks`);
  return {
    ...parsePortfolioSeries(v, p, points),
    kind,
    author: str(r.author, `${p}.author`),
    summary: str(r.summary, `${p}.summary`),
    rule: str(r.rule, `${p}.rule`),
    rebalance,
    components: list(r.components, `${p}.components`, (x, q) => {
      const c = rec(x, q);
      return { label: str(c.label, `${q}.label`), weight: num(c.weight, `${q}.weight`) };
    }),
    universe: list(r.universe, `${p}.universe`, str),
    start: isoDate(r.start, `${p}.start`),
    benchmarks: Object.fromEntries(Object.entries(benchmarks).map(([k, x]) => [k, parseReference(x, `${p}.benchmarks.${k}`)])),
  };
}

function parseProfile(v: unknown, p: string): Profile {
  const r = rec(v, p);
  return {
    id: str(r.id, `${p}.id`),
    name: str(r.name, `${p}.name`),
    tagline: str(r.tagline, `${p}.tagline`),
    expect: str(r.expect, `${p}.expect`),
    warning: str(r.warning, `${p}.warning`),
    portfolio_id: str(r.portfolio_id, `${p}.portfolio_id`),
    related_ids: list(r.related_ids, `${p}.related_ids`, str),
    runs_link: bool(r.runs_link, `${p}.runs_link`),
  };
}

const PORTFOLIO_SCHEMA = 2;

export function parsePortfolios(json: unknown): PortfolioData {
  const r = rec(json, "carteiras");
  if (r.schema !== PORTFOLIO_SCHEMA) {
    throw new DataError(`Versão dos dados incompatível: o painel espera a versão ${PORTFOLIO_SCHEMA}, recebeu ${String(r.schema)}.`);
  }
  if (r.currency !== "BRL") fail("currency", "BRL");
  const dates = list(r.dates, "dates", isoDate);
  if (dates.length < 2) fail("dates", "pelo menos duas datas");
  ascendingDates(dates.map((date) => ({ date })), "dates");
  const portfolios = list(r.portfolios, "portfolios", (x, p) => parsePortfolio(x, p, dates.length));
  if (portfolios.length === 0) fail("portfolios", "pelo menos uma carteira");
  const benchmarks = list(r.benchmarks, "benchmarks", (x, p) => parsePortfolioSeries(x, p, dates.length));
  uniqueSafeIds([...portfolios, ...benchmarks].map((x) => x.id), "portfolios");
  const ids = new Set(portfolios.map((x) => x.id));
  const profiles = list(r.profiles, "profiles", parseProfile);
  profiles.forEach((p, i) => {
    // um perfil que aponta para uma carteira inexistente abriria uma tela vazia
    if (!ids.has(p.portfolio_id)) fail(`profiles[${i}].portfolio_id`, "o id de uma carteira existente");
    p.related_ids.forEach((id, j) => {
      if (!ids.has(id)) fail(`profiles[${i}].related_ids[${j}]`, "o id de uma carteira existente");
    });
  });
  return {
    schema: PORTFOLIO_SCHEMA,
    currency: "BRL",
    generated_at: isoDate(r.generated_at, "generated_at"),
    start: isoDate(r.start, "start"),
    common_start: isoDate(r.common_start, "common_start"),
    end: isoDate(r.end, "end"),
    dates,
    assumptions: list(r.assumptions, "assumptions", str),
    portfolios,
    benchmarks,
    profiles,
  };
}
