import { useEffect, useRef } from "react";
import { PriceChart } from "../../charts/PriceChart";
import { formatDate, formatPercent } from "../../data/format";
import { outcome, resultClass } from "../../data/outcome";
import type { Run } from "../../data/types";
import { Reveal, useReducedMotion } from "../../motion";
import { Hint } from "../../ui/Hint";
import { EmptyState } from "../../ui/States";
import { TradeDetail } from "./TradeDetail";
import "./chart-screen.css";

const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

interface ChartScreenProps {
  run: Run;
  selectedId: string | null;
  onSelect: (tradeId: string) => void;
}

export function ChartScreen({ run, selectedId, onSelect }: ChartScreenProps) {
  const selected = run.trades.find((t) => t.id === selectedId) ?? null;
  const detail = useRef<HTMLDivElement>(null);
  const mounted = useRef(false);
  const reduced = useReducedMotion();

  // ao escolher uma operação, a explicação (a história central da tela) entra na vista, sem tirar o foco de onde o usuário está
  useEffect(() => {
    if (!mounted.current) {
      mounted.current = true;
      return;
    }
    if (selectedId) detail.current?.scrollIntoView({ block: "nearest", behavior: reduced ? "auto" : "smooth" });
  }, [selectedId, reduced]);

  return (
    <div className="chart-screen">
      <section className="panel" aria-labelledby="price-title">
        <h2 id="price-title">Preço do ativo e jogadas do bot</h2>
        <p className="panel-sub">
          Cada barra é um <Hint term="candle">candle</Hint>. Seta para cima é compra; seta para baixo é saída. Clique em uma seta para ver o motivo.
        </p>
        {run.prices.length === 0 ? (
          <EmptyState flat title="Sem dados de preço" hint="Esta execução não trouxe os preços do ativo." />
        ) : (
          <PriceChart prices={run.prices} trades={run.trades} selectedId={selectedId} onSelect={onSelect} />
        )}
      </section>

      <div className="side">
        {run.trades.length === 0 ? (
          <EmptyState title="Nenhuma operação" hint="O bot não encontrou sinais para operar neste período." />
        ) : (
          <>
            <div ref={detail} aria-live="polite">
              {selected ? (
                <Reveal key={selected.id}>
                  <TradeDetail trade={selected} />
                </Reveal>
              ) : (
                <p className="prompt">Clique em um marcador do gráfico ou escolha uma operação na lista para ver a explicação.</p>
              )}
            </div>
            <section className="panel trade-list-panel" aria-labelledby="trades-title">
              <h2 id="trades-title">Operações</h2>
              <ul className="trade-list" aria-label="Operações do bot">
                {run.trades.map((t) => (
                  <li key={t.id}>
                    <button type="button" aria-pressed={t.id === selectedId} onClick={() => onSelect(t.id)}>
                      <span>
                        {formatDate(t.entry_date)} → {formatDate(t.exit_date)}
                      </span>
                      <span className={resultClass[outcome(t.pnl_pct).kind]}>
                        {capitalize(outcome(t.pnl_pct).word)} {formatPercent(Math.abs(t.pnl_pct))}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          </>
        )}
      </div>
    </div>
  );
}
