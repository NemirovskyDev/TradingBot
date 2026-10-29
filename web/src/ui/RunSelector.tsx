import { useId } from "react";
import { displayTicker, strategyLabel } from "../data/labels";
import type { RunRef } from "../data/types";
import "./ui.css";

interface RunSelectorProps {
  runs: RunRef[];
  value: string;
  onChange: (id: string) => void;
}

/**
 * Dois seletores: o ativo (agrupado por categoria, cada ativo uma vez) e a estratégia (só as que existem para o ativo).
 * Com centenas de execuções, um único seletor "ativo + estratégia" seria inviável de percorrer.
 */
export function RunSelector({ runs, value, onChange }: RunSelectorProps) {
  const assetId = useId();
  const strategyId = useId();
  const current = runs.find((r) => r.id === value) ?? runs[0];
  if (!current) return null;

  const firstByTicker = new Map<string, RunRef>();
  for (const r of runs) if (!firstByTicker.has(r.ticker)) firstByTicker.set(r.ticker, r);
  const grouped = [...firstByTicker.values()].some((r) => r.category);
  const groups = new Map<string, RunRef[]>();
  for (const r of firstByTicker.values()) {
    const key = r.category ?? "";
    groups.set(key, [...(groups.get(key) ?? []), r]);
  }
  const ofAsset = runs.filter((r) => r.ticker === current.ticker);

  const option = (r: RunRef) => (
    <option key={r.ticker} value={r.ticker}>
      {r.name ? `${displayTicker(r.ticker)} · ${r.name}` : displayTicker(r.ticker)}
    </option>
  );

  // ao trocar de ativo, mantém a estratégia atual se o novo ativo a tem; senão usa a primeira dele
  const changeAsset = (ticker: string) => {
    const options = runs.filter((r) => r.ticker === ticker);
    const next = options.find((r) => r.strategy === current.strategy) ?? options[0];
    if (next) onChange(next.id);
  };

  return (
    <div className="run-selector">
      <div className="select-field">
        <label htmlFor={assetId}>Ativo</label>
        <select id={assetId} value={current.ticker} onChange={(e) => changeAsset(e.target.value)}>
          {grouped
            ? [...groups.entries()].map(([category, items]) => (
                <optgroup key={category} label={category || "Outros"}>
                  {items.map(option)}
                </optgroup>
              ))
            : [...firstByTicker.values()].map(option)}
        </select>
      </div>
      <div className="select-field">
        <label htmlFor={strategyId}>Estratégia</label>
        <select
          id={strategyId}
          value={current.strategy}
          onChange={(e) => {
            const next = ofAsset.find((r) => r.strategy === e.target.value);
            if (next) onChange(next.id);
          }}
        >
          {ofAsset.map((r) => (
            <option key={r.id} value={r.strategy}>
              {strategyLabel(r.strategy)}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
