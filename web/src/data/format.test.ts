import { formatDate, formatNumber, formatPercent, formatPrice } from "./format";

test("formatPercent uses pt-BR decimal comma and a typographic minus", () => {
  expect(formatPercent(0.124)).toBe("12,4%");
  expect(formatPercent(-0.082)).toBe("−8,2%");
  expect(formatPercent(0)).toBe("0,0%");
});

test("formatPercent never shows a negative zero", () => {
  expect(formatPercent(-0.00001)).toBe("0,0%");
  expect(formatPercent(-0)).toBe("0,0%");
});

test("formatPercent respects digits", () => {
  expect(formatPercent(0.1, 0)).toBe("10%");
  expect(formatPercent(0.12345, 2)).toBe("12,35%");
});

test("formatPrice uses two decimals, comma and thousands dots", () => {
  expect(formatPrice(512.4)).toBe("512,40");
  expect(formatPrice(1234.5)).toBe("1.234,50");
});

test("formatDate turns ISO into dd/mm/aaaa without timezone shifts", () => {
  expect(formatDate("2025-09-12")).toBe("12/09/2025");
  expect(formatDate("2025-01-01")).toBe("01/01/2025");
});

test("formatNumber uses the pt-BR comma and the typographic minus", () => {
  expect(formatNumber(1.234)).toBe("1,23");
  expect(formatNumber(-0.94)).toBe("−0,94");
  expect(formatNumber(-0.001)).toBe("0,00");
  expect(formatNumber(3, 0)).toBe("3");
});


test("formatPrice uses the typographic minus for negatives", () => {
  expect(formatPrice(-3.5)).toBe("−3,50");
});
