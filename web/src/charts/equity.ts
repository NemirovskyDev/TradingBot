import type { EquityPoint } from "../data/types";

export interface LinePoint {
  time: string;
  value: number;
}

/** Separa a curva do bot e a do comprar e segurar no formato que o gráfico espera (data AAAA-MM-DD). */
export function toEquitySeries(equity: EquityPoint[]): { strategy: LinePoint[]; buyHold: LinePoint[] } {
  return {
    strategy: equity.map((p) => ({ time: p.date, value: p.strategy })),
    buyHold: equity.map((p) => ({ time: p.date, value: p.buy_hold })),
  };
}
