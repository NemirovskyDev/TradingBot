import { render } from "@testing-library/react";
import { axe } from "vitest-axe";
import { makeIndex, makeRun } from "./test/fixtures";
import { ChartScreen } from "./features/chart/ChartScreen";
import { GlossaryScreen } from "./features/glossary/GlossaryScreen";
import { Overview } from "./features/overview/Overview";
import { RiskScreen } from "./features/risk/RiskScreen";
import { TradesScreen } from "./features/trades/TradesScreen";
import { RunHeader } from "./ui/RunHeader";
import { Shell } from "./ui/Shell";
import { SimulationBanner } from "./ui/SimulationBanner";
import { ErrorState, Loading } from "./ui/States";
import { DataError } from "./data/validate";

vi.mock("lightweight-charts", async () => await import("./test/lightweightMock"));

// O jsdom não calcula contraste; ele é conferido em contrast.test.ts a partir dos tokens.
const options = { rules: { "color-contrast": { enabled: false } } };

function page(route: Parameters<typeof Shell>[0]["route"], body: React.ReactNode) {
  const run = makeRun();
  return (
    <>
      <SimulationBanner />
      <Shell route={route}>
        <RunHeader run={run} runs={makeIndex().runs} value="demo-sma_cross" onChange={() => {}} />
        {body}
      </Shell>
    </>
  );
}

test.each([
  ["visao-geral", () => <Overview run={makeRun()} />],
  ["grafico", () => <ChartScreen run={makeRun()} selectedId="t2" onSelect={() => {}} />],
  ["operacoes", () => <TradesScreen run={makeRun()} />],
  ["risco", () => <RiskScreen run={makeRun()} />],
  ["glossario", () => <GlossaryScreen />],
] as const)("no axe violations on the %s screen", async (route, body) => {
  const { container } = render(page(route, body()));
  expect(await axe(container, options)).toHaveNoViolations();
});

test("no axe violations on the empty, error and loading states", async () => {
  const { container } = render(
    <main>
      <Loading />
      <ErrorState error={new DataError("Não foi possível carregar os dados (erro 500).")} onRetry={() => {}} />
      <TradesScreen run={makeRun({ trades: [] })} />
      <RiskScreen run={makeRun({ blocked: [] })} />
    </main>,
  );
  expect(await axe(container, options)).toHaveNoViolations();
});
