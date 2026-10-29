import { createChart, LineStyle, PriceScaleMode } from "lightweight-charts";
import { useEffect, useRef } from "react";
import { formatPercent } from "../data/format";
import type { PortfolioSeries } from "../data/types";
import { useDrawIn } from "../motion";
import { baseOptions, chartColors, type ChartColors } from "./theme";
import "./charts.css";

const HEIGHT = 340;

/** Cada referência tem cor, formato de linha e rótulo próprios: o formato e o rótulo separam as linhas também para quem não distingue cores. */
const BENCHMARK_STYLES: Record<string, { style: LineStyle; swatch: string; color: keyof ChartColors; tag: string }> = {
  cdi: { style: LineStyle.Dashed, swatch: "swatch-ref-cdi", color: "refCdi", tag: "CDI" },
  ibovespa: { style: LineStyle.Dotted, swatch: "swatch-ref-ibov", color: "refIbov", tag: "Ibov." },
  sp500: { style: LineStyle.LargeDashed, swatch: "swatch-ref-sp", color: "refSp", tag: "S&P" },
};
const FALLBACK_STYLE = BENCHMARK_STYLES.cdi!;

interface PortfolioChartProps {
  dates: string[];
  selected: PortfolioSeries;
  benchmarks: PortfolioSeries[];
}

/** Rótulo curto para a ponta da linha: sem o parêntese e sem a palavra "Carteira". */
const shortName = (name: string) => name.split(" (")[0]!.replace(/^Carteira /, "");

/** Pontos a partir do índice `from`, reescalados para valer 100 ali: a carteira e as referências começam juntas, mesmo que a referência exista há mais tempo. */
function points(dates: string[], values: (number | null)[], from: number) {
  const base = values[from];
  if (base == null) return [];
  return dates.flatMap((time, i) => (i >= from && values[i] != null ? [{ time, value: (values[i]! * 100) / base }] : []));
}

/** Valor de R$ 100 investidos no início: a carteira escolhida contra as referências. */
export function PortfolioChart({ dates, selected, benchmarks }: PortfolioChartProps) {
  const host = useRef<HTMLDivElement>(null);
  useDrawIn(host, selected.id);
  const from = selected.equity.findIndex((v) => v !== null);

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
      const { style, color, tag } = BENCHMARK_STYLES[b.id] ?? FALLBACK_STYLE;
      chart
        .addLineSeries({ color: colors[color], lineWidth: 2, lineStyle: style, priceLineVisible: false, title: tag })
        .setData(points(dates, b.equity, from) as never);
    }
    chart
      .addLineSeries({ color: colors.action, lineWidth: 3, priceLineVisible: false, title: shortName(selected.name) })
      .setData(points(dates, selected.equity, from) as never);
    chart.timeScale().fitContent();
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth }));
    observer?.observe(el);
    return () => {
      observer?.disconnect();
      chart.remove();
    };
  }, [dates, selected, benchmarks, from]);

  const last = selected.equity.filter((v): v is number => v !== null).at(-1)!;
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
