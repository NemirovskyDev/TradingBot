export type OutcomeKind = "gain" | "loss" | "flat";

export interface Outcome {
  kind: OutcomeKind;
  /** minúsculo, para frases ("ganho", "perda", "sem variação") */
  word: string;
}

/** Resultado de uma operação em três estados, igual em todas as telas. "0,0%" (já arredondado) conta como sem variação. */
export function outcome(pnlPct: number): Outcome {
  if (Number(Math.abs(pnlPct * 100).toFixed(1)) === 0) return { kind: "flat", word: "sem variação" };
  return pnlPct > 0 ? { kind: "gain", word: "ganho" } : { kind: "loss", word: "perda" };
}

export const resultClass: Record<OutcomeKind, string> = {
  gain: "result-gain",
  loss: "result-loss",
  flat: "result-flat",
};
