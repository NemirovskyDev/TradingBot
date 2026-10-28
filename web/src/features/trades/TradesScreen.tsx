import { useState } from "react";
import { formatDate, formatPercent, formatPrice, formatQty } from "../../data/format";
import { outcome, resultClass } from "../../data/outcome";
import type { Run, Trade } from "../../data/types";
import { EmptyState } from "../../ui/States";
import { hrefTo } from "../../ui/routes";
import { SortableTable, type Column } from "../../ui/SortableTable";
import "./trades.css";

type Filter = "all" | "wins" | "losses";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "Todos" },
  { id: "wins", label: "Ganhos" },
  { id: "losses", label: "Perdas" },
];

const COLUMNS: Column<Trade>[] = [
  {
    key: "period",
    header: "Período",
    render: (t) => `${formatDate(t.entry_date)} → ${formatDate(t.exit_date)}`,
    sortValue: (t) => t.entry_date,
  },
  {
    key: "price",
    header: "Preço",
    align: "right",
    render: (t) => `${formatPrice(t.entry_price)} → ${formatPrice(t.exit_price)}`,
    sortValue: (t) => t.entry_price,
  },
  { key: "qty", header: "Quantidade", align: "right", render: (t) => formatQty(t.qty), sortValue: (t) => t.qty },
  {
    key: "result",
    header: "Resultado",
    align: "right",
    sortValue: (t) => t.pnl_pct,
    render: (t) => {
      const o = outcome(t.pnl_pct);
      return (
        <>
          <span className={resultClass[o.kind]}>{formatPercent(t.pnl_pct)}</span> <span className="result-word">{o.word}</span>
        </>
      );
    },
  },
  {
    key: "why",
    header: "Por quê",
    className: "wrap",
    render: (t) => (
      <>
        <p>
          <strong>Compra:</strong> {t.reason_entry}
        </p>
        <p>
          <strong>Saída:</strong> {t.reason_exit}
        </p>
      </>
    ),
  },
  {
    key: "link",
    header: "Gráfico",
    render: (t) => (
      <a
        className="row-link"
        href={hrefTo("grafico", { trade: t.id })}
        aria-label={`Ver no gráfico a operação de ${formatDate(t.entry_date)}`}
      >
        Ver no gráfico
      </a>
    ),
  },
];

export function TradesScreen({ run }: { run: Run }) {
  const [filter, setFilter] = useState<Filter>("all");
  if (run.trades.length === 0) {
    return <EmptyState title="Nenhuma operação" hint="O bot não encontrou sinais para operar neste período." />;
  }
  const rows = run.trades.filter((t) => {
    const kind = outcome(t.pnl_pct).kind;
    return filter === "wins" ? kind === "gain" : filter === "losses" ? kind === "loss" : true;
  });
  return (
    <section className="panel trades" aria-labelledby="trades-heading">
      <div className="trades-head">
        <h2 id="trades-heading">Operações</h2>
        <div role="group" aria-label="Filtrar por resultado" className="filter">
          {FILTERS.map((f) => (
            <button key={f.id} type="button" aria-pressed={filter === f.id} onClick={() => setFilter(f.id)}>
              {f.label}
            </button>
          ))}
        </div>
      </div>
      {rows.length === 0 ? (
        <EmptyState flat title="Nenhuma operação neste filtro" hint="Troque o filtro para ver as outras operações." />
      ) : (
        <SortableTable
          caption="Operações do bot"
          columns={COLUMNS}
          rows={rows}
          getKey={(t) => t.id}
          initialSort={{ key: "period", dir: "asc" }}
        />
      )}
    </section>
  );
}
