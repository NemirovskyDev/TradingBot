import { useCallback, useEffect, useState } from "react";
import { loadPortfolios } from "./load";
import type { PortfolioData } from "./types";
import { DataError } from "./validate";

export type PortfoliosState =
  | { status: "loading" }
  | { status: "error"; error: DataError }
  | { status: "ready"; data: PortfolioData };

export function usePortfolios(): PortfoliosState & { retry: () => void } {
  const [state, setState] = useState<PortfoliosState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let current = true;
    setState({ status: "loading" });
    loadPortfolios().then(
      (data) => current && setState({ status: "ready", data }),
      (e: unknown) =>
        current && setState({ status: "error", error: e instanceof DataError ? e : new DataError("Erro inesperado ao carregar os dados.") }),
    );
    return () => {
      current = false;
    };
  }, [attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { ...state, retry };
}
