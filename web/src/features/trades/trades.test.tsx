import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { makeRun } from "../../test/fixtures";
import { SortableTable, type Column } from "../../ui/SortableTable";
import { TradesScreen } from "./TradesScreen";

interface Row {
  id: string;
  name: string;
  value: number;
}
const ROWS: Row[] = [
  { id: "a", name: "Banana", value: 3 },
  { id: "b", name: "Abacaxi", value: 10 },
  { id: "c", name: "Cereja", value: 2 },
];
const COLUMNS: Column<Row>[] = [
  { key: "name", header: "Nome", render: (r) => r.name, sortValue: (r) => r.name },
  { key: "value", header: "Valor", align: "right", render: (r) => String(r.value), sortValue: (r) => r.value },
  { key: "note", header: "Nota", render: () => "—" },
];

function bodyNames(): string[] {
  return screen.getAllByRole("row").slice(1).map((r) => within(r).getAllByRole("cell")[0]!.textContent ?? "");
}

test("table sorts by header click and sets aria-sort, toggling direction", async () => {
  render(<SortableTable columns={COLUMNS} rows={ROWS} getKey={(r) => r.id} caption="Frutas" />);
  const header = screen.getByRole("columnheader", { name: /valor/i });
  expect(header).toHaveAttribute("aria-sort", "none");
  await userEvent.click(within(header).getByRole("button"));
  expect(header).toHaveAttribute("aria-sort", "ascending");
  expect(bodyNames()).toEqual(["Cereja", "Banana", "Abacaxi"]);
  await userEvent.click(within(header).getByRole("button"));
  expect(header).toHaveAttribute("aria-sort", "descending");
  expect(bodyNames()).toEqual(["Abacaxi", "Banana", "Cereja"]);
});

test("table sorts numbers numerically, not as text", async () => {
  render(<SortableTable columns={COLUMNS} rows={ROWS} getKey={(r) => r.id} caption="Frutas" initialSort={{ key: "value", dir: "asc" }} />);
  expect(bodyNames()).toEqual(["Cereja", "Banana", "Abacaxi"]); // 2, 3, 10 (como texto seria 10, 2, 3)
});

test("table sorts by keyboard (Enter on the header button)", async () => {
  render(<SortableTable columns={COLUMNS} rows={ROWS} getKey={(r) => r.id} caption="Frutas" />);
  within(screen.getByRole("columnheader", { name: /nome/i })).getByRole("button").focus();
  await userEvent.keyboard("{Enter}");
  expect(bodyNames()).toEqual(["Abacaxi", "Banana", "Cereja"]);
});

test("columns without sortValue have no sort button", () => {
  render(<SortableTable columns={COLUMNS} rows={ROWS} getKey={(r) => r.id} caption="Frutas" />);
  expect(within(screen.getByRole("columnheader", { name: /nota/i })).queryByRole("button")).toBeNull();
});

test("TradesScreen lists every trade and links each one to the chart", () => {
  render(<TradesScreen run={makeRun()} />);
  expect(screen.getAllByRole("row")).toHaveLength(4); // cabeçalho + 3
  const links = screen.getAllByRole("link", { name: /ver no gráfico/i });
  expect(links.map((l) => l.getAttribute("href"))).toEqual(["#/grafico?trade=t1", "#/grafico?trade=t2", "#/grafico?trade=t3"]);
});

test("filter 'Perdas' shows only negative results", async () => {
  render(<TradesScreen run={makeRun()} />);
  await userEvent.click(screen.getByRole("button", { name: "Perdas" }));
  expect(screen.getAllByRole("row")).toHaveLength(2);
  expect(screen.getByText("−4,2%")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Perdas" })).toHaveAttribute("aria-pressed", "true");
});

test("a filter with no matches shows an empty state", async () => {
  const wins = makeRun().trades.filter((t) => t.pnl_pct > 0);
  render(<TradesScreen run={makeRun({ trades: wins })} />);
  await userEvent.click(screen.getByRole("button", { name: "Perdas" }));
  expect(screen.getByText(/nenhuma operação neste filtro/i)).toBeInTheDocument();
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
});

test("a run with no trades shows the empty state and no filter", () => {
  render(<TradesScreen run={makeRun({ trades: [] })} />);
  expect(screen.getByText("Nenhuma operação")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Perdas" })).not.toBeInTheDocument();
});

test("the reason cell wraps long text instead of overflowing", () => {
  const long = "Texto muito longo ".repeat(30);
  const run = makeRun();
  run.trades[0]!.reason_entry = long.trim();
  render(<TradesScreen run={run} />);
  const cell = screen.getByText(long.trim()).closest("td")!;
  expect(cell).toHaveClass("wrap");
});

test("results use words as well as color", () => {
  render(<TradesScreen run={makeRun()} />);
  expect(screen.getAllByText(/ganho/i).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/perda/i).length).toBeGreaterThan(0);
});

test("period and price are single columns so the table fits next to the sidebar", () => {
  render(<TradesScreen run={makeRun()} />);
  const headers = screen.getAllByRole("columnheader").map((h) => h.textContent?.replace(/[↑↓]/g, "").trim());
  expect(headers).toEqual(["Período", "Preço", "Quantidade", "Resultado", "Por quê", "Gráfico"]);
  expect(screen.getByText("06/01/2024 → 16/01/2024")).toBeInTheDocument();
  expect(screen.getByText("102,50 → 108,10")).toBeInTheDocument();
});

test("a trade that ends flat (0,0%) is not called a gain or a loss, and counts are coherent", async () => {
  const run = makeRun();
  run.trades[1]!.pnl_pct = 0.00001;
  render(<TradesScreen run={run} />);
  expect(screen.getByText("sem variação")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Ganhos" }));
  expect(screen.getAllByRole("row")).toHaveLength(3); // cabeçalho + 2 ganhos
  await userEvent.click(screen.getByRole("button", { name: "Perdas" }));
  expect(screen.getByText(/nenhuma operação neste filtro/i)).toBeInTheDocument();
});

test("each 'Ver no gráfico' link names its own trade", () => {
  render(<TradesScreen run={makeRun()} />);
  const names = screen.getAllByRole("link", { name: /ver no gráfico/i }).map((l) => l.getAttribute("aria-label"));
  expect(new Set(names).size).toBe(3);
});

test("a mobile sort control sorts the table without the header buttons", async () => {
  render(<TradesScreen run={makeRun()} />);
  const select = screen.getByRole("combobox", { name: /ordenar por/i });
  await userEvent.selectOptions(select, "result:desc");
  const first = screen.getAllByRole("row")[1]!;
  expect(first).toHaveTextContent("7,2%");
});
