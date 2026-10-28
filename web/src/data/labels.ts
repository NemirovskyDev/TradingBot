const STRATEGIES: Record<string, string> = {
  sma_cross: "Cruzamento de médias",
  rsi_reversion: "Reversão por RSI",
  momentum: "Momentum (tendência)",
};

/** Nome em português da estratégia; ids desconhecidos aparecem como vieram. */
export function strategyLabel(id: string): string {
  return STRATEGIES[id] ?? id;
}
