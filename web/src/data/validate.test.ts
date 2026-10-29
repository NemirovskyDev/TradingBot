import { makeIndex, makeRun } from "../test/fixtures";
import { DataError, parseIndex, parseRun } from "./validate";

test("parseRun accepts a valid fixture", () => {
  const run = parseRun(JSON.parse(JSON.stringify(makeRun())));
  expect(run.trades).toHaveLength(3);
  expect(run.meta.params.risco.risk_per_trade).toBe(0.01);
});

test("parseRun rejects a missing trades field naming it", () => {
  const raw = JSON.parse(JSON.stringify(makeRun())) as Record<string, unknown>;
  delete raw.trades;
  expect(() => parseRun(raw)).toThrow(DataError);
  expect(() => parseRun(raw)).toThrow(/trades/);
});

test("parseRun rejects a non-ISO date and names the field", () => {
  const raw = JSON.parse(JSON.stringify(makeRun()));
  raw.prices[3].date = "12/09/2025";
  expect(() => parseRun(raw)).toThrow(/prices\[3\]\.date/);
});

test("parseRun rejects an impossible calendar date", () => {
  const raw = JSON.parse(JSON.stringify(makeRun()));
  raw.trades[0].entry_date = "2024-02-31";
  expect(() => parseRun(raw)).toThrow(DataError);
});

test.each([null, 42, "texto", [], undefined])("parseRun rejects non-object input %p", (value) => {
  expect(() => parseRun(value)).toThrow(DataError);
});

test("parseRun rejects a non-numeric price", () => {
  const raw = JSON.parse(JSON.stringify(makeRun()));
  raw.prices[0].close = "100";
  expect(() => parseRun(raw)).toThrow(/prices\[0\]\.close/);
});

test("parseRun accepts a run with no trades and no blocked signals", () => {
  const raw = JSON.parse(JSON.stringify(makeRun({ trades: [], blocked: [] })));
  expect(parseRun(raw).trades).toEqual([]);
});

test("parseIndex accepts schema 1", () => {
  expect(parseIndex(JSON.parse(JSON.stringify(makeIndex()))).runs).toHaveLength(2);
});

test("parseIndex rejects schema 2 with a version message", () => {
  expect(() => parseIndex({ schema: 2, runs: [] })).toThrow(/vers/i);
});

test("parseIndex rejects run ids that are not file-safe", () => {
  expect(() => parseIndex({ schema: 1, runs: [{ id: "../x", ticker: "A", strategy: "s", label: "l" }] })).toThrow(DataError);
});

test("parseRun rejects prices out of date order and names the index", () => {
  const raw = JSON.parse(JSON.stringify(makeRun()));
  [raw.prices[1], raw.prices[2]] = [raw.prices[2], raw.prices[1]];
  expect(() => parseRun(raw)).toThrow(/prices\[2\]\.date/);
});

test("parseRun rejects a repeated equity date", () => {
  const raw = JSON.parse(JSON.stringify(makeRun()));
  raw.equity[5].date = raw.equity[4].date;
  expect(() => parseRun(raw)).toThrow(/equity\[5\]\.date/);
});

test("parseRun rejects duplicate trade ids", () => {
  const raw = JSON.parse(JSON.stringify(makeRun()));
  raw.trades[1].id = raw.trades[0].id;
  expect(() => parseRun(raw)).toThrow(/trades\[1\]\.id/);
});

test("parseRun rejects trade ids that would break marker ids (colon, spaces)", () => {
  for (const bad of ["a:b", "a b", ""]) {
    const raw = JSON.parse(JSON.stringify(makeRun()));
    raw.trades[0].id = bad;
    expect(() => parseRun(raw)).toThrow(/trades\[0\]\.id/);
  }
});

test("parseIndex keeps optional name and category and rejects non-text values", () => {
  const run = { id: "a", ticker: "A", strategy: "s", label: "l", name: "Alfa", category: "Cripto" };
  expect(parseIndex({ schema: 1, runs: [run] }).runs[0]).toMatchObject({ name: "Alfa", category: "Cripto" });
  expect(() => parseIndex({ schema: 1, runs: [{ ...run, category: 3 }] })).toThrow(/runs\[0\]\.category/);
});

test("parseIndex rejects duplicate run ids", () => {
  const run = { id: "a", ticker: "A", strategy: "s", label: "l" };
  expect(() => parseIndex({ schema: 1, runs: [run, run] })).toThrow(/runs\[1\]\.id/);
});
