import type { ReactNode } from "react";
import "./ui.css";

interface MetricProps {
  label: ReactNode;
  value: ReactNode;
  tone?: "good" | "bad" | "neutral";
  detail?: string;
}

/** Uma métrica da faixa de resumo: rótulo, valor e uma linha de contexto. A cor nunca é o único sinal (o texto explica). */
export function Metric({ label, value, tone = "neutral", detail }: MetricProps) {
  return (
    <div className="metric">
      <dt>{label}</dt>
      <dd className={`metric-value metric-${tone}`}>{value}</dd>
      {detail && <dd className="metric-detail">{detail}</dd>}
    </div>
  );
}
