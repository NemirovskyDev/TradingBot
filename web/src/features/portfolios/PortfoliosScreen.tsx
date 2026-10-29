import { useState } from "react";
import { PortfolioChart } from "../../charts/PortfolioChart";
import { formatDate, formatPercent } from "../../data/format";
import type { PortfolioData, PortfolioSeries } from "../../data/types";
import { CountUp } from "../../motion";
import { Hint } from "../../ui/Hint";
import { Metric } from "../../ui/MetricCard";
import { SortableTable, type Column } from "../../ui/SortableTable";
import "./portfolios.css";

const pct = (v: number | null, digits = 1) => (v === null ? "—" : formatPercent(v, digits));
/** 30% e não 30,0%: o produto 0,3 × 100 sai com ruído de ponto flutuante, então compara com folga. */
const weightDigits = (w: number) => (Math.abs(w * 100 - Math.round(w * 100)) < 1e-9 ? 0 : 1);
const sortable = (v: number | null) => v ?? Number.NEGATIVE_INFINITY;

interface Row extends PortfolioSeries {
  reference: boolean;
}

const COLUMNS: Column<Row>[] = [
  {
    key: "name",
    header: "Carteira",
    render: (r) => (
      <span className="name-cell">
        {r.name}
        {r.reference && <span className="badge badge-quiet">Referência</span>}
      </span>
    ),
    sortValue: (r) => r.name,
  },
  { key: "cagr", header: "Ao ano", align: "right", render: (r) => pct(r.metrics.cagr), sortValue: (r) => sortable(r.metrics.cagr) },
  { key: "total", header: "No total", align: "right", render: (r) => pct(r.metrics.total_return, 0), sortValue: (r) => sortable(r.metrics.total_return) },
  { key: "dd", header: "Maior queda", align: "right", render: (r) => pct(r.metrics.max_drawdown), sortValue: (r) => sortable(r.metrics.max_drawdown) },
  { key: "vol", header: "Oscilação ao ano", align: "right", render: (r) => pct(r.metrics.volatility), sortValue: (r) => sortable(r.metrics.volatility) },
];

/** A frase que um leigo lê primeiro: o que a carteira rendeu e como se compara. */
function reading(selected: PortfolioSeries, cdi: PortfolioSeries | undefined, ibov: PortfolioSeries | undefined): string {
  const { cagr, max_drawdown } = selected.metrics;
  if (cagr === null) return "Não há dados suficientes para calcular o retorno ao ano.";
  const against = (ref: PortfolioSeries | undefined, label: string) =>
    ref?.metrics.cagr == null ? null : `${cagr >= ref.metrics.cagr ? "acima" : "abaixo"} ${label} (${pct(ref.metrics.cagr)})`;
  const parts = [against(cdi, "do CDI"), against(ibov, "do Ibovespa")].filter(Boolean).join(" e ");
  const drop = max_drawdown === null ? "" : ` A pior queda foi de ${pct(-max_drawdown)}.`;
  return `Rendeu ${pct(cagr)} ao ano${parts ? `, ${parts}` : ""}.${drop}`;
}

function AnnualTable({ selected, references }: { selected: PortfolioSeries; references: PortfolioSeries[] }) {
  const byYear = (s: PortfolioSeries) => new Map(s.annual_returns.map((a) => [a.year, a.return]));
  const refs = references.map((r) => ({ id: r.id, name: r.name, map: byYear(r) }));
  return (
    <div className="table-scroll" role="region" aria-label={`Retorno de cada ano: ${selected.name} e referências`} tabIndex={0}>
      <table className="annual">
        <thead>
          <tr>
            <th scope="col">Ano</th>
            <th scope="col">{selected.name}</th>
            {refs.map((r) => (
              <th key={r.id} scope="col">
                {r.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {selected.annual_returns.map((a) => (
            <tr key={a.year}>
              <th scope="row">
                {a.year}
                {a.partial && <span className="partial"> (parcial)</span>}
              </th>
              <td>{pct(a.return)}</td>
              {refs.map((r) => (
                <td key={r.id}>{pct(r.map.get(a.year) ?? null)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function PortfoliosScreen({ data }: { data: PortfolioData }) {
  const [selectedId, setSelectedId] = useState(data.portfolios[0]!.id);
  const selected = data.portfolios.find((p) => p.id === selectedId) ?? data.portfolios[0]!;
  const cdi = data.benchmarks.find((b) => b.id === "cdi");
  const ibov = data.benchmarks.find((b) => b.id === "ibovespa");
  const rows: Row[] = [
    ...data.portfolios.map((p) => ({ ...p, reference: false })),
    ...data.benchmarks.map((b) => ({ ...b, reference: true })),
  ];
  const { metrics } = selected;

  return (
    <div className="portfolios">
      <header className="run-header">
        <div>
          <h1>Carteiras</h1>
          <p className="run-sub">
            Como metodologias clássicas de alocação teriam se saído em reais, de {formatDate(data.start)} a {formatDate(data.end)}. É um{" "}
            <Hint term="backtest">backtest</Hint>: o passado não garante o futuro.
          </p>
        </div>
      </header>

      <section className="panel" aria-labelledby="comparativo">
        <h2 id="comparativo">Comparativo</h2>
        <p className="panel-sub">Todas começam com o mesmo valor, no mesmo dia. As referências mostram o que o dinheiro teria feito sem montar carteira.</p>
        {/* em tela média a tabela é mais larga que o painel: rola dentro dele em vez de alargar a página */}
        <div className="compare-scroll" role="region" aria-label="Tabela comparativa das carteiras" tabIndex={0}>
          <SortableTable
            columns={COLUMNS}
            rows={rows}
            getKey={(r) => r.id}
            caption="Retorno ao ano, retorno total, maior queda e oscilação de cada carteira e das referências"
            initialSort={{ key: "cagr", dir: "desc" }}
          />
        </div>
      </section>

      <fieldset className="chooser">
        <legend>Escolha uma carteira para ver os detalhes</legend>
        <div className="chips">
          {data.portfolios.map((p) => (
            <label key={p.id} className="chip">
              <input type="radio" name="carteira" value={p.id} checked={p.id === selected.id} onChange={() => setSelectedId(p.id)} />
              <span>{p.name}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <section className="panel detail" aria-labelledby="detalhe">
        <h2 id="detalhe">{selected.name}</h2>
        <p className="author">Metodologia de {selected.author}</p>
        <p className="lead">{selected.summary}</p>
        <p className="reading">{reading(selected, cdi, ibov)}</p>

        <dl className="metrics">
          <Metric
            label={<Hint term="cagr">Retorno ao ano</Hint>}
            value={metrics.cagr === null ? "—" : <CountUp value={metrics.cagr} format={formatPercent} />}
            detail={cdi ? `CDI: ${pct(cdi.metrics.cagr)}` : undefined}
          />
          <Metric
            label="Retorno no total"
            value={pct(metrics.total_return, 0)}
            detail={`R$ 100 viraram R$ ${selected.equity[selected.equity.length - 1]!.toFixed(0)}`}
          />
          <Metric
            label={<Hint term="drawdown">Maior queda</Hint>}
            value={metrics.max_drawdown === null ? "—" : <CountUp value={-metrics.max_drawdown} format={formatPercent} />}
            tone="bad"
            detail="Do pico ao ponto mais baixo"
          />
          <Metric label={<Hint term="volatilidade">Oscilação</Hint>} value={pct(metrics.volatility)} detail="Ao ano" />
        </dl>

        <PortfolioChart dates={data.dates} selected={selected} benchmarks={data.benchmarks} />

        <div className="how">
          <h3>Como funciona</h3>
          {selected.components.length > 0 ? (
            <ul className="components" aria-label="Composição da carteira">
              {selected.components.map((c) => (
                <li key={c.label}>
                  <span>{c.label}</span>
                  <strong>{formatPercent(c.weight, weightDigits(c.weight))}</strong>
                </li>
              ))}
            </ul>
          ) : (
            <p>Os pesos mudam conforme o sinal. Classes usadas: {selected.universe.join(", ")}.</p>
          )}
          <p>
            {selected.rule} <Hint term="rebalanceamento">Rebalanceamento</Hint> {selected.rebalance === "yearly" ? "anual" : "mensal"}.
          </p>
        </div>

        <h3>Ano a ano</h3>
        <AnnualTable selected={selected} references={data.benchmarks} />
      </section>

      <section className="panel" aria-labelledby="premissas">
        <h2 id="premissas">Como foi calculado</h2>
        <ul className="assumptions">
          {data.assumptions.map((a) => (
            <li key={a}>{a}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
