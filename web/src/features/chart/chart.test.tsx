import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { toCandles, toMarkers } from "../../charts/candles";
import { calls, resetCalls } from "../../test/lightweightMock";
import { formatDate, formatPrice } from "../../data/format";
import { setReducedMotion } from "../../test/matchMedia";
import { makeRun } from "../../test/fixtures";
import { ChartScreen } from "./ChartScreen";
import { TradeDetail } from "./TradeDetail";

vi.mock("lightweight-charts", async () => await import("../../test/lightweightMock"));

beforeEach(resetCalls);

function Harness({ initial = null, run = makeRun() }: { initial?: string | null; run?: ReturnType<typeof makeRun> }) {
  const [id, setId] = useState<string | null>(initial);
  return <ChartScreen run={run} selectedId={id} onSelect={setId} />;
}

test("toCandles maps fields and sorts by date", () => {
  const prices = makeRun().prices.slice(0, 3).reverse();
  const candles = toCandles(prices);
  expect(candles.map((c) => c.time)).toEqual([...candles.map((c) => c.time)].sort());
  expect(candles[0]).toEqual({
    time: prices.at(-1)!.date,
    open: prices.at(-1)!.open,
    high: prices.at(-1)!.high,
    low: prices.at(-1)!.low,
    close: prices.at(-1)!.close,
  });
});

test("toMarkers makes a buy and an exit marker per trade, sorted by time", () => {
  const markers = toMarkers(makeRun().trades);
  expect(markers).toHaveLength(6);
  expect(markers.filter((m) => m.shape === "arrowUp")).toHaveLength(3);
  expect(markers.filter((m) => m.shape === "arrowDown")).toHaveLength(3);
  const times = markers.map((m) => m.time);
  expect(times).toEqual([...times].sort());
});

test("only the selected trade carries text labels, so dense charts stay readable", () => {
  expect(toMarkers(makeRun().trades).every((m) => m.text === "")).toBe(true);
  const labeled = toMarkers(makeRun().trades, "t2").filter((m) => m.text !== "");
  expect(labeled.map((m) => [m.id, m.text])).toEqual([
    ["t2:entry", "Compra"],
    ["t2:exit", "Saída"],
  ]);
});

test("buy and exit markers differ in shape and position, not only color", () => {
  const [buy, exit] = toMarkers(makeRun().trades.slice(0, 1));
  expect(buy!.shape).toBe("arrowUp");
  expect(exit!.shape).toBe("arrowDown");
  expect(buy!.position).toBe("belowBar");
  expect(exit!.position).toBe("aboveBar");
});

test("the selected trade gets bigger markers", () => {
  const markers = toMarkers(makeRun().trades, "t2");
  expect(markers.filter((m) => m.size === 2).map((m) => m.id)).toEqual(["t2:entry", "t2:exit"]);
});

test("TradeDetail shows both reasons, prices and the result with words", () => {
  const trade = makeRun().trades[1]!;
  render(<TradeDetail trade={trade} />);
  expect(screen.getByText(trade.reason_entry)).toBeInTheDocument();
  expect(screen.getByText(trade.reason_exit)).toBeInTheDocument();
  expect(screen.getByText("−4,2%")).toBeInTheDocument();
  expect(screen.getByText(/perda/i)).toBeInTheDocument();
});

test("ChartScreen asks for a click when nothing is selected", () => {
  render(<Harness />);
  expect(screen.getByText(/clique em um marcador/i)).toBeInTheDocument();
});

test("choosing a trade in the list opens its detail, by keyboard", async () => {
  render(<Harness />);
  const list = screen.getByRole("list", { name: /operações/i });
  const buttons = within(list).getAllByRole("button");
  expect(buttons).toHaveLength(3);
  buttons[1]!.focus();
  await userEvent.keyboard("{Enter}");
  expect(screen.getByText("O preço tocou o stop de proteção.")).toBeInTheDocument();
  expect(buttons[1]).toHaveAttribute("aria-pressed", "true");
});

test("a selected id from the URL opens its detail right away", () => {
  render(<Harness initial="t3" />);
  expect(screen.getByText("O período do teste terminou com a posição aberta.")).toBeInTheDocument();
});

test("clicking a marker on the chart selects its trade", async () => {
  render(<Harness />);
  expect(calls.clickHandlers).toHaveLength(1);
  calls.clickHandlers[0]!({ hoveredObjectId: "t2:exit" });
  expect(await screen.findByText("O preço tocou o stop de proteção.")).toBeInTheDocument();
});

test("clicking a date with a trade event falls back to the date match", async () => {
  render(<Harness />);
  calls.clickHandlers[0]!({ time: makeRun().trades[0]!.entry_date });
  expect(await screen.findByText(makeRun().trades[0]!.reason_exit)).toBeInTheDocument();
});

test("ChartScreen with one price point and no trades does not crash", () => {
  const run = makeRun({ prices: makeRun().prices.slice(0, 1), trades: [] });
  render(<Harness run={run} />);
  expect(screen.getByText(/nenhuma operação/i)).toBeInTheDocument();
});

test("ChartScreen with no prices shows an empty state and no chart", () => {
  render(<Harness run={makeRun({ prices: [] })} />);
  expect(screen.getByText(/sem dados de preço/i)).toBeInTheDocument();
  expect(calls.charts).toBe(0);
});

test("an unknown selected id shows the prompt instead of crashing", () => {
  render(<Harness initial="zzz" />);
  expect(screen.getByText(/clique em um marcador/i)).toBeInTheDocument();
});

test("the trade explanation sits above the list so it is visible without scrolling", () => {
  render(<Harness initial="t2" />);
  const detail = screen.getByText("O preço tocou o stop de proteção.");
  const list = screen.getByRole("list", { name: /operações/i });
  expect(detail.compareDocumentPosition(list) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

test("selecting a trade scrolls its explanation into view", async () => {
  const spy = vi.spyOn(Element.prototype, "scrollIntoView");
  render(<Harness />);
  expect(spy).not.toHaveBeenCalled();
  await userEvent.click(within(screen.getByRole("list", { name: /operações/i })).getAllByRole("button")[0]!);
  expect(spy).toHaveBeenCalled();
  spy.mockRestore();
});

test("the selected marker pulses once (bigger, then settles) unless reduced motion is on", async () => {
  setReducedMotion(false);
  render(<Harness initial="t2" />);
  await waitFor(() => {
    const sizes = calls.markers.map((m) => (m as Array<{ id: string; size: number }>).find((x) => x.id === "t2:entry")?.size);
    expect(sizes).toContain(3);
    expect(sizes.at(-1)).toBe(2);
  });
});

test("with reduced motion the selected marker goes straight to its final size", async () => {
  render(<Harness initial="t2" />);
  const sizes = calls.markers.map((m) => (m as Array<{ id: string; size: number }>).find((x) => x.id === "t2:entry")?.size);
  expect(sizes).not.toContain(3);
  expect(sizes.at(-1)).toBe(2);
});

test("the selected trade draws its entry and stop levels on the chart", () => {
  render(<Harness initial="t2" />);
  expect(calls.priceLines.map((l) => [l.title, l.price])).toEqual([
    ["Entrada", 110],
    ["Stop", 105.4],
  ]);
});

test("changing the selected trade removes the previous levels", async () => {
  render(<Harness initial="t1" />);
  await userEvent.click(within(screen.getByRole("list", { name: /operações/i })).getAllByRole("button")[1]!);
  expect(calls.removedPriceLines).toBe(2);
  expect(calls.priceLines).toHaveLength(4);
});

test("the OHLC read-out starts on the last candle and follows the crosshair", () => {
  const run = makeRun();
  render(<Harness run={run} />);
  const readout = screen.getByRole("group", { name: /valores do candle/i });
  const last = run.prices.at(-1)!;
  expect(readout).toHaveTextContent(formatDate(last.date));
  const first = run.prices[0]!;
  act(() => calls.crosshairHandlers[0]!({ time: first.date }));
  expect(readout).toHaveTextContent(formatDate(first.date));
  expect(readout).toHaveTextContent(formatPrice(first.close));
  act(() => calls.crosshairHandlers[0]!({}));
  expect(readout).toHaveTextContent(formatDate(last.date));
});

