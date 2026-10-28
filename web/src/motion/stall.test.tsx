import { act, render, screen } from "@testing-library/react";
import { setReducedMotion } from "../test/matchMedia";
import { CountUp, Reveal } from "./index";

// Simula uma animação que nunca avança: o conteúdo precisa terminar visível e com o valor final mesmo assim.
vi.mock("motion", () => ({
  animate: () => ({ stop: () => {}, finished: new Promise(() => {}) }),
}));

beforeEach(() => {
  vi.useFakeTimers();
  setReducedMotion(false);
});
afterEach(() => vi.useRealTimers());

test("content is visible when the animation never runs: Reveal clears its hidden state by itself", () => {
  render(
    <Reveal>
      <p>conteúdo</p>
    </Reveal>,
  );
  const el = screen.getByText("conteúdo").parentElement!;
  expect(el.style.opacity).toBe("0"); // começou escondido para a animação
  act(() => void vi.advanceTimersByTime(3000));
  expect(el.style.opacity).toBe("");
});

test("CountUp ends on the final value even if the animation stalls", () => {
  render(<CountUp value={42} format={(n) => `${n}%`} duration={0.5} />);
  expect(screen.getByText("0%")).toBeInTheDocument();
  act(() => void vi.advanceTimersByTime(3000));
  expect(screen.getByText("42%")).toBeInTheDocument();
});
