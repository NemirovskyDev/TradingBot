import { ColorType, type DeepPartial, type ChartOptions } from "lightweight-charts";
import { formatPrice } from "../data/format";

function cssVar(name: string, fallback: string): string {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback; // no jsdom e antes do CSS carregar a variável vem vazia
}

export interface ChartColors {
  ink: string;
  inkSoft: string;
  line: string;
  surface: string;
  action: string;
  gain: string;
  loss: string;
  benchmark: string;
}

export function chartColors(): ChartColors {
  return {
    ink: cssVar("--ink", "#e8eef4"),
    inkSoft: cssVar("--ink-soft", "#9fb0c0"),
    line: cssVar("--line", "#243241"),
    surface: cssVar("--surface", "#121a23"),
    action: cssVar("--action", "#7cb2ff"),
    gain: cssVar("--gain", "#3ddc97"),
    loss: cssVar("--loss", "#ff7b7b"),
    benchmark: cssVar("--benchmark", "#8fa1b3"), // contraste ≥3:1 sobre a superfície, para a linha tracejada
  };
}

/** Opções comuns aos gráficos: cores do tema, fonte do painel e números em pt-BR. */
export function baseOptions(colors: ChartColors, height: number): DeepPartial<ChartOptions> {
  return {
    height,
    layout: {
      background: { type: ColorType.Solid, color: colors.surface },
      textColor: colors.inkSoft,
      fontFamily: getComputedStyle(document.body).fontFamily || "system-ui, sans-serif",
      fontSize: 12,
    },
    grid: { vertLines: { visible: false }, horzLines: { color: colors.line } },
    rightPriceScale: { borderVisible: false },
    timeScale: { borderVisible: false },
    localization: { locale: "pt-BR", priceFormatter: (p: number) => formatPrice(p) },
    handleScale: { mouseWheel: false }, // a roda do mouse continua rolando a página
  };
}
