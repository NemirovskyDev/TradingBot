import { readFileSync } from "node:fs";
import { resolve } from "node:path";

// Contraste WCAG calculado direto de tokens.css: o jsdom não avalia contraste, então este teste é a trava.
const css = readFileSync(resolve(__dirname, "tokens.css"), "utf8");

function token(name: string): string {
  const match = css.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!match) throw new Error(`token --${name} não encontrado em tokens.css`);
  return match[1]!;
}

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = channels.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

const TEXT_PAIRS: [string, string][] = [
  ["ink", "surface"],
  ["ink", "ground"],
  ["ink", "action-wash"],
  ["ink-soft", "surface"],
  ["ink-soft", "ground"],
  ["ink-soft", "action-wash"],
  ["action", "surface"],
  ["action", "action-wash"],
  ["action-ink", "action"],
  ["gain", "surface"],
  ["gain", "ground"],
  ["loss", "surface"],
  ["loss", "ground"],
  ["alert", "surface"],
];

test.each(TEXT_PAIRS)("text --%s on --%s meets WCAG AA (4.5:1)", (fg, bg) => {
  expect(contrast(token(fg), token(bg))).toBeGreaterThanOrEqual(4.5);
});

test("white text on the dark tooltip background meets AA", () => {
  expect(contrast("#ffffff", token("ink"))).toBeGreaterThanOrEqual(4.5);
});

test("the dashed benchmark line is at least 3:1 against the chart background (non-text)", () => {
  expect(contrast("#6b7a8a", token("surface"))).toBeGreaterThanOrEqual(3);
});

test("button hover color keeps white text readable", () => {
  expect(contrast("#1b44bb", "#ffffff")).toBeGreaterThanOrEqual(4.5);
});
