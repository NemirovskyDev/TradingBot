import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { makeCatalogIndex, makeIndex, makeRun } from "../test/fixtures";
import { RunHeader } from "./RunHeader";
import { RunSelector } from "./RunSelector";

function setup(value = "aapl-sma_cross") {
  const onChange = vi.fn();
  const utils = render(<RunSelector runs={makeCatalogIndex().runs} value={value} onChange={onChange} />);
  return { onChange, ...utils };
}

const asset = () => screen.getByRole("combobox", { name: /ativo/i });
const strategy = () => screen.getByRole("combobox", { name: /estratégia/i });

test("the asset select groups assets by category and lists each asset once", () => {
  const { container } = setup();
  const groups = [...container.querySelectorAll("optgroup")].map((g) => g.getAttribute("label"));
  expect(groups).toEqual(["Ações EUA", "Ações B3", "Cripto"]);
  expect(within(asset()).getAllByRole("option")).toHaveLength(3);
});

test("asset options show the ticker and the name", () => {
  setup();
  expect(screen.getByRole("option", { name: "PETR4 · Petrobras PN" })).toBeInTheDocument(); // sem o ".SA" técnico
  expect(screen.getByRole("option", { name: "BTC · Bitcoin" })).toBeInTheDocument(); // sem o "-USD"
  expect(screen.getByRole("option", { name: "PETR4 · Petrobras PN" })).toHaveValue("PETR4.SA"); // o valor segue o ticker completo
});

test("the strategy select lists only the strategies of the current asset, in plain Portuguese", () => {
  setup("btc_usd-sma_cross");
  const options = within(strategy()).getAllByRole("option");
  expect(options.map((o) => o.textContent)).toEqual(["Cruzamento de médias"]);
  expect(asset()).toHaveValue("BTC-USD");
});

test("choosing another asset keeps the current strategy when that asset has it", async () => {
  const { onChange } = setup("aapl-sma_cross");
  await userEvent.selectOptions(asset(), "PETR4.SA");
  expect(onChange).toHaveBeenCalledWith("petr4_sa-sma_cross");
});

test("choosing an asset without the current strategy falls back to its first strategy", async () => {
  const { onChange } = setup("aapl-momentum");
  await userEvent.selectOptions(asset(), "BTC-USD");
  expect(onChange).toHaveBeenCalledWith("btc_usd-sma_cross");
});

test("choosing another strategy emits the run of the same asset", async () => {
  const { onChange } = setup("aapl-sma_cross");
  await userEvent.selectOptions(strategy(), "momentum");
  expect(onChange).toHaveBeenCalledWith("aapl-momentum");
});

test("without categories (synthetic demo) there are no option groups", () => {
  const { container } = render(<RunSelector runs={makeIndex().runs} value="demo-sma_cross" onChange={() => {}} />);
  expect(container.querySelectorAll("optgroup")).toHaveLength(0);
});

test("an unknown selected id falls back to the first run instead of crashing", () => {
  render(<RunSelector runs={makeCatalogIndex().runs} value="nao-existe" onChange={() => {}} />);
  expect(asset()).toHaveValue("AAPL");
});

test("RunHeader shows the asset name and category from the index", () => {
  render(<RunHeader run={makeRun()} runs={makeCatalogIndex().runs} value="petr4_sa-sma_cross" onChange={() => {}} />);
  expect(screen.getByText("Petrobras PN", { selector: ".run-asset" })).toBeInTheDocument();
  expect(screen.getByText(/Ações B3/, { selector: ".run-category" })).toBeInTheDocument();
});

test("RunHeader names the asset even while the run is loading", () => {
  render(<RunHeader runs={makeCatalogIndex().runs} value="btc_usd-sma_cross" onChange={() => {}} />);
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/^BTC · /);
  expect(screen.getByText("Bitcoin", { selector: ".run-asset" })).toBeInTheDocument();
});
