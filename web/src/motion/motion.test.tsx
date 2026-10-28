import { act, render, renderHook, screen, waitFor } from "@testing-library/react";
import { createRef } from "react";
import { setReducedMotion } from "../test/matchMedia";
import { CountUp, Reveal, useDrawIn, useReducedMotion } from "./index";

const fmt = (n: number) => `${n.toFixed(1)}%`;

test("useReducedMotion reads the preference and reacts when it changes", async () => {
  const { result } = renderHook(() => useReducedMotion());
  expect(result.current).toBe(true);
  act(() => setReducedMotion(false));
  await waitFor(() => expect(result.current).toBe(false));
});

test("CountUp shows the final value immediately when reduced motion is on", () => {
  render(<CountUp value={12.4} format={fmt} />);
  expect(screen.getByText("12.4%")).toBeInTheDocument();
});

test("CountUp animates and always ends on the final value", async () => {
  setReducedMotion(false);
  render(<CountUp value={50} format={fmt} duration={0.05} />);
  await waitFor(() => expect(screen.getByText("50.0%")).toBeInTheDocument(), { timeout: 2000 });
});

test("CountUp follows a new value", async () => {
  const { rerender } = render(<CountUp value={10} format={fmt} />);
  rerender(<CountUp value={20} format={fmt} />);
  expect(screen.getByText("20.0%")).toBeInTheDocument();
});

test("Reveal renders its children untouched when reduced motion is on", () => {
  render(
    <Reveal>
      <p>conteúdo</p>
    </Reveal>,
  );
  const el = screen.getByText("conteúdo").parentElement!;
  expect(el).toBeVisible();
  expect(el.style.opacity).toBe("");
});

test("Reveal keeps content in the DOM while animating and clears its inline styles at the end", async () => {
  setReducedMotion(false);
  render(
    <Reveal>
      <p>conteúdo</p>
    </Reveal>,
  );
  const el = screen.getByText("conteúdo").parentElement!;
  expect(screen.getByText("conteúdo")).toBeInTheDocument();
  await waitFor(() => expect(el.style.opacity).toBe(""), { timeout: 3000 });
});

test("useDrawIn leaves the element alone with reduced motion", () => {
  const el = document.createElement("div");
  document.body.append(el);
  const ref = { current: el };
  renderHook(() => useDrawIn(ref, "a"));
  expect(el.style.clipPath).toBe("");
  el.remove();
});

test("useDrawIn tolerates a ref with no element", () => {
  const ref = createRef<HTMLDivElement>();
  expect(() => renderHook(() => useDrawIn(ref, "a"))).not.toThrow();
});
