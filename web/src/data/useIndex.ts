import { useCallback, useEffect, useState } from "react";
import { loadIndex } from "./load";
import type { RunIndex } from "./types";
import { DataError } from "./validate";

export type IndexState =
  | { status: "loading" }
  | { status: "error"; error: DataError }
  | { status: "ready"; index: RunIndex };

export function useIndex(): IndexState & { retry: () => void } {
  const [state, setState] = useState<IndexState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let current = true;
    setState({ status: "loading" });
    loadIndex().then(
      (index) => current && setState({ status: "ready", index }),
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
