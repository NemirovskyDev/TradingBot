import { formatDate } from "../data/format";
import { displayTicker, strategyLabel } from "../data/labels";
import type { Run, RunRef } from "../data/types";
import { Hint } from "./Hint";
import { RunSelector } from "./RunSelector";
import "./ui.css";

interface RunHeaderProps {
  /** Ausente enquanto a execução carrega ou se deu erro: o seletor continua ali para o usuário sair do problema. */
  run?: Run;
  runs: RunRef[];
  value: string;
  onChange: (id: string) => void;
}

export function RunHeader({ run, runs, value, onChange }: RunHeaderProps) {
  const ref = runs.find((r) => r.id === value);
  const ticker = run?.meta.ticker ?? ref?.ticker ?? "";
  const strategy = run?.meta.strategy ?? ref?.strategy ?? "";
  return (
    <header className="run-header">
      <div>
        <h1>
          {displayTicker(ticker)} · {strategyLabel(strategy)}
          {run?.meta.synthetic && (
            <span className="badge" title="Dados sintéticos gerados para demonstração">
              Exemplo
            </span>
          )}
        </h1>
        {ref?.name && (
          <p className="run-asset">
            {ref.name}
            {ref.category && <span className="run-category"> · {ref.category}</span>}
          </p>
        )}
        {run && (
          <p className="run-sub">
            <Hint term="fora_amostra">Trecho de teste</Hint>, de {formatDate(run.meta.start)} a {formatDate(run.meta.end)}
          </p>
        )}
      </div>
      <RunSelector runs={runs} value={value} onChange={onChange} />
    </header>
  );
}
