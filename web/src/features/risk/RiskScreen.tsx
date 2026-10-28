import { formatDate, formatPercent, formatPrice, formatQty } from "../../data/format";
import type { BlockedSignal, CostParams, RiskParams, Run } from "../../data/types";
import { EmptyState } from "../../ui/States";
import { SortableTable, type Column } from "../../ui/SortableTable";
import "./risk.css";

const pct = (v: number) => formatPercent(v, Number.isInteger(Number((v * 100).toFixed(6))) ? 0 : 1);

const RISK_LIMITS: { key: keyof RiskParams; label: string; format: (v: number) => string; note: string }[] = [
  { key: "risk_per_trade", label: "Risco por operação", format: pct, note: "do capital, no máximo, se o stop for atingido" },
  { key: "max_open_positions", label: "Posições abertas ao mesmo tempo", format: formatQty, note: "limite de operações simultâneas" },
  { key: "max_position_pct", label: "Tamanho máximo de uma posição", format: pct, note: "do capital em um único ativo" },
  { key: "max_sector_pct", label: "Máximo por setor", format: pct, note: "do capital em um mesmo setor" },
  { key: "weekly_loss_limit", label: "Perda semanal que pausa o bot", format: pct, note: "se o capital cair isso na semana, o bot para de comprar" },
];

const COSTS: { key: keyof CostParams; label: string; format: (v: number) => string; note: (v: number) => string }[] = [
  {
    key: "commission",
    label: "Corretagem",
    format: (v) => (v === 0 ? "Sem corretagem" : formatPrice(v)),
    note: () => "custo simulado em cada operação",
  },
  {
    key: "slippage_bps",
    label: "Escorregamento (slippage)",
    format: (v) => formatPercent(v / 10_000, 2),
    note: (v) => `${formatQty(v)} pontos-base: o preço executado fica um pouco pior que o esperado`,
  },
];

const BLOCKED_COLUMNS: Column<BlockedSignal>[] = [
  { key: "date", header: "Data", render: (b) => formatDate(b.date) },
  { key: "ticker", header: "Ativo", render: (b) => b.ticker },
  { key: "reason", header: "Motivo", className: "wrap", render: (b) => b.reason },
];

export function RiskScreen({ run }: { run: Run }) {
  const { risco, custos } = run.meta.params;
  const limits = RISK_LIMITS.filter((l) => risco[l.key] !== undefined);
  const costs = COSTS.filter((c) => custos[c.key] !== undefined);
  return (
    <div className="risk">
      <section className="panel" aria-labelledby="gate-title">
        <h2 id="gate-title">Portão de risco</h2>
        <p className="panel-sub">
          É uma regra automática, separada da inteligência artificial: qualquer compra que desrespeite estes limites é barrada, não importa a opinião do analista.
        </p>
        {limits.length + costs.length === 0 ? (
          <p>Os limites não foram informados nesta execução.</p>
        ) : (
          <dl className="limits">
            {limits.map((l) => (
              <div key={l.key}>
                <dt>{l.label}</dt>
                <dd>{l.format(risco[l.key]!)}</dd>
                <dd className="limit-note">{l.note}</dd>
              </div>
            ))}
            {costs.map((c) => (
              <div key={c.key}>
                <dt>{c.label}</dt>
                <dd>{c.format(custos[c.key]!)}</dd>
                <dd className="limit-note">{c.note(custos[c.key]!)}</dd>
              </div>
            ))}
          </dl>
        )}
      </section>

      <section className="panel blocked" aria-labelledby="blocked-title">
        <h2 id="blocked-title">Sinais bloqueados</h2>
        <p className="panel-sub">Vezes em que a estratégia quis comprar e o portão de risco disse não.</p>
        {run.blocked.length === 0 ? (
          <EmptyState flat title="Nenhum sinal foi bloqueado" hint="O portão de risco não precisou barrar nenhuma compra neste período." />
        ) : (
          <SortableTable caption="Sinais bloqueados pelo risco" columns={BLOCKED_COLUMNS} rows={run.blocked} getKey={(b) => `${b.date}|${b.ticker}|${b.reason}`} />
        )}
      </section>
    </div>
  );
}
