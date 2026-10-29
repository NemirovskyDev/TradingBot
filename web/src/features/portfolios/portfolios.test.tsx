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
  expect(screen.getByText(/desde 01\/06\/2020 até 01\/06\/2021/)).toBeInTheDocument();
  const table = screen.getByRole("table", { name: /retorno ao ano/i });
  const names = within(table).getAllByRole("row").slice(1).map((r) => within(r).getAllByRole("cell")[0]!.textContent);
  expect(names).toHaveLength(9); // 6 carteiras e 3 referências
  expect(within(table).getAllByText("Referência")).toHaveLength(3);
  expect(within(table).getAllByText("Exemplo")).toHaveLength(4); // os 4 exemplos por perfil
});

test("the comparison table starts sorted by return per year, best first", () => {
  render(<PortfoliosScreen data={makePortfolios()} />);
  const rows = within(screen.getByRole("table", { name: /retorno ao ano/i })).getAllByRole("row").slice(1);
  const perYear = rows.map((r) => Number(within(r).getAllByRole("cell")[1]!.textContent!.replace("%", "").replace(",", ".")));
  expect(perYear).toEqual([...perYear].sort((x, y) => y - x));
  expect(within(rows[0]!).getAllByRole("cell")[0]).toHaveTextContent("Swing em ativos voláteis");
});

test("clicking a portfolio row in the table selects it and moves focus to its details", async () => {
  render(<PortfoliosScreen data={makePortfolios()} />);
  const table = screen.getByRole("table", { name: /retorno ao ano/i });
  await userEvent.click(within(table).getByRole("button", { name: "Momentum dual (GEM)" }));
  expect(screen.getByRole("region", { name: "Momentum dual (GEM)" })).toBeInTheDocument();
  expect(screen.getByRole("radio", { name: "Momentum dual (GEM)" })).toBeChecked(); // os chips acompanham
  await vi.waitFor(() => expect(screen.getByRole("heading", { level: 2, name: "Momentum dual (GEM)" })).toHaveFocus());
  expect(within(table).getByRole("button", { name: "Momentum dual (GEM)" })).toHaveAttribute("aria-pressed", "true");
  expect(within(table).getByRole("button", { name: "ARCA" })).toHaveAttribute("aria-pressed", "false");
});

test("the keyboard can pick a portfolio from the table with Enter", async () => {
  render(<PortfoliosScreen data={makePortfolios()} />);
  const table = screen.getByRole("table", { name: /retorno ao ano/i });
  within(table).getByRole("button", { name: "Momentum dual (GEM)" }).focus();
  await userEvent.keyboard("{Enter}");
  expect(screen.getByRole("region", { name: "Momentum dual (GEM)" })).toBeInTheDocument();
});

test("reference rows are not selectable and carry a swatch matching the chart", async () => {
  render(<PortfoliosScreen data={makePortfolios()} />);
  const table = screen.getByRole("table", { name: /retorno ao ano/i });
  expect(within(table).queryByRole("button", { name: /CDI|Ibovespa|S&P/ })).not.toBeInTheDocument();
  await userEvent.click(within(table).getByText("CDI"));
  expect(screen.getByRole("region", { name: "ARCA" })).toBeInTheDocument(); // nada mudou
  expect(table.querySelectorAll(".swatch-ref-cdi, .swatch-ref-ibov, .swatch-ref-sp")).toHaveLength(3);
});

test("the comparison uses the common window by default and can show each portfolio's full history", async () => {
  render(<PortfoliosScreen data={makePortfolios()} />);
  expect(screen.getByRole("radio", { name: /mesmo período para todas \(desde 01\/12\/2020\)/i })).toBeChecked();
  const table = () => screen.getByRole("table", { name: /retorno ao ano/i });
  const arcaCommon = within(within(table()).getByRole("button", { name: "ARCA" }).closest("tr")!).getAllByRole("cell")[1]!.textContent;
  expect(arcaCommon).toBe("11,1%"); // metrics_common: 12,5% − 1,4 ponto
  expect(within(table()).queryByRole("columnheader", { name: /desde/i })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("radio", { name: /histórico completo de cada uma/i }));
  const row = within(table()).getByRole("button", { name: "Momentum dual (GEM)" }).closest("tr")!;
  expect(within(row).getAllByRole("cell").map((c) => c.textContent)).toContain("01/12/2020"); // coluna Desde
  expect(within(row).getAllByRole("cell").map((c) => c.textContent)).toContain("15,8%"); // metrics próprio
  expect(screen.getByText(/períodos diferentes não se comparam de forma justa/i)).toBeInTheDocument();
});

test("choosing an objective shows what to expect, the real numbers of its example, the warning and similar methodologies", async () => {
  render(<PortfoliosScreen data={makePortfolios()} />);
  expect(screen.queryByRole("note", { name: /./ })).not.toBeInTheDocument();
  expect(screen.getAllByRole("radio", { name: /Perfil/ })).toHaveLength(4);
  await userEvent.click(screen.getByRole("radio", { name: /Perfil estabilidade/ }));
  const panel = screen.getByRole("heading", { level: 3, name: "Perfil estabilidade" }).closest(".profile-panel") as HTMLElement;
  expect(within(panel).getByText("O que esperar de estabilidade.")).toBeInTheDocument();
  expect(within(panel).getByText(/Rendeu 10,9% ao ano, acima do CDI \(10,1%\)/)).toBeInTheDocument();
  expect(within(panel).getByRole("note")).toHaveTextContent("Aviso de estabilidade.");
  expect(within(panel).getByRole("button", { name: "ARCA" })).toBeInTheDocument();
  expect(within(panel).getByText(/11,1% ao ano, queda de 20,0%/)).toBeInTheDocument(); // números da janela comum
  expect(screen.getByRole("region", { name: "Estabilidade" })).toBeInTheDocument(); // o detalhe abaixo acompanha
});

test("a profile with no similar methodology lists none, and only the swing profile links to the per-asset strategies", async () => {
  render(<PortfoliosScreen data={makePortfolios()} />);
  await userEvent.click(screen.getByRole("radio", { name: /Perfil renda-dividendos/ }));
  expect(screen.queryByText(/metodologias parecidas/i)).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: /estratégias por ativo/i })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("radio", { name: /Perfil swing-alto-risco/ }));
  expect(screen.getByRole("link", { name: /estratégias por ativo/i })).toHaveAttribute("href", "#/visao-geral");
});

test("picking a similar methodology from a profile selects it and moves focus to its details", async () => {
  render(<PortfoliosScreen data={makePortfolios()} />);
  await userEvent.click(screen.getByRole("radio", { name: /Perfil crescimento/ }));
  const panel = screen.getByRole("heading", { level: 3, name: "Perfil crescimento" }).closest(".profile-panel") as HTMLElement;
  await userEvent.click(within(panel).getByRole("button", { name: "Momentum dual (GEM)" }));
  expect(screen.getByRole("region", { name: "Momentum dual (GEM)" })).toBeInTheDocument();
  await vi.waitFor(() => expect(screen.getByRole("heading", { level: 2, name: "Momentum dual (GEM)" })).toHaveFocus());
});

test("the chips are grouped into classic methodologies and project examples", () => {
  render(<PortfoliosScreen data={makePortfolios()} />);
  expect(screen.getAllByRole("radio", { name: /^(ARCA|Momentum dual \(GEM\))$/ })).toHaveLength(2);
  expect(screen.getByText(/exemplos por objetivo \(montados pelo projeto\)/i)).toBeInTheDocument();
  expect(screen.getByRole("radio", { name: "Swing em ativos voláteis" })).toBeInTheDocument();
});

test("a portfolio that starts late shows its own start date and a chart that begins there", async () => {
  render(<PortfoliosScreen data={makePortfolios()} />);
  await userEvent.click(screen.getByRole("radio", { name: "Momentum dual (GEM)" }));
  const detail = screen.getByRole("region", { name: "Momentum dual (GEM)" });
  expect(within(detail).getByText(/de 01\/12\/2020 até 01\/06\/2021/)).toBeInTheDocument();
  const selectedSeries = calls.data.at(-1) as { time: string; value: number }[];
  expect(selectedSeries[0]).toEqual({ time: "2020-12-01", value: 100 }); // sem os pontos vazios do começo
  expect(selectedSeries).toHaveLength(3);
  const cdi = calls.data.at(-4) as { time: string; value: number }[];
  expect(cdi[0]).toEqual({ time: "2020-12-01", value: 100 }); // a referência é reescalada para começar junto
  expect(cdi.at(-1)!.value).toBeCloseTo((110 * 100) / 105, 6);
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
