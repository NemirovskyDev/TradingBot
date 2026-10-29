import { displayTicker, strategyLabel } from "./labels";

test("displayTicker hides the technical suffixes but keeps real tickers intact", () => {
  expect(displayTicker("PETR4.SA")).toBe("PETR4");
  expect(displayTicker("BTC-USD")).toBe("BTC");
  expect(displayTicker("petr4.sa")).toBe("petr4");
  expect(displayTicker("BRK-B")).toBe("BRK-B"); // o hífen de uma classe de ação não é sufixo de moeda
  expect(displayTicker("AAPL")).toBe("AAPL");
});

test("strategyLabel translates known strategies and keeps unknown ones", () => {
  expect(strategyLabel("momentum")).toBe("Momentum (tendência)");
  expect(strategyLabel("outra")).toBe("outra");
});
