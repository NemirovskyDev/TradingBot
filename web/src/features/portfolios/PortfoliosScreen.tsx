import { useState } from "react";
import { PortfolioChart } from "../../charts/PortfolioChart";
import { formatDate, formatPercent } from "../../data/format";
import type { Portfolio, PortfolioData, PortfolioMetrics, PortfolioSeries, Profile } from "../../data/types";
import { CountUp, useReducedMotion } from "../../motion";
import { Hint } from "../../ui/Hint";
import { Metric } from "../../ui/MetricCard";
import { SortableTable, type Column } from "../../ui/SortableTable";
import { hrefTo } from "../../ui/routes";
import "./portfolios.css";

const pct = (v: number | null, digits = 1) => (v === null ? "—" : formatPercent(v, digits));
const sortable = (v: number | null) => v ?? Number.NEGATIVE_INFINITY;
/** 30% e não 30,0%: o produto 0,3 × 100 sai com ruído de ponto flutuante, então compara com folga. */
const weightDigits = (w: number) => (Math.abs(w * 100 - Math.round(w * 100)) < 1e-9 ? 0 : 1);
const lastValue = (equity: (number | null)[]) => equity.filter((v): v is number => v !== null).at(-1)!;

type Mode = "common" | "full";

interface Row {
  id: string;
  name: string;
  reference: boolean;
  example: boolean;
  start: string | null;
  metrics: PortfolioMetrics;
}

/** Mesma cor e formato de linha do gráfico: a tabela e o gráfico se explicam juntos. */
const REFERENCE_SWATCH: Record<string, string> = { cdi: "swatch-ref-cdi", ibovespa: "swatch-ref-ibov", sp500: "swatch-ref-sp" };

const columns = (selectedId: string, mode: Mode): Column<Row>[] => [
  {
    key: "name",
    header: "Carteira",
    render: (r) =>
      r.reference ? (
        <span className="name-cell">
          <span className={`swatch ${REFERENCE_SWATCH[r.id] ?? ""}`} aria-hidden="true" />
          {r.name}
          <span className="badge badge-quiet">Referência</span>
        </span>
      ) : (
        <span className="name-cell">
          <button type="button" className="row-pick" aria-pressed={r.id === selectedId}>
            {r.name}
          </button>
          {r.example && <span className="badge badge-quiet">Exemplo</span>}
        </span>
      ),
    sortValue: (r) => r.name,
  },
  ...(mode === "full"
    ? [{ key: "start", header: "Desde", render: (r: Row) => (r.start ? formatDate(r.start) : "—"), sortValue: (r: Row) => r.start ?? "" }]
    : []),
  { key: "cagr", header: "Ao ano", align: "right", render: (r) => pct(r.metrics.cagr), sortValue: (r) => sortable(r.metrics.cagr) },
  { key: "total", header: "No total", align: "right", render: (r) => pct(r.metrics.total_return, 0), sortValue: (r) => sortable(r.metrics.total_return) },
  { key: "dd", header: "Maior queda", align: "right", render: (r) => pct(r.metrics.max_drawdown), sortValue: (r) => sortable(r.metrics.max_drawdown) },
  { key: "vol", header: "Oscilação ao ano", align: "right", render: (r) => pct(r.metrics.volatility), sortValue: (r) => sortable(r.metrics.volatility) },
];

/** A frase que um leigo lê primeiro: o que a carteira rendeu e como se compara, no mesmo período. */
function reading(selected: Portfolio): string {
  const { cagr, max_drawdown } = selected.metrics;
  if (cagr === null) return "Não há dados suficientes para calcular o retorno ao ano.";
  const against = (id: string, label: string) => {
    const ref = selected.benchmarks[id]?.metrics.cagr;
    return ref == null ? null : `${cagr >= ref ? "acima" : "abaixo"} ${label} (${pct(ref)})`;
  };
  const parts = [against("cdi", "do CDI"), against("ibovespa", "do Ibovespa")].filter(Boolean).join(" e ");
  const drop = max_drawdown === null ? "" : ` A pior queda foi de ${pct(-max_drawdown)}.`;
  return `Rendeu ${pct(cagr)} ao ano${parts ? `, ${parts}` : ""}.${drop}`;
}

function AnnualTable({ selected, references }: { selected: Portfolio; references: PortfolioSeries[] }) {
  const refs = references.map((r) => ({
    id: r.id,
    name: r.name,
    map: new Map((selected.benchmarks[r.id]?.annual_returns ?? []).map((a) => [a.year, a.return])),
  }));
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

interface ProfilePanelProps {
  profile: Profile;
  data: PortfolioData;
  onPick: (id: string) => void;
}

/** O que esperar de um perfil: texto simples, os números reais do exemplo dele e as metodologias parecidas. */
function ProfilePanel({ profile, data, onPick }: ProfilePanelProps) {
  const example = data.portfolios.find((p) => p.id === profile.portfolio_id)!;
  const related = profile.related_ids.map((id) => data.portfolios.find((p) => p.id === id)).filter((p): p is Portfolio => p !== undefined);
  return (
    <div className="profile-panel" aria-live="polite">
      <h3>{profile.name}</h3>
      <p className="lead">{profile.expect}</p>
      <p className="reading">No exemplo “{example.name}”: {reading(example)}</p>
      <p className="profile-warning" role="note">
        <strong>Atenção:</strong> {profile.warning}
      </p>
      <div className="profile-links">
        <button type="button" className="button" onClick={() => onPick(example.id)}>
          Ver o exemplo em detalhe
        </button>
        {profile.runs_link && (
          <a className="button button-quiet" href={hrefTo("visao-geral")}>
            Ver as estratégias por ativo
          </a>
        )}
      </div>
      {related.length > 0 && (
        <div className="related">
          <p className="related-title">Metodologias parecidas, medidas no mesmo período para todas:</p>
          <ul>
            {related.map((p) => (
              <li key={p.id}>
                <button type="button" className="chip-link" onClick={() => onPick(p.id)}>
                  {p.name}
                </button>
                <span className="related-metrics">
                  {pct(p.metrics_common.cagr)} ao ano, queda de {pct(p.metrics_common.max_drawdown === null ? null : -p.metrics_common.max_drawdown)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function PortfoliosScreen({ data }: { data: PortfolioData }) {
  const [selectedId, setSelectedId] = useState(data.portfolios[0]!.id);
  const [profileId, setProfileId] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("common");
  const selected = data.portfolios.find((p) => p.id === selectedId) ?? data.portfolios[0]!;
  const profile = data.profiles.find((p) => p.id === profileId) ?? null;
  const reduced = useReducedMotion();
  const classic = data.portfolios.filter((p) => p.kind === "classic");
  const examples = data.portfolios.filter((p) => p.kind === "profile");

  /** Clique na tabela, num perfil ou numa metodologia parecida: escolhe a carteira e leva a tela e o foco ao detalhe (os chips só trocam, pois já estão perto). */
  const pick = (id: string) => {
    setSelectedId(id);
    requestAnimationFrame(() => {
      const heading = document.getElementById("detalhe");
      heading?.scrollIntoView?.({ behavior: reduced ? "auto" : "smooth", block: "start" });
      heading?.focus({ preventScroll: true });
    });
  };
  const pickProfile = (p: Profile) => {
    setProfileId(p.id);
    setSelectedId(p.portfolio_id);
  };

  const metricsOf = (s: { metrics: PortfolioMetrics; metrics_common: PortfolioMetrics }) => (mode === "common" ? s.metrics_common : s.metrics);
  const rows: Row[] = [
    ...data.portfolios.map((p) => ({ id: p.id, name: p.name, reference: false, example: p.kind === "profile", start: p.start, metrics: metricsOf(p) })),
    ...data.benchmarks.map((b) => ({ id: b.id, name: b.name, reference: true, example: false, start: null, metrics: metricsOf(b) })),
  ];
  const { metrics } = selected;

  return (
    <div className="portfolios">
      <header className="run-header">
        <div>
          <h1>Carteiras</h1>
          <p className="run-sub">
            Como metodologias clássicas de alocação e exemplos por objetivo teriam se saído em reais, desde {formatDate(data.start)} até {formatDate(data.end)}.
            É um <Hint term="backtest">backtest</Hint>: o passado não garante o futuro.
          </p>
        </div>
      </header>

      <fieldset className="chooser goals">
        <legend>Qual é o seu objetivo?</legend>
        <div className="goal-grid">
          {data.profiles.map((p) => (
            <label key={p.id} className="goal">
              <input type="radio" name="objetivo" value={p.id} checked={p.id === profileId} onChange={() => pickProfile(p)} />
              <span className="goal-card">
                <strong>{p.name}</strong>
                <span>{p.tagline}</span>
              </span>
            </label>
          ))}
        </div>
        {profile && <ProfilePanel profile={profile} data={data} onPick={pick} />}
      </fieldset>

      <section className="panel" aria-labelledby="comparativo">
        <h2 id="comparativo">Comparativo</h2>
        <p className="panel-sub">
          Todas começam com o mesmo valor, no mesmo dia. As referências mostram o que o dinheiro teria feito sem montar carteira. Clique em uma carteira para
          ver os detalhes.
        </p>
        <fieldset className="mode">
          <legend className="sr-only">Período usado na comparação</legend>
          <label>
            <input type="radio" name="periodo" checked={mode === "common"} onChange={() => setMode("common")} />
            <span>Mesmo período para todas (desde {formatDate(data.common_start)})</span>
          </label>
          <label>
            <input type="radio" name="periodo" checked={mode === "full"} onChange={() => setMode("full")} />
            <span>Histórico completo de cada uma</span>
          </label>
        </fieldset>
        {mode === "full" && (
          <p className="mode-note">
            Períodos diferentes não se comparam de forma justa: cada carteira entra com o seu começo, e as mais antigas pegaram crises que as outras não viveram.
          </p>
        )}
        {/* em tela média a tabela é mais larga que o painel: rola dentro dele em vez de alargar a página */}
        <div className="compare-scroll" role="region" aria-label="Tabela comparativa das carteiras" tabIndex={0}>
          <SortableTable
            key={mode}
            columns={columns(selected.id, mode)}
            rows={rows}
            getKey={(r) => r.id}
            caption="Retorno ao ano, retorno total, maior queda e oscilação de cada carteira e das referências"
            initialSort={{ key: "cagr", dir: "desc" }}
            onRowClick={(row) => !row.reference && pick(row.id)}
            rowClassName={(r) => (r.reference ? undefined : r.id === selected.id ? "pickable is-selected" : "pickable")}
          />
        </div>
      </section>

      <fieldset className="chooser">
        <legend>Escolha uma carteira para ver os detalhes</legend>
        <p className="chips-title">Metodologias clássicas</p>
        <div className="chips">
          {classic.map((p) => (
            <label key={p.id} className="chip">
              <input type="radio" name="carteira" value={p.id} checked={p.id === selected.id} onChange={() => setSelectedId(p.id)} />
              <span>{p.name}</span>
            </label>
          ))}
        </div>
        <p className="chips-title">Exemplos por objetivo (montados pelo projeto)</p>
        <div className="chips">
          {examples.map((p) => (
            <label key={p.id} className="chip">
              <input type="radio" name="carteira" value={p.id} checked={p.id === selected.id} onChange={() => setSelectedId(p.id)} />
              <span>{p.name}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <section className="panel detail" aria-labelledby="detalhe">
        <h2 id="detalhe" tabIndex={-1}>
          {selected.name}
        </h2>
        <p className="author">
          {selected.kind === "classic" ? `Metodologia de ${selected.author}` : selected.author} · de {formatDate(selected.start)} até {formatDate(data.end)}
        </p>
        <p className="lead">{selected.summary}</p>
        <p className="reading">{reading(selected)}</p>

        <dl className="metrics">
          <Metric
            label={<Hint term="cagr">Retorno ao ano</Hint>}
            value={metrics.cagr === null ? "—" : <CountUp value={metrics.cagr} format={formatPercent} />}
            detail={selected.benchmarks.cdi ? `CDI: ${pct(selected.benchmarks.cdi.metrics.cagr)}` : undefined}
          />
          <Metric label="Retorno no total" value={pct(metrics.total_return, 0)} detail={`R$ 100 viraram R$ ${lastValue(selected.equity).toFixed(0)}`} />
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
            <p>Os pesos mudam conforme o sinal. Ativos usados: {selected.universe.join(", ")}.</p>
          )}
          <p>
            {selected.rule} <Hint term="rebalanceamento">Rebalanceamento</Hint>{" "}
            {selected.rebalance === "yearly" ? "anual" : selected.rebalance === "monthly" ? "mensal" : "diário"}.
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
