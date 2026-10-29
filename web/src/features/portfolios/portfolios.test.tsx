import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { calls, resetCalls } from "../../test/lightweightMock";
import { makePortfolios } from "../../test/fixtures";
import { PortfoliosScreen } from "./PortfoliosScreen";

vi.mock("lightweight-charts", async () => await import("../../test/lightweightMock"));

beforeEach(() => resetCalls());

test("shows the period, the backtest warning and the comparison table with the references", () => {
  render(<PortfoliosScreen data={makePortfolios()} />);
  expect(screen.getByRole("heading", { level: 1, name: "Carteiras" })).toBeInTheDocument();
  expect(screen.getByText(/01\/06\/2020/)).toBeInTheDocument();
  const table = screen.getByRole("table", { name: /retorno ao ano/i });
  const names = within(table).getAllByRole("row").slice(1).map((r) => within(r).getAllByRole("cell")[0]!.textContent);
  expect(names).toHaveLength(5); // 2 carteiras e 3 referências
  expect(within(table).getAllByText("Referência")).toHaveLength(3);
});

test("the comparison table starts sorted by return per year, best first", () => {
  render(<PortfoliosScreen data={makePortfolios()} />);
  const rows = within(screen.getByRole("table", { name: /retorno ao ano/i })).getAllByRole("row").slice(1);
  expect(within(rows[0]!).getAllByRole("cell")[0]).toHaveTextContent("S&P 500 em reais");
});

test("ARCA is shown first with its composition, rule and an honest reading against the references", () => {
  render(<PortfoliosScreen data={makePortfolios()} />);
  const detail = screen.getByRole("region", { name: "ARCA" });
  expect(within(detail).getByText(/Thiago Nigro/)).toBeInTheDocument();
  expect(within(detail).getByRole("list", { name: /composição/i })).toHaveTextContent("25%");
  expect(within(detail).getByText(/Rendeu 12,5% ao ano, acima do CDI \(10,1%\) e acima do Ibovespa \(10,4%\)/)).toBeInTheDocument();
  expect(within(detail).getByText(/Rebalanceia uma vez por ano/)).toBeInTheDocument();
});

test("choosing another portfolio redraws the chart and shows its own rule", async () => {
  render(<PortfoliosScreen data={makePortfolios()} />);
  const charts = calls.charts;
  await userEvent.click(screen.getByRole("radio", { name: "Momentum dual (GEM)" }));
  const detail = screen.getByRole("region", { name: "Momentum dual (GEM)" });
  expect(within(detail).getByText(/Decide no fechamento de cada mês/)).toBeInTheDocument();
  expect(within(detail).getByText(/Os pesos mudam conforme o sinal/)).toBeInTheDocument();
  expect(within(detail).queryByRole("list", { name: /composição/i })).not.toBeInTheDocument();
  expect(calls.charts).toBeGreaterThan(charts);
});

test("the chart draws the selected portfolio and the three references on the shared dates", () => {
  render(<PortfoliosScreen data={makePortfolios()} />);
  expect(calls.data).toHaveLength(4);
  expect(calls.data[0]).toHaveLength(4);
  expect(calls.data.at(-1)).toEqual([
    { time: "2020-06-01", value: 100 },
    { time: "2020-12-01", value: 110 },
    { time: "2021-03-01", value: 120 },
    { time: "2021-06-01", value: 130 },
  ]);
  expect(screen.getByRole("img", { name: /R\$ 100 investidos em ARCA/ })).toBeInTheDocument();
});

test("the annual table marks partial years and lines the references up by year", () => {
  render(<PortfoliosScreen data={makePortfolios()} />);
  const region = screen.getByRole("region", { name: /retorno de cada ano: ARCA/i });
  const rows = within(region).getAllByRole("row").slice(1);
  expect(within(rows[0]!).getByRole("rowheader")).toHaveTextContent("2020 (parcial)");
  expect(within(rows[1]!).getByRole("rowheader")).toHaveTextContent("2021");
  expect(within(rows[1]!).getAllByRole("cell").map((c) => c.textContent)).toEqual(["12,0%", "12,0%", "12,0%", "12,0%"]);
  expect(within(region).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
    "Ano",
    "ARCA",
    "CDI",
    "Ibovespa (BOVA11)",
    "S&P 500 em reais (IVVB11)",
  ]);
});

test("weights print without a spurious decimal (30%, not 30,0%) and keep real ones (7,5%)", () => {
  const data = makePortfolios();
  data.portfolios[0]!.components = [
    { label: "A", weight: 0.3 },
    { label: "B", weight: 0.075 },
    { label: "C", weight: 0.4 },
  ];
  render(<PortfoliosScreen data={data} />);
  const list = screen.getByRole("list", { name: /composição/i });
  expect(within(list).getAllByRole("listitem").map((li) => li.textContent)).toEqual(["A30%", "B7,5%", "C40%"]);
});

test("a null metric shows a dash instead of NaN", () => {
  const data = makePortfolios();
  data.portfolios[0]!.metrics.cagr = null;
  render(<PortfoliosScreen data={data} />);
  expect(screen.getByText(/Não há dados suficientes para calcular o retorno ao ano/)).toBeInTheDocument();
  expect(document.body.textContent).not.toMatch(/NaN|undefined/);
});

test("lists the assumptions, including that there is no income tax", () => {
  render(<PortfoliosScreen data={makePortfolios()} />);
  expect(screen.getByText("Não há imposto de renda.")).toBeInTheDocument();
});

test("no axe violations", async () => {
  const { container } = render(<PortfoliosScreen data={makePortfolios()} />);
  expect(await axe(container, { rules: { "color-contrast": { enabled: false } } })).toHaveNoViolations();
});
