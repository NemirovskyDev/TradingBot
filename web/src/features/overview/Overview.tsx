import { EquityChart } from "../../charts/EquityChart";
import { formatNumber, formatPercent } from "../../data/format";
import type { Run } from "../../data/types";
import { outcome, type OutcomeKind } from "../../data/outcome";
import { CountUp } from "../../motion";
import { Hint } from "../../ui/Hint";
import { Metric } from "../../ui/MetricCard";
import { EmptyState } from "../../ui/States";
import { VerdictPanel } from "./VerdictPanel";
import "./overview.css";

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

function tradeSummary(run: Run): string {
  if (run.trades.length === 0) return "Nenhuma operação";
  const count = (kind: OutcomeKind) => run.trades.filter((t) => outcome(t.pnl_pct).kind === kind).length;
  const flat = count("flat");
  const parts = [plural(count("gain"), "ganho", "ganhos"), plural(count("loss"), "perda", "perdas")];
  if (flat > 0) parts.push(`${flat} sem variação`);
  return parts.join(" · "); // ganhos + perdas + sem variação sempre somam o total
}

export function Overview({ run }: { run: Run }) {
  const { metrics } = run;
  return (
    <div className="overview">
      <dl className="metrics panel">
        <Metric
          label="Retorno da estratégia"
          value={<CountUp value={metrics.total_return} format={formatPercent} />}
          tone={metrics.total_return >= 0 ? "good" : "bad"}
          detail={`Comprar e segurar: ${formatPercent(metrics.benchmark_return)}`}
        />
        <Metric
          label={<Hint term="drawdown">Maior queda</Hint>}
          value={<CountUp value={-metrics.max_drawdown} format={formatPercent} />}
          tone="bad"
          detail="Do pico ao ponto mais baixo"
        />
        <Metric
          label={<Hint term="sharpe">Índice de Sharpe</Hint>}
          value={<CountUp value={metrics.sharpe} format={formatNumber} />}
          detail="Retorno por unidade de risco"
        />
        <Metric
          label="Operações"
          value={<CountUp value={metrics.n_trades} format={(n) => String(Math.round(n))} />}
          detail={tradeSummary(run)}
        />
      </dl>

      <div className="overview-grid">
        <section className="panel" aria-labelledby="equity-title">
          <h2 id="equity-title">Curva de capital</h2>
          <p className="panel-sub">
            Quanto o capital teria virado com o bot, contra <Hint term="buy_hold">comprar e segurar</Hint>.
          </p>
          {run.equity.length === 0 ? (
            <EmptyState flat title="Sem curva de capital" hint="Esta execução não trouxe os dados de capital." />
          ) : (
            <EquityChart equity={run.equity} />
          )}
        </section>
        <VerdictPanel verdict={run.verdict} />
      </div>
    </div>
  );
}
