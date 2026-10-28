import { render, screen, within } from "@testing-library/react";
import { toEquitySeries } from "../../charts/equity";
import { calls, resetCalls } from "../../test/lightweightMock";
import { makeRun } from "../../test/fixtures";
import { Overview } from "./Overview";
import { VerdictPanel } from "./VerdictPanel";

vi.mock("lightweight-charts", async () => await import("../../test/lightweightMock"));

beforeEach(resetCalls);

test("Overview shows the four metrics formatted in pt-BR", () => {
  render(<Overview run={makeRun()} />);
  expect(screen.getByText("12,4%")).toBeInTheDocument(); // retorno
  expect(screen.getByText("−8,2%")).toBeInTheDocument(); // maior queda
  expect(screen.getByText("1,23")).toBeInTheDocument(); // sharpe
  expect(screen.getByText("3")).toBeInTheDocument(); // operações
  expect(screen.getByText(/9,1%/)).toBeInTheDocument(); // benchmark ao lado do retorno
});

test("Overview summarizes wins and losses with correct plurals", () => {
  render(<Overview run={makeRun()} />);
  expect(screen.getByText("2 ganhos · 1 perda")).toBeInTheDocument();
});

test("Overview with no trades says so instead of '0 ganhos · 0 perdas'", () => {
  render(<Overview run={makeRun({ trades: [] })} />);
  expect(screen.getByText("Nenhuma operação")).toBeInTheDocument();
});

test("VerdictPanel lists the reasons when the strategy did not pass", () => {
  render(<VerdictPanel verdict={{ passed: false, reasons: ["Poucas operações.", "Queda grande."] }} />);
  expect(screen.getByText(/Ainda não passou/)).toBeInTheDocument();
  const items = screen.getAllByRole("listitem");
  expect(items.map((i) => i.textContent)).toEqual(["Poucas operações.", "Queda grande."]);
});

test("VerdictPanel says so when every criterion was met", () => {
  render(<VerdictPanel verdict={{ passed: true, reasons: [] }} />);
  expect(screen.getByText("Passou")).toBeInTheDocument();
  expect(screen.queryByRole("list")).not.toBeInTheDocument();
});

test("toEquitySeries keeps order and length", () => {
  const run = makeRun();
  const { strategy, buyHold } = toEquitySeries(run.equity);
  expect(strategy).toHaveLength(run.equity.length);
  expect(buyHold).toHaveLength(run.equity.length);
  expect(strategy[0]).toEqual({ time: run.equity[0]!.date, value: run.equity[0]!.strategy });
  expect(buyHold.at(-1)).toEqual({ time: run.equity.at(-1)!.date, value: run.equity.at(-1)!.buy_hold });
});

test("EquityChart feeds both series to the chart and keeps a table alternative", () => {
  const { container } = render(<Overview run={makeRun()} />);
  expect(calls.charts).toBe(1);
  expect(calls.data).toHaveLength(2);
  expect(screen.getByText(/ver os dados em tabela/i)).toBeInTheDocument();
  const table = container.querySelector("table")!;
  expect(within(table).getAllByRole("row")).toHaveLength(61); // cabeçalho + 60 dias
});

test("Overview with an empty equity curve shows an empty state and no chart", () => {
  render(<Overview run={makeRun({ equity: [] })} />);
  expect(screen.getByText(/sem curva de capital/i)).toBeInTheDocument();
  expect(calls.charts).toBe(0);
});

test("EquityChart removes the chart on unmount", () => {
  const { unmount } = render(<Overview run={makeRun()} />);
  unmount();
  expect(calls.removed).toBe(1);
});

test("Overview with a single equity point renders without crashing", () => {
  const run = makeRun();
  render(<Overview run={{ ...run, equity: run.equity.slice(0, 1) }} />);
  expect(screen.getByText(/curva de capital/i)).toBeInTheDocument();
  expect(calls.data).toHaveLength(2);
});

test("Overview counts flat trades separately so wins + losses + flat equals the total", () => {
  const run = makeRun();
  run.trades[1]!.pnl_pct = 0;
  render(<Overview run={run} />);
  expect(screen.getByText("2 ganhos · 0 perdas · 1 sem variação")).toBeInTheDocument();
});
