import type { Price, Trade } from "../data/types";

export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface Marker {
  time: string;
  position: "belowBar" | "aboveBar";
  shape: "arrowUp" | "arrowDown";
  color: string;
  text: string;
  id: string;
  size: number;
}

export interface MarkerColors {
  gain: string;
  loss: string;
}

const DEFAULT_COLORS: MarkerColors = { gain: "#3ddc97", loss: "#ff7b7b" };

export function toCandles(prices: Price[]): Candle[] {
  return prices
    .map((p) => ({ time: p.date, open: p.open, high: p.high, low: p.low, close: p.close }))
    .sort((a, b) => a.time.localeCompare(b.time));
}

/**
 * Uma seta para cima (compra) e uma para baixo (saída) por operação, ordenadas por data como o gráfico exige.
 * Forma e posição distinguem os dois, então a cor não é o único sinal; só a operação selecionada ganha
 * o texto "Compra"/"Saída" (rotular todas sobrepõe os textos em gráficos densos).
 */
export function toMarkers(
  trades: Trade[],
  selectedId: string | null = null,
  colors: MarkerColors = DEFAULT_COLORS,
  selectedSize = 2,
): Marker[] {
  const markers = trades.flatMap((t): Marker[] => {
    const selected = t.id === selectedId;
    const size = selected ? selectedSize : 1;
    return [
      { time: t.entry_date, position: "belowBar", shape: "arrowUp", color: colors.gain, text: selected ? "Compra" : "", id: `${t.id}:entry`, size },
      {
        time: t.exit_date,
        position: "aboveBar",
        shape: "arrowDown",
        color: t.pnl_pct < 0 ? colors.loss : colors.gain,
        text: selected ? "Saída" : "",
        id: `${t.id}:exit`,
        size,
      },
    ];
  });
  return markers.sort((a, b) => a.time.localeCompare(b.time));
}
