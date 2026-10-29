const STRATEGIES: Record<string, string> = {
  sma_cross: "Golden cross 50/200",
  donchian: "Rompimento Donchian",
  momentum: "Momentum de 12 meses",
};

/** Nome em português da estratégia; ids desconhecidos aparecem como vieram. */
export function strategyLabel(id: string): string {
  return STRATEGIES[id] ?? id;
}

/** Ticker sem os sufixos técnicos do Yahoo (".SA" da B3, "-USD" das criptos); o valor interno continua o ticker completo. */
export function displayTicker(ticker: string): string {
  return ticker.replace(/\.SA$/i, "").replace(/-USD$/i, "");
}
