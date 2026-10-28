import { useEffect, useRef, useState } from "react";
import { useIndex } from "./data/useIndex";
import { useRun } from "./data/useRun";
import type { Run, RunRef } from "./data/types";
import { ChartScreen } from "./features/chart/ChartScreen";
import { GlossaryScreen } from "./features/glossary/GlossaryScreen";
import { Overview } from "./features/overview/Overview";
import { RiskScreen } from "./features/risk/RiskScreen";
import { TradesScreen } from "./features/trades/TradesScreen";
import { Reveal } from "./motion";
import { ErrorBoundary } from "./ui/ErrorBoundary";
import { RunHeader } from "./ui/RunHeader";
import { Shell } from "./ui/Shell";
import { SimulationBanner } from "./ui/SimulationBanner";
import { EmptyState, ErrorState, Loading } from "./ui/States";
import { hrefTo, ROUTES, useHashRoute, type RouteId } from "./ui/routes";

function RunScreen({ run, route, selectedTrade }: { run: Run; route: RouteId; selectedTrade: string | null }) {
  switch (route) {
    case "grafico":
      return (
        <ChartScreen
          run={run}
          selectedId={selectedTrade}
          onSelect={(id) => {
            window.location.hash = hrefTo("grafico", { trade: id });
          }}
        />
      );
    case "operacoes":
      return <TradesScreen run={run} />;
    case "risco":
      return <RiskScreen run={run} />;
    default:
      return <Overview run={run} />;
  }
}

function Runs({ runs, route, selectedTrade }: { runs: RunRef[]; route: RouteId; selectedTrade: string | null }) {
  const [runId, setRunId] = useState<string>(runs[0]!.id);
  const state = useRun(runId);

  const changeRun = (id: string) => {
    setRunId(id);
    // o id da operação é de uma execução específica: outra execução poderia abrir uma operação diferente
    if (selectedTrade) window.location.hash = hrefTo(route);
  };

  return (
    <>
      {/* o seletor fica sempre visível: mesmo com erro ou carregando, o usuário consegue escolher outra execução */}
      <RunHeader run={state.status === "ready" ? state.run : undefined} runs={runs} value={runId} onChange={changeRun} />
      {state.status === "loading" && <Loading />}
      {state.status === "error" && <ErrorState error={state.error} onRetry={state.retry} />}
      {state.status === "ready" && (
        <ErrorBoundary key={`${runId}-${route}`}>
          <Reveal key={route}>
            <RunScreen run={state.run} route={route} selectedTrade={selectedTrade} />
          </Reveal>
        </ErrorBoundary>
      )}
    </>
  );
}

export default function App() {
  const { route, params } = useHashRoute();
  const index = useIndex();
  const firstRoute = useRef(true);

  useEffect(() => {
    const label = ROUTES.find((r) => r.id === route)?.label ?? "Painel";
    document.title = `${label} · TradingBot`;
    // trocar de tela por hash não move o foco sozinho: leva o foco ao conteúdo para teclado e leitor de tela
    if (firstRoute.current) {
      firstRoute.current = false;
      return;
    }
    document.getElementById("conteudo")?.focus({ preventScroll: true });
  }, [route]);

  let content;
  if (route === "glossario") {
    // o glossário não depende dos dados: continua útil mesmo se o carregamento falhar
    content = (
      <>
        <header className="run-header">
          <h1>Glossário</h1>
        </header>
        <GlossaryScreen />
      </>
    );
  } else if (index.status === "loading") {
    content = <Loading />;
  } else if (index.status === "error") {
    content = <ErrorState error={index.error} onRetry={index.retry} />;
  } else if (index.index.runs.length === 0) {
    content = <EmptyState title="Nenhuma execução disponível" hint="Gere os dados de exemplo com o backend e recarregue a página." />;
  } else {
    content = <Runs runs={index.index.runs} route={route} selectedTrade={params.get("trade")} />;
  }

  return (
    <>
      <SimulationBanner />
      <Shell route={route}>{content}</Shell>
    </>
  );
}
