import { useCallback, useEffect, useState } from "react";
import { loadRun } from "./load";
import type { Run } from "./types";
import { DataError } from "./validate";

export type RunState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; error: DataError }
  | { status: "ready"; run: Run };

export type UseRun = RunState & { retry: () => void; run?: Run; error?: DataError };

/** Carrega uma execução; uma resposta atrasada de um id anterior é descartada. */
export function useRun(id: string | null, fetchFn: typeof fetch = fetch): UseRun {
  const [state, setState] = useState<RunState>({ status: id ? "loading" : "idle" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!id) {
      setState({ status: "idle" });
      return;
    }
    let current = true;
    setState({ status: "loading" });
    loadRun(id, fetchFn).then(
      (run) => current && setState({ status: "ready", run }),
      (e: unknown) =>
        current && setState({ status: "error", error: e instanceof DataError ? e : new DataError("Erro inesperado ao carregar os dados.") }),
    );
    return () => {
      current = false;
    };
    // fetchFn entra só por injeção em testes; mudar a identidade dele não deve recarregar
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { ...state, retry };
}
