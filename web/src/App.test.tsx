import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { makeIndex, makeRun } from "./test/fixtures";

vi.mock("lightweight-charts", async () => await import("./test/lightweightMock"));

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function stubFetch(handler: (url: string) => Response | Promise<Response>) {
  const fn = vi.fn((url: RequestInfo | URL) => Promise.resolve(handler(String(url))));
  vi.stubGlobal("fetch", fn);
  return fn;
}

function happyPath(url: string): Response {
  if (url.endsWith("data/index.json")) return json(makeIndex());
  if (url.endsWith("demo-sma_cross.json")) return json(makeRun());
  if (url.endsWith("demo-momentum.json")) return json(makeRun({ verdict: { passed: true, reasons: [] } }));
  return new Response("", { status: 404 });
}

afterEach(() => {
  vi.unstubAllGlobals();
  window.location.hash = "";
});

test("app renders the simulation banner", () => {
  stubFetch(happyPath);
  render(<App />);
  expect(screen.getByText(/Não é recomendação de investimento/i)).toBeInTheDocument();
});

test("app loads the index and shows the first run's overview", async () => {
  stubFetch(happyPath);
  render(<App />);
  expect(screen.getByRole("status")).toHaveTextContent(/carregando/i);
  expect(await screen.findByRole("heading", { level: 1, name: /DEMO/ })).toBeInTheDocument();
  expect(await screen.findByText("12,4%")).toBeInTheDocument();
  expect(screen.getByText("Exemplo")).toBeInTheDocument();
});

test("app shows an error with retry when the index cannot be loaded, and recovers", async () => {
  let fail = true;
  stubFetch((url) => (fail ? new Response("", { status: 500 }) : happyPath(url)));
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveTextContent(/erro 500/);
  fail = false;
  await userEvent.click(screen.getByRole("button", { name: /tentar de novo/i }));
  expect(await screen.findByText("12,4%")).toBeInTheDocument();
});

test("app shows an error when a run file is malformed, without a blank screen", async () => {
  stubFetch((url) => (url.endsWith("demo-sma_cross.json") ? json({ meta: {} }) : happyPath(url)));
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveTextContent(/inválido/i);
});

test("choosing another run loads it", async () => {
  stubFetch(happyPath);
  render(<App />);
  await screen.findByText("12,4%");
  await userEvent.selectOptions(screen.getByRole("combobox", { name: /estratégia/i }), "momentum");
  expect(await screen.findByText("Passou")).toBeInTheDocument();
});

test("the hash route switches screens", async () => {
  stubFetch(happyPath);
  render(<App />);
  await screen.findByText("12,4%");
  window.location.hash = "#/operacoes";
  expect(await screen.findByRole("table", { name: /operações do bot/i })).toBeInTheDocument();
  expect(document.title).toMatch(/Operações/);
});

test("the glossary works even if the data fails to load", async () => {
  stubFetch(() => new Response("", { status: 500 }));
  window.location.hash = "#/glossario";
  render(<App />);
  expect(await screen.findByRole("heading", { level: 1, name: "Glossário" })).toBeInTheDocument();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test("an index with no runs says there is nothing to show", async () => {
  stubFetch((url) => (url.endsWith("index.json") ? json({ schema: 1, runs: [] }) : json({}, 404)));
  render(<App />);
  expect(await screen.findByText(/nenhuma execução disponível/i)).toBeInTheDocument();
});

test("selecting a trade on the chart updates the hash so the link can be shared", async () => {
  stubFetch(happyPath);
  window.location.hash = "#/grafico";
  render(<App />);
  const buttons = await screen.findAllByRole("button", { name: /→/ });
  await userEvent.click(buttons[1]!);
  await waitFor(() => expect(window.location.hash).toBe("#/grafico?trade=t2"));
});

test("the run selector stays available when the run fails to load, so the user can leave the error", async () => {
  stubFetch((url) => (url.endsWith("demo-sma_cross.json") ? json({ meta: {} }) : happyPath(url)));
  render(<App />);
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  await userEvent.selectOptions(screen.getByRole("combobox", { name: /estratégia/i }), "momentum");
  expect(await screen.findByText("12,4%")).toBeInTheDocument();
});

test("switching run clears the selected trade from the link", async () => {
  stubFetch(happyPath);
  window.location.hash = "#/grafico?trade=t2";
  render(<App />);
  await screen.findByText("O preço tocou o stop de proteção.");
  await userEvent.selectOptions(screen.getByRole("combobox", { name: /estratégia/i }), "momentum");
  await waitFor(() => expect(window.location.hash).toBe("#/grafico"));
});

test("changing the route moves focus to the content for keyboard and screen reader users", async () => {
  stubFetch(happyPath);
  render(<App />);
  await screen.findByText("12,4%");
  window.location.hash = "#/risco";
  await waitFor(() => expect(screen.getByRole("main")).toHaveFocus());
});
