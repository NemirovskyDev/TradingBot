import { useId } from "react";
import { strategyLabel } from "../data/labels";
import type { RunRef } from "../data/types";
import "./ui.css";

interface RunSelectorProps {
  runs: RunRef[];
  value: string;
  onChange: (id: string) => void;
}

export function RunSelector({ runs, value, onChange }: RunSelectorProps) {
  const id = useId();
  return (
    <div className="run-selector">
      <label htmlFor={id}>Execução</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
        {runs.map((r) => (
          <option key={r.id} value={r.id}>
            {r.ticker} · {strategyLabel(r.strategy)}
          </option>
        ))}
      </select>
    </div>
  );
}
