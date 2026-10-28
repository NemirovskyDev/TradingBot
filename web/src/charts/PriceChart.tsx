import { createChart, LineStyle, type ISeriesApi, type MouseEventParams } from "lightweight-charts";
import { useEffect, useMemo, useRef, useState } from "react";
import { formatDate, formatPrice } from "../data/format";
import type { Price, Trade } from "../data/types";
import { useDrawIn, useReducedMotion } from "../motion";
import { toCandles, toMarkers } from "./candles";
import { baseOptions, chartColors } from "./theme";
import "./charts.css";

const PULSE_MS = 260;

interface PriceChartProps {
  prices: Price[];
  trades: Trade[];
  selectedId: string | null;
  onSelect: (tradeId: string) => void;
}

/** Candles com compras e saídas marcadas; clicar em um marcador (ou na data de um evento) seleciona a operação. */
export function PriceChart({ prices, trades, selectedId, onSelect }: PriceChartProps) {
  const host = useRef<HTMLDivElement>(null);
  useDrawIn(host, prices);
  const series = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const latest = useRef({ trades, onSelect });
  latest.current = { trades, onSelect };
  const reduced = useReducedMotion();
  const [hoverDate, setHoverDate] = useState<string | null>(null);
  const byDate = useMemo(() => new Map(prices.map((p) => [p.date, p])), [prices]);
  const shown = (hoverDate ? byDate.get(hoverDate) : undefined) ?? prices.at(-1);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    const colors = chartColors();
    const height = window.innerWidth >= 1024 ? 540 : 360;
    const chart = createChart(el, { ...baseOptions(colors, height), width: el.clientWidth });
    // alta = vela vazada, baixa = vela cheia: o sentido não depende só da cor
    const candles = chart.addCandlestickSeries({
      upColor: colors.surface,
      borderUpColor: colors.gain,
      wickUpColor: colors.gain,
      downColor: colors.loss,
      borderDownColor: colors.loss,
      wickDownColor: colors.loss,
    });
    candles.setData(toCandles(prices) as never);
    series.current = candles;
    chart.timeScale().fitContent();

    const onClick = (param: MouseEventParams) => {
      const { trades: current, onSelect: select } = latest.current;
      if (typeof param.hoveredObjectId === "string") {
        const id = param.hoveredObjectId.split(":")[0];
        if (id && current.some((t) => t.id === id)) return select(id);
      }
      if (typeof param.time === "string") {
        const hit = current.find((t) => t.entry_date === param.time || t.exit_date === param.time);
        if (hit) select(hit.id);
      }
    };
    const onMove = (param: MouseEventParams) => setHoverDate(typeof param.time === "string" ? param.time : null);
    chart.subscribeClick(onClick);
    chart.subscribeCrosshairMove(onMove);

    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth }));
    observer?.observe(el);
    return () => {
      observer?.disconnect();
      chart.unsubscribeClick(onClick);
      chart.unsubscribeCrosshairMove(onMove);
      series.current = null;
      chart.remove();
    };
  }, [prices]);

  // marcadores; o selecionado dá um pulso único (maior e depois assenta), salvo com movimento reduzido
  useEffect(() => {
    const s = series.current;
    if (!s) return;
    const colors = chartColors();
    const settled = toMarkers(trades, selectedId, colors);
    if (!selectedId || reduced) {
      s.setMarkers(settled as never);
      return;
    }
    s.setMarkers(toMarkers(trades, selectedId, colors, 3) as never);
    const timer = window.setTimeout(() => s.setMarkers(settled as never), PULSE_MS);
    return () => window.clearTimeout(timer);
  }, [trades, selectedId, prices, reduced]);

  // níveis de entrada e de stop da operação selecionada
  useEffect(() => {
    const s = series.current;
    const trade = trades.find((t) => t.id === selectedId);
    if (!s || !trade) return;
    const colors = chartColors();
    const base = { lineWidth: 1 as const, lineStyle: LineStyle.Dashed, axisLabelVisible: true };
    const lines = [
      s.createPriceLine({ ...base, price: trade.entry_price, color: colors.action, title: "Entrada" }),
      s.createPriceLine({ ...base, price: trade.stop, color: colors.loss, title: "Stop" }),
    ];
    return () => {
      for (const line of lines) {
        try {
          s.removePriceLine(line);
        } catch {
          /* o gráfico já foi removido junto com a tela */
        }
      }
    };
  }, [trades, selectedId, prices]);

  return (
    <div className="price-chart">
      {shown && (
        <div role="group" aria-label="Valores do candle" className="ohlc">
          <span className="ohlc-date">{formatDate(shown.date)}</span>
          <span>Abertura {formatPrice(shown.open)}</span>
          <span>Máxima {formatPrice(shown.high)}</span>
          <span>Mínima {formatPrice(shown.low)}</span>
          <span>Fechamento {formatPrice(shown.close)}</span>
        </div>
      )}
      <div ref={host} className="chart-host" role="img" aria-label="Gráfico de candles do ativo com as compras e saídas do bot" />
    </div>
  );
}
