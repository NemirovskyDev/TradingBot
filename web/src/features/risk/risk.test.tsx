import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { makeRun } from "../../test/fixtures";
import { Hint } from "../../ui/Hint";
import { TERMS } from "../glossary/terms";
import { GlossaryScreen } from "../glossary/GlossaryScreen";
import { RiskScreen } from "./RiskScreen";

test("RiskScreen lists blocked signals with date and reason", () => {
  render(<RiskScreen run={makeRun()} />);
  expect(screen.getByText("Limite de 5 posições abertas atingido.")).toBeInTheDocument();
  expect(screen.getByText("31/01/2024")).toBeInTheDocument();
});

test("RiskScreen shows an empty state when nothing was blocked", () => {
  render(<RiskScreen run={makeRun({ blocked: [] })} />);
  expect(screen.getByText("Nenhum sinal foi bloqueado")).toBeInTheDocument();
});

test("RiskScreen shows the configured limits in plain pt-BR", () => {
  render(<RiskScreen run={makeRun()} />);
  expect(screen.getByText("Risco por operação")).toBeInTheDocument();
  expect(screen.getByText("1%")).toBeInTheDocument();
  expect(screen.getByText("20%")).toBeInTheDocument();
  expect(screen.getByText("40%")).toBeInTheDocument();
  expect(screen.getByText("5%")).toBeInTheDocument();
  expect(screen.getByText("Sem corretagem")).toBeInTheDocument();
  expect(screen.getByText("0,05%")).toBeInTheDocument();
  expect(screen.getByText(/5 pontos-base/)).toBeInTheDocument();
});

test("RiskScreen does not crash when the run carries no limits", () => {
  const run = makeRun();
  run.meta.params = { estrategia: {}, risco: {}, custos: {} };
  render(<RiskScreen run={run} />);
  expect(screen.getByText(/limites não foram informados/i)).toBeInTheDocument();
});

test("RiskScreen explains that the risk gate is automatic and independent of the AI", () => {
  render(<RiskScreen run={makeRun()} />);
  expect(screen.getByText(/regra automática/i)).toBeInTheDocument();
});

test("GlossaryScreen has the required terms", () => {
  render(<GlossaryScreen />);
  for (const name of [/candle/i, /drawdown/i, /sharpe/i, /stop/i, /buy and hold/i]) {
    expect(screen.getAllByText(name).length).toBeGreaterThan(0);
  }
});

test("GlossaryScreen lists every term from the shared source, in alphabetical order", () => {
  render(<GlossaryScreen />);
  const names = screen.getAllByRole("term").map((t) => t.textContent ?? "");
  expect(names).toHaveLength(Object.keys(TERMS).length);
  expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b, "pt-BR")));
});

test("Hint text comes from the shared glossary", async () => {
  render(<Hint term="stop">stop</Hint>);
  await userEvent.tab();
  expect(await screen.findByRole("tooltip")).toHaveTextContent(TERMS.stop.short);
});
