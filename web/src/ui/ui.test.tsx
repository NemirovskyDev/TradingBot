import { act, render, renderHook, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { strategyLabel } from "../data/labels";
import { DataError } from "../data/validate";
import { makeIndex, makeRun } from "../test/fixtures";
import { Hint } from "./Hint";
import { RunHeader } from "./RunHeader";
import { RunSelector } from "./RunSelector";
import { Shell } from "./Shell";
import { EmptyState, ErrorState, Loading } from "./States";
import { useHashRoute } from "./routes";

afterEach(() => {
  window.location.hash = "";
});

test("useHashRoute follows the hash", async () => {
  const { result } = renderHook(() => useHashRoute());
  expect(result.current.route).toBe("visao-geral");
  act(() => {
    window.location.hash = "#/risco";
  });
  await waitFor(() => expect(result.current.route).toBe("risco"));
});

test("useHashRoute falls back to the overview for unknown routes and reads query params", async () => {
  window.location.hash = "#/nada-aqui?trade=t2";
  const { result } = renderHook(() => useHashRoute());
  expect(result.current.route).toBe("visao-geral");
  act(() => {
    window.location.hash = "#/grafico?trade=t2";
  });
  await waitFor(() => expect(result.current.route).toBe("grafico"));
  expect(result.current.params.get("trade")).toBe("t2");
});

test("Shell marks the current page and lists every section", () => {
  render(
    <Shell route="operacoes">
      <p>conteúdo</p>
    </Shell>,
  );
  const current = screen.getAllByRole("link", { current: "page" });
  expect(current.length).toBeGreaterThan(0);
  expect(current.every((a) => a.textContent?.includes("Operações"))).toBe(true);
  for (const label of ["Visão geral", "Gráfico", "Operações", "Risco", "Glossário"]) {
    expect(screen.getAllByRole("link", { name: label }).length).toBeGreaterThan(0);
  }
  expect(screen.getByText("conteúdo")).toBeInTheDocument();
});

test("Shell credits TradingView for the charts", () => {
  render(<Shell route="visao-geral">x</Shell>);
  expect(screen.getByRole("link", { name: /TradingView/i })).toHaveAttribute("href", "https://www.tradingview.com/");
});

test("Loading announces itself as a status", () => {
  render(<Loading />);
  expect(screen.getByRole("status")).toHaveTextContent(/carregando/i);
});

test("ErrorState shows the message and the retry button calls it", async () => {
  const onRetry = vi.fn();
  render(<ErrorState error={new DataError("Não foi possível carregar os dados (erro 404).")} onRetry={onRetry} />);
  expect(screen.getByRole("alert")).toHaveTextContent("erro 404");
  await userEvent.click(screen.getByRole("button", { name: /tentar de novo/i }));
  expect(onRetry).toHaveBeenCalledOnce();
});

test("EmptyState shows title and hint", () => {
  render(<EmptyState title="Nenhuma operação" hint="O bot não encontrou sinais neste período." />);
  expect(screen.getByText("Nenhuma operação")).toBeInTheDocument();
  expect(screen.getByText(/não encontrou sinais/)).toBeInTheDocument();
});

test("RunSelector lists runs and emits the chosen id", async () => {
  const onChange = vi.fn();
  render(<RunSelector runs={makeIndex().runs} value="demo-sma_cross" onChange={onChange} />);
  const select = screen.getByRole("combobox", { name: /execução/i });
  expect(select).toHaveValue("demo-sma_cross");
  await userEvent.selectOptions(select, "demo-momentum");
  expect(onChange).toHaveBeenCalledWith("demo-momentum");
});

test("RunHeader shows the 'exemplo' badge only for synthetic data", () => {
  const { rerender } = render(<RunHeader run={makeRun()} runs={makeIndex().runs} value="demo-sma_cross" onChange={() => {}} />);
  expect(screen.getByText("Exemplo")).toBeInTheDocument();
  const real = makeRun();
  real.meta.synthetic = false;
  rerender(<RunHeader run={real} runs={makeIndex().runs} value="demo-sma_cross" onChange={() => {}} />);
  expect(screen.queryByText("Exemplo")).not.toBeInTheDocument();
});

test("RunHeader names the strategy and the period in pt-BR", () => {
  render(<RunHeader run={makeRun()} runs={makeIndex().runs} value="demo-sma_cross" onChange={() => {}} />);
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/DEMO/);
  expect(screen.getByText(/01\/01\/2024/)).toBeInTheDocument();
});

test("Hint opens on focus, exposes role tooltip with the glossary text and closes on Escape", async () => {
  render(<Hint term="drawdown">Maior queda</Hint>);
  const trigger = screen.getByRole("button", { name: /maior queda/i });
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  await userEvent.tab();
  expect(trigger).toHaveFocus();
  const tip = await screen.findByRole("tooltip");
  expect(tip).toHaveTextContent(/pico/i);
  expect(trigger).toHaveAccessibleDescription(/pico/i);
  await userEvent.keyboard("{Escape}");
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
});

test("strategyLabel translates known strategies and keeps unknown ones", () => {
  expect(strategyLabel("sma_cross")).toBe("Cruzamento de médias");
  expect(strategyLabel("outra")).toBe("outra");
});

test("the skip link moves focus to the content without changing the route", async () => {
  window.location.hash = "#/grafico?trade=t2";
  render(
    <Shell route="grafico">
      <p>conteúdo</p>
    </Shell>,
  );
  await userEvent.click(screen.getByRole("link", { name: /ir para o conteúdo/i }));
  expect(window.location.hash).toBe("#/grafico?trade=t2");
  expect(screen.getByRole("main")).toHaveFocus();
});

test("Hint stays open while the pointer moves onto the tooltip (hoverable) and closes on Escape even without focus", async () => {
  render(<Hint term="stop">stop</Hint>);
  await userEvent.hover(screen.getByRole("button", { name: "stop" }));
  const tip = await screen.findByRole("tooltip");
  await userEvent.hover(tip);
  expect(screen.getByRole("tooltip")).toBeInTheDocument();
  await userEvent.keyboard("{Escape}");
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
});

test("ErrorState gives a plain-language message, the technical detail and what to do", () => {
  render(<ErrorState error={new DataError('Campo "meta.ticker" inválido: esperado texto.')} onRetry={() => {}} />);
  const alert = screen.getByRole("alert");
  expect(alert).toHaveTextContent(/meta\.ticker/);
  expect(alert).toHaveTextContent(/python -m tradingbot export/);
});

test("RunHeader still offers the selector when the run is not loaded", async () => {
  const onChange = vi.fn();
  render(<RunHeader runs={makeIndex().runs} value="demo-sma_cross" onChange={onChange} />);
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/Cruzamento de médias/);
  await userEvent.selectOptions(screen.getByRole("combobox", { name: /execução/i }), "demo-momentum");
  expect(onChange).toHaveBeenCalledWith("demo-momentum");
});

test("RunSelector shows readable strategy names, not raw ids", () => {
  render(<RunSelector runs={makeIndex().runs} value="demo-sma_cross" onChange={() => {}} />);
  expect(screen.getByRole("option", { name: /Cruzamento de médias/ })).toBeInTheDocument();
  expect(screen.queryByRole("option", { name: /sma_cross/ })).not.toBeInTheDocument();
});
