import { createChart, LineStyle, PriceScaleMode } from "lightweight-charts";
import { useEffect, useRef } from "react";
import { formatPercent } from "../data/format";
import type { PortfolioSeries } from "../data/types";
import { useDrawIn } from "../motion";
import { baseOptions, chartColors } from "./theme";
import "./charts.css";

const HEIGHT = 340;

/** Um estilo de linha por referência: o formato, e não só a cor, separa as linhas (também para quem não distingue cores). */
const BENCHMARK_STYLES: Record<string, { style: LineStyle; swatch: string }> = {
  cdi: { style: LineStyle.Dashed, swatch: "swatch-dashed" },
  ibovespa: { style: LineStyle.Dotted, swatch: "swatch-dotted" },
  sp500: { style: LineStyle.LargeDashed, swatch: "swatch-large-dashed" },
};
const FALLBACK_STYLE = BENCHMARK_STYLES.cdi!;

interface PortfolioChartProps {
  dates: string[];
  selected: PortfolioSeries;
  benchmarks: PortfolioSeries[];
}

function points(dates: string[], values: number[]) {
  return dates.map((time, i) => ({ time, value: values[i]! }));
}

/** Valor de R$ 100 investidos no início: a carteira escolhida contra as referências. */
export function PortfolioChart({ dates, selected, benchmarks }: PortfolioChartProps) {
  const host = useRef<HTMLDivElement>(null);
  useDrawIn(host, selected.id);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    const colors = chartColors();
    // escala logarítmica: em 12 anos a diferença entre carteiras de retorno parecido some na escala linear
    const chart = createChart(el, {
      ...baseOptions(colors, HEIGHT),
      rightPriceScale: { borderVisible: false, mode: PriceScaleMode.Logarithmic },
      width: el.clientWidth,
    });
    for (const b of benchmarks) {
      const { style } = BENCHMARK_STYLES[b.id] ?? FALLBACK_STYLE;
      chart
        .addLineSeries({ color: colors.benchmark, lineWidth: 2, lineStyle: style, priceLineVisible: false, lastValueVisible: false })
        .setData(points(dates, b.equity) as never);
    }
    chart
      .addLineSeries({ color: colors.action, lineWidth: 3, priceLineVisible: false })
      .setData(points(dates, selected.equity) as never);
    chart.timeScale().fitContent();
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth }));
    observer?.observe(el);
    return () => {
      observer?.disconnect();
      chart.remove();
    };
  }, [dates, selected, benchmarks]);

  const last = selected.equity[selected.equity.length - 1]!;
  return (
    <div className="portfolio-chart">
      <ul className="legend" aria-label="Legenda do gráfico">
        <li>
          <span className="swatch swatch-solid" aria-hidden="true" /> {selected.name}
        </li>
        {benchmarks.map((b) => (
          <li key={b.id}>
            <span className={`swatch ${(BENCHMARK_STYLES[b.id] ?? FALLBACK_STYLE).swatch}`} aria-hidden="true" /> {b.name}
          </li>
        ))}
      </ul>
      <p className="chart-note">Escala logarítmica: a mesma distância na vertical é sempre a mesma variação em porcentagem.</p>
      <div
        ref={host}
        className="chart-host"
        role="img"
        aria-label={`Gráfico do valor de R$ 100 investidos em ${selected.name} contra ${benchmarks.map((b) => b.name).join(", ")}. A carteira terminou em R$ ${last.toFixed(0)} (${formatPercent(last / 100 - 1, 0)} no total). Os números estão na tabela comparativa.`}
      />
    </div>
  );
}
