import { createChart, LineStyle } from "lightweight-charts";
import { useEffect, useRef } from "react";
import { formatDate, formatPrice } from "../data/format";
import type { EquityPoint } from "../data/types";
import { useDrawIn } from "../motion";
import { toEquitySeries } from "./equity";
import { baseOptions, chartColors } from "./theme";
import "./charts.css";

const HEIGHT = 320;

/** Curva de capital do bot contra comprar e segurar. A tabela abaixo traz os mesmos dados para quem não usa o gráfico. */
export function EquityChart({ equity }: { equity: EquityPoint[] }) {
  const host = useRef<HTMLDivElement>(null);
  useDrawIn(host, equity);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    const colors = chartColors();
    const chart = createChart(el, { ...baseOptions(colors, HEIGHT), width: el.clientWidth });
    const { strategy, buyHold } = toEquitySeries(equity);
    chart
      .addLineSeries({ color: colors.benchmark, lineWidth: 2, lineStyle: LineStyle.Dashed, priceLineVisible: false })
      .setData(buyHold as never);
    chart.addLineSeries({ color: colors.action, lineWidth: 2, priceLineVisible: false }).setData(strategy as never);
    chart.timeScale().fitContent();
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth }));
    observer?.observe(el);
    return () => {
      observer?.disconnect();
      chart.remove();
    };
  }, [equity]);

  return (
    <div className="equity-chart">
      <ul className="legend" aria-label="Legenda do gráfico">
        <li>
          <span className="swatch swatch-solid" aria-hidden="true" /> Estratégia
        </li>
        <li>
          <span className="swatch swatch-dashed" aria-hidden="true" /> Comprar e segurar
        </li>
      </ul>
      <div ref={host} className="chart-host" role="img" aria-label="Gráfico da curva de capital da estratégia contra comprar e segurar" />
      <details className="data-table">
        <summary>Ver os dados em tabela</summary>
        <div className="table-scroll" role="region" aria-label="Dados da curva de capital" tabIndex={0}>
          <table>
            <thead>
              <tr>
                <th scope="col">Data</th>
                <th scope="col">Estratégia</th>
                <th scope="col">Comprar e segurar</th>
              </tr>
            </thead>
            <tbody>
              {equity.map((p) => (
                <tr key={p.date}>
                  <td>{formatDate(p.date)}</td>
                  <td>{formatPrice(p.strategy)}</td>
                  <td>{formatPrice(p.buy_hold)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
